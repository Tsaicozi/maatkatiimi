#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import logging

from helius_token_scanner_bot import HeliusTokenScannerBot, DexInfoFetcher
from dex_fetchers import fetch_from_dexscreener, fetch_from_jupiter, fetch_from_solscan
from solana_rpc_helpers import rpc_get_tx


async def main():
    logging.basicConfig(level=logging.INFO)

    ws_url = os.getenv("HELIUS_WS_URL") or (
        f"wss://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY','')}"
    )
    programs = [
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # SPL Token program
    ]

    # Oikeat DEX hakijat
    fetcher = DexInfoFetcher(
        dexscreener=fetch_from_dexscreener,
        jupiter=fetch_from_jupiter,
        solscan=fetch_from_solscan,
    )

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

