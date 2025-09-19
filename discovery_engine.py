"""
DiscoveryEngine - Solana uutuustoken-seulonta
Toteuttaa docs/DISCOVERY_ENGINE_SPEC.md vaatimukset
"""

import asyncio
import logging
import time
import random
import contextlib
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Awaitable, Protocol
from zoneinfo import ZoneInfo
from config import load_config
from metrics import metrics, init_metrics

# RPC interfaces
try:
    from rpc_interfaces import SolanaRPC, MintInfo, LPInfo, Distribution, FlowStats
    RPC_INTERFACES_AVAILABLE = True
except ImportError:
    RPC_INTERFACES_AVAILABLE = False
    # Fallback stubs
    class MintInfo:
        renounced_mint: bool = True
        renounced_freeze: bool = True
    class LPInfo:
        locked_or_burned: bool = True
        liquidity_usd: float = 5000.0
    class Distribution:
        top_share: float = 0.08
    class FlowStats:
        unique_buyers: int = 50
        buy_sell_ratio: float = 1.2
    class SolanaRPC:
        async def get_mint_info(self, mint): return MintInfo()
        async def get_lp_info(self, pool_address): return LPInfo()
        async def get_holder_distribution(self, mint, top_n=10): return Distribution()
        async def get_flow_stats(self, mint, window_sec=300): return FlowStats()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone
HELSINKI_TZ = ZoneInfo("Europe/Helsinki")

@dataclass
class TokenCandidate:
    """Token ehdokas DiscoveryEngine:lle"""
    # Perustiedot
    mint: str
    symbol: str = ""
    name: str = ""
    decimals: int = 9
    # DEX pool osoite (tarvitaan joissain integraatiotesteissä)
    pool_address: str = ""
    
    # Likviditeetti ja jakelu
    liquidity_usd: float = 0.0
    top10_holder_share: float = 0.0
    lp_locked: bool = False
    lp_burned: bool = False
    
    # Authority tiedot
    mint_authority_renounced: bool = False
    freeze_authority_renounced: bool = False
    
    # Momentti ja aktiviteetti
    age_minutes: float = 0.0
    unique_buyers_5m: int = 0
    buys_5m: int = 0
    sells_5m: int = 0
    buy_sell_ratio: float = 1.0
    price_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    
    # Pisteytys
    novelty_score: float = 0.0
    liquidity_score: float = 0.0
    distribution_score: float = 0.0
    # Yhteenvetomainen aktiivisuuspiste (testien yhteensopivuus)
    activity_score: float = 0.0
    rug_risk_score: float = 0.0
    overall_score: float = 0.0
    last_score: float = 0.0
    
    # Metadata
    source: str = ""
    first_seen: datetime = field(default_factory=lambda: datetime.now(HELSINKI_TZ))
    last_updated: datetime = field(default_factory=lambda: datetime.now(HELSINKI_TZ))
    
    # RPC data cache
    _rpc_data_cache: Dict[str, Any] = field(default_factory=dict, init=False)
    
    # Extra metadata
    extra: Dict[str, Any] = field(default_factory=dict)

class MarketSource(Protocol):
    """Protokolla markkinoiden data lähteille"""
    
    async def start(self) -> None:
        """Käynnistä data lähde"""
        ...
    
    async def stop(self) -> None:
        """Sammuta data lähde"""
        ...
    
    async def get_new_tokens(self) -> List[TokenCandidate]:
        """Hae uudet tokenit"""
        ...

class DiscoveryEngine:
    """
    Solana uutuustoken-seulonta moottori
    
    Käyttää asynkronisia tuottajia -> Queue -> TokenCandidate
    Suorittaa pikafiltteröinnin ja pisteytyksen
    """
    
    def __init__(
        self,
        rpc_endpoint: str = None,
        market_sources: List[MarketSource] = None,
        min_liq_usd: float = None,
        rpc_client: Optional[SolanaRPC] = None,
        rpc=None,  # uusi alias taaksepäin yhteensopivuudelle
        **_
    ):
        """
        Alusta DiscoveryEngine
        
        Args:
            rpc_endpoint: Solana RPC endpoint
            market_sources: Lista markkinoiden data lähteistä
            min_liq_usd: Minimilikviditeetti USD (jos None, käytetään konfiguraatiota)
            rpc_client: RPC client (jos None, luodaan uusi)
        """
        self.rpc_endpoint = rpc_endpoint
        self.market_sources = list(market_sources or [])
        
        # Lue konfiguraatio
        self.config = load_config()
        self.min_liq_usd = min_liq_usd if min_liq_usd is not None else self.config.discovery.min_liq_usd
        
        # Uudet säätimet tuoreille tokeneille
        self.min_liq_fresh_usd = float(getattr(self.config.discovery, "min_liq_fresh_usd", 1200.0))
        self.max_top10_share_fresh = float(getattr(self.config.discovery, "max_top10_share_fresh", 0.98))
        self.max_top10_share_norm = float(getattr(self.config.discovery, "max_top10_share", 0.95))
        self.base_score_threshold = float(getattr(self.config.discovery, "score_threshold", 0.52))
        self.min_score_cap_delta = float(getattr(self.config.discovery, "min_score_cap_delta", 0.10))
        
        # Fresh-pass ikkuna ja trade-tilastot
        self.fresh_window_sec = int(getattr(self.config.discovery, "fresh_window_sec", 90))
        self.trade_min_unique_buyers = int(getattr(self.config.discovery, "trade_min_unique_buyers", 3))
        self.trade_min_trades = int(getattr(self.config.discovery, "trade_min_trades", 5))
        self.candidate_ttl_sec = float(getattr(self.config.discovery, "candidate_ttl_sec", 600))
        self._trade_stats = {}  # mint -> {"buys":int,"sells":int,"unique_buyers":set(),"first_ts":float,"last_ts":float}
        
        # Fresh-pass asetukset
        self.fresh_pass_cfg = getattr(self.config.discovery, "fresh_pass", None)
        if self.fresh_pass_cfg:
            self._fresh_cfg = self.fresh_pass_cfg
        else:
            # Fallback jos ei ole konfiguraatiota
            class _F: 
                enabled=True
                ttl_sec=90
                min_unique_buyers=0
                min_trades=0
                sources=("pumpportal_ws","helius_logs")
            self._fresh_cfg = _F()
        
        # RPC client - tuki sekä vanhalle että uudelle kutsutavalle
        self.rpc_client = rpc_client or rpc  # voi olla None -> rikastusmetodeissa tarkista!
        if self.rpc_client is None and rpc_endpoint:
            self.rpc_client = SolanaRPC(rpc_endpoint)
        
        # Eventit ja sentinel
        self._stop_event = asyncio.Event()
        self._closed_event = asyncio.Event()
        self._sentinel = object()  # herättää jonon pysäytyksessä
        
        # Sisäinen tila
        self.candidate_queue: asyncio.Queue[TokenCandidate] = asyncio.Queue(maxsize=self.config.discovery.max_queue)
        self.processed_candidates: Dict[str, TokenCandidate] = {}
        self.running = False
        
        # Deduplikointi
        self.candidate_sources: Dict[str, List[str]] = {}  # mint -> [source1, source2, ...]
        self.candidate_first_seen: Dict[str, float] = {}  # mint -> timestamp
        
        # Dev-lompakko seuranta
        self.dev_wallet_activity: Dict[str, Dict] = {}  # mint -> {dev_wallet: str, first_seen: float, sells: []}

        # LP-lock seuranta
        self.lp_lock_timing: Dict[str, Dict] = {}  # mint -> {first_seen: float, lp_locked_at: float, lock_delay_minutes: float}

        # Ostajien kiihtyvyys seuranta
        self.buyer_acceleration: Dict[str, List] = {}  # mint -> [(timestamp, unique_buyers), ...]
        self.ws_seen_recently: Dict[str, float] = {}   # mint -> last ts seen from ws source
        self.ws_seen_initial: Dict[str, float] = {}    # mint -> first ts seen for spread-out dedupe
        self.ws_seen_count: Dict[str, int] = {}
        
        # Dynaaminen score-kynnys
        self.score_history = deque(maxlen=100)  # Liukuva ikkuna 15 min (100 * 9s)
        self.last_score_update = 0
        self.filter_reason_history = deque(maxlen=200)  # 30 min ikkuna hylkäyssyyille
        
        # Tehtävät
        self.source_tasks: List[asyncio.Task] = []
        self.scorer_task: Optional[asyncio.Task] = None
        
        # Pisteytys parametrit
        self.score_threshold = self.config.discovery.score_threshold
        self.max_candidates = 100
        self.last_effective_score = None
        
        logger.info(f"DiscoveryEngine alustettu: {len(market_sources)} lähdettä, min_liq=${min_liq_usd}")

    def _is_fresh(self, c) -> bool:
        """Tunnista tuoreet tokenit (≤10 min on-chain aikaleimasta)"""
        ts = (getattr(c, "extra", {}) or {}).get("first_pool_ts") \
             or (getattr(c, "extra", {}) or {}).get("first_trade_ts")
        return bool(ts and (time.time() - float(ts)) / 60.0 <= 10.0)

    def update_trade_stats(self, mint: str, buyer: str|None, side: str|None, ts: float):
        """Päivitä trade-tilastot mintille"""
        st = self._trade_stats.get(mint)
        if not st:
            st = {"buys":0,"sells":0,"unique_buyers":set(),"first_ts":ts,"last_ts":ts}
            self._trade_stats[mint] = st
        if side == "buy": 
            st["buys"] += 1
        if side == "sell": 
            st["sells"] += 1
        if buyer: 
            st["unique_buyers"].add(buyer)
        st["last_ts"] = ts

    def _is_ws_fresh_source(self, c) -> bool:
        """Tarkista onko lähde fresh-pass kelpoinen"""
        src = ((c.extra or {}).get("source") if c and getattr(c,"extra",None) else None)
        return bool(src and (src in getattr(self._fresh_cfg,"sources",("pumpportal_ws","helius_logs"))))

    def _age_sec(self, c) -> float:
        """Laske tokenin ikä sekunneissa"""
        ts = (c.extra or {}).get("first_pool_ts") or (c.extra or {}).get("first_trade_ts") or getattr(c, "first_seen_ts", time.time())
        try:
            return max(0.0, time.time() - float(ts))
        except Exception:
            return 1e9

    def _ws_trade_stats(self, c):
        """Hae trade-tilastot mintille"""
        st = self._trade_stats.get(c.mint) if c and getattr(c,"mint",None) else None
        if not st:
            return 0,0,0
        buyers = len(st.get("unique_buyers") or set())
        buys   = int(st.get("buys") or 0)
        sells  = int(st.get("sells") or 0)
        return buyers, buys, sells

    async def start(self) -> None:
        """Käynnistä lähteet ja scorer-loop. Ei blokkaa."""
        self._stop_event.clear()
        self._closed_event.clear()

        # Metrics alustus jätetään ulkoiselle koodille (testit hoitavat sen)
        # global metrics
        # if not metrics and self.config.metrics.enabled:
        #     init_metrics(
        #         namespace=self.config.metrics.namespace,
        #         host=self.config.metrics.host,
        #         port=self.config.metrics.port,
        #         enabled=self.config.metrics.enabled
        #     )

        # Metrics
        if metrics:
            metrics.engine_running.set(1)

        # Lähdeadapterit (voi olla tyhjä lista)
        self.source_tasks = [
            asyncio.create_task(src.run(self.candidate_queue), name=f"src:{type(src).__name__}")
            for src in (self.market_sources or [])
        ]

        # Scorer-loop
        self.scorer_task = asyncio.create_task(self._scorer_loop(), name="scorer_loop")

    async def stop(self) -> None:
        """Pysäytä siististi. Turvallinen kutsua useasti."""
        if self._stop_event.is_set():
            return
        # ilmoita pysäytyksestä
        self._stop_event.set()
        
        # Metrics
        if metrics:
            metrics.engine_running.set(0)

        # herätä queue (ettei get() jää odottamaan)
        with contextlib.suppress(asyncio.QueueFull):
            self.candidate_queue.put_nowait(self._sentinel)  # EI await

        # peruuta lähteet
        for t in self.source_tasks:
            t.cancel()
        # odota niiden kaatuminen ilman poikkeusvuotoa
        if self.source_tasks:
            await asyncio.gather(*self.source_tasks, return_exceptions=True)

        # peruuta scorer-loop, jos se ei jo lopu sentinelillä
        if self.scorer_task and not self.scorer_task.done():
            self.scorer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.scorer_task

        self._closed_event.set()

    async def wait_closed(self, timeout: float | None = 5.0) -> None:
        """Odottaa että pysäytys on valmis (testeissä kätevä)."""
        try:
            await asyncio.wait_for(self._closed_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            # viimeinen varmistus: sammuta väkisin
            if self.scorer_task and not self.scorer_task.done():
                self.scorer_task.cancel()

    async def run_until_idle(self, idle_seconds: float = 0.5, max_wait: float = 3.0) -> None:
        """
        Odottaa, että jonossa ei tule uusia ehdokkaita 'idle_seconds' aikana,
        tai kunnes max_wait täyttyy. Ei korvaa start/stop -elinkaarta.
        """
        start = asyncio.get_event_loop().time()
        last_seen = start
        while (asyncio.get_event_loop().time() - start) < max_wait:
            if self.candidate_queue.empty():
                if (asyncio.get_event_loop().time() - last_seen) >= idle_seconds:
                    return
                await asyncio.sleep(0.05)
            else:
                last_seen = asyncio.get_event_loop().time()
                await asyncio.sleep(0.05)

    async def _run_source(self, source: MarketSource) -> None:
        """Aja yksi markkinoiden lähde"""
        try:
            await source.start()
            logger.info(f"✅ Lähde käynnistetty: {source.__class__.__name__}")
            
            while self.running:
                try:
                    # Hae uudet tokenit
                    new_tokens = await source.get_new_tokens()
                    
                    for token in new_tokens:
                        if not self.running:
                            break
                        
                        # Lisää queueen
                        try:
                            await self.candidate_queue.put(token)
                            logger.debug(f"Token lisätty queueen: {token.symbol}")
                            
                            # Metrics: candidates_in per source
                            from metrics import metrics as global_metrics
                            if global_metrics:
                                source_name = getattr(source, '__class__', type(source)).__name__.lower()
                                global_metrics.candidates_in.labels(source=source_name).inc()
                                
                        except asyncio.QueueFull:
                            logger.warning("Candidate queue täynnä, pudotetaan vanhin")
                            try:
                                self.candidate_queue.get_nowait()
                                await self.candidate_queue.put(token)
                                
                                # Metrics: candidates_in per source
                                from metrics import metrics as global_metrics
                                if global_metrics:
                                    source_name = getattr(source, '__class__', type(source)).__name__.lower()
                                    global_metrics.candidates_in.labels(source=source_name).inc()
                                    
                            except asyncio.QueueEmpty:
                                pass
                    
                    # Odota seuraavaan hakuun
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    logger.error(f"Virhe lähdessä {source.__class__.__name__}: {e}")
                    await asyncio.sleep(5.0)  # Odota ennen uudelleenyritystä
                    
        except asyncio.CancelledError:
            logger.info(f"🛑 Lähde {source.__class__.__name__} peruttu")
            raise  # Kupla ulos jotta task päättyy
        except Exception as e:
            logger.error(f"Kriittinen virhe lähdessä {source.__class__.__name__}: {e}")
        finally:
            try:
                await source.stop()
            except Exception as e:
                logger.warning(f"Virhe sammutettaessa lähdettä: {e}")

    async def _scorer_loop(self) -> None:
        """Pääscorer loop - käsittelee tokenit queue:sta"""
        logger.info("🎯 Scorer loop käynnistetty")
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Odota uusi token tai stop event
                    done, pending = await asyncio.wait([
                        asyncio.create_task(self.candidate_queue.get()),
                        asyncio.create_task(self._stop_event.wait())
                    ], return_when=asyncio.FIRST_COMPLETED)
                    
                    # Peruuta pending tehtävät
                    for task in pending:
                        task.cancel()
                    
                    # Tarkista stop event
                    if self._stop_event.is_set():
                        logger.info("🛑 Stop event saatu, pysäytetään scorer loop")
                        break
                    
                    # Hae token
                    token_task = done.pop()
                    if token_task.done() and not token_task.cancelled():
                        token = token_task.result()
                        
                        # Tarkista sentinel
                        if token is self._sentinel:
                            logger.info("🛑 Sentinel saatu, pysäytetään scorer loop")
                            break
                        
                        # Käsittele trade-päivitys
                        if isinstance(token, dict) and token.get("type") == "trade_update":
                            self.update_trade_stats(
                                token["mint"], 
                                token.get("buyer"), 
                                token.get("side"), 
                                token.get("ts", time.time())
                            )
                            continue
                        
                        # Käsittele token
                        await self._process_candidate(token)
                    
                except asyncio.CancelledError:
                    logger.info("🛑 Scorer loop peruutettu")
                    break
                except Exception as e:
                    logger.error(f"Virhe scorer loop:ssa: {e}")
                    if not self._stop_event.is_set():
                        await asyncio.sleep(0.1)  # Lyhyt tauko virheiden välillä
                        
        finally:
            logger.info("🎯 Scorer loop päättynyt")
            self._closed_event.set()

    async def _process_candidate(self, candidate: TokenCandidate) -> None:
        """Käsittele yksi token ehdokas"""
        start_time = time.time()
        try:
            # Deduplikointi
            if candidate.mint in self.processed_candidates:
                existing = self.processed_candidates[candidate.mint]
                if existing.last_updated > candidate.first_seen:
                    return  # Vanhempi versio, ohita
            
            # Pikafiltteri
            if not self._fast_filter(candidate):
                logger.debug(f"Token hylätty pikafiltterissä: {candidate.symbol}")
                return
            
            # Rikasoi data RPC:stä
            await self._enrich_quick(candidate)
            
            # Laske pisteytys
            self._score(candidate)
            
            # Tallenna
            self.processed_candidates[candidate.mint] = candidate
            
            # Pidä vain parhaat
            if len(self.processed_candidates) > self.max_candidates:
                self._trim_candidates()
            
            # Metrics
            from metrics import metrics as global_metrics
            if global_metrics:
                global_metrics.candidates_seen.inc()
                global_metrics.candidates_scored.inc()
                global_metrics.queue_depth.set(self.candidate_queue.qsize())
                global_metrics.score_hist.observe(candidate.overall_score)
            
            # Päivitä score-historia dynaamista kynnystä varten
            self.score_history.append(candidate.overall_score)
            
            # Deduplikointi ja lähde-yhdistely
            mint = getattr(candidate, 'mint', 'unknown')
            source_name = getattr(candidate, 'source', 'unknown')
            current_time = time.time()
            
            if mint not in self.candidate_sources:
                self.candidate_sources[mint] = []
                self.candidate_first_seen[mint] = current_time
            
            # Lisää lähde jos ei ole jo listassa
            if source_name not in self.candidate_sources[mint]:
                self.candidate_sources[mint].append(source_name)
                
                # Bonus pisteytys jos sama mint nähdään ≥ 2 lähteestä ~60s sisällä
                time_since_first = current_time - self.candidate_first_seen[mint]
                if len(self.candidate_sources[mint]) >= 2 and time_since_first <= 60:
                    candidate.overall_score += 0.02
                    logger.info(f"🎯 Multi-source bonus: {candidate.symbol} (+0.02, sources: {self.candidate_sources[mint]})")
            
            # Merkitse lähteet
            if not hasattr(candidate, 'extra'):
                candidate.extra = {}
            candidate.extra['seen_from'] = self.candidate_sources[mint]
            
            # Dev-lompakko seuranta
            self._check_dev_wallet_behavior(candidate)
            
            # LP-lock viive seuranta
            self._check_lp_lock_timing(candidate)
            
            # Ostajien kiihtyvyys seuranta
            self._track_buyer_acceleration(candidate)
            
            # Spread & slippage tarkistus
            self._check_spread_slippage(candidate)
            
            logger.info(f"✅ Token käsitelty: {candidate.symbol} (Score: {candidate.overall_score:.3f}, Sources: {self.candidate_sources[mint]})")
            
        except Exception as e:
            logger.error(f"Virhe käsiteltäessä tokenia {candidate.symbol}: {e}")

    def _age_minutes(self, candidate: TokenCandidate) -> float:
        """
        Laske tokenin ikä minuutteina käyttäen on-chain aikaleimoja
        
        Args:
            candidate: TokenCandidate objekti
            
        Returns:
            Ikä minuutteina
        """
        # Etsi ensisijainen aikaleima (first_pool_ts tai first_trade_ts)
        timestamp = None
        
        # Kokeile first_pool_ts
        if hasattr(candidate, 'extra') and candidate.extra:
            timestamp = candidate.extra.get("first_pool_ts")
        
        # Kokeile first_trade_ts
        if not timestamp and hasattr(candidate, 'extra') and candidate.extra:
            timestamp = candidate.extra.get("first_trade_ts")
        
        # Käytä first_seen_ts fallbackina
        if not timestamp:
            timestamp = candidate.first_seen_ts
        
        # Laske ikä minuutteina
        current_time = time.time()
        age_seconds = max(0.0, current_time - timestamp)
        age_minutes = age_seconds / 60.0
        
        return age_minutes

    def _calculate_dynamic_score_threshold(self) -> float:
        """
        Laske dynaaminen score-kynnys kvantiilin mukaan + kynnyskatto
        
        Returns:
            Dynaaminen min_score
        """
        # Käytä uusia säätimiä
        base = self.base_score_threshold
        cap = self.min_score_cap_delta
        
        # Jos ei tarpeeksi dataa, käytä baseline
        if len(self.score_history) < 10:
            q80 = base
        else:
            # Laske 80% kvantiili
            scores = list(self.score_history)
            scores.sort()
            n = len(scores)
            q80_index = int(0.8 * n)
            q80 = scores[q80_index] if q80_index < n else scores[-1]
        
        # Kynnyskatto: effective = max(base, min(q80, base + cap))
        effective = max(base, min(q80, base + cap))
        
        # Automaattinen pohjakynnys: jos rug_controls_missing > 30% 30 min ikkunassa
        if len(self.filter_reason_history) >= 50:  # Vähintään 50 hylkäystä
            rug_missing_count = sum(1 for reason in self.filter_reason_history if reason == "rug_controls_missing")
            rug_missing_ratio = rug_missing_count / len(self.filter_reason_history)
            
            if rug_missing_ratio > 0.30:  # > 30%
                # Nosta pohjakynnystä 0.05
                base = min(0.95, base + 0.05)
                effective = max(effective, base)
                logger.warning(f"🚨 Automaattinen pohjakynnys nostettu: {base:.2f} (rug_missing: {rug_missing_ratio:.1%})")
        
        # Päivitä metriikka
        if metrics:
            metrics.min_score_effective.set(effective)
        
        logger.info(f"min_score dynamic={effective:.2f} (base={base:.2f}, q80={q80:.2f}, cap={cap:.2f})")
        
        # Tallenna viimeisin effective score
        self.last_effective_score = effective
        
        return effective

    def _is_ultra_fresh(self, candidate: TokenCandidate) -> bool:
        """
        Tarkista onko token ultra-fresh (≤ 10 minuuttia) - vain on-chain aikaleimoilla
        
        Args:
            candidate: TokenCandidate objekti
            
        Returns:
            True jos token on ultra-fresh
        """
        # Tarkista että on on-chain aikaleima
        if not hasattr(candidate, 'extra') or not candidate.extra:
            return False
        ts = candidate.extra.get("first_pool_ts") or candidate.extra.get("first_trade_ts")
        if not ts:
            return False  # ⬅️ vain on-chain-lähteet
        
        # Ultra-fresh ehto: ikä <= 10.0 minuuttia
        age_min = (time.time() - ts) / 60.0
        return age_min <= 10.0

    def _fast_filter(self, candidate: TokenCandidate) -> bool:
        """
        Kaksivaiheinen pikafiltteri: tuoreille löysempi, vanhoille tiukempi
        
        Args:
            candidate: Token ehdokas
            
        Returns:
            True jos token läpäisee filtterit
        """
        # --- FRESH-PASS: älä hylkää heti tuoretta WS-kandia ---
        if getattr(self._fresh_cfg, "enabled", True) and self._is_ws_fresh_source(candidate):
            age = self._age_sec(candidate)
            if age <= float(getattr(self._fresh_cfg,"ttl_sec",90)):
                mint = getattr(candidate, "mint", None)
                ts_now = time.time()
                if mint:
                    # Estä kovat burstit (alle 1s) ja throttle per mint
                    first_seen = self.ws_seen_initial.get(mint)
                    last_seen = self.ws_seen_recently.get(mint, 0.0)
                    if first_seen is None:
                        self.ws_seen_initial[mint] = ts_now
                        self.ws_seen_count[mint] = 0
                    else:
                        # ohita alle 0.8s väli
                        if ts_now - last_seen < 0.8:
                            logger.debug("WS burst skip mint=%s dt=%.3fs", mint[:8], ts_now - last_seen)
                            return False
                        # jos jo >4 eventtiä alle 10s sisällä → droppaa
                        if ts_now - first_seen < 10.0 and self.ws_seen_count.get(mint, 0) >= 4:
                            logger.debug("WS throttle mint=%s count>=4 in <10s", mint[:8])
                            return False
                        if ts_now - first_seen > 10.0:
                            self.ws_seen_initial[mint] = ts_now
                            self.ws_seen_count[mint] = 0
                    self.ws_seen_recently[mint] = ts_now
                    self.ws_seen_count[mint] = self.ws_seen_count.get(mint, 0) + 1
                buyers, buys, sells = self._ws_trade_stats(candidate)
                min_buyers = max(1, int(getattr(self._fresh_cfg, "min_unique_buyers", 0) or 0))
                min_trades = max(1, int(getattr(self._fresh_cfg, "min_trades", 0) or 0))
                ok = (buyers >= min_buyers) or ((buys + sells) >= min_trades)
                if ok:
                    # metriikat ja loki
                    from metrics import metrics as _m
                    if _m:
                        try:
                            _m.candidates_filtered_reason.labels(reason="fresh_pass").inc()
                            _m.fresh_pass_total.inc()
                        except Exception:
                            pass
                    logger.info("FRESH-PASS mint=%s age=%.1fs buyers=%d trades=%d", getattr(candidate,"mint",None), age, buyers, buys+sells)
                    return True
        # --- /FRESH-PASS ---
        
        fresh = self._is_fresh(candidate)
        
        # FRESH-PASS: anna pass jos jokin ehdoista täyttyy
        if fresh:
            ts = (candidate.extra or {}).get("first_pool_ts") or (candidate.extra or {}).get("first_trade_ts") or candidate.first_seen.timestamp()
            age = time.time() - ts
            if age <= self.fresh_window_sec:
                # anna pass jos jokin näistä täyttyy - käytä getattr-defaultteja
                buyers = int((candidate.extra or {}).get("trade_unique_buyers_30s") or getattr(candidate,"unique_buyers_5m",0) or 0)
                trades = int((candidate.extra or {}).get("trade_buys_30s") or getattr(candidate,"buys_5m",0) or 0) \
                       + int((candidate.extra or {}).get("trade_sells_30s") or getattr(candidate,"sells_5m",0) or 0)
                if buyers >= self.trade_min_unique_buyers or trades >= self.trade_min_trades:
                    logger.info("FRESH-PASS mint=%s buyers=%d trades=%d age=%.1fs", candidate.mint[:8], buyers, trades, age)
                    from metrics import metrics as global_metrics
                    if global_metrics:
                        global_metrics.candidates_filtered_reason.labels(reason="fresh_pass").inc()
                    return True  # ohita liq/top10/authority tässä vaiheessa
        
        # LIQ: tuoreille pienempi minimilikviditeetti
        min_liq = self.min_liq_fresh_usd if fresh else self.min_liq_usd
        if (candidate.liquidity_usd or 0.0) < float(min_liq):
            logger.debug(f"❌ {candidate.symbol}: Liian pieni likviditeetti (${candidate.liquidity_usd:.0f}, min=${min_liq:.0f}, fresh={fresh})")
            from metrics import metrics as global_metrics
            if global_metrics:
                global_metrics.candidates_filtered.inc()
                global_metrics.candidates_filtered_reason.labels(reason="low_liq").inc()
            self.filter_reason_history.append("low_liq")
            return False

        # RUG-controls: hae riskikonfiguraatio
        risk_cfg = getattr(self.config, "risk", None)
        require_lp_locked = getattr(risk_cfg, "require_lp_locked", True)
        require_renounced = getattr(risk_cfg, "require_renounced", True)

        controls_ok = True
        if require_lp_locked and not (candidate.lp_locked or candidate.lp_burned):
            controls_ok = False
        if require_renounced and not (candidate.mint_authority_renounced and candidate.freeze_authority_renounced):
            controls_ok = False

        if not controls_ok and not fresh:
            logger.debug(f"⚠️ {candidate.symbol}: Dev/LP kontrollit aktiiviset (fresh={fresh})")
            from metrics import metrics as global_metrics
            if global_metrics:
                global_metrics.candidates_filtered.inc()
                global_metrics.candidates_filtered_reason.labels(reason="rug_controls_missing").inc()
            self.filter_reason_history.append("rug_controls_missing")
            return False
        
        # Tuoreille tokenille: älä hylkää authority/LP-syystä heti; jatka pisteytykseen
        if fresh and (candidate.liquidity_usd or 0.0) >= float(self.min_liq_fresh_usd):
            # älä hylkää authority/LP-syystä heti; jatka pisteytykseen
            pass
        
        # Holder-konsentraatio: tuoreille löysempi raja
        max_share = self.max_top10_share_fresh if fresh else self.max_top10_share_norm
        if (candidate.top10_holder_share or 1.0) > float(max_share):
            logger.debug(f"❌ {candidate.symbol}: Liian korkea top10 share ({candidate.top10_holder_share:.2f}, max={max_share:.2f}, fresh={fresh})")
            from metrics import metrics as global_metrics
            if global_metrics:
                global_metrics.candidates_filtered.inc()
                global_metrics.candidates_filtered_reason.labels(reason="concentrated_holders").inc()
            self.filter_reason_history.append("concentrated_holders")
            return False
        
        logger.debug(f"✅ {candidate.symbol}: Pikafiltterit läpäisty (fresh={fresh})")
        return True

    def _check_dev_wallet_behavior(self, candidate: TokenCandidate):
        """Tarkista dev-lompakon käyttäytyminen"""
        try:
            mint = getattr(candidate, 'mint', 'unknown')
            current_time = time.time()
            
            # Hae dev-lompakko (oletetaan että se on extra-datassa)
            dev_wallet = None
            if hasattr(candidate, 'extra') and candidate.extra:
                dev_wallet = candidate.extra.get('dev_wallet')
            
            if not dev_wallet:
                return
            
            # Alusta seuranta jos ei ole
            if mint not in self.dev_wallet_activity:
                self.dev_wallet_activity[mint] = {
                    'dev_wallet': dev_wallet,
                    'first_seen': current_time,
                    'sells': []
                }
            
            # Simuloi myynti-tapahtumia (korvaa oikealla RPC-kutsulla)
            # Tässä esimerkissä tarkistetaan onko dev-lompakko myynyt < 10 min listauksesta
            age_minutes = self._age_minutes(candidate)
            
            if age_minutes < 10:
                # Tarkista onko dev-lompakko myynyt (mock data)
                # Korvaa oikealla RPC-kutsulla joka hakee tapahtumat
                has_sold = self._check_dev_wallet_sells(dev_wallet, mint, current_time)
                
                if has_sold:
                    # Lisää rug_risk
                    if not hasattr(candidate, 'rug_risk_score'):
                        candidate.rug_risk_score = 0.0
                    candidate.rug_risk_score += 0.3  # +30% rug risk
                    candidate.overall_score = max(0.0, candidate.overall_score - 0.1)  # -10% overall
                    
                    logger.warning(f"🚨 Dev-lompakko myynyt < 10min: {candidate.symbol} (dev: {dev_wallet[:8]}...)")
                    
                    # Päivitä metriikka
                    from metrics import metrics as global_metrics
                    if global_metrics:
                        global_metrics.candidates_filtered_reason.labels(reason="dev_wallet_sold_early").inc()
        
        except Exception as e:
            logger.error(f"Virhe tarkistettaessa dev-lompakko käyttäytymistä: {e}")
    
    def _check_dev_wallet_sells(self, dev_wallet: str, mint: str, current_time: float) -> bool:
        """Tarkista onko dev-lompakko myynyt (mock implementation)"""
        # Mock: 5% todennäköisyys että dev-lompakko on myynyt
        import random
        return random.random() < 0.05

    def _check_lp_lock_timing(self, candidate: TokenCandidate):
        """Tarkista LP-lock viive"""
        try:
            mint = getattr(candidate, 'mint', 'unknown')
            current_time = time.time()
            
            # Alusta seuranta jos ei ole
            if mint not in self.lp_lock_timing:
                self.lp_lock_timing[mint] = {
                    'first_seen': current_time,
                    'lp_locked_at': None,
                    'lock_delay_minutes': None
                }
            
            # Tarkista onko LP lukittu
            if candidate.lp_locked and self.lp_lock_timing[mint]['lp_locked_at'] is None:
                # LP juuri lukittu
                self.lp_lock_timing[mint]['lp_locked_at'] = current_time
                lock_delay_minutes = (current_time - self.lp_lock_timing[mint]['first_seen']) / 60.0
                self.lp_lock_timing[mint]['lock_delay_minutes'] = lock_delay_minutes
                
                # Jos LP lukittu vasta > 10 min listauksesta, miinus pisteisiin
                if lock_delay_minutes > 10:
                    penalty = min(0.2, (lock_delay_minutes - 10) * 0.02)  # Max 20% penalty
                    candidate.overall_score = max(0.0, candidate.overall_score - penalty)
                    
                    logger.warning(f"⚠️ LP-lock viive: {candidate.symbol} lukittu vasta {lock_delay_minutes:.1f}min listauksesta (penalty: -{penalty:.2f})")
                    
                    # Päivitä metriikka
                    from metrics import metrics as global_metrics
                    if global_metrics:
                        global_metrics.candidates_filtered_reason.labels(reason="lp_lock_delayed").inc()
                else:
                    logger.info(f"✅ LP-lock ajoissa: {candidate.symbol} lukittu {lock_delay_minutes:.1f}min listauksesta")

                if not hasattr(candidate, 'extra') or candidate.extra is None:
                    candidate.extra = {}
                candidate.extra["lp_lock_delay_minutes"] = lock_delay_minutes

        except Exception as e:
            logger.error(f"Virhe tarkistettaessa LP-lock viivettä: {e}")

    def _track_buyer_acceleration(self, candidate: TokenCandidate):
        """Seuraa ostajien kiihtyvyyttä (1m-derivaatta)"""
        try:
            mint = getattr(candidate, 'mint', 'unknown')
            current_time = time.time()
            unique_buyers = getattr(candidate, 'unique_buyers_5m', 0)
            
            # Alusta seuranta jos ei ole
            if mint not in self.buyer_acceleration:
                self.buyer_acceleration[mint] = []
            
            # Lisää nykyinen mittaus
            self.buyer_acceleration[mint].append((current_time, unique_buyers))
            
            # Pidä vain viimeisen 5 min data
            cutoff_time = current_time - 300  # 5 min
            self.buyer_acceleration[mint] = [(ts, buyers) for ts, buyers in self.buyer_acceleration[mint] if ts > cutoff_time]
            
            # Laske kiihtyvyys jos tarpeeksi dataa
            if len(self.buyer_acceleration[mint]) >= 2:
                # Laske 1-min derivaatta (muutos per minuutti)
                recent_data = self.buyer_acceleration[mint][-2:]  # Viimeiset 2 mittaus
                time_diff = recent_data[1][0] - recent_data[0][0]
                buyer_diff = recent_data[1][1] - recent_data[0][1]
                
                if time_diff > 0:
                    acceleration = buyer_diff / (time_diff / 60.0)  # Ostajia per minuutti
                    
                    # Lisää pieni bonus jos kiihtyvyys on positiivinen
                    if acceleration > 0:
                        bonus = min(0.05, acceleration * 0.01)  # Max 5% bonus
                        candidate.overall_score = min(1.0, candidate.overall_score + bonus)
                        
                        if acceleration > 5:  # > 5 ostajaa/min
                            logger.info(f"🚀 Ostajien kiihtyvyys: {candidate.symbol} +{acceleration:.1f} ostajaa/min (bonus: +{bonus:.3f})")
                    
                    # Tallenna kiihtyvyys extra-dataan
                    if not hasattr(candidate, 'extra'):
                        candidate.extra = {}
                    candidate.extra['buyer_acceleration'] = acceleration
        
        except Exception as e:
            logger.error(f"Virhe seuratessa ostajien kiihtyvyyttä: {e}")

    def _check_spread_slippage(self, candidate: TokenCandidate):
        """Tarkista spread & slippage (exit-likviditeettiriski)"""
        try:
            # Hae spread-tiedot (oletetaan että ne ovat extra-datassa)
            spread_percent = None
            if hasattr(candidate, 'extra') and candidate.extra:
                spread_percent = candidate.extra.get('spread_percent')
            
            # Jos ei spread-tietoja, simuloi (korvaa oikealla API-kutsulla)
            if spread_percent is None:
                # Mock spread: 0.1% - 5% satunnaisesti
                import random
                spread_percent = random.uniform(0.1, 5.0)
            
            # Spread > 2% → rangaistus (exit-likviditeettiriski)
            if spread_percent > 2.0:
                penalty = min(0.15, (spread_percent - 2.0) * 0.05)  # Max 15% penalty
                candidate.overall_score = max(0.0, candidate.overall_score - penalty)
                
                logger.warning(f"⚠️ Korkea spread: {candidate.symbol} {spread_percent:.1f}% (exit-risk, penalty: -{penalty:.2f})")
                
                # Päivitä metriikka
                from metrics import metrics as global_metrics
                if global_metrics:
                    global_metrics.candidates_filtered_reason.labels(reason="high_spread").inc()
            else:
                logger.debug(f"✅ Spread OK: {candidate.symbol} {spread_percent:.1f}%")
            
            # Tallenna spread extra-dataan
            if not hasattr(candidate, 'extra'):
                candidate.extra = {}
            candidate.extra['spread_percent'] = spread_percent
        
        except Exception as e:
            logger.error(f"Virhe tarkistettaessa spread & slippage: {e}")

    async def _enrich_quick(self, candidate: TokenCandidate) -> None:
        """
        Hae mint/LP/holder/flow -tiedot RPC-apuista
        """
        try:
            # RPC-kutsut käyttäen RPC interfaces
            mint_info = await self.rpc_client.get_mint_info(candidate.mint)
            lp_info = await self.rpc_client.get_lp_info(candidate.mint)
            distribution = await self.rpc_client.get_holder_distribution(candidate.mint, top_n=10)
            flow_stats = await self.rpc_client.get_flow_stats(candidate.mint, window_sec=300)
            
            # Päivitä candidate tiedot
            candidate.mint_authority_renounced = mint_info.renounced_mint
            candidate.freeze_authority_renounced = mint_info.renounced_freeze
            candidate.decimals = mint_info.decimals
            
            candidate.lp_locked = lp_info.locked_or_burned
            candidate.liquidity_usd = lp_info.liquidity_usd
            
            candidate.top10_holder_share = distribution.top_share
            
            candidate.unique_buyers_5m = flow_stats.unique_buyers
            candidate.buy_sell_ratio = flow_stats.buy_sell_ratio
            
            # Cache RPC data
            candidate._rpc_data_cache = {
                "mint_info": mint_info,
                "lp_info": lp_info,
                "distribution": distribution,
                "flow_stats": flow_stats
            }
            
        except Exception as e:
            logger.warning(f"RPC enrichment epäonnistui {candidate.symbol}: {e}")
            
            # Raw fallback: hyödynnä itemistä tulevia vihjeitä
            if (candidate.liquidity_usd or 0) == 0:
                hint = candidate.extra or {}
                candidate.liquidity_usd = float(hint.get("liq_hint") or 0.0)
            if (candidate.top10_holder_share is None) and (candidate.extra and candidate.extra.get("top10_hint") is not None):
                candidate.top10_holder_share = float(candidate.extra["top10_hint"])
            
            # Hyödynnä WS trade-tilastoja jos RPC-liq/top10 puuttuu
            hint = candidate.extra or {}
            if not (candidate.liquidity_usd and candidate.liquidity_usd > 0):
                # jos lähde välitti liq_hintin:
                if hint.get("liq_hint"):
                    candidate.liquidity_usd = float(hint["liq_hint"])
                # kokeile per-mint trade-tilastoja
                st = self._trade_stats.get(candidate.mint)
                if st:
                    # voit johdatella pseudo-liq arviota trade-määrän perusteella (esim. buys*X) tai vain tallentaa pisteytykseen
                    candidate.extra["trade_buys_30s"] = st["buys"]
                    candidate.extra["trade_sells_30s"] = st["sells"]
                    candidate.extra["trade_unique_buyers_30s"] = len(st["unique_buyers"])
            
            # Fallback values
            candidate.mint_authority_renounced = True
            candidate.freeze_authority_renounced = True
            candidate.lp_locked = True
            if (candidate.liquidity_usd or 0) == 0:
                candidate.liquidity_usd = 5000.0
            if candidate.top10_holder_share is None:
                candidate.top10_holder_share = 0.08
            candidate.unique_buyers_5m = 50
            candidate.buy_sell_ratio = 1.2

# Vanhat placeholder metodit poistettu - käytetään RPC interfaces

    def _score(self, candidate: TokenCandidate) -> None:
        """
        Laske kokonaispiste speksin kaavalla
        
        Pisteytys:
        - novelty (ikä min)
        - unique buyers 5m
        - buy/sell-suhde
        - liq_score, dist_score
        - rug_risk vähennys
        """
        # Novelty score (uudempi = parempi) - käytä on-chain aikaleimaa
        age_min = self._age_minutes(candidate)
        if age_min < 5:
            candidate.novelty_score = 1.0
        elif age_min < 15:
            candidate.novelty_score = 0.8
        elif age_min < 60:
            candidate.novelty_score = 0.6
        else:
            candidate.novelty_score = 0.3
        
        # Liquidity score
        if candidate.liquidity_usd >= 10000:
            candidate.liquidity_score = 1.0
        elif candidate.liquidity_usd >= 5000:
            candidate.liquidity_score = 0.8
        else:
            candidate.liquidity_score = 0.6
        
        # Distribution score (parempi jakelu = parempi)
        if candidate.top10_holder_share <= 0.5:
            candidate.distribution_score = 1.0
        elif candidate.top10_holder_share <= 0.7:
            candidate.distribution_score = 0.8
        else:
            candidate.distribution_score = 0.5
        
        # Rug risk score (pienempi riski = parempi)
        rug_risk = 0.0
        
        # Authority risk
        if not (candidate.mint_authority_renounced and candidate.freeze_authority_renounced):
            rug_risk += 0.3
        
        # LP risk
        if not (candidate.lp_locked or candidate.lp_burned):
            rug_risk += 0.2
        
        # Holder concentration risk
        if candidate.top10_holder_share > 0.8:
            rug_risk += 0.2
        
        candidate.rug_risk_score = rug_risk
        
        # Turvallisesti nosta paikalliset muuttujat getattr-defaultteilla
        buys  = int(getattr(candidate, "buys_5m", 0) or 0)
        sells = int(getattr(candidate, "sells_5m", 0) or 0)
        uniq  = int(getattr(candidate, "unique_buyers_5m", 0) or 0)
        total = max(1, buys + sells)
        buy_ratio = buys / total
        
        # Päivitä kentät jos ne puuttuvat ja extra-hintit löytyvät
        if uniq == 0 and (candidate.extra or {}).get("trade_unique_buyers_30s") is not None:
            candidate.unique_buyers_5m = int(candidate.extra["trade_unique_buyers_30s"])
            uniq = candidate.unique_buyers_5m
        if buys == 0 and (candidate.extra or {}).get("trade_buys_30s") is not None:
            candidate.buys_5m = int(candidate.extra["trade_buys_30s"])
            buys = candidate.buys_5m
        if sells == 0 and (candidate.extra or {}).get("trade_sells_30s") is not None:
            candidate.sells_5m = int(candidate.extra["trade_sells_30s"])
            sells = candidate.sells_5m
        
        # Kokonaispiste (0..1) - käytä paikallisia muuttujia
        # Parannettu algoritmi: painota enemmän aktiivisuutta ja turvallisuutta
        base_score = (
            candidate.novelty_score * 0.25 +           # Vähennetty paino
            candidate.liquidity_score * 0.2 +          # Vähennetty paino
            candidate.distribution_score * 0.2 +       # Vähennetty paino
            min(uniq / 50, 1.0) * 0.2 +               # Lisätty paino (50 ostajaa = täysi piste)
            min(buy_ratio / 1.5, 1.0) * 0.15          # Lisätty paino (1.5 ratio = täysi piste)
        )
        
        # Lisää bonus aktiivisille tokeneille
        activity_bonus = 0.0
        if uniq >= 20 and buys >= 20:
            activity_bonus = 0.1  # 10% bonus jos täyttää sniper-ehdot
        elif uniq >= 10 and buys >= 10:
            activity_bonus = 0.05  # 5% bonus jos lähellä sniper-ehtoja
        
        # Lisää momentum-bonus nopeasti kasvaville tokeneille
        momentum_bonus = 0.0
        if age_min and age_min < 2.0:  # Alle 2 minuuttia vanha
            if uniq >= 5:  # Vähintään 5 ostajaa
                momentum_bonus = 0.05  # 5% bonus nopealle kasvulle
        elif age_min and age_min < 5.0:  # Alle 5 minuuttia vanha
            if uniq >= 15:  # Vähintään 15 ostajaa
                momentum_bonus = 0.03  # 3% bonus hyvälle kasvulle
        
        # Vähennä rug risk ja lisää bonukset
        candidate.overall_score = max(0.0, min(1.0, base_score - candidate.rug_risk_score + activity_bonus + momentum_bonus))
        candidate.last_score = candidate.overall_score
        
        logger.debug(f"Pisteytys {candidate.symbol}: novelty={candidate.novelty_score:.2f}, "
                    f"liq={candidate.liquidity_score:.2f}, dist={candidate.distribution_score:.2f}, "
                    f"rug={candidate.rug_risk_score:.2f}, activity_bonus={activity_bonus:.2f}, "
                    f"momentum_bonus={momentum_bonus:.2f}, overall={candidate.overall_score:.3f}")

    def _trim_candidates(self) -> None:
        """Pidä vain parhaat kandidatit"""
        if len(self.processed_candidates) <= self.max_candidates:
            return

        # Järjestä score mukaan ja pidä parhaat
        sorted_candidates = sorted(
            self.processed_candidates.items(),
            key=lambda x: x[1].overall_score,
            reverse=True
        )

        # Pidä vain parhaat
        self.processed_candidates = dict(sorted_candidates[:self.max_candidates])

        logger.debug(f"Trimmed candidates: {len(self.processed_candidates)} remaining")

    def _purge_stale_candidates(self) -> None:
        """Poista liian vanhat kandidatit, jotta sama setti ei jää ikuisesti listalle."""
        ttl = getattr(self, "candidate_ttl_sec", None)
        if not ttl:
            return

        now = time.time()
        removed = 0
        for mint, candidate in list(self.processed_candidates.items()):
            ts = None
            extra = getattr(candidate, "extra", None) or {}
            ts = extra.get("first_pool_ts") or extra.get("first_trade_ts")

            if ts is None:
                last_updated = getattr(candidate, "last_updated", None)
                if isinstance(last_updated, datetime):
                    ts = last_updated.timestamp()

            if ts is None:
                first_seen = getattr(candidate, "first_seen", None)
                if isinstance(first_seen, datetime):
                    ts = first_seen.timestamp()

            if ts is None:
                ts = self.candidate_first_seen.get(mint)

            try:
                ts_val = float(ts) if ts is not None else None
            except (TypeError, ValueError):
                ts_val = None

            if ts_val is None:
                continue

            if now - ts_val >= ttl:
                removed += 1
                self.processed_candidates.pop(mint, None)
                self.candidate_sources.pop(mint, None)
                self.candidate_first_seen.pop(mint, None)
                self._trade_stats.pop(mint, None)
                self.dev_wallet_activity.pop(mint, None)
                self.lp_lock_timing.pop(mint, None)
                self.buyer_acceleration.pop(mint, None)
                self.ws_seen_recently.pop(mint, None)
                self.ws_seen_initial.pop(mint, None)
                self.ws_seen_count.pop(mint, None)

        if removed:
            logger.info("🧹 Poistettiin %d vanhaa kandidaattia (ttl=%.0fs)", removed, ttl)

    def best_candidates(self, k: int = 10, min_score: float = None) -> List[TokenCandidate]:
        """
        Palauta parhaat kandidatit
        
        Args:
            k: Maksimimäärä kandidatteja
            min_score: Minimipiste (jos None, käytä configista)
            
        Returns:
            Lista parhaista kandidateista
        """
        # Siivoa liian vanhat ehdokkaat ennen valintaa
        self._purge_stale_candidates()

        # Käytä dynaamista kynnystä jos min_score ei annettu
        if min_score is None:
            min_score = self._calculate_dynamic_score_threshold()
        
        # Filtteröi minimipisteen mukaan
        filtered = [
            candidate for candidate in self.processed_candidates.values()
            if candidate.overall_score >= min_score
        ]
        
        # Laske ultra-fresh määrä
        ultra_fresh_count = sum(1 for c in filtered if self._is_ultra_fresh(c))
        if ultra_fresh_count > 0:
            logger.info(f"✅ Löydettiin {ultra_fresh_count} ultra-fresh kandidattia")
        
        # Järjestä score mukaan
        sorted_candidates = sorted(
            filtered,
            key=lambda x: x.overall_score,
            reverse=True
        )
        
        # Palauta top-k
        result = sorted_candidates[:k]
        
        logger.info(f"Palautettu {len(result)} kandidattia (min_score={min_score})")
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Hae engine tilastot"""
        return {
            "running": self.running,
            "queue_size": self.candidate_queue.qsize(),
            "processed_candidates": len(self.processed_candidates),
            "active_sources": len([t for t in self.source_tasks if not t.done()]),
            "score_threshold": self.score_threshold,
            "min_liquidity_usd": self.min_liq_usd
        }

# Test function
async def test_discovery_engine():
    """Testaa DiscoveryEngine"""
    logger.info("🧪 Testataan DiscoveryEngine...")
    
    # Mock source
    class MockSource:
        async def start(self): pass
        async def stop(self): pass
        async def get_new_tokens(self) -> List[TokenCandidate]:
            return [
                TokenCandidate(
                    mint="test_mint_1",
                    symbol="TEST1",
                    name="Test Token 1",
                    decimals=6,
                    liquidity_usd=5000.0,
                    top10_holder_share=0.6,
                    age_minutes=2.0
                )
            ]
    
    # Luo engine
    engine = DiscoveryEngine(
        rpc_endpoint="https://api.mainnet-beta.solana.com",
        market_sources=[MockSource()],
        min_liq_usd=3000.0
    )
    
    try:
        # Käynnistä
        await engine.start()
        
        # Odota hetki
        await asyncio.sleep(2)
        
        # Hae parhaat
        best = engine.best_candidates(k=5, min_score=0.5)
        logger.info(f"Parhaat kandidatit: {len(best)}")
        
        for candidate in best:
            logger.info(f"  {candidate.symbol}: {candidate.overall_score:.3f}")
        
    finally:
        await engine.stop()

if __name__ == "__main__":
    asyncio.run(test_discovery_engine())
