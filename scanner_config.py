from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _env_int(name: str, default: int, *, fallback: Optional[str] = None) -> int:
    value = os.getenv(name)
    if value is None and fallback:
        value = os.getenv(fallback)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float, *, fallback: Optional[str] = None) -> float:
    value = os.getenv(name)
    if value is None and fallback:
        value = os.getenv(fallback)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass
class ScannerConfig:
    max_retry_attempts: int = _env_int("SCANNER_MAX_RETRY_ATTEMPTS", 4, fallback="SCANNER_MAX_RETRIES")
    retry_initial_delay: float = _env_float("SCANNER_RETRY_INITIAL_DELAY", 5.0, fallback="SCANNER_RETRY_INITIAL")
    retry_backoff: float = _env_float("SCANNER_RETRY_BACKOFF", 2.0)
    retry_max_delay: float = _env_float("SCANNER_RETRY_MAX_DELAY", 60.0)
    retry_fetch_timeout: float = _env_float("SCANNER_RETRY_FETCH_TIMEOUT", 12.0)
    memory_cleanup_interval: float = _env_float("SCANNER_MEMORY_CLEANUP_INTERVAL", 300.0)  # seconds
    liquidity_history_ttl: float = _env_float("SCANNER_LIQUIDITY_HISTORY_TTL", 3600.0, fallback="SCANNER_LIQUIDITY_TTL")   # seconds
    breaker_failure_threshold: int = _env_int("SCANNER_BREAKER_THRESHOLD", 5)
    breaker_timeout: float = _env_float("SCANNER_BREAKER_TIMEOUT", 60.0)
    # --- Kynnykset / heuristiikat ---
    min_liquidity_usd: float = _env_float("SCANNER_MIN_LIQUIDITY_USD", 20_000.0)
    min_volume24h_usd: float = _env_float("SCANNER_MIN_VOLUME24H_USD", 30_000.0)
    min_buyers_30m: int = _env_int("SCANNER_MIN_BUYERS_30M", 7)
    min_age_min: int = _env_int("SCANNER_MIN_AGE_MIN", 3)
    util_min: float = _env_float("SCANNER_UTIL_MIN", 0.3)
    util_max: float = _env_float("SCANNER_UTIL_MAX", 8.0)
    util_enabled: bool = _env_bool("SCANNER_UTIL_ENABLED", True)
    min_publish_score: int = _env_int("SCANNER_MIN_PUBLISH_SCORE", 70)
    # Poolin "aktiivisuus" ennen pisteytystä
    pool_min_trades24h: int = _env_int("SCANNER_POOL_MIN_TRADES24H", 20)
    pool_max_last_trade_min: int = _env_int("SCANNER_POOL_MAX_LAST_TRADE_MIN", 10)
    pool_min_age_min: int = _env_int("SCANNER_POOL_MIN_AGE_MIN", 0)
    enforce_active_pool: bool = _env_bool("SCANNER_ENFORCE_ACTIVE_POOL", True)
    # FDV sanity
    enable_fdv_sanity: bool = _env_bool("SCANNER_ENABLE_FDV_SANITY", True)
    fdv_sanity_tolerance: float = _env_float("SCANNER_FDV_SANITY_TOLERANCE", 0.30)
    # buyers30m-käyttäytyminen
    require_buyers30m: bool = _env_bool("SCANNER_REQUIRE_BUYERS30M", True)
    # Jos True = pehmeä pisteytys (ei kovaa droppia) jos buyers30m alle rajan.
    buyers30m_soft_mode: bool = _env_bool("SCANNER_BUYERS30M_SOFT_MODE", False)
    # --- Symboli / placeholder -käyttäytyminen ---
    strict_placeholder: bool = _env_bool("SCANNER_STRICT_PLACEHOLDER", False)        # True => TOKEN_* = kova droppi
    placeholder_penalty: int = _env_int("SCANNER_PLACEHOLDER_PENALTY", 10)           # pistevähennys jos placeholder mutta ei strict
    min_symbol_len: int = _env_int("SCANNER_MIN_SYMBOL_LEN", 2)
    max_symbol_len: int = _env_int("SCANNER_MAX_SYMBOL_LEN", 15)
    # --- Raydium-watcherin asetukset ---
    enable_raydium_watcher: bool = _env_bool("SCANNER_ENABLE_RAYDIUM_WATCHER", True)
    raydium_quote_allowlist: tuple[str, ...] = ("USDC", "USDT", "SOL")
    raydium_min_quote_usd: float = _env_float("SCANNER_RAYDIUM_MIN_QUOTE_USD", 3000.0)   # alkureservin kynnys (arvio)
    raydium_programs: tuple[str, ...] = ()  # jos tyhjä -> luetaan envistä main.py:ssä
