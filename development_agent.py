#!/usr/bin/env python3
"""
DevelopmentAgent
Seuraa bottia (cycle_events + logit), ehdottaa parannuksia ja voi ajaa
PerformanceAgentin hitailla sykleillä. Tarjoaa myös yksinkertaisen
asynkronisen anti-pattern skannauksen (time.sleep, sync I/O yms.).
"""
from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo


HELSINKI_TZ = ZoneInfo("Europe/Helsinki")
logger = logging.getLogger(__name__)


@dataclass
class DevAgentConfig:
    cycle_events_path: str = ".runtime/cycle_events.ndjson"
    bot_log_path: str = "automatic_hybrid_bot.log"
    suggestion_dir: str = ".runtime/development_reports"
    slow_cycle_threshold_sec: float = 3.0
    monitor_interval_sec: float = 1.0
    profile_on_slow_cycle: bool = True
    anti_pattern_files: Tuple[str, ...] = (
        "hybrid_trading_bot.py",
        "automatic_hybrid_bot.py",
        "discovery_engine.py",
        "sources/pumpportal_ws_newtokens.py",
        "sources/raydium_newpools.py",
    )


@dataclass
class CycleEvent:
    ts: str
    evt: str
    cycle_id: int | None = None
    result: str | None = None
    error: str | None = None
    hot: int | None = None
    tokens: int | None = None
    run_id: str | None = None


@dataclass
class DevSuggestion:
    kind: str
    message: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DevReport:
    generated_at: str
    slow_cycles: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[DevSuggestion] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "slow_cycles": self.slow_cycles,
            "errors": self.errors,
            "suggestions": [dataclasses.asdict(s) for s in self.suggestions],
        }


class DevelopmentAgent:
    def __init__(self, cfg: Optional[DevAgentConfig] = None):
        self.cfg = cfg or DevAgentConfig()
        self._stop_event = asyncio.Event()
        self._last_cycle_seen: int | None = None
        self._seen_offsets: Dict[str, int] = {}
        self._slow_cycle_buffer: List[Dict[str, Any]] = []
        self._errors_buffer: List[Dict[str, Any]] = []

    def _read_new_lines(self, path: Path) -> List[str]:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                return []
            # File offset bookkeeping
            offset = self._seen_offsets.get(str(path), 0)
            size = path.stat().st_size
            if offset > size:
                offset = 0  # rotated
            lines: List[str] = []
            with path.open("r", encoding="utf-8", errors="replace") as f:
                f.seek(offset)
                chunk = f.read()
                if not chunk:
                    self._seen_offsets[str(path)] = f.tell()
                    return []
                lines = chunk.splitlines()
                self._seen_offsets[str(path)] = f.tell()
            return lines
        except Exception as e:
            logger.debug("read_new_lines error for %s: %s", path, e)
            return []

    def _parse_cycle_line(self, line: str) -> Optional[CycleEvent]:
        try:
            data = json.loads(line)
            if not isinstance(data, dict):
                return None
            evt = data.get("evt")
            if not evt:
                return None
            return CycleEvent(
                ts=data.get("ts") or time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                evt=evt,
                cycle_id=data.get("cycle_id"),
                result=data.get("result"),
                error=data.get("error"),
                hot=data.get("hot"),
                tokens=data.get("tokens"),
                run_id=data.get("run_id"),
            )
        except Exception:
            return None

    def _scan_log_errors(self, lines: Iterable[str]) -> List[Dict[str, Any]]:
        found: List[Dict[str, Any]] = []
        patterns = [
            (re.compile(r"RPC .*error|timeout|connection" , re.I), "rpc_error"),
            (re.compile(r"Queue .* täynnä|Queue .* full", re.I), "queue_full"),
            (re.compile(r"DiscoveryEngine virhe|Critical|Kriittinen", re.I), "critical"),
        ]
        for ln in lines:
            for rx, kind in patterns:
                if rx.search(ln):
                    found.append({"kind": kind, "line": ln[:500]})
                    break
        return found

    def _anti_pattern_scan(self) -> List[DevSuggestion]:
        suggestions: List[DevSuggestion] = []
        for rel in self.cfg.anti_pattern_files:
            p = Path(rel)
            if not p.exists():
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            hits: List[str] = []
            if re.search(r"\btime\.sleep\(\s*\d", txt):
                hits.append("time.sleep käytössä – vaihda await asyncio.sleep")
            if re.search(r"\brequests\.(get|post|put|delete)\(", txt):
                hits.append("requests.* synk-kutsut asynk-kontekstissa – käytä aiohttp")
            if re.search(r"open\(.*\)\s*\.read\(\)", txt) and re.search(r"async\s+def", txt):
                hits.append("open().read() asynk-funktiossa – käytä asyncio.to_thread tai aiofiles")
            if re.search(r"run_until_complete\(", txt):
                hits.append("loop.run_until_complete – vältä; käytä suoraan await")

            for h in hits:
                suggestions.append(DevSuggestion(kind="anti_pattern", message=h, meta={"file": rel}))
        return suggestions

    async def _maybe_profile(self) -> Optional[Dict[str, Any]]:
        try:
            from performance_agent import PerformanceAgent
        except ImportError:
            return None
        agent = PerformanceAgent(sample_interval_sec=0.02)
        try:
            await agent.__aenter__()
            # Short sampling burst
            end = asyncio.get_running_loop().time() + 0.8
            while asyncio.get_running_loop().time() < end:
                agent.snapshot()
                await asyncio.sleep(0.05)
        finally:
            with contextlib.suppress(Exception):
                await agent.__aexit__(None, None, None)
        return agent.build_report().to_dict()

    async def monitor(self) -> None:
        Path(self.cfg.suggestion_dir).mkdir(parents=True, exist_ok=True)
        logger.info("DevelopmentAgent started")
        while not self._stop_event.is_set():
            try:
                # cycle events
                ev_lines = self._read_new_lines(Path(self.cfg.cycle_events_path))
                for ln in ev_lines:
                    evt = self._parse_cycle_line(ln)
                    if not evt:
                        continue
                    if evt.evt == "cycle_end":
                        self._last_cycle_seen = evt.cycle_id
                        # Heuristics: slow cycle if tokens small and hot small but warnings earlier
                        if self.cfg.profile_on_slow_cycle:
                            # Approx: if no tokens and not success OR many errors seen recently
                            recent_errs = len(self._errors_buffer[-10:])
                            if (evt.result != "success") or (recent_errs >= 3):
                                prof = await self._maybe_profile()
                                if prof:
                                    self._slow_cycle_buffer.append({
                                        "cycle_id": evt.cycle_id,
                                        "profile": prof,
                                    })

                # log errors
                log_lines = self._read_new_lines(Path(self.cfg.bot_log_path))
                errs = self._scan_log_errors(log_lines)
                if errs:
                    self._errors_buffer.extend(errs[-50:])

                await asyncio.sleep(self.cfg.monitor_interval_sec)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.debug("monitor loop error: %s", e)
                await asyncio.sleep(self.cfg.monitor_interval_sec)

    def build_report(self) -> DevReport:
        sug: List[DevSuggestion] = []
        # From anti-patterns
        with contextlib.suppress(Exception):
            sug.extend(self._anti_pattern_scan())
        # From errors
        if self._errors_buffer:
            kinds = {}
            for e in self._errors_buffer[-200:]:
                kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
            if kinds.get("rpc_error", 0) >= 3:
                sug.append(DevSuggestion(
                    kind="rpc",
                    message="Korkea RPC virhemäärä – nosta timeoutit, lisää backoff ja fallback-endpointit",
                ))
            if kinds.get("queue_full", 0) >= 2:
                sug.append(DevSuggestion(
                    kind="queue",
                    message="Queue täyttyy – säädä max_queue tai pudota burstien aikana vanhinta dataa varmemmin",
                ))

        gen = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        rep = DevReport(
            generated_at=gen,
            slow_cycles=list(self._slow_cycle_buffer[-10:]),
            errors=list(self._errors_buffer[-50:]),
            suggestions=sug,
        )
        return rep

    def write_report(self, rep: DevReport) -> Path:
        Path(self.cfg.suggestion_dir).mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        out = Path(self.cfg.suggestion_dir) / f"dev_report_{ts}.json"
        out.write_text(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Development report written: %s", out)
        return out

    def stop(self) -> None:
        self._stop_event.set()


def _setup_logging() -> None:
    try:
        from logging.handlers import RotatingFileHandler
        p = Path("development_agent.log")
        fh = RotatingFileHandler(p, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        sh = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        fh.setFormatter(fmt)
        sh.setFormatter(fmt)
        logging.basicConfig(level=logging.INFO, handlers=[fh, sh], force=True)
    except Exception:
        logging.basicConfig(level=logging.INFO)


async def run_monitor_once(duration_sec: float = 5.0) -> Path:
    agent = DevelopmentAgent()
    task = asyncio.create_task(agent.monitor())
    try:
        await asyncio.sleep(duration_sec)
    finally:
        agent.stop()
        with contextlib.suppress(Exception):
            task.cancel()
            await task
    rep = agent.build_report()
    return agent.write_report(rep)


async def main_async(mode: str, duration: float) -> None:
    _setup_logging()
    if mode == "monitor":
        agent = DevelopmentAgent()
        try:
            await agent.monitor()
        except KeyboardInterrupt:
            agent.stop()
            rep = agent.build_report()
            agent.write_report(rep)
    else:
        out = await run_monitor_once(duration)
        logger.info("One-shot report: %s", out)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DevelopmentAgent CLI")
    parser.add_argument("--mode", choices=["once", "monitor"], default="once")
    parser.add_argument("--duration", type=float, default=5.0, help="Duration for once-mode")
    args = parser.parse_args()
    asyncio.run(main_async(args.mode, args.duration))


if __name__ == "__main__":
    main()

