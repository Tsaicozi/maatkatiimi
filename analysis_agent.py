#!/usr/bin/env python3
"""
Analysis Agent

- Optionally runs AutomaticHybridBot in-process (offline by default)
- Follows .runtime/cycle_events.ndjson and automatic_hybrid_bot.log with rotation-aware tailers
- Aggregates cycle metrics, errors/warnings, drift, and writes periodic analysis JSON files

Usage examples:
  python analysis_agent.py --once
  python analysis_agent.py --run-bot --analysis-interval 60
  python analysis_agent.py --from-beginning --output-dir .
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
import contextlib
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo


# --- Logging (JSON) ---
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


def setup_logging(log_path: str = "analysis_agent.log", *, level: int = logging.INFO) -> None:
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    file_h = RotatingFileHandler(p, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    stream_h = logging.StreamHandler(sys.stdout)
    fmt = JsonFormatter()
    file_h.setFormatter(fmt)
    stream_h.setFormatter(fmt)
    logging.basicConfig(level=level, handlers=[file_h, stream_h], force=True)


logger = logging.getLogger("analysis_agent")


# --- Constants ---
HELSINKI_TZ = ZoneInfo("Europe/Helsinki")
RUNTIME_DIR = Path(".runtime")
CYCLE_EVENTS_PATH = RUNTIME_DIR / "cycle_events.ndjson"
BOT_LOG_PATH = Path("automatic_hybrid_bot.log")


# --- Utilities ---
def now_iso() -> str:
    return datetime.now(HELSINKI_TZ).isoformat(timespec="seconds")


def parse_iso(ts: str) -> Optional[datetime]:
    try:
        # Accept both local and Z times
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def seconds_to_next_minute(dt: datetime) -> float:
    # Drift relative to exact minute boundaries
    aligned_minute = dt.replace(second=0, microsecond=0)
    # Nearest following boundary
    if dt.second != 0 or dt.microsecond != 0:
        aligned_minute = aligned_minute.replace()  # just to make intent explicit
    elapsed = (dt - aligned_minute).total_seconds()
    return elapsed  # 0..59.999 (how far past the minute we are)


# --- Rotation-aware tailer ---
class RotationAwareTailer:
    """
    Minimal rotation-aware tailer for text files.
    - Re-opens when inode changes or file is truncated
    - Calls on_line callback for each new line
    """

    def __init__(
        self,
        path: Path,
        *,
        from_beginning: bool = False,
        poll_interval: float = 0.5,
        name: str = "tailer",
        encoding: str = "utf-8",
        on_line: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.path = path
        self.from_beginning = from_beginning
        self.poll_interval = poll_interval
        self.name = name
        self.encoding = encoding
        self.on_line = on_line
        self._stop = False
        self._fh: Optional[Any] = None
        self._inode: Optional[int] = None
        self._pos: int = 0

    def stop(self) -> None:
        self._stop = True

    async def run(self) -> None:
        logger.info("Tailer start", extra={"file": str(self.path), "name": self.name})
        while not self._stop:
            try:
                if self._fh is None:
                    if not self.path.exists():
                        await asyncio.sleep(self.poll_interval)
                        continue
                    self._fh = self.path.open("r", encoding=self.encoding, errors="replace")
                    try:
                        st = self.path.stat()
                        self._inode = int(st.st_ino)
                        if self.from_beginning:
                            self._pos = 0
                            self._fh.seek(0)
                            self.from_beginning = False  # only first open
                        else:
                            # seek to end
                            self._fh.seek(0, os.SEEK_END)
                            self._pos = self._fh.tell()
                    except Exception:
                        pass

                # Detect rotation or truncation
                try:
                    st = self.path.stat()
                    inode = int(st.st_ino)
                    if self._inode is not None and inode != self._inode:
                        # rotated: reopen fresh file
                        try:
                            self._fh.close()  # type: ignore[union-attr]
                        except Exception:
                            pass
                        self._fh = None
                        self._inode = None
                        self._pos = 0
                        continue
                except FileNotFoundError:
                    # rotated away before new is created
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Read new lines
                assert self._fh is not None
                self._fh.seek(self._pos)
                chunk = await asyncio.to_thread(self._fh.read)
                if not chunk:
                    await asyncio.sleep(self.poll_interval)
                    continue
                self._pos = self._fh.tell()
                for line in chunk.splitlines():
                    if self.on_line:
                        try:
                            self.on_line(line)
                        except Exception:
                            logger.exception("on_line callback failed")
            except Exception:
                logger.exception("Tailer error")
                await asyncio.sleep(self.poll_interval)


# --- Aggregation state ---
@dataclass
class CycleStats:
    total: int = 0
    success: int = 0
    fail: int = 0
    last_cycle_id: int = 0
    tokens_total: int = 0
    hot_total: int = 0
    last_tokens: int = 0
    last_hot: int = 0
    last_ts: Optional[str] = None
    drift_samples: List[float] = field(default_factory=list)
    durations_sec: List[float] = field(default_factory=list)
    last_duration_sec: Optional[float] = None


@dataclass
class LogStats:
    errors: int = 0
    warnings: int = 0
    error_messages: Dict[str, int] = field(default_factory=dict)
    warning_messages: Dict[str, int] = field(default_factory=dict)
    last_error_ts: Optional[str] = None


class Aggregator:
    def __init__(self) -> None:
        self.cycles = CycleStats()
        self.logs = LogStats()
        self.run_id: Optional[str] = None
        self._cycle_start_ts: Dict[int, datetime] = {}

    def ingest_cycle_line(self, line: str) -> None:
        try:
            obj = json.loads(line)
        except Exception:
            return
        evt = obj.get("evt")
        if evt not in {"cycle_start", "cycle_end"}:
            return
        # Track run_id when present
        rid = obj.get("run_id")
        if rid:
            self.run_id = rid
        if evt == "cycle_start":
            self.cycles.total += 1
            self.cycles.last_cycle_id = int(obj.get("cycle_id") or self.cycles.last_cycle_id)
            ts = obj.get("ts") or now_iso()
            self.cycles.last_ts = ts
            dt = parse_iso(ts)
            if dt is not None:
                drift = seconds_to_next_minute(dt)
                # stores how far past minute boundary cycle logged
                self.cycles.drift_samples.append(float(drift))
                if self.cycles.last_cycle_id:
                    self._cycle_start_ts[self.cycles.last_cycle_id] = dt
        elif evt == "cycle_end":
            result = (obj.get("result") or "").lower()
            if result == "success":
                self.cycles.success += 1
                self.cycles.last_tokens = int(obj.get("tokens") or 0)
                self.cycles.last_hot = int(obj.get("hot") or 0)
                self.cycles.tokens_total += self.cycles.last_tokens
                self.cycles.hot_total += self.cycles.last_hot
            else:
                self.cycles.fail += 1
            ts = obj.get("ts") or now_iso()
            self.cycles.last_ts = ts
            # Compute duration if we have matching start ts
            cid_raw = obj.get("cycle_id")
            try:
                cid = int(cid_raw) if cid_raw is not None else None
            except Exception:
                cid = None
            dt_end = parse_iso(ts)
            if cid is not None and dt_end is not None:
                dt_start = self._cycle_start_ts.pop(cid, None)
                if dt_start is not None:
                    dur = max(0.0, (dt_end - dt_start).total_seconds())
                    self.cycles.last_duration_sec = float(dur)
                    self.cycles.durations_sec.append(float(dur))

    def ingest_log_line(self, line: str) -> None:
        # Expect JSON log lines from AutomaticHybridBot
        try:
            obj = json.loads(line)
        except Exception:
            return
        lvl = (obj.get("level") or "").upper()
        msg = str(obj.get("msg") or "")
        ts = str(obj.get("ts") or now_iso())
        if lvl == "ERROR":
            self.logs.errors += 1
            self.logs.last_error_ts = ts
            self.logs.error_messages[msg] = self.logs.error_messages.get(msg, 0) + 1
        elif lvl == "WARNING":
            self.logs.warnings += 1
            self.logs.warning_messages[msg] = self.logs.warning_messages.get(msg, 0) + 1

    def build_report(self) -> Dict[str, Any]:
        drift_avg = sum(self.cycles.drift_samples) / len(self.cycles.drift_samples) if self.cycles.drift_samples else 0.0
        drift_p95 = 0.0
        if self.cycles.drift_samples:
            sorted_samples = sorted(self.cycles.drift_samples)
            idx = int(0.95 * (len(sorted_samples) - 1))
            drift_p95 = sorted_samples[idx]
        duration_avg = sum(self.cycles.durations_sec) / len(self.cycles.durations_sec) if self.cycles.durations_sec else 0.0
        duration_p95 = 0.0
        if self.cycles.durations_sec:
            sorted_durations = sorted(self.cycles.durations_sec)
            didx = int(0.95 * (len(sorted_durations) - 1))
            duration_p95 = sorted_durations[didx]
        return {
            "timestamp": now_iso(),
            "run_id": self.run_id,
            "cycles": {
                "total": self.cycles.total,
                "success": self.cycles.success,
                "fail": self.cycles.fail,
                "last_cycle_id": self.cycles.last_cycle_id,
                "last_ts": self.cycles.last_ts,
                "last_tokens": self.cycles.last_tokens,
                "last_hot": self.cycles.last_hot,
                "tokens_total": self.cycles.tokens_total,
                "hot_total": self.cycles.hot_total,
                "last_duration_sec": self.cycles.last_duration_sec,
                "duration_avg_sec": round(duration_avg, 3),
                "duration_p95_sec": round(duration_p95, 3),
                "duration_samples": len(self.cycles.durations_sec),
                "drift_avg_sec": round(drift_avg, 3),
                "drift_p95_sec": round(drift_p95, 3),
                "drift_samples": len(self.cycles.drift_samples),
            },
            "logs": {
                "errors": self.logs.errors,
                "warnings": self.logs.warnings,
                "last_error_ts": self.logs.last_error_ts,
                "top_error_messages": sorted(self.logs.error_messages.items(), key=lambda kv: kv[1], reverse=True)[:10],
                "top_warning_messages": sorted(self.logs.warning_messages.items(), key=lambda kv: kv[1], reverse=True)[:10],
            },
            # Placeholder for compatibility; not derivable from logs alone
            "hot_candidates": [],
        }


# --- Agent ---
class AnalysisAgent:
    def __init__(
        self,
        *,
        run_bot: bool = False,
        from_beginning: bool = False,
        analysis_interval: int = 60,
        output_dir: Path = Path("."),
        once: bool = False,
    ) -> None:
        self.run_bot = run_bot
        self.from_beginning = from_beginning
        self.analysis_interval = max(5, int(analysis_interval))
        self.output_dir = output_dir
        self.once = once
        self.aggregator = Aggregator()
        self._tasks: List[asyncio.Task[Any]] = []
        self._stopping = False

    async def _start_bot_task(self) -> None:
        # Lazy import to avoid heavy deps when not running the bot
        os.environ.setdefault("HYBRID_BOT_OFFLINE", "1")  # default offline
        try:
            from automatic_hybrid_bot import AutomaticHybridBot  # type: ignore
        except Exception as e:
            logger.warning("Cannot import AutomaticHybridBot; running analysis only", extra={"error": str(e)})
            return
        bot = AutomaticHybridBot()
        try:
            await bot.start()
        except asyncio.CancelledError:
            # Propagate graceful shutdown
            raise
        except Exception:
            logger.exception("Bot task crashed")

    def _on_cycle_line(self, line: str) -> None:
        self.aggregator.ingest_cycle_line(line)

    def _on_log_line(self, line: str) -> None:
        self.aggregator.ingest_log_line(line)

    async def _writer_loop(self) -> None:
        # Periodically write analysis files
        # For --once mode, write a single file then stop
        await asyncio.sleep(0.1)
        if self.once:
            await self._write_snapshot()
            return
        while not self._stopping:
            try:
                await asyncio.sleep(self.analysis_interval)
                await self._write_snapshot()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Writer loop error")

    async def _write_snapshot(self) -> None:
        report = self.aggregator.build_report()
        ts = datetime.now(HELSINKI_TZ).strftime("%Y%m%d_%H%M%S")
        out = self.output_dir / f"hybrid_trading_analysis_{ts}.json"
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            tmp = out.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            tmp.replace(out)
            logger.info("Analysis snapshot written", extra={"file": str(out)})
        except Exception:
            logger.exception("Failed writing analysis snapshot")

    async def start(self) -> None:
        # Start tailers
        cycle_tailer = RotationAwareTailer(
            CYCLE_EVENTS_PATH, from_beginning=self.from_beginning, name="cycle_events", on_line=self._on_cycle_line
        )
        log_tailer = RotationAwareTailer(
            BOT_LOG_PATH, from_beginning=self.from_beginning, name="bot_log", on_line=self._on_log_line
        )
        self._tasks.append(asyncio.create_task(cycle_tailer.run()))
        self._tasks.append(asyncio.create_task(log_tailer.run()))
        self._tasks.append(asyncio.create_task(self._writer_loop()))
        if self.run_bot:
            self._tasks.append(asyncio.create_task(self._start_bot_task()))

    async def stop(self) -> None:
        self._stopping = True
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await asyncio.wait_for(t, timeout=3.0)
            except Exception:
                pass
        # Final snapshot on shutdown (if not once)
        if not self.once:
            with contextlib.suppress(Exception):
                await self._write_snapshot()


# --- CLI ---
async def async_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hybrid Trading Analysis Agent")
    parser.add_argument("--run-bot", action="store_true", help="Run AutomaticHybridBot in-process (offline by default)")
    parser.add_argument("--once", action="store_true", help="Write one analysis file and exit")
    parser.add_argument("--from-beginning", action="store_true", help="Read cycle events from beginning of file")
    parser.add_argument("--analysis-interval", type=int, default=60, help="Seconds between periodic analysis outputs")
    parser.add_argument("--output-dir", type=str, default=".", help="Directory to write analysis files")
    args = parser.parse_args(argv)

    setup_logging("analysis_agent.log", level=logging.INFO)
    logger.info("Agent starting", extra={
        "run_bot": args.run_bot,
        "once": args.once,
        "from_beginning": args.from_beginning,
        "interval": args.analysis_interval,
        "output": args.output_dir,
    })

    agent = AnalysisAgent(
        run_bot=args.run_bot,
        from_beginning=args.from_beginning,
        analysis_interval=args.analysis_interval,
        output_dir=Path(args.output_dir),
        once=args.once,
    )
    await agent.start()

    # Graceful signal handling
    stop_event = asyncio.Event()

    def _signal_handler(_: int, __: Any) -> None:
        if not stop_event.is_set():
            stop_event.set()

    try:
        import contextlib  # noqa: F401
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, _signal_handler, sig, None)
    except Exception:
        pass

    if args.once:
        # Wait briefly for tailers to read current files, then stop
        await asyncio.sleep(0.6)
        await agent.stop()
        return 0

    # Run until signal
    await stop_event.wait()
    await agent.stop()
    return 0


def main() -> None:
    try:
        rc = asyncio.run(async_main())
    except KeyboardInterrupt:
        rc = 0
    except Exception:
        logger.exception("Agent crashed")
        rc = 1
    # Do not sys.exit in async contexts; normal return is fine
    if rc != 0:
        print(f"analysis_agent exited with code {rc}")


if __name__ == "__main__":
    main()

