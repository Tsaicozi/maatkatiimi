#!/usr/bin/env python3
"""
Cloud Agent Leader - Runs in Cursor's cloud environment
Monitors and manages other agents running in the same cloud
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
from collections import deque
import json
import subprocess
import psutil
import time
import os
from telegram_bot_integration import TelegramBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cloud_agent_leader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class AgentStatus:
    """Agent status information"""
    name: str
    pid: Optional[int]
    status: str  # running, stopped, error
    last_seen: datetime
    cpu_percent: float
    memory_mb: float
    log_file: str
    error_count: int = 0

@dataclass
class AgentHealth:
    """Agent health metrics"""
    name: str
    is_healthy: bool
    last_cycle: Optional[datetime]
    error_rate: float
    performance_score: float
    issues: List[str]

class CloudAgentLeader:
    """Cloud Agent Leader that monitors other agents in Cursor's cloud"""
    
    def __init__(self, telegram_enabled: bool = True):
        self.agents: Dict[str, AgentStatus] = {}
        self.health_metrics: Dict[str, AgentHealth] = {}
        self.running = False
        self.monitor_interval = 30  # seconds
        self.health_check_interval = 300  # 5 minutes
        self.telegram_enabled = telegram_enabled
        
        # Initialize Telegram bot
        if self.telegram_enabled:
            try:
                self.telegram_bot = TelegramBot()
                logger.info("📱 Telegram integration enabled")
            except Exception as e:
                logger.warning(f"⚠️ Telegram integration failed: {e}")
                self.telegram_enabled = False
                self.telegram_bot = None
        else:
            self.telegram_bot = None
        
        # Agent configurations
        self.agent_configs = {
            'automatic_hybrid_bot': {
                'script': 'automatic_hybrid_bot.py',
                'log_file': 'automatic_hybrid_bot.log',
                'stdout_log': None,
                'expected_cycle_time': 300,  # 5 minutes
                'max_errors': 5
            }
            # Note: hybrid_trading_bot is now integrated into automatic_hybrid_bot
            # No separate process needed
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    async def start(self):
        """Start the Cloud Agent Leader"""
        logger.info("🚀 Starting Cloud Agent Leader...")
        self.running = True
        
        # Send startup notification
        if self.telegram_enabled:
            await self._send_telegram_message("🚀 Cloud Agent Leader started in Cursor Cloud\n\nMonitoring agents:\n• automatic_hybrid_bot\n• hybrid_trading_bot")
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_agents()),
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._report_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("📋 Tasks cancelled, shutting down...")
        finally:
            await self._cleanup()
            
    async def _monitor_agents(self):
        """Monitor running agents"""
        logger.info("👀 Starting agent monitoring...")
        
        while self.running:
            try:
                await self._scan_running_agents()
                await self._update_agent_status()
                await asyncio.sleep(self.monitor_interval)
            except Exception as e:
                logger.error(f"❌ Error in agent monitoring: {e}")
                await asyncio.sleep(5)
                
    async def _scan_running_agents(self):
        """Scan for running agent processes"""
        for agent_name, config in self.agent_configs.items():
            try:
                # Find process by script name
                pid = self._find_agent_process(config['script'])
                
                if pid:
                    # Get process info
                    process = psutil.Process(pid)
                    cpu_percent = process.cpu_percent()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    
                    # Update or create agent status
                    if agent_name in self.agents:
                        self.agents[agent_name].pid = pid
                        self.agents[agent_name].status = 'running'
                        self.agents[agent_name].last_seen = datetime.now(timezone.utc)
                        self.agents[agent_name].cpu_percent = cpu_percent
                        self.agents[agent_name].memory_mb = memory_mb
                    else:
                        self.agents[agent_name] = AgentStatus(
                            name=agent_name,
                            pid=pid,
                            status='running',
                            last_seen=datetime.now(timezone.utc),
                            cpu_percent=cpu_percent,
                            memory_mb=memory_mb,
                            log_file=config['log_file']
                        )
                        logger.info(f"✅ Found running agent: {agent_name} (PID: {pid})")
                        # Send Telegram notification for new agent
                        if self.telegram_enabled:
                            await self._send_telegram_message(f"✅ Agent {agent_name} is now running (PID: {pid})")
                else:
                    # Agent not running
                    if agent_name in self.agents:
                        if self.agents[agent_name].status == 'running':
                            logger.warning(f"⚠️ Agent {agent_name} stopped running")
                            # Send Telegram notification for stopped agent
                            if self.telegram_enabled:
                                await self._send_telegram_message(f"⚠️ Agent {agent_name} has stopped running")
                        self.agents[agent_name].status = 'stopped'
                        self.agents[agent_name].pid = None
                    else:
                        self.agents[agent_name] = AgentStatus(
                            name=agent_name,
                            pid=None,
                            status='stopped',
                            last_seen=datetime.now(timezone.utc),
                            cpu_percent=0.0,
                            memory_mb=0.0,
                            log_file=config['log_file']
                        )
                        
            except Exception as e:
                logger.error(f"❌ Error scanning agent {agent_name}: {e}")
                
    def _find_agent_process(self, script_name: str) -> Optional[int]:
        """Find process ID for agent script"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and any(script_name in arg for arg in cmdline):
                        return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"❌ Error finding process for {script_name}: {e}")
        return None
        
    async def _update_agent_status(self):
        """Update agent status based on log files and performance"""
        for agent_name, agent in self.agents.items():
            try:
                config = self.agent_configs[agent_name]
                
                # Check log file for errors (try both main log and stdout log)
                error_count = self._count_log_errors(agent.log_file)
                if config.get('stdout_log') and Path(config['stdout_log']).exists():
                    stdout_errors = self._count_log_errors(config['stdout_log'])
                    error_count = max(error_count, stdout_errors)
                agent.error_count = error_count
                
                # Check if agent is healthy
                if agent.status == 'running':
                    if error_count > config['max_errors']:
                        agent.status = 'error'
                        logger.error(f"❌ Agent {agent_name} has too many errors: {error_count}")
                        # Send Telegram alert for critical errors
                        if self.telegram_enabled:
                            await self._send_telegram_message(f"🚨 CRITICAL: Agent {agent_name} has {error_count} errors!")
                    elif agent.cpu_percent > 80:
                        agent.status = 'error'
                        logger.error(f"❌ Agent {agent_name} using too much CPU: {agent.cpu_percent}%")
                        # Send Telegram alert for high CPU
                        if self.telegram_enabled:
                            await self._send_telegram_message(f"🔥 HIGH CPU: Agent {agent_name} using {agent.cpu_percent}% CPU")
                    elif agent.memory_mb > 1000:  # 1GB
                        agent.status = 'error'
                        logger.error(f"❌ Agent {agent_name} using too much memory: {agent.memory_mb}MB")
                        # Send Telegram alert for high memory
                        if self.telegram_enabled:
                            await self._send_telegram_message(f"💾 HIGH MEMORY: Agent {agent_name} using {agent.memory_mb:.1f}MB")
                        
            except Exception as e:
                logger.error(f"❌ Error updating status for {agent_name}: {e}")
                
    def _count_log_errors(self, log_file: str) -> int:
        """Count recent errors in log file (ignore stale history)."""
        try:
            if not Path(log_file).exists():
                return 0

            # Check if log file is recent (within last 2 hours)
            log_mtime = Path(log_file).stat().st_mtime
            log_age_hours = (time.time() - log_mtime) / 3600
            
            # If log file is older than 2 hours, consider it stale
            if log_age_hours > 2:
                logger.warning(f"⚠️ Log file {log_file} is stale ({log_age_hours:.1f} hours old)")
                return 0

            cutoff = datetime.now() - timedelta(hours=6)
            error_count = 0

            with open(log_file, 'r') as handle:
                recent_lines = deque(handle, maxlen=5000)

            noise_markers = (
                "Helius WS-virhe",
                "PumpPortal /recent endpoint",
            )

            for line in recent_lines:
                if 'ERROR' not in line and 'CRITICAL' not in line:
                    continue
                if any(marker in line for marker in noise_markers):
                    continue

                ts = self._parse_log_timestamp(line)
                if ts is None or ts >= cutoff:
                    error_count += 1

            return error_count
        except Exception as e:
            logger.error(f"❌ Error reading log file {log_file}: {e}")
            return 0

    @staticmethod
    def _parse_log_timestamp(line: str) -> Optional[datetime]:
        """Best-effort log timestamp parser."""
        try:
            return datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S,%f")
        except ValueError:
            return None
            
    async def _health_check_loop(self):
        """Periodic health checks"""
        logger.info("🏥 Starting health check loop...")
        
        while self.running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"❌ Error in health check: {e}")
                await asyncio.sleep(60)
                
    async def _perform_health_checks(self):
        """Perform comprehensive health checks"""
        for agent_name, agent in self.agents.items():
            try:
                config = self.agent_configs[agent_name]
                issues = []
                
                # Check if agent is running
                if agent.status != 'running':
                    issues.append(f"Agent not running (status: {agent.status})")
                    
                # Check error rate
                if agent.error_count > config['max_errors']:
                    issues.append(f"Too many errors: {agent.error_count}")
                    
                # Check performance
                if agent.cpu_percent > 80:
                    issues.append(f"High CPU usage: {agent.cpu_percent}%")
                    
                if agent.memory_mb > 1000:
                    issues.append(f"High memory usage: {agent.memory_mb}MB")
                    
                # Check last seen time
                time_since_last_seen = (datetime.now(timezone.utc) - agent.last_seen).total_seconds()
                if time_since_last_seen > config['expected_cycle_time'] * 2:
                    issues.append(f"Not seen for {time_since_last_seen:.0f} seconds")
                    
                # Calculate health score
                is_healthy = len(issues) == 0
                error_rate = agent.error_count / max(1, time_since_last_seen / 60)  # errors per minute
                performance_score = max(0, 100 - agent.cpu_percent - (agent.memory_mb / 10))
                
                # Update health metrics
                self.health_metrics[agent_name] = AgentHealth(
                    name=agent_name,
                    is_healthy=is_healthy,
                    last_cycle=agent.last_seen,
                    error_rate=error_rate,
                    performance_score=performance_score,
                    issues=issues
                )
                
                if not is_healthy:
                    logger.warning(f"⚠️ Agent {agent_name} health issues: {', '.join(issues)}")
                    # Send Telegram notification for health issues
                    if self.telegram_enabled:
                        issues_text = '\n'.join([f"• {issue}" for issue in issues])
                        await self._send_telegram_message(f"⚠️ Health Alert: {agent_name}\n\nIssues:\n{issues_text}")
                    
            except Exception as e:
                logger.error(f"❌ Error in health check for {agent_name}: {e}")
                
    async def _report_loop(self):
        """Periodic reporting"""
        logger.info("📊 Starting report loop...")
        
        while self.running:
            try:
                await self._generate_report()
                await asyncio.sleep(600)  # 10 minutes
            except Exception as e:
                logger.error(f"❌ Error in report generation: {e}")
                await asyncio.sleep(60)
                
    async def _generate_report(self):
        """Generate status report"""
        try:
            report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'environment': 'Cursor Cloud',
                'agents': {},
                'summary': {
                    'total_agents': len(self.agents),
                    'running_agents': sum(1 for a in self.agents.values() if a.status == 'running'),
                    'healthy_agents': sum(1 for h in self.health_metrics.values() if h.is_healthy),
                    'total_errors': sum(a.error_count for a in self.agents.values())
                }
            }
            
            # Add agent details
            for agent_name, agent in self.agents.items():
                health = self.health_metrics.get(agent_name)
                report['agents'][agent_name] = {
                    'status': agent.status,
                    'pid': agent.pid,
                    'cpu_percent': agent.cpu_percent,
                    'memory_mb': agent.memory_mb,
                    'error_count': agent.error_count,
                    'last_seen': agent.last_seen.isoformat(),
                    'is_healthy': health.is_healthy if health else False,
                    'performance_score': health.performance_score if health else 0,
                    'issues': health.issues if health else []
                }
                
            # Log report
            logger.info("📊 Cloud Agent Leader Report:")
            logger.info(f"   Total agents: {report['summary']['total_agents']}")
            logger.info(f"   Running: {report['summary']['running_agents']}")
            logger.info(f"   Healthy: {report['summary']['healthy_agents']}")
            logger.info(f"   Total errors: {report['summary']['total_errors']}")
            
            # Save report to file
            report_file = f"cloud_agent_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"📄 Report saved to {report_file}")
            
            # Send Telegram report
            if self.telegram_enabled:
                await self._send_telegram_report(report)
            
        except Exception as e:
            logger.error(f"❌ Error generating report: {e}")
            
    async def _cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up resources...")
        
        # Send shutdown notification
        if self.telegram_enabled:
            await self._send_telegram_message("🛑 Cloud Agent Leader shutting down gracefully...")
        
        self.running = False
        
    def get_status(self) -> Dict:
        """Get current status"""
        return {
            'running': self.running,
            'agents': {name: {
                'status': agent.status,
                'pid': agent.pid,
                'cpu_percent': agent.cpu_percent,
                'memory_mb': agent.memory_mb,
                'error_count': agent.error_count,
                'last_seen': agent.last_seen.isoformat()
            } for name, agent in self.agents.items()},
            'health_metrics': {name: {
                'is_healthy': health.is_healthy,
                'performance_score': health.performance_score,
                'error_rate': health.error_rate,
                'issues': health.issues
            } for name, health in self.health_metrics.items()}
        }
        
    async def _send_telegram_message(self, message: str):
        """Send message to Telegram"""
        if not self.telegram_enabled or not self.telegram_bot:
            return
            
        try:
            await self.telegram_bot.send_message(message)
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
            
    async def _send_telegram_report(self, report: Dict):
        """Send formatted report to Telegram"""
        if not self.telegram_enabled or not self.telegram_bot:
            return
            
        try:
            # Format report for Telegram
            summary = report['summary']
            timestamp = datetime.fromisoformat(report['timestamp'].replace('Z', '+00:00'))
            
            message = f"📊 Cloud Agent Leader Report\n"
            message += f"🕐 {timestamp.strftime('%H:%M:%S UTC')}\n\n"
            message += f"📈 Summary:\n"
            message += f"• Total agents: {summary['total_agents']}\n"
            message += f"• Running: {summary['running_agents']}\n"
            message += f"• Healthy: {summary['healthy_agents']}\n"
            message += f"• Total errors: {summary['total_errors']}\n\n"
            
            # Add agent details
            message += "🤖 Agent Status:\n"
            for agent_name, agent_data in report['agents'].items():
                status_emoji = "✅" if agent_data['is_healthy'] else "❌"
                message += f"{status_emoji} {agent_name}: {agent_data['status']}\n"
                if agent_data['pid']:
                    message += f"   PID: {agent_data['pid']}, CPU: {agent_data['cpu_percent']:.1f}%, Memory: {agent_data['memory_mb']:.1f}MB\n"
                if agent_data['issues']:
                    message += f"   Issues: {', '.join(agent_data['issues'])}\n"
                message += "\n"
                
            await self.telegram_bot.send_message(message)
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram report: {e}")

async def main():
    """Main entry point"""
    # Check if Telegram should be disabled
    telegram_enabled = os.getenv('TELEGRAM_DISABLED', '').lower() != 'true'
    leader = CloudAgentLeader(telegram_enabled=telegram_enabled)
    
    try:
        await leader.start()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        logger.info("👋 Cloud Agent Leader stopped")

async def demo():
    """Demo function to test Cloud Agent Leader with Telegram"""
    print("🧪 Cloud Agent Leader Demo with Telegram Integration")
    print("=" * 50)
    
    # Create leader with Telegram enabled
    leader = CloudAgentLeader(telegram_enabled=True)
    
    try:
        # Send test message
        print("📱 Sending test Telegram message...")
        await leader._send_telegram_message("🧪 Cloud Agent Leader Demo Test\n\nThis is a test message from the Cloud Agent Leader running in Cursor Cloud!")
        
        # Simulate agent status
        print("🤖 Simulating agent status...")
        leader.agents['test_agent'] = AgentStatus(
            name='test_agent',
            pid=12345,
            status='running',
            last_seen=datetime.now(timezone.utc),
            cpu_percent=25.5,
            memory_mb=512.3,
            log_file='test.log',
            error_count=0
        )
        
        # Generate test report
        print("📊 Generating test report...")
        test_report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'environment': 'Cursor Cloud Demo',
            'agents': {
                'test_agent': {
                    'status': 'running',
                    'pid': 12345,
                    'cpu_percent': 25.5,
                    'memory_mb': 512.3,
                    'error_count': 0,
                    'last_seen': datetime.now(timezone.utc).isoformat(),
                    'is_healthy': True,
                    'performance_score': 85.0,
                    'issues': []
                }
            },
            'summary': {
                'total_agents': 1,
                'running_agents': 1,
                'healthy_agents': 1,
                'total_errors': 0
            }
        }
        
        await leader._send_telegram_report(test_report)
        
        print("✅ Demo completed successfully!")
        print("📱 Check your Telegram for test messages")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        print("👋 Demo finished")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'demo':
        asyncio.run(demo())
    else:
        asyncio.run(main())
