#!/usr/bin/env python3
"""
RPC Pool with Round-Robin Load Balancing and Quarantine
Kevyt failover-mechanismi Solana RPC-endpointeille
"""

import time
import asyncio
import random
import logging
from typing import List, Optional, Callable, Any
from dataclasses import dataclass

log = logging.getLogger(__name__)

@dataclass
class RPCEndpoint:
    """Yksittäinen RPC endpoint karanteeni-tilalla"""
    url: str
    errors: int = 0
    quarantine_until: float = 0.0
    last_used: float = 0.0

    def healthy(self) -> bool:
        """Onko endpoint terve (ei karanteenissa)"""
        return time.time() >= self.quarantine_until

    def mark_error(self, penalty_sec: int = 120):
        """Merkitse virhe ja mahdollisesti karanteeni"""
        self.errors += 1
        if self.errors >= 5:  # 5 virhettä → karanteeni
            self.quarantine_until = time.time() + penalty_sec
            self.errors = 0
            log.warning(f"🚫 RPC endpoint karanteenissa: {self.url} ({penalty_sec}s)")

    def mark_success(self):
        """Merkitse onnistunut kutsu"""
        self.errors = 0
        self.last_used = time.time()

class RPCRoundRobin:
    """
    Round-robin RPC pool karanteeni-toiminnolla
    
    Features:
    - Round-robin load balancing
    - Automatic quarantine for failing endpoints
    - Fallback to least recently quarantined endpoint
    - Metrics integration
    """
    
    def __init__(self, endpoints: List[str], error_threshold: int = 5, penalty_sec: int = 120):
        self.nodes = [RPCEndpoint(url) for url in endpoints]
        self.current_index = 0
        self.error_threshold = error_threshold
        self.penalty_sec = penalty_sec
        
        # Sekoita järjestys alussa
        random.shuffle(self.nodes)
        log.info(f"🔄 RPC Pool alustettu: {len(self.nodes)} endpointtia")

    def _pick_healthy_endpoint(self) -> Optional[RPCEndpoint]:
        """Valitse seuraava terve endpoint round-robin:lla"""
        healthy_nodes = [n for n in self.nodes if n.healthy()]
        
        if not healthy_nodes:
            # Kaikki karanteenissa → valitse vanhin karanteeni
            oldest_quarantine = min(self.nodes, key=lambda n: n.quarantine_until)
            log.warning(f"⚠️ Kaikki RPC endpointit karanteenissa, käytetään: {oldest_quarantine.url}")
            return oldest_quarantine
        
        # Round-robin terveiden endpointtien joukossa
        for _ in range(len(healthy_nodes)):
            node = healthy_nodes[self.current_index % len(healthy_nodes)]
            self.current_index += 1
            return node
        
        return None

    async def call(self, rpc_function: Callable, *args, **kwargs) -> Any:
        """
        Suorita RPC-kutsu failover:lla
        
        Args:
            rpc_function: RPC-funktio joka ottaa endpoint URL:n ensimmäisenä parametrina
            *args, **kwargs: RPC-funktion parametrit (endpoint URL lisätään automaattisesti)
        
        Returns:
            RPC-funktion tulos
            
        Raises:
            Exception: Jos kaikki endpointit epäonnistuvat
        """
        last_exception: Optional[Exception] = None
        attempts = 0
        max_attempts = len(self.nodes)
        
        while attempts < max_attempts:
            node = self._pick_healthy_endpoint()
            if not node:
                break
                
            try:
                log.debug(f"🔄 RPC kutsu: {node.url}")
                result = await rpc_function(node.url, *args, **kwargs)
                node.mark_success()
                return result
                
            except Exception as e:
                node.mark_error(self.penalty_sec)
                last_exception = e
                attempts += 1
                
                log.warning(f"❌ RPC virhe {node.url}: {e}")
                
                # Lyhyt viive ennen seuraavaa yritystä
                if attempts < max_attempts:
                    await asyncio.sleep(0.1)
        
        # Kaikki endpointit epäonnistuivat
        error_msg = f"RPC pool exhausted after {attempts} attempts"
        if last_exception:
            error_msg += f" (last error: {last_exception})"
        
        log.error(f"💥 {error_msg}")
        raise RuntimeError(error_msg) from last_exception

    def get_status(self) -> dict:
        """Hae poolin tila metriikoita varten"""
        now = time.time()
        healthy_count = sum(1 for n in self.nodes if n.healthy())
        quarantined_count = len(self.nodes) - healthy_count
        
        return {
            "total_endpoints": len(self.nodes),
            "healthy_endpoints": healthy_count,
            "quarantined_endpoints": quarantined_count,
            "endpoints": [
                {
                    "url": node.url,
                    "healthy": node.healthy(),
                    "errors": node.errors,
                    "quarantine_remaining": max(0, node.quarantine_until - now)
                }
                for node in self.nodes
            ]
        }

# Globaalinen RPC pool instanssi
_rpc_pool: Optional[RPCRoundRobin] = None

def init_rpc_pool(endpoints: List[str], error_threshold: int = 5, penalty_sec: int = 120) -> RPCRoundRobin:
    """Alusta globaali RPC pool"""
    global _rpc_pool
    _rpc_pool = RPCRoundRobin(endpoints, error_threshold, penalty_sec)
    return _rpc_pool

def get_rpc_pool() -> Optional[RPCRoundRobin]:
    """Hae globaali RPC pool"""
    return _rpc_pool

async def rpc_call(rpc_function: Callable, *args, **kwargs) -> Any:
    """Kätevä wrapper globaaliin RPC pool:iin"""
    if not _rpc_pool:
        raise RuntimeError("RPC pool not initialized. Call init_rpc_pool() first.")
    return await _rpc_pool.call(rpc_function, *args, **kwargs)
