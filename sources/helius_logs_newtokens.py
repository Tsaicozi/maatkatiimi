# sources/helius_logs_newtokens.py
from __future__ import annotations
import asyncio, json, logging, contextlib, websockets, time
from datetime import datetime
from zoneinfo import ZoneInfo
from discovery_engine import TokenCandidate
from metrics import metrics

logger = logging.getLogger(__name__)

class HeliusLogsNewTokensSource:
    """
    Helius WebSocket source for real-time token creation monitoring.
    Connects to Helius WebSocket and subscribes to program logs.
    """
    def __init__(self, ws_url: str, programs: list[str]):
        self.ws_url = ws_url
        self.programs = programs
        self._stop = asyncio.Event()
        self._seen = set()
        self._ws = None

    def _extract_mint_from_logs(self, logs: list[str]) -> str | None:
        """Extract mint address from program logs"""
        for log in logs:
            # Look for InitializeMint instruction logs
            if "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA invoke" in log:
                # Extract mint address from the log
                # Format: "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA invoke [1]"
                # The mint address is typically in the accounts list
                parts = log.split()
                if len(parts) > 4:
                    # The mint address is usually the first account after invoke
                    for i, part in enumerate(parts):
                        if part == "invoke" and i + 1 < len(parts):
                            # Skip the [1] part and get the next account
                            if i + 2 < len(parts):
                                return parts[i + 2]
        return None

    def _extract_symbol_from_logs(self, logs: list[str]) -> str | None:
        """Extract token symbol from program logs if available"""
        for log in logs:
            # Look for metadata or symbol information
            if "symbol" in log.lower():
                # Try to extract symbol from log
                import re
                match = re.search(r'symbol["\']?\s*[:=]\s*["\']?([A-Za-z0-9]+)', log, re.IGNORECASE)
                if match:
                    return match.group(1)
        return None

    async def run(self, queue):
        logger.info("🦅 HeliusLogsNewTokensSource run() käynnistetty")
        
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self._ws = ws
                    
                    # Subscribe to program logs
                    for program_id in self.programs:
                        subscribe_msg = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "logsSubscribe",
                            "params": [
                                {
                                    "mentions": [program_id]
                                },
                                {
                                    "commitment": "confirmed"
                                }
                            ]
                        }
                        await ws.send(json.dumps(subscribe_msg))
                        logger.info(f"✅ Helius WS: Tilaus program logs lähetetty: {program_id[:8]}...")
                    
                    while not self._stop.is_set():
                        message = await ws.recv()
                        try:
                            event = json.loads(message)
                            
                            # Handle subscription confirmation
                            if "result" in event and isinstance(event["result"], str):
                                logger.info(f"✅ Helius WS: Tilaus vahvistettu: {event['result'][:8]}...")
                                continue
                            
                            # Handle log notifications
                            if "params" in event and "result" in event["params"]:
                                log_data = event["params"]["result"]
                                if "value" in log_data:
                                    logs = log_data["value"]["logs"]
                                    signature = log_data["value"].get("signature", "")
                                    
                                    # Extract mint address from logs
                                    mint = self._extract_mint_from_logs(logs)
                                    if mint and mint not in self._seen:
                                        self._seen.add(mint)
                                        
                                        # Extract symbol if available
                                        symbol = self._extract_symbol_from_logs(logs) or f"TOKEN_{mint[:8]}"
                                        
                                        # Create TokenCandidate
                                        cand = TokenCandidate(
                                            mint=mint,
                                            symbol=symbol,
                                            name=f"New Token {symbol}",
                                            first_seen=datetime.now(tz=ZoneInfo("Europe/Helsinki")),
                                            extra={
                                                "first_trade_ts": time.time(),
                                                "source": "helius_logs",
                                                "signature": signature,
                                                "program_id": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                                            },
                                        )
                                        
                                        with contextlib.suppress(asyncio.QueueFull):
                                            if metrics:
                                                metrics.candidates_in.labels(source="helius_logs").inc()
                                            queue.put_nowait(cand)
                                            
                                        logger.info(f"🆕 Helius: Uusi token löydetty: {mint[:8]}... ({symbol})")

                        except json.JSONDecodeError as e:
                            logger.warning(f"Helius WS: JSON parse error: {e}")
                            continue
                        except Exception as e:
                            logger.warning(f"Helius WS: Message processing error: {e}")
                            continue

            except websockets.exceptions.ConnectionClosedOK:
                logger.info("Helius WS-yhteys suljettu siististi.")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Helius WS-virhe: {e}. Yritetään uudelleen 5s kuluttua.")
                await asyncio.sleep(5)

        logger.info("🛑 HeliusLogsNewTokensSource run() lopetettu")

    async def stop(self):
        self._stop.set()
        if self._ws:
            await self._ws.close()
