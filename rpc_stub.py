"""
Stub RPC implementation for load testing
"""
from __future__ import annotations
import asyncio
import time
import random
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class StubTokenInfo:
    """Mock token information"""
    mint: str
    symbol: str
    name: str
    decimals: int = 9
    supply: int = 1000000000
    freeze_authority: Optional[str] = None
    mint_authority: Optional[str] = None

@dataclass
class StubPoolInfo:
    """Mock pool information"""
    address: str
    token_a: str
    token_b: str
    liquidity_usd: float
    volume_24h: float
    price_change_24h: float

class StubSolanaRPC:
    """
    Stub RPC implementation for load testing
    - Simulates realistic response times
    - Returns consistent mock data
    - Configurable latency and error rates
    """
    
    def __init__(self, *, 
                 base_latency_ms: float = 50.0,
                 jitter_ms: float = 20.0,
                 error_rate: float = 0.01,
                 timeout_sec: float = 5.0):
        self.base_latency_ms = base_latency_ms
        self.jitter_ms = jitter_ms
        self.error_rate = error_rate
        self.timeout_sec = timeout_sec
        
        # Mock data cache
        self._token_cache: Dict[str, StubTokenInfo] = {}
        self._pool_cache: Dict[str, StubPoolInfo] = {}
        
    async def _simulate_latency(self):
        """Simulate realistic RPC latency"""
        latency = self.base_latency_ms + random.uniform(-self.jitter_ms, self.jitter_ms)
        latency = max(1.0, latency)  # Minimum 1ms
        await asyncio.sleep(latency / 1000.0)
        
    async def _should_error(self) -> bool:
        """Determine if this call should return an error"""
        return random.random() < self.error_rate
        
    async def get_token_info(self, mint: str) -> Optional[StubTokenInfo]:
        """Get token information with simulated latency"""
        await self._simulate_latency()
        
        if await self._should_error():
            raise Exception(f"RPC error for token {mint}")
            
        # Return cached or create new mock data
        if mint not in self._token_cache:
            self._token_cache[mint] = StubTokenInfo(
                mint=mint,
                symbol=f"TOKEN{len(self._token_cache) % 1000:03d}",
                name=f"Mock Token {len(self._token_cache)}",
                freeze_authority=None if random.random() > 0.1 else "FreezeAuth123",
                mint_authority=None if random.random() > 0.1 else "MintAuth123"
            )
            
        return self._token_cache[mint]
        
    async def get_pool_info(self, pool_address: str) -> Optional[StubPoolInfo]:
        """Get pool information with simulated latency"""
        await self._simulate_latency()
        
        if await self._should_error():
            raise Exception(f"RPC error for pool {pool_address}")
            
        # Return cached or create new mock data
        if pool_address not in self._pool_cache:
            self._pool_cache[pool_address] = StubPoolInfo(
                address=pool_address,
                token_a=f"TokenA{len(self._pool_cache)}",
                token_b=f"TokenB{len(self._pool_cache)}",
                liquidity_usd=random.uniform(1000, 10000000),
                volume_24h=random.uniform(10000, 1000000),
                price_change_24h=random.uniform(-50, 100)
            )
            
        return self._pool_cache[pool_address]
        
    async def get_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account information with simulated latency"""
        await self._simulate_latency()
        
        if await self._should_error():
            raise Exception(f"RPC error for account {address}")
            
        return {
            "lamports": random.randint(1000000, 1000000000),
            "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "executable": False,
            "rent_epoch": 0
        }
        
    async def get_multiple_accounts(self, addresses: List[str]) -> List[Optional[Dict[str, Any]]]:
        """Get multiple accounts with simulated latency"""
        await self._simulate_latency()
        
        if await self._should_error():
            raise Exception(f"RPC error for multiple accounts")
            
        results = []
        for address in addresses:
            results.append(await self.get_account_info(address))
            
        return results
        
    async def get_slot(self) -> int:
        """Get current slot with simulated latency"""
        await self._simulate_latency()
        return int(time.time() * 2)  # Mock slot progression
        
    async def get_block_height(self) -> int:
        """Get current block height with simulated latency"""
        await self._simulate_latency()
        return int(time.time() / 0.4)  # Mock block progression (2.5 blocks/sec)

