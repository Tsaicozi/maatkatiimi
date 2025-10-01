import os
import time
import json
import math
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import argparse

import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv
from pycoingecko import CoinGeckoAPI

# =============================
# Config & setup
# =============================
load_dotenv('.env2')  # Käytä .env2 tiedostoa

LOG_FILE = os.getenv("LOG_FILE", "crypto_new_token_screener.log")
MAX_LOG_BYTES = int(os.getenv("MAX_LOG_BYTES", "1048576"))  # 1 MB
BACKUP_COUNT = int(os.getenv("BACKUP_COUNT", "3"))

_base_logger = logging.getLogger("screener")
_base_logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
_base_logger.addHandler(handler)
RUN_ID = datetime.now(timezone.utc).isoformat()
logger = logging.LoggerAdapter(_base_logger, extra={"run_id": RUN_ID})

# Required envs
COINGECKO_PRO_KEY = os.getenv("COINGECKO_PRO_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not COINGECKO_PRO_KEY:
    logger.error("Missing COINGECKO_PRO_KEY in environment")
if not TELEGRAM_TOKEN:
    logger.error("Missing TELEGRAM_TOKEN in environment")
if not TELEGRAM_CHAT_ID:
    logger.error("Missing TELEGRAM_CHAT_ID in environment")

# API clients
cg = CoinGeckoAPI(api_key=COINGECKO_PRO_KEY)

# =============================
# Defaults (overridable by env/CLI)
# =============================
HISTORY_DAYS = int(os.getenv("HISTORY_DAYS", "90"))  # allowed: 1/7/14/30/90/180
RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
EMA_SHORT_SPAN = int(os.getenv("EMA_SHORT_SPAN", "5"))
EMA_LONG_SPAN = int(os.getenv("EMA_LONG_SPAN", "20"))
ATR_PERIOD = int(os.getenv("ATR_PERIOD", "14"))
MOMENTUM_THRESHOLD_24H = float(os.getenv("MOMENTUM_THRESHOLD_24H", "10.0"))  # %
VOL_INCREASE_THRESHOLD = float(os.getenv("VOL_INCREASE_THRESHOLD", "1.5"))     # x average
VOL_ZSCORE_THRESHOLD = float(os.getenv("VOL_ZSCORE_THRESHOLD", "2.0"))          # optional additional trigger
NOUSU_60D_THRESHOLD = float(os.getenv("NOUSU_60D_THRESHOLD", "0.9"))            # 90% over 60d
MAX_RETRACEMENT_THRESHOLD = float(os.getenv("MAX_RETRACEMENT_THRESHOLD", "0.25"))
MIN_24H_VOLUME_USD = float(os.getenv("MIN_24H_VOLUME_USD", "200000"))
PRICE_MIN = float(os.getenv("PRICE_MIN", "0.0001"))
MARKET_CAP_MIN = float(os.getenv("MARKET_CAP_MIN", "1000000"))

COOLDOWN_HOURS = int(os.getenv("COOLDOWN_HOURS", "48"))
FOUND_TICKERS_FILE = os.getenv("FOUND_TICKERS_FILE", "found_new_tokens.json")

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
SAVE_RESULTS_CSV = os.getenv("SAVE_RESULTS_CSV", "0") == "1"
RESULTS_PATH = os.getenv("RESULTS_PATH", "results.csv")

# Dynamic data length requirements based on token age
MIN_DATA_LEN_NEW = 3      # For tokens < 7 days old
_est_default = max(EMA_LONG_SPAN + 1, RSI_PERIOD + 1, ATR_PERIOD + 2, 20) + 5
MIN_DATA_LEN_ESTABLISHED = int(os.getenv("MIN_DATA_LEN_ESTABLISHED", str(_est_default)))  # For older tokens
NEW_TOKEN_AGE_DAYS = 7    # Threshold for considering a token "new"

# Strategy toggles (env overridable; also CLI flags)
ENABLE_MOMC = os.getenv("ENABLE_MOMC", "0") == "1"
ENABLE_BASE = os.getenv("ENABLE_BASE", "0") == "1"

# NEW / MID / EST logic
NEW_TOKEN_MAX_DAYS = int(os.getenv("NEW_TOKEN_MAX_DAYS", "7"))    # <=7 → NEW
MID_TOKEN_MAX_DAYS = int(os.getenv("MID_TOKEN_MAX_DAYS", "25"))   # 8–25 → MID, >=26 → EST
NEW_MIN_DATA_LEN   = int(os.getenv("NEW_MIN_DATA_LEN", "10"))
MID_MIN_DATA_LEN   = int(os.getenv("MID_MIN_DATA_LEN", "16"))

# Relaxed thresholds for new/mid momentum
RELAXED_VOL_INCREASE = float(os.getenv("RELAXED_VOL_INCREASE", "1.2"))
RELAXED_VOL_Z        = float(os.getenv("RELAXED_VOL_Z", "1.5"))
REQUIRE_CONSECUTIVE_NEW = os.getenv("REQUIRE_CONSECUTIVE_NEW", "0") == "1"

# EST-specific thresholds (MOMC)
VOL_Z_EST = float(os.getenv("VOL_Z_EST", "1.6"))
VOL_PCT_RANK_EST = float(os.getenv("VOL_PCT_RANK_EST", "0.70"))

# Trading strategy parameters
PORTFOLIO_VALUE = float(os.getenv("PORTFOLIO_VALUE", "10000.0"))  # USD
RISK_NEW = float(os.getenv("RISK_NEW", "0.02"))  # 2% risk per NEW trade
RISK_EST = float(os.getenv("RISK_EST", "0.015"))  # 1.5% risk per EST trade
STOP_NEW = float(os.getenv("STOP_NEW", "0.20"))  # 20% stop loss for NEW
STOP_EST = float(os.getenv("STOP_EST", "0.15"))  # 15% stop loss for EST
TP1_NEW = float(os.getenv("TP1_NEW", "0.50"))  # 50% take profit 1 for NEW
TP2_NEW = float(os.getenv("TP2_NEW", "1.00"))  # 100% take profit 2 for NEW
TP1_EST = float(os.getenv("TP1_EST", "0.30"))  # 30% take profit 1 for EST
TP2_EST = float(os.getenv("TP2_EST", "0.60"))  # 60% take profit 2 for EST
MAX_ALLOC_PCT = float(os.getenv("MAX_ALLOC_PCT", "0.10"))  # 10% max allocation per trade
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "5"))  # Max open positions
TRAIL_ATR_NEW = float(os.getenv("TRAIL_ATR_NEW", "2.0"))  # ATR multiplier for trailing stop NEW
TRAIL_ATR_EST = float(os.getenv("TRAIL_ATR_EST", "1.5"))  # ATR multiplier for trailing stop EST
TIME_MAX_H_NEW_H = int(os.getenv("TIME_MAX_H_NEW_H", "24"))  # Max hold time for NEW (hours)
TIME_MAX_H_EST_H = int(os.getenv("TIME_MAX_H_EST_H", "72"))  # Max hold time for EST (hours)
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"  # Dry run mode
ORDERS_STATE_FILE = os.getenv("ORDERS_STATE_FILE", "orders_state.json")

# =============================
# Utilities
# =============================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_found_tickers() -> Dict[str, str]:
    if os.path.exists(FOUND_TICKERS_FILE):
        try:
            with open(FOUND_TICKERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {FOUND_TICKERS_FILE}: {e}")
    return {}


def save_found_tickers(found: Dict[str, str]) -> None:
    try:
        with open(FOUND_TICKERS_FILE, "w", encoding="utf-8") as f:
            json.dump(found, f)
    except Exception as e:
        logger.error(f"Error writing {FOUND_TICKERS_FILE}: {e}")


def within_cooldown(last_iso: str, cooldown_hours: int) -> bool:
    try:
        last_dt = datetime.fromisoformat(last_iso)
        return datetime.now(timezone.utc) - last_dt < timedelta(hours=cooldown_hours)
    except Exception:
        return False


def load_orders_state() -> Dict[str, Any]:
    """Load trading orders state from file"""
    if os.path.exists(ORDERS_STATE_FILE):
        try:
            with open(ORDERS_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {ORDERS_STATE_FILE}: {e}")
    return {"open": [], "closed": []}


def save_orders_state(state: Dict[str, Any]) -> None:
    """Save trading orders state to file"""
    try:
        with open(ORDERS_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing {ORDERS_STATE_FILE}: {e}")


# =============================
# Retry / backoff
# =============================

def retry_call(fn, *args, tries: int = 3, backoff: float = 2.0, **kwargs):
    delay = 1.0
    for attempt in range(1, tries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == tries:
                logger.error(f"Retry failed for {fn.__name__}: {e}")
                raise
            logger.warning(f"Error on {fn.__name__} attempt {attempt}: {e}. Retrying in {delay:.1f}s")
            time.sleep(delay)
            delay *= backoff


# =============================
# Data IO – CoinGecko
# =============================

def get_new_coins(limit_ids: int = 150) -> List[Dict[str, Any]]:
    """Fetch latest added coins (PRO endpoint). Returns list of dicts with 'id' and 'symbol'."""
    data = retry_call(cg.get_coins_list_new)
    coins = data[:limit_ids]
    return coins


def get_markets_for_ids(ids: List[str]) -> List[Dict[str, Any]]:
    if not ids:
        return []
    out = []
    CHUNK = 100  # Avoid URL length limits
    for i in range(0, len(ids), CHUNK):
        chunk_ids = ids[i:i+CHUNK]
        ids_param = ",".join(chunk_ids)
        markets = retry_call(
            cg.get_coins_markets,
            vs_currency="usd",
            ids=ids_param,
            price_change_percentage="24h",
        ) or []
        out.extend(markets)
        time.sleep(0.3)  # gentle pacing
    return out


def get_unique_exchange_count(coin_id: str) -> int:
    """Return number of unique exchanges listing this coin (by exchange identifier)."""
    try:
        data = retry_call(
            cg.get_coin_by_id,
            id=coin_id,
            localization="false",
            tickers="true",
            market_data="false",
            community_data="false",
            developer_data="false",
            sparkline="false",
        )
        tickers = data.get("tickers", []) or []
        exch_ids = set()
        for t in tickers:
            m = t.get("market") or {}
            ident = m.get("identifier") or m.get("name")
            if ident:
                exch_ids.add(ident)
        return len(exch_ids)
    except Exception as e:
        logger.error(f"get_unique_exchange_count error for {coin_id}: {e}")
        return 0


def enforce_exchanges_min(candidates: List[Dict[str, str]], exchanges_min: int) -> List[Dict[str, str]]:
    if exchanges_min is None or exchanges_min <= 1:
        return candidates
    kept = []
    for c in candidates:
        cnt = get_unique_exchange_count(c["id"])
        logger.info(f"{c['symbol']} exchanges={cnt}")
        if cnt >= exchanges_min:
            kept.append(c)
        time.sleep(0.5)
    return kept


def get_price_and_volume(coin_id: str) -> Dict[str, float]:
    """Fetch current price and 24h volume for a single coin id."""
    try:
        m = retry_call(cg.get_coins_markets, vs_currency="usd", ids=coin_id)
        if not m:
            return {"price": float("nan"), "volume": 0.0}
        row = m[0]
        return {
            "price": float(row.get("current_price") or float("nan")),
            "volume": float(row.get("total_volume") or 0.0)
        }
    except Exception as e:
        logger.error(f"get_price_and_volume error for {coin_id}: {e}")
        return {"price": float("nan"), "volume": 0.0}


def fetch_ohlc_and_volume(coin_id: str) -> pd.DataFrame:
    """Return daily OHLC + daily volume (as daily max of 24h rolling volume)."""
    try:
        # Try shorter periods first for new tokens
        for days in [7, 14, 30, 90]:
            try:
                ohlc = retry_call(cg.get_coin_ohlc_by_id, id=coin_id, vs_currency="usd", days=days)
                if ohlc and len(ohlc) > 0:
                    break
            except:
                continue
        else:
            logger.debug(f"No OHLC data available for {coin_id}")
            return pd.DataFrame()
            
        df_ohlc = pd.DataFrame(ohlc, columns=["timestamp", "open", "high", "low", "close"])
        df_ohlc["date"] = pd.to_datetime(df_ohlc["timestamp"], unit="ms").dt.date

        # Try to get volume data
        try:
            market_chart = retry_call(cg.get_coin_market_chart_by_id, id=coin_id, vs_currency="usd", days=days)
            df_vol = pd.DataFrame(market_chart.get("total_volumes", []), columns=["timestamp", "volume"])
            if not df_vol.empty:
                df_vol["date"] = pd.to_datetime(df_vol["timestamp"], unit="ms").dt.date
                # Use daily 95% quantile of the 24h rolling volume as a robust daily volume proxy
                df_volume_daily = df_vol.groupby("date")["volume"].quantile(0.95).reset_index()
                df = pd.merge(df_ohlc, df_volume_daily, on="date", how="inner")
            else:
                # Fallback: use OHLC data only with estimated volume
                df = df_ohlc.copy()
                df["volume"] = 1000000  # Default volume for new tokens
        except:
            # Fallback: use OHLC data only with estimated volume
            df = df_ohlc.copy()
            df["volume"] = 1000000  # Default volume for new tokens

        df["Date"] = pd.to_datetime(df["date"])  # keep full datetime index if needed
        df.drop(columns=["date"], inplace=True)
        return df
    except Exception as e:
        logger.error(f"fetch_ohlc_and_volume error for {coin_id}: {e}")
        return pd.DataFrame()


# =============================
# Indicators
# =============================

def rsi_wilder(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()


def compute_indicators(df: pd.DataFrame, is_new_token: bool = False) -> Dict[str, Any]:
    df = df.copy()
    df["ema_short"] = df["close"].ewm(span=EMA_SHORT_SPAN, adjust=False).mean()
    df["ema_long"] = df["close"].ewm(span=EMA_LONG_SPAN, adjust=False).mean()
    df["rsi"] = rsi_wilder(df["close"], RSI_PERIOD)
    df["atr"] = atr(df, ATR_PERIOD)

    # Volatility proxy
    df["atr_pct"] = (df["atr"] / df["close"]).replace([np.inf, -np.inf], np.nan) * 100

    # Volume stats (using daily max of 24h rolling volumes)
    df["vol_ma20"] = df["volume"].rolling(window=20, min_periods=5).mean()
    df["vol_std20"] = df["volume"].rolling(window=20, min_periods=5).std()
    df["vol_z"] = (df["volume"] - df["vol_ma20"]) / df["vol_std20"]

    # HTF-style metrics
    if len(df) > 60:
        df["ret_60d"] = df["close"] / df["close"].shift(60) - 1
    else:
        df["ret_60d"] = 0

    high_rolling = df["high"].rolling(20, min_periods=5).max()
    low_rolling = df["low"].rolling(20, min_periods=5).min()
    df["max_retracement"] = (high_rolling - low_rolling) / high_rolling.replace(0, np.nan)

    # Donchian highs
    df["donchian_high10"] = df["high"].rolling(10, min_periods=5).max()
    df["donchian_high20"] = df["high"].rolling(20, min_periods=5).max()

    # Two-bar high
    two_bar_high = False
    if len(df) >= 3:
        two_bar_high = bool(df["close"].iloc[-1] > max(df["close"].iloc[-2], df["close"].iloc[-3]))

    # Volume percentile rank over last 20
    if len(df) >= 20:
        vol_pct_rank20 = df["volume"].iloc[-20:].rank(pct=True).iloc[-1]  # 0..1
    else:
        vol_pct_rank20 = float("nan")

    last = df.iloc[-1]

    # Require 2 consecutive days of volume breakout for more robust signal
    breakout = False
    if len(df) >= 2 and not math.isnan(last.get("vol_ma20", np.nan)) and last.get("vol_ma20", 0) > 0:
        recent = df.tail(2)
        # Both days must meet volume threshold
        cond_mult = (recent["volume"].iloc[-1] > VOL_INCREASE_THRESHOLD * recent["vol_ma20"].iloc[-1] and
                    recent["volume"].iloc[-2] > VOL_INCREASE_THRESHOLD * recent["vol_ma20"].iloc[-2])
        # Or z-score threshold for both days
        cond_z = (recent.get("vol_z", -np.inf).iloc[-1] > VOL_ZSCORE_THRESHOLD and
                 recent.get("vol_z", -np.inf).iloc[-2] > VOL_ZSCORE_THRESHOLD)
        breakout = bool(cond_mult or cond_z)
    elif not math.isnan(last.get("vol_ma20", np.nan)) and last.get("vol_ma20", 0) > 0:
        # Fallback to single day if insufficient data
        cond_mult = last["volume"] > VOL_INCREASE_THRESHOLD * last["vol_ma20"]
        cond_z = last.get("vol_z", -np.inf) > VOL_ZSCORE_THRESHOLD
        breakout = bool(cond_mult or cond_z)

    htf = bool((last.get("ret_60d", 0) > NOUSU_60D_THRESHOLD) and (last.get("max_retracement", 1) < MAX_RETRACEMENT_THRESHOLD))

    # Additional indicators for new tokens
    high_momentum = False
    volume_spike = False
    
    if is_new_token:
        # For new tokens: check 24h momentum and volume spikes
        if len(df) >= 2:
            price_change_24h = (last["close"] - df["close"].iloc[-2]) / df["close"].iloc[-2] * 100
            high_momentum = price_change_24h > 20.0  # 20% 24h gain
        
        # Volume spike: current volume > 3x average
        if last.get("vol_ma20", 0) > 0:
            volume_spike = last["volume"] > 3.0 * last["vol_ma20"]

    return {
        "current_price": float(last["close"]),
        "ema_bias_pct": float(((last["ema_short"] - last["ema_long"]) / last["ema_long"]) * 100) if last["ema_long"] else 0.0,
        "rsi": float(last.get("rsi", np.nan)),
        "atr_pct": float(last.get("atr_pct", np.nan)),
        "breakout": breakout,
        "htf": htf,
        "ret_60d": float(last.get("ret_60d", 0)),
        "max_retracement": float(last.get("max_retracement", 0)),
        "current_volume": float(last.get("volume", 0)),
        "avg_volume": float(last.get("vol_ma20", 0)),
        "vol_z": float(last.get("vol_z", np.nan)),
        "donchian_high10": float(df["donchian_high10"].iloc[-1]) if not df["donchian_high10"].isna().all() else float("nan"),
        "donchian_high20": float(df["donchian_high20"].iloc[-1]) if not df["donchian_high20"].isna().all() else float("nan"),
        "two_bar_high": bool(two_bar_high),
        "vol_pct_rank20": float(vol_pct_rank20),
        "high_momentum": high_momentum,
        "volume_spike": volume_spike,
    }


# =============================
# Telegram
# =============================

def _tg_escape_md2(s: str) -> str:
    for ch in r"_*[]()~`>#+-=|{}.!":
        s = s.replace(ch, f"\\{ch}")
    return s


def send_telegram_message(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram env missing; skip sending message")
        return
    
    # Tarkista viestin pituus
    if len(text) > 4096:
        logger.warning(f"Message too long ({len(text)} chars), truncating...")
        text = text[:4090] + "..."
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    
    # Retry Telegram-kutsu
    def _send():
        r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        if r.status_code == 429:  # Rate limit
            retry_after = int(r.headers.get('Retry-After', 1))
            logger.warning(f"Telegram rate limit, waiting {retry_after}s")
            time.sleep(retry_after)
            raise Exception("Rate limited")
        elif r.status_code >= 500:  # Server error
            raise Exception(f"Server error {r.status_code}")
        elif not r.ok:
            raise Exception(f"HTTP {r.status_code}: {r.text}")
        return r
    
    try:
        retry_call(_send, tries=3, backoff=1.5)
        logger.info("Telegram message sent")
    except Exception as e:
        logger.error(f"Telegram exception: {e}")


def build_telegram_report(df: pd.DataFrame) -> str:
    if df.empty:
        return "💡 Seulonta suoritettu.\nEi potentiaalisia kryptoja löytynyt."

    lines = ["💡 Seulonta suoritettu.", "Potentiaalisia kryptoja:"]
    
    # Group by category
    new_tokens = df[df.get("Category", "") == "NEW"]
    established_tokens = df[df.get("Category", "") == "ESTABLISHED"]
    
    if not new_tokens.empty:
        lines.append("\n🆕 UUDET TOKENIT:")
        for _, row in new_tokens.iterrows():
            lines.extend(format_token_row(row, is_new=True))
    
    if not established_tokens.empty:
        lines.append("\n🏛️ VAKIINTUNEET TOKENIT:")
        for _, row in established_tokens.iterrows():
            lines.extend(format_token_row(row, is_new=False))
    
    return "\n".join(lines)


def format_token_row(row: pd.Series, is_new: bool = False) -> list:
    """Format a single token row for Telegram"""
    sym = str(row["Ticker"])
    cid = str(row["Coin ID"])
    category = row.get("Category", "UNKNOWN")
    confidence = row.get("Confidence", "UNKNOWN")
    age_days = row.get("Age_Days", 0)
    rsi = row.get("RSI", np.nan)
    atrp = row.get("ATR%", np.nan)
    vol = row.get("Volume", np.nan)
    volma = row.get("VolMA20", np.nan)
    z = row.get("VolZ", np.nan)
    
    # Confidence emoji
    conf_emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(confidence, "⚪")
    
    # Category emoji
    cat_emoji = "🆕" if is_new else "🏛️"
    
    lines = [
        f"{cat_emoji} {sym} ({conf_emoji} {confidence})",
        f"├ {cid} | {age_days}d ikäinen",
        f"📊 Breakout: {row['Breakout']} | HTF: {row['HTF']}",
        f"├ RSI: {rsi:.2f} | ATR%: {atrp:.2f}",
        f"├ Vol: {vol:,.0f} | MA20: {volma:,.0f} | z: {z:.2f}",
        f"🔗 https://www.coingecko.com/en/coins/{cid}",
        "",
    ]
    
    return lines


# =============================
# Trading – signals & simple state machine
# =============================

def generate_trade_signals(df: pd.DataFrame,
                           portfolio_value: float,
                           risk_new: float = RISK_NEW,
                           risk_est: float = RISK_EST,
                           stop_new: float = STOP_NEW,
                           stop_est: float = STOP_EST,
                           tp1_new: float = TP1_NEW,
                           tp2_new: float = TP2_NEW,
                           tp1_est: float = TP1_EST,
                           tp2_est: float = TP2_EST,
                           max_alloc_pct: float = MAX_ALLOC_PCT) -> List[Dict[str, Any]]:
    signals = []
    for _, r in df.iterrows():
        cat = r.get("Category", "EST")
        if cat == "NEW":
            stop_pct = stop_new; risk_pct = risk_new; tp1 = tp1_new; tp2 = tp2_new
        else:
            stop_pct = stop_est; risk_pct = risk_est; tp1 = tp1_est; tp2 = tp2_est
        R = portfolio_value * risk_pct
        size_usd = R / max(stop_pct, 1e-6)
        size_usd = min(size_usd, portfolio_value * max_alloc_pct)
        signals.append({
            "coin_id": r["Coin ID"],
            "symbol": r["Ticker"],
            "category": cat,
            "stop_pct": stop_pct,
            "tp1_pct": tp1,
            "tp2_pct": tp2,
            "risk_pct": risk_pct,
            "position_usd": round(float(size_usd), 2),
            "vol_ma20": float(r.get("VolMA20", 0) or 0),
            "atr_pct": float(r.get("ATR%", 0) or 0),
        })
    return signals


def build_entry_msg(o: Dict[str, Any]) -> str:
    return (
        f"🟢 ENTRY {o['symbol']} ({o['category']})\n"
        f"Size: ${o['position_usd']:.2f} | Qty: {o.get('quantity', 0):.6f}\n"
        f"Entry: ${o['entry_price']:.6f}\n"
        f"SL: {o['stop_pct']*100:.1f}% → ${o['stop_price']:.6f}\n"
        f"TP1: {o['tp1_pct']*100:.0f}% → ${o['tp1_price']:.6f}, TP2: {o['tp2_pct']*100:.0f}% → ${o['tp2_price']:.6f}\n"
        f"Vol: {o.get('entry_volume', 0):,.0f} | Trail ATR×: {o['trail_atr_mult']} | MaxH: {o['time_max_h']}h"
    )


def build_update_msg(o: Dict[str, Any], reason: str) -> str:
    return (
        f"ℹ️ {o['symbol']} update — {reason}\n"
        f"Last: ${o['last_price']:.6f} | PnL: {o['pnl_pct']*100:.1f}%\n"
        f"SL @ ${o['stop_price']:.6f} | TP1 @ ${o['tp1_price']:.6f} | TP2 @ ${o['tp2_price']:.6f}"
    )


def open_new_orders(signals: List[Dict[str, Any]],
                     state: Dict[str, Any],
                     max_positions: int = MAX_POSITIONS,
                     dry_run: bool = DRY_RUN) -> List[Dict[str, Any]]:
    """Open orders from signals. Returns list of orders created in this call."""
    created: List[Dict[str, Any]] = []
    open_count = len(state.get("open", []))
    for s in signals:
        if open_count >= max_positions:
            break
        
        # Entry checks
        market_data = get_price_and_volume(s["coin_id"])
        px = market_data.get("price", float("nan"))
        current_vol = market_data.get("volume", 0.0)
        
        if not (isinstance(px, float) and px == px):
            logger.info(f"Skip entry {s['symbol']} — no price")
            continue
            
        # Liquidity check: skip if volume dropped below threshold
        if current_vol < MIN_24H_VOLUME_USD:
            logger.info(f"Skip entry {s['symbol']} — volume too low: {current_vol:,.0f} < {MIN_24H_VOLUME_USD:,.0f}")
            continue
            
        # Slippage check: position size vs 24h volume
        position_usd = s["position_usd"]
        if position_usd > 0.005 * current_vol:  # 0.5% of 24h volume
            logger.info(f"Skip entry {s['symbol']} — position too large: ${position_usd:,.0f} > 0.5% of 24h vol")
            continue
            
        # Calculate token quantity (rounded to 6-8 decimals)
        qty = position_usd / px
        qty = round(qty, 6)  # Simple rounding for now
        
        tp1_price = px * (1 + s["tp1_pct"]) ; tp2_price = px * (1 + s["tp2_pct"]) ; stop_price = px * (1 - s["stop_pct"]) 
        order = {
            "coin_id": s["coin_id"],
            "symbol": s["symbol"],
            "category": s["category"],
            "entry_ts": utc_now_iso(),
            "entry_price": px,
            "position_usd": position_usd,
            "quantity": qty,
            "stop_pct": s["stop_pct"],
            "tp1_pct": s["tp1_pct"],
            "tp2_pct": s["tp2_pct"],
            "stop_price": stop_price,
            "tp1_price": tp1_price,
            "tp2_price": tp2_price,
            "trail_atr_mult": TRAIL_ATR_NEW if s["category"]=="NEW" else TRAIL_ATR_EST,
            "time_max_h": TIME_MAX_H_NEW_H if s["category"]=="NEW" else TIME_MAX_H_EST_H,
            "last_price": px,
            "pnl_pct": 0.0,
            "tp1_hit": False,
            "status": "open",
            "vol_ma20": s.get("vol_ma20", 0.0),
            "entry_volume": current_vol,
        }
        state["open"].append(order)
        created.append(order)
        open_count += 1
        if not dry_run:
            try:
                send_telegram_message(build_entry_msg(order))
            except Exception:
                pass
    return created


def evaluate_positions(state: Dict[str, Any], dry_run: bool = DRY_RUN) -> None:
    now = datetime.now(timezone.utc)
    still_open = []
    for o in state.get("open", []):
        mkt = get_price_and_volume(o["coin_id"])
        px = mkt.get("price", o.get("last_price", float("nan")))
        if not (isinstance(px, float) and px == px):
            still_open.append(o)
            continue
        o["last_price"] = px
        o["pnl_pct"] = (px / o["entry_price"]) - 1
        reason = None
        # TP2
        if px >= o["tp2_price"]:
            o["status"] = "closed"; reason = "TP2 hit — close"
        # TP1 (move stop to BE)
        elif (not o.get("tp1_hit")) and px >= o["tp1_price"]:
            o["tp1_hit"] = True
            o["stop_price"] = max(o["stop_price"], o["entry_price"])  # move to break-even
            reason = "TP1 hit — stop moved to BE"
        # STOP
        elif px <= o["stop_price"]:
            o["status"] = "closed"; reason = "Stop hit"
        # TIME-BASED EXIT
        else:
            entered = datetime.fromisoformat(o["entry_ts"])
            if (now - entered) > timedelta(hours=o.get("time_max_h", 48)):
                o["status"] = "closed"; reason = "Time-based exit"
        if reason:
            o["exit_reason"] = reason
            try:
                if not dry_run:
                    send_telegram_message(build_update_msg(o, reason))
            except Exception:
                pass
        if o["status"] == "open":
            still_open.append(o)
        else:
            # move to closed
            o["exit_ts"] = utc_now_iso()
            state.setdefault("closed", []).append(o)
    state["open"] = still_open


def build_run_journal(opened: List[Dict[str, Any]], closed: List[Dict[str, Any]]) -> str:
    """Build a compact end-of-run summary of new entries and closed positions."""
    lines = ["🧾 Run journal"]
    # Opened
    if opened:
        lines.append("\n🟢 Opened:")
        for o in opened:
            sym = str(o.get("symbol", "?"))
            ent = o.get("entry_price", float("nan"))
            sz = o.get("position_usd", 0)
            lines.append(f"• {sym} — ${ent:.6f} | ${sz:,.0f}")
    else:
        lines.append("\n🟢 Opened: –")
    # Closed
    if closed:
        lines.append("\n🔴 Closed:")
        for c in closed:
            sym = str(c.get("symbol", "?"))
            pnl = c.get("pnl_pct", 0.0)
            rsn = c.get("exit_reason", "closed")
            lines.append(f"• {sym} — PnL {pnl*100:.1f}% | {rsn}")
    else:
        lines.append("\n🔴 Closed: –")
    return "\n".join(lines)


# =============================
# Signal functions
# =============================

def signal_mom_c(ind: Dict[str, Any], category: str, last_close: float) -> bool:
    ok_trend = (ind.get("ema_bias_pct", 0) > 0)
    two_bar_high = bool(ind.get("two_bar_high", False))
    volz = ind.get("vol_z", float("nan"))
    volma = ind.get("avg_volume", 0) or 0
    curvol = ind.get("current_volume", 0) or 0
    vol_pct_rank20 = ind.get("vol_pct_rank20", float("nan"))

    if category in ("NEW", "MID"):
        vol_ok = (curvol > RELAXED_VOL_INCREASE * volma) or (isinstance(volz, (int,float)) and volz > RELAXED_VOL_Z)
        if category == "MID":
            d10 = ind.get("donchian_high10", float("inf"))
            extra = (not np.isnan(d10)) and (last_close > d10)
        else:
            extra = True
        return ok_trend and two_bar_high and vol_ok and extra
    else:
        # EST: löysempi volz + vol_pct_rank20 vaihtoehto tai pisteytys fallback
        vol_ok_est = (isinstance(volz, (int,float)) and volz > VOL_Z_EST) or (isinstance(vol_pct_rank20, (int,float)) and vol_pct_rank20 >= VOL_PCT_RANK_EST)

        # Score fallback (robusti jatkopotku):
        # two_bar_high (1), ema_bias>0 (1), close>Donchian10 (1), (volz>1.5 or vol>1.3xMA20) (1), vol_pct_rank20>=0.70 (1)
        score = 0
        if two_bar_high:
            score += 1
        if ok_trend:
            score += 1
        d10 = ind.get("donchian_high10", float("inf"))
        if not np.isnan(d10) and last_close > d10:
            score += 1
        vol_cond = (isinstance(volz, (int,float)) and volz > 1.5) or (ind.get("current_volume", 0) > 1.3 * (ind.get("avg_volume", 0) or 1))
        if vol_cond:
            score += 1
        if isinstance(vol_pct_rank20, (int,float)) and vol_pct_rank20 >= 0.70:
            score += 1

        strong_score = (score >= 3)

        return ok_trend and two_bar_high and (vol_ok_est or strong_score)


def signal_donchian_base(ind: Dict[str, Any], category: str, last_close: float) -> bool:
    d20 = ind.get("donchian_high20", float("inf"))
    dc_ok = (not np.isnan(d20)) and (last_close > d20)
    atr_th = 12 if category == "NEW" else (10 if category == "MID" else 8)
    atr_ok = (ind.get("atr_pct", 0) > atr_th)
    vpr = ind.get("vol_pct_rank20", float("nan"))
    volz = ind.get("vol_z", float("nan"))
    
    # EST: löysempi vol_pct_rank20 + volz vaihtoehto
    if category == "EST":
        vol_pr_ok = (isinstance(vpr, (int,float)) and vpr >= 0.55) or (isinstance(volz, (int,float)) and volz > 1.4)
    else:
        vol_pr_ok = isinstance(vpr, (int,float)) and vpr >= 0.60
    
    return bool(dc_ok and atr_ok and vol_pr_ok)


# =============================
# Strategy pipeline
# =============================

def get_candidate_ids(limit: int = 50,
                     min_vol_usd: float = MIN_24H_VOLUME_USD,
                     price_min: float = PRICE_MIN,
                     mcap_min: float = MARKET_CAP_MIN,
                     mom_threshold: float = MOMENTUM_THRESHOLD_24H) -> List[Dict[str, str]]:
    # pull recent coins (take extra to allow for missing market data)
    new_coins = get_new_coins(limit_ids=limit * 3)
    ids = [c["id"] for c in new_coins]

    markets = get_markets_for_ids(ids)
    # filter markets by 24h change, liquidity, and quality
    filtered = [
        m for m in markets
        if m.get("price_change_percentage_24h") is not None
        and m.get("price_change_percentage_24h") > mom_threshold
        and (m.get("total_volume") or 0) >= min_vol_usd
        and (m.get("current_price") or 0) > price_min  # Filter out micro-tokens
        and (m.get("market_cap") or 0) >= mcap_min  # Min market cap
    ]

    # sort by 24h % change desc
    filtered.sort(key=lambda x: x["price_change_percentage_24h"], reverse=True)

    # Debug print top-20
    logger.info("Top 20 by 24h %% change among new coins: " +
                ", ".join([f"{m['symbol'].upper()} {m['price_change_percentage_24h']:.2f}%" for m in filtered[:20]]))

    return [{"id": m["id"], "symbol": m["symbol"].upper()} for m in filtered[:limit]]


def get_token_age_days(coin_id: str) -> int:
    """Get token age in days since first listing"""
    try:
        # Get coin details to find first listing date
        data = retry_call(
            cg.get_coin_by_id,
            id=coin_id,
            localization="false",
            tickers="false",
            market_data="false",
            community_data="false",
            developer_data="false",
            sparkline="false",
        )
        
        # Try to get genesis date or first listing date
        genesis_date = data.get("genesis_date")
        if genesis_date:
            try:
                genesis_dt = datetime.fromisoformat(genesis_date.replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - genesis_dt).days
                return max(0, age_days)
            except:
                pass
        
        # Fallback: estimate from market data availability
        # Try to get historical data to estimate age
        try:
            ohlc = retry_call(cg.get_coin_ohlc_by_id, id=coin_id, vs_currency="usd", days=30)
            if ohlc and len(ohlc) > 0:
                # Estimate age from available data points
                data_points = len(ohlc)
                if data_points <= 7:
                    return 3  # Very new
                elif data_points <= 14:
                    return 10  # New
                else:
                    return 20  # Established
        except:
            pass
        
        # Default to "new" for unknown tokens (they're in new coins list)
        return 3  # Assume new if we can't determine age
        
    except Exception as e:
        logger.debug(f"Could not determine age for {coin_id}: {e}")
        return 3  # Default to "new" for unknown tokens


def process_token(coin: Dict[str, str]) -> Optional[Dict[str, Any]]:
    coin_id = coin["id"]
    symbol = coin["symbol"]
    df = fetch_ohlc_and_volume(coin_id)
    
    if df.empty:
        logger.info(f"{symbol}: no data available")
        return None
    
    # Determine token age and category
    age_days = int(len(df))
    is_new = age_days <= NEW_TOKEN_MAX_DAYS
    is_mid = (age_days > NEW_TOKEN_MAX_DAYS) and (age_days <= MID_TOKEN_MAX_DAYS)
    category = "NEW" if is_new else ("MID" if is_mid else "EST")

    if category == "NEW":
        min_len_required = NEW_MIN_DATA_LEN
    elif category == "MID":
        min_len_required = MID_MIN_DATA_LEN
    else:
        min_len_required = MIN_DATA_LEN_ESTABLISHED

    if len(df) < min_len_required:
        logger.info(f"{symbol}: insufficient data ({len(df)} days, need {min_len_required} for {category} token, age: {age_days}d)")
        return None

    ind = compute_indicators(df, is_new_token=is_new)
    last_close = float(df["close"].iloc[-1])

    # nykyiset säännöt
    pass_core = bool(ind.get("breakout") or ind.get("htf"))

    # uudet säännöt (opt-in flagit)
    pass_momc = ENABLE_MOMC and signal_mom_c(ind, category, last_close)
    pass_base = ENABLE_BASE and signal_donchian_base(ind, category, last_close)

    if pass_core or pass_momc or pass_base:
        # ... (palauta dict kuten ennen) + lisäavut:
        strategy = "core" if pass_core else ("momc" if pass_momc else "base")
        confidence = "HIGH" if (ind["breakout"] and ind["htf"]) else "MEDIUM" if ind["breakout"] else "LOW"
        
        logger.info(f"{symbol} ({category}) passes: core={pass_core} momc={pass_momc} base={pass_base} strategy={strategy}")
        return {
            "Ticker": symbol,
            "Coin ID": coin_id,
            "Breakout": bool(ind.get("breakout")),
            "HTF": bool(ind.get("htf")),
            "RSI": ind.get("rsi"),
            "ATR%": ind.get("atr_pct"),
            "Volatility": ind.get("atr_pct"),
            "Volume": ind.get("current_volume"),
            "VolMA20": ind.get("avg_volume"),
            "VolZ": ind.get("vol_z"),
            "Ret60D": ind.get("ret_60d"),
            "MaxRetr": ind.get("max_retracement"),
            "AgeDays": age_days,
            "Category": category,
            "Strategy": strategy,
            "Trust": "low" if category == "NEW" else ("medium" if category == "MID" else "medium"),
        }
    else:
        logger.info(f"{symbol} filtered: core={pass_core} momc={pass_momc} base={pass_base} category={category}")
        return None


def dedupe_with_cooldown(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    found = load_found_tickers()
    now_iso = utc_now_iso()
    out = []
    for row in candidates:
        cid = row["Coin ID"]
        last = found.get(cid)
        if last and within_cooldown(last, COOLDOWN_HOURS):
            logger.info(f"Skip {cid} due to cooldown (last alert {last})")
            continue
        found[cid] = now_iso
        out.append(row)
    save_found_tickers(found)
    return out


def run_screen(limit: int = 50,
               min_vol_usd: float = MIN_24H_VOLUME_USD,
               price_min: float = PRICE_MIN,
               mcap_min: float = MARKET_CAP_MIN,
               mom_threshold: float = MOMENTUM_THRESHOLD_24H,
               exchanges_min: int = 1) -> pd.DataFrame:
    logger.info(f"Starting screen run (run_id={RUN_ID})")
    try:
        coins = get_candidate_ids(limit=limit,
                                  min_vol_usd=min_vol_usd,
                                  price_min=price_min,
                                  mcap_min=mcap_min,
                                  mom_threshold=mom_threshold)
        # apply exchanges-min filter
        coins = enforce_exchanges_min(coins, exchanges_min)
        if not coins:
            logger.info("No coins left after exchanges_min filter")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Failed to get candidates: {e}")
        return pd.DataFrame()

    results: List[Dict[str, Any]] = []
    for coin in coins:
        try:
            res = process_token(coin)
            if res:
                results.append(res)
            time.sleep(1.5)  # gentle pacing
        except Exception as e:
            logger.error(f"Error processing {coin.get('id')} {coin.get('symbol')}: {e}")
            time.sleep(1.0)

    if not results:
        logger.info("No tokens passed the filters")
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = dedupe_with_cooldown(df.to_dict(orient="records"))
    df = pd.DataFrame(df)

    if not df.empty and SAVE_RESULTS_CSV:
        try:
            df.assign(run_ts=utc_now_iso()).to_csv(RESULTS_PATH, index=False)
            logger.info(f"Saved results to {RESULTS_PATH}")
        except Exception as e:
            logger.error(f"Failed to save results CSV: {e}")

    logger.info(f"Results count after dedupe: {len(df)}")
    return df


# =============================
# Main (CLI)
# =============================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="New token momentum screener (CoinGecko)")
    parser.add_argument("--limit", type=int, default=int(os.getenv("LIMIT", "50")), help="Max results to test")
    parser.add_argument("--min-vol", dest="min_vol", type=float, default=MIN_24H_VOLUME_USD, help="Min 24h volume USD")
    parser.add_argument("--price-min", dest="price_min", type=float, default=PRICE_MIN, help="Min current price")
    parser.add_argument("--mcap-min", dest="mcap_min", type=float, default=MARKET_CAP_MIN, help="Min market cap")
    parser.add_argument("--mom-th", dest="mom_th", type=float, default=MOMENTUM_THRESHOLD_24H, help="Min 24h percent change")
    parser.add_argument("--exchanges-min", dest="exchanges_min", type=int, default=int(os.getenv("EXCHANGES_MIN", "1")), help="Min unique exchanges listing the coin")
    parser.add_argument("--save-csv", dest="save_csv", action="store_true", help="Save results to CSV")
    parser.add_argument("--csv-path", dest="csv_path", type=str, default=RESULTS_PATH, help="CSV output path")
    # Trading args
    parser.add_argument("--portfolio", dest="portfolio", type=float, default=PORTFOLIO_VALUE, help="Portfolio value (USD)")
    parser.add_argument("--risk-new", dest="risk_new", type=float, default=RISK_NEW, help="Risk per NEW trade (fraction)")
    parser.add_argument("--risk-est", dest="risk_est", type=float, default=RISK_EST, help="Risk per EST trade (fraction)")
    parser.add_argument("--max-alloc", dest="max_alloc", type=float, default=MAX_ALLOC_PCT, help="Max allocation per trade (fraction)")
    parser.add_argument("--max-positions", dest="max_positions", type=int, default=MAX_POSITIONS, help="Max open positions")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Do not send Telegram messages / no live actions")
    parser.add_argument("--enable-momc", dest="enable_momc", action="store_true", help="Enable Momentum-Continuation signal")
    parser.add_argument("--enable-base", dest="enable_base", action="store_true", help="Enable Donchian BASE signal")
    args = parser.parse_args()

    # Apply CLI overrides
    if args.save_csv:
        SAVE_RESULTS_CSV = True  # type: ignore
    RESULTS_PATH = args.csv_path  # type: ignore
    if args.dry_run:
        DRY_RUN = True  # type: ignore
    if args.enable_momc:
        ENABLE_MOMC = True  # type: ignore
    if args.enable_base:
        ENABLE_BASE = True  # type: ignore

    print("Skripti käynnistyi – hakee dataa...")
    try:
        df = run_screen(limit=args.limit,
                        min_vol_usd=args.min_vol,
                        price_min=args.price_min,
                        mcap_min=args.mcap_min,
                        mom_threshold=args.mom_th,
                        exchanges_min=args.exchanges_min)
        
        # === Trading: generate signals & update state ===
        state = load_orders_state()
        prev_closed_len = len(state.get("closed", []))
        created_orders: List[Dict[str, Any]] = []
        if df is not None and not df.empty:
            signals = generate_trade_signals(df,
                                             portfolio_value=args.portfolio,
                                             risk_new=args.risk_new,
                                             risk_est=args.risk_est,
                                             max_alloc_pct=args.max_alloc)
            created_orders = open_new_orders(signals, state, max_positions=args.max_positions, dry_run=DRY_RUN)
        evaluate_positions(state, dry_run=DRY_RUN)
        new_closed = state.get("closed", [])[prev_closed_len:]
        save_orders_state(state)

        # Build and send screening report as before
        if df is None or df.empty:
            report = "💡 Seulonta suoritettu.\nEi potentiaalisia kryptoja löytynyt."
        else:
            with pd.option_context('display.max_columns', None, 'display.width', 120):
                logger.info("Final results:\n" + df.to_string(index=False))
            report = build_telegram_report(df)
        
        # Build and append journal
        journal = build_run_journal(created_orders, new_closed)
        final_msg = report + "\n\n" + journal if report else journal
        
        if not DRY_RUN:
            send_telegram_message(final_msg)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    print("Skripti suoritettu.")
