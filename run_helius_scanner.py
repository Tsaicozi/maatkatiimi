#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import logging

from helius_token_scanner_bot import HeliusTokenScannerBot, DexInfoFetcher, DexInfo
from solana_rpc_helpers import rpc_get_tx


async def main():
    logging.basicConfig(level=logging.INFO)

    ws_url = os.getenv("HELIUS_WS_URL") or (
        f"wss://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY','')}"
    )
    programs = [
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # SPL Token program
    ]

    # Placeholder DEX fetchers — korvaa oikeilla toteutuksilla
    async def _dexscreener(mint: str) -> DexInfo:
        return DexInfo(status="not_found", reason="stub")

    async def _jupiter(mint: str) -> DexInfo:
        return DexInfo(status="not_found", reason="stub")

    async def _solscan(mint: str) -> DexInfo:
        return DexInfo(status="not_found", reason="stub")

    fetcher = DexInfoFetcher(dexscreener=_dexscreener, jupiter=_jupiter, solscan=_solscan)

    bot = HeliusTokenScannerBot(
        ws_url=ws_url,
        programs=programs,
        dex_fetcher=fetcher,
        rpc_get_tx=rpc_get_tx,
    )

    await bot.start()
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())

