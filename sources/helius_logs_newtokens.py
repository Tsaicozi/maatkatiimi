from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, Optional

import aiohttp
import websockets
from zoneinfo import ZoneInfo

from discovery_engine import TokenCandidate
from metrics import metrics

logger = logging.getLogger(__name__)


@dataclass
class MintCandidate:
    mint: str
    owner: str
    minted_raw: Decimal
    minted_ui: float
    decimals: Optional[int]
    initialize_seen: bool


class HeliusTransactionsNewTokensSource:
    """Helius transactionSubscribe source for real-time token creations."""

    _SYSTEM_ACCOUNTS = {
        "11111111111111111111111111111111",
        "ComputeBudget111111111111111111111111111111",
        "SysvarRent111111111111111111111111111111111",
        "SysvarC1ock11111111111111111111111111111111",
        "Sysvar1nstructions1111111111111111111111111",
        "SysvarRecentB1ockHashes11111111111111111111",
        "SysvarEpochSchedu1e111111111111111111111111",
        "SysvarStakeHistory1111111111111111111111111",
        "BPFLoaderUpgradeab1e11111111111111111111111",
        "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
        "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
        "Stake11111111111111111111111111111111111111",
        "Vote111111111111111111111111111111111111111",
    }

    def __init__(
        self,
        ws_url: str,
        programs: Iterable[str],
        *,
        seen_ttl: float = 3600.0,
        metadata_timeout: float = 10.0,
    ) -> None:
        self.ws_url = ws_url
        self.programs = list(programs or [])
        self._stop = asyncio.Event()
        self._seen: Dict[str, float] = {}
        self._seen_ttl = seen_ttl
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._metadata_timeout = metadata_timeout
        self._rpc_url = self._normalize_rpc_url(ws_url)

    async def run(self, queue: asyncio.Queue) -> None:
        logger.info("🦅 HeliusTransactionsNewTokensSource run() käynnistetty")

        while not self._stop.is_set():
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self._ws = ws
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=self._metadata_timeout)
                    ) as http_session:
                        await self._subscribe(ws)

                        while not self._stop.is_set():
                            raw_msg = await ws.recv()
                            try:
                                event = json.loads(raw_msg)
                            except json.JSONDecodeError as exc:
                                logger.warning("Helius WS JSON-virhe: %s", exc)
                                continue

                            if not self._is_transaction_notification(event):
                                continue

                            value = event["params"]["result"].get("value") or {}
                            signature = value.get("signature")
                            slot = value.get("slot")
                            block_time = value.get("blockTime")

                            for candidate in self._extract_candidates(value):
                                mint = candidate.mint
                                self._prune_seen()
                                if mint in self._seen:
                                    continue

                                metadata = await self._fetch_metadata(http_session, mint)
                                symbol, name, decimals = self._derive_metadata(candidate, metadata)

                                self._seen[mint] = time.time()

                                token = TokenCandidate(
                                    mint=mint,
                                    symbol=symbol,
                                    name=name,
                                    decimals=decimals if decimals is not None else (candidate.decimals or 9),
                                    first_seen=datetime.now(tz=ZoneInfo("Europe/Helsinki")),
                                    extra={
                                        "source": "helius_transactions",
                                        "signature": signature,
                                        "slot": slot,
                                        "block_time": block_time,
                                        "owner": candidate.owner,
                                        "minted_amount_raw": str(candidate.minted_raw),
                                        "minted_amount_ui": candidate.minted_ui,
                                        "metadata": metadata,
                                        "initialize_seen": candidate.initialize_seen,
                                    },
                                )

                                with contextlib.suppress(asyncio.QueueFull):
                                    if metrics:
                                        metrics.candidates_in.labels(source="helius_transactions").inc()
                                    queue.put_nowait(token)

                                logger.info(
                                    "🆕 Helius: Uusi token: %s... (symbol=%s, owner=%s)",
                                    mint[:8],
                                    symbol,
                                    candidate.owner[:8],
                                )

            except websockets.exceptions.ConnectionClosedOK:
                logger.info("Helius WS-yhteys suljettiin siististi")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Helius WS-virhe: %s – yritetään uudestaan 5s kuluttua", exc)
                await asyncio.sleep(5)

        logger.info("🛑 HeliusTransactionsNewTokensSource run() lopetettu")

    async def stop(self) -> None:
        self._stop.set()
        if self._ws:
            await self._ws.close()

    async def _subscribe(self, ws: websockets.WebSocketClientProtocol) -> None:
        if not self.programs:
            raise RuntimeError("Helius transaction source vaatii program-listan")

        for idx, program_id in enumerate(self.programs, start=1):
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": idx,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": [program_id]},
                    {"commitment": "confirmed"},
                ],
            }
            await ws.send(json.dumps(subscribe_msg))
            logger.info(
                "✅ Helius WS: logsSubscribe lähetetty: %s...",
                program_id[:8],
            )

    def _is_transaction_notification(self, event: dict) -> bool:
        if not isinstance(event, dict):
            return False
        if "params" not in event or "result" not in event.get("params", {}):
            return False
        result = event["params"]["result"]
        return isinstance(result, dict) and result.get("value")

    def _extract_candidates(self, value: dict) -> Iterable[MintCandidate]:
        if not isinstance(value, dict):
            return []

        # logsSubscribe palauttaa erilaisen datan kuin transactionSubscribe
        # Parsitaan mint-osoitteet logeista
        logs = value.get("logs", [])
        signature = value.get("signature", "")
        
        candidates: list[MintCandidate] = []
        
        # Etsitään initializeMint-logeja (yksinkertainen versio)
        for log in logs:
            if not isinstance(log, str):
                continue
            
            # Etsitään token-mint osoitteita logeista
            # Tämä on yksinkertaistettu versio - tuotannossa tarvittaisiin enemmän parsintaa
            if "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA invoke" in log:
                # Yksinkertainen token-tapahtuma havaittu
                # Passthrough-tilassa tulostetaan vain havainto
                if os.getenv("HELIUS_PASSTHROUGH"):
                    logger.info(f"[helius] mint=TOKEN_DETECTED signature={signature[:20]}...")
                
                # Luodaan dummy-kandidaatti testausta varten
                candidate = MintCandidate(
                    mint="DETECTED_FROM_LOGS",
                    owner="UNKNOWN",
                    minted_raw=Decimal(0),
                    minted_ui=Decimal(0),
                    decimals=None,
                    initialize_seen=True,
                )
                candidates.append(candidate)
                break
        
        return candidates

    def _collect_initialize_mints(self, message: dict, meta: dict) -> Dict[str, Dict[str, Optional[int]]]:
        found: Dict[str, Dict[str, Optional[int]]] = {}

        for inst in self._iter_instructions(message, meta):
            parsed = inst.get("parsed") if isinstance(inst, dict) else None
            if not isinstance(parsed, dict):
                continue
            if parsed.get("type") != "initializeMint":
                continue
            info = parsed.get("info") or {}
            mint = info.get("mint") or self._first_account(inst)
            if not mint or not self._is_valid_solana_address(mint):
                continue
            try:
                decimals = int(info.get("decimals")) if info.get("decimals") is not None else None
            except (TypeError, ValueError):
                decimals = None
            found[mint] = {
                "decimals": decimals,
                "authority": info.get("mintAuthority"),
                "freezeAuthority": info.get("freezeAuthority"),
            }
        return found

    def _iter_instructions(self, message: dict, meta: dict):
        instructions = message.get("instructions") if isinstance(message, dict) else None
        if isinstance(instructions, list):
            for inst in instructions:
                yield inst

        inner = meta.get("innerInstructions") if isinstance(meta, dict) else None
        if isinstance(inner, list):
            for block in inner:
                ins = block.get("instructions") if isinstance(block, dict) else None
                if isinstance(ins, list):
                    for inst in ins:
                        yield inst

    def _first_account(self, inst: dict) -> Optional[str]:
        accounts = inst.get("accounts") if isinstance(inst, dict) else None
        if isinstance(accounts, list) and accounts:
            first = accounts[0]
            if isinstance(first, dict):
                return first.get("pubkey")
            if isinstance(first, str):
                return first
        return None

    def _mint_owner_from_balance(self, entry: dict) -> tuple[Optional[str], Optional[str]]:
        if not isinstance(entry, dict):
            return None, None
        mint = entry.get("mint")
        owner = entry.get("owner") or entry.get("account") or entry.get("pubkey")
        if owner and isinstance(owner, dict):
            owner = owner.get("pubkey")
        return mint, owner

    def _parse_amount(self, token_amount: Optional[dict]) -> Decimal:
        if not isinstance(token_amount, dict):
            return Decimal(0)
        amount = token_amount.get("amount")
        if amount is not None:
            try:
                return Decimal(str(amount))
            except InvalidOperation:
                pass
        ui_amount = token_amount.get("uiAmountString") or token_amount.get("uiAmount")
        decimals = token_amount.get("decimals")
        if ui_amount is not None and decimals is not None:
            try:
                return Decimal(str(ui_amount)) * (Decimal(10) ** int(decimals))
            except (InvalidOperation, ValueError):
                return Decimal(0)
        return Decimal(0)

    def _to_ui(self, raw: Decimal, decimals: Optional[int]) -> float:
        try:
            if decimals is None:
                return float(raw)
            scale = Decimal(10) ** int(decimals)
            return float(raw / scale)
        except (InvalidOperation, ValueError, OverflowError):
            return float(raw)

    def _is_valid_solana_address(self, address: str) -> bool:
        if not isinstance(address, str):
            return False
        if len(address) < 32 or len(address) > 44:
            return False
        import base58

        try:
            decoded = base58.b58decode(address)
            return len(decoded) == 32
        except Exception:
            return False

    def _normalize_rpc_url(self, ws_url: str) -> Optional[str]:
        if not isinstance(ws_url, str):
            return None
        if ws_url.startswith("wss://"):
            return "https://" + ws_url[len("wss://") :]
        if ws_url.startswith("ws://"):
            return "http://" + ws_url[len("ws://") :]
        if ws_url.startswith("http://") or ws_url.startswith("https://"):
            return ws_url
        return None

    async def _fetch_metadata(self, session: aiohttp.ClientSession, mint: str) -> dict:
        if not self._rpc_url or not mint:
            return {}
        payload = {
            "jsonrpc": "2.0",
            "id": "get-asset",
            "method": "getAsset",
            "params": {
                "id": mint,
                "displayOptions": {"showFungible": True},
            },
        }
        try:
            async with session.post(self._rpc_url, json=payload) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.json()
        except Exception as exc:
            logger.debug("Helius metadata fetch failed for %s: %s", mint, exc)
            return {}

        return data.get("result") or {}

    def _derive_metadata(self, candidate: MintCandidate, metadata: dict) -> tuple[str, str, Optional[int]]:
        mint = candidate.mint
        symbol = None
        name = None
        decimals = candidate.decimals

        if isinstance(metadata, dict):
            token_info = metadata.get("tokenInfo") or metadata.get("token_info") or {}
            content = metadata.get("content") or {}
            meta_inner = content.get("metadata") or {}

            symbol = (
                token_info.get("symbol")
                or meta_inner.get("symbol")
                or meta_inner.get("symbolFromName")
            )
            name = token_info.get("name") or meta_inner.get("name")
            try:
                decimals_meta = token_info.get("decimals") or metadata.get("decimals")
                if decimals_meta is not None:
                    decimals = int(decimals_meta)
            except (TypeError, ValueError):
                pass

        if not symbol:
            symbol = f"TOKEN_{mint[:8]}"
        if not name:
            name = symbol

        return symbol, name, decimals

    def _prune_seen(self) -> None:
        cutoff = time.time() - self._seen_ttl
        for mint in list(self._seen.keys()):
            if self._seen[mint] < cutoff:
                self._seen.pop(mint, None)


# Backwards compatibility alias
HeliusLogsNewTokensSource = HeliusTransactionsNewTokensSource
