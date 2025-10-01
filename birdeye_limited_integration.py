from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import aiohttp


class LimitedMarketDataClient:
    """Kerää markkinametriikoita ilmaisista lähteistä.

    - DexScreener: likviditeetti, volyymi, viimeisin hinta
    - Jupiter Price API: hinnan täydennys
    - Solscan: holder-määrä ja metadata

    Tarkoituksena on korvata Birdeye API:n maksulliset ominaisuudet yhdistämällä
    useita ilmaisia lähteitä ja palauttaa mahdollisimman samanlainen metrikkapaketti.
    """

    def __init__(self, *, api_key: Optional[str] = None, timeout: float = 8.0) -> None:
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.logger = logging.getLogger(__name__)

    async def fetch(
        self,
        session: aiohttp.ClientSession,
        mint: str,
        *,
        age_minutes: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        dex_task = asyncio.create_task(self._fetch_dexscreener(session, mint))
        jupiter_task = asyncio.create_task(self._fetch_jupiter(session, mint))
        solscan_task = asyncio.create_task(self._fetch_solscan(session, mint))

        dex_metrics = await dex_task
        jupiter_price = await jupiter_task
        solscan_meta = await solscan_task

        if not dex_metrics and jupiter_price is None and solscan_meta is None:
            return None

        metrics: Dict[str, Any] = dex_metrics.copy() if dex_metrics else {}

        if jupiter_price is not None and metrics.get("price") is None:
            metrics["price"] = jupiter_price

        if solscan_meta:
            holders = solscan_meta.get("holders")
            if holders is not None:
                metrics.setdefault("holders", holders)
            symbol = solscan_meta.get("symbol")
            name = solscan_meta.get("name")
            if symbol and "metadata" not in metrics:
                metrics["metadata"] = {"symbol": symbol, "name": name}

        if age_minutes is not None and metrics.get("last_trade_minutes") is None:
            metrics["last_trade_minutes"] = age_minutes

        if metrics and "source" not in metrics:
            metrics["source"] = "limited"

        if not metrics:
            # muodostetaan minimaalinen paketti, jos saatiin edes hinta
            if jupiter_price is not None:
                metrics = {
                    "price": jupiter_price,
                    "volume_24h": None,
                    "liquidity": None,
                    "buyers_30m": None,
                    "holders": solscan_meta.get("holders") if solscan_meta else None,
                    "util": None,
                    "top_liquidity": [],
                    "source": "limited",
                    "last_trade_minutes": age_minutes,
                }
        else:
            metrics.setdefault("top_liquidity", [])

        return metrics or None

    async def _fetch_dexscreener(
        self,
        session: aiohttp.ClientSession,
        mint: str,
    ) -> Optional[Dict[str, Any]]:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
        try:
            async with session.get(url, timeout=self.timeout) as resp:
                if resp.status != 200:
                    self.logger.debug("DexScreener status %s mintille %s", resp.status, mint[:8])
                    return None
                data = await resp.json()
        except Exception as exc:
            self.logger.debug("DexScreener virhe %s: %s", mint[:8], exc)
            return None

        pairs = data.get("pairs") if isinstance(data, dict) else None
        if not isinstance(pairs, list) or not pairs:
            return None

        sol_pairs = [p for p in pairs if p.get("chainId") in {"solana", "101"}]
        candidates = sol_pairs or pairs

        def score(pair: Dict[str, Any]) -> float:
            liq = self._safe_float((pair.get("liquidity") or {}).get("usd")) or 0.0
            vol = self._safe_float((pair.get("volume") or {}).get("h24")) or 0.0
            return liq * 0.7 + vol * 0.3

        best = max(candidates, key=score)

        liquidity = self._safe_float((best.get("liquidity") or {}).get("usd"))
        volume = self._safe_float((best.get("volume") or {}).get("h24"))
        price = self._safe_float(best.get("priceUsd"), best.get("priceNative"))
        fdv = self._safe_float(best.get("fdv"))
        market_cap = self._safe_float(best.get("marketCap"))

        txns = best.get("txns") or {}
        h1 = txns.get("h1") or {}
        buyers_approx = self._safe_float(h1.get("buys"))

        now_ms = int(time.time() * 1000)
        last_trade_raw = best.get("updatedAt") or best.get("lastTradeAt") or best.get("lastTrade")
        last_trade_minutes = None
        if isinstance(last_trade_raw, (int, float)) and last_trade_raw > 0:
            last_trade_minutes = max(0.0, (now_ms - int(last_trade_raw)) / 60000.0)

        pair_created_at = best.get("pairCreatedAt")
        pair_age_hours = None
        if isinstance(pair_created_at, (int, float)) and pair_created_at > 0:
            pair_age_hours = max(0.0, (now_ms - int(pair_created_at)) / 3_600_000.0)

        util = None
        if liquidity and liquidity > 0 and volume is not None:
            util = volume / liquidity

        top_liq_pairs = []
        for item in sorted(
            candidates,
            key=lambda p: self._safe_float((p.get("liquidity") or {}).get("usd")) or 0.0,
            reverse=True,
        )[:2]:
            top_liq_pairs.append(
                {
                    "pairAddress": item.get("pairAddress"),
                    "dexId": item.get("dexId"),
                    "liquidity": self._safe_float((item.get("liquidity") or {}).get("usd")),
                    "volume_24h": self._safe_float((item.get("volume") or {}).get("h24")),
                    "url": item.get("url"),
                }
            )

        metrics: Dict[str, Any] = {
            "price": price,
            "liquidity": liquidity,
            "volume_24h": volume,
            "fdv": fdv,
            "market_cap": market_cap,
            "buyers_30m": buyers_approx,
            "util": util,
            "last_trade_minutes": last_trade_minutes,
            "pair_age_hours": pair_age_hours,
            "top_liquidity": top_liq_pairs,
            "source": "dexscreener",
        }
        price_change = best.get("priceChange") or {}
        if isinstance(price_change, dict):
            metrics["price_change_m5"] = self._safe_float(price_change.get("m5"))
            metrics["price_change_h1"] = self._safe_float(price_change.get("h1"))
            metrics["price_change_h24"] = self._safe_float(price_change.get("h24"))
        return metrics

    async def _fetch_jupiter(
        self,
        session: aiohttp.ClientSession,
        mint: str,
    ) -> Optional[float]:
        url = "https://price.jup.ag/v6/price"
        params = {"ids": mint}
        try:
            async with session.get(url, params=params, timeout=self.timeout) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None
        price = (((data.get("data") or {}).get(mint) or {}).get("price"))
        return self._safe_float(price)

    async def _fetch_solscan(
        self,
        session: aiohttp.ClientSession,
        mint: str,
    ) -> Optional[Dict[str, Any]]:
        url = "https://public-api.solscan.io/token/meta"
        params = {"tokenAddress": mint}
        headers = {"User-Agent": "matkatiimi-bot/1.0"}
        try:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None
        if isinstance(data, dict):
            holders = data.get("holder") or data.get("holders")
            symbol = data.get("symbol")
            name = data.get("name")
            return {"holders": self._safe_int(holders), "symbol": symbol, "name": name}
        return None

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            if isinstance(value, str) and not value.strip():
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(float(value))
        except (TypeError, ValueError):
            return None
