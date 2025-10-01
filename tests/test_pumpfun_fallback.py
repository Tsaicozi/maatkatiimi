import json
from types import SimpleNamespace

import pytest

from helius_token_scanner_bot import HeliusTokenScannerBot, ScannerSettings


def _make_settings(**overrides) -> ScannerSettings:
    base = dict(
        ws_url="wss://example",
        programs=["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"],
        telegram_enabled=False,
        telegram_cooldown=0.0,
        fetch_transaction=False,
        transaction_rpc_url="https://example",
        fetch_asset=False,
        fetch_accounts=False,
        fetch_signatures=False,
        rpc_rate_limit=1,
        search_assets=False,
        search_limit=10,
        search_poll=10.0,
        fetch_risk=False,
        goplus_bearer=None,
        allowed_decimals=(6, 9),
        min_supply=0.0,
        max_top_share=0.90,
        jsonl_path=None,
        dexscreener_enabled=True,
        dexscreener_min_liquidity=0.0,
        dexscreener_min_volume=0.0,
        dexscreener_min_price=0.0,
        dexscreener_max_price=0.0,
        dexscreener_reject_path=None,
        dexscreener_whitelist=(),
        score_threshold=0.0,
        birdeye_enabled=False,
        birdeye_min_liquidity=0.0,
        birdeye_min_volume=0.0,
        birdeye_min_price=0.0,
        birdeye_min_holders=0,
        birdeye_api_key=None,
    )
    base.update(overrides)
    return ScannerSettings(**base)


class DummyResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    async def json(self):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummySession:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    def get(self, url, timeout=None):
        if url in self.payloads:
            self.calls.append(url)
            return DummyResponse(self.payloads[url])
        return DummyResponse({}, status=404)

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_pumpfun_fallback(monkeypatch):
    payload = {
        "price": 0.001,
        "volume24h": 1500,
        "liquidity": 2500,
        "fdv": 100000,
        "marketCap": 90000,
        "website": "https://pump.fun/token",
    }
    session = DummySession({"https://frontend-api.pump.fun/coins/MINT": payload})

    settings = _make_settings()
    bot = HeliusTokenScannerBot(settings)
    bot._http_session = session

    metrics = await bot._fallback_market_metrics("MINT")
    assert metrics is not None
    assert metrics["price"] == pytest.approx(0.001)
    assert metrics["volume_24h"] == pytest.approx(1500)
    assert metrics["liquidity"] == pytest.approx(2500)
    assert metrics["fdv"] == pytest.approx(100000)
    assert metrics["util"] == pytest.approx(1500 / 2500)
    assert metrics["source"] == "fallback"
