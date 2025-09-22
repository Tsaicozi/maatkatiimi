import asyncio
import json
import logging
import contextlib

import pytest

from helius_token_scanner_bot import (
    HeliusTokenScannerBot,
    NewTokenEvent,
    DexInfoFetcher,
    DexInfo,
)


@pytest.mark.asyncio
async def test_consumer_start_logs_info(caplog):
    caplog.set_level(logging.INFO)

    # Dex fetcher joka ei koske verkkoon
    async def _pending(_mint: str) -> DexInfo:
        return DexInfo(status="pending", reason="no_providers")

    bot = HeliusTokenScannerBot(ws_url="wss://dummy", dex_fetcher=DexInfoFetcher(dexscreener=_pending))
    await bot.start()

    # INFO-loki kuluttajan startista
    assert any("_consume_queue käynnistyi" in m for _, _, m in caplog.record_tuples), "Kuluttajan start INFO-loki puuttuu"

    # Sammuta siististi
    await bot.stop()


@pytest.mark.asyncio
async def test_dex_reason_initialized_and_summary_logged(caplog):
    caplog.set_level(logging.INFO)

    # Fallback-ketju: DexScreener=error -> Jupiter=not_found -> Solscan=ok
    async def _dexscreener(_mint: str) -> DexInfo:
        raise RuntimeError("boom")

    async def _jupiter(_mint: str) -> DexInfo:
        return DexInfo(status="not_found", reason="no_pair")

    async def _solscan(_mint: str) -> DexInfo:
        return DexInfo(status="ok", dex_name="Solscan", pair_address="PAIR_ABC", reason="solscan_ok")

    fetcher = DexInfoFetcher(dexscreener=_dexscreener, jupiter=_jupiter, solscan=_solscan)
    bot = HeliusTokenScannerBot(ws_url="wss://dummy", dex_fetcher=fetcher)

    await bot.start()
    await bot.enqueue(NewTokenEvent(mint="MINT_XYZ"))
    await asyncio.sleep(0.05)
    await bot.stop()

    # Tarkista että summary-loki tuli ja dex_reason on olemassa
    summaries = []
    for rec in caplog.records:
        try:
            payload = json.loads(rec.getMessage())
            if payload.get("evt") == "summary":
                summaries.append(payload)
        except Exception:
            pass

    assert summaries, "Summary-loki puuttuu"
    s = summaries[-1]
    assert s.get("dex_status") == "ok"
    assert "dex_reason" in s and isinstance(s.get("dex_reason"), str)


@pytest.mark.asyncio
async def test_fallback_chain_pending_when_all_fail(caplog):
    caplog.set_level(logging.INFO)

    async def _fail(_mint: str) -> DexInfo:
        return DexInfo(status="error", reason="provider_error")

    fetcher = DexInfoFetcher(dexscreener=_fail, jupiter=_fail, solscan=_fail)
    bot = HeliusTokenScannerBot(ws_url="wss://dummy", dex_fetcher=fetcher)

    await bot.start()
    await bot.enqueue(NewTokenEvent(mint="MINT_FAIL"))
    await asyncio.sleep(0.05)
    await bot.stop()

    # Löytyy pending status summaryssa
    found = False
    for rec in caplog.records:
        with contextlib.suppress(Exception):
            payload = json.loads(rec.getMessage())
            if payload.get("evt") == "summary" and payload.get("dex_status") == "pending":
                found = True
                break
    assert found, "pending summary puuttuu all-fail -tilanteessa"

