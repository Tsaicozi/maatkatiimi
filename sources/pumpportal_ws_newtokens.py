# sources/pumpportal_ws_newtokens.py
from __future__ import annotations
import asyncio, json, logging, contextlib, websockets, time
from datetime import datetime
from zoneinfo import ZoneInfo
from discovery_engine import TokenCandidate
from metrics import metrics
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

class PumpPortalWSNewTokensSource:
    def __init__(
        self,
        *,
        on_new_token: Optional[Callable[[TokenCandidate, dict], Awaitable[None]]] = None,
        on_trade: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        self._stop = asyncio.Event()
        self._ws = None
        self._trade_stats = {}  # mint -> {"buys":int,"sells":int,"unique_buyers":set(),"first_ts":float,"last_ts":float}
        self._subscribed_mints = set()  # Mintit joille on jo tilattu trade-seuranta
        self._debug_counter = 0
        self._on_new_token = on_new_token
        self._on_trade = on_trade

    async def run(self, queue):
        logger.info("🎯 PumpPortalWSNewTokensSource run() käynnistetty")
        try:
            async with websockets.connect("wss://pumpportal.fun/api/data") as ws:
                self._ws = ws
                await ws.send(json.dumps({"method":"subscribeNewToken"}))
                logger.info("✅ PumpPortal WS: Tilaus 'subscribeNewToken' lähetetty")
                
                while not self._stop.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        try:
                            ev = json.loads(raw)
                            
                            # Tarkista onko new-token vai trade-event
                            if ev.get("method") == "subscribeNewToken" or "mint" in ev:
                                await self._handle_new_token_event(ev, queue)
                            elif ev.get("method") == "subscribeTokenTrade" or "trader" in ev:
                                await self._handle_trade_event(ev, queue)
                                
                        except Exception as e:
                            logger.warning(f"PumpPortal WS event error: {e}")
                    except asyncio.TimeoutError:
                        if self._stop.is_set():
                            break
                        continue
                    except asyncio.CancelledError:
                        with contextlib.suppress(Exception):
                            await ws.close()
                        raise
                        continue
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"PumpPortal WS virhe: {e}")
            await asyncio.sleep(1.0)
        logger.info("🛑 PumpPortalWSNewTokensSource run() lopetettu")

    async def _handle_new_token_event(self, ev, queue):
        """Käsittele new-token event ja aloita trade-seuranta"""
        d = ev.get("data") or ev
        mint = d.get("mint") or d.get("tokenAddress") or d.get("mintAddress")
        if not mint: 
            return
            
        created = d.get("createdAt") or d.get("firstTradeAt")
        try:
            ts = float(created); 
            if ts and ts > 1e12: ts = ts/1000.0
        except Exception:
            ts = time.time()
        
        # Convert timestamp to datetime
        first_seen_dt = datetime.fromtimestamp(ts, tz=ZoneInfo("Europe/Helsinki"))
        
        # Alusta trade-tilastot
        if mint not in self._trade_stats:
            self._trade_stats[mint] = {
                "buys": 0,
                "sells": 0, 
                "unique_buyers": set(),
                "first_ts": ts,
                "last_ts": ts
            }
        
        cand = TokenCandidate(
            mint=mint,
            symbol=d.get("symbol") or d.get("ticker") or (mint[:8] + "…" + mint[-4:] if len(mint) > 12 else mint),
            name=d.get("name") or d.get("symbol") or d.get("ticker") or mint,
            first_seen=first_seen_dt,
            source="pumpportal_ws",
            extra={
                "first_trade_ts": ts, 
                "source": "pumpportal_ws", 
                "pool_address": d.get("poolAddress"),
                "trade_buys_30s": 0,
                "trade_sells_30s": 0,
                "trade_unique_buyers_30s": 0,
                "last_trade_ts": ts
            },
        )
        
        if self._on_new_token:
            async def _invoke_callback():
                try:
                    await self._on_new_token(cand, d)
                except Exception as cb_err:
                    logger.warning("PumpPortal WS sniper callback error: %s", cb_err)

            try:
                asyncio.create_task(_invoke_callback())
            except RuntimeError as task_err:
                logger.warning("PumpPortal WS sniper callback scheduling failed: %s", task_err)

        # DEBUG: lokita jokainen ehdokas
        logger.info(f"PUSH cand mint={mint} first_ts={ts} liq_hint=0 src=pumpportal_ws")
        
        with contextlib.suppress(asyncio.QueueFull):
            if metrics: metrics.candidates_in.labels(source="pumpportal_ws").inc()
            queue.put_nowait(cand)
        
        # Aloita trade-seuranta tälle mintille
        if mint not in self._subscribed_mints and self._ws:
            try:
                await self._ws.send(json.dumps({
                    "method": "subscribeTokenTrade",
                    "keys": [mint]
                }))
                self._subscribed_mints.add(mint)
                logger.debug(f"✅ Trade-seuranta aloitettu mintille: {mint[:8]}...")
            except Exception as e:
                logger.warning(f"Virhe aloittaessa trade-seurantaa {mint}: {e}")

    async def _handle_trade_event(self, ev, queue):
        """Käsittele trade-event ja päivitä tilastot"""
        d = ev.get("data") or ev
        mint = d.get("mint") or d.get("tokenAddress")
        if not mint:
            return
            
        trader = d.get("trader") or d.get("buyer") or d.get("seller")
        side = d.get("side") or d.get("type")  # "buy" tai "sell"
        ts = time.time()
        
        # Päivitä trade-tilastot
        if mint in self._trade_stats:
            stats = self._trade_stats[mint]
            if side == "buy":
                stats["buys"] += 1
            elif side == "sell":
                stats["sells"] += 1
            
            if trader:
                stats["unique_buyers"].add(trader)
            
            stats["last_ts"] = ts
            
            # Päivitä trade-tilastot extra-dataan
            stats["trade_buys_30s"] = stats["buys"]
            stats["trade_sells_30s"] = stats["sells"] 
            stats["trade_unique_buyers_30s"] = len(stats["unique_buyers"])
            stats["last_trade_ts"] = ts
            
            # DEBUG-loki 1/20 trade-eventistä
            self._debug_counter += 1
            if self._debug_counter % 20 == 0:
                logger.debug("PP-WS trade mint=%s buyer=%s side=%s", mint[:8], trader[:8] if trader else "N/A", side)
            
            # Metrics
            if metrics: 
                metrics.candidates_in.labels(source="pumpportal_ws_trades").inc()
            
            # Lähetä trade-päivitys queueen (jos haluat että DE käsittelee sen)
            trade_update = {
                "type": "trade_update",
                "mint": mint,
                "buyer": trader,
                "side": side,
                "ts": ts,
                "stats": {
                    "buys": stats["buys"],
                    "sells": stats["sells"],
                    "unique_buyers": len(stats["unique_buyers"])
                }
            }

            # Vaihtoehto: työnnä queueen trade-päivitys
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(trade_update)

            if self._on_trade:
                try:
                    await self._on_trade({"mint": mint, **d, "ts": ts})
                except Exception as cb_err:
                    logger.warning("PumpPortal WS trade callback error: %s", cb_err)

    def stop(self):
        self._stop.set()
        if self._ws:
            asyncio.create_task(self._ws.close())
