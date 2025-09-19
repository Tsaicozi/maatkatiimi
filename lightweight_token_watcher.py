#!/usr/bin/env python3
"""
Kevyt CoinGecko-pohjainen Solana-token watcher.
- Lukee .env:stä COINGECKO_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
- Pollaa CoinGecko Pro API:sta Solana-ecosystem -tokenit
- Vertaa aiemmin nähtyihin tokeneihin (.runtime/lightwatch_seen.json)
- Ilmoittaa uudet tokenit Telegramiin
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import aiohttp
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("lightwatch")

RUNTIME_DIR = Path(".runtime")
SEEN_PATH = RUNTIME_DIR / "lightwatch_seen.json"
COINGECKO_ENDPOINT = (
    "https://pro-api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd&category=solana-ecosystem&order=market_cap_desc"
    "&per_page=100&page=1&sparkline=false&price_change_percentage=1h,24h"
)


class LightweightTokenWatcher:
    def __init__(self, *, poll_interval: float = 60.0) -> None:
        load_dotenv()
        self.poll_interval = poll_interval
        self.coingecko_key = os.getenv("COINGECKO_API_KEY")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.session: aiohttp.ClientSession | None = None
        if not self.coingecko_key:
            raise RuntimeError("COINGECKO_API_KEY puuttuu ympäristöstä")
        if not (self.telegram_token and self.telegram_chat_id):
            raise RuntimeError("Telegram asetukset puuttuvat (.env)" )

    async def __aenter__(self) -> "LightweightTokenWatcher":
        self.session = aiohttp.ClientSession()
        RUNTIME_DIR.mkdir(exist_ok=True)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self.session:
            await self.session.close()

    async def fetch_tokens(self) -> list[dict[str, Any]]:
        assert self.session is not None
        headers = {
            "Accept": "application/json",
            "x-cg-pro-api-key": self.coingecko_key,
            "User-Agent": "lightwatch/1.0",
        }
        async with self.session.get(COINGECKO_ENDPOINT, headers=headers, timeout=15) as resp:
            if resp.status == 200:
                return await resp.json()
            text = await resp.text()
            raise RuntimeError(f"CoinGecko status {resp.status}: {text[:120]}")

    def load_seen(self) -> set[str]:
        if SEEN_PATH.exists():
            try:
                return set(json.loads(SEEN_PATH.read_text(encoding="utf-8")))
            except Exception as exc:
                logger.warning("Seen-listan luku epäonnistui: %s", exc)
        return set()

    def save_seen(self, seen: set[str]) -> None:
        SEEN_PATH.write_text(json.dumps(sorted(seen)), encoding="utf-8")

    async def send_telegram(self, text: str) -> None:
        assert self.session is not None
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        async with self.session.post(url, json=payload, timeout=10) as resp:
            if resp.status != 200:
                detail = await resp.text()
                raise RuntimeError(f"Telegram status {resp.status}: {detail[:120]}")

    def format_token(self, data: dict[str, Any]) -> str:
        name = data.get("name") or "?"
        symbol = data.get("symbol") or "?"
        price = data.get("current_price") or 0
        change_1h = data.get("price_change_percentage_1h_in_currency") or 0
        change_24h = data.get("price_change_percentage_24h_in_currency") or 0
        market_cap = data.get("market_cap") or 0
        supply = data.get("circulating_supply") or 0
        url = data.get("id")
        link = f"https://www.coingecko.com/coins/{url}" if url else ""
        return (
            f"*{name}* (`{symbol.upper()}`)\n"
            f"Hinta: ${price:.4f}\n"
            f"1h: {change_1h:+.2f}% | 24h: {change_24h:+.2f}%\n"
            f"Markkina-arvo: ${market_cap:,.0f}\n"
            f"Liikkeessä: {supply:,.0f}\n"
            f"[CoinGecko]({link})"
        )

    async def process(self) -> None:
        seen = self.load_seen()
        tokens = await self.fetch_tokens()
        new_tokens: list[dict[str, Any]] = []
        for entry in tokens:
            token_id = entry.get("id")
            if not token_id:
                continue
            if token_id not in seen:
                new_tokens.append(entry)
                seen.add(token_id)
        if not new_tokens:
            logger.info("Ei uusia tokeneita")
        else:
            logger.info("%d uutta tokenia", len(new_tokens))
            batches = [new_tokens[i:i + 5] for i in range(0, len(new_tokens), 5)]
            for batch in batches:
                body = "\n\n".join(self.format_token(it) for it in batch)
                text = "🚀 *Uusia Solana-ecosystem tokeneita*\n\n" + body
                await self.send_telegram(text)
        self.save_seen(seen)

    async def run_forever(self) -> None:
        async with self:
            while True:
                try:
                    await self.process()
                except Exception as exc:
                    logger.error("Watcher virhe: %s", exc)
                await asyncio.sleep(self.poll_interval)


async def main() -> None:
    interval = float(os.getenv("LIGHTWATCH_INTERVAL", "120"))
    watcher = LightweightTokenWatcher(poll_interval=interval)
    await watcher.run_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Watcher pysäytettiin")
