#!/usr/bin/env python3
"""
Integrated Agent Leader - Käyttää Hybrid Agenttia token-seulontaan
Tämä on Agent Leader joka on integroitu nykyiseen trading bot -järjestelmään.
"""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from agent_leader import AgentLeader, TaskPriority
from hybrid_agent import HybridAgent, HybridAgentConfig

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integrated_agent_leader.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)
TZ = ZoneInfo("Europe/Helsinki")

class IntegratedAgentLeader:
    """Integroitu Agent Leader joka hallinnoi Hybrid Agenttia"""
    
    def __init__(self):
        self.agent_leader = AgentLeader(telegram_enabled=True)
        self.hybrid_agent = None
        self.is_running = False
        
        # Konfiguraatio
        self.scan_interval = 60  # sekuntia
        self.report_interval = 300  # 5 minuuttia
        
    async def start(self) -> None:
        """Käynnistää integroidun Agent Leaderin"""
        logger.info("🚀 Starting Integrated Agent Leader...")
        
        try:
            # Luo Hybrid Agent
            config = HybridAgentConfig(
                scan_interval=self.scan_interval,
                max_tokens_per_cycle=100,
                min_score_threshold=0.8,
                telegram_enabled=True,
                report_interval=self.report_interval
            )
            
            self.hybrid_agent = HybridAgent(config)
            
            # Rekisteröi Hybrid Agent
            await self.agent_leader.register_agent(self.hybrid_agent)
            
            # Käynnistä Agent Leader
            self.is_running = True
            
            # Käynnistä taustatehtävät
            tasks = [
                asyncio.create_task(self._main_loop()),
                asyncio.create_task(self.agent_leader.start())
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Failed to start Integrated Agent Leader: {e}")
            raise
        finally:
            await self.stop()
    
    async def _main_loop(self) -> None:
        """Pääsilmukka joka luo tehtäviä Hybrid Agentille"""
        logger.info("🔄 Starting main task loop...")
        
        cycle_count = 0
        
        while self.is_running:
            try:
                cycle_count += 1
                logger.info(f"📋 Creating task for cycle {cycle_count}")
                
                # Luo token-seulonta tehtävä
                task_id = await self.agent_leader.create_task(
                    name="token_scan",
                    description=f"Token scan cycle {cycle_count}",
                    priority=TaskPriority.HIGH,
                    data={
                        "cycle": cycle_count,
                        "max_tokens": 100,
                        "timestamp": datetime.now(TZ).isoformat()
                    }
                )
                
                logger.info(f"✅ Created task {task_id}")
                
                # Odota seuraavaan sykliin
                await asyncio.sleep(self.scan_interval)
                
            except asyncio.CancelledError:
                logger.info("🛑 Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(30)  # Odota 30s ennen uudelleenyritystä
    
    async def stop(self) -> None:
        """Sammuttaa integroidun Agent Leaderin"""
        logger.info("🛑 Stopping Integrated Agent Leader...")
        self.is_running = False
        
        if self.hybrid_agent:
            await self.hybrid_agent.stop()
        
        logger.info("✅ Integrated Agent Leader stopped")

async def demo():
    """Demo integroidusta Agent Leaderista"""
    logger.info("🎭 Starting Integrated Agent Leader demo...")
    
    leader = IntegratedAgentLeader()
    
    try:
        # Käynnistä 2 minuutin demo
        await asyncio.wait_for(leader.start(), timeout=120)
    except asyncio.TimeoutError:
        logger.info("⏰ Demo timeout reached")
    finally:
        await leader.stop()

async def main():
    """Pääfunktio"""
    logger.info("🚀 Starting Integrated Agent Leader...")
    
    leader = IntegratedAgentLeader()
    
    try:
        await leader.start()
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await leader.stop()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(demo())
    else:
        asyncio.run(main())
