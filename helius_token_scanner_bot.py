from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

# Valinnaiset importit vain runtimea varten; testit eivät käytä WS-tuotantoa
try:
    import websockets  # type: ignore
except Exception:  # pragma: no cover
    websockets = None  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class NewTokenEvent:
    mint: str
    symbol: str = ""
    name: str = ""
    signature: str | None = None
    source: str = "helius_logs"


@dataclass
class DexInfo:
    status: str  # "ok" | "pending" | "error" | "not_found"
    dex_name: str | None = None
    pair_address: str | None = None
    reason: str = ""


class DexInfoFetcher:
    """
    Fallback-ketju DEX-infon hakemiseksi. Järjestys: DexScreener -> Jupiter -> Solscan.
    Tarjoajat injektoidaan, jotta testaus onnistuu ilman verkkoa.
    """

    def __init__(
        self,
        dexscreener: Callable[[str], Awaitable[DexInfo]] | None = None,
        jupiter: Callable[[str], Awaitable[DexInfo]] | None = None,
        solscan: Callable[[str], Awaitable[DexInfo]] | None = None,
    ) -> None:
        async def _na(mint: str) -> DexInfo:
            return DexInfo(status="not_found", reason="provider_not_configured")

        self._dexscreener = dexscreener or _na
        self._jupiter = jupiter or _na
        self._solscan = solscan or _na

    async def fetch(self, mint: str, *, timeout_sec: float = 5.0) -> DexInfo:
        reason_chain: list[str] = []

        async def _try(name: str, fn: Callable[[str], Awaitable[DexInfo]]) -> Optional[DexInfo]:
            try:
                return await asyncio.wait_for(fn(mint), timeout=timeout_sec)
            except asyncio.TimeoutError:
                reason_chain.append(f"{name}=timeout")
                return None
            except Exception as e:  # pragma: no cover - kattava fallback
                reason_chain.append(f"{name}=error:{e}")
                return None

        # 1) DexScreener
        r = await _try("dexscreener", self._dexscreener)
        if r and r.status == "ok":
            r.reason = r.reason or "dexscreener_ok"
            return r
        if r and r.reason:
            reason_chain.append(f"dexscreener={r.reason}")

        # 2) Jupiter
        r = await _try("jupiter", self._jupiter)
        if r and r.status == "ok":
            r.reason = r.reason or "jupiter_ok"
            return r
        if r and r.reason:
            reason_chain.append(f"jupiter={r.reason}")

        # 3) Solscan
        r = await _try("solscan", self._solscan)
        if r and r.status == "ok":
            r.reason = r.reason or "solscan_ok"
            return r
        if r and r.reason:
            reason_chain.append(f"solscan={r.reason}")

        return DexInfo(status="pending", dex_name=None, pair_address=None, reason=";".join(reason_chain) or "all_failed")


class HeliusTokenScannerBot:
    """
    Helius WS -pohjainen uuden tokenin skanneri (producer) + kuluttaja-queue (consumer).

    - INFO-tason kuluttaja-start -loki
    - `dex_reason` on aina alustettu, jotta summary-lokitus ei koskaan kaadu
    - Fallback: DexScreener -> Jupiter -> Solscan
    - Siisti sammutus (cancel, queue sentinel)
    """

    def __init__(
        self,
        *,
        ws_url: str,
        programs: list[str] | None = None,
        dex_fetcher: DexInfoFetcher | None = None,
        queue_maxsize: int = 1000,
    ) -> None:
        self.ws_url = ws_url
        self.programs = programs or ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"]
        self.dex_fetcher = dex_fetcher or DexInfoFetcher()
        self._stop = asyncio.Event()
        self._queue: asyncio.Queue[NewTokenEvent | object] = asyncio.Queue(maxsize=queue_maxsize)
        self._producer_task: asyncio.Task | None = None
        self._consumer_task: asyncio.Task | None = None
        self._sentinel: object = object()

    # --- Public API ---
    async def start(self) -> None:
        if self._producer_task or self._consumer_task:
            return
        # Kuluttaja start INFO-tasolla – korjaus
        self._consumer_task = asyncio.create_task(self._consume_queue(), name="helius_consumer")
        logger.info("📥 _consume_queue käynnistyi")
        # Tuottaja voidaan käynnistää myöhemmin testeissä; jos WS:ää ei ole, ohita
        if websockets and hasattr(websockets, "connect"):
            self._producer_task = asyncio.create_task(self._producer_loop(), name="helius_producer")

    async def stop(self) -> None:
        if self._stop.is_set():
            return
        self._stop.set()
        # herätä kuluttaja
        with contextlib.suppress(asyncio.QueueFull):
            self._queue.put_nowait(self._sentinel)
        # peruuta tuottaja
        if self._producer_task and not self._producer_task.done():
            self._producer_task.cancel()
        # odota tehtävät
        await asyncio.gather(
            *[t for t in (self._producer_task, self._consumer_task) if t],
            return_exceptions=True,
        )

    # Testiystävällinen injektointi
    async def enqueue(self, event: NewTokenEvent) -> None:
        await self._queue.put(event)

    # --- Internal ---
    async def _producer_loop(self) -> None:  # pragma: no cover - tuotantopolku
        backoff = 1.0
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.ws_url) as ws:  # type: ignore
                    # Tilaa program-logs mainituille ohjelmille
                    for program_id in self.programs:
                        sub = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "logsSubscribe",
                            "params": [{"mentions": [program_id]}, {"commitment": "confirmed"}],
                        }
                        await ws.send(json.dumps(sub))
                        logger.info("✅ Helius WS: tilaus lähetetty: %s", program_id[:8] + "…")

                    backoff = 1.0  # reset backoff kun yhteys auki
                    while not self._stop.is_set():
                        msg = await ws.recv()
                        data = json.loads(msg)
                        params = data.get("params", {})
                        value = (params.get("result") or {}).get("value") if isinstance(params, dict) else None
                        if not value:
                            continue
                        logs = value.get("logs") or []
                        sig = value.get("signature")
                        mint = self._extract_mint_from_logs(logs)
                        if not mint:
                            continue
                        ev = NewTokenEvent(mint=mint, symbol=f"TOKEN_{mint[:6]}", name=f"New Token {mint[:4]}", signature=sig)
                        with contextlib.suppress(asyncio.QueueFull):
                            self._queue.put_nowait(ev)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("Helius producer error: %s", e)
                await asyncio.sleep(min(30.0, backoff))
                backoff = min(30.0, backoff * 2.0)

    async def _consume_queue(self) -> None:
        while not self._stop.is_set():
            item = await self._queue.get()
            if item is self._sentinel:
                break
            if not isinstance(item, NewTokenEvent):
                continue

            dex_status = "pending"
            dex_reason = "unknown"  # turvallinen alustaminen – korjaus
            dex_name: str | None = None
            pair: str | None = None
            try:
                info = await self.dex_fetcher.fetch(item.mint)
                dex_status = info.status or "pending"
                dex_reason = info.reason or ""
                dex_name = info.dex_name
                pair = info.pair_address
            except Exception as e:
                dex_status = "error"
                dex_reason = f"fetch_failed:{e}"

            # Summary-loki ei kaadu vaikka reason olisi tyhjä
            summary = {
                "evt": "summary",
                "mint": item.mint,
                "symbol": item.symbol,
                "dex_status": dex_status,
                "dex_reason": dex_reason or "",
                "dex": dex_name or "",
                "pair": pair or "",
                "source": item.source,
            }
            logger.info(json.dumps(summary, ensure_ascii=False))

    @staticmethod
    def _extract_mint_from_logs(logs: list[str]) -> str | None:  # pragma: no cover - yksinkertainen stub
        # Kevyt heuristiikka; oikeassa elämässä parsitaan account-lista
        for line in logs or []:
            parts = line.split()
            for p in parts:
                if len(p) >= 32 and p.isalnum():
                    return p
        return None


# Pieni smoke-ajuri manuaalisesti
async def _smoke() -> None:  # pragma: no cover
    logging.basicConfig(level=logging.INFO)

    async def _fake_ok(_mint: str) -> DexInfo:
        return DexInfo(status="ok", dex_name="DexScreener", pair_address="PAIR123", reason="dexscreener_ok")

    bot = HeliusTokenScannerBot(ws_url="wss://example", dex_fetcher=DexInfoFetcher(dexscreener=_fake_ok))
    await bot.start()
    await bot.enqueue(NewTokenEvent(mint="MINT1234567890"))
    await asyncio.sleep(0.05)
    await bot.stop()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(_smoke())

