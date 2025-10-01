#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import logging
import aiohttp
from dotenv import load_dotenv

from helius_token_scanner_bot import HeliusTokenScannerBot, DexInfoFetcher
from raydium_pool_watcher import RaydiumPoolWatcher
from trading_config import TradingConfig
from trader import Trader
from dex_fetchers import (
    fetch_from_birdeye,
    fetch_from_coingecko,
    fetch_from_dexscreener,
    fetch_from_jupiter,
    fetch_from_solscan,
)
from scanner_config import ScannerConfig
from circuit_breaker import CircuitBreakerConfig
from solana_rpc_helpers import rpc_get_tx
from health_server import HealthServer
from trending_lookback import TrendingLookbackSweep

load_dotenv()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logging.getLogger(__name__).warning("Invalid int for %s: %s", name, value)
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        logging.getLogger(__name__).warning("Invalid float for %s: %s", name, value)
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


async def main():
    logging.basicConfig(level=logging.INFO)

    ws_url = os.getenv("HELIUS_WS_URL") or (
        f"wss://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY','')}"
    )
    programs = [
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # SPL Token program
    ]
    token22_program = os.getenv("SPL_TOKEN22_PROGRAM", "TokenzQdBNbLqP5VEhGz1vK5ja2V21w8bJ5vYvGphL9u")
    if token22_program and token22_program not in programs:
        programs.append(token22_program)
    
    # Raydium program id:t (CPMM ja CLMM – pidä envissä konffattavina)
    RAY_AMM = os.getenv("RAYDIUM_AMM_PROGRAM", "RVKd61ztZW9yK21G4xMqi6nG5iG6JdzDyxN1q6i1dV4")   # esimerkki (päivitä tarvittaessa)
    RAY_CLMM = os.getenv("RAYDIUM_CLMM_PROGRAM", "CAMMCzo5YL8CKqQCDx9hcQzYbx8jG9LXNhtzK1Zx6UeD") # esimerkki (päivitä tarvittaessa)
    raydium_programs = tuple(pid for pid in (RAY_AMM, RAY_CLMM) if pid)
    
    # Orca program id
    ORCA_WHIRLPOOLS = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
    
    # Pump.fun program id
    PUMP_FUN = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
    
    # Lisää kaikki program ID:t pääohjelmaan
    for program_id in [RAY_AMM, RAY_CLMM, ORCA_WHIRLPOOLS, PUMP_FUN]:
        if program_id and program_id not in programs:
            programs.append(program_id)

    # Oikeat DEX hakijat
    breaker_cfg = CircuitBreakerConfig(
        failure_threshold=_env_int("SCANNER_BREAKER_THRESHOLD", 5),
        timeout=_env_float("SCANNER_BREAKER_TIMEOUT", 60.0),
    )

    config = ScannerConfig(
        max_retry_attempts=_env_int("SCANNER_MAX_RETRIES", 4),
        retry_initial_delay=_env_float("SCANNER_RETRY_INITIAL", 5.0),
        retry_backoff=_env_float("SCANNER_RETRY_BACKOFF", 2.0),
        retry_max_delay=_env_float("SCANNER_RETRY_MAX_DELAY", 60.0),
        retry_fetch_timeout=_env_float("SCANNER_RETRY_FETCH_TIMEOUT", 12.0),
        memory_cleanup_interval=_env_float("SCANNER_MEMORY_CLEANUP_INTERVAL", 300.0),
        liquidity_history_ttl=_env_float("SCANNER_LIQUIDITY_TTL", 3600.0),
    min_liquidity_usd=_env_float("SCANNER_MIN_LIQ", 15000.0),
    min_volume24h_usd=_env_float("SCANNER_MIN_VOL24H", 20000.0),
    min_buyers_30m=_env_int("SCANNER_MIN_BUYERS30M", 5),
    min_age_min=_env_int("SCANNER_MIN_AGE_MIN", 0),
    util_min=_env_float("SCANNER_UTIL_MIN", 0.4),
    util_max=_env_float("SCANNER_UTIL_MAX", 6.0),
    min_publish_score=_env_int("SCANNER_SCORE_MIN", 40),
    pool_min_trades24h=_env_int("SCANNER_POOL_MIN_TRADES24H", 10),
        pool_max_last_trade_min=_env_int("SCANNER_POOL_MAX_LASTTRADE_MIN", 10),
        pool_min_age_min=_env_int("SCANNER_POOL_MIN_AGE_MIN", 0),
        enable_fdv_sanity=_env_bool("SCANNER_ENABLE_FDV_SANITY", True),
        fdv_sanity_tolerance=_env_float("SCANNER_FDV_SANITY_TOL", 0.30),
        require_buyers30m=_env_bool("SCANNER_REQUIRE_BUYERS30M", True),
        buyers30m_soft_mode=_env_bool("SCANNER_BUYERS30M_SOFT_MODE", True),
        strict_placeholder=_env_bool("SCANNER_STRICT_PLACEHOLDER", False),
        placeholder_penalty=_env_int("SCANNER_PLACEHOLDER_PENALTY", 10),
        min_symbol_len=_env_int("SCANNER_MIN_SYMBOL_LEN", 2),
        max_symbol_len=_env_int("SCANNER_MAX_SYMBOL_LEN", 15),
        enable_raydium_watcher=_env_bool("SCANNER_ENABLE_RAYDIUM_WATCHER", True),
        raydium_quote_allowlist=tuple((os.getenv("SCANNER_RAYDIUM_QUOTES", "USDC,USDT,SOL")).split(",")),
        raydium_min_quote_usd=_env_float("SCANNER_RAYDIUM_MIN_QUOTE_USD", 3000.0),
        raydium_programs=raydium_programs or (),
    )

    # Trading configuration
    trade_cfg = TradingConfig(
        enabled=bool(int(os.getenv("AUTO_TRADE", "0"))),
        dry_run=bool(int(os.getenv("DRY_RUN", "1"))),
        max_trade_usd=_env_float("TRADE_MAX_USD", 100.0),
        slippage_bps=_env_int("TRADE_SLIPPAGE_BPS", 150),
        priority_fee_microlamports=_env_int("TRADE_PRIORITY_FEE_U", 200000),
        compute_unit_limit=_env_int("TRADE_CU_LIMIT", 600000),
        min_score_to_buy=_env_int("TRADE_MIN_SCORE", 50),
        min_liq_usd_to_buy=_env_float("TRADE_MIN_LIQ_USD", 10000.0),
        util_min=_env_float("TRADE_UTIL_MIN", 0.35),
        util_max=_env_float("TRADE_UTIL_MAX", 6.0),
        take_profit_pct=_env_float("TRADE_TP_PCT", 25.0),
        stop_loss_pct=_env_float("TRADE_SL_PCT", 20.0),
        cooldown_sec=_env_int("TRADE_COOLDOWN_SEC", 120),
        require_can_sell_probe=bool(int(os.getenv("TRADE_REQUIRE_CAN_SELL", "1"))),
    )

    async def _buyers30m_provider(_mint: str) -> int | None:
        # Palauta None kun integraatio ei vielä anna signaalia → ei kovaa droppia
        return None

    fetcher = DexInfoFetcher(
        birdeye=fetch_from_birdeye,
        dexscreener=fetch_from_dexscreener,
        coingecko=fetch_from_coingecko,
        jupiter=fetch_from_jupiter,
        solscan=fetch_from_solscan,
        breaker_config=breaker_cfg,
        buyers30m_provider=_buyers30m_provider,
    )

    bot = HeliusTokenScannerBot(
        ws_url=ws_url,
        programs=programs,
        dex_fetcher=fetcher,
        rpc_get_tx=rpc_get_tx,
        config=config,
    )
    
    # Trader-instanssi botille
    http_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    bot.trader = Trader(http_url, trade_cfg, logging.getLogger("trader"))
    bot.trade_cfg = trade_cfg
    
    # Telegram bot for scanner notifications only
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if telegram_bot_token and telegram_chat_id and telegram_bot_token != "your_bot_token_here":
        try:
            # Real Telegram bot with aiohttp
            class SimpleTelegramBot:
                def __init__(self, token: str, chat_id: str):
                    self.enabled = True
                    self.token = token
                    self.chat_id = chat_id
                    self.base_url = f"https://api.telegram.org/bot{token}"
                    
                async def send_message(self, message: str, parse_mode: str = "Markdown"):
                    try:
                        async with aiohttp.ClientSession() as session:
                            url = f"{self.base_url}/sendMessage"
                            data = {
                                "chat_id": self.chat_id,
                                "text": message,
                                "parse_mode": parse_mode,
                                "disable_web_page_preview": True
                            }
                            async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                                if resp.status != 200:
                                    logging.getLogger(__name__).error(f"Telegram API error: {resp.status}")
                                    return False
                                return True
                    except Exception as e:
                        logging.getLogger(__name__).error(f"Failed to send Telegram message: {e}")
                        return False
            
            telegram_bot = SimpleTelegramBot(telegram_bot_token, telegram_chat_id)
            bot.set_telegram_bot(telegram_bot)
            logging.getLogger(__name__).info("✅ Real Telegram bot initialized for scanner notifications")
        except Exception as e:
            logging.getLogger(__name__).error(f"❌ Failed to initialize Telegram bot: {e}")
    else:
        logging.getLogger(__name__).info("📱 Telegram bot not configured")

    metrics_port = _env_int("SCANNER_METRICS_PORT", 0)
    metrics_host = os.getenv("SCANNER_METRICS_HOST", "0.0.0.0")
    if metrics_port > 0:
        from prometheus_client import start_http_server

        start_http_server(metrics_port, addr=metrics_host)
        logging.getLogger(__name__).info(
            "Prometheus metrics available on %s:%s", metrics_host, metrics_port
        )

    health_server: HealthServer | None = None
    health_port = _env_int("SCANNER_HEALTH_PORT", 0)
    if health_port > 0:
        health_host = os.getenv("SCANNER_HEALTH_HOST", "0.0.0.0")
        health_server = HealthServer(bot, health_host, health_port)
        await health_server.start()

    await bot.start()
    
    # --- Raydium-pooliseulonta WS:llä ---
    if config.enable_raydium_watcher and raydium_programs:
        raywatch = RaydiumPoolWatcher(
            ws_url=ws_url,
            program_ids=raydium_programs,
            on_pair=lambda mint, meta: asyncio.create_task(
                bot.submit_pair_candidate(mint, source="raydium", meta=meta)
            ),
            quote_allowlist=set(x.strip().upper() for x in config.raydium_quote_allowlist),
            min_quote_usd=config.raydium_min_quote_usd,
        )
        asyncio.create_task(raywatch.run_forever())
        logging.getLogger(__name__).info("🔄 Raydium pool watcher started")
    
    # Lookback sweep task
    lookback_task = None
    birdeye_api_key = os.getenv("BIRDEYE_API_KEY")
    if birdeye_api_key:
        async def on_lookback_pair(candidate):
            """Handle lookback pair candidate"""
            try:
                # Submit to bot's queue
                from helius_token_scanner_bot import NewTokenEvent
                event = NewTokenEvent(
                    mint=candidate.mint,
                    symbol=candidate.meta.get("birdeye", {}).get("symbol", f"TOKEN_{candidate.mint[:8]}"),
                    name=candidate.meta.get("birdeye", {}).get("name", f"Token {candidate.mint[:8]}"),
                    signature=None
                )
                bot._queue.put_nowait(event)
                logging.getLogger(__name__).info(f"📥 Lookback candidate: {candidate.mint[:8]}... ({candidate.type})")
            except Exception as e:
                logging.getLogger(__name__).error(f"Error processing lookback candidate: {e}")
        
        lookback = TrendingLookbackSweep(
            birdeye_api_key=birdeye_api_key,
            window_sec=_env_int("LOOKBACK_WINDOW_SEC", 5400),  # 90 min
            interval_sec=_env_int("LOOKBACK_INTERVAL_SEC", 60),  # 1 min
            on_pair=on_lookback_pair
        )
        lookback_task = asyncio.create_task(lookback.run_forever())
        logging.getLogger(__name__).info("🔄 Lookback sweep started")
    
    
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logging.getLogger(__name__).info("Received shutdown signal, stopping gracefully...")
    finally:
        if lookback_task:
            lookback_task.cancel()
            try:
                await lookback_task
            except asyncio.CancelledError:
                pass
        
        if health_server:
            await health_server.stop()
        await bot.graceful_shutdown(timeout=_env_float("SCANNER_SHUTDOWN_TIMEOUT", 30.0))
        logging.getLogger(__name__).info("Bot shutdown complete")




if __name__ == "__main__":
    asyncio.run(main())
