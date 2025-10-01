#!/usr/bin/env python3
"""DexScreener-pohjainen toisen vaiheen token seulonta.

Skripti lukee ensimmäisen vaiheen JSONL-syötteen (esim. Helius-mintit), hakee
DexScreener API:sta tokeniin liittyvät poolit, valitsee niistä parhaimman
likviditeetin, ja käyttää hinnan, volyymin sekä likviditeetin kynnysarvoja
seulomaan jatkoon vain lupaavimmat tokenit.

DexScreener ei vaadi API-avainta, joten skripti ei enää lue .env-tiedostoa.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import aiohttp


LOGGER_NAME = "dexscreener_second_stage"
logger = logging.getLogger(LOGGER_NAME)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


class DexScreenerClient:
    """Kevyt asiakas DexScreenerin token-endpointtiin."""

    BASE_URL = "https://api.dexscreener.com/latest/dex/tokens"

    def __init__(self, *, timeout: float = 10.0, max_concurrent: int = 4):
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "DexScreenerClient":
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        if self._session:
            await self._session.close()
        self._session = None

    async def fetch_pairs(self, mint: str) -> List[Dict[str, Any]]:
        session = await self._ensure_session()
        url = f"{self.BASE_URL}/{mint}"
        async with self._semaphore:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.debug("DexScreener palautti %s mintille %s", resp.status, mint[:8])
                        return []
                    payload = await resp.json()
            except Exception as exc:  # pragma: no cover - verkko-ongelmat
                logger.debug("DexScreener kutsu epäonnistui %s: %s", mint[:8], exc)
                return []

        pairs = payload.get("pairs") if isinstance(payload, dict) else None
        if not isinstance(pairs, list):
            return []
        return pairs


def parse_jsonl(path: Path) -> List[Dict[str, Any]]:
    tokens: List[Dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"Syötepolkua ei löytynyt: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                tokens.append(json.loads(line))
            except json.JSONDecodeError:
                logger.debug("Ohitetaan kelvoton JSON-rivi: %s", line[:80])
    return tokens


def write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _coerce_float(*values: Any) -> Optional[float]:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _select_best_pair(pairs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    best_liquidity = -1.0
    for pair in pairs:
        liq = _coerce_float((pair.get("liquidity") or {}).get("usd"))
        if liq is None:
            continue
        if liq > best_liquidity:
            best = pair
            best_liquidity = liq
    if best is None and pairs:
        best = pairs[0]
    return best


def extract_metrics(pairs: List[Dict[str, Any]]) -> Tuple[Dict[str, Optional[float]], Optional[Dict[str, Any]]]:
    best = _select_best_pair(pairs)
    if not best:
        return {"price": None, "volume_24h": None, "liquidity": None}, None

    volume_payload = best.get("volume") or {}
    liquidity_payload = best.get("liquidity") or {}

    metrics = {
        "price": _coerce_float(best.get("priceUsd"), best.get("priceNative")),
        "volume_24h": _coerce_float(volume_payload.get("h24"), volume_payload.get("hour24")),
        "liquidity": _coerce_float(liquidity_payload.get("usd")),
    }
    return metrics, best


@dataclass
class FilterConfig:
    min_liquidity: float
    min_volume: float
    min_price: float
    max_price: float


def token_passes_filter(metrics: Dict[str, Optional[float]], cfg: FilterConfig) -> Tuple[bool, str]:
    price = metrics.get("price")
    volume = metrics.get("volume_24h")
    liquidity = metrics.get("liquidity")

    if liquidity is None or liquidity < cfg.min_liquidity:
        return False, "liquidity"
    if volume is None or volume < cfg.min_volume:
        return False, "volume"
    if price is None:
        return False, "price_missing"
    if price < cfg.min_price:
        return False, "price_low"
    if cfg.max_price > 0 and price > cfg.max_price:
        return False, "price_high"
    return True, "ok"


async def filter_tokens(
    client: DexScreenerClient,
    mints: Iterable[Dict[str, Any]],
    cfg: FilterConfig,
    *,
    concurrency: int = 4,
) -> List[Dict[str, Any]]:
    semaphore = asyncio.Semaphore(concurrency)
    accepted: List[Dict[str, Any]] = []

    async def process(entry: Dict[str, Any]) -> None:
        mint = entry.get("mint") or entry.get("address")
        if not mint:
            return
        async with semaphore:
            pairs = await client.fetch_pairs(mint)
        if not pairs:
            return

        metrics, best_pair = extract_metrics(pairs)
        ok, reason = token_passes_filter(metrics, cfg)

        enriched = dict(entry)
        enriched.setdefault("dexscreener", {})
        ds_payload = enriched["dexscreener"] if isinstance(enriched["dexscreener"], dict) else {}
        ds_payload.update(
            {
                "price": metrics["price"],
                "volume_24h": metrics["volume_24h"],
                "liquidity": metrics["liquidity"],
                "filter_reason": reason,
            }
        )
        if best_pair:
            ds_payload.update(
                {
                    "pair_address": best_pair.get("pairAddress"),
                    "dex": best_pair.get("dexId"),
                    "url": best_pair.get("url"),
                    "base_symbol": best_pair.get("baseToken", {}).get("symbol"),
                    "quote_symbol": best_pair.get("quoteToken", {}).get("symbol"),
                    "raw": best_pair,
                }
            )
        enriched["dexscreener"] = ds_payload

        if ok:
            accepted.append(enriched)

    await asyncio.gather(*(process(entry) for entry in mints))
    return accepted


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DexScreener-vetoinen toisen vaiheen token filtteri")
    parser.add_argument("--input", type=str, required=True, help="JSONL syöte (esim. helius_mints.jsonl)")
    parser.add_argument("--output", type=str, required=True, help="JSONL tuloste seulotuille tokeneille")
    parser.add_argument("--min-liquidity", type=float, default=10_000.0, help="Vähimmäislikviditeetti (USD)")
    parser.add_argument("--min-volume", type=float, default=5_000.0, help="Vähimmäisvolyymi 24h (USD)")
    parser.add_argument("--min-price", type=float, default=0.0001, help="Vähimmäishinta (USD)")
    parser.add_argument("--max-price", type=float, default=10.0, help="Suurin sallittu hinta (0 = ei rajaa)")
    parser.add_argument("--concurrency", type=int, default=4, help="Samaan aikaan tehtävien pyyntöjen määrä")
    parser.add_argument("--verbose", action="store_true", help="Lisää debug-lokia")
    return parser


async def run_async(args: argparse.Namespace) -> int:
    mints = parse_jsonl(Path(args.input))
    if not mints:
        logger.warning("Syöte ei sisältänyt yhtään tokenia.")
        write_jsonl(Path(args.output), [])
        return 0

    cfg = FilterConfig(
        min_liquidity=max(0.0, args.min_liquidity),
        min_volume=max(0.0, args.min_volume),
        min_price=max(0.0, args.min_price),
        max_price=max(0.0, args.max_price),
    )

    async with DexScreenerClient(max_concurrent=max(1, args.concurrency)) as client:
        accepted = await filter_tokens(
            client,
            mints,
            cfg,
            concurrency=max(1, args.concurrency),
        )

    write_jsonl(Path(args.output), accepted)
    logger.info(
        "DexScreener-seulonta valmis. syöte=%d hyväksytty=%d tuloste=%s",
        len(mints),
        len(accepted),
        args.output,
    )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    try:
        return asyncio.run(run_async(args))
    except KeyboardInterrupt:  # pragma: no cover
        return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())

