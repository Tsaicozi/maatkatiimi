# config.py
from __future__ import annotations
import os
import yaml
import dataclasses
import time
import copy
from dataclasses import dataclass, field
from typing import Optional

def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None: return default
    return v.lower() in ("1", "true", "yes", "y", "on")

def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    return int(v) if v is not None and v.strip() != "" else default

def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    return float(v) if v is not None and v.strip() != "" else default

def _env_str(name: str, default: Optional[str]) -> Optional[str]:
    v = os.getenv(name)
    return v if v is not None and v.strip() != "" else default

def _filter_fields(dc_cls, data: dict) -> dict:
    """Suodata tuntemattomat kentät dataclass:sta"""
    allowed = {f.name for f in dataclasses.fields(dc_cls)}
    return {k: v for k, v in (data or {}).items() if k in allowed}

@dataclass
class SourcesCfg:
    raydium: bool = True
    orca: bool = False
    pumpfun: bool = True
    birdeye_ws: bool = True
    pumpportal_ws: bool = True
    geckoterminal: bool = True
    dexscreener: bool = True
    helius_logs: bool = True    # UUSI

@dataclass
class FreshPassCfg:
    enabled: bool = True
    ttl_sec: int = 90
    min_unique_buyers: int = 0
    min_trades: int = 0
    sources: tuple[str, ...] = ("pumpportal_ws","helius_logs")

@dataclass
class DiscoveryCfg:
    min_liq_usd: float = 3000.0
    min_liq_fresh_usd: float = 1200.0
    score_threshold: float = 0.65
    min_score_cap_delta: float = 0.10
    max_top10_share: float = 0.95
    max_top10_share_fresh: float = 0.98
    max_queue: int = 2000
    fresh_window_sec: int = 90
    trade_min_unique_buyers: int = 3
    trade_min_trades: int = 5
    candidate_ttl_sec: int = 600
    sources: SourcesCfg = field(default_factory=SourcesCfg)
    fresh_pass: FreshPassCfg = field(default_factory=FreshPassCfg)
    helius_programs: list = field(default_factory=lambda: [
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"   # SPL Token (InitializeMint*)
    ])

@dataclass
class RiskCfg:
    require_lp_locked: bool = True
    max_top10_share: float = 0.90
    require_renounced: bool = True

@dataclass
class TradingCfg:
    enabled: bool = False
    paper_trade: bool = True
    default_amount_sol: float = 0.01
    slippage: float = 10.0
    priority_fee: float = 0.00001
    pool: str = "auto"
    min_score_for_trade: Optional[float] = None
    sniper_enabled: bool = False
    sniper_buy_amount_sol: float = 0.01
    sniper_sell_delay_sec: float = 20.0
    sniper_sell_amount: str = "100%"
    sniper_sources: tuple[str, ...] = ("pumpportal_ws",)

@dataclass
class TelegramCfg:
    cooldown_seconds: int = 900
    batch_summary: bool = True
    rate_limit_seconds: int | None = None  # alias
    max_backoff_seconds: int = 30  # Lisätty puuttuva kenttä
    backoff_multiplier: float = 2.0  # Lisätty puuttuva kenttä
    mint_cooldown_seconds: int = 1800
    enable_command_polling: bool = True
    allowed_chat_id: int | None = None
    poll_interval_sec: float = 1.0

    def __post_init__(self):
        if self.rate_limit_seconds is not None:
            self.cooldown_seconds = int(self.rate_limit_seconds)

@dataclass
class IOCfg:
    rpc_endpoints: list = field(default_factory=lambda: [
        "https://api.mainnet-beta.solana.com",
        "https://solana-api.projectserum.com", 
        "https://rpc.ankr.com/solana"
    ])
    rpc_timeout_sec: float = 3.0
    ws_connect_timeout_sec: float = 5.0
    retry_max: int = 4
    rpc: dict = field(default_factory=lambda: {
        "url": "https://mainnet.helius-rpc.com/?api-key=your-key",
        "ws_url": "wss://mainnet.helius-rpc.com/?api-key=your-key"
    })
    pump_portal: dict = field(default_factory=lambda: {
        "base_url": "https://pumpportal.fun",
        "base_ws": "wss://pumpportal.fun/api/data",
        "api_key": None,
        "poll_interval_sec": 2
    })
    trade_api: dict = field(default_factory=lambda: {
        "base_url": "https://pumpportal.fun"
    })
    birdeye: dict = field(default_factory=lambda: {
        "api_key": None,
        "ws_url": "wss://public-api.birdeye.so/socket"
    })

@dataclass
class MetricsCfg:
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 9108
    namespace: str = "hybrid_bot"

@dataclass
class RuntimeCfg:
    timezone: str = "Europe/Helsinki"
    test_max_cycles: Optional[int] = None
    test_max_runtime_sec: Optional[float] = None
    kill_switch_path: Optional[str] = None

@dataclass
class AppCfg:
    discovery: DiscoveryCfg = field(default_factory=DiscoveryCfg)
    risk: RiskCfg = field(default_factory=RiskCfg)
    trading: TradingCfg = field(default_factory=TradingCfg)
    telegram: TelegramCfg = field(default_factory=TelegramCfg)
    io: IOCfg = field(default_factory=IOCfg)
    metrics: MetricsCfg = field(default_factory=MetricsCfg)
    runtime: RuntimeCfg = field(default_factory=RuntimeCfg)

def load_config(path: str = "config.yaml") -> AppCfg:
    data = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    # Hoida Telegram alias
    tel_raw = data.get("telegram") or {}
    if "rate_limit_seconds" in tel_raw and "cooldown_seconds" not in tel_raw:
        tel_raw["cooldown_seconds"] = tel_raw["rate_limit_seconds"]

    # Mapaus -> dataclass (suodata tuntemattomat kentät)
    discovery_data = data.get("discovery", {})
    sources_data = discovery_data.pop("sources", {})  # Poista sources discovery_datasta
    fresh_pass_data = discovery_data.pop("fresh_pass", {})  # Poista fresh_pass discovery_datasta
    
    cfg = AppCfg(
        discovery=DiscoveryCfg(
            **_filter_fields(DiscoveryCfg, discovery_data),
            sources=SourcesCfg(**_filter_fields(SourcesCfg, sources_data)),
            fresh_pass=FreshPassCfg(**_filter_fields(FreshPassCfg, fresh_pass_data))
        ),
        risk=RiskCfg(**_filter_fields(RiskCfg, data.get("risk"))),
        trading=TradingCfg(**_filter_fields(TradingCfg, data.get("trading"))),
        telegram=TelegramCfg(**_filter_fields(TelegramCfg, tel_raw)),
        io=IOCfg(**_filter_fields(IOCfg, data.get("io"))),
        metrics=MetricsCfg(**_filter_fields(MetricsCfg, data.get("metrics"))),
        runtime=RuntimeCfg(**_filter_fields(RuntimeCfg, data.get("runtime"))),
    )

    # Ympäristömuuttujilla override (tarvituimmat)
    cfg.metrics.enabled = _env_bool("METRICS_ENABLED", cfg.metrics.enabled)
    cfg.metrics.port = _env_int("METRICS_PORT", cfg.metrics.port)
    cfg.discovery.score_threshold = _env_float("DISCOVERY_SCORE_THRESHOLD", cfg.discovery.score_threshold)
    cfg.discovery.min_liq_usd = _env_float("DISCOVERY_MIN_LIQ_USD", cfg.discovery.min_liq_usd)
    cfg.discovery.min_liq_fresh_usd = _env_float("DISCOVERY_MIN_LIQ_FRESH_USD", cfg.discovery.min_liq_fresh_usd)
    cfg.discovery.min_score_cap_delta = _env_float("DISCOVERY_MIN_SCORE_CAP_DELTA", cfg.discovery.min_score_cap_delta)
    cfg.discovery.max_top10_share = _env_float("DISCOVERY_MAX_TOP10_SHARE", cfg.discovery.max_top10_share)
    cfg.discovery.max_top10_share_fresh = _env_float("DISCOVERY_MAX_TOP10_SHARE_FRESH", cfg.discovery.max_top10_share_fresh)
    cfg.discovery.candidate_ttl_sec = _env_int("DISCOVERY_CANDIDATE_TTL_SEC", cfg.discovery.candidate_ttl_sec) if os.getenv("DISCOVERY_CANDIDATE_TTL_SEC") else cfg.discovery.candidate_ttl_sec
    cfg.runtime.test_max_cycles = _env_int("TEST_MAX_CYCLES", cfg.runtime.test_max_cycles) if os.getenv("TEST_MAX_CYCLES") else cfg.runtime.test_max_cycles
    cfg.runtime.test_max_runtime_sec = _env_float("TEST_MAX_RUNTIME", cfg.runtime.test_max_runtime_sec) if os.getenv("TEST_MAX_RUNTIME") else cfg.runtime.test_max_runtime_sec
    
    # Trading ENV-override
    cfg.trading.enabled = _env_bool("TRADING_ENABLED", cfg.trading.enabled)
    cfg.trading.paper_trade = _env_bool("TRADING_PAPER_TRADE", cfg.trading.paper_trade)
    cfg.trading.default_amount_sol = _env_float("TRADING_DEFAULT_AMOUNT_SOL", cfg.trading.default_amount_sol)
    cfg.trading.slippage = _env_float("TRADING_SLIPPAGE", cfg.trading.slippage)
    cfg.trading.priority_fee = _env_float("TRADING_PRIORITY_FEE", cfg.trading.priority_fee)
    cfg.trading.pool = _env_str("TRADING_POOL", cfg.trading.pool)
    if os.getenv("TRADING_MIN_SCORE_FOR_TRADE"):
        cfg.trading.min_score_for_trade = _env_float("TRADING_MIN_SCORE_FOR_TRADE", cfg.trading.min_score_for_trade)
    cfg.trading.sniper_enabled = _env_bool("TRADING_SNIPER_ENABLED", cfg.trading.sniper_enabled)
    cfg.trading.sniper_buy_amount_sol = _env_float("TRADING_SNIPER_BUY_AMOUNT_SOL", cfg.trading.sniper_buy_amount_sol)
    cfg.trading.sniper_sell_delay_sec = _env_float("TRADING_SNIPER_SELL_DELAY_SEC", cfg.trading.sniper_sell_delay_sec)
    cfg.trading.sniper_sell_amount = _env_str("TRADING_SNIPER_SELL_AMOUNT", cfg.trading.sniper_sell_amount)
    sniper_sources_env = _env_str("TRADING_SNIPER_SOURCES", None)
    if sniper_sources_env:
        cfg.trading.sniper_sources = tuple(s.strip() for s in sniper_sources_env.split(",") if s.strip()) or cfg.trading.sniper_sources
    
    # Telegram ENV-override
    cfg.telegram.cooldown_seconds = _env_int("TELEGRAM_COOLDOWN_SECONDS", cfg.telegram.cooldown_seconds)
    cfg.telegram.max_backoff_seconds = _env_int("TELEGRAM_MAX_BACKOFF", cfg.telegram.max_backoff_seconds)
    cfg.telegram.backoff_multiplier = _env_float("TELEGRAM_BACKOFF_MULTIPLIER", cfg.telegram.backoff_multiplier)
    cfg.telegram.mint_cooldown_seconds = _env_int("TELEGRAM_MINT_COOLDOWN_SECONDS", cfg.telegram.mint_cooldown_seconds)
    cfg.telegram.enable_command_polling = _env_bool("TELEGRAM_ENABLE_COMMAND_POLLING", cfg.telegram.enable_command_polling)
    cfg.telegram.allowed_chat_id = _env_int("TELEGRAM_ALLOWED_CHAT_ID", cfg.telegram.allowed_chat_id)
    cfg.telegram.poll_interval_sec = _env_float("TELEGRAM_POLL_INTERVAL_SEC", cfg.telegram.poll_interval_sec)

    # Helius API - ota avain ja URL:t ympäristöstä
    helius_api_key = _env_str("HELIUS_API_KEY", None)
    helius_rest_url = _env_str("HELIUS_RPC_URL", None)
    helius_ws_url = _env_str("HELIUS_WS_URL", None)
    if helius_api_key:
        host = _env_str("HELIUS_HOST", "mainnet.helius-rpc.com") or "mainnet.helius-rpc.com"
        helius_rest_url = helius_rest_url or f"https://{host}/?api-key={helius_api_key}"
        helius_ws_url = helius_ws_url or f"wss://{host}/?api-key={helius_api_key}"

    if helius_rest_url or helius_ws_url:
        try:
            if isinstance(cfg.io.rpc, dict):
                if helius_rest_url:
                    cfg.io.rpc["url"] = helius_rest_url
                if helius_ws_url:
                    cfg.io.rpc["ws_url"] = helius_ws_url
                if helius_api_key:
                    cfg.io.rpc["api_key"] = helius_api_key
        except Exception:
            pass

        if helius_rest_url:
            try:
                existing = list(cfg.io.rpc_endpoints or [])
            except Exception:
                existing = []
            deduped = [helius_rest_url] + [url for url in existing if url != helius_rest_url]
            cfg.io.rpc_endpoints = deduped
    
    return cfg


# --- Lightweight cached loader for performance-critical paths ---
_CFG_CACHE: dict[str, tuple[float, float, AppCfg]] = {}

def load_config_cached(ttl_sec: int = 30, path: str = "config.yaml") -> AppCfg:
    """
    Cached loader that avoids re-parsing YAML repeatedly.
    Cache invalidates if TTL expires or file mtime changes.

    Returns a deepcopy of the cached config to avoid accidental mutation leaks.
    """
    try:
        mtime = os.path.getmtime(path) if os.path.exists(path) else -1.0
    except Exception:
        mtime = -1.0

    now = time.time()
    cached = _CFG_CACHE.get(path)
    if cached:
        loaded_at, last_mtime, cfg = cached
        if (now - loaded_at) < float(ttl_sec) and last_mtime == mtime:
            return copy.deepcopy(cfg)

    cfg = load_config(path)
    _CFG_CACHE[path] = (now, mtime, cfg)
    return copy.deepcopy(cfg)
