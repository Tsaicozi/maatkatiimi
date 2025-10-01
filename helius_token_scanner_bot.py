from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
import os
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, Dict, List, Tuple
import aiohttp
from collections import defaultdict
from position_manager import PositionManager
from balance_manager import BalanceManager

# Telegram-integraatio
# TelegramBot removed - using simple notification system
from scanner_config import ScannerConfig
from circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from prometheus_client import Counter, Histogram, Gauge

# Trading removed - scanner only

# CoinGecko enrichment
try:
    from coingecko_enricher import enrich_token_with_coingecko, CoinGeckoTokenData, CoinGeckoScore
    COINGECKO_ENRICHMENT_AVAILABLE = True
except ImportError:
    COINGECKO_ENRICHMENT_AVAILABLE = False
    enrich_token_with_coingecko = None
    CoinGeckoTokenData = None
    CoinGeckoScore = None

tokens_processed_metric = Counter(
    "scanner_tokens_processed_total",
    "Total number of tokens processed by the scanner",
)
dex_fetch_duration_metric = Histogram(
    "scanner_dex_fetch_duration_seconds",
    "Duration of DEX information fetch calls",
)
queue_size_metric = Gauge(
    "scanner_queue_size",
    "Current depth of the token event queue",
)
memory_usage_metric = Gauge(
    "scanner_memory_usage_entries",
    "Internal scanner structure sizes",
    ["structure"],
)

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
class DexPool:
    pair_id: str
    dex_id: str
    liquidity_usd: float
    volume_h24: float
    price_usd: Optional[float]
    fdv: Optional[float]
    market_cap: Optional[float]
    price_change: Dict[str, float]
    url: Optional[str]
    age_min: int
    trades24h: int
    last_trade_min: int

@dataclass
class DexInfo:
    status: str  # "ok" | "pending" | "error" | "not_found"
    dex_name: str | None = None
    pair_address: str | None = None
    reason: str = ""
    alt_pairs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class _Source:
    """Per-datalähde circuit breaker -kääre."""
    def __init__(self, name: str, fn: Callable[..., Any], cfg: CircuitBreakerConfig):
        self.name = name
        self.fn = fn
        self.breaker = CircuitBreaker(cfg)

    async def call(self, *a, timeout: float = 10.0, **kw) -> Any:
        if self.breaker.is_open():
            raise RuntimeError(f"breaker_open:{self.name}")
        try:
            return await asyncio.wait_for(self.fn(*a, **kw), timeout=timeout)
        except Exception:
            self.breaker.record_failure()
            raise
        else:
            self.breaker.record_success()

class DexInfoFetcher:
    """
    Fallback-ketju DEX-infon hakemiseksi. Järjestys: Birdeye -> DexScreener -> Jupiter -> CoinGecko -> Solscan.
    Tarjoajat injektoidaan, jotta testaus onnistuu ilman verkkoa. Jokaisella tarjoajalla on oma breaker.
    """

    def __init__(
        self,
        *,
        birdeye: Callable[..., Any] | None = None,
        dexscreener: Callable[..., Any] | None = None,
        coingecko: Callable[..., Any] | None = None,
        jupiter: Callable[..., Any] | None = None,
        solscan: Callable[..., Any] | None = None,
        breaker_config: CircuitBreakerConfig | None = None,
        buyers30m_provider: Optional[Callable[[str], asyncio.Future]] = None,
    ) -> None:
        async def _na(mint: str) -> DexInfo:
            return DexInfo(status="not_found", reason="provider_not_configured")

        self._providers: dict[str, Callable[[str], Awaitable[DexInfo]]] = {
            "birdeye": birdeye or _na,
            "dexscreener": dexscreener or _na,
            "jupiter": jupiter or _na,
            "coingecko": coingecko or _na,
            "solscan": solscan or _na,
        }
        cfg = breaker_config or CircuitBreakerConfig()
        self._breakers = {
            "birdeye": CircuitBreaker(cfg),
            "dexscreener": CircuitBreaker(cfg),
            "jupiter": CircuitBreaker(cfg),
            "coingecko": CircuitBreaker(cfg),
            "solscan": CircuitBreaker(cfg),
        }
        self._sources = {
            "birdeye": _Source("birdeye", birdeye or _na, cfg),
            "dexscreener": _Source("dexscreener", dexscreener or _na, cfg),
            "coingecko": _Source("coingecko", coingecko or _na, cfg),
            "jupiter": _Source("jupiter", jupiter or _na, cfg),
            "solscan": _Source("solscan", solscan or _na, cfg),
        }
        self._buyers_provider = buyers30m_provider

    async def _call_provider(
        self,
        name: str,
        fn: Callable[[str], Awaitable[DexInfo]],
        mint: str,
        timeout: float,
        reason_chain: list[str],
    ) -> Optional[DexInfo]:
        breaker = self._breakers[name]
        if not breaker.allow_request():
            reason_chain.append(f"{name}=circuit_open")
            return None
        try:
            result = await asyncio.wait_for(fn(mint), timeout=timeout)
        except asyncio.TimeoutError:
            breaker.record_failure()
            reason_chain.append(f"{name}=timeout")
            return None
        except Exception as exc:  # pragma: no cover - kattava fallback
            breaker.record_failure()
            reason_chain.append(f"{name}=error:{exc}")
            return None
        breaker.record_success()
        return result

    async def fetch(self, mint: str, *, timeout: float = 10.0) -> DexInfo:
        reason_chain: list[str] = []
        success_info: Optional[DexInfo] = None

        async def _attempt(name: str) -> Optional[DexInfo]:
            provider = self._providers[name]
            return await self._call_provider(name, provider, mint, timeout, reason_chain)

        # 1) Birdeye
        r = await _attempt("birdeye")
        if r and r.status == "ok":
            # Tarkista onko Birdeye-data riittävää
            metadata = r.metadata or {}
            liquidity = metadata.get("liquidity_usd", 0)
            volume = metadata.get("volume_24h_usd", 0)
            
            # Jos Birdeye ei anna likviditeettiä tai volyymiä, kokeile DexScreener:ia
            if liquidity == 0 and volume == 0:
                reason_chain.append(f"birdeye=insufficient_data")
                # Jatka DexScreener:iin
            else:
                r.reason = r.reason or "birdeye_ok"
                success_info = r
        elif r and r.reason:
            reason_chain.append(f"birdeye={r.reason}")

        # 2) DexScreener
        if success_info is None:
            r = await _attempt("dexscreener")
            if r and r.status == "ok":
                r.reason = r.reason or "dexscreener_ok"
                success_info = r
            elif r and r.reason:
                reason_chain.append(f"dexscreener={r.reason}")
                # DS 404 ei ole kovaportti - jatka muihin lähteisiin

        # 3) Jupiter
        if success_info is None:
            r = await _attempt("jupiter")
            if r and r.status == "ok":
                r.reason = r.reason or "jupiter_ok"
                success_info = r
            elif r and r.reason:
                reason_chain.append(f"jupiter={r.reason}")

        # 4) CoinGecko
        if success_info is None:
            r = await _attempt("coingecko")
            if r and r.status == "ok":
                r.reason = r.reason or "coingecko_ok"
                success_info = r
            elif r and r.reason:
                reason_chain.append(f"coingecko={r.reason}")
        
        # 4.5) CoinGecko Enrichment (if we have basic data)
        if success_info and COINGECKO_ENRICHMENT_AVAILABLE:
            try:
                cg_data, cg_score = await enrich_token_with_coingecko(mint, success_info.metadata)
                if cg_data and cg_score.total_score > 0:
                    # Enrich the existing data
                    if cg_data.symbol and cg_data.name:
                        success_info.metadata["coingecko_symbol"] = cg_data.symbol
                        success_info.metadata["coingecko_name"] = cg_data.name
                        success_info.metadata["coingecko_logo"] = cg_data.logo_url
                    
                    # Add social links
                    if cg_data.homepage_url:
                        success_info.metadata["homepage_url"] = cg_data.homepage_url
                    if cg_data.twitter_url:
                        success_info.metadata["twitter_url"] = cg_data.twitter_url
                    
                    # Add market data
                    if cg_data.ath_usd:
                        success_info.metadata["ath_usd"] = cg_data.ath_usd
                    if cg_data.ath_change_percentage:
                        success_info.metadata["ath_change_percentage"] = cg_data.ath_change_percentage
                    
                    # Add scoring bonuses
                    success_info.metadata["coingecko_score"] = cg_score.total_score
                    success_info.metadata["coingecko_bonuses"] = {
                        "symbol_resolution": cg_score.symbol_resolution_bonus,
                        "confluence": cg_score.confluence_bonus,
                        "trending": cg_score.trending_bonus,
                        "recently_added": cg_score.recently_added_bonus,
                        "tradability": cg_score.tradability_bonus,
                        "social": cg_score.social_bonus
                    }
                    
                    # Update reason with CG confirmation
                    if cg_score.has_official_symbol:
                        success_info.reason += "+CG_verified"
                    
                    logger.info(f"CoinGecko enrichment for {mint}: +{cg_score.total_score} points")
            except Exception as e:
                logger.error(f"CoinGecko enrichment error for {mint}: {e}")

        # 5) Solscan
        if success_info is None:
            r = await _attempt("solscan")
            if r and r.status == "ok":
                r.reason = r.reason or "solscan_ok"
                success_info = r
            elif r and r.reason:
                reason_chain.append(f"solscan={r.reason}")

        if success_info:
            if self._buyers_provider:
                buyers_value: Optional[int] = None
                try:
                    buyers_value = await asyncio.wait_for(
                        self._buyers_provider(mint), timeout=timeout
                    )
                except Exception:
                    buyers_value = None
                if buyers_value is not None:
                    success_info.metadata = success_info.metadata or {}
                    success_info.metadata.setdefault("buyers_30m", buyers_value)
            return success_info

        return DexInfo(status="pending", dex_name=None, pair_address=None, reason=";".join(reason_chain) or "all_failed")


    @staticmethod
    def _active_pool(p: DexPool, cfg: ScannerConfig) -> bool:
        return (
            p.trades24h >= cfg.pool_min_trades24h
            and p.last_trade_min <= cfg.pool_max_last_trade_min
            and p.age_min >= cfg.pool_min_age_min
        )

    @staticmethod
    def score_pool(p: DexPool) -> float:
        liq = max(p.liquidity_usd or 0.0, 1.0)
        vol = max(p.volume_h24 or 0.0, 0.0)
        recent = 1.0 if (p.last_trade_min or 999) <= 10 else 0.0
        age_ok = 1.0 if (p.age_min or 0) >= 30 else 0.0
        return 0.7*(liq**0.5) + 0.25*math.log1p(vol) + 5.0*recent + 3.0*age_ok

    @staticmethod
    def pick_primary_pool(pools: List[DexPool], cfg: ScannerConfig) -> Optional[DexPool]:
        actives = [p for p in pools if DexInfoFetcher._active_pool(p, cfg)]
        if actives:
            return max(actives, key=DexInfoFetcher.score_pool)
        if not cfg.enforce_active_pool and pools:
            return max(pools, key=DexInfoFetcher.score_pool)
        return None


class HeliusTokenScannerBot:
    """
    Helius WS -pohjainen uuden tokenin skanneri (producer) + kuluttaja-queue (consumer).

    - INFO-tason kuluttaja-start -loki
    - `dex_reason` on aina alustettu, jotta summary-lokitus ei koskaan kaadu
    - Fallback: Birdeye -> DexScreener -> Jupiter -> CoinGecko -> Solscan
    - Siisti sammutus (cancel, queue sentinel)
    """

    def __init__(
        self,
        *,
        ws_url: str,
        programs: list[str] | None = None,
        dex_fetcher: DexInfoFetcher | None = None,
        queue_maxsize: int = 1000,
        rpc_get_tx: Callable[[str], Awaitable[dict]] | None = None,
        config: ScannerConfig | None = None,
    ) -> None:
        self.ws_url = ws_url
        self.programs = programs or ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"]
        self._config = config or ScannerConfig()
        if dex_fetcher is not None:
            self.dex_fetcher = dex_fetcher
        else:
            breaker_cfg = CircuitBreakerConfig(
                failure_threshold=self._config.breaker_failure_threshold,
                timeout=self._config.breaker_timeout,
            )
            self.dex_fetcher = DexInfoFetcher(breaker_config=breaker_cfg)
        self._stop = asyncio.Event()
        self._queue: asyncio.Queue[NewTokenEvent | object] = asyncio.Queue(maxsize=queue_maxsize)
        self._producer_task: asyncio.Task | None = None
        self._consumer_task: asyncio.Task | None = None
        self._sentinel: object = object()
        self._rpc_get_tx = rpc_get_tx
        self._retry_tasks: dict[str, asyncio.Task] = {}
        self._max_retry_attempts = self._config.max_retry_attempts
        self._retry_initial_delay = self._config.retry_initial_delay
        self._retry_backoff = self._config.retry_backoff
        
        # Telegram bot for scanner notifications
        self.telegram_bot: Optional[Any] = None
        
        # Trading integration
        self.trader = None
        self.trade_cfg = None
        self._last_trade_ts: dict = {}
        self._open_positions: dict = {}  # Track open positions: {mint: {entry_price, entry_time, entry_volume, entry_liquidity}}
        self._positions_file = "open_positions.json"  # File to persist positions
        self._wallet_report_task: asyncio.Task | None = None
        
        # New position and balance management
        self.positions = PositionManager(path=os.getenv("POSITIONS_PATH", "open_positions.json"))
        self.balance_mgr = None  # Will be set when trader is initialized
        self._wallet_report_interval = 7200  # 2 hours in seconds
        # Per-mint cooldown (2-3 min TG:lle)
        self._telegram_cooldown: dict[str, float] = {}
        self._cooldown_duration = 180.0  # 3 minuuttia
        
        # Load existing positions on startup
        self._load_positions()
        
        # Force sell all positions on startup to get cash back
        self._force_sell_all_on_startup = True
        # Pair failover tracking
        self._published_pairs: dict[str, str] = {}  # mint -> pair_id
        self._retry_max_delay = self._config.retry_max_delay
        self._retry_fetch_timeout = self._config.retry_fetch_timeout
        self._liquidity_history: dict[str, list[tuple[float, float]]] = {}
        self._blacklisted_until: dict[str, float] = {}
        self._cleanup_task: asyncio.Task | None = None
        
        # Symbol retry worker
        self._symbol_retry_queue: asyncio.Queue[str] = asyncio.Queue()
        self._symbol_retry_task: asyncio.Task | None = None
        self._symbol_retry_schedule = [30, 120, 300, 900, 1800]  # seconds
        self._min_symbol_confidence = 0.7
        self._placeholder_penalty = 10
        self._resolved_symbols: dict[str, tuple[str, float]] = {}  # mint -> (symbol, confidence)
        
        # Diagnostics metrics
        self._symbol_resolution_times: dict[str, float] = {}  # mint -> resolution_time
        self._symbols_resolved_total = 0
        self._placeholder_upgraded_total = 0
        self._dex_pending_to_live_times: dict[str, float] = {}  # mint -> time_to_live
        
        self._cleanup_interval = self._config.memory_cleanup_interval
        self._liquidity_ttl = self._config.liquidity_history_ttl
        self._start_time = time.time()

        # Telegram-botti ilmoituksille
        self.telegram_bot = None
        
        # Uusi: ulkoisten parikandidaattien syöttö
        self._candidate_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    # --- UUSI: ulkoisten parikandidaattien syöttö ---
    async def submit_pair_candidate(self, mint: str, source: str = "external", meta: dict | None = None):
        """
        Luo TokenCandidate pair-first -löydöstä ja syötä botin putkeen.
        Jos teillä on eri jonon nimi, vaihda alla `self._candidate_queue` -> teidän jono.
        """
        candidate = {
            "type": "pair",
            "mint": mint,
            "source": source,
            "meta": meta or {},
        }
        # Oletusjono; muuta tarvittaessa
        await self._candidate_queue.put(candidate)

    # --- Public API ---
    async def start(self) -> None:
        if self._producer_task or self._consumer_task:
            return
        # Kuluttaja start INFO-tasolla – korjaus
        self._ensure_consumer_started()
        # Tuottaja voidaan käynnistää myöhemmin testeissä; jos WS:ää ei ole, ohita
        if websockets and hasattr(websockets, "connect"):
            self._producer_task = asyncio.create_task(self._producer_loop(), name="helius_producer")
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop(), name="cleanup_loop")
        
        # Käynnistä vanhempien tokenien skannaus (ajastettu)
        if not hasattr(self, '_older_tokens_task') or self._older_tokens_task.done():
            self._older_tokens_task = asyncio.create_task(self._older_tokens_loop(), name="older_tokens_scanner")
        
        # Käynnistä status update loop (30 min välein)
        if not hasattr(self, '_status_update_task') or self._status_update_task.done():
            self._status_update_task = asyncio.create_task(self._status_update_loop(), name="status_update_loop")
        
        # Käynnistä symbol retry worker
        if not self._symbol_retry_task or self._symbol_retry_task.done():
            self._symbol_retry_task = asyncio.create_task(self._symbol_retry_worker(), name="symbol_retry_worker")
        
        # Käynnistä wallet report worker (2h välein)
        if not self._wallet_report_task or self._wallet_report_task.done():
            self._wallet_report_task = asyncio.create_task(self._wallet_report_worker(), name="wallet_report_worker")
        
        # Force sell all positions on startup if enabled
        if getattr(self, '_force_sell_all_on_startup', False):
            logger.info("🔄 Force selling all positions on startup...")
            await self._force_sell_all_positions()
            self._force_sell_all_on_startup = False  # Only do this once

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
        # peruuta retry-tehtävät
        retry_tasks = list(self._retry_tasks.values())
        for task in retry_tasks:
            task.cancel()
        if retry_tasks:
            await asyncio.gather(*retry_tasks, return_exceptions=True)
        self._retry_tasks.clear()
        # peruuta vanhempien tokenien skannaus
        if hasattr(self, '_older_tokens_task') and self._older_tokens_task and not self._older_tokens_task.done():
            self._older_tokens_task.cancel()
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
        # odota tehtävät
        tasks_to_wait = [self._producer_task, self._consumer_task]
        if hasattr(self, '_older_tokens_task') and self._older_tokens_task:
            tasks_to_wait.append(self._older_tokens_task)
        await asyncio.gather(
            *[t for t in tasks_to_wait if t],
            return_exceptions=True,
        )

    async def _lookback_sweep(self):
        """Lookback sweep for missed tokens"""
        while not self._shutdown:
            try:
                await asyncio.sleep(60)  # 1 minute intervals
                
                # Get recent pools from DexScreener
                recent_pools = await self._get_recent_pools()
                if recent_pools:
                    logger.info(f"Lookback sweep found {len(recent_pools)} recent pools")
                    
                    for pool in recent_pools:
                        if pool.get("pairAddress"):
                            await self.submit_pair_candidate(
                                pool["pairAddress"], 
                                source="lookback_sweep",
                                meta=pool
                            )
                
                # CoinGecko recently added sweep
                if COINGECKO_ENRICHMENT_AVAILABLE:
                    try:
                        from coingecko_enricher import get_coingecko_enricher
                        enricher = await get_coingecko_enricher()
                        recently_added = await enricher.get_recently_added_coins(limit=20)
                        
                        if recently_added:
                            logger.info(f"CoinGecko lookback found {len(recently_added)} recently added coins")
                            
                            for coin in recently_added:
                                if coin.get("mint"):
                                    await self.submit_pair_candidate(
                                        coin["mint"],
                                        source="coingecko_recently_added",
                                        meta=coin
                                    )
                    except Exception as e:
                        logger.error(f"CoinGecko lookback sweep error: {e}")
                        
            except Exception as e:
                logger.error(f"Lookback sweep error: {e}")
                await asyncio.sleep(30)

    async def _status_update_loop(self):
        """30-minute status update loop"""
        while not self._shutdown:
            try:
                await asyncio.sleep(1800)  # 30 minutes
                
                # Get scanner stats
                scanner_stats = {
                    "tokens_processed": self.tokens_processed_metric._value._value,
                    "queue_size": self._processing_queue.qsize(),
                    "uptime": time.time() - self._start_time if hasattr(self, '_start_time') else 0
                }
                
                # Send status update
                if self.telegram_bot and self.telegram_bot.enabled:
                    message = f"📊 **Scanner Status Update**\n\n⏱️ **Uptime:** {scanner_stats['uptime']/3600:.1f}h\n🔍 **Processed:** {scanner_stats['tokens_processed']}\n📋 **Queue:** {scanner_stats['queue_size']}"
                    await self.telegram_bot.send_message(message)
                
                logger.info("Status update sent to Telegram")
                
            except Exception as e:
                logger.error(f"Status update loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry

    async def _symbol_retry_worker(self):
        """Background worker to resolve placeholder symbols"""
        logger.info("🔄 Symbol retry worker started")
        
        while not self._stop.is_set():
            try:
                # Wait for mint to retry
                mint = await asyncio.wait_for(self._symbol_retry_queue.get(), timeout=1.0)
                
                # Try to resolve symbol with retry schedule
                for delay in self._symbol_retry_schedule:
                    if self._stop.is_set():
                        break
                        
                    try:
                        symbol, confidence = await self._resolve_symbol_from_sources(mint)
                        if symbol and confidence >= self._min_symbol_confidence:
                            # Track resolution time
                            resolution_time = time.time()
                            self._symbol_resolution_times[mint] = resolution_time
                            self._symbols_resolved_total += 1
                            self._placeholder_upgraded_total += 1
                            
                            # Update resolved symbol
                            self._resolved_symbols[mint] = (symbol, confidence)
                            
                            # Send Telegram update
                            await self._send_symbol_update(mint, symbol, confidence)
                            
                            # Check for confluence updates
                            await self._check_confluence_update(mint)
                            
                            logger.info(f"✅ Symbol resolved: {mint[:8]} → {symbol} (conf: {confidence:.2f})")
                            break
                            
                    except Exception as e:
                        logger.debug(f"Symbol resolution attempt failed for {mint[:8]}: {e}")
                    
                    # Wait before next attempt
                    await asyncio.sleep(delay)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Symbol retry worker error: {e}")
                await asyncio.sleep(5)
        
        logger.info("🔄 Symbol retry worker stopped")

    async def _resolve_symbol_from_sources(self, mint: str) -> tuple[str, float]:
        """Resolve symbol from multiple sources with confidence scoring"""
        try:
            # Try DexScreener first
            dex_info = await self.dex_fetcher.fetch_dex_info(mint)
            if dex_info and dex_info.status == "ok":
                # Try to get symbol from DexScreener data
                if hasattr(dex_info, 'raw_data') and dex_info.raw_data:
                    ds_data = dex_info.raw_data.get('dexscreener', {})
                    if ds_data and ds_data.get('status') == 'ok':
                        pairs = ds_data.get('pairs', [])
                        if pairs:
                            base_token = pairs[0].get('baseToken', {})
                            symbol = base_token.get('symbol')
                            if symbol and not symbol.startswith('TOKEN_'):
                                return symbol, 0.8
            
            # Try Birdeye
            if hasattr(dex_info, 'raw_data') and dex_info.raw_data:
                be_data = dex_info.raw_data.get('birdeye', {})
                if be_data and be_data.get('status') == 'ok':
                    symbol = be_data.get('symbol')
                    if symbol and not symbol.startswith('TOKEN_'):
                        return symbol, 0.7
            
            # Try CoinGecko contract endpoint
            if COINGECKO_ENRICHMENT_AVAILABLE:
                try:
                    cg_data = await enrich_token_with_coingecko(mint)
                    if cg_data and cg_data.symbol:
                        return cg_data.symbol, 0.9  # High confidence for CoinGecko
                except Exception:
                    pass
            
            # Try Jupiter
            if hasattr(dex_info, 'raw_data') and dex_info.raw_data:
                jup_data = dex_info.raw_data.get('jupiter', {})
                if jup_data and jup_data.get('status') == 'ok':
                    symbol = jup_data.get('symbol')
                    if symbol and not symbol.startswith('TOKEN_'):
                        return symbol, 0.6
            
        except Exception as e:
            logger.debug(f"Symbol resolution error for {mint[:8]}: {e}")
        
        return "", 0.0

    async def _send_symbol_update(self, mint: str, symbol: str, confidence: float):
        """Send Telegram update for resolved symbol"""
        try:
            if not self.telegram_bot or not self.telegram_bot.enabled:
                return
            
            message = f"✏️ **Symbol päivitetty**\n\n🪙 **Token:** `{mint[:8]}...{mint[-8:]}`\n📛 **Symbol:** {symbol}\n🎯 **Confidence:** {confidence:.1%}"
            
            await self.telegram_bot.send_message(message)
            logger.info(f"📱 Symbol update sent to Telegram: {mint[:8]} → {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to send symbol update: {e}")

    async def _check_confluence_update(self, mint: str):
        """Check and send confluence update if multiple sources now available"""
        try:
            if not self.telegram_bot or not self.telegram_bot.enabled:
                return
            
            # Re-fetch DEX info to check for new sources
            dex_info = await self.dex_fetcher.fetch_dex_info(mint)
            if not dex_info:
                return
            
            # Count available sources
            sources = []
            if hasattr(dex_info, 'raw_data') and dex_info.raw_data:
                if dex_info.raw_data.get('birdeye', {}).get('status') == 'ok':
                    sources.append("BE ✅")
                if dex_info.raw_data.get('dexscreener', {}).get('status') == 'ok':
                    sources.append("DS ✅")
                if dex_info.raw_data.get('jupiter', {}).get('status') == 'ok':
                    sources.append("JUP ✅")
            
            # Check CoinGecko
            if mint in self._resolved_symbols:
                sources.append("CG ✅")
            
            # Send update if we have multiple sources
            if len(sources) >= 2:
                confluence_text = " | ".join(sources)
                message = f"🔄 **Confluence Update**\n\n🪙 **Token:** `{mint[:8]}...{mint[-8:]}`\n📊 **Sources:** {confluence_text}"
                
                await self.telegram_bot.send_message(message)
                logger.info(f"📱 Confluence update sent: {mint[:8]} - {confluence_text}")
                
        except Exception as e:
            logger.error(f"Failed to send confluence update: {e}")

    def _calculate_token_age(self, metadata: dict) -> float:
        """Calculate token age in minutes"""
        try:
            # Try to get creation time from metadata
            pair_created_at = metadata.get("pair_created_at")
            if pair_created_at:
                ts = float(pair_created_at)
                if ts > 1e12:  # Convert from milliseconds
                    ts /= 1000.0
                age_minutes = max(0.0, (time.time() - ts) / 60.0)
                return age_minutes
            
            # Fallback: assume very new if no timestamp
            return 0.0
            
        except (TypeError, ValueError):
            return 0.0

    def get_diagnostics_metrics(self) -> dict:
        """Get diagnostics metrics for monitoring"""
        try:
            # Calculate P50/P90 resolution times
            resolution_times = list(self._symbol_resolution_times.values())
            if resolution_times:
                resolution_times.sort()
                p50_idx = int(len(resolution_times) * 0.5)
                p90_idx = int(len(resolution_times) * 0.9)
                p50_time = resolution_times[p50_idx] if p50_idx < len(resolution_times) else 0
                p90_time = resolution_times[p90_idx] if p90_idx < len(resolution_times) else 0
            else:
                p50_time = p90_time = 0
            
            return {
                "symbols_resolved_total": self._symbols_resolved_total,
                "placeholder_upgraded_total": self._placeholder_upgraded_total,
                "symbol_resolution_p50_seconds": p50_time,
                "symbol_resolution_p90_seconds": p90_time,
                "active_retry_queue_size": self._symbol_retry_queue.qsize(),
                "resolved_symbols_count": len(self._resolved_symbols),
                "dex_pending_to_live_count": len(self._dex_pending_to_live_times)
            }
        except Exception as e:
            logger.error(f"Failed to get diagnostics metrics: {e}")
            return {}

    async def graceful_shutdown(self, timeout: float = 30.0) -> None:
        try:
            await asyncio.wait_for(self.stop(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Graceful shutdown timeout; forcing cancellation")
            tasks = [
                self._producer_task,
                self._consumer_task,
                self._cleanup_task,
                *self._retry_tasks.values(),
            ]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            await asyncio.gather(
                *[t for t in tasks if t],
                return_exceptions=True,
            )

    # Testiystävällinen injektointi
    async def enqueue(self, event: NewTokenEvent) -> None:
        # Varmista että kuluttaja on käynnissä, vaikka start() olisi jäänyt kutsumatta
        self._ensure_consumer_started()
        await self._queue.put(event)

    def _ensure_consumer_started(self) -> None:
        if not self._consumer_task or self._consumer_task.done() or self._consumer_task.cancelled():
            self._consumer_task = asyncio.create_task(self._consume_queue(), name="helius_consumer")
            logger.info("📥 _consume_queue käynnistyi")

    # --- Internal ---
    async def _producer_loop(self) -> None:  # pragma: no cover - tuotantopolku
        backoff = 1.0
        while not self._stop.is_set():
            try:
                # Lisää ping_interval ja ping_timeout WebSocket yhteysasetuksiin
                async with websockets.connect(
                    self.ws_url, 
                    ping_interval=20,  # Ping 20s välein
                    ping_timeout=10,   # 10s timeout pingille
                    close_timeout=10   # 10s timeout sulkemiselle
                ) as ws:  # type: ignore
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
                    last_ping = time.time()
                    
                    while not self._stop.is_set():
                        try:
                            # Käytä asyncio.wait_for timeoutin kanssa
                            msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        except asyncio.TimeoutError:
                            # Lähetä ping jos ei ole saatu viestiä 30s
                            if time.time() - last_ping > 30:
                                try:
                                    await ws.ping()
                                    last_ping = time.time()
                                    logger.debug("📡 Helius WS: ping lähetetty")
                                except Exception as ping_e:
                                    logger.warning("⚠️ Helius WS: ping epäonnistui: %s", ping_e)
                                    break
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            logger.info("🔌 Helius WS: yhteys suljettu")
                            break
                            
                        try:
                            data = json.loads(msg)
                        except Exception:
                            continue
                        params = data.get("params", {})
                        # Subscription confirmation
                        if "result" in data and isinstance(data["result"], str):
                            logger.info("✅ Helius WS: subscription confirmed: %s", data["result"][:8] + "…")
                            continue
                        value = (params.get("result") or {}).get("value") if isinstance(params, dict) else None
                        if not value:
                            continue
                        logs = value.get("logs") or []
                        sig = value.get("signature")
                        mint = await self._try_extract_mint(logs, sig)
                        if not mint:
                            continue
                        # Varmista että kuluttaja käy
                        self._ensure_consumer_started()
                        ev = NewTokenEvent(mint=mint, symbol=f"TOKEN_{mint[:6]}", name=f"New Token {mint[:4]}", signature=sig)
                        with contextlib.suppress(asyncio.QueueFull):
                            self._queue.put_nowait(ev)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Hiljennä melua: INFO ja progressiivinen backoff 15→30→60s
                logger.info("Helius WS hiccup: %s", e)
                await asyncio.sleep(min(60.0, max(15.0, backoff)))
                backoff = min(60.0, max(15.0, backoff * 2.0))

    async def _consume_queue(self) -> None:
        try:
            while not self._stop.is_set():
                item = await self._queue.get()
                queue_size_metric.set(self._queue.qsize())
                if item is self._sentinel:
                    break
                if not isinstance(item, NewTokenEvent):
                    continue

                dex_status = "pending"
                dex_reason = "unknown"  # turvallinen alustaminen – korjaus
                dex_name: str | None = None
                pair: str | None = None
                try:
                    start_fetch = time.perf_counter()
                    info = await self.dex_fetcher.fetch(
                        item.mint,
                        timeout=self._retry_fetch_timeout,
                    )
                    dex_fetch_duration_metric.observe(time.perf_counter() - start_fetch)
                    dex_status = info.status or "pending"
                    dex_reason = info.reason or ""
                    dex_name = info.dex_name
                    pair = info.pair_address
                    alt_pairs = info.alt_pairs or []
                    metadata = info.metadata or {}
                    liquidity_val = self._extract_liquidity(metadata)
                    
                        
                except Exception as e:
                    dex_status = "error"
                    dex_reason = f"fetch_failed:{e}"
                    alt_pairs = []
                    metadata = {}
                    liquidity_val = None

                rug_alert = False
                if liquidity_val is not None:
                    rug_alert = self._check_liquidity_drop(item.mint, liquidity_val)

                blacklisted = self._is_blacklisted(item.mint) or rug_alert

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
                    "alt_pairs": alt_pairs,
                    "metadata": metadata,
                }
                if liquidity_val is not None:
                    summary["liquidity_usd"] = liquidity_val
                if rug_alert:
                    summary["rug_alert"] = True
                    summary["dex_reason"] = (summary["dex_reason"] + ";rug_alert") if summary["dex_reason"] else "rug_alert"
                    summary["blacklisted_until"] = self._blacklisted_until.get(item.mint)
                    logger.warning(
                        "🚨 RUG ALERT: %s (liquidity drop detected)", item.mint[:8]
                    )
                elif blacklisted:
                    summary["blacklisted_until"] = self._blacklisted_until.get(item.mint)

                decision, score, decision_notes = self._decide_candidate(
                    summary,
                    rug_alert=rug_alert,
                    blacklisted=blacklisted,
                )
                summary["score"] = score
                summary["decision"] = decision
                summary["decision_notes"] = decision_notes

                logger.info(json.dumps(summary, ensure_ascii=False))

                notes = self._build_notes(
                    summary,
                    rug_alert=rug_alert,
                    blacklisted=blacklisted,
                    extra_notes=decision_notes,
                )

                if decision == "publish":
                    await self._send_telegram_notification(summary)
                    # Try auto-trade after sending notification
                    await self._maybe_auto_trade(summary)
                    
                    # Check if we should sell any existing positions
                    await self._check_and_sell_positions(summary)
                else:
                    self._append_reject(summary)
                    if not blacklisted and summary.get("dex_status") != "ok":
                        self._schedule_retry(item, summary)

                self._write_jsonl_entry(
                    summary,
                    decision=decision,
                    score=score,
                    notes=notes,
                )
                tokens_processed_metric.inc()
        except Exception as e:
            logger.error("💥 consumer task kaatui: %s", e)

    async def _send_telegram_notification(self, summary: dict) -> None:
        """Lähetä Telegram-ilmoitus uudesta tokenista"""
        try:
            if not self.telegram_bot.enabled:
                return
            
            # Luo viesti tokenista
            mint = summary.get("mint", "")
            symbol = summary.get("symbol", "")
            dex_status = summary.get("dex_status", "")
            dex_name = summary.get("dex", "")
            pair = summary.get("pair", "")
            source = summary.get("source", "")
            metadata = summary.get("metadata", {}) or {}

            if dex_status != "ok":
                logger.debug(
                    "Skip Telegram notify for %s – dex_status=%s",
                    mint[:8],
                    dex_status,
                )
                return

            liquidity = None
            volume = None
            buyers30 = None
            pair_created_at = None

            try:
                if metadata.get("liquidity_usd") is not None:
                    liquidity = float(metadata["liquidity_usd"])
            except (TypeError, ValueError):
                liquidity = None

            try:
                if metadata.get("volume_24h_usd") is not None:
                    volume = float(metadata["volume_24h_usd"])
            except (TypeError, ValueError):
                volume = None

            try:
                if metadata.get("buyers_30m") is not None:
                    buyers30 = int(metadata["buyers_30m"])
            except (TypeError, ValueError):
                buyers30 = None

            try:
                if metadata.get("pair_created_at") is not None:
                    pair_created_at = float(metadata["pair_created_at"])
            except (TypeError, ValueError):
                pair_created_at = None

            util_text = "n/a"
            if liquidity and liquidity > 0 and volume is not None:
                util_val = volume / liquidity if liquidity else None
                if util_val is not None:
                    util_text = f"{util_val:.1f}"

            buyers_text = "n/a" if buyers30 is None else str(buyers30)

            age_text = "n/a"
            if pair_created_at:
                ts = pair_created_at
                if ts > 1e12:
                    ts /= 1000.0
                age_min = max(0.0, (time.time() - ts) / 60.0)
                age_text = f"{age_min:.0f}m"

            # Määritä status emoji
            status_emoji = {
                "ok": "✅",
                "pending": "⏳", 
                "error": "❌",
                "not_found": "🚫"
            }.get(dex_status, "❓")
            
            # Lisää puuttuvat kentät
            # TH (Top Holders)
            th_text = "n/a"
            if isinstance(metadata.get("holders"), dict):
                top5_pct = metadata["holders"].get("top5_pct_list", [])
                if len(top5_pct) >= 5:
                    th_values = [f"{pct:.1f}" for pct in top5_pct[:5]]
                    th_sum = sum(top5_pct[:5])
                    th_text = f"{'|'.join(th_values)} [{th_sum:.0f}%]"
            
            # Fresh 1D/7D
            fresh_text = "n/a"
            if isinstance(metadata.get("holders"), dict):
                fresh1d = metadata["holders"].get("fresh1d_pct", 0)
                fresh7d = metadata["holders"].get("fresh7d_pct", 0)
                fresh_text = f"1D: {fresh1d:.0f}% | 7D: {fresh7d:.0f}%"
            
            # ATH/Δ
            ath_text = "n/a"
            if metadata.get("ath_usd"):
                ath_price = float(metadata["ath_usd"])
                current_price = float(metadata.get("price_usd", 0))
                if current_price > 0:
                    ath_change = ((current_price - ath_price) / ath_price) * 100
                    ath_text = f"ATH ${ath_price:.4f} ({ath_change:+.1f}%)"
            
            # Confluence badges
            confluence_badges = []
            dex_reason = summary.get("dex_reason", "")
            if "coingecko" in dex_reason and "ok" in dex_reason:
                confluence_badges.append("CG ✅")
            if "dexscreener" in dex_reason and "ok" in dex_reason:
                confluence_badges.append("DS ✅")
            if "birdeye" in dex_reason and "ok" in dex_reason:
                confluence_badges.append("BE ✅")
            
            confluence_text = " | ".join(confluence_badges) if confluence_badges else "n/a"
            
            # Luo viesti
            message = f"""🆕 **Uusi Token Löydetty!**

{status_emoji} **Status:** {dex_status.upper()}
🪙 **Token:** `{mint[:8]}...{mint[-8:]}`
📛 **Symbol:** {symbol or "N/A"}
🏪 **DEX:** {dex_name or "N/A"}
💱 **Pair:** {pair or "N/A"}
📡 **Lähde:** {source}

⚙️ util={util_text} | buyers30m={buyers_text} | age={age_text}
📊 **TH:** {th_text}
🆕 **Fresh:** {fresh_text}
📈 **ATH/Δ:** {ath_text}
✅ **Confluence:** {confluence_text}

🔗 **Linkit:**
• [DexScreener](https://dexscreener.com/solana/{mint})
• [Solscan](https://solscan.io/token/{mint})
• [Jupiter](https://jup.ag/swap/SOL-{mint})"""
            
            # Lähetä vain jos status on "ok" tai "pending" (ei virheitä)
            if dex_status in ["ok", "pending"]:
                await self.telegram_bot.send_message(message)
                logger.debug(f"📱 Telegram-ilmoitus lähetetty tokenista: {mint[:8]}...")
            
        except Exception as e:
            logger.warning(f"⚠️ Telegram-ilmoituksen lähetys epäonnistui: {e}")

    def _schedule_retry(self, event: NewTokenEvent, summary: dict) -> None:
        if self._max_retry_attempts <= 0 or self._stop.is_set():
            return
        status = summary.get("dex_status")
        if status == "ok":
            return
        if status not in {"pending", "error", "not_found"}:
            return
        if self._is_blacklisted(event.mint):
            return
        if event.mint in self._retry_tasks and not self._retry_tasks[event.mint].done():
            return
        task = asyncio.create_task(
            self._retry_fetch(event),
            name=f"dex_retry:{event.mint[:8]}",
        )
        self._retry_tasks[event.mint] = task

    async def _retry_fetch(self, event: NewTokenEvent) -> None:
        attempt = 1
        delay = self._retry_initial_delay
        success = False
        try:
            if self._is_blacklisted(event.mint):
                return
            while not self._stop.is_set() and attempt <= self._max_retry_attempts:
                await asyncio.sleep(delay)
                if self._stop.is_set():
                    break

                try:
                    start_fetch = time.perf_counter()
                    info = await self.dex_fetcher.fetch(event.mint, timeout=self._retry_fetch_timeout)
                    dex_fetch_duration_metric.observe(time.perf_counter() - start_fetch)
                    status = info.status or "pending"
                    reason = info.reason or ""
                    dex_name = info.dex_name or ""
                    pair_addr = info.pair_address or ""
                    alt_pairs = info.alt_pairs or []
                    metadata = info.metadata or {}
                    liquidity_val = self._extract_liquidity(metadata)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    status = "error"
                    reason = f"fetch_failed:{e}"
                    dex_name = ""
                    pair_addr = ""
                    alt_pairs = []
                    metadata = {}
                    liquidity_val = None

                summary = {
                    "evt": "summary_retry",
                    "mint": event.mint,
                    "symbol": event.symbol,
                    "dex_status": status,
                    "dex_reason": reason,
                    "dex": dex_name,
                    "pair": pair_addr,
                    "source": event.source,
                    "attempt": attempt,
                    "alt_pairs": alt_pairs,
                    "metadata": metadata,
                }
                if liquidity_val is not None:
                    summary["liquidity_usd"] = liquidity_val

                logger.info(json.dumps(summary, ensure_ascii=False))

                rug_alert = False
                if liquidity_val is not None:
                    rug_alert = self._check_liquidity_drop(event.mint, liquidity_val)

                blacklisted = self._is_blacklisted(event.mint) or rug_alert
                if rug_alert:
                    summary["rug_alert"] = True
                    summary["dex_reason"] = (summary["dex_reason"] + ";rug_alert") if summary["dex_reason"] else "rug_alert"
                    summary["blacklisted_until"] = self._blacklisted_until.get(event.mint)
                elif blacklisted:
                    summary["blacklisted_until"] = self._blacklisted_until.get(event.mint)

                decision, score, decision_notes = self._decide_candidate(
                    summary,
                    rug_alert=rug_alert,
                    blacklisted=blacklisted,
                )
                summary["score"] = score
                summary["decision"] = decision

                notes = self._build_notes(
                    summary,
                    rug_alert=rug_alert,
                    blacklisted=blacklisted,
                    extra_notes=decision_notes,
                )
                self._write_jsonl_entry(
                    summary,
                    decision=decision,
                    score=score,
                    notes=notes,
                )

                if decision == "publish":
                    success = True
                    await self._send_telegram_notification(summary)
                    # Try auto-trade after sending notification
                    await self._maybe_auto_trade(summary)
                    break

                if attempt == self._max_retry_attempts or blacklisted:
                    self._append_reject(summary)

                attempt += 1
                delay = min(self._retry_max_delay, delay * self._retry_backoff)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("⚠️ Retry loop epäonnistui mintille %s: %s", event.mint[:8], e)
        finally:
            if not success and not self._stop.is_set() and attempt > self._max_retry_attempts:
                logger.warning(
                    "❌ Dex-informaatiota ei saatu mintille %s retry-yrityksistä huolimatta",
                    event.mint[:8],
                )
            self._retry_tasks.pop(event.mint, None)

    def _append_reject(self, row: dict) -> None:
        try:
            with open("dex_rejects.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _extract_liquidity(self, metadata: dict[str, Any]) -> float | None:
        if not metadata:
            return None
        value = metadata.get("liquidity_usd")
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    
    
    

    def _build_notes(
        self,
        summary: dict,
        *,
        rug_alert: bool,
        blacklisted: bool,
        extra_notes: Optional[list[str]] = None,
    ) -> list[str]:
        notes: list[str] = list(extra_notes or [])
        metadata = summary.get("metadata") or {}
        if rug_alert:
            notes.append("rug_alert")
        if blacklisted and not rug_alert:
            notes.append("blacklisted")
        fdv_note = metadata.get("fdv_note")
        if fdv_note:
            notes.append(str(fdv_note))
        buyers = metadata.get("buyers_30m")
        if isinstance(buyers, (int, float)):
            if buyers >= 3:
                notes.append("buyers_ok")
            else:
                notes.append("buyers_low")
        if summary.get("dex_status") == "ok":
            notes.append("dex_ok")
        else:
            notes.append("dex_pending")
        return notes

    def _write_jsonl_entry(
        self,
        summary: dict,
        *,
        decision: str,
        score: Optional[float],
        notes: list[str],
    ) -> None:
        try:
            metadata = summary.get("metadata") or {}
            mint = summary.get("mint")
            symbol = summary.get("symbol")
            liquidity = summary.get("liquidity_usd")
            if liquidity is None:
                liquidity = metadata.get("liquidity_usd")
            volume = metadata.get("volume_24h_usd")
            util = None
            try:
                if liquidity and volume is not None and float(liquidity) > 0:
                    util = float(volume) / float(liquidity)
            except (TypeError, ValueError, ZeroDivisionError):
                util = None

            buyers30 = metadata.get("buyers_30m")
            try:
                buyers30 = int(buyers30) if buyers30 is not None else None
            except (TypeError, ValueError):
                buyers30 = None

            pair_created = metadata.get("pair_created_at")
            age_min = None
            if pair_created:
                try:
                    ts = float(pair_created)
                    if ts > 1e12:
                        ts /= 1000.0
                    age_min = max(0.0, (time.time() - ts) / 60.0)
                except (TypeError, ValueError):
                    age_min = None

            price_change = metadata.get("price_change")
            decimals = metadata.get("decimals")
            try:
                decimals = int(decimals) if decimals is not None else None
            except (TypeError, ValueError):
                decimals = None

            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "mint": mint,
                "program": summary.get("program") or "spl",
                "symbol": symbol,
                "decimals": decimals,
                "authorities": {
                    "mint": None,
                    "freeze": None,
                    "risks": []
                },
                "holders": {
                    "count": None,
                    "top10_pct": None,
                    "delta_15m": None,
                },
                "dex": {
                    "primaryPairId": summary.get("pair"),
                    "dexId": summary.get("dex"),
                    "liq_usd": liquidity,
                    "vol_h24": volume,
                    "util": util,
                    "price_usd": metadata.get("price_usd"),
                    "fdv": metadata.get("fdv"),
                    "age_min": age_min,
                    "priceChange": price_change,
                },
                "score": float(score) if score is not None else None,
                "decision": decision,
                "notes": notes,
            }
            if score is not None:
                entry["score"] = float(score)
            entry["score"] = entry.get("score") or score
            entry["dex"]["buyers30m"] = buyers30

            with open("token_events.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            logger.debug("JSONL write failed", exc_info=True)

    def _check_liquidity_drop(self, mint: str, liquidity: float | None) -> bool:
        if liquidity is None or liquidity <= 0:
            return False
        now = time.time()
        history = self._liquidity_history.setdefault(mint, [])
        history.append((now, liquidity))
        cutoff = now - 300.0
        history[:] = [(ts, val) for ts, val in history if ts >= cutoff]
        if not history:
            return False
        max_liq = max(val for _, val in history)
        if max_liq <= 0:
            return False
        if liquidity <= max_liq * 0.4:
            if not self._is_blacklisted(mint):
                self._blacklisted_until[mint] = now + 86400.0
            return True
        return False

    def _is_blacklisted(self, mint: str) -> bool:
        until = self._blacklisted_until.get(mint)
        return bool(until and time.time() < until)

    async def _cleanup_loop(self) -> None:
        while not self._stop.is_set():
            await asyncio.sleep(self._cleanup_interval)
            await self._cleanup_memory()

    async def _cleanup_memory(self) -> None:
        now = time.time()
        ttl = self._liquidity_ttl

        for mint in list(self._liquidity_history.keys()):
            history = self._liquidity_history.get(mint, [])
            if not history:
                self._liquidity_history.pop(mint, None)
                continue
            filtered = [(ts, val) for ts, val in history if now - ts < ttl]
            if filtered:
                self._liquidity_history[mint] = filtered
            else:
                self._liquidity_history.pop(mint, None)

        for mint, expires in list(self._blacklisted_until.items()):
            if now >= expires:
                self._blacklisted_until.pop(mint, None)

        memory_usage_metric.labels("liquidity_history").set(len(self._liquidity_history))
        memory_usage_metric.labels("blacklisted").set(len(self._blacklisted_until))

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy" if not self._stop.is_set() else "stopped",
            "queue_size": self._queue.qsize(),
            "active_retries": len(self._retry_tasks),
            "memory_usage": {
                "liquidity_history": len(self._liquidity_history),
                "blacklisted": len(self._blacklisted_until),
            },
            "uptime": time.time() - self._start_time,
        }


    def _parse_pools(self, dex_raw: dict) -> List[DexPool]:
        pools: List[DexPool] = []
        for p in (dex_raw.get("dexscreener", {}) or {}).get("pairs", []) or []:
            pools.append(
                DexPool(
                    pair_id=p.get("pairId") or "",
                    dex_id=p.get("dexId") or p.get("dexType") or "",
                    liquidity_usd=float((p.get("liquidity") or {}).get("usd") or p.get("liquidityUsd") or 0.0),
                    volume_h24=float((p.get("volume") or {}).get("h24") or p.get("volumeH24") or 0.0),
                    price_usd=(lambda x: float(x) if x is not None else None)(p.get("priceUsd")),
                    fdv=(lambda x: float(x) if x is not None else None)(p.get("fdv")),
                    market_cap=(lambda x: float(x) if x is not None else None)(p.get("marketCap")),
                    price_change={
                        "m5": float(((p.get("priceChange") or {}).get("m5")) or p.get("m5") or 0.0),
                        "h1": float(((p.get("priceChange") or {}).get("h1")) or p.get("h1") or 0.0),
                        "h6": float(((p.get("priceChange") or {}).get("h6")) or p.get("h6") or 0.0),
                        "h24": float(((p.get("priceChange") or {}).get("h24")) or p.get("h24") or 0.0),
                    },
                    url=p.get("url"),
                    age_min=int(((p.get("age") or {}).get("min")) or p.get("ageMin") or 0),
                    trades24h=int(((p.get("trades") or {}).get("h24")) or p.get("trades24h") or 0),
                    last_trade_min=int(((p.get("lastTrade") or {}).get("minAgo")) or p.get("lastTradeMin") or 999),
                )
            )
        return pools

    def _score(self, p: DexPool, util: float, buyers30m: int, enriched: dict) -> int:
        s = 0
        if (p.liquidity_usd or 0.0) >= self._config.min_liquidity_usd: s += 15
        if (p.volume_h24 or 0.0)   >= self._config.min_volume24h_usd: s += 10
        if self._config.util_enabled and self._config.util_min <= util <= self._config.util_max: s += 5
        if (p.age_min or 0) >= 30: s += 5
        if buyers30m >= self._config.min_buyers_30m: s += 15
        bsr = float(enriched.get("market", {}).get("buy_sell_ratio", 0.0))
        if 1.1 <= bsr <= 3.0: s += 10
        renounced = bool(enriched.get("authorities", {}).get("renounced"))
        if renounced: s += 10
        if enriched.get("decimals") in (6, 9): s += 5
        if not enriched.get("placeholder_symbol", False): s += 5
        top10 = enriched.get("holders", {}).get("top10_pct", 1.0)
        try:
            if float(top10) <= 0.85: s += 5
        except Exception:
            pass
        m5 = p.price_change.get("m5", 0.0); h1 = p.price_change.get("h1", 0.0)
        if 2.0 <= m5 <= 120.0: s += 5
        if 2.0 <= h1 <= 80.0:  s += 5
        # --- Placeholder pehmeänä rangaistuksena ---
        if enriched.get("placeholder_symbol", False):
            if self._config.strict_placeholder:
                # Nollaa pisteet ja anna kovasyy (mutta varsinainen droppi tapahtuu kutsukohdassa)
                s = 0
            else:
                s = max(0, s - int(self._config.placeholder_penalty))
        return int(s)

    def _log_drop(self, reason: str, mint: str, extra: dict | None = None) -> None:
        info = {"reason": reason, "mint": mint}
        if extra: info.update(extra)
        try:
            logger.info("drop_decision %s", info)
        except Exception:
            pass

    def _has_token22_traps(self, enriched: dict) -> bool:
        # Toteuta token-22 ansaliput -tarkistus
        return False

    def _enrich_basic(self, candidate) -> dict:
        # Toteuta perusrikkaus
        return {"mint": candidate.mint}

    def _log_exception(self, context: str, e: Exception) -> None:
        logger.exception(f"{context}: {e}")

    async def _publish(self, enriched: dict) -> None:
        mint = enriched.get('mint', '')
        current_time = time.time()
        
        # Tarkista cooldown
        if mint in self._telegram_cooldown:
            last_sent = self._telegram_cooldown[mint]
            if current_time - last_sent < self._cooldown_duration:
                logger.info(f"Telegram cooldown active for {mint}, skipping message")
                return
        
        # Älä lähetä viestiä jos token on "pending" tilassa
        dex_status = enriched.get('dex_status', '')
        if dex_status == "pending":
            logger.info(f"Token {mint} is in pending state, skipping Telegram message")
            return
        
        # Päivitä cooldown
        self._telegram_cooldown[mint] = current_time
        
        d = enriched.get("dex", {})
        metadata = enriched.get("metadata", {})
        is_update = enriched.get("lp_changed", False)
        
        # Kilpailijan tyylinen formatointi
        symbol = (
            d.get('resolved_symbol')
            or metadata.get('resolved_symbol')
            or metadata.get('base_symbol')
            or f"TOKEN_{mint[:6]}"
        )
        # Turvallinen numeromuunnos
        def _f(v, default=0.0):
            try:
                return float(v)
            except Exception:
                return float(default)
        price = _f(d.get('price_usd', metadata.get('price_usd', 0)))
        liq = _f(d.get('liq_usd', metadata.get('liquidity_usd', 0)))
        vol = _f(d.get('vol_h24', metadata.get('volume_24h_usd', 0)))
        fdv = _f(d.get('fdv', metadata.get('fdv', 0)))
        age_min = int(_f(d.get('age_min', metadata.get('age_min', 0))))
        buyers30m = int(_f(d.get('buyers30m', metadata.get('buyers_30m', 0))))
        
        # Formatoidaan hinta kilpailijan tyyliin
        if price and price > 0:
            if price < 0.0001:
                price_str = f"${price:.0e}"
            elif price < 0.01:
                price_str = f"${price:.6f}"
            else:
                price_str = f"${price:.4f}"
        else:
            price_str = "n/a"
        
        # Emoji-header
        header = "🔄 *Token Update*" if is_update else "💊 *New Token*"
        
        # Kilpailijan tyylinen viesti - turvallinen formatointi
        try:
            ds_url = d.get('url') or metadata.get('pair_url') or ''
            
            # Calculate additional fields
            th_series = self._calculate_th_series(metadata)
            fresh_stats = self._calculate_fresh_stats(metadata)
            dev_history = self._calculate_dev_history(metadata)
            ath_info = self._calculate_ath_info(metadata, price)
            
            text = f"""{header}

├ {symbol} ({mint[:8]}...)
└ #SOL | 🌱{age_min:.0f}m | 👁️{buyers30m}

📊 Stats
 ├ USD   {price_str}
 ├ MC    ${int(fdv/1000):.0f}K
 ├ Vol   ${int(vol/1000):.1f}K
 ├ LP    ${int(liq/1000):.1f}K
 ├ Age   {age_min:.0f}m
 └ Buyers {buyers30m}

🔒 Security
 ├ Fresh     {fresh_stats}
 ├ Top 10    {th_series}
 ├ TH        {th_series}
 ├ Dev Toks  {dev_history}
 └ ATH       {ath_info}

🔗 Links
 └ [DexScreener]({ds_url}) | [Solscan](https://solscan.io/token/{mint})

🔥 First Call @ ${int(fdv/1000):.0f}K"""
        except Exception as e:
            # Fallback yksinkertaiseen viestiin
            text = f"{header}\n\n{symbol} ({mint[:8]}...)\nPrice: {price_str}\nMC: ${int(fdv/1000):.0f}K\nVol: ${int(vol/1000):.1f}K\nLP: ${int(liq/1000):.1f}K"
        
        # Lähetä Telegram-viesti
        try:
            if self.telegram_bot and self.telegram_bot.enabled:
                await self.telegram_bot.send_message(text)
                logger.info(f"📱 Telegram-viesti lähetetty tokenista: {mint[:8]}...")
        except Exception as e:
            logger.warning(f"⚠️ Telegram-viestin lähetys epäonnistui: {e}")

    def _calculate_th_series(self, metadata: dict) -> str:
        """Calculate top-5 holder percentages"""
        try:
            holders_data = metadata.get("holders", {})
            if isinstance(holders_data, dict):
                top5_pct = holders_data.get("top5_pct_list", [])
                if isinstance(top5_pct, list) and len(top5_pct) >= 5:
                    # Format as "3.5|2.7|2.7|2.3|2.2 [sum%]"
                    formatted = "|".join([f"{pct:.1f}" for pct in top5_pct[:5]])
                    total = sum(top5_pct[:5])
                    return f"{formatted} [{total:.0f}%]"
            return "n/a"
        except Exception:
            return "n/a"

    def _calculate_fresh_stats(self, metadata: dict) -> str:
        """Calculate fresh 1D/7D percentages"""
        try:
            holders_data = metadata.get("holders", {})
            if isinstance(holders_data, dict):
                fresh1d = holders_data.get("fresh1d_pct", 0)
                fresh7d = holders_data.get("fresh7d_pct", 0)
                if fresh1d > 0 or fresh7d > 0:
                    return f"{fresh1d:.1f}% 1D | {fresh7d:.1f}% 7D"
            return "n/a"
        except Exception:
            return "n/a"

    def _calculate_dev_history(self, metadata: dict) -> str:
        """Calculate dev history (simple heuristic)"""
        try:
            # Simple heuristic: check if creator has previous mints/sales
            dev_data = metadata.get("dev_history", {})
            if isinstance(dev_data, dict):
                prev_mints = dev_data.get("previous_mints", 0)
                has_sales = dev_data.get("has_sales", False)
                if prev_mints > 0 or has_sales:
                    return f"{prev_mints} / {1 if has_sales else 0} (🅳)"
            return "n/a"
        except Exception:
            return "n/a"

    def _calculate_ath_info(self, metadata: dict, current_price: float) -> str:
        """Calculate ATH and delta from current price"""
        try:
            ath_data = metadata.get("ath", {})
            if isinstance(ath_data, dict):
                ath_price = ath_data.get("price", 0)
                ath_time = ath_data.get("timestamp", 0)
                if ath_price > 0 and current_price > 0:
                    delta_pct = ((current_price - ath_price) / ath_price) * 100
                    # Calculate time since ATH
                    if ath_time > 0:
                        time_since = (time.time() - ath_time) / 60  # minutes
                        if time_since < 60:
                            time_str = f"{time_since:.0f}m"
                        else:
                            time_str = f"{time_since/60:.0f}h"
                    else:
                        time_str = "n/a"
                    return f"${ath_price:.4f} ({delta_pct:+.1f}% / {time_str})"
            return "n/a"
        except Exception:
            return "n/a"

    # -------- Symboliresolveri & apurit --------
    def _resolve_symbol(self, enriched: dict, dex_raw: dict) -> Tuple[str | None, float, bool]:
        """
        Palauttaa: (symbol, confidence 0..1, is_placeholder)
        - kerää ehdokkaita Helius metadata → DexScreener → Birdeye → Jupiter
        - valitsee ensimmäisen validin; jos kaikki huonoja, palauttaa None ja placeholder=True
        """
        cand: List[Tuple[str, float, str]] = []
        # Helius / DAS metadata
        m_sym = (enriched.get("metadata") or {}).get("symbol") or (enriched.get("content", {}).get("metadata") or {}).get("symbol")
        if m_sym: cand.append((str(m_sym), 0.9, "helius"))
        # DexScreener
        try:
            pairs = (dex_raw.get("dexscreener", {}) or {}).get("pairs", []) or []
            for p in pairs[:2]:
                bsym = (p.get("baseToken") or {}).get("symbol")
                if bsym: cand.append((str(bsym), 0.8, "dexscreener"))
        except Exception:
            pass
        # Birdeye
        try:
            be = (dex_raw.get("birdeye", {}) or {})
            if isinstance(be, dict):
                bsym = be.get("symbol")
                if bsym: cand.append((str(bsym), 0.7, "birdeye"))
        except Exception:
            pass
        # Jupiter
        try:
            j = (dex_raw.get("jupiter", {}) or {})
            jsym = j.get("symbol") or (j.get("data") or {}).get("symbol")
            if jsym: cand.append((str(jsym), 0.85, "jupiter"))
        except Exception:
            pass
        # CoinGecko (vahva vahvistus)
        try:
            cg_sym = enriched.get("coingecko_symbol")
            if cg_sym: cand.append((str(cg_sym), 0.95, "coingecko"))
        except Exception:
            pass

        # Validaattori
        def _is_placeholder(s: str) -> bool:
            s_up = s.upper()
            return s_up.startswith("TOKEN_") or s_up in ("UNKNOWN", "N/A", "NA")
        def _is_valid(s: str) -> bool:
            if not s: return False
            s = s.strip()
            if _is_placeholder(s): return False
            if not (self._config.min_symbol_len <= len(s) <= self._config.max_symbol_len): return False
            # sallitut: A-Z0-9_$ (yksinkertaistetaan)
            return all(ch.isalnum() or ch in ("_", "$") for ch in s)

        for sym, conf, src in cand:
            if _is_valid(sym):
                return sym.strip().upper(), conf, False
        # Kaikki ehdokkaat placeholder/invalid → liputa placeholder
        # Palauta paras placeholder silti nimenä, jos halutaan näyttää viesteissä
        best = cand[0][0] if cand else None
        return (best.strip().upper() if isinstance(best, str) else None), 0.1, True

    def _is_bluechip(self, mint: str, symbol: Optional[str]) -> bool:
        mint = (mint or "").strip()
        sym = (symbol or "").upper()
        # Tunnetut Solana bluechipit ja stablecoinit (hylätään kaikki)
        BLUECHIP_MINTS = set((
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            "So11111111111111111111111111111111111111112",   # wSOL
        ))
        BLUECHIP_SYMS = set(("USDC", "USDT", "WSOL", "SOL"))
        if mint in BLUECHIP_MINTS: return True
        if sym in BLUECHIP_SYMS: return True
        return False

    def _decide_candidate(
        self,
        summary: dict,
        *,
        rug_alert: bool,
        blacklisted: bool,
    ) -> tuple[str, Optional[float], list[str]]:
        extra_notes: list[str] = []
        if rug_alert or blacklisted:
            extra_notes.append("risk_drop")
            return "drop", None, extra_notes

        # --- SYMBOLIN RESOLVONTI (uusi logiikka) ---
        mint = summary.get("mint", "")
        symbol = (summary.get("symbol") or "").upper()
        
        # Käytä symbol resolveria jos saatavilla
        if hasattr(self, '_resolve_symbol'):
            # Luo mock dex_raw -data symbol resolverille
            dex_raw = {
                "dexscreener": summary.get("metadata", {}),
                "birdeye": summary.get("metadata", {}),
                "jupiter": summary.get("metadata", {}),
            }
            resolved_symbol, symbol_confidence, is_placeholder = self._resolve_symbol(summary, dex_raw)
            
            # Päivitä summary uudella symbolilla
            if resolved_symbol:
                summary["resolved_symbol"] = resolved_symbol
                summary["symbol_confidence"] = symbol_confidence
                symbol = resolved_symbol.upper()
            
            # Bluechip-suodatin
            if self._is_bluechip(mint, resolved_symbol):
                extra_notes.append("bluechip_non_target")
                return "drop", None, extra_notes
            
            # Placeholder-käsittely (pehmeä rangaistus)
            if is_placeholder:
                if self._config.strict_placeholder:
                    extra_notes.append("placeholder_symbol_strict")
                    return "drop", None, extra_notes
                else:
                    extra_notes.append("placeholder_symbol_penalty")
                    # Lisää retry-jonoon symbolin resolvointia varten
                    try:
                        self._symbol_retry_queue.put_nowait(mint)
                        logger.debug(f"Added {mint[:8]} to symbol retry queue")
                    except asyncio.QueueFull:
                        logger.warning(f"Symbol retry queue full, skipping {mint[:8]}")
                    # Jatka pisteytykseen, mutta vähennä pisteitä myöhemmin
        else:
            # Vanha logiikka fallbackina - POISTETTU (ei enää kova portti)
            pass

        metadata = summary.get("metadata") or {}
        try:
            liquidity = float(metadata.get("liquidity_usd")) if metadata.get("liquidity_usd") is not None else None
        except (TypeError, ValueError):
            liquidity = None
        try:
            volume = float(metadata.get("volume_24h_usd")) if metadata.get("volume_24h_usd") is not None else None
        except (TypeError, ValueError):
            volume = None

        util = None
        if liquidity is not None and liquidity > 0 and volume is not None:
            util = volume / liquidity

        # Smart cooldown for new pools
        age_minutes = self._calculate_token_age(metadata)
        dex_source = summary.get("source", "")
        
        # If very new pool (< 2 min) and no DEX data yet, use light publish
        if age_minutes < 2 and dex_source in ["raydium_live", "orca_live"] and liquidity is None:
            # Light publish with minimal data
            liquidity = 500  # Lower default for very new pools
            volume = 50
            extra_notes.append("light_publish_new_pool")
        
        # Salli tokeneita ilman täydellistä market dataa (kilpailijan tyyliin)
        # Jos ei ole likviditeettiä eikä volyymiä, salli silti uudet tokeneita
        if liquidity is None and volume is None:
            # Aseta oletusarvot uusille tokeneille
            liquidity = 1000  # $1K oletuslikviditeetti
            volume = 100     # $100 oletusvolyymi
            extra_notes.append("new_token_defaults")
        
        # Jos volyymi on 0 mutta likviditeetti on olemassa, salli
        if volume == 0 and liquidity is not None and liquidity > 0:
            volume = 100  # Aseta minimi volyymi
            extra_notes.append("zero_volume_override")

        cfg = self._config

        # Alenna kynnysarvoja kilpailijan tyyliin
        min_liq = min(cfg.min_liquidity_usd, 1000)  # $1K minimi
        min_vol = min(cfg.min_volume24h_usd, 100)   # $100 minimi
        
        # Jos likviditeetti on olemassa mutta alle kynnyksen, salli silti
        if liquidity is not None and liquidity < min_liq:
            if liquidity > 0:  # Jos likviditeetti > 0, salli
                extra_notes.append("low_liquidity_override")
            else:
                extra_notes.append("market_threshold_fail")
                return "drop", None, extra_notes
        
        # Jos volyymi on olemassa mutta alle kynnyksen, salli silti
        if volume is not None and volume < min_vol:
            if volume >= 0:  # Jos volyymi >= 0, salli
                extra_notes.append("low_volume_override")
            else:
                extra_notes.append("market_threshold_fail")
                return "drop", None, extra_notes

        if util is not None and (util < cfg.util_min or util > cfg.util_max):
            extra_notes.append("util_out_of_bounds")
            return "drop", None, extra_notes

        buyers30 = metadata.get("buyers_30m")
        try:
            buyers30 = int(buyers30) if buyers30 is not None else None
        except (TypeError, ValueError):
            buyers30 = None

        pair_created = metadata.get("pair_created_at")
        age_min = None
        if pair_created is not None:
            try:
                ts = float(pair_created)
                if ts > 1e12:
                    ts /= 1000.0
                age_min = max(0.0, (time.time() - ts) / 60.0)
            except (TypeError, ValueError):
                age_min = None

        if age_min is not None and age_min < cfg.min_age_min:
            extra_notes.append("age_too_fresh")
            return "drop", None, extra_notes

        last_trade_min = metadata.get("last_trade_minutes")
        try:
            last_trade_min = float(last_trade_min) if last_trade_min is not None else None
        except (TypeError, ValueError):
            last_trade_min = None

        if (
            cfg.pool_max_last_trade_min is not None
            and last_trade_min is not None
            and last_trade_min > cfg.pool_max_last_trade_min
        ):
            extra_notes.append("stale_pool")
            return "drop", None, extra_notes

        # Soft mode: buyers30m ei kaada ennen pisteytystä - POISTETTU (ei enää kova portti)
        # if not cfg.buyers30m_soft_mode:
        #     if buyers30 is not None and age_min is not None:
        #         if buyers30 < cfg.min_buyers_30m and age_min < max(cfg.min_age_min, 30.0):
        #             extra_notes.append("buyers_low_early")
        #             return "drop", None, extra_notes
        #
        #     if buyers30 is not None and buyers30 < cfg.min_buyers_30m:
        #         extra_notes.append("buyers_low")
        #         return "drop", None, extra_notes

        trades24 = metadata.get("trades_24h") or metadata.get("txns_24h")
        try:
            trades24 = int(trades24) if trades24 is not None else None
        except (TypeError, ValueError):
            trades24 = None

        if trades24 is not None and trades24 < cfg.pool_min_trades24h:
            extra_notes.append("trades24_low")
            return "drop", None, extra_notes

        score_dex = self._score_dex(liquidity, volume, util, age_min)
        score_demand = self._score_demand(buyers30)
        score_structure = self._score_structure(summary, metadata)
        score_momentum = self._score_momentum(metadata.get("price_change"))

        score = score_dex + score_demand + score_structure + score_momentum
        
        # Jupiter bonus (ei portti, vaan bonus)
        jupiter_data = (summary.get("metadata") or {}).get("jupiter", {})
        if jupiter_data and jupiter_data.get("price"):
            score += 5
            extra_notes.append("jupiter_bonus")
        
        # Pump.fun bonus (badge + momentum)
        source_tags = ((summary.get("metadata") or {}).get("source_tags", [])) or (
            ["pump"] if str(mint).endswith("pump") else []
        )
        if "pump" in source_tags:
            pump_bonus = 3  # Base bonus for being a Pump.fun token
            price_change = metadata.get("price_change", {})
            if isinstance(price_change, dict):
                try:
                    m5 = float(price_change.get("m5", 0)) if price_change.get("m5") is not None else 0
                    h1 = float(price_change.get("h1", 0)) if price_change.get("h1") is not None else 0
                    # Additional bonus for strong momentum
                    if m5 >= 50:  # 50%+ in 5 minutes
                        pump_bonus += 5
                    elif m5 >= 20:  # 20%+ in 5 minutes
                        pump_bonus += 3
                    if h1 >= 100:  # 100%+ in 1 hour
                        pump_bonus += 4
                    elif h1 >= 50:  # 50%+ in 1 hour
                        pump_bonus += 2
                except (TypeError, ValueError):
                    pass
            score += pump_bonus
            extra_notes.append(f"pump_bonus_{pump_bonus}")
        
        # Multi-source confluence bonus (Birdeye + DexScreener)
        birdeye_ok = (summary.get("metadata") or {}).get("birdeye_status") == "ok"
        dexscreener_ok = (summary.get("metadata") or {}).get("dexscreener_status") == "ok"
        if birdeye_ok and dexscreener_ok:
            score += 5
            extra_notes.append("multi_source_confluence")
        
        # DexScreener watchers bonus (if available)
        watchers = metadata.get("watchers", 0)
        if watchers > 0:
            if watchers >= 100:
                score += 3
            elif watchers >= 50:
                score += 2
            elif watchers >= 10:
                score += 1
            extra_notes.append(f"watchers_bonus_{watchers}")
        
        # Placeholder-penalty (pehmeä rangaistus)
        if "placeholder_symbol_penalty" in extra_notes:
            score = max(0.0, score - self._config.placeholder_penalty)
        
        score = max(0.0, min(100.0, score))

        extra_notes.append(f"score={score:.0f}")
        if util is not None:
            extra_notes.append(f"util={util:.2f}")
        else:
            extra_notes.append("util=n/a")
        if buyers30 is not None:
            extra_notes.append(f"buyers30m={buyers30}")
        if age_min is not None:
            extra_notes.append(f"age={int(age_min)}m")
        
        # Lisää symbol resolution -tiedot
        if "resolved_symbol" in summary:
            extra_notes.append(f"resolved_symbol={summary['resolved_symbol']}")
        if "symbol_confidence" in summary:
            extra_notes.append(f"symbol_confidence={summary['symbol_confidence']:.2f}")

        fdv = metadata.get("fdv")
        supply = metadata.get("supply")
        price = metadata.get("price_usd")
        if (
            cfg.enable_fdv_sanity
            and fdv is not None
            and supply is not None
            and price is not None
        ):
            try:
                fdv_calc = float(price) * float(supply)
                fdv_val = float(fdv)
                tolerance = cfg.fdv_sanity_tolerance
                if fdv_calc > 0 and abs(fdv_calc - fdv_val) / fdv_calc > tolerance:
                    extra_notes.append("fdv_sanity_fail")
                    return "drop", None, extra_notes
            except (TypeError, ValueError):
                pass

        # Alenna publish-kynnys kilpailijan tyyliin
        min_score = min(cfg.min_publish_score, 25)  # 25 pistettä minimi
        decision = "publish" if score >= min_score else "drop"
        if decision == "publish":
            extra_notes.append("score_threshold_passed")
        else:
            extra_notes.append("score_threshold_failed")

        return decision, score, extra_notes

    def _score_dex(self, liq: float, vol: float, util: Optional[float], age_min: Optional[float]) -> float:
        score = 0.0
        
        # Alenna likviditeettikynnyksiä kilpailijan tyyliin
        if liq >= 50_000:
            score += 25
        elif liq >= 20_000:
            score += 20
        elif liq >= 10_000:
            score += 15
        elif liq >= 5_000:
            score += 12
        elif liq >= 1_000:
            score += 8
        elif liq >= 100:
            score += 5
        else:
            score += 2  # Antaa pisteitä vaikka likviditeetti olisi pieni

        # Alenna volyymikynnyksiä
        if vol >= 100_000:
            score += 15
        elif vol >= 50_000:
            score += 12
        elif vol >= 20_000:
            score += 10
        elif vol >= 5_000:
            score += 8
        elif vol >= 1_000:
            score += 6
        elif vol >= 100:
            score += 4
        else:
            score += 2  # Antaa pisteitä vaikka volyymi olisi pieni

        # Util-pisteet (ei pakollinen)
        if util is not None:
            if 0.5 <= util <= 3.0:
                score += 8
            elif 0.3 <= util <= 5.0:
                score += 5
            elif util > 0:
                score += 2
        else:
            score += 1  # Antaa pisteitä vaikka util puuttuisi

        # Age-pisteet (ei pakollinen)
        if age_min is not None:
            if age_min >= 120:
                score += 5
            elif age_min >= 60:
                score += 4
            elif age_min >= 30:
                score += 3
            elif age_min >= 10:
                score += 2
            else:
                score += 1
        else:
            score += 1  # Antaa pisteitä vaikka age puuttuisi

        return min(score, 45.0)

    def _score_demand(self, buyers30: Optional[int]) -> float:
        if buyers30 is None:
            return 8.0  # Antaa pisteitä vaikka data puuttuisi
        if buyers30 >= 40:
            return 25.0
        if buyers30 >= 25:
            return 20.0
        if buyers30 >= 15:
            return 15.0
        if buyers30 >= 7:
            return 12.0
        if buyers30 >= 3:
            return 8.0
        return 5.0

    def _score_structure(self, summary: dict, metadata: dict[str, Any]) -> float:
        score = 20.0  # Aloita korkeammalla
        
        # Antaa pisteitä vaikka symbol olisi placeholder
        symbol = summary.get("symbol", "")
        if symbol and not symbol.upper().startswith("TOKEN_"):
            score += 8.0
        else:
            score += 3.0  # Antaa pisteitä placeholder-symboleillekin
            
        if metadata.get("fdv_note"):
            score -= 3.0  # Vähemmän rangaistus
        
        # TH-series scoring (top-5 holder distribution)
        holders_data = metadata.get("holders", {})
        if isinstance(holders_data, dict):
            top5_pct = holders_data.get("top5_pct_list", [])
            if isinstance(top5_pct, list) and len(top5_pct) >= 5:
                total_top5 = sum(top5_pct[:5])
                if total_top5 < 30:  # Good distribution
                    score += 3
                elif total_top5 > 70:  # Concentrated
                    score -= 3
        
        # Fresh 1D/7D scoring
        fresh1d = holders_data.get("fresh1d_pct", 0) if isinstance(holders_data, dict) else 0
        fresh7d = holders_data.get("fresh7d_pct", 0) if isinstance(holders_data, dict) else 0
        if fresh1d >= 10:
            score += 2
        
        # CoinGecko enrichment bonuses
        cg_score = metadata.get("coingecko_score", 0)
        if cg_score > 0:
            score += float(cg_score)
            logger.info(f"Added CoinGecko bonus: +{cg_score} points")
        
        # CoinGecko verification bonus
        if metadata.get("coingecko_symbol") and metadata.get("coingecko_name"):
            score += 5.0  # Extra bonus for verified symbol
        if fresh7d >= 20:
            score += 2
            
        # Confluence bonus (useampi lähde löytyi)
        dex_reason = summary.get("dex_reason", "")
        confluence_count = 0
        if "birdeye" in dex_reason and "ok" in dex_reason:
            confluence_count += 1
        if "dexscreener" in dex_reason and "ok" in dex_reason:
            confluence_count += 1
        if "jupiter" in dex_reason and "ok" in dex_reason:
            confluence_count += 1
        if "coingecko" in dex_reason and "ok" in dex_reason:
            confluence_count += 1
            
        if confluence_count >= 2:
            score += 5.0  # Confluence bonus
        elif confluence_count >= 3:
            score += 8.0  # Strong confluence bonus
            
        # CoinGecko verification bonus
        if "coingecko" in dex_reason and "ok" in dex_reason:
            score += 3.0  # Extra bonus for CoinGecko verification
            
        return max(0.0, min(score, 30.0))

    def _score_momentum(self, price_change: Any) -> float:
        if not isinstance(price_change, dict):
            return 8.0  # Antaa pisteitä vaikka data puuttuisi
        score = 8.0
        try:
            m5 = float(price_change.get("m5")) if price_change.get("m5") is not None else None
        except (TypeError, ValueError):
            m5 = None
        if m5 is not None:
            if m5 >= 10:
                score += 12
            elif m5 >= 5:
                score += 8
            elif m5 >= 0:
                score += 5
            elif m5 >= -10:
                score += 2  # Antaa pisteitä myös hieman laskeneille
            else:
                score -= 4
        try:
            h1 = float(price_change.get("h1")) if price_change.get("h1") is not None else None
        except (TypeError, ValueError):
            h1 = None
        if h1 is not None:
            if h1 >= 20:
                score += 8
            elif h1 >= 10:
                score += 6
            elif h1 >= 0:
                score += 3
            else:
                score -= 3
        return max(0.0, min(score, 25.0))

    async def _scan_older_tokens(self) -> None:
        """
        Skannaa tokeneita Pump.fun:sta ja DexScreener:sta jotka voivat olla jo indeksoitu ja joilla on oikeat symbolit.
        Tämä auttaa löytämään tokeneita joilla on oikeat symbolit ja markkinadata.
        """
        try:
            logger.info("🔍 Scanning Pump.fun and DexScreener for tokens with real symbols...")
            
            # Hae tokeneita Pump.fun:sta
            await self._scan_pump_fun_tokens()
            
            # Hae tokeneita DexScreener:sta
            await self._scan_dexscreener_tokens()
            
        except Exception as e:
            logger.error(f"Error scanning tokens: {e}")

    async def _scan_pump_fun_tokens(self) -> None:
        """Skannaa uusia tokeneita Pump.fun:sta"""
        try:
            async with aiohttp.ClientSession() as session:
                # Pump.fun API endpoint uusille tokeneille
                url = "https://frontend-api.pump.fun/coins"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        coins = data.get("coins", [])
                        
                        # Suodata uusimmat tokeneita (alle 1 tunti vanhoja)
                        current_time = int(time.time())
                        recent_coins = []
                        
                        for coin in coins:
                            if isinstance(coin, dict):
                                created_timestamp = coin.get("created_timestamp")
                                if created_timestamp:
                                    try:
                                        created_time = int(created_timestamp)
                                        age_minutes = (current_time - created_time) / 60
                                        if age_minutes <= 60:  # Alle 1 tunti vanha
                                            recent_coins.append(coin)
                                    except (ValueError, TypeError):
                                        continue
                        
                        logger.info(f"Found {len(recent_coins)} recent Pump.fun tokens")
                        
                        # Analysoi jokainen token
                        for coin in recent_coins[:5]:  # Rajoita 5:een
                            try:
                                mint = coin.get("mint")
                                symbol = coin.get("symbol")
                                name = coin.get("name")
                                
                                if mint and symbol and not symbol.upper().startswith("TOKEN_"):
                                    # Varmista että kuluttaja käy
                                    self._ensure_consumer_started()
                                    ev = NewTokenEvent(
                                        mint=mint, 
                                        symbol=symbol, 
                                        name=name or f"Token {symbol}", 
                                        signature=None
                                    )
                                    with contextlib.suppress(asyncio.QueueFull):
                                        self._queue.put_nowait(ev)
                                    logger.info(f"Added Pump.fun token: {symbol} ({mint[:8]}...)")
                                    
                            except Exception as e:
                                logger.debug(f"Error processing Pump.fun token: {e}")
                    else:
                        # Liikaa melua tuotannossa → INFO + progressiivinen backoff
                        logger.info(f"Pump.fun unavailable (HTTP {response.status}), will retry with backoff")
                        
        except Exception as e:
            logger.error(f"Error scanning Pump.fun tokens: {e}")

    async def _scan_dexscreener_tokens(self) -> None:
        """Skannaa tokeneita DexScreener:sta"""
        try:
            async with aiohttp.ClientSession() as session:
                # Hae uusimpia tokeneita DexScreener:sta käyttäen search endpoint:ia
                url = "https://api.dexscreener.com/latest/dex/search?q=solana"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get("pairs", [])
                        
                        # Suodata Solana-pareja jotka ovat uusia (alle 1 tunti vanhoja)
                        current_time = int(time.time())
                        recent_pairs = []
                        
                        for pair in pairs:
                            if isinstance(pair, dict):
                                chain_id = pair.get("chainId")
                                if chain_id == "solana":
                                    # Tarkista onko pari uusi
                                    pair_created_at = pair.get("pairCreatedAt")
                                    if pair_created_at:
                                        try:
                                            created_time = int(pair_created_at) / 1000  # Convert from milliseconds
                                            age_minutes = (current_time - created_time) / 60
                                            if age_minutes <= 60:  # Alle 1 tunti vanha
                                                recent_pairs.append(pair)
                                        except (ValueError, TypeError):
                                            continue
                        
                        logger.info(f"Found {len(recent_pairs)} recent Solana pairs from DexScreener")
                        
                        # Analysoi jokainen pari
                        for pair in recent_pairs[:5]:  # Rajoita 5:een
                            try:
                                base_token = pair.get("baseToken", {})
                                mint = base_token.get("address")
                                symbol = base_token.get("symbol")
                                name = base_token.get("name")
                                
                                if mint and symbol and not symbol.upper().startswith("TOKEN_"):
                                    # Varmista että kuluttaja käy
                                    self._ensure_consumer_started()
                                    ev = NewTokenEvent(
                                        mint=mint, 
                                        symbol=symbol, 
                                        name=name or f"Token {symbol}", 
                                        signature=None
                                    )
                                    with contextlib.suppress(asyncio.QueueFull):
                                        self._queue.put_nowait(ev)
                                    logger.info(f"Added DexScreener token: {symbol} ({mint[:8]}...)")
                                    
                            except Exception as e:
                                logger.debug(f"Error processing DexScreener pair: {e}")
                    else:
                        logger.warning(f"Failed to fetch DexScreener tokens: HTTP {response.status}")
                        
        except Exception as e:
            logger.error(f"Error scanning DexScreener tokens: {e}")

    async def _older_tokens_loop(self) -> None:
        """
        Ajastettu silmukka joka skannaa vanhempia tokeneita 5 minuutin välein.
        """
        while not self._stop.is_set():
            try:
                await self._scan_older_tokens()
                # Odota 5 minuuttia ennen seuraavaa skannausta
                await asyncio.sleep(5 * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in older tokens loop: {e}")
                await asyncio.sleep(60)  # Odota 1 minuutti virheen jälkeen

    async def _try_extract_mint(self, logs: list[str], signature: str | None) -> str | None:
        """
        Yritä päätellä mint:
        1) Logeista: etsi InitializeMint/InitializeMint2 ja heuristinen osoite
        2) RPC: getTransaction(signature) → postTokenBalances.mint tai viestin accountKeys:stä
        """
        # 1) Logien perusteella (pika)
        if logs:
            joined = "\n".join(logs)
            if ("InitializeMint" in joined) or ("InitializeMint2" in joined):
                # poimi pitkä aakkisnumeerinen merkkijono joka ei ole tunnettujen ohjelmien id
                for line in logs:
                    for token in line.replace(",", " ").split():
                        if self._looks_like_pubkey(token) and not self._is_known_program(token):
                            return token

        # 2) RPC fallback, jos allekirjoitus löytyy ja rpc_get_tx on injektoitu
        if signature and self._rpc_get_tx:
            try:
                tx = await self._rpc_get_tx(signature)
                mint = self._extract_mint_from_tx(tx)
                if mint:
                    return mint
            except Exception:
                pass

        return None

    @staticmethod
    def _looks_like_pubkey(s: str) -> bool:
        return bool(s and len(s) >= 32 and s.isalnum())

    @staticmethod
    def _is_known_program(addr: str) -> bool:
        KNOWN = {
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "11111111111111111111111111111111",  # SystemProgram
            "SysvarRent111111111111111111111111111111111",
            "ComputeBudget111111111111111111111111111111",
            "AddressLookupTab1e1111111111111111111111111",
            "BPFLoaderUpgradeab1e11111111111111111111111",
            "Vote111111111111111111111111111111111111111",
            "Sysvar1nstructions1111111111111111111111111",
            "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
        }
        return addr in KNOWN

    @classmethod
    def _extract_mint_from_tx(cls, tx: dict) -> str | None:
        # 2a) postTokenBalances mint
        meta = tx.get("meta") or {}
        ptb = meta.get("postTokenBalances") or []
        if isinstance(ptb, list) and ptb:
            # Jos vain yksi mint löytyy, käytä sitä
            mints = {b.get("mint") for b in ptb if isinstance(b, dict) and b.get("mint")}
            if len(mints) == 1:
                m = next(iter(mints))
                if isinstance(m, str) and cls._looks_like_pubkey(m):
                    return m

        # 2b) Viestin accountKeys: valitse ensimmäinen joka ei ole tunnettu ohjelma/sysvar
        msg = (tx.get("transaction") or {}).get("message") or {}
        keys = msg.get("accountKeys") or []
        addresses: list[str] = []
        for k in keys:
            if isinstance(k, str):
                addresses.append(k)
            elif isinstance(k, dict) and isinstance(k.get("pubkey"), str):
                addresses.append(k["pubkey"])
        for a in addresses:
            if a and cls._looks_like_pubkey(a) and not cls._is_known_program(a):
                return a
        return None
    
    def set_telegram_bot(self, telegram_bot: Any):
        """Set Telegram bot for scanner notifications"""
        self.telegram_bot = telegram_bot
        logger.info("Telegram bot set for scanner notifications")
    
    def get_trading_status(self) -> dict:
        """Get trading status for health endpoint"""
        try:
            if not hasattr(self, 'trader') or not self.trader:
                return {
                    "trading_available": False,
                    "trading_enabled": False,
                    "dry_run": True,
                    "reason": "trader_not_initialized"
                }
            
            if not hasattr(self, 'trade_cfg') or not self.trade_cfg:
                return {
                    "trading_available": False,
                    "trading_enabled": False,
                    "dry_run": True,
                    "reason": "trade_config_not_initialized"
                }
            
            return {
                "trading_available": True,
                "trading_enabled": self.trade_cfg.enabled,
                "dry_run": self.trade_cfg.dry_run,
                "max_trade_usd": self.trade_cfg.max_trade_usd,
                "min_score_to_buy": self.trade_cfg.min_score_to_buy,
                "min_liq_usd_to_buy": self.trade_cfg.min_liq_usd_to_buy,
                "has_keypair": self.trader.kp is not None,
                "cooldown_sec": self.trade_cfg.cooldown_sec
            }
        except Exception as e:
            return {
                "trading_available": False,
                "trading_enabled": False,
                "dry_run": True,
                "error": str(e)
            }

    async def _wallet_report_worker(self):
        """Send wallet balance report every 2 hours"""
        logger.info("💰 Wallet report worker started (2h interval)")
        
        # Send initial report after 5 seconds
        await asyncio.sleep(5)
        await self._send_wallet_report()
        
        while not self._stop.is_set():
            try:
                await asyncio.sleep(self._wallet_report_interval)
                await self._send_wallet_report()
            except Exception as e:
                logger.error(f"Wallet report worker error: {e}")
                await asyncio.sleep(60)
        
        logger.info("💰 Wallet report worker stopped")
    
    async def _send_wallet_report(self):
        """Send wallet balance and trading stats to Telegram"""
        try:
            if not self.telegram_bot or not self.telegram_bot.enabled:
                return
            
            if not self.trader or not self.trade_cfg:
                return
            
            # Get detailed wallet balance using BalanceManager
            if hasattr(self, 'balance_mgr') and self.balance_mgr:
                snap = await self.balance_mgr.snapshot(self.positions.get_all())
                sol_total_display = snap['sol_total_display']
                sol_spendable_display = snap['sol_spendable_display']
                wsol_display = snap['wsol_display']
                sol_total = snap['sol_total']
            else:
                # Fallback to old method
                sol_balance = await self.trader.get_sol_balance()
                sol_total_display = f"{sol_balance:.5f}"
                sol_spendable_display = f"{sol_balance:.5f}"
                wsol_display = "0.00000"
                sol_total = sol_balance
            
            sol_price = float(os.getenv("SOL_PRICE_FALLBACK", "208"))
            balance_usd = sol_total * sol_price
            
            # Trading stats
            total_trades = len(self._last_trade_ts)
            open_positions = len(self._open_positions)  # Actual open positions
            
            # Build message
            message = f"""📊 **Wallet Report**

💰 **Balance:**
├ Total: {sol_total_display} SOL
├ Spendable: {sol_spendable_display} SOL
├ wSOL: {wsol_display} SOL
└ USD: ${balance_usd:.2f}

📈 **Trading:**
├ Status: {"✅ LIVE" if self.trade_cfg.enabled and not self.trade_cfg.dry_run else "🔴 DRY-RUN"}
├ Trades: {total_trades}
├ Open Positions: {open_positions}
└ Max/Trade: ${self.trade_cfg.max_trade_usd}

⏰ {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC"""
            
            await self.telegram_bot.send_message(message)
            logger.info(f"📱 Wallet report sent: {sol_total_display} SOL (${balance_usd:.2f})")
            
        except Exception as e:
            logger.error(f"Failed to send wallet report: {e}")
    
    async def _maybe_auto_trade(self, enriched: dict) -> None:
        if not getattr(self, "trader", None) or not getattr(self, "trade_cfg", None):
            return
        cfg = self.trade_cfg
        if not cfg.enabled:
            return
        # Risk gate: score / liq / util / cooldown
        mint = enriched.get("mint","")
        symbol = enriched.get("symbol", "")
        now = time.time()
        last = self._last_trade_ts.get(mint, 0)
        if (now - last) < cfg.cooldown_sec:
            return
        
        # Get data from metadata instead of "dex"
        metadata = enriched.get("metadata", {}) or {}
        score_raw = enriched.get("score")
        score = int(score_raw) if score_raw is not None else 0
        liq = float(metadata.get("liquidity_usd") or 0.0)
        vol = float(metadata.get("volume_24h_usd") or 0.0)
        
        # Calculate util
        util = (vol / liq) if liq > 0 else 0.0
        
        if score < cfg.min_score_to_buy or liq < cfg.min_liq_usd_to_buy:
            logger.debug(f"auto_trade_skip {mint[:8]}: score={score} liq={liq}")
            return
        if not (cfg.util_min <= util <= cfg.util_max):
            logger.debug(f"auto_trade_skip {mint[:8]}: util={util:.2f} out of bounds")
            return
        
        # Estimate prices for sizing
        sol_price = float(os.getenv("SOL_PRICE_FALLBACK", "208"))
        token_price = float(metadata.get("price_usd") or 0.0)
        
        if token_price <= 0:
            logger.debug(f"auto_trade_skip {mint[:8]}: no price data")
            return
        
        # BUY
        try:
            logger.info("🔄 auto_trade_try %s score=%s liq=$%.0f util=%.2f", mint[:8], score, liq, util)
            res = await self.trader.buy_token_for_usd(mint, token_price, sol_price)
            
            if res.get("ok"):
                self._last_trade_ts[mint] = now
                sig = res.get("sig", "")
                logger.info("✅ auto_trade_buy_ok mint=%s sig=%s", mint[:8], sig)
                
                # Get actual trade details
                qty_atoms = int(res.get("qty_atoms") or 0)
                fill_price_usd = float(res.get("fill_price_usd") or 0.0)
                
                if qty_atoms > 0:
                    # Track position using new PositionManager
                    pos = {
                        "mint": mint,
                        "symbol": symbol,
                        "qty_atoms": qty_atoms,
                        "entry_price_usd": fill_price_usd,
                        "entry_time": now,
                        "entry_liquidity": liq,
                        "entry_volume": vol,
                        "status": "open",
                    }
                    self.positions.add_position(mint, pos)
                    
                    # Also update old system for compatibility
                    self._open_positions[mint] = {
                        "entry_price": fill_price_usd,
                        "entry_time": now,
                        "entry_volume": vol,
                        "entry_liquidity": liq,
                        "entry_symbol": symbol
                    }
                    self._save_positions()  # Save to disk
                
                # Send detailed Telegram notification
                if self.telegram_bot and self.telegram_bot.enabled:
                    # Get current balance
                    sol_balance = await self.trader.get_sol_balance()
                    trade_size_sol = cfg.max_trade_usd / sol_price
                    
                    message = f"""🟢 **AUTO-BUY EXECUTED**

🪙 **Token:** `{mint[:8]}...{mint[-8:]}`
📛 **Symbol:** {symbol}
💰 **Amount:** ~{trade_size_sol:.4f} SOL (${cfg.max_trade_usd})
💵 **Price:** ${token_price:.8f}

📊 **Metrics:**
├ Score: {score}
├ Liq: ${liq:,.0f}
└ Util: {util:.2f}

💼 **Wallet:**
└ Balance: {sol_balance:.4f} SOL

                        🔗 **Tx:** `{str(sig)[:16]}...{str(sig)[-16:]}`"""
                    
                    await self.telegram_bot.send_message(message)
            else:
                reason = res.get("reason", "unknown")
                logger.info("⚠️ auto_trade_buy_skip mint=%s reason=%s", mint[:8], reason)
                
                # Send skip notification for important reasons
                if reason.startswith("insufficient_balance") or reason == "cant_sell_probe_fail":
                    if self.telegram_bot and self.telegram_bot.enabled:
                        await self.telegram_bot.send_message(
                            f"⚠️ **BUY SKIPPED**\n\n🪙 `{mint[:8]}...`\n📛 {symbol}\n❌ Reason: {reason}"
                        )
        except Exception as e:
            logger.exception(f"❌ auto_trade_buy_error: {e}")
            # Send error notification
            if self.telegram_bot and self.telegram_bot.enabled:
                try:
                    await self.telegram_bot.send_message(
                        f"❌ **BUY ERROR**\n\n🪙 `{mint[:8]}...`\n📛 {symbol}\n⚠️ Error: {str(e)[:100]}"
                    )
                except:
                    pass

    async def _check_sell_conditions(self, mint: str, current_data: dict) -> bool:
        """Check if position should be sold based on current market data"""
        if mint not in self._open_positions:
            return False
        
        position = self._open_positions[mint]
        entry_price = position["entry_price"]
        entry_time = position["entry_time"]
        entry_volume = position["entry_volume"]
        entry_liquidity = position["entry_liquidity"]
        
        current_price = float(current_data.get("price_usd", 0))
        current_volume = float(current_data.get("volume_24h_usd", 0))
        current_liquidity = float(current_data.get("liquidity_usd", 0))
        current_time = time.time()
        
        # 1. Take Profit: +100%
        if current_price > 0 and entry_price > 0:
            price_change_pct = ((current_price - entry_price) / entry_price) * 100
            if price_change_pct >= 100:
                logger.info(f"🎯 TAKE PROFIT: {mint[:8]} +{price_change_pct:.1f}%")
                return True
        
        # 2. Stop Loss: -30%
        if current_price > 0 and entry_price > 0:
            price_change_pct = ((current_price - entry_price) / entry_price) * 100
            if price_change_pct <= -30:
                logger.info(f"🛑 STOP LOSS: {mint[:8]} {price_change_pct:.1f}%")
                return True
        
        # 3. Time-based exit: 48h
        if (current_time - entry_time) > 172800:  # 48 hours
            logger.info(f"⏰ TIME EXIT: {mint[:8]} after 48h")
            return True
        
        # 4. AGGRESSIVE Volume/Liquidity exit
        if entry_volume > 0 and current_volume < (entry_volume * 0.2):  # Volume < 20%
            logger.info(f"📉 VOLUME EXIT: {mint[:8]} volume dropped to {current_volume/entry_volume*100:.1f}%")
            return True
        
        if entry_liquidity > 0 and current_liquidity < (entry_liquidity * 0.5):  # Liquidity < 50%
            logger.info(f"💧 LIQUIDITY EXIT: {mint[:8]} liquidity dropped to {current_liquidity/entry_liquidity*100:.1f}%")
            return True
        
        if current_volume < 1000:  # Volume < $1000
            logger.info(f"📉 LOW VOLUME EXIT: {mint[:8]} volume < $1000")
            return True
        
        return False

    async def _sell_position(self, mint: str, reason: str) -> bool:
        """Sell a position and remove from tracking"""
        if mint not in self._open_positions:
            return False
        
        try:
            position = self._open_positions[mint]
            symbol = position["entry_symbol"]
            
            logger.info(f"🔄 SELLING: {mint[:8]} ({symbol}) - {reason}")
            
            # Get current SOL price
            sol_price = float(os.getenv("SOL_PRICE_FALLBACK", "208"))
            
            # Sell position
            res = await self.trader.sell_token_for_base(mint, sol_price)
            
            if res.get("ok"):
                sig = res.get("sig", "")
                logger.info(f"✅ SELL SUCCESS: {mint[:8]} sig={sig}")
                
                # Remove from tracking
                del self._open_positions[mint]
                self._save_positions()  # Save to disk
                
                # Send Telegram notification
                if self.telegram_bot and self.telegram_bot.enabled:
                    message = f"""🔴 **POSITION SOLD**

🪙 **Token:** `{mint[:8]}...{mint[-8:]}`
📛 **Symbol:** {symbol}
📊 **Reason:** {reason}
🔗 **Tx:** `{str(sig)[:16]}...{str(sig)[-16:]}`"""
                    
                    await self.telegram_bot.send_message(message)
                
                return True
            else:
                logger.error(f"❌ SELL FAILED: {mint[:8]} reason={res.get('reason')}")
                return False
                
        except Exception as e:
            logger.exception(f"❌ SELL ERROR: {mint[:8]} error={e}")
            return False

    async def _check_and_sell_positions(self, current_token_data: dict) -> None:
        """Check all open positions and sell if conditions are met"""
        if not self._open_positions:
            return
        
        current_mint = current_token_data.get("mint", "")
        current_metadata = current_token_data.get("metadata", {})
        
        # Check each open position
        positions_to_sell = []
        for mint, position in self._open_positions.items():
            # Use current token data if it matches, otherwise use position data
            if mint == current_mint:
                check_data = current_metadata
            else:
                # For other positions, we'd need to fetch current data
                # For now, skip non-current positions
                continue
            
            should_sell = await self._check_sell_conditions(mint, check_data)
            if should_sell:
                positions_to_sell.append(mint)
        
        # Sell positions that meet criteria
        for mint in positions_to_sell:
            position = self._open_positions[mint]
            entry_price = position["entry_price"]
            current_price = float(current_metadata.get("price_usd", 0))
            
            if current_price > 0 and entry_price > 0:
                price_change_pct = ((current_price - entry_price) / entry_price) * 100
                if price_change_pct >= 100:
                    reason = f"Take Profit (+{price_change_pct:.1f}%)"
                elif price_change_pct <= -30:
                    reason = f"Stop Loss ({price_change_pct:.1f}%)"
                else:
                    reason = "Volume/Liquidity Exit"
            else:
                reason = "Volume/Liquidity Exit"
            
            await self._sell_position(mint, reason)

    def _load_positions(self) -> None:
        """Load positions from file on startup"""
        try:
            if os.path.exists(self._positions_file):
                with open(self._positions_file, 'r') as f:
                    data = json.load(f)
                    # Convert string keys back to float where needed
                    for mint, position in data.items():
                        position["entry_price"] = float(position["entry_price"])
                        position["entry_time"] = float(position["entry_time"])
                        position["entry_volume"] = float(position["entry_volume"])
                        position["entry_liquidity"] = float(position["entry_liquidity"])
                    self._open_positions = data
                    logger.info(f"📂 Loaded {len(self._open_positions)} positions from {self._positions_file}")
        except Exception as e:
            logger.error(f"Failed to load positions: {e}")
            self._open_positions = {}

    def _save_positions(self) -> None:
        """Save positions to file"""
        try:
            with open(self._positions_file, 'w') as f:
                json.dump(self._open_positions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save positions: {e}")

    async def _force_sell_all_positions(self) -> None:
        """Force sell all positions on startup to get cash back"""
        if not self._open_positions:
            logger.info("📊 No positions to sell on startup")
            return
        
        logger.info(f"🔄 FORCE SELLING {len(self._open_positions)} positions on startup...")
        
        positions_to_sell = list(self._open_positions.keys())
        for mint in positions_to_sell:
            position = self._open_positions[mint]
            symbol = position["entry_symbol"]
            
            logger.info(f"🔄 FORCE SELL: {mint[:8]} ({symbol}) - Startup cleanup")
            
            try:
                # Get current SOL price
                sol_price = float(os.getenv("SOL_PRICE_FALLBACK", "208"))
                
                # Sell position
                res = await self.trader.sell_token_for_base(mint, sol_price)
                
                if res.get("ok"):
                    sig = res.get("sig", "")
                    logger.info(f"✅ FORCE SELL SUCCESS: {mint[:8]} sig={sig}")
                    
                    # Remove from tracking
                    del self._open_positions[mint]
                    self._save_positions()
                    
                    # Send Telegram notification
                    if self.telegram_bot and self.telegram_bot.enabled:
                        message = f"""🔴 **FORCE SELL (STARTUP)**

🪙 **Token:** `{mint[:8]}...{mint[-8:]}`
📛 **Symbol:** {symbol}
📊 **Reason:** Startup cleanup
🔗 **Tx:** `{str(sig)[:16]}...{str(sig)[-16:]}`"""
                        
                        await self.telegram_bot.send_message(message)
                else:
                    logger.warning(f"⚠️ FORCE SELL FAILED: {mint[:8]} reason={res.get('reason')} (will let ReconcileWorker handle)")
                    # Don't remove from tracking - let ReconcileWorker handle it later
                    
            except Exception as e:
                logger.warning(f"⚠️ FORCE SELL ERROR: {mint[:8]} error={e} (will let ReconcileWorker handle)")
                # Don't remove from tracking - let ReconcileWorker handle it later
        
        logger.info(f"✅ Force sell completed. {len(self._open_positions)} positions remaining.")


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
