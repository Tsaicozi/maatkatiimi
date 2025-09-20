#!/usr/bin/env python3
"""
Hybrid Agent - Integroi automatic_hybrid_bot Agent Leader -järjestelmään
Tämä agentti toimii Agent Leaderin hallinnoimana ja suorittaa token-seulontaa.
"""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Import Agent Leader interfaces
from agent_leader import ManagedAgent, AgentTask, TaskResult, AgentHealth, AgentStatus

# Import existing bot components
try:
    from discovery_engine import DiscoveryEngine
    from sources.pumpportal_ws_newtokens import PumpPortalWebSocketSource
    from telegram_bot_integration import TelegramBot
except ImportError as e:
    print(f"⚠️ Import error: {e}")
    DiscoveryEngine = None
    PumpPortalWebSocketSource = None
    TelegramBot = None

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Europe/Helsinki")

@dataclass
class HybridAgentConfig:
    """Hybrid Agent konfiguraatio"""
    scan_interval: int = 60
    max_tokens_per_cycle: int = 100
    min_score_threshold: float = 0.8
    telegram_enabled: bool = True
    report_interval: int = 300

class HybridAgent:
    """Hybrid Agent joka integroi automatic_hybrid_bot Agent Leaderiin"""
    
    def __init__(self, config: Optional[HybridAgentConfig] = None):
        self.agent_id = "hybrid_trading_agent"
        self.agent_name = "Hybrid Trading Agent"
        self.config = config or HybridAgentConfig()
        
        # Bot components
        self.discovery_engine = None
        self.pumpportal_source = None
        self.telegram = None
        
        # State
        self.is_running = False
        self.start_time = None
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.error_count = 0
        self.last_error = None
        self.last_heartbeat = datetime.now(TZ)
        
        # Statistics
        self.stats = {
            "cycles_completed": 0,
            "tokens_analyzed": 0,
            "hot_tokens_found": 0,
            "telegram_messages_sent": 0
        }
    
    async def get_agent_id(self) -> str:
        return self.agent_id
    
    async def get_agent_name(self) -> str:
        return self.agent_name
    
    async def can_handle_task(self, task: AgentTask) -> bool:
        """Tarkistaa voiko agentti käsitellä tehtävän"""
        # Hybrid agentti voi käsitellä token-seulonta tehtäviä
        return (
            task.name.startswith("token_scan") or
            task.name.startswith("discovery_cycle") or
            task.name.startswith("hybrid_analysis")
        )
    
    async def execute_task(self, task: AgentTask) -> TaskResult:
        """Suorittaa tehtävän"""
        start_time = datetime.now(TZ)
        
        try:
            if task.name == "token_scan":
                result = await self._perform_token_scan(task.data)
            elif task.name == "discovery_cycle":
                result = await self._perform_discovery_cycle(task.data)
            elif task.name == "hybrid_analysis":
                result = await self._perform_hybrid_analysis(task.data)
            else:
                raise ValueError(f"Unknown task type: {task.name}")
            
            self.tasks_completed += 1
            execution_time = (datetime.now(TZ) - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                success=True,
                data=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            self.tasks_failed += 1
            self.error_count += 1
            self.last_error = str(e)
            execution_time = (datetime.now(TZ) - start_time).total_seconds()
            
            logger.error(f"Task execution failed: {e}")
            
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _perform_token_scan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Suorittaa token-seulontaa"""
        logger.info("🔍 Performing token scan...")
        
        if not self.discovery_engine:
            raise RuntimeError("Discovery engine not initialized")
        
        # Suorita analyysi
        results = await self.discovery_engine.run_analysis_cycle()
        
        self.stats["cycles_completed"] += 1
        self.stats["tokens_analyzed"] += results.get("tokens_analyzed", 0)
        self.stats["hot_tokens_found"] += len(results.get("hot_candidates", []))
        
        # Lähetä Telegram-viesti jos löytyi kuumia tokeneita
        if results.get("hot_candidates") and self.telegram:
            await self._send_telegram_report(results)
            self.stats["telegram_messages_sent"] += 1
        
        return {
            "scan_completed": True,
            "tokens_analyzed": results.get("tokens_analyzed", 0),
            "hot_tokens": len(results.get("hot_candidates", [])),
            "timestamp": datetime.now(TZ).isoformat()
        }
    
    async def _perform_discovery_cycle(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Suorittaa discovery-syklin"""
        logger.info("🔄 Running discovery cycle...")
        
        if not self.discovery_engine:
            raise RuntimeError("Discovery engine not initialized")
        
        # Käynnistä discovery-sykli
        results = await self.discovery_engine.run_analysis_cycle()
        
        return {
            "cycle_completed": True,
            "results": results,
            "timestamp": datetime.now(TZ).isoformat()
        }
    
    async def _perform_hybrid_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Suorittaa hybrid-analyysin"""
        logger.info("🧠 Performing hybrid analysis...")
        
        # Tässä voisi olla monimutkaisempaa analyysiä
        # Esim. AI-sentimentti, markkinatrendit, jne.
        
        return {
            "analysis_completed": True,
            "analysis_type": "hybrid",
            "timestamp": datetime.now(TZ).isoformat()
        }
    
    async def _send_telegram_report(self, results: Dict[str, Any]) -> None:
        """Lähettää Telegram-raportin"""
        if not self.telegram:
            return
        
        hot_candidates = results.get("hot_candidates", [])
        if not hot_candidates:
            return
        
        message = f"🔥 **Hot Tokens Found**\n\n"
        message += f"Found {len(hot_candidates)} hot tokens:\n\n"
        
        for i, token in enumerate(hot_candidates[:5], 1):  # Top 5
            message += f"{i}. **{token.get('symbol', 'Unknown')}**\n"
            message += f"   Score: {token.get('score', 0):.3f}\n"
            message += f"   Sources: {', '.join(token.get('sources', []))}\n\n"
        
        message += f"⏰ {datetime.now(TZ).strftime('%H:%M:%S')}"
        
        try:
            await self.telegram.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    async def get_health(self) -> AgentHealth:
        """Palauttaa agentin terveydentilan"""
        now = datetime.now(TZ)
        uptime = (now - self.start_time).total_seconds() if self.start_time else 0.0
        
        # Määritä status
        if not self.is_running:
            status = AgentStatus.OFFLINE
        elif self.error_count > 10:
            status = AgentStatus.UNHEALTHY
        elif self.error_count > 5:
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
            memory_usage=0.0,  # Could be implemented
            cpu_usage=0.0,     # Could be implemented
            error_count=self.error_count,
            last_error=self.last_error
        )
    
    async def start(self) -> None:
        """Käynnistää agentin"""
        logger.info(f"🚀 Starting {self.agent_name}...")
        
        try:
            # Alusta komponentit
            if DiscoveryEngine:
                self.discovery_engine = DiscoveryEngine()
                logger.info("✅ Discovery engine initialized")
            
            if PumpPortalWebSocketSource:
                self.pumpportal_source = PumpPortalWebSocketSource()
                logger.info("✅ PumpPortal source initialized")
            
            if self.config.telegram_enabled and TelegramBot:
                self.telegram = TelegramBot()
                logger.info("✅ Telegram integration initialized")
            
            self.is_running = True
            self.start_time = datetime.now(TZ)
            self.last_heartbeat = datetime.now(TZ)
            
            logger.info(f"✅ {self.agent_name} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start {self.agent_name}: {e}")
            self.error_count += 1
            self.last_error = str(e)
            raise
    
    async def stop(self) -> None:
        """Sammuttaa agentin"""
        logger.info(f"🛑 Stopping {self.agent_name}...")
        
        try:
            # Sammuta komponentit
            if self.pumpportal_source:
                await self.pumpportal_source.stop()
            
            self.is_running = False
            
            logger.info(f"✅ {self.agent_name} stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping {self.agent_name}: {e}")

# Demo function
async def demo_hybrid_agent():
    """Demo Hybrid Agentin toiminnasta"""
    logger.info("🎭 Starting Hybrid Agent demo...")
    
    # Luo Hybrid Agent
    config = HybridAgentConfig(
        scan_interval=30,
        max_tokens_per_cycle=10,
        min_score_threshold=0.7
    )
    
    agent = HybridAgent(config)
    
    # Käynnistä agentti
    await agent.start()
    
    # Luo testitehtäviä
    from agent_leader import AgentTask, TaskPriority
    
    test_tasks = [
        AgentTask(
            id="test_1",
            name="token_scan",
            description="Test token scan",
            priority=TaskPriority.HIGH,
            data={"max_tokens": 5}
        ),
        AgentTask(
            id="test_2", 
            name="discovery_cycle",
            description="Test discovery cycle",
            priority=TaskPriority.MEDIUM,
            data={}
        )
    ]
    
    # Suorita tehtävät
    for task in test_tasks:
        if await agent.can_handle_task(task):
            result = await agent.execute_task(task)
            logger.info(f"Task {task.name}: {'✅' if result.success else '❌'}")
    
    # Näytä terveys
    health = await agent.get_health()
    logger.info(f"Agent health: {health.status.value}")
    
    # Sammuta agentti
    await agent.stop()

if __name__ == "__main__":
    # Demo mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(demo_hybrid_agent())
    else:
        print("Usage: python3 hybrid_agent.py demo")
