#!/usr/bin/env python3
"""
Agent Manager & Task Supervisor

- Monitors AutomaticHybridBot via cycle events heartbeat
- Optionally spawns and restarts the bot with exponential backoff
- Integrates AnalysisAgent for continuous reporting
- Graceful shutdown forwarding signals to child

Usage:
  python agent_manager.py --follow-only --analysis-interval 60 --output-dir /workspace
  python agent_manager.py --offline --analysis-interval 60 --output-dir /workspace
  python agent_manager.py --offline --stall-threshold-sec 180 --backoff-min 2 --backoff-max 60
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional
import contextlib
from zoneinfo import ZoneInfo

HELSINKI_TZ = ZoneInfo("Europe/Helsinki")
RUNTIME_DIR = Path(".runtime")
LAST_CYCLE_PATH = RUNTIME_DIR / "last_cycle.json"


# --- Logging ---
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(log_path: str = "agent_manager.log", *, level: int = logging.INFO) -> None:
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    file_h = RotatingFileHandler(p, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    stream_h = logging.StreamHandler(sys.stdout)
    fmt = JsonFormatter()
    file_h.setFormatter(fmt)
    stream_h.setFormatter(fmt)
    logging.basicConfig(level=level, handlers=[file_h, stream_h], force=True)


logger = logging.getLogger("agent_manager")


def parse_iso(ts: str) -> Optional[datetime]:
    try:
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    except Exception:
        return None


async def read_last_cycle_ts() -> Optional[datetime]:
    try:
        if not LAST_CYCLE_PATH.exists():
            return None
        data = json.loads(LAST_CYCLE_PATH.read_text(encoding="utf-8"))
        ts = str(data.get("ts") or "")
        dt = parse_iso(ts)
        return dt
    except Exception:
        return None


@dataclass
class BackoffState:
    attempt: int = 0
    backoff_min: float = 2.0
    backoff_max: float = 60.0

    def next_delay(self) -> float:
        base = min(self.backoff_min * (2 ** max(0, self.attempt - 1)), self.backoff_max)
        # jitter ±20%
        jitter = base * 0.2
        delay = max(0.5, base + random.uniform(-jitter, jitter))
        self.attempt += 1
        return delay

    def reset(self) -> None:
        self.attempt = 0


class AgentManager:
    def __init__(
        self,
        *,
        follow_only: bool,
        offline: bool,
        stall_threshold_sec: int,
        backoff_min: float,
        backoff_max: float,
        max_restarts: int,
        analysis_interval: int,
        analysis_output: Path,
    ) -> None:
        self.follow_only = follow_only
        self.offline = offline
        self.stall_threshold_sec = max(30, int(stall_threshold_sec))
        self.max_restarts = max(0, int(max_restarts))
        self.proc: Optional[asyncio.subprocess.Process] = None
        self._stop = False
        self._restarts = 0
        self._backoff = BackoffState(backoff_min=backoff_min, backoff_max=backoff_max)
        self.analysis_interval = max(10, int(analysis_interval))
        self.analysis_output = analysis_output
        self._tasks: list[asyncio.Task[Any]] = []

    async def _spawn_bot(self) -> None:
        if self.follow_only:
            logger.info("Follow-only: not spawning bot")
            return
        if self.proc and self.proc.returncode is None:
            logger.info("Bot already running (pid=%s)", self.proc.pid)
            return
        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        if self.offline:
            env.setdefault("HYBRID_BOT_OFFLINE", "1")
        # Ensure immediate first cycle after start
        env.setdefault("TEST_ALIGN_NOW", "1")
        cmd = [sys.executable, str(Path("/workspace/automatic_hybrid_bot.py"))]
        logger.info("Spawning bot", extra={"cmd": " ".join(cmd), "offline": self.offline})
        self.proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=str(Path("/workspace")),
        )
        # Stream a few lines from stdout/stderr for visibility
        self._tasks.append(asyncio.create_task(self._pump_stream(self.proc.stdout, "bot.stdout")))
        self._tasks.append(asyncio.create_task(self._pump_stream(self.proc.stderr, "bot.stderr")))
        self._backoff.reset()

    async def _pump_stream(self, stream: Optional[asyncio.StreamReader], name: str) -> None:
        if stream is None:
            return
        try:
            while not self._stop:
                line = await stream.readline()
                if not line:
                    break
                # write to manager logger at DEBUG to avoid noise
                try:
                    logger.debug("%s: %s", name, line.decode("utf-8", "replace").rstrip())
                except Exception:
                    logger.debug("%s: <binary line>", name)
        except Exception:
            # Stream may close on process exit
            pass

    async def _monitor_process(self) -> None:
        while not self._stop:
            if self.follow_only:
                await asyncio.sleep(1.0)
                continue
            if self.proc is None or self.proc.returncode is not None:
                # not running → spawn
                if self.max_restarts and self._restarts >= self.max_restarts:
                    logger.error("Max restarts reached; not spawning further")
                    return
                await self._spawn_bot()
                self._restarts += 1
            # Wait until it exits
            if self.proc is not None:
                rc = await self.proc.wait()
                logger.warning("Bot exited", extra={"returncode": rc})
                # backoff before next spawn
                delay = self._backoff.next_delay()
                await asyncio.sleep(delay)

    async def _heartbeat_watcher(self) -> None:
        last_ok: Optional[datetime] = None
        while not self._stop:
            try:
                dt = await read_last_cycle_ts()
                now = datetime.now(HELSINKI_TZ)
                if dt is not None:
                    last_ok = dt
                idle = (now - (last_ok or now)).total_seconds()
                if idle >= self.stall_threshold_sec:
                    logger.error(
                        "Stall detected", extra={"idle_sec": idle, "threshold": self.stall_threshold_sec}
                    )
                    last_ok = now  # prevent repeated immediate triggers
                    if not self.follow_only:
                        await self._restart_bot_reason("stall")
                else:
                    logger.info(
                        "Heartbeat ok", extra={"idle_sec": round(idle, 1), "threshold": self.stall_threshold_sec}
                    )
            except Exception:
                logger.exception("Heartbeat watcher error")
            await asyncio.sleep(30)

    async def _restart_bot_reason(self, reason: str) -> None:
        if self.follow_only:
            logger.info("Follow-only: skip restart", extra={"reason": reason})
            return
        if self.proc and self.proc.returncode is None:
            try:
                logger.warning("Sending SIGTERM to bot", extra={"pid": self.proc.pid, "reason": reason})
                self.proc.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(self.proc.wait(), timeout=12.0)
                except asyncio.TimeoutError:
                    logger.warning("Force killing bot (timeout)")
                    self.proc.kill()
            except Exception:
                logger.exception("Error terminating bot")
        # backoff then spawn
        delay = self._backoff.next_delay()
        await asyncio.sleep(delay)
        await self._spawn_bot()

    async def _start_analysis(self) -> None:
        try:
            from analysis_agent import AnalysisAgent  # type: ignore
        except Exception as e:
            logger.warning("AnalysisAgent not available", extra={"error": str(e)})
            return
        agent = AnalysisAgent(
            run_bot=False,
            from_beginning=False,
            analysis_interval=self.analysis_interval,
            output_dir=self.analysis_output,
            once=False,
        )
        await agent.start()
        # run until stopped
        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        finally:
            with contextlib.suppress(Exception):
                await agent.stop()

    async def start(self) -> None:
        # Ensure runtime dir
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        # Kick off tasks
        self._tasks.append(asyncio.create_task(self._monitor_process()))
        self._tasks.append(asyncio.create_task(self._heartbeat_watcher()))
        self._tasks.append(asyncio.create_task(self._start_analysis()))

    async def stop(self) -> None:
        self._stop = True
        # Terminate bot
        if self.proc and self.proc.returncode is None:
            try:
                logger.info("Forwarding SIGTERM to bot", extra={"pid": self.proc.pid})
                self.proc.send_signal(signal.SIGTERM)
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(self.proc.wait(), timeout=12.0)
            except Exception:
                logger.exception("Error stopping bot")
        # Cancel tasks
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(t, timeout=3.0)


async def async_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Agent Manager & Task Supervisor")
    parser.add_argument("--follow-only", action="store_true", help="Do not spawn; only monitor and analyze")
    parser.add_argument("--offline", action="store_true", help="Run bot in offline mode when spawning")
    parser.add_argument("--stall-threshold-sec", type=int, default=180, help="Idle seconds before restart")
    parser.add_argument("--backoff-min", type=float, default=2.0, help="Min backoff seconds")
    parser.add_argument("--backoff-max", type=float, default=60.0, help="Max backoff seconds")
    parser.add_argument("--max-restarts", type=int, default=0, help="Max restarts (0 = unlimited)")
    parser.add_argument("--analysis-interval", type=int, default=60, help="Seconds between analysis outputs")
    parser.add_argument("--output-dir", type=str, default="/workspace", help="Directory for analysis files")
    args = parser.parse_args(argv)

    setup_logging("agent_manager.log", level=logging.INFO)
    logger.info("Manager starting", extra={
        "follow_only": args.follow_only,
        "offline": args.offline,
        "stall_threshold": args.stall_threshold_sec,
        "analysis_interval": args.analysis_interval,
        "output_dir": args.output_dir,
    })

    mgr = AgentManager(
        follow_only=args.follow_only,
        offline=args.offline,
        stall_threshold_sec=args.stall_threshold_sec,
        backoff_min=args.backoff_min,
        backoff_max=args.backoff_max,
        max_restarts=args.max_restarts,
        analysis_interval=args.analysis_interval,
        analysis_output=Path(args.output_dir),
    )
    await mgr.start()

    stop_event = asyncio.Event()

    def on_signal(_: int, __: Any) -> None:
        if not stop_event.is_set():
            stop_event.set()

    try:
        import contextlib  # noqa: F401
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, on_signal, sig, None)
    except Exception:
        pass

    await stop_event.wait()
    await mgr.stop()
    return 0


def main() -> None:
    try:
        rc = asyncio.run(async_main())
    except KeyboardInterrupt:
        rc = 0
    except Exception:
        logger.exception("Manager crashed")
        rc = 1
    if rc != 0:
        print(f"agent_manager exited with code {rc}")


if __name__ == "__main__":
    main()

