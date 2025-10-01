"""
Trending Lookback Sweep - käy läpi viimeiset 90 min new_listing/trending
ja työnnä uudet mintit putkeen (dedupe + cooldown)
"""
import asyncio
import aiohttp
import time
import logging
from typing import Callable, Dict, Any, Set
from dataclasses import dataclass

@dataclass
class TokenCandidate:
    """Token candidate from lookback sweep"""
    type: str  # "pair", "trending", "new_listing"
    mint: str
    meta: Dict[str, Any]
    source: str = "lookback"

class TrendingLookbackSweep:
    def __init__(
        self, 
        birdeye_api_key: str, 
        window_sec: int = 5400,  # 90 min
        interval_sec: int = 60,  # 1 min
        on_pair: Callable = None
    ):
        self.key = birdeye_api_key
        self.win = window_sec
        self.intv = interval_sec
        self.on_pair = on_pair
        self.seen: Set[str] = set()
        self.log = logging.getLogger(__name__)
        
    async def run_forever(self):
        """Run the lookback sweep forever"""
        if not self.key:
            self.log.warning("Birdeye API key missing, skipping lookback sweep")
            return
            
        self.log.info(f"Starting lookback sweep: {self.win}s window, {self.intv}s interval")
        
        while True:
            try:
                await self._sweep_new_listings()
                await self._sweep_trending()
            except Exception as e:
                self.log.error(f"Lookback sweep error: {e}")
            
            await asyncio.sleep(self.intv)
    
    async def _sweep_new_listings(self):
        """Sweep Birdeye new listings"""
        headers = {"X-API-KEY": self.key, "accept": "application/json"}
        url = "https://public-api.birdeye.so/defi/v2/tokens/new_listing?chain=solana&limit=200"
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = data.get("data", {}).get("tokens", [])
                        
                        current_time = time.time() * 1000
                        new_count = 0
                        
                        for token in tokens:
                            mint = token.get("address")
                            created_time = token.get("createdTime", 0)
                            
                            if not mint or mint in self.seen:
                                continue
                                
                            # Check if token is within our window
                            if (current_time - created_time) <= self.win * 1000:
                                self.seen.add(mint)
                                new_count += 1
                                
                                # Create token candidate
                                candidate = TokenCandidate(
                                    type="new_listing",
                                    mint=mint,
                                    meta={"birdeye": token, "created_time": created_time},
                                    source="lookback_new_listing"
                                )
                                
                                if self.on_pair:
                                    await self.on_pair(candidate)
                        
                        if new_count > 0:
                            self.log.info(f"Lookback sweep found {new_count} new listings")
                            
        except Exception as e:
            self.log.warning(f"New listings sweep error: {e}")
    
    async def _sweep_trending(self):
        """Sweep Birdeye trending tokens"""
        headers = {"X-API-KEY": self.key, "accept": "application/json"}
        url = "https://public-api.birdeye.so/defi/v2/tokens/trending?chain=solana&limit=100"
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = data.get("data", {}).get("tokens", [])
                        
                        current_time = time.time() * 1000
                        new_count = 0
                        
                        for token in tokens:
                            mint = token.get("address")
                            created_time = token.get("createdTime", 0)
                            
                            if not mint or mint in self.seen:
                                continue
                                
                            # Check if token is within our window
                            if (current_time - created_time) <= self.win * 1000:
                                self.seen.add(mint)
                                new_count += 1
                                
                                # Create token candidate
                                candidate = TokenCandidate(
                                    type="trending",
                                    mint=mint,
                                    meta={"birdeye": token, "created_time": created_time},
                                    source="lookback_trending"
                                )
                                
                                if self.on_pair:
                                    await self.on_pair(candidate)
                        
                        if new_count > 0:
                            self.log.info(f"Lookback sweep found {new_count} trending tokens")
                            
        except Exception as e:
            self.log.warning(f"Trending sweep error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sweep statistics"""
        return {
            "seen_tokens": len(self.seen),
            "window_sec": self.win,
            "interval_sec": self.intv
        }
