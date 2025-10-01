# sources/pumpportal_newtokens.py
from __future__ import annotations
import asyncio, time, contextlib, aiohttp, logging, datetime
from discovery_engine import TokenCandidate
from metrics import metrics

logger = logging.getLogger(__name__)

class PumpPortalNewTokensSource:
    def __init__(self, base_url: str, poll_interval: float = 2.0):
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self._stop = asyncio.Event()
        self._seen = set()
        self._ctr = 0
        self._error_streak = 0
        self._last_error_status = None

    def _get_mint(self, it):
        return it.get("mint") or it.get("tokenAddress") or it.get("mintAddress")

    def _get_pool(self, it):
        return it.get("poolAddress") or it.get("pool") or None

    def _get_first_ts(self, it):
        # hyväksy sekunnit / millisekunnit / ISO8601
        v = it.get("firstTradeAt") or it.get("createdAt") or it.get("first_trade_unix")
        if v is None: return None
        try:
            # numero?
            fv = float(v)
            # jos näyttää millisekunneilta
            if fv > 1e12: fv = fv / 1000.0
            return fv
        except Exception:
            # ISO8601
            try:
                dt = datetime.datetime.fromisoformat(str(v).replace("Z","+00:00"))
                return dt.timestamp()
            except Exception:
                return None

    async def run(self, queue):
        logger.info("🎯 PumpPortalNewTokensSource run() käynnistetty")
        if not self.base_url:
            logger.warning("PumpPortal base_url puuttuu – lähde ohitetaan.")
            return
        try:
            async with aiohttp.ClientSession() as session:
                while not self._stop.is_set():
                    try:
                        url = f"{self.base_url}/recent?limit=200"
                        async with session.get(url, timeout=5) as resp:
                            status = resp.status
                            try:
                                data = await resp.json(content_type=None)
                            except Exception:
                                data = []
                        if status >= 400:
                            self._error_streak += 1
                            if metrics: metrics.source_errors.inc()
                            backoff = min(60.0, self.poll_interval * (2 ** min(6, self._error_streak - 1)))
                            log_once = (
                                status != self._last_error_status
                                or self._error_streak in (1, 3, 5, 10, 20)
                            )
                            if log_once:
                                logger.warning(
                                    "⚠️ PumpPortal HTTP fetch epäonnistui: status=%s (attempt=%s, url=%s). Backoff=%.1fs",
                                    status,
                                    self._error_streak,
                                    url,
                                    backoff,
                                )
                                self._last_error_status = status
                            if status == 404 and self._error_streak >= 3:
                                logger.warning(
                                    "🚫 PumpPortal /recent endpoint palauttaa 404 toistuvasti – poistetaan HTTP-lähde käytöstä. Tarkista base_url: %s",
                                    self.base_url,
                                )
                                return
                            await asyncio.sleep(backoff)
                            continue

                        if self._error_streak:
                            logger.info(
                                "✅ PumpPortal HTTP fetch palautui: status=%s, edellinen virhesarja=%s",
                                status,
                                self._error_streak,
                            )
                        self._error_streak = 0
                        self._last_error_status = None

                        items = data if isinstance(data, list) else (data.get("data") or [])
                        logger.info(f"🌊 PumpPortal fetch: status={status}, items={len(items)}")
                        
                        # Inkrementoi metriikka jos käytössä
                        if metrics:
                            metrics.candidates_in.labels(source="pumpportal_fetch").inc(len(items))
                        
                        for it in items:
                            if not isinstance(it, dict):
                                continue
                            
                            # DEBUG: joka 200. item
                            if self._ctr % 200 == 0:
                                logger.info("pumpportal sample keys=%s", list(it.keys())[:10])
                            self._ctr += 1
                            
                            mint = self._get_mint(it)
                            if not mint or mint in self._seen:
                                continue
                            self._seen.add(mint)
                            
                            first_ts = self._get_first_ts(it)
                            liq = it.get("liquidityUsd") or it.get("liqUsd") or 0.0
                            top10 = it.get("top10Share") or it.get("topHoldersShare") or None
                            
                            symbol = it.get("symbol") or it.get("ticker") or (mint[:8] + "…" + mint[-4:] if len(mint) > 12 else mint)
                            name = it.get("name") or symbol or mint
                            cand = TokenCandidate(
                                mint=mint,
                                symbol=symbol,
                                name=name,
                                extra={"first_trade_ts": first_ts, "source": "pumpportal", "liq_hint": liq, "top10_hint": top10, "pool_address": self._get_pool(it)},
                            )
                            
                            # DEBUG: lokita jokainen ehdokas
                            logger.info(f"PUSH cand mint={mint} first_ts={first_ts} liq_hint={liq} src=pumpportal")
                            
                            with contextlib.suppress(asyncio.QueueFull):
                                if metrics: metrics.candidates_in.labels(source="pumpportal").inc()
                                queue.put_nowait(cand)
                    except Exception:
                        await asyncio.sleep(0.5)
                    await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            raise

    def stop(self):
        self._stop.set()
