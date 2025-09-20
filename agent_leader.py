#!/usr/bin/env python3
"""
Agent Leader
- Valvoo agentteja
- Antaa heille tehtäviä (priorisoitu jono)
- Raportoi Telegramiin rehellisesti (ei mielistelyä)

Python 3.10+
Asynkroninen, käyttöönottaa RotatingFileHandlerin ja Europe/Helsinki -aikavyöhykkeen.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional, Protocol, Tuple, List
from zoneinfo import ZoneInfo


HELSINKI_TZ = ZoneInfo("Europe/Helsinki")


# --- Logging setup (non-invasive) ---
def _setup_logging_if_needed(log_path: str = "agent_leader.log", level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # kun muu järjestelmä on jo asettanut handlerit
    file_h = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    stream_h = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_h.setFormatter(fmt)
    stream_h.setFormatter(fmt)
    logging.basicConfig(level=level, handlers=[file_h, stream_h], force=True)


logger = logging.getLogger(__name__)
_setup_logging_if_needed()


# --- Data structures ---
@dataclass(slots=True)
class AgentTask:
    task_id: str
    description: str
    priority: int = 0  # pienempi numero = korkeampi prioriteetti
    payload: Dict[str, Any] = field(default_factory=dict)
    timeout_sec: Optional[float] = None
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(HELSINKI_TZ))


@dataclass(slots=True)
class TaskResult:
    task_id: str
    agent_name: str
    ok: bool
    error: Optional[str] = None
    details: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(HELSINKI_TZ))
    finished_at: Optional[datetime] = None
    duration_sec: Optional[float] = None


@dataclass(slots=True)
class AgentHealth:
    name: str
    ok: bool
    reason: Optional[str] = None
    running_tasks: int = 0
    last_heartbeat_ts: float = field(default_factory=time.time)


class ManagedAgent(Protocol):
    name: str
    max_concurrent: int

    async def run_task(self, task: AgentTask) -> TaskResult: ...

    async def health(self) -> AgentHealth: ...


class AgentLeader:
    """
    Yksinkertainen agenttien johtaja:
    - Ylläpitää priorisoitua tehtäväjonoa
    - Allokoi tehtäviä vapaille agenteille (max_concurrent huomioiden)
    - Kerää tulokset ja raportoi realistisesti
    - Siisti sammutus SIGINT/SIGTERM
    """

    def __init__(self, *, telegram=None, report_interval_sec: int = 60):
        self.telegram = telegram
        self.report_interval_sec = report_interval_sec

        # Jono: pienempi priority ensin; toissijaisesti FIFO aikaleimalla
        self._queue: "asyncio.PriorityQueue[Tuple[int, float, AgentTask]]" = asyncio.PriorityQueue()
        self._agents: List[ManagedAgent] = []
        self._running_per_agent: Dict[str, int] = {}
        self._inflight: Dict[str, asyncio.Task] = {}
        self._results: List[TaskResult] = []

        self._dispatcher_task: Optional[asyncio.Task] = None
        self._reporter_task: Optional[asyncio.Task] = None
        self._health_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._started = False

        # Statistiikka
        self._assigned_count = 0
        self._success_count = 0
        self._fail_count = 0

    # --- Public API ---
    def register_agent(self, agent: ManagedAgent) -> None:
        if any(a.name == agent.name for a in self._agents):
            raise ValueError(f"Agent name already registered: {agent.name}")
        self._agents.append(agent)
        self._running_per_agent[agent.name] = 0
        logger.info("Agent registered: %s (max_concurrent=%d)", agent.name, agent.max_concurrent)

    async def submit_task(self, description: str, *, payload: Optional[Dict[str, Any]] = None,
                          priority: int = 0, timeout_sec: Optional[float] = None,
                          deadline: Optional[datetime] = None, task_id: Optional[str] = None) -> str:
        tid = task_id or uuid.uuid4().hex
        task = AgentTask(
            task_id=tid,
            description=description,
            priority=priority,
            payload=dict(payload or {}),
            timeout_sec=timeout_sec,
            deadline=deadline,
        )
        await self._queue.put((priority, time.time(), task))
        return tid

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._stop_event.clear()
        self._dispatcher_task = asyncio.create_task(self._dispatcher_loop(), name="leader:dispatcher")
        self._reporter_task = asyncio.create_task(self._reporter_loop(), name="leader:reporter")
        self._health_task = asyncio.create_task(self._health_loop(), name="leader:health")
        self._install_signal_handlers()
        logger.info("AgentLeader started (%d agents)", len(self._agents))

    async def stop(self) -> None:
        self._stop_event.set()
        for task in (self._dispatcher_task, self._reporter_task, self._health_task):
            if task:
                task.cancel()
        with contextlib.suppress(Exception):
            await asyncio.gather(*(t for t in (self._dispatcher_task, self._reporter_task, self._health_task) if t), return_exceptions=True)
        # Odota käynnissä olevat tehtävät loppuun lyhyellä timeoutilla
        if self._inflight:
            with contextlib.suppress(Exception):
                await asyncio.wait(self._inflight.values(), timeout=5.0)
        logger.info("AgentLeader stopped. Success=%d Fail=%d Queue=%d", self._success_count, self._fail_count, self._queue.qsize())

    # --- Internal ---
    def _install_signal_handlers(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self._request_shutdown("SIGTERM")))
            loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(self._request_shutdown("SIGINT")))
        except Exception as e:
            logger.debug("Signal handlers not installed: %s", e)

    async def _request_shutdown(self, reason: str) -> None:
        logger.info("Shutdown requested: %s", reason)
        await self.stop()

    async def _dispatcher_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                try:
                    priority, ts, task = await asyncio.wait_for(self._queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue

                # Deadline check
                if task.deadline and datetime.now(HELSINKI_TZ) > task.deadline:
                    self._fail_count += 1
                    logger.warning("Task deadline missed: %s (%s)", task.task_id, task.description)
                    await self._notify_if_enabled(f"⚠️ Tehtävä myöhästyi: {task.description}\nID: {task.task_id}")
                    continue

                agent = self._select_agent()
                if agent is None:
                    # ei vapaata agenttia: palauta jonoa päähän lyhyen tauon jälkeen
                    await asyncio.sleep(0.1)
                    await self._queue.put((priority, ts, task))
                    continue

                self._assigned_count += 1
                self._running_per_agent[agent.name] += 1
                coro = self._run_task_with_agent(agent, task)
                t = asyncio.create_task(coro, name=f"run:{agent.name}:{task.task_id}")
                self._inflight[task.task_id] = t
                t.add_done_callback(lambda _t, a=agent: self._release_agent_slot(a))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Dispatcher loop error: %s", e)

    def _select_agent(self) -> Optional[ManagedAgent]:
        # Yksinkertainen valinta: valitse ensimmäinen jolla vapaa slotti
        for agent in self._agents:
            running = self._running_per_agent.get(agent.name, 0)
            if running < max(1, int(getattr(agent, "max_concurrent", 1) or 1)):
                return agent
        return None

    def _release_agent_slot(self, agent: ManagedAgent) -> None:
        self._running_per_agent[agent.name] = max(0, self._running_per_agent.get(agent.name, 1) - 1)

    async def _run_task_with_agent(self, agent: ManagedAgent, task: AgentTask) -> None:
        started = time.time()
        try:
            if task.timeout_sec and task.timeout_sec > 0:
                res = await asyncio.wait_for(agent.run_task(task), timeout=task.timeout_sec)
            else:
                res = await agent.run_task(task)
            res.finished_at = datetime.now(HELSINKI_TZ)
            res.duration_sec = time.time() - started
            self._results.append(res)
            self._success_count += 1 if res.ok else 0
            self._fail_count += 0 if res.ok else 1
            # Realistiset nopeat raportit epäonnistumisista
            if not res.ok:
                await self._notify_if_enabled(
                    f"🔴 Tehtävä epäonnistui agentilla {agent.name}: {task.description}\n"
                    f"Virhe: {res.error or 'tuntematon'}\nID: {task.task_id}"
                )
        except asyncio.TimeoutError:
            self._fail_count += 1
            await self._notify_if_enabled(f"🟠 Tehtävä aikakatkaistiin agentilla {agent.name}: {task.description}\nID: {task.task_id}")
        except Exception as e:
            self._fail_count += 1
            logger.warning("Task crashed on %s: %s", agent.name, e)
            await self._notify_if_enabled(f"🔴 Tehtävä kaatui agentilla {agent.name}: {task.description}\nVirhe: {e}")
        finally:
            self._inflight.pop(task.task_id, None)

    async def _health_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                for agent in self._agents:
                    with contextlib.suppress(Exception):
                        h = await agent.health()
                        if not h.ok:
                            await self._notify_if_enabled(f"⚠️ Agentin terveystila heikko: {h.name} — {h.reason or 'ei syytä'}")
                await asyncio.sleep(15.0)
        except asyncio.CancelledError:
            pass

    async def _reporter_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(self.report_interval_sec)
                await self._send_periodic_report()
        except asyncio.CancelledError:
            pass

    async def _send_periodic_report(self) -> None:
        # Realistinen, suora sävy
        total = self._assigned_count
        if total == 0 and self._queue.qsize() == 0:
            # Ei turhaa viestintää
            return
        success = self._success_count
        fail = self._fail_count
        inflight = len(self._inflight)
        qlen = self._queue.qsize()
        rate = (success / total * 100.0) if total else 0.0
        worst = self._worst_agent_by_fail_rate()
        lines = [
            "📊 Agent Leader - tilanne",
            f"🧩 Agenteja: {len(self._agents)} | Käynnissä: {inflight}",
            f"📥 Jonossa: {qlen}",
            f"✅ Onnistui: {success} | 🔴 Epäonnistui: {fail} | 🎯 Osuus: {rate:.1f}%",
        ]
        if worst:
            agent_name, fail_rate, counts = worst
            if counts[0] + counts[1] >= 5 and fail_rate >= 0.5:
                lines.append(f"⚠️ Heikoin agentti: {agent_name} ({fail_rate:.0%} epäonnistuu)")
        # Pidä sävy asiallisena
        await self._notify_if_enabled("\n".join(lines))

    def _worst_agent_by_fail_rate(self) -> Optional[Tuple[str, float, Tuple[int, int]]]:
        # Laske yksinkertaiset agenttikohtaiset tilastot
        counts: Dict[str, List[int]] = {}
        for r in self._results:
            arr = counts.setdefault(r.agent_name, [0, 0])
            if r.ok:
                arr[0] += 1
            else:
                arr[1] += 1
        worst: Tuple[str, float, Tuple[int, int]] | None = None
        for name, (ok_n, fail_n) in counts.items():
            total = ok_n + fail_n
            if total == 0:
                continue
            fail_rate = fail_n / total
            if worst is None or fail_rate > worst[1]:
                worst = (name, fail_rate, (ok_n, fail_n))
        return worst

    async def _notify_if_enabled(self, message: str) -> None:
        tg = self.telegram
        if tg is None:
            logger.info("[notify] %s", message.replace("\n", " ")[:180])
            return
        try:
            await tg.send_message(message)
        except Exception as e:
            logger.warning("Telegram send failed: %s", e)


# --- Demo agent ---
class EchoAgent:
    def __init__(self, name: str, *, max_concurrent: int = 1, fail_ratio: float = 0.0, min_run_ms: int = 50, max_run_ms: int = 250):
        self.name = name
        self.max_concurrent = int(max_concurrent)
        self._fail_ratio = float(max(0.0, min(1.0, fail_ratio)))
        self._min_ms = int(max(1, min_run_ms))
        self._max_ms = int(max(self._min_ms, max_run_ms))

    async def run_task(self, task: AgentTask) -> TaskResult:
        import random
        started = datetime.now(HELSINKI_TZ)
        # Simuloi työ
        sleep_ms = random.randint(self._min_ms, self._max_ms)
        await asyncio.sleep(sleep_ms / 1000.0)
        # Mahd. epäonnistuminen
        if random.random() < self._fail_ratio:
            return TaskResult(task_id=task.task_id, agent_name=self.name, ok=False, error="demo failure", started_at=started)
        # Palauta tulos
        return TaskResult(task_id=task.task_id, agent_name=self.name, ok=True, details=f"echo:{task.description}", metrics={"sleep_ms": sleep_ms}, started_at=started)

    async def health(self) -> AgentHealth:
        return AgentHealth(name=self.name, ok=True)


# --- CLI ---
async def _demo_main() -> None:
    # Telegram optional
    telegram = None
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        try:
            from telegram_bot_integration import TelegramBot
            telegram = TelegramBot(rate_limit_sec=1, max_backoff_sec=20, backoff_multiplier=2.0)
        except Exception:
            telegram = None

    leader = AgentLeader(telegram=telegram, report_interval_sec=30)
    # Rekisteröi pari demoagenttia
    leader.register_agent(EchoAgent("echo-fast", max_concurrent=2, fail_ratio=0.1))
    leader.register_agent(EchoAgent("echo-slow", max_concurrent=1, fail_ratio=0.2, min_run_ms=120, max_run_ms=400))

    await leader.start()

    # Syötä muutama tehtävä
    for i in range(15):
        await leader.submit_task(f"demo_task_{i}", priority=0 if i % 3 == 0 else 5, timeout_sec=3.0)

    # Aja tietty aika tai kunnes jono tyhjä ja ei inflightteja
    deadline = time.time() + 60
    try:
        while time.time() < deadline:
            if leader._queue.qsize() == 0 and not leader._inflight:
                break
            await asyncio.sleep(0.25)
    finally:
        await leader.stop()


def _main() -> None:
    try:
        asyncio.run(_demo_main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("KeyboardInterrupt")


if __name__ == "__main__":
    _main()

