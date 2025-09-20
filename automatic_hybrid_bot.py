#!/usr/bin/env python3
"""
Automatic Hybrid Trading Bot
Käynnistää hybrid trading botin automaattisesti ja lähettää Telegram ilmoituksia
Parannettu: tarkka ajastus, lokien rotaatio, siisti sammutus, aikavyöhyke
"""

import asyncio
import signal
import sys
import logging
import time
import os
import json
import contextlib
import atexit
from pathlib import Path
from logging.handlers import RotatingFileHandler


class NullTelegramBot:
    """Offline-placeholder Telegram client that logs instead of sending"""

    def __init__(self):
        self.logger = logging.getLogger("null_telegram_bot")
        self.enabled = False

    async def send_message(self, message: str, *_, **__) -> bool:
        preview = message.replace("\n", " ")
        self.logger.info("[offline] Telegram message skipped: %s", preview[:160])
        return False

    def __getattr__(self, name):  # pragma: no cover - simple async shim
        async def _noop(*args, **kwargs):
            self.logger.debug("NullTelegramBot.%s called; ignored", name)
            return False

        return _noop

# --- LOGGING SETUP (drop-in) ---
class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "level": record.levelname,
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

def setup_logging(log_path="automatic_hybrid_bot.log", *, json_logs=True, level=logging.INFO):
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    file_h = RotatingFileHandler(p, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    stream_h = logging.StreamHandler(sys.stdout)

    if json_logs:
        fmt = JsonFormatter()
    else:
        fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    file_h.setFormatter(fmt)
    stream_h.setFormatter(fmt)

    # Yliaja aiemmat handlerit ja ota sekä tiedosto että konsoli käyttöön
    logging.basicConfig(level=level, handlers=[file_h, stream_h], force=True)

    # Varmista että nimetyt loggerit propagoivat juureen (eivät jää "omiksi saariksi")
    for name in (
        "automatic_hybrid_bot",
        "hybrid_trading_bot",
        "discovery_engine",
        "sources.pumpportal_newtokens",
        "sources.raydium_newpools",
        "rpc_pool",
        "telegram_bot_integration",
        "quality_panel",
    ):
        logging.getLogger(name).propagate = True
# --- END LOGGING SETUP ---

# Nosta PumpPortal moduulilogi INFO:lle
logging.getLogger("sources.pumpportal_newtokens").setLevel(logging.INFO)
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from hybrid_trading_bot import HybridTradingBot
from telegram_bot_integration import TelegramBot
from config import load_config, load_config_cached
from metrics import init_metrics
from json_logging import generate_run_id, generate_cycle_id
from rpc_pool import init_rpc_pool, get_rpc_pool

# Aikavyöhyke
HELSINKI_TZ = ZoneInfo("Europe/Helsinki")

# Aseta logging heti käynnistyksessä
setup_logging("automatic_hybrid_bot.log", json_logs=True, level=logging.INFO)
logger = logging.getLogger(__name__)

class AutomaticHybridBot:
    """Automaattinen Hybrid Trading Bot - Parannettu versio"""
    
    def __init__(self, *, max_cycles: int | None = None, max_runtime_sec: float | None = None):
        # Lue runtime konfiguraatio
        config = load_config()

        # Offline-modin tunnistus (HYBRID_BOT_OFFLINE=1/true/on)
        offline_env = (os.getenv("HYBRID_BOT_OFFLINE") or "").strip().lower()
        self.offline_mode = offline_env in {"1", "true", "yes", "on"}

        # Luo Telegram bot ensin (tai offline stub)
        if self.offline_mode:
            self.telegram_bot = NullTelegramBot()
            logger.info("🧪 Offline mode aktiivinen – Telegram ilmoitukset ohitetaan")
        else:
            self.telegram_bot = TelegramBot(
                rate_limit_sec=config.telegram.cooldown_seconds,
                max_backoff_sec=config.telegram.max_backoff_seconds,
                backoff_multiplier=config.telegram.backoff_multiplier
            )

        # Injektoi Telegram bot HybridTradingBotiin
        self.trading_bot = HybridTradingBot(telegram=self.telegram_bot, offline_mode=self.offline_mode)
        self.running = False
        self.cycle_count = 0
        self.baseline_metrics = None
        self.start_time = None
        self.run_id = generate_run_id()
        # JSON logging setup
        self.json_logger = logging.getLogger(__name__)
        self._run_started_at = time.time()
        
        # Testimoodi parametrit (ympäristömuuttujat ylikirjoittavat konfiguraation)
        self._max_cycles = max_cycles or config.runtime.test_max_cycles
        self._max_runtime_sec = max_runtime_sec or config.runtime.test_max_runtime_sec
        self._deadline = None  # Asetetaan start():ssa
        
        # Startup watchdog
        self._startup_watchdog_task = None
        self._startup_watchdog_sec = int(os.getenv("STARTUP_WATCHDOG_SEC", "5") or "5")
        
        # Manual trigger
        self._manual_trigger_task = None
        self._manual_trigger_path = Path(".runtime/trigger_cycle")
        self._manual_trigger_interval = float(os.getenv("MANUAL_TRIGGER_POLL_SEC", "1.0") or "1.0")
        
        # Heartbeat
        self._last_cycle_ts = time.time()
        self._heartbeat_task = None
        self._heartbeat_interval = float(os.getenv("HEARTBEAT_INTERVAL_SEC", "10") or "10")
        
        # Monotonic scheduling state
        self._next_tick_mono = None
        
        # Graceful shutdown state
        self._shutting_down = False
        self._shutdown_timeout_sec = float(os.getenv("SHUTDOWN_TIMEOUT_SEC", "12") or 12)
        
        # step-trace: oma tiedosto riippumatta loggingista
        self._trace_path = Path(".runtime") / "shutdown_trace.log"
        self._trace_path.parent.mkdir(parents=True, exist_ok=True)
        def _trace_step(msg):
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            try:
                with self._trace_path.open("a", encoding="utf-8") as f:
                    f.write(f"[{ts}] {msg}\n")
            except Exception:
                pass
        self._trace = _trace_step
        self._trace("init: constructed")
        
        # 1) asyncio-polku (loop.add_signal_handler)
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self.request_shutdown("SIGTERM(loop)")))
            loop.add_signal_handler(signal.SIGINT,  lambda: asyncio.create_task(self.request_shutdown("SIGINT(loop)")))
            self._trace("signal: loop handlers installed")
        except Exception as e:
            self._trace(f"signal: loop handler install failed: {e}")
        
        # 2) sync-fallback (signal.signal) → aja shutdown coroutinen thread-safe
        def _sync_sig_handler(signum, frame):
            self._trace(f"signal: sync handler fired {signum}")
            try:
                loop = asyncio.get_running_loop()
                # jos ollaan loop-threadissä:
                loop.call_soon_threadsafe(asyncio.create_task, self.request_shutdown(f"SIGNAL {signum}(sync)"))
            except RuntimeError:
                # ei aktiivista loopia tässä threadissä → käytä policyä
                try:
                    loop = asyncio.get_event_loop_policy().get_event_loop()
                    loop.call_soon_threadsafe(asyncio.create_task, self.request_shutdown(f"SIGNAL {signum}(sync-py)"))
                except Exception:
                    self._trace("signal: no loop available; hard exit")
                    # Älä käytä sys.exit() - anna prosessin kuolla luonnollisesti
                    import os
                    os._exit(0)
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, _sync_sig_handler)
            except Exception as e:
                self._trace(f"signal: sync install failed for {sig}: {e}")
        
        # atexit-varmistus
        def _atexit_hook():
            self._trace("atexit: process exiting")
        atexit.register(_atexit_hook)
    
    def _signal_handler(self):
        """Käsittele sammutus signaalit - graceful shutdown"""
        logger.info("📡 Vastaanotettu sammutus signaali")
        self.running = False
    
    async def request_shutdown(self, reason: str = "signal"):
        """
        Idempotentti shutdown-pyyntö. Käynnistää graceful shutdownin taustalla.
        """
        if getattr(self, "_shutting_down", False):
            return
        self._shutting_down = True
        self._trace(f"shutdown: requested ({reason})")
        self.running = False  # Pysäytä pääsilmukka
        try:
            await asyncio.wait_for(self.shutdown(), timeout=self._shutdown_timeout_sec)
            self._trace("shutdown: completed OK")
        except asyncio.TimeoutError:
            self._trace("shutdown: TIMEOUT — forcing exit")
        except Exception as e:
            self._trace(f"shutdown: error {e}")
        finally:
            await asyncio.sleep(0.2)
            # Älä käytä sys.exit() async-kontekstissa - se aiheuttaa SystemExit exceptionin
            # Sen sijaan palauta False tai heitä asyncio.CancelledError
            raise asyncio.CancelledError("Bot shutdown requested")
    
    def _align_to_next_minute(self) -> float:
        """Align seuraavaan minuuttiin"""
        import os
        if os.getenv("TEST_ALIGN_NOW") == "1":
            # käynnistä heti, ilman minuutin align-odotusta
            logger.info("🧪 TEST_ALIGN_NOW=1 → aloitetaan syklit heti")
            return 0.0  # heti
        
        now = datetime.now(HELSINKI_TZ)
        next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        wait_seconds = (next_minute - now).total_seconds()
        logger.info(f"⏰ Align seuraavaan minuuttiin: {wait_seconds:.1f}s odotusta")
        return wait_seconds
    
    def _calculate_baseline_metrics(self, result: dict) -> dict:
        """Laske baseline metriikat"""
        return {
            'portfolio_value': result.get('portfolio_value', 0),
            'total_pnl': result.get('portfolio_pnl', 0),
            'active_positions': result.get('active_positions', 0),
            'performance_metrics': result.get('performance_metrics', {}).copy(),
            'timestamp': result.get('timestamp', datetime.now(HELSINKI_TZ).isoformat())
        }
    
    async def _send_hourly_report(self, result: dict) -> None:
        """Lähetä tunnin raportti vertaillen baselineen"""
        try:
            current_metrics = self._calculate_baseline_metrics(result)
            
            if self.baseline_metrics:
                # Vertaa baselineen
                portfolio_change = current_metrics['portfolio_value'] - self.baseline_metrics['portfolio_value']
                pnl_change = current_metrics['total_pnl'] - self.baseline_metrics['total_pnl']
                positions_change = current_metrics['active_positions'] - self.baseline_metrics['active_positions']
                
                # Performance muutos
                current_win_rate = current_metrics['performance_metrics'].get('win_rate', 0)
                baseline_win_rate = self.baseline_metrics['performance_metrics'].get('win_rate', 0)
                win_rate_change = current_win_rate - baseline_win_rate
                
                message = f"⏰ *Tunnin Raportti:*\n\n"
                message += f"💰 Portfolio: ${current_metrics['portfolio_value']:.2f} ({portfolio_change:+.2f})\n"
                message += f"📈 PnL: ${current_metrics['total_pnl']:.2f} ({pnl_change:+.2f})\n"
                message += f"🎯 Win Rate: {current_win_rate:.1f}% ({win_rate_change:+.1f}%)\n"
                message += f"📊 Positioita: {current_metrics['active_positions']} ({positions_change:+d})\n"
                message += f"🔄 Syklejä: {self.cycle_count}\n"
                message += f"⏱️ Aikaa kulunut: {self._get_runtime()}"
                
                if result.get('hot_candidates'):
                    message += f"\n🔥 Hot Candidates: {len(result['hot_candidates'])}"
                
                await self.telegram_bot.send_message(message)
                logger.info("✅ Tunnin raportti lähetetty")
            else:
                # Ensimmäinen raportti - aseta baseline
                self.baseline_metrics = current_metrics
                message = f"📊 *Baseline Asetettu:*\n\n"
                message += f"💰 Portfolio: ${current_metrics['portfolio_value']:.2f}\n"
                message += f"📈 PnL: ${current_metrics['total_pnl']:.2f}\n"
                message += f"🎯 Win Rate: {current_metrics['performance_metrics'].get('win_rate', 0):.1f}%\n"
                message += f"📊 Positioita: {current_metrics['active_positions']}"
                
                await self.telegram_bot.send_message(message)
                logger.info("✅ Baseline asetettu")
                
        except Exception as e:
            logger.error(f"Virhe lähettäessä tunnin raporttia: {e}")
    
    def _get_runtime(self) -> str:
        """Hae ajettu aika"""
        if self.start_time:
            runtime = datetime.now(HELSINKI_TZ) - self.start_time
            hours = int(runtime.total_seconds() // 3600)
            minutes = int((runtime.total_seconds() % 3600) // 60)
            return f"{hours}h {minutes}m"
        return "0h 0m"
    
    def _write_cycle_status(self, evt: str, payload: dict):
        """
        Kirjoita .runtime/last_cycle.json (atomisesti) ja appendaa .runtime/cycle_events.ndjson.
        """
        import json
        from pathlib import Path
        base = Path(".runtime")
        base.mkdir(parents=True, exist_ok=True)
        last = base / "last_cycle.json"
        log = base / "cycle_events.ndjson"
        data = {"evt": evt, **payload}
        # atomic write
        tmp = base / "_last.tmp"
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(last)
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    
    async def _startup_watchdog(self):
        """Startup watchdog - pakota ensimmäinen sykli 5s sisällä"""
        try:
            await asyncio.sleep(self._startup_watchdog_sec)
            from pathlib import Path
            last = Path(".runtime/last_cycle.json")
            needs_kick = True
            existed = last.exists()
            if existed:
                try:
                    import json
                    data = json.loads(last.read_text(encoding="utf-8")) or {}
                    last_run_id = data.get("run_id")
                    if last_run_id == getattr(self, "run_id", None):
                        needs_kick = False  # oma runi on jo kirjoittanut cycle_start
                    else:
                        # tsekataan aikaleima – jos ennen starttia, käsitellään vanhana
                        ts = data.get("ts")
                        if ts:
                            try:
                                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                                needs_kick = dt.timestamp() < getattr(self, "_run_started_at", time.time()) - 0.2
                            except Exception:
                                needs_kick = True
                        else:
                            needs_kick = True
                    if needs_kick:
                        # varmistetaan ettei uusi runi esty edellisen tuoreesta tiedostosta
                        mtime = last.stat().st_mtime
                        if mtime >= getattr(self, "_run_started_at", time.time()) - 0.1 and last_run_id != getattr(self, "run_id", None):
                            # tiedosto on lähes samanikäinen -> silti pakota uusi sykli
                            needs_kick = True
                except Exception:
                    needs_kick = True
            if needs_kick:
                logger.warning(
                    "⏱️ Startup watchdog käynnistää syklin (last_exists=%s, needs_kick=%s)",
                    existed,
                    needs_kick
                )
                print(f"WATCHDOG TRIGGER (no fresh cycle in {self._startup_watchdog_sec}s)")
                await self.run_trading_cycle()
        except Exception as e:
            logger.warning(f"Startup watchdog error: {e}")
    
    async def _manual_trigger_watcher(self):
        """Manuaalitriggeri tiedostolla"""
        while True:
            try:
                if self._manual_trigger_path.exists():
                    self._manual_trigger_path.unlink(missing_ok=True)
                    print("MANUAL_TRIGGER cycle")
                    await self.run_trading_cycle()
            except Exception as e:
                logger.warning(f"Manual trigger error: {e}")
            await asyncio.sleep(self._manual_trigger_interval)
    
    async def _heartbeat(self):
        """Heartbeat - idle-detector"""
        while True:
            try:
                idle = time.time() - float(getattr(self, "_last_cycle_ts", 0))
                if idle >= 20:  # yli 20s ilman cycle_end/start
                    logger.info(f"💓 heartbeat: idle={idle:.1f}s (scheduler alive)")
            except Exception:
                pass
            await asyncio.sleep(self._heartbeat_interval)
    
    async def run_trading_cycle(self):
        """Suorita yksi trading-sykli"""
        cycle_start = time.time()
        
        # Varmista että discovery engine on käynnissä
        try:
            await self.trading_bot._ensure_discovery_started()
        except Exception as e:
            logger.warning(f"Virhe käynnistettäessä discovery engine: {e}")
        
        # Suorita analyysi sykli
        cycle_id = generate_cycle_id()
        logger.info(f"🔄 Aloitetaan analyysi sykli #{self.cycle_count + 1}")
        self.json_logger.info("Cycle started", extra={"cycle_number": self.cycle_count + 1, "cycle_id": cycle_id})
        
        # ASCII-markkeri ja status-tiedosto cycle_start
        payload = {
            "ts": datetime.now(HELSINKI_TZ).isoformat(timespec="seconds"),
            "run_id": getattr(self, "run_id", None),
            "cycle_id": self.cycle_count + 1,
        }
        print(f"CYCLE_START cycle_id={self.cycle_count + 1}")   # ASCII-markkeri stdoutiin
        self._write_cycle_status("cycle_start", payload)
        
        # Evt-logi cycle_start
        self._log_evt = getattr(self, "_log_evt", None) or (lambda evt, **kv: logger.info(json.dumps({"evt": evt, **kv}, ensure_ascii=False)))
        self._log_evt("cycle_start",
                      run_id=getattr(self, "run_id", None),
                      cycle_id=self.cycle_count + 1)
        
        try:
            result = await self.trading_bot.run_analysis_cycle()
        except AttributeError as e:
            # Jos _ensure_discovery_started puuttuu, älä jää looppaamaan
            logger.error(f"🛑 Kriittinen virhe trading-syklissä: {e}. Pysäytetään kunnes koodi päivitetty.")
            self.json_logger.error("Critical error in trading cycle", extra={"error": str(e), "cycle_id": cycle_id})
            self.stop()
            return
        except Exception as e:
            logger.error(f"Virhe trading-syklissä: {e}")
            self.json_logger.error("Error in trading cycle", extra={"error": str(e), "cycle_id": cycle_id})
            
            # ASCII-markkeri ja status-tiedosto cycle_end fail
            payload = {
                "ts": datetime.now(HELSINKI_TZ).isoformat(timespec="seconds"),
                "run_id": getattr(self, "run_id", None),
                "cycle_id": self.cycle_count + 1,
                "error": str(e),
                "result": "fail",
            }
            print(f"CYCLE_END cycle_id={self.cycle_count + 1} result=fail")  # ASCII-markkeri stdoutiin
            self._write_cycle_status("cycle_end", payload)
            
            # Evt-logi cycle_end fail
            self._log_evt("cycle_end",
                          result="fail",
                          error=str(e),
                          run_id=getattr(self, "run_id", None),
                          cycle_id=self.cycle_count + 1)
            return
        
        if result.get('error'):
            logger.error(f"Analyysi sykli epäonnistui: {result['error']}")
            self.json_logger.error("Cycle failed", extra={"error": result['error'], "cycle_id": cycle_id})
            
            # ASCII-markkeri ja status-tiedosto cycle_end fail
            payload = {
                "ts": datetime.now(HELSINKI_TZ).isoformat(timespec="seconds"),
                "run_id": getattr(self, "run_id", None),
                "cycle_id": self.cycle_count + 1,
                "error": str(result['error']),
                "result": "fail",
            }
            print(f"CYCLE_END cycle_id={self.cycle_count + 1} result=fail")  # ASCII-markkeri stdoutiin
            self._write_cycle_status("cycle_end", payload)
            
            # Evt-logi cycle_end fail
            self._log_evt("cycle_end",
                          result="fail",
                          error=str(result['error']),
                          run_id=getattr(self, "run_id", None),
                          cycle_id=self.cycle_count + 1)
        else:
            self.cycle_count += 1
            cycle_duration = time.time() - cycle_start
            self.json_logger.info("Cycle completed", extra={
                "cycle_id": cycle_id,
                "duration_sec": cycle_duration,
                "hot_candidates": len(result.get('hot_candidates', [])),
                "tokens_analyzed": result.get('tokens_analyzed', 0)
            })
            logger.info(f"✅ Sykli #{self.cycle_count} valmis")
            
            # ASCII-markkeri ja status-tiedosto cycle_end success
            hot = 0
            toks = 0
            if isinstance(result, dict):
                hot = len(result.get("hot_candidates", []) or [])
                toks = len(result.get("tokens", []) or [])
            payload = {
                "ts": datetime.now(HELSINKI_TZ).isoformat(timespec="seconds"),
                "run_id": getattr(self, "run_id", None),
                "cycle_id": self.cycle_count,
                "tokens": toks,
                "hot": hot,
                "result": "success",
            }
            print(f"CYCLE_END cycle_id={self.cycle_count} hot={hot} tokens={toks}")  # ASCII-markkeri stdoutiin
            self._write_cycle_status("cycle_end", payload)
            
            # Evt-logi cycle_end success
            self._log_evt("cycle_end",
                          result="success",
                          run_id=getattr(self, "run_id", None),
                          cycle_id=self.cycle_count,
                          tokens=toks,
                          hot=hot)
            
            # Tunnin raportti (joka 60. sykli)
            if self.cycle_count % 60 == 0:
                await self._send_hourly_report(result)
        
        # Päivitä heartbeat
        self._last_cycle_ts = time.time()
    
    async def start(self):
        """Käynnistä automaattinen bot - tarkka ajastus"""
        logger.info("🚀 Käynnistetään Automatic Hybrid Trading Bot...")
        self.start_time = datetime.now(HELSINKI_TZ)
        self._run_started_at = time.time()
        
        # Aseta deadline kun event loop on käynnissä
        if self._max_runtime_sec:
            self._deadline = asyncio.get_running_loop().time() + self._max_runtime_sec
        
        # Itse-SIG-testi (valinn.): FORCE_TERM_AFTER_SEC
        tsec = int(os.getenv("FORCE_TERM_AFTER_SEC","0") or "0")
        if tsec > 0:
            async def _self_term():
                await asyncio.sleep(tsec)
                self._trace(f"self-term: sending SIGTERM after {tsec}s")
                os.kill(os.getpid(), signal.SIGTERM)
            asyncio.create_task(_self_term())
        
        self._trace("start: scheduler armed")
        
        # Käynnistä metrics server
        config = load_config()
        config.metrics.enabled = False
        logger.info("📊 Metrics disabled (forced by code override)")
        actual_port = init_metrics(
            namespace=config.metrics.namespace,
            host=config.metrics.host,
            port=config.metrics.port,
            enabled=config.metrics.enabled
        )
        if actual_port:
            # Curl-ystävällinen host
            ok_host = "127.0.0.1" if config.metrics.host in ("0.0.0.0", "") else config.metrics.host
            logger.info(f"📊 Metrics endpoint: http://{config.metrics.host}:{actual_port}/metrics")
            logger.info(f"📊 Metrics endpoint (curl): http://{ok_host}:{actual_port}/metrics")
        
        # Alusta RPC pool
        rpc_pool = init_rpc_pool(
            endpoints=config.io.rpc_endpoints,
            error_threshold=5,
            penalty_sec=120
        )
        logger.info(f"🔄 RPC Pool alustettu: {len(config.io.rpc_endpoints)} endpointtia")
        
        # Lähetä käynnistys viesti (taustataskuna)
        if not self.offline_mode:
            asyncio.create_task(self._send_startup_message())
        else:
            logger.info("🧪 Offline mode: käynnistysviesti ohitetaan")

        # Käynnistä komennonpollaus (taustataskuna)
        if not self.offline_mode and config.telegram.enable_command_polling:
            asyncio.create_task(self._start_telegram_polling())
        
        self.running = True
        
        # 1) KÄYNNISTÄ AJASTUS-SILMUKKA ENNEN LÄHTEIDEN KÄYNNISTYSTÄ
        logger.info("⏱️ Cycle scheduler armed (interval=60s)")
        if os.getenv("TEST_ALIGN_NOW") == "1":
            logger.info("🧪 TEST_ALIGN_NOW=1 → first cycle immediate")
        
        # 2) KÄYNNISTÄ TAUSTATASKUT
        self._startup_watchdog_task = asyncio.create_task(self._startup_watchdog())
        self._manual_trigger_task = asyncio.create_task(self._manual_trigger_watcher())
        self._heartbeat_task = asyncio.create_task(self._heartbeat())
        
        # 3) LÄHTEET KÄYNNISTETÄÄN VASTA KUN SYKLI ALOITTAA
        
        # Align ensimmäiseen minuuttiin
        align_seconds = self._align_to_next_minute()
        logger.info(f"⏰ Align odotus: {align_seconds:.1f}s")
        await asyncio.sleep(align_seconds)
        logger.info("✅ Align odotus valmis, aloitetaan pääsilmukka")
        # aseta monotonic schedule lähtöpiste
        try:
            self._next_tick_mono = asyncio.get_running_loop().time()
        except Exception:
            self._next_tick_mono = None
        # cache kill switch path kerran
        try:
            cfg_once = load_config_cached()
            self._kill_switch_path = cfg_once.runtime.kill_switch_path
        except Exception:
            self._kill_switch_path = None
        
        # Pääsilmukka - tarkka 60s ajastus
        while self.running:
            try:
                # Tarkista pysäytysehtoja (testimoodi)
                if (self._max_cycles and self.cycle_count >= self._max_cycles) or \
                   (self._deadline and asyncio.get_event_loop().time() >= self._deadline):
                    logger.info(f"🛑 Pysäytysehto täyttyi - lopetetaan")
                    if self._max_cycles and self.cycle_count >= self._max_cycles:
                        logger.info(f"   - Maksimisyklejä ({self._max_cycles}) saavutettu")
                    if self._deadline and asyncio.get_event_loop().time() >= self._deadline:
                        logger.info(f"   - Maksimiaika saavutettu")
                    self.stop()
                    break
                
                # Suorita sykli
                await self.run_trading_cycle()
                
                # Tarkista kill switch ilman jatkuvaa YAML-latausta
                if getattr(self, "_kill_switch_path", None) and os.path.exists(self._kill_switch_path):
                    logger.warning("🛑 Kill switch havaittu – pysäytetään botti siististi.")
                    await self.request_shutdown("kill_switch")
                    break
                
                # Driftitön ajastus monotonic-kellolla
                try:
                    loop_now = asyncio.get_running_loop().time()
                except Exception:
                    loop_now = None
                if loop_now is not None:
                    if self._next_tick_mono is None:
                        self._next_tick_mono = loop_now
                    self._next_tick_mono += 60.0
                    delay = self._next_tick_mono - loop_now
                    if delay > 0:
                        logger.info(f"⏰ Odotetaan {delay:.1f} sekuntia ennen seuraavaa sykliä...")
                        await asyncio.sleep(delay)
                    else:
                        logger.warning("⚠️ Sykli kesti liian kauan - jatketaan heti")
                else:
                    # Varafallback jos monotonic ei saatavilla
                    await asyncio.sleep(60.0)
                
            except KeyboardInterrupt:
                logger.info("📡 KeyboardInterrupt vastaanotettu")
                break
            except Exception as e:
                logger.error(f"Virhe pääsilmukassa: {e}")
                await asyncio.sleep(5)  # Odota ennen uudelleenyritystä
        
        await self._graceful_shutdown()
    
    async def _send_startup_message(self):
        """Lähetä käynnistys viesti taustataskuna"""
        try:
            await self.telegram_bot.send_message(
                "🤖 *Automatic Hybrid Trading Bot käynnistetty!*\n"
                "📍 Aikavyöhyke: Europe/Helsinki\n"
                "⏰ Ajastus: 60s välein (driftittömästi)\n"
                "📊 Tunnin raportit baselineen verrattuna"
            )
        except Exception as e:
            logger.warning(f"Virhe lähettäessä käynnistys viestiä: {e}")
    
    async def _start_telegram_polling(self):
        """Käynnistä Telegram komennonpollaus taustataskuna"""
        try:
            config = load_config_cached()
            await self.telegram_bot.start_polling(
                on_command=self._on_telegram_command,
                poll_interval=config.telegram.poll_interval_sec,
                allowed_chat_id=config.telegram.allowed_chat_id
            )
        except Exception as e:
            logger.warning(f"Virhe käynnistettäessä Telegram pollaus: {e}")
    
    async def _start_sources_background(self):
        """Käynnistä lähteet taustataskuna"""
        try:
            # Käynnistä discovery engine taustataskuna
            await self.trading_bot._ensure_discovery_started()
            logger.info("✅ Discovery engine käynnistetty taustalla")
        except Exception as e:
            logger.warning(f"Virhe käynnistettäessä lähteitä taustalla: {e}")
    
    async def shutdown(self):
        """Idempotentti graceful shutdown järjestyksessä"""
        import contextlib, asyncio, time, logging
        if getattr(self, "_shutdown_started", False):
            return
        self._shutdown_started = True
        self._trace("shutdown: begin")
        logger.info("🛑 Sammutus aloitettu…")

        # 1) telegram notice
        self._trace("step: telegram_notice")
        with contextlib.suppress(Exception):
            if getattr(self, "trading_bot", None):
                await asyncio.wait_for(self.trading_bot.send_shutdown_notice("signal"), timeout=2.0)
                await asyncio.sleep(0.2)

        # 2) peruuttele omat taustataskit
        self._trace("step: cancel_own_tasks")
        for tn in ("_manual_trigger_task","_heartbeat_task","_startup_watchdog_task"):
            t = getattr(self, tn, None)
            if t:
                t.cancel()
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(t, timeout=2.0)

        # 3) pysäytä DiscoveryEngine (stop + wait_closed)
        self._trace("step: de_stop")
        with contextlib.suppress(Exception):
            de = getattr(getattr(self, "trading_bot", None), "discovery", None)
            if de:
                await asyncio.wait_for(de.stop(), timeout=3.0)
                self._trace("step: de_wait_closed")
                await asyncio.wait_for(de.wait_closed(), timeout=3.0)
                self._trace("step: de_wait_closed_ok")

        # 4) sulje sessiot (telegram tms.)
        self._trace("step: close_sessions")
        with contextlib.suppress(Exception):
            tg = getattr(getattr(self, "trading_bot", None), "telegram", None)
            if tg and hasattr(tg, "close"):
                await asyncio.wait_for(tg.close(), timeout=2.0)

        # 5) flush logs
        try:
            for h in logging.getLogger().handlers:
                with contextlib.suppress(Exception): h.flush()
        except Exception: pass

        # 6) Lopuksi loki
        logger.info("✅ Graceful shutdown valmis")
        self._trace("shutdown: end")
    
    async def _graceful_shutdown(self):
        """Siisti sammutus - vanha nimi, kutsuu uutta shutdown()"""
        await self.shutdown()

    def stop(self):
        """Pysäytä bot siististi"""
        if self.running:
            logger.info("🛑 Pysäytetään AutomaticHybridBot...")
            self.running = False
            
            # Pysäytä komennonpollaus
            try:
                asyncio.create_task(self.telegram_bot.stop_polling())
            except Exception as e:
                logger.warning(f"Virhe pysäyttäessä komennonpollaus: {e}")

    async def _on_telegram_command(self, cmd: str, chat_id: int):
        """Käsittele Telegram komennot"""
        if cmd.startswith('/stats'):
            try:
                text = self.trading_bot.get_stats_text()
                await self.telegram_bot.send_message(text)
            except Exception as e:
                logger.warning(f"Virhe käsittellessä /stats komentoa: {e}")

    async def run(self):
        """Käynnistä bot ja odota että se lopettaa"""
        await self.start()

async def main():
    """Pääfunktio"""
    # Lue konfiguraatio
    cfg = load_config()
    
    # Lue ympäristömuuttujat testimoodia varten
    max_cycles = int(os.getenv("TEST_MAX_CYCLES", "0") or 0) or None
    max_runtime = float(os.getenv("TEST_MAX_RUNTIME", "0") or 0.0) or None
    
    # Loggaa konfiguraatio arvot
    logger.info(f"TEST_MAX_CYCLES={cfg.runtime.test_max_cycles} TEST_MAX_RUNTIME={cfg.runtime.test_max_runtime_sec}")
    logger.info(f"Ympäristömuuttujat: max_cycles={max_cycles}, max_runtime={max_runtime}")
    
    # Luo bot testimoodin parametreilla
    bot = AutomaticHybridBot(max_cycles=max_cycles, max_runtime_sec=max_runtime)
    
    # Loggaa testimoodi jos aktiivinen
    if max_cycles or max_runtime:
        logger.info(f"🧪 Testimoodi aktiivinen: max_cycles={max_cycles}, max_runtime={max_runtime}s")
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("📡 KeyboardInterrupt pääfunktiossa")
    except Exception as e:
        logger.error(f"Kriittinen virhe: {e}")
        # Ei sys.exit - anna prosessin kuolla luonnollisesti

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Pyydä siisti sammutus — jos loop jo poissa, lokita vain
        import logging
        logging.getLogger(__name__).info("🛑 KeyboardInterrupt — requesting shutdown")
        # ei suoraa sys.exit(1): atexit hoitaa minimit
    except Exception as e:
        logger.error(f"Sovelluksen virhe: {e}")
    finally:
        logger.info("👋 Automatic Hybrid Trading Bot lopetettu")
