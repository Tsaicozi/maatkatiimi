#!/usr/bin/env python3
"""
PerformanceAgent
Analysoi suorituskykyä, optimoi algoritmeja, parantaa muistinkäyttöä ja ehdottaa nopeutusratkaisuja.

Vaatimukset (repo-specific):
- Python 3.10+, typing-annotaatiot
- Asyncio, ei blokkaavia kutsuja kuumissa poluissa
- Lokit: logging + RotatingFileHandler
- TZ: Europe/Helsinki (zoneinfo)
"""
from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import logging
import os
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo


HELSINKI_TZ = ZoneInfo("Europe/Helsinki")
logger = logging.getLogger(__name__)


@dataclass
class Sample:
    ts: float
    task_name: str
    loop_time: float
    cpu_time: float
    mem_rss_mb: float | None = None


@dataclass
class PerfReport:
    run_started_at: str
    duration_sec: float
    samples: List[Sample] = field(default_factory=list)
    hotspots: List[Dict[str, Any]] = field(default_factory=list)
    memory_top: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_started_at": self.run_started_at,
            "duration_sec": self.duration_sec,
            "samples": [dataclasses.asdict(s) for s in self.samples],
            "hotspots": self.hotspots,
            "memory_top": self.memory_top,
            "suggestions": self.suggestions,
        }


class AsyncSampler:
    """Kevyt asyncio-sampler, välttää blokkausta. Ei käytä raskaita profiilereita oletuksena."""

    def __init__(self, interval_sec: float = 0.05):
        self.interval_sec = interval_sec
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._samples: List[Sample] = []
        self._t0: float = 0.0

    @property
    def samples(self) -> List[Sample]:
        return self._samples

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._t0 = time.perf_counter()

        async def _runner():
            loop = asyncio.get_running_loop()
            getrusage = None
            with contextlib.suppress(Exception):
                import resource  # UNIX only

                def _cpu_time():
                    ru = resource.getrusage(resource.RUSAGE_SELF)
                    return float(ru.ru_utime + ru.ru_stime)

                nonlocal getrusage
                getrusage = _cpu_time

            while self._running:
                try:
                    now = time.perf_counter()
                    loop_time = loop.time()
                    cpu_time = getrusage() if getrusage else (now - self._t0)

                    rss_mb = None
                    with contextlib.suppress(Exception):
                        import psutil  # optional

                        p = psutil.Process(os.getpid())
                        rss_mb = float(p.memory_info().rss) / (1024 * 1024)

                    name = asyncio.current_task().get_name() if asyncio.current_task() else "sampler"
                    self._samples.append(Sample(ts=now, task_name=name, loop_time=loop_time, cpu_time=cpu_time, mem_rss_mb=rss_mb))
                    await asyncio.sleep(self.interval_sec)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.debug("AsyncSampler loop error: %s", e)
                    await asyncio.sleep(self.interval_sec)

        self._task = asyncio.create_task(_runner(), name="perf_sampler")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task
            self._task = None


class PerformanceAgent:
    """
    Suorituskykyagentti: kerää näytteitä, analysoi hotspotteja, ottaa tracemalloc-snapshotit,
    ja tuottaa suosituksia. Asynkroninen ja kevyt.
    """

    def __init__(self, *, sample_interval_sec: float = 0.02, snapshot_limit: int = 20):
        self.sampler = AsyncSampler(interval_sec=sample_interval_sec)
        self.snapshot_limit = snapshot_limit
        self._snapshots: List[tracemalloc.Snapshot] = []
        self._t_start: float = 0.0
        self._started_at_iso: str = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

    async def __aenter__(self):
        self._t_start = time.perf_counter()
        with contextlib.suppress(RuntimeError):
            tracemalloc.start(15)
        await self.sampler.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.sampler.stop()
        with contextlib.suppress(Exception):
            self._snapshots.append(tracemalloc.take_snapshot())
        return False

    def snapshot(self) -> None:
        with contextlib.suppress(Exception):
            if tracemalloc.is_tracing():
                if len(self._snapshots) >= self.snapshot_limit:
                    self._snapshots.pop(0)
                self._snapshots.append(tracemalloc.take_snapshot())

    def _analyze_hotspots(self) -> List[Dict[str, Any]]:
        hotspots: Dict[str, Dict[str, Any]] = {}
        prev: Optional[Sample] = None
        for s in self.sampler.samples:
            if prev:
                dt = max(1e-9, s.ts - prev.ts)
                dcpu = max(0.0, s.cpu_time - prev.cpu_time)
                util = min(1.0, dcpu / dt)  # crude CPU util ratio
                key = s.task_name
                h = hotspots.setdefault(key, {"task": key, "util_sum": 0.0, "dur_sum": 0.0, "samples": 0})
                h["util_sum"] += util
                h["dur_sum"] += dt
                h["samples"] += 1
            prev = s

        result = []
        for h in hotspots.values():
            avg_util = h["util_sum"] / max(1, h["samples"])
            result.append({
                "task": h["task"],
                "avg_cpu_util": round(avg_util, 3),
                "total_observed_sec": round(h["dur_sum"], 3),
            })
        result.sort(key=lambda x: x["avg_cpu_util"], reverse=True)
        return result

    def _analyze_memory(self) -> List[Dict[str, Any]]:
        if not self._snapshots or not tracemalloc.is_tracing():
            return []
        try:
            last = self._snapshots[-1]
            stats = last.statistics("lineno")
            top = []
            for st in stats[:15]:
                top.append({
                    "file": f"{st.traceback[0].filename}:{st.traceback[0].lineno}",
                    "size_kb": round(st.size / 1024.0, 1),
                    "count": st.count,
                    "trace": str(st.traceback.format())[:300],
                })
            return top
        except Exception:
            return []

    def _generate_suggestions(self, hotspots: List[Dict[str, Any]], memory_top: List[Dict[str, Any]]) -> List[str]:
        suggestions: List[str] = []
        # CPU suggestions
        if hotspots:
            top = hotspots[0]
            if top.get("avg_cpu_util", 0.0) > 0.6:
                suggestions.append("Korkea CPU-util hot path: käytä batching/async I/O; vältä synkronisia kutsuja.")
        # Memory suggestions
        big_allocs = [x for x in memory_top if x.get("size_kb", 0) > 256]
        if big_allocs:
            suggestions.append("Suuria allokaatioita havaittu: käytä generaatoreita/streamingia, rajaa listojen kokoa.")
        # Repo-specific heuristics
        suggestions.extend([
            "DiscoveryEngine: priorisoi pikafiltterit ennen RPC-kutsuja.",
            "Käytä asyncio.wait FIRST_COMPLETED -mallia burstien hallintaan (jo käytössä scorer-loopissa).",
            "RPC-client: lisää connection pool ja timeoutit; hyödynnä backoff.",
            "Pienennä queue maxsize tai lisää put_nowait + pudotus-strategia burstien aikana.",
        ])
        return suggestions

    def build_report(self) -> PerfReport:
        duration = time.perf_counter() - self._t_start
        hotspots = self._analyze_hotspots()
        memory_top = self._analyze_memory()
        suggestions = self._generate_suggestions(hotspots, memory_top)
        return PerfReport(
            run_started_at=self._started_at_iso,
            duration_sec=duration,
            samples=self.sampler.samples,
            hotspots=hotspots,
            memory_top=memory_top,
            suggestions=suggestions,
        )


async def profile_async_callable(fn: Callable[[], Any], *, duration_sec: float = 2.0) -> PerfReport:
    agent = PerformanceAgent()
    async with agent:
        deadline = asyncio.get_running_loop().time() + duration_sec
        while asyncio.get_running_loop().time() < deadline:
            agent.snapshot()
            await asyncio.sleep(0.05)
    return agent.build_report()


def _default_log_setup() -> None:
    try:
        from logging.handlers import RotatingFileHandler
        p = Path("performance_agent.log")
        fh = RotatingFileHandler(p, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        sh = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        fh.setFormatter(fmt)
        sh.setFormatter(fmt)
        logging.basicConfig(level=logging.INFO, handlers=[fh, sh], force=True)
    except Exception:
        logging.basicConfig(level=logging.INFO)


async def _demo_target() -> None:
    # Pieni CPU/alloc -demolooppi
    acc = 0
    for _ in range(20000):
        acc += 1
    await asyncio.sleep(0.01)


async def main_async(duration: float = 1.5, outfile: Optional[str] = None) -> str:
    _default_log_setup()
    logger.info("PerformanceAgent start")
    report = await profile_async_callable(_demo_target, duration_sec=duration)
    data = report.to_dict()
    if not outfile:
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        outfile = f"performance_report_{ts}.json"
    Path(outfile).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Report written: %s", outfile)
    return outfile


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PerformanceAgent CLI")
    parser.add_argument("--duration", type=float, default=1.5, help="Profiling duration seconds")
    parser.add_argument("--outfile", type=str, default=None, help="Output JSON report path")
    args = parser.parse_args()
    asyncio.run(main_async(duration=args.duration, outfile=args.outfile))


if __name__ == "__main__":
    main()

