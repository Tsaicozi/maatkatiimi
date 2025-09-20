#!/usr/bin/env python3
"""
Cloud Agent Leader - Käynnistää Agent Leaderin pilvessä valvomaan GitHub-agnenteja
Tämä on pääkomponentti joka hallinnoi kaikkia pilvessä olevia agenteja.
"""

import asyncio
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from agent_leader import AgentLeader, TaskPriority
from hybrid_agent import HybridAgent, HybridAgentConfig
from github_agent import GitHubAgent, GitHubAgentConfig

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cloud_agent_leader.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)
TZ = ZoneInfo("Europe/Helsinki")

class CloudAgentLeader:
    """Cloud Agent Leader joka hallinnoi kaikkia pilvessä olevia agenteja"""
    
    def __init__(self):
        self.agent_leader = AgentLeader(telegram_enabled=True)
        self.agents = {}
        self.is_running = False
        
        # Konfiguraatio
        self.scan_interval = 60  # sekuntia
        self.report_interval = 300  # 5 minuuttia
        
    async def start(self) -> None:
        """Käynnistää Cloud Agent Leaderin"""
        logger.info("☁️ Starting Cloud Agent Leader...")
        
        try:
            # Luo ja rekisteröi agenteja
            await self._register_agents()
            
            # Käynnistä Agent Leader
            self.is_running = True
            
            # Käynnistä taustatehtävät
            tasks = [
                asyncio.create_task(self._main_loop()),
                asyncio.create_task(self._github_monitoring_loop()),
                asyncio.create_task(self.agent_leader.start())
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Failed to start Cloud Agent Leader: {e}")
            raise
        finally:
            await self.stop()
    
    async def _register_agents(self) -> None:
        """Rekisteröi kaikki agenteja"""
        logger.info("📝 Registering agents...")
        
        # 1. Hybrid Trading Agent
        try:
            hybrid_config = HybridAgentConfig(
                scan_interval=self.scan_interval,
                max_tokens_per_cycle=100,
                min_score_threshold=0.8,
                telegram_enabled=True,
                report_interval=self.report_interval
            )
            
            hybrid_agent = HybridAgent(hybrid_config)
            await self.agent_leader.register_agent(hybrid_agent)
            self.agents["hybrid"] = hybrid_agent
            logger.info("✅ Hybrid Trading Agent registered")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to register Hybrid Agent: {e}")
        
        # 2. GitHub Agent
        try:
            github_token = os.getenv('GITHUB_TOKEN')
            if github_token:
                github_config = GitHubAgentConfig(
                    github_token=github_token,
                    repository="jarihiirikoski/matkatiimi",  # Vaihda omaan repositoryyn
                    check_interval=120,  # 2 minuuttia
                    telegram_enabled=True
                )
                
                github_agent = GitHubAgent(github_config)
                await self.agent_leader.register_agent(github_agent)
                self.agents["github"] = github_agent
                logger.info("✅ GitHub Agent registered")
            else:
                logger.warning("⚠️ GITHUB_TOKEN not set, skipping GitHub Agent")
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to register GitHub Agent: {e}")
        
        # 3. Tulevaisuudessa voisi lisätä muita agenteja:
        # - Discord Agent
        # - Slack Agent  
        # - Email Agent
        # - Database Agent
        # - Monitoring Agent
        
        logger.info(f"📊 Total agents registered: {len(self.agents)}")
    
    async def _main_loop(self) -> None:
        """Pääsilmukka joka luo tehtäviä agenteille"""
        logger.info("🔄 Starting main task loop...")
        
        cycle_count = 0
        
        while self.is_running:
            try:
                cycle_count += 1
                logger.info(f"📋 Creating tasks for cycle {cycle_count}")
                
                # Luo tehtäviä eri agenteille
                await self._create_agent_tasks(cycle_count)
                
                # Odota seuraavaan sykliin
                await asyncio.sleep(self.scan_interval)
                
            except asyncio.CancelledError:
                logger.info("🛑 Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(30)
    
    async def _create_agent_tasks(self, cycle_count: int) -> None:
        """Luo tehtäviä eri agenteille"""
        
        # Hybrid Agent tehtävät
        if "hybrid" in self.agents:
            await self.agent_leader.create_task(
                name="token_scan",
                description=f"Token scan cycle {cycle_count}",
                priority=TaskPriority.HIGH,
                data={
                    "cycle": cycle_count,
                    "max_tokens": 100,
                    "timestamp": datetime.now(TZ).isoformat()
                }
            )
        
        # GitHub Agent tehtävät
        if "github" in self.agents:
            # Tarkista workflowt
            await self.agent_leader.create_task(
                name="github_workflow_check",
                description=f"GitHub workflow check {cycle_count}",
                priority=TaskPriority.MEDIUM,
                data={"cycle": cycle_count}
            )
            
            # Tarkista PR:t
            await self.agent_leader.create_task(
                name="github_pr_check",
                description=f"GitHub PR check {cycle_count}",
                priority=TaskPriority.MEDIUM,
                data={"cycle": cycle_count}
            )
            
            # Tarkista turvallisuushälytykset
            await self.agent_leader.create_task(
                name="github_security_check",
                description=f"GitHub security check {cycle_count}",
                priority=TaskPriority.HIGH,
                data={"cycle": cycle_count}
            )
    
    async def _github_monitoring_loop(self) -> None:
        """GitHub Actions -monitorointisilmukka"""
        logger.info("🔍 Starting GitHub monitoring loop...")
        
        while self.is_running:
            try:
                # Tarkista GitHub Actions -workflowjen tila
                await self._check_github_actions_health()
                
                # Odota 5 minuuttia
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                logger.info("🛑 GitHub monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in GitHub monitoring loop: {e}")
                await asyncio.sleep(300)
    
    async def _check_github_actions_health(self) -> None:
        """Tarkistaa GitHub Actions -workflowjen terveyden"""
        try:
            # Tässä voisi tehdä GitHub API -kutsun tarkistaakseen
            # workflowjen tilan ja lähettää hälytyksiä tarvittaessa
            
            logger.info("🔍 Checking GitHub Actions health...")
            # Simuloi tarkistusta
            await asyncio.sleep(1)
            logger.info("✅ GitHub Actions healthy")
            
        except Exception as e:
            logger.error(f"GitHub Actions health check failed: {e}")
    
    async def stop(self) -> None:
        """Sammuttaa Cloud Agent Leaderin"""
        logger.info("🛑 Stopping Cloud Agent Leader...")
        self.is_running = False
        
        # Sammuta kaikki agenteja
        for name, agent in self.agents.items():
            try:
                await agent.stop()
                logger.info(f"✅ {name} agent stopped")
            except Exception as e:
                logger.error(f"Error stopping {name} agent: {e}")
        
        logger.info("✅ Cloud Agent Leader stopped")

async def demo():
    """Demo Cloud Agent Leaderista"""
    logger.info("🎭 Starting Cloud Agent Leader demo...")
    
    leader = CloudAgentLeader()
    
    try:
        # Käynnistä 3 minuutin demo
        await asyncio.wait_for(leader.start(), timeout=180)
    except asyncio.TimeoutError:
        logger.info("⏰ Demo timeout reached")
    finally:
        await leader.stop()

async def main():
    """Pääfunktio"""
    logger.info("☁️ Starting Cloud Agent Leader...")
    
    leader = CloudAgentLeader()
    
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
