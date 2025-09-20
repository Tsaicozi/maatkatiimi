#!/usr/bin/env python3
"""
GitHub Agent - Integroi GitHub Actions ja muut GitHub-agnentit Agent Leaderiin
Tämä agentti valvoo GitHub Actions -workflowja, pull requesteja ja muita GitHub-tapahtumia.
"""

import asyncio
import logging
import aiohttp
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Import Agent Leader interfaces
from agent_leader import ManagedAgent, AgentTask, TaskResult, AgentHealth, AgentStatus

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Europe/Helsinki")

@dataclass
class GitHubAgentConfig:
    """GitHub Agent konfiguraatio"""
    github_token: str
    repository: str  # owner/repo format
    webhook_secret: Optional[str] = None
    check_interval: int = 60  # sekuntia
    max_workflows: int = 10
    telegram_enabled: bool = True

class GitHubAgent:
    """GitHub Agent joka valvoo GitHub Actions -agenteja"""
    
    def __init__(self, config: GitHubAgentConfig):
        self.agent_id = "github_agent"
        self.agent_name = "GitHub Actions Monitor"
        self.config = config
        
        # State
        self.is_running = False
        self.start_time = None
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.error_count = 0
        self.last_error = None
        self.last_heartbeat = datetime.now(TZ)
        
        # GitHub API
        self.session = None
        self.headers = {
            "Authorization": f"token {config.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Agent-Leader/1.0"
        }
        
        # Statistics
        self.stats = {
            "workflows_checked": 0,
            "workflows_failed": 0,
            "pull_requests_checked": 0,
            "issues_checked": 0,
            "alerts_sent": 0
        }
        
        # Webhook events
        self.webhook_events = []
    
    async def get_agent_id(self) -> str:
        return self.agent_id
    
    async def get_agent_name(self) -> str:
        return self.agent_name
    
    async def can_handle_task(self, task: AgentTask) -> bool:
        """Tarkistaa voiko agentti käsitellä tehtävän"""
        return (
            task.name.startswith("github_") or
            task.name.startswith("workflow_") or
            task.name.startswith("pr_") or
            task.name.startswith("issue_")
        )
    
    async def execute_task(self, task: AgentTask) -> TaskResult:
        """Suorittaa tehtävän"""
        start_time = datetime.now(TZ)
        
        try:
            if task.name == "github_workflow_check":
                result = await self._check_workflows(task.data)
            elif task.name == "github_pr_check":
                result = await self._check_pull_requests(task.data)
            elif task.name == "github_issue_check":
                result = await self._check_issues(task.data)
            elif task.name == "github_security_check":
                result = await self._check_security_alerts(task.data)
            elif task.name == "github_webhook_process":
                result = await self._process_webhook(task.data)
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
            
            logger.error(f"GitHub task execution failed: {e}")
            
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _check_workflows(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Tarkistaa GitHub Actions -workflowjen tilan"""
        logger.info("🔄 Checking GitHub Actions workflows...")
        
        if not self.session:
            raise RuntimeError("HTTP session not initialized")
        
        # Hae workflow runs
        url = f"https://api.github.com/repos/{self.config.repository}/actions/runs"
        params = {
            "per_page": self.config.max_workflows,
            "status": "all"
        }
        
        async with self.session.get(url, headers=self.headers, params=params) as response:
            if response.status != 200:
                raise RuntimeError(f"GitHub API error: {response.status}")
            
            data = await response.json()
            workflow_runs = data.get("workflow_runs", [])
        
        # Analysoi workflowjen tila
        failed_workflows = []
        running_workflows = []
        
        for run in workflow_runs:
            if run["conclusion"] == "failure":
                failed_workflows.append({
                    "id": run["id"],
                    "name": run["name"],
                    "head_branch": run["head_branch"],
                    "created_at": run["created_at"],
                    "html_url": run["html_url"]
                })
            elif run["status"] == "in_progress":
                running_workflows.append({
                    "id": run["id"],
                    "name": run["name"],
                    "head_branch": run["head_branch"],
                    "started_at": run["run_started_at"]
                })
        
        self.stats["workflows_checked"] += len(workflow_runs)
        self.stats["workflows_failed"] += len(failed_workflows)
        
        return {
            "workflows_checked": len(workflow_runs),
            "failed_workflows": failed_workflows,
            "running_workflows": running_workflows,
            "timestamp": datetime.now(TZ).isoformat()
        }
    
    async def _check_pull_requests(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Tarkistaa pull requestien tilan"""
        logger.info("📋 Checking pull requests...")
        
        if not self.session:
            raise RuntimeError("HTTP session not initialized")
        
        # Hae pull requestit
        url = f"https://api.github.com/repos/{self.config.repository}/pulls"
        params = {"state": "all", "per_page": 20}
        
        async with self.session.get(url, headers=self.headers, params=params) as response:
            if response.status != 200:
                raise RuntimeError(f"GitHub API error: {response.status}")
            
            pull_requests = await response.json()
        
        # Analysoi PR:t
        open_prs = [pr for pr in pull_requests if pr["state"] == "open"]
        draft_prs = [pr for pr in open_prs if pr["draft"]]
        review_needed = [pr for pr in open_prs if not pr["draft"] and pr["review_comments"] == 0]
        
        self.stats["pull_requests_checked"] += len(pull_requests)
        
        return {
            "total_prs": len(pull_requests),
            "open_prs": len(open_prs),
            "draft_prs": len(draft_prs),
            "review_needed": len(review_needed),
            "timestamp": datetime.now(TZ).isoformat()
        }
    
    async def _check_issues(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Tarkistaa issuet"""
        logger.info("🐛 Checking issues...")
        
        if not self.session:
            raise RuntimeError("HTTP session not initialized")
        
        # Hae issuet
        url = f"https://api.github.com/repos/{self.config.repository}/issues"
        params = {"state": "open", "per_page": 20}
        
        async with self.session.get(url, headers=self.headers, params=params) as response:
            if response.status != 200:
                raise RuntimeError(f"GitHub API error: {response.status}")
            
            issues = await response.json()
        
        # Analysoi issuet
        high_priority = [issue for issue in issues if "high" in issue.get("labels", [])]
        bugs = [issue for issue in issues if "bug" in [label["name"] for label in issue.get("labels", [])]]
        
        self.stats["issues_checked"] += len(issues)
        
        return {
            "total_issues": len(issues),
            "high_priority": len(high_priority),
            "bugs": len(bugs),
            "timestamp": datetime.now(TZ).isoformat()
        }
    
    async def _check_security_alerts(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Tarkistaa turvallisuushälytykset"""
        logger.info("🔒 Checking security alerts...")
        
        if not self.session:
            raise RuntimeError("HTTP session not initialized")
        
        # Hae Dependabot alerts
        url = f"https://api.github.com/repos/{self.config.repository}/dependabot/alerts"
        params = {"state": "open"}
        
        async with self.session.get(url, headers=self.headers, params=params) as response:
            if response.status != 200:
                # Dependabot ei välttämättä ole käytössä
                logger.warning(f"Dependabot alerts not available: {response.status}")
                return {"alerts": [], "timestamp": datetime.now(TZ).isoformat()}
            
            alerts = await response.json()
        
        # Analysoi hälytykset
        high_severity = [alert for alert in alerts if alert.get("security_advisory", {}).get("severity") == "high"]
        critical_severity = [alert for alert in alerts if alert.get("security_advisory", {}).get("severity") == "critical"]
        
        return {
            "total_alerts": len(alerts),
            "high_severity": len(high_severity),
            "critical_severity": len(critical_severity),
            "alerts": alerts[:5],  # Top 5
            "timestamp": datetime.now(TZ).isoformat()
        }
    
    async def _process_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Käsittelee GitHub webhook-tapahtumia"""
        logger.info("🎣 Processing GitHub webhook...")
        
        event_type = data.get("event_type")
        payload = data.get("payload", {})
        
        # Käsittele eri webhook-tyypit
        if event_type == "workflow_run":
            return await self._handle_workflow_webhook(payload)
        elif event_type == "pull_request":
            return await self._handle_pr_webhook(payload)
        elif event_type == "issues":
            return await self._handle_issue_webhook(payload)
        else:
            return {"processed": False, "event_type": event_type}
    
    async def _handle_workflow_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Käsittelee workflow webhook-tapahtuman"""
        workflow_run = payload.get("workflow_run", {})
        
        if workflow_run.get("conclusion") == "failure":
            # Lähetä hälytys epäonnistuneesta workflowsta
            await self._send_workflow_alert(workflow_run)
            self.stats["alerts_sent"] += 1
        
        return {
            "workflow_id": workflow_run.get("id"),
            "conclusion": workflow_run.get("conclusion"),
            "alert_sent": workflow_run.get("conclusion") == "failure"
        }
    
    async def _handle_pr_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Käsittelee PR webhook-tapahtuman"""
        pr = payload.get("pull_request", {})
        action = payload.get("action")
        
        return {
            "pr_number": pr.get("number"),
            "action": action,
            "title": pr.get("title")
        }
    
    async def _handle_issue_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Käsittelee issue webhook-tapahtuman"""
        issue = payload.get("issue", {})
        action = payload.get("action")
        
        return {
            "issue_number": issue.get("number"),
            "action": action,
            "title": issue.get("title")
        }
    
    async def _send_workflow_alert(self, workflow_run: Dict[str, Any]) -> None:
        """Lähettää hälytyksen epäonnistuneesta workflowsta"""
        # Tämä voisi lähettää Telegram-viestin
        logger.warning(f"🚨 Workflow failed: {workflow_run.get('name')} - {workflow_run.get('html_url')}")
    
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
            memory_usage=0.0,
            cpu_usage=0.0,
            error_count=self.error_count,
            last_error=self.last_error
        )
    
    async def start(self) -> None:
        """Käynnistää agentin"""
        logger.info(f"🚀 Starting {self.agent_name}...")
        
        try:
            # Alusta HTTP-sessio
            self.session = aiohttp.ClientSession()
            
            # Testaa GitHub API -yhteys
            test_url = f"https://api.github.com/repos/{self.config.repository}"
            async with self.session.get(test_url, headers=self.headers) as response:
                if response.status != 200:
                    raise RuntimeError(f"GitHub API connection failed: {response.status}")
            
            self.is_running = True
            self.start_time = datetime.now(TZ)
            self.last_heartbeat = datetime.now(TZ)
            
            logger.info(f"✅ {self.agent_name} started successfully")
            logger.info(f"📊 Monitoring repository: {self.config.repository}")
            
        except Exception as e:
            logger.error(f"Failed to start {self.agent_name}: {e}")
            self.error_count += 1
            self.last_error = str(e)
            raise
    
    async def stop(self) -> None:
        """Sammuttaa agentin"""
        logger.info(f"🛑 Stopping {self.agent_name}...")
        
        try:
            if self.session:
                await self.session.close()
            
            self.is_running = False
            
            logger.info(f"✅ {self.agent_name} stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping {self.agent_name}: {e}")

# Demo function
async def demo_github_agent():
    """Demo GitHub Agentin toiminnasta"""
    logger.info("🎭 Starting GitHub Agent demo...")
    
    # Luo GitHub Agent (tarvitsee GitHub token)
    config = GitHubAgentConfig(
        github_token="your_github_token_here",
        repository="jarihiirikoski/matkatiimi",  # Vaihda omaan repositoryyn
        check_interval=30
    )
    
    agent = GitHubAgent(config)
    
    # Käynnistä agentti
    await agent.start()
    
    # Luo testitehtäviä
    from agent_leader import AgentTask, TaskPriority
    
    test_tasks = [
        AgentTask(
            id="github_1",
            name="github_workflow_check",
            description="Check GitHub Actions workflows",
            priority=TaskPriority.HIGH,
            data={}
        ),
        AgentTask(
            id="github_2",
            name="github_pr_check", 
            description="Check pull requests",
            priority=TaskPriority.MEDIUM,
            data={}
        )
    ]
    
    # Suorita tehtävät
    for task in test_tasks:
        if await agent.can_handle_task(task):
            result = await agent.execute_task(task)
            logger.info(f"Task {task.name}: {'✅' if result.success else '❌'}")
            if result.success:
                logger.info(f"Result: {result.data}")
    
    # Näytä terveys
    health = await agent.get_health()
    logger.info(f"Agent health: {health.status.value}")
    
    # Sammuta agentti
    await agent.stop()

if __name__ == "__main__":
    # Demo mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(demo_github_agent())
    else:
        print("Usage: python3 github_agent.py demo")
        print("Note: Set GITHUB_TOKEN environment variable")
