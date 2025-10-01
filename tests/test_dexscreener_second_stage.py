import asyncio
from typing import Dict, List

import pytest

from dexscreener_second_stage import (
    FilterConfig,
    extract_metrics,
    filter_tokens,
    token_passes_filter,
)


class DummyClient:
    def __init__(self, responses: Dict[str, List[Dict]]):
        self.responses = responses
        self.calls: List[str] = []

    async def fetch_pairs(self, mint: str):
        self.calls.append(mint)
        return self.responses.get(mint, [])


def test_extract_metrics_selects_highest_liquidity_pair():
    pairs = [
        {
            "dexId": "dexA",
            "priceUsd": "0.5",
            "volume": {"h24": 1000},
            "liquidity": {"usd": 2000},
        },
        {
            "dexId": "dexB",
            "priceUsd": "0.6",
            "volume": {"h24": 4000},
            "liquidity": {"usd": 5000},
        },
    ]
    metrics, best = extract_metrics(pairs)
    assert metrics["price"] == pytest.approx(0.6)
    assert metrics["volume_24h"] == pytest.approx(4000)
    assert metrics["liquidity"] == pytest.approx(5000)
    assert best and best["dexId"] == "dexB"


def test_token_passes_filter_thresholds():
    cfg = FilterConfig(min_liquidity=1000, min_volume=500, min_price=0.1, max_price=2.0)
    metrics = {"price": 1.0, "volume_24h": 700, "liquidity": 2000}
    ok, reason = token_passes_filter(metrics, cfg)
    assert ok is True
    assert reason == "ok"

    metrics_bad = {"price": 0.05, "volume_24h": 700, "liquidity": 2000}
    ok, reason = token_passes_filter(metrics_bad, cfg)
    assert ok is False
    assert reason == "price_low"


@pytest.mark.asyncio
async def test_filter_tokens_enriches_results():
    cfg = FilterConfig(min_liquidity=1000, min_volume=500, min_price=0.1, max_price=2.0)
    tokens = [{"mint": "Mint111", "symbol": "AAA"}, {"mint": "Mint222", "symbol": "BBB"}]
    responses = {
        "Mint111": [
            {
                "priceUsd": 0.8,
                "volume": {"h24": 1500},
                "liquidity": {"usd": 2500},
                "pairAddress": "PAIR111",
                "dexId": "raydium",
                "url": "https://dexscreener.com/solana/pair111",
                "baseToken": {"symbol": "AAA"},
                "quoteToken": {"symbol": "USDC"},
            }
        ],
        "Mint222": [
            {
                "priceUsd": 0.05,
                "volume": {"h24": 200},
                "liquidity": {"usd": 900},
                "pairAddress": "PAIR222",
            }
        ],
    }
    client = DummyClient(responses)

    accepted = await filter_tokens(client, tokens, cfg, concurrency=2)
    assert len(accepted) == 1
    enriched = accepted[0]
    assert enriched["mint"] == "Mint111"
    ds = enriched["dexscreener"]
    assert ds["price"] == pytest.approx(0.8)
    assert ds["volume_24h"] == pytest.approx(1500)
    assert ds["liquidity"] == pytest.approx(2500)
    assert ds["pair_address"] == "PAIR111"
    assert ds["filter_reason"] == "ok"
    assert client.calls == ["Mint111", "Mint222"]

