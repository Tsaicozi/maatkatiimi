import asyncio
import logging
import os
import time
import aiohttp
from typing import Callable, Dict, Any

class BirdeyeNewListingPoller:
    """
    Kevyt polleri: hakee Birdeye new_listing -listan ja emittoi mint-osoitteet.
    """
    def __init__(self, api_key: str, chain: str, interval_sec: float,
                 on_pair: Callable[[str, Dict[str, Any]], None]) -> None:
        self.api_key = api_key
        self.chain = chain
        self.interval_sec = interval_sec
        self.on_pair = on_pair
        self.logger = logging.getLogger(__name__)
        self._last_seen: set[str] = set()

    async def run_forever(self):
        headers = {"X-API-KEY": self.api_key, "accept": "application/json"}
        url = f"https://public-api.birdeye.so/defi/v2/tokens/new_listing?chain={self.chain}&limit=100"
        while True:
            try:
                async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as sess:
                    async with sess.get(url) as resp:
                        if resp.status != 200:
                            self.logger.warning("birdeye new_listing status=%s", resp.status)
                            await asyncio.sleep(self.interval_sec)
                            continue
                        payload = await resp.json()
                        items = (payload.get("data") or {}).get("tokens") or []
                        for it in items:
                            mint = it.get("address")
                            if not mint or mint in self._last_seen:
                                continue
                            self._last_seen.add(mint)
                            meta = {
                                "birdeye": {
                                    "symbol": it.get("symbol"),
                                    "name": it.get("name"),
                                    "price": it.get("price"),
                                    "liquidity": it.get("liquidity"),
                                    "v24hUSD": it.get("v24hUSD"),
                                    "pair": it.get("pair"),
                                }
                            }
                            self.on_pair(mint, meta)
            except Exception as e:
                self.logger.exception("birdeye_new_listing_poller_error: %s", e)
            await asyncio.sleep(self.interval_sec)
