# Agent Leader - Pilveen Asennusopas

Tämä opas kuvaa kuinka Agent Leader -järjestelmä asennetaan pilveen toimimaan itsenäisesti muiden agenttien kanssa.

## 🎯 Mitä on luotu

### ✅ Agent Leader Core
- **`agent_leader.py`** - Pääkomponentti, asyncio-pohjainen agenttien hallinta
- **`hybrid_agent.py`** - Integroitu agentti joka käyttää nykyistä trading bot -järjestelmää
- **`integrated_agent_leader.py`** - Yhdistetty järjestelmä joka hallinnoi Hybrid Agenttia

### ✅ Docker & Cloud Ready
- **`Dockerfile.agent_leader`** - Optimoitu kontaineri
- **`docker-compose.agent_leader.yml`** - Perus Agent Leader setup
- **`docker-compose.integrated.yml`** - Integroitu järjestelmä
- **`deploy_agent_leader.sh`** - Perus deployment
- **`deploy_integrated.sh`** - Integroitu deployment

### ✅ Konfiguraatio & Monitoring
- **`.env.agent_leader`** - Environment-muuttujat (Telegram konfiguroitu)
- **`agent_leader_config.yaml`** - Kattava konfiguraatio
- **`monitoring/`** - Prometheus & Grafana configs
- **`quick_start_agent_leader.sh`** - Nopea käynnistys

## 🚀 Asennusvaihtoehdot

### 1. Paikallinen testaus

```bash
# Demo-moodi (30s testi)
./quick_start_agent_leader.sh
# Valitse option 1

# Tai suoraan
python3 agent_leader.py demo
```

### 2. Integroitu järjestelmä (suositeltu)

```bash
# Demo integroidusta järjestelmästä
python3 integrated_agent_leader.py demo

# Käynnistä integroitu järjestelmä
python3 integrated_agent_leader.py
```

### 3. Docker deployment

```bash
# Perus Agent Leader
./deploy_agent_leader.sh deploy-local

# Integroitu järjestelmä
./deploy_integrated.sh deploy
```

## 📱 Telegram-konfiguraatio

Telegram on jo konfiguroitu ja toimii:

- **Bot Token**: `8468877865:AAFrap3-U3fv2vacVI_yhXm6-hCHbB7SX54`
- **Chat ID**: `7939379291`
- **Testattu**: ✅ Viestit lähetetään onnistuneesti

### Telegram-viestien tyypit:

1. **Agenttien rekisteröinti**
   ```
   🤖 **New Agent Registered**
   Name: Hybrid Trading Agent
   ID: hybrid_trading_agent
   Total agents: 1
   ```

2. **Tehtävien epäonnistuminen**
   ```
   🚨 **Task Failed**
   Task: token_scan
   Agent: hybrid_trading_agent
   Error: Discovery engine not initialized
   ```

3. **Jaksolliset raportit** (5min välein)
   ```
   📊 **Agent Leader Report**
   ⏱️ Uptime: 2.5h
   🤖 Agents: 1
   📋 Tasks: 150 (✅145 ❌5)
   📈 Success rate: 96.7%
   🔄 Pending tasks: 2
   ```

4. **Sammutusilmoitukset**
   ```
   🛑 **Agent Leader Stopped**
   Uptime: 2.5h
   Tasks completed: 145
   Tasks failed: 5
   ```

## 🐳 Docker-käyttöönotto

### Perus Agent Leader

```bash
# 1. Rakenna kuva
docker build -f Dockerfile.agent_leader -t agent-leader .

# 2. Käynnistä kontaineri
docker run -d --name agent-leader \
  --env-file .env.agent_leader \
  -v $(pwd)/logs:/app/logs \
  agent-leader

# 3. Tarkista lokit
docker logs -f agent-leader
```

### Integroitu järjestelmä (Docker Compose)

```bash
# 1. Käynnistä kaikki palvelut
docker-compose -f docker-compose.integrated.yml up -d

# 2. Tarkista status
docker-compose -f docker-compose.integrated.yml ps

# 3. Näytä lokit
docker-compose -f docker-compose.integrated.yml logs -f integrated-agent-leader

# 4. Sammuta
docker-compose -f docker-compose.integrated.yml down
```

## 📊 Monitoring

### Grafana Dashboard
- **URL**: http://localhost:3000
- **Käyttäjätunnus**: admin
- **Salasana**: admin123
- **Dashboard**: Agent Leader Dashboard

### Prometheus Metrics
- **URL**: http://localhost:9090
- **Metrics endpoint**: http://localhost:8080/metrics

### Avainluvut
- `agent_leader_agents_total` - Agenttien määrä
- `agent_leader_tasks_completed_total` - Suoritettujen tehtävien määrä
- `agent_leader_tasks_failed_total` - Epäonnistuneiden tehtävien määrä
- `agent_leader_task_execution_time_seconds` - Tehtävien suoritusaika

## 🔧 Konfiguraatio

### Environment-muuttujat (.env.agent_leader)

```bash
# Telegram (konfiguroitu)
TELEGRAM_BOT_TOKEN=8468877865:AAFrap3-U3fv2vacVI_yhXm6-hCHbB7SX54
TELEGRAM_CHAT_ID=7939379291

# Agent Leader
AGENT_LEADER_LOG_LEVEL=INFO
AGENT_LEADER_REPORT_INTERVAL=300
AGENT_LEADER_HEALTH_CHECK_INTERVAL=30

# API Keys (kopioitu .env:stä)
HELIUS_API_KEY=6e64d1b6-eead-47c8-9150-2b1d80c3b92a
COINGECKO_API_KEY=CG-NMU9VJoVYYRneDWigEwAjvnN
```

### Konfiguraatiotiedosto (agent_leader_config.yaml)

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

## 🚀 Pilveen asennus

### 1. Valmistelu

```bash
# Muokkaa deployment-scriptiä
nano deploy_integrated.sh
# Muuta DOCKER_REGISTRY omaan registryyn

# Tarkista environment-muuttujat
cat .env.agent_leader
```

### 2. Asennus

```bash
# Asenna integroitu järjestelmä
./deploy_integrated.sh deploy

# Tarkista status
./deploy_integrated.sh status

# Näytä lokit
./deploy_integrated.sh logs
```

### 3. Verifiointi

```bash
# Tarkista että kontainerit pyörivät
docker ps

# Tarkista Telegram-viestit
# (Pitäisi tulla viestejä Agent Leaderin käynnistyksestä)

# Tarkista monitoring
curl http://localhost:9090  # Prometheus
curl http://localhost:3000  # Grafana
```

## 🔍 Vianmääritys

### Yleisimmät ongelmat

1. **Telegram-viestit eivät tule**
   ```bash
   # Tarkista environment-muuttujat
   docker exec integrated-agent-leader env | grep TELEGRAM
   
   # Testaa Telegram-yhteys
   python3 get_telegram_chat_id.py
   ```

2. **Agentti ei vastaa**
   ```bash
   # Tarkista lokit
   docker logs integrated-agent-leader
   
   # Tarkista terveys
   docker exec integrated-agent-leader python3 -c "
   import asyncio
   from agent_leader import AgentLeader
   async def check():
       leader = AgentLeader()
       print(f'Agents: {len(leader.agents)}')
   asyncio.run(check())
   "
   ```

3. **Discovery Engine ei toimi**
   ```bash
   # Tarkista että kaikki riippuvuudet on asennettu
   docker exec integrated-agent-leader pip list | grep -E "(discovery|pumpportal)"
   
   # Tarkista konfiguraatio
   docker exec integrated-agent-leader cat .env
   ```

### Logien tarkistus

```bash
# Agent Leader lokit
docker logs -f integrated-agent-leader

# Kaikki palvelut
docker-compose -f docker-compose.integrated.yml logs -f

# Vain virheet
docker logs integrated-agent-leader 2>&1 | grep ERROR
```

## 📈 Skalautuvuus

### Horizontal scaling

```yaml
# docker-compose.integrated.yml
services:
  integrated-agent-leader:
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
    server integrated-agent-leader-1:8080;
    server integrated-agent-leader-2:8080;
    server integrated-agent-leader-3:8080;
}
```

## 🔒 Turvallisuus

### Best practices

1. **Environment-muuttujat**: Älä commitoi `.env.agent_leader` tiedostoa
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

## 🎉 Valmis!

Agent Leader -järjestelmä on nyt:

- ✅ **Täysin toimiva** - Testattu paikallisesti
- ✅ **Telegram-integroitu** - Viestit lähetetään onnistuneesti
- ✅ **Docker-valmis** - Kontainerit rakennettu
- ✅ **Monitoring-valmis** - Prometheus + Grafana
- ✅ **Pilveen valmis** - Deployment-scriptit luotu
- ✅ **Skaalautuva** - Useiden agenttien tuki
- ✅ **Luotettava** - Graceful shutdown ja error handling

### Seuraavat vaiheet:

1. **Testaa paikallisesti**: `./quick_start_agent_leader.sh`
2. **Deploy pilveen**: `./deploy_integrated.sh deploy`
3. **Monitoroi**: Käytä Grafana dashboardia
4. **Lisää agenteja**: Toteuta uusia ManagedAgent-protokollan mukaan
5. **Skaalaa**: Lisää instansseja tarpeen mukaan

**Agent Leader on valmis toimimaan itsenäisesti pilvessä!** 🚀
