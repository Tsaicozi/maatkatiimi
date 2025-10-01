import os
import time
import json
import math
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

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

logger = logging.getLogger("screener")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

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

# Strategy parameters
HISTORY_DAYS = 90  # allowed values for OHLC: 1/7/14/30/90/180
RSI_PERIOD = 14
EMA_SHORT_SPAN = 5
EMA_LONG_SPAN = 20
ATR_PERIOD = 14
MOMENTUM_THRESHOLD_24H = float(os.getenv("MOMENTUM_THRESHOLD_24H", "10.0"))  # %
VOL_INCREASE_THRESHOLD = float(os.getenv("VOL_INCREASE_THRESHOLD", "1.5"))     # x average
VOL_ZSCORE_THRESHOLD = float(os.getenv("VOL_ZSCORE_THRESHOLD", "2.0"))          # optional additional trigger
NOUSU_60D_THRESHOLD = float(os.getenv("NOUSU_60D_THRESHOLD", "0.9"))            # 90% over 60d
MAX_RETRACEMENT_THRESHOLD = float(os.getenv("MAX_RETRACEMENT_THRESHOLD", "0.25"))
MIN_24H_VOLUME_USD = float(os.getenv("MIN_24H_VOLUME_USD", "200000"))

COOLDOWN_HOURS = int(os.getenv("COOLDOWN_HOURS", "48"))
FOUND_TICKERS_FILE = os.getenv("FOUND_TICKERS_FILE", "found_new_tokens.json")

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))

# Minimum data length based on indicators used
MIN_DATA_LEN = max(EMA_LONG_SPAN + 1, RSI_PERIOD + 1, ATR_PERIOD + 2, 20) + 5

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
    CHUNK = 100  # Chunk size to avoid URL length limits
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
        time.sleep(0.3)  # Gentle pacing between chunks
    
    return out


def fetch_ohlc_and_volume(coin_id: str) -> pd.DataFrame:
    """Return daily OHLC + daily volume (as daily max of 24h rolling volume)."""
    try:
        ohlc = retry_call(cg.get_coin_ohlc_by_id, id=coin_id, vs_currency="usd", days=HISTORY_DAYS)
        df_ohlc = pd.DataFrame(ohlc, columns=["timestamp", "open", "high", "low", "close"])
        df_ohlc["date"] = pd.to_datetime(df_ohlc["timestamp"], unit="ms").dt.date

        market_chart = retry_call(cg.get_coin_market_chart_by_id, id=coin_id, vs_currency="usd", days=int(HISTORY_DAYS))
        df_vol = pd.DataFrame(market_chart.get("total_volumes", []), columns=["timestamp", "volume"])  # 24h rolling volume
        if df_vol.empty:
            return pd.DataFrame()
        df_vol["date"] = pd.to_datetime(df_vol["timestamp"], unit="ms").dt.date
        # Use daily 95% quantile of the 24h rolling volume as a robust daily volume proxy
        # (less spike-sensitive than max, more conservative than median)
        df_volume_daily = df_vol.groupby("date")["volume"].quantile(0.95).reset_index()

        df = pd.merge(df_ohlc, df_volume_daily, on="date", how="inner")
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


def compute_indicators(df: pd.DataFrame) -> Dict[str, Any]:
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
    for _, row in df.iterrows():
        sym = str(row["Ticker"])
        cid = str(row["Coin ID"])
        rsi = row.get("RSI", np.nan)
        atrp = row.get("ATR%", np.nan)
        vol = row.get("Volume" , np.nan)
        volma = row.get("VolMA20", np.nan)
        z = row.get("VolZ", np.nan)
        
        lines += [
            f"💊 {sym}",
            f"├ {cid}",
            f"📊 Breakout: {row['Breakout']} | HTF: {row['HTF']}",
            f"├ RSI: {rsi:.2f} | ATR%: {atrp:.2f}",
            f"├ Vol: {vol:,.0f} | MA20: {volma:,.0f} | z: {z:.2f}",
            f"🔗 https://www.coingecko.com/en/coins/{cid}",
            "",
        ]
    return "\n".join(lines)


# =============================
# Strategy pipeline
# =============================

def get_candidate_ids(limit: int = 50) -> List[Dict[str, str]]:
    # pull recent coins (take extra to allow for missing market data)
    new_coins = get_new_coins(limit_ids=limit * 3)
    ids = [c["id"] for c in new_coins]

    markets = get_markets_for_ids(ids)
    # filter markets by 24h change, liquidity, and quality
    filtered = [
        m for m in markets
        if m.get("price_change_percentage_24h") is not None
        and m.get("price_change_percentage_24h") > MOMENTUM_THRESHOLD_24H
        and (m.get("total_volume") or 0) >= MIN_24H_VOLUME_USD
        and (m.get("current_price") or 0) > 0.0001  # Filter out micro-tokens
        and (m.get("market_cap") or 0) >= 1_000_000  # Min $1M market cap
    ]

    # sort by 24h % change desc
    filtered.sort(key=lambda x: x["price_change_percentage_24h"], reverse=True)

    # Debug print top-20
    logger.info("Top 20 by 24h %% change among new coins: " +
                ", ".join([f"{m['symbol'].upper()} {m['price_change_percentage_24h']:.2f}%" for m in filtered[:20]]))

    return [{"id": m["id"], "symbol": m["symbol"].upper()} for m in filtered[:limit]]


def process_token(coin: Dict[str, str]) -> Optional[Dict[str, Any]]:
    coin_id = coin["id"]
    symbol = coin["symbol"]
    df = fetch_ohlc_and_volume(coin_id)
    if df.empty or len(df) < MIN_DATA_LEN:
        logger.info(f"{symbol}: insufficient data ({len(df) if not df.empty else 0} days)")
        return None

    ind = compute_indicators(df)

    # Decision rule: breakout or HTF
    if ind["breakout"] or ind["htf"]:
        logger.info(f"{symbol} passes: breakout={ind['breakout']} htf={ind['htf']}")
        return {
            "Ticker": symbol,
            "Coin ID": coin_id,
            "Breakout": ind["breakout"],
            "HTF": ind["htf"],
            "RSI": ind["rsi"],
            "ATR%": ind["atr_pct"],
            "Volatility": ind["atr_pct"],  # kept for backward compatibility
            "Volume": ind["current_volume"],
            "VolMA20": ind["avg_volume"],
            "VolZ": ind["vol_z"],
            "Ret60D": ind["ret_60d"],
            "MaxRetr": ind["max_retracement"],
        }
    else:
        logger.info(f"{symbol} filtered out: breakout={ind['breakout']} htf={ind['htf']}")
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


def run_screen(limit: int = 50) -> pd.DataFrame:
    logger.info("Starting screen run")
    try:
        coins = get_candidate_ids(limit=limit)
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
    logger.info(f"Results count after dedupe: {len(df)}")
    return df


# =============================
# Main
# =============================
if __name__ == "__main__":
    print("Skripti käynnistyi – hakee dataa...")
    try:
        df = run_screen(limit=50)
        if df is None or df.empty:
            report = "💡 Seulonta suoritettu.\nEi potentiaalisia kryptoja löytynyt."
        else:
            # Pretty log
            with pd.option_context('display.max_columns', None, 'display.width', 120):
                logger.info("Final results:\n" + df.to_string(index=False))
            report = build_telegram_report(df)
        send_telegram_message(report)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    print("Skripti suoritettu.")
