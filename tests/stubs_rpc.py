# tests/stubs_rpc.py
from __future__ import annotations
import random, asyncio
from dataclasses import dataclass

@dataclass
class MintInfo:
    renounced_mint: bool
    renounced_freeze: bool
    decimals: int

@dataclass
class LPInfo:
    locked_or_burned: bool
    liquidity_usd: float

@dataclass
class Distribution:
    top_share: float
    total_holders: int

@dataclass
class FlowStats:
    unique_buyers: int
    buys: int
    sells: int
    buy_sell_ratio: float

class StubFastRPC:
    """Nopeat "rikastukset" ilman verkkoa; satunnaistaa järkevillä rajoilla."""
    async def get_mint_info(self, mint: str) -> MintInfo:
        await asyncio.sleep(0)  # yield
        # 90% renounced, 10% ei
        return MintInfo(
            renounced_mint=random.random() > 0.1, 
            renounced_freeze=True,
            decimals=9
        )

    async def get_lp_info(self, pool_address: str) -> LPInfo:
        await asyncio.sleep(0)
        liq = random.uniform(3000, 40000)  # 3k–40k USD
        # 85% locked/burned
        return LPInfo(locked_or_burned=random.random() > 0.15, liquidity_usd=liq)

    async def get_holder_distribution(self, mint: str, top_n: int = 10) -> Distribution:
        await asyncio.sleep(0)
        top_share = random.uniform(0.05, 0.92)  # 5–92 %
        return Distribution(top_share=top_share, total_holders=random.randint(50, 5000))

    async def get_flow_stats(self, mint: str, window_sec: int = 300) -> FlowStats:
        await asyncio.sleep(0)
        buys = random.randint(0, 120)
        sells = random.randint(0, 100)
        uniq = random.randint(0, 80)
        ratio = buys / max(sells, 1)  # Avoid division by zero
        return FlowStats(unique_buyers=uniq, buys=buys, sells=sells, buy_sell_ratio=ratio)
