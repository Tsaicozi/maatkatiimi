# Agent Leader - Keskitetty Agenttien Hallinta

Agent Leader on asyncio-pohjainen järjestelmä, joka hallinnoi ja valvoo useita agenteja, jakaa tehtäviä, valvoo terveydentilaa ja raportoi Telegramissa.

## 🚀 Ominaisuudet

- **Asyncio-pohjainen**: Tehokas asynkroninen suoritus
- **Agenttien hallinta**: Rekisteröi ja hallinnoi useita agenteja
- **Tehtävien jakaminen**: Priorisoi ja jakaa tehtäviä agenteille
- **Terveydenvalvonta**: Jatkuva agenttien terveydentilan seuranta
- **Telegram-raportointi**: Blunt, realistic summaries
- **Graceful shutdown**: Siisti sammutus SIGINT/SIGTERM signaaleilla
- **Docker-tuki**: Valmis pilveen asennusta varten
- **Monitoring**: Prometheus + Grafana integraatio

## 📋 Rakenne

### Pääkomponentit

- **AgentLeader**: Pääluokka joka hallinnoi kaikkia agenteja
- **ManagedAgent**: Protokolla agenttien toteuttamiseen
- **AgentTask**: Tehtävät joita agentit suorittavat
- **TaskResult**: Tehtävien tulokset
- **AgentHealth**: Agenttien terveydentila

### Tietorakenteet

```python
@dataclass
class AgentTask:
    id: str
    name: str
    description: str
    priority: TaskPriority
    data: Dict[str, Any]
    status: TaskStatus
    # ... muut kentät

@dataclass
class TaskResult:
    task_id: str
    success: bool
    data: Any
    error: Optional[str]
    execution_time: Optional[float]
    # ... muut kentät
```

## 🛠️ Asennus ja Käyttö

### Paikallinen kehitys

```bash
# Kloonaa repository
git clone <repository-url>
cd matkatiimi

# Asenna riippuvuudet
pip install -r requirements.txt

# Käynnistä demo
python3 agent_leader.py demo

# Käynnistä normaalisti
python3 agent_leader.py
```

### Docker-käyttö

```bash
# Rakenna Docker-kuva
docker build -f Dockerfile.agent_leader -t agent-leader .

# Käynnistä kontaineri
docker run -d --name agent-leader \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e TELEGRAM_CHAT_ID=your_chat_id \
  agent-leader

# Tarkista lokit
docker logs -f agent-leader
```

### Docker Compose (suositeltu)

```bash
# Käynnistä kaikki palvelut
docker-compose -f docker-compose.agent_leader.yml up -d

# Tarkista status
docker-compose -f docker-compose.agent_leader.yml ps

# Näytä lokit
docker-compose -f docker-compose.agent_leader.yml logs -f agent-leader

# Sammuta
docker-compose -f docker-compose.agent_leader.yml down
```

## 🚀 Pilveen Asennus

### Automaattinen deployment

```bash
# Tee deployment-script suoritettavaksi
chmod +x deploy_agent_leader.sh

# Asenna paikallisesti testausta varten
./deploy_agent_leader.sh deploy-local

# Asenna pilveen
./deploy_agent_leader.sh deploy
```

### Manuaalinen deployment

```bash
# 1. Rakenna ja pushaa Docker-kuva
docker build -f Dockerfile.agent_leader -t your-registry/agent-leader:latest .
docker push your-registry/agent-leader:latest

# 2. Luo environment-tiedosto
cp .env.example .env.agent_leader
# Muokkaa .env.agent_leader tiedostoa

# 3. Käynnistä palvelut
docker-compose -f docker-compose.agent_leader.yml up -d
```

## 📊 Monitoring

### Grafana Dashboard

- **URL**: http://localhost:3000
- **Käyttäjätunnus**: admin
- **Salasana**: admin123

### Prometheus Metrics

- **URL**: http://localhost:9090
- **Metrics endpoint**: http://localhost:8080/metrics

### Avainluvut

- `agent_leader_agents_total`: Agenttien kokonaismäärä
- `agent_leader_tasks_completed_total`: Suoritettujen tehtävien määrä
- `agent_leader_tasks_failed_total`: Epäonnistuneiden tehtävien määrä
- `agent_leader_task_execution_time_seconds`: Tehtävien suoritusaika

## 🔧 Konfiguraatio

### Environment-muuttujat

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Agent Leader
AGENT_LEADER_LOG_LEVEL=INFO
AGENT_LEADER_REPORT_INTERVAL=300
AGENT_LEADER_HEALTH_CHECK_INTERVAL=30

# Redis (valinnainen)
REDIS_URL=redis://redis:6379/0
```

### Konfiguraatiotiedosto

Muokkaa `agent_leader_config.yaml` tiedostoa tarpeidesi mukaan:

```yaml
general:
  timezone: "Europe/Helsinki"
  log_level: "INFO"

agents:
  max_agents: 50
  health_check_interval: 30

tasks:
  max_queue_size: 1000
  task_timeout: 300
```

## 🤖 Agenttien Kehittäminen

### Perusagentti

```python
class MyAgent:
    async def get_agent_id(self) -> str:
        return "my_agent"
    
    async def get_agent_name(self) -> str:
        return "My Custom Agent"
    
    async def can_handle_task(self, task: AgentTask) -> bool:
        return task.name.startswith("my_task")
    
    async def execute_task(self, task: AgentTask) -> TaskResult:
        # Toteuta tehtävän suoritus
        try:
            result = await self._do_work(task)
            return TaskResult(
                task_id=task.id,
                success=True,
                data=result
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e)
            )
    
    async def get_health(self) -> AgentHealth:
        return AgentHealth(
            agent_id=await self.get_agent_id(),
            status=AgentStatus.HEALTHY,
            last_heartbeat=datetime.now(TZ)
        )
    
    async def start(self) -> None:
        # Käynnistyslogiikka
        pass
    
    async def stop(self) -> None:
        # Sammutuslogiikka
        pass
```

### Agentin rekisteröinti

```python
# Luo Agent Leader
leader = AgentLeader()

# Luo agentti
my_agent = MyAgent()

# Rekisteröi agentti
await leader.register_agent(my_agent)

# Käynnistä Agent Leader
await leader.start()
```

## 📱 Telegram-raportointi

Agent Leader lähettää automaattisesti:

- **Agenttien rekisteröinti**: Uusien agenttien ilmoitukset
- **Tehtävien epäonnistuminen**: Välittömät hälytykset
- **Jaksolliset raportit**: 5 minuutin välein
- **Sammutusilmoitukset**: Graceful shutdown

### Viestien muoto

```
🚀 **Agent Leader Started**
Agents: 3
Time: 2025-09-20 08:13:35

📊 **Agent Leader Report**
⏱️ Uptime: 2.5h
🤖 Agents: 3
📋 Tasks: 150 (✅145 ❌5)
📈 Success rate: 96.7%
🔄 Pending tasks: 2
🏥 Agent status: healthy: 2, degraded: 1
```

## 🔍 Vianmääritys

### Yleisimmät ongelmat

1. **Agentti ei vastaa**
   ```bash
   # Tarkista lokit
   docker logs agent-leader
   
   # Tarkista agentin terveys
   curl http://localhost:8080/health
   ```

2. **Telegram-viestit eivät tule**
   ```bash
   # Tarkista environment-muuttujat
   docker exec agent-leader env | grep TELEGRAM
   
   # Testaa Telegram-yhteys
   python3 -c "from telegram_bot_integration import TelegramBotIntegration; print('OK')"
   ```

3. **Tehtävät eivät suoritu**
   ```bash
   # Tarkista agenttien status
   docker exec agent-leader python3 -c "
   import asyncio
   from agent_leader import AgentLeader
   async def check():
       leader = AgentLeader()
       print(f'Agents: {len(leader.agents)}')
       print(f'Queue: {len(leader.task_queue)}')
   asyncio.run(check())
   "
   ```

### Logien tarkistus

```bash
# Agent Leader lokit
docker logs -f agent-leader

# Kaikki palvelut
docker-compose -f docker-compose.agent_leader.yml logs -f

# Vain virheet
docker logs agent-leader 2>&1 | grep ERROR
```

## 🚀 Skalautuvuus

### Horizontal scaling

```yaml
# docker-compose.agent_leader.yml
services:
  agent-leader:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

### Load balancing

```yaml
# Nginx konfiguraatio
upstream agent_leader {
    server agent-leader-1:8080;
    server agent-leader-2:8080;
    server agent-leader-3:8080;
}
```

## 🔒 Turvallisuus

### Best practices

1. **Environment-muuttujat**: Älä koskaan commitoi salaisia tietoja
2. **Docker secrets**: Käytä Docker secrets tuotantoympäristössä
3. **Network isolation**: Käytä Docker networkeja
4. **Resource limits**: Aseta CPU/memory rajoitukset
5. **Health checks**: Käytä health checkejä

### Tuotantokonfiguraatio

```yaml
# agent_leader_config.yaml
security:
  enable_auth: true
  api_key: "${API_KEY}"
  allowed_ips: ["10.0.0.0/8"]
  rate_limit_requests: 100

cloud:
  auto_scaling:
    enabled: true
    min_instances: 2
    max_instances: 10
```

## 📚 API-dokumentaatio

### REST API (tulevaisuudessa)

```bash
# Agenttien lista
GET /api/agents

# Tehtävien lista
GET /api/tasks

# Agentin terveys
GET /api/agents/{agent_id}/health

# Uuden tehtävän luonti
POST /api/tasks
{
  "name": "My Task",
  "description": "Task description",
  "priority": "HIGH",
  "data": {}
}
```

## 🤝 Contributing

1. Fork repository
2. Luo feature branch
3. Commit muutokset
4. Push branch
5. Luo Pull Request

## 📄 Lisenssi

MIT License - katso LICENSE tiedosto

## 🆘 Tuki

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@example.com

---

**Agent Leader** - Tehokas ja luotettava agenttien hallinta pilvessä! 🚀
