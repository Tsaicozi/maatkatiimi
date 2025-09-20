#!/usr/bin/env python3
"""
Agent Leader - Keskitetty agenttien hallinta ja valvonta
Toteuttaa asyncio-pohjaisen AgentLeader-luokan, joka hallinnoi useita agenteja,
jakaa tehtäviä, valvoo terveydentilaa ja raportoi Telegramissa.
"""

import asyncio
import logging
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Protocol, Any, Callable
from zoneinfo import ZoneInfo
import json
import os
from pathlib import Path

# Telegram integration
try:
    from telegram_bot_integration import TelegramBot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ Telegram integration not available")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_leader.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Timezone
TZ = ZoneInfo("Europe/Helsinki")

class TaskPriority(Enum):
    """Tehtävien prioriteetit"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

class TaskStatus(Enum):
    """Tehtävien tilat"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentStatus(Enum):
    """Agenttien tilat"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"

@dataclass
class AgentTask:
    """Agenttien tehtävä"""
    id: str
    name: str
    description: str
    priority: TaskPriority
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(TZ))
    assigned_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@dataclass
class TaskResult:
    """Tehtävän tulos"""
    task_id: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(TZ))

@dataclass
class AgentHealth:
    """Agentin terveydentila"""
    agent_id: str
    status: AgentStatus
    last_heartbeat: datetime
    tasks_completed: int = 0
    tasks_failed: int = 0
    uptime: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None

class ManagedAgent(Protocol):
    """Protokolla agenttien toteuttamiseen"""
    
    async def get_agent_id(self) -> str:
        """Palauttaa agentin yksilöllisen tunnisteen"""
        ...
    
    async def get_agent_name(self) -> str:
        """Palauttaa agentin nimen"""
        ...
    
    async def can_handle_task(self, task: AgentTask) -> bool:
        """Tarkistaa voiko agentti käsitellä tehtävän"""
        ...
    
    async def execute_task(self, task: AgentTask) -> TaskResult:
        """Suorittaa tehtävän"""
        ...
    
    async def get_health(self) -> AgentHealth:
        """Palauttaa agentin terveydentilan"""
        ...
    
    async def start(self) -> None:
        """Käynnistää agentin"""
        ...
    
    async def stop(self) -> None:
        """Sammuttaa agentin"""
        ...

class EchoAgent:
    """Demo-agentti joka toistaa saamansa tehtävät"""
    
    def __init__(self, agent_id: str = "echo_agent"):
        self.agent_id = agent_id
        self.agent_name = "Echo Agent"
        self.is_running = False
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.start_time = None
        self.last_heartbeat = datetime.now(TZ)
        self.error_count = 0
        self.last_error = None
    
    async def get_agent_id(self) -> str:
        return self.agent_id
    
    async def get_agent_name(self) -> str:
        return self.agent_name
    
    async def can_handle_task(self, task: AgentTask) -> bool:
        # Echo agentti voi käsitellä kaikkia tehtäviä
        return True
    
    async def execute_task(self, task: AgentTask) -> TaskResult:
        start_time = datetime.now(TZ)
        try:
            # Simuloi tehtävän suorittamista
            await asyncio.sleep(0.1)
            
            # Jos tehtävä sisältää "fail", epäonnistu tahallisesti
            if "fail" in task.name.lower():
                raise Exception(f"Simulated failure for task: {task.name}")
            
            result_data = {
                "echo": f"Echoed: {task.description}",
                "task_id": task.id,
                "timestamp": datetime.now(TZ).isoformat()
            }
            
            self.tasks_completed += 1
            execution_time = (datetime.now(TZ) - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                success=True,
                data=result_data,
                execution_time=execution_time
            )
            
        except Exception as e:
            self.tasks_failed += 1
            self.error_count += 1
            self.last_error = str(e)
            execution_time = (datetime.now(TZ) - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def get_health(self) -> AgentHealth:
        now = datetime.now(TZ)
        uptime = (now - self.start_time).total_seconds() if self.start_time else 0.0
        
        # Määritä status
        if not self.is_running:
            status = AgentStatus.OFFLINE
        elif self.error_count > 5:
            status = AgentStatus.UNHEALTHY
        elif self.error_count > 2:
            status = AgentStatus.DEGRADED
        else:
            status = AgentStatus.HEALTHY
        
        return AgentHealth(
            agent_id=self.agent_id,
            status=status,
            last_heartbeat=self.last_heartbeat,
            tasks_completed=self.tasks_completed,
            tasks_failed=self.tasks_failed,
            uptime=uptime,
            memory_usage=0.0,  # Simulated
            cpu_usage=0.0,     # Simulated
            error_count=self.error_count,
            last_error=self.last_error
        )
    
    async def start(self) -> None:
        self.is_running = True
        self.start_time = datetime.now(TZ)
        logger.info(f"🚀 {self.agent_name} started")
    
    async def stop(self) -> None:
        self.is_running = False
        logger.info(f"🛑 {self.agent_name} stopped")

class AgentLeader:
    """Keskitetty agenttien hallinta ja valvonta"""
    
    def __init__(self, telegram_enabled: bool = True):
        self.agents: Dict[str, ManagedAgent] = {}
        self.tasks: Dict[str, AgentTask] = {}
        self.task_queue: List[AgentTask] = []
        self.is_running = False
        self.telegram_enabled = telegram_enabled and TELEGRAM_AVAILABLE
        
        # Telegram integration
        if self.telegram_enabled:
            try:
                self.telegram = TelegramBot()
                logger.info("✅ Telegram integration enabled")
            except Exception as e:
                logger.warning(f"⚠️ Telegram integration failed: {e}")
                self.telegram_enabled = False
        else:
            self.telegram = None
        
        # Statistics
        self.stats = {
            "tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "agents_registered": 0,
            "start_time": None
        }
        
        # Graceful shutdown
        self.shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Asettaa signaalinkäsittelijät graceful shutdown:lle"""
        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def register_agent(self, agent: ManagedAgent) -> None:
        """Rekisteröi uuden agentin"""
        agent_id = await agent.get_agent_id()
        agent_name = await agent.get_agent_name()
        
        if agent_id in self.agents:
            logger.warning(f"⚠️ Agent {agent_id} already registered")
            return
        
        self.agents[agent_id] = agent
        self.stats["agents_registered"] += 1
        
        logger.info(f"✅ Registered agent: {agent_name} ({agent_id})")
        
        if self.telegram_enabled:
            await self._send_telegram_message(
                f"🤖 **New Agent Registered**\n"
                f"Name: {agent_name}\n"
                f"ID: {agent_id}\n"
                f"Total agents: {len(self.agents)}"
            )
    
    async def create_task(self, name: str, description: str, priority: TaskPriority, 
                         data: Dict[str, Any] = None) -> str:
        """Luo uuden tehtävän"""
        task_id = f"task_{len(self.tasks) + 1}_{int(datetime.now().timestamp())}"
        
        task = AgentTask(
            id=task_id,
            name=name,
            description=description,
            priority=priority,
            data=data or {}
        )
        
        self.tasks[task_id] = task
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority.value)
        
        self.stats["tasks_created"] += 1
        
        logger.info(f"📋 Created task: {name} (Priority: {priority.name})")
        
        return task_id
    
    async def _assign_tasks(self) -> None:
        """Jakaa tehtäviä agenteille"""
        if not self.task_queue:
            return
        
        for task in self.task_queue[:]:  # Copy to avoid modification during iteration
            if task.status != TaskStatus.PENDING:
                continue
            
            # Etsi sopiva agentti
            best_agent = None
            for agent_id, agent in self.agents.items():
                if await agent.can_handle_task(task):
                    best_agent = agent
                    break
            
            if best_agent:
                task.assigned_agent = await best_agent.get_agent_id()
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now(TZ)
                
                # Suorita tehtävä asynkronisesti
                asyncio.create_task(self._execute_task(task, best_agent))
                
                self.task_queue.remove(task)
                logger.info(f"🎯 Assigned task {task.name} to {await best_agent.get_agent_id()}")
    
    async def _execute_task(self, task: AgentTask, agent: ManagedAgent) -> None:
        """Suorittaa tehtävän agentilla"""
        try:
            result = await agent.execute_task(task)
            
            if result.success:
                task.status = TaskStatus.COMPLETED
                task.result = result.data
                self.stats["tasks_completed"] += 1
                logger.info(f"✅ Task completed: {task.name}")
            else:
                task.status = TaskStatus.FAILED
                task.error = result.error
                self.stats["tasks_failed"] += 1
                logger.error(f"❌ Task failed: {task.name} - {result.error}")
                
                # Lähetä hälytys Telegramissa
                if self.telegram_enabled:
                    await self._send_telegram_message(
                        f"🚨 **Task Failed**\n"
                        f"Task: {task.name}\n"
                        f"Agent: {await agent.get_agent_id()}\n"
                        f"Error: {result.error}"
                    )
            
            task.completed_at = datetime.now(TZ)
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.stats["tasks_failed"] += 1
            logger.error(f"💥 Task execution crashed: {task.name} - {e}")
            
            if self.telegram_enabled:
                await self._send_telegram_message(
                    f"💥 **Task Execution Crashed**\n"
                    f"Task: {task.name}\n"
                    f"Agent: {await agent.get_agent_id()}\n"
                    f"Error: {str(e)}"
                )
    
    async def _monitor_agents(self) -> None:
        """Valvoo agenttien terveydentilaa"""
        unhealthy_agents = []
        
        for agent_id, agent in self.agents.items():
            try:
                health = await agent.get_health()
                
                if health.status == AgentStatus.UNHEALTHY:
                    unhealthy_agents.append(agent_id)
                    logger.warning(f"⚠️ Agent {agent_id} is unhealthy")
                elif health.status == AgentStatus.OFFLINE:
                    logger.error(f"🔴 Agent {agent_id} is offline")
                
            except Exception as e:
                logger.error(f"💥 Health check failed for agent {agent_id}: {e}")
                unhealthy_agents.append(agent_id)
        
        # Lähetä hälytys jos agentteja on ongelmia
        if unhealthy_agents and self.telegram_enabled:
            await self._send_telegram_message(
                f"⚠️ **Unhealthy Agents Detected**\n"
                f"Agents: {', '.join(unhealthy_agents)}\n"
                f"Total agents: {len(self.agents)}"
            )
    
    async def _send_telegram_message(self, message: str) -> None:
        """Lähettää Telegram-viestin"""
        if not self.telegram_enabled or not self.telegram:
            return
        
        try:
            await self.telegram.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    async def _periodic_report(self) -> None:
        """Lähettää jaksollisen raportin"""
        if not self.telegram_enabled:
            return
        
        uptime = (datetime.now(TZ) - self.stats["start_time"]).total_seconds()
        
        # Laske tilastot
        total_tasks = self.stats["tasks_completed"] + self.stats["tasks_failed"]
        success_rate = (self.stats["tasks_completed"] / total_tasks * 100) if total_tasks > 0 else 0
        
        # Laske agenttien tilat
        agent_statuses = {}
        for agent_id, agent in self.agents.items():
            try:
                health = await agent.get_health()
                agent_statuses[health.status.value] = agent_statuses.get(health.status.value, 0) + 1
            except:
                agent_statuses["unknown"] = agent_statuses.get("unknown", 0) + 1
        
        message = (
            f"📊 **Agent Leader Report**\n"
            f"⏱️ Uptime: {uptime/3600:.1f}h\n"
            f"🤖 Agents: {len(self.agents)}\n"
            f"📋 Tasks: {total_tasks} (✅{self.stats['tasks_completed']} ❌{self.stats['tasks_failed']})\n"
            f"📈 Success rate: {success_rate:.1f}%\n"
            f"🔄 Pending tasks: {len(self.task_queue)}"
        )
        
        if agent_statuses:
            status_text = ", ".join([f"{status}: {count}" for status, count in agent_statuses.items()])
            message += f"\n🏥 Agent status: {status_text}"
        
        await self._send_telegram_message(message)
    
    async def start(self) -> None:
        """Käynnistää Agent Leaderin"""
        logger.info("🚀 Starting Agent Leader...")
        self.is_running = True
        self.stats["start_time"] = datetime.now(TZ)
        
        # Käynnistä kaikki rekisteröidyt agentit
        for agent in self.agents.values():
            await agent.start()
        
        if self.telegram_enabled:
            await self._send_telegram_message(
                f"🚀 **Agent Leader Started**\n"
                f"Agents: {len(self.agents)}\n"
                f"Time: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        # Käynnistä taustatehtävät
        tasks = [
            asyncio.create_task(self._main_loop()),
            asyncio.create_task(self._monitoring_loop()),
            asyncio.create_task(self._reporting_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("🛑 Agent Leader main loop cancelled")
        finally:
            await self.stop()
    
    async def _main_loop(self) -> None:
        """Pääsilmukka"""
        while not self.shutdown_event.is_set():
            try:
                await self._assign_tasks()
                await asyncio.sleep(1)  # Tarkista tehtäviä sekunnin välein
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)
    
    async def _monitoring_loop(self) -> None:
        """Valvontasilmukka"""
        while not self.shutdown_event.is_set():
            try:
                await self._monitor_agents()
                await asyncio.sleep(30)  # Tarkista terveys 30s välein
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _reporting_loop(self) -> None:
        """Raportointisilmukka"""
        while not self.shutdown_event.is_set():
            try:
                await asyncio.sleep(300)  # 5 minuutin välein
                if not self.shutdown_event.is_set():
                    await self._periodic_report()
            except Exception as e:
                logger.error(f"Error in reporting loop: {e}")
                await asyncio.sleep(300)
    
    async def stop(self) -> None:
        """Sammuttaa Agent Leaderin"""
        logger.info("🛑 Stopping Agent Leader...")
        self.is_running = False
        
        # Sammuta kaikki agentit
        for agent in self.agents.values():
            try:
                await agent.stop()
            except Exception as e:
                logger.error(f"Error stopping agent: {e}")
        
        if self.telegram_enabled:
            uptime = (datetime.now(TZ) - self.stats["start_time"]).total_seconds()
            await self._send_telegram_message(
                f"🛑 **Agent Leader Stopped**\n"
                f"Uptime: {uptime/3600:.1f}h\n"
                f"Tasks completed: {self.stats['tasks_completed']}\n"
                f"Tasks failed: {self.stats['tasks_failed']}"
            )
        
        logger.info("✅ Agent Leader stopped gracefully")

async def demo():
    """Demo-funktio Agent Leaderin testaamiseen"""
    logger.info("🎭 Starting Agent Leader demo...")
    
    # Luo Agent Leader
    leader = AgentLeader(telegram_enabled=True)  # Enable Telegram for demo
    
    # Luo demo-agentti
    echo_agent = EchoAgent("demo_echo")
    await leader.register_agent(echo_agent)
    
    # Luo testitehtäviä
    await leader.create_task("Test Task 1", "Simple echo test", TaskPriority.HIGH)
    await leader.create_task("Test Task 2", "Another echo test", TaskPriority.MEDIUM)
    await leader.create_task("Fail Task", "This should fail", TaskPriority.LOW)
    
    # Käynnistä Agent Leader
    try:
        await asyncio.wait_for(leader.start(), timeout=30)  # 30s demo
    except asyncio.TimeoutError:
        logger.info("⏰ Demo timeout reached")
    finally:
        await leader.stop()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(demo())
    else:
        # Käynnistä Agent Leader normaalisti
        leader = AgentLeader()
        asyncio.run(leader.start())
