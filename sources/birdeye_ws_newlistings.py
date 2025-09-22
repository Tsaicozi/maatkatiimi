# sources/birdeye_ws_newlistings.py
from __future__ import annotations
import asyncio, json, logging, time, contextlib, datetime
import websockets
from discovery_engine import TokenCandidate
from metrics import metrics

logger = logging.getLogger(__name__)

class BirdeyeWSNewListingsSource:
    """
    Birdeye WebSocket source for Solana new token listings.
    Connects to wss://public-api.birdeye.so/socket and subscribes to new listings.
    """
    def __init__(self, ws_url: str = "wss://public-api.birdeye.so/socket", api_key: str | None = None):
        self.ws_url = ws_url
        self.api_key = api_key
        self._stop = asyncio.Event()
        self._seen = set()
        self._ws = None

    def _get_mint(self, it):
        """Extract mint address from Birdeye data"""
        return it.get("address") or it.get("mint") or it.get("tokenAddress")

    def _get_pool(self, it):
        """Extract pool address from Birdeye data"""
        return it.get("poolAddress") or it.get("pool") or None

    def _get_first_ts(self, it):
        """Extract first timestamp from Birdeye data"""
        # Birdeye typically uses Unix timestamps
        v = it.get("createdAt") or it.get("firstTradeAt") or it.get("timestamp")
        if v is None: 
            return None
        try:
            fv = float(v)
            # Convert milliseconds to seconds if needed
            if fv > 1e12: 
                fv = fv / 1000.0
            return fv
        except Exception:
            try:
                # Try ISO8601 format
                dt = datetime.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
                return dt.timestamp()
            except Exception:
                return None

    async def run(self, queue):
        logger.info("🐦 BirdeyeWSNewListingsSource run() käynnistetty")
        
        while not self._stop.is_set():
            try:
                # Try simple connection without headers (compatibility issue with extra_headers)
                async with websockets.connect(self.ws_url) as ws:
                    self._ws = ws
                    
                    # Subscribe to new pairs (Birdeye's equivalent of new listings)
                    subscribe_msg = {
                        "type": "subscribe",
                        "channel": "newPairs",
                        "params": {
                            "chain": "solana"
                        }
                    }
                    
                    # Add API key to subscription message if provided
                    if self.api_key:
                        subscribe_msg["apiKey"] = self.api_key
                    
                    await ws.send(json.dumps(subscribe_msg))
                    logger.info("✅ Birdeye WS: Tilaus 'newPairs' lähetetty" + (f" (API key: {self.api_key[:8]}...)" if self.api_key else " (ei API key)"))

                    while not self._stop.is_set():
                        message = await ws.recv()
                        try:
                            event = json.loads(message)
                            
                            # Handle different Birdeye message types
                            if event.get("type") == "newPairs" and event.get("data"):
                                data = event["data"]
                                if not isinstance(data, dict):
                                    continue

                                mint = self._get_mint(data)
                                if not mint or mint in self._seen:
                                    continue
                                self._seen.add(mint)

                                first_ts = self._get_first_ts(data)
                                
                                # Extract liquidity and holder data if available
                                liq = data.get("liquidity") or data.get("liquidityUsd") or 0.0
                                top10 = data.get("top10Share") or data.get("topHoldersShare") or None
                                
                                # Extract symbol and name
                                symbol = data.get("symbol") or data.get("ticker")
                                name = data.get("name") or data.get("tokenName")

                                from zoneinfo import ZoneInfo
                                cand = TokenCandidate(
                                    mint=mint,
                                    symbol=symbol,
                                    name=name,
                                    first_seen=datetime.datetime.fromtimestamp(first_ts, tz=ZoneInfo("Europe/Helsinki")) if first_ts else datetime.datetime.now(tz=ZoneInfo("Europe/Helsinki")),
                                    extra={
                                        "first_trade_ts": first_ts,
                                        "source": "birdeye_ws",
                                        "liq_hint": liq,
                                        "top10_hint": top10,
                                        "pool_address": self._get_pool(data)
                                    },
                                )

                                with contextlib.suppress(asyncio.QueueFull):
                                    if metrics:
                                        metrics.candidates_in.labels(source="birdeye_ws").inc()
                                    queue.put_nowait(cand)
                                    
                        except json.JSONDecodeError as e:
                            logger.warning(f"Birdeye WS: JSON parse error: {e}")
                            continue
                        except Exception as e:
                            logger.warning(f"Birdeye WS: Message processing error: {e}")
                            continue
                            
            except websockets.exceptions.ConnectionClosedOK:
                logger.info("Birdeye WS-yhteys suljettu siististi.")
            except Exception as e:
                logger.error(f"Birdeye WS-virhe: {e}. Yritetään uudelleen 5s kuluttua.")
                await asyncio.sleep(5)
                    
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Birdeye WS-virhe: {e}. Yritetään uudelleen 5s kuluttua.")
                await asyncio.sleep(5)
                
        logger.info("🛑 BirdeyeWSNewListingsSource run() lopetettu")

    async def stop(self):
        self._stop.set()
        if self._ws:
            await self._ws.close()
