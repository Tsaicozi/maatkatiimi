# Agent Leader - GitHub Cloud Deployment

Tämä opas kuvaa kuinka Agent Leader asennetaan GitHub Actions -pilveen valvomaan ja ohjaamaan muita agenteja.

## 🎯 Mitä on luotu

### ✅ GitHub Integration
- **`github_agent.py`** - GitHub Actions -monitorointi
- **`cloud_agent_leader.py`** - Cloud Agent Leader joka hallinnoi kaikkia agenteja
- **`.github/workflows/agent-leader-cloud.yml`** - GitHub Actions deployment
- **`.github/workflows/agent-leader-deploy.yml`** - Perus deployment workflow

### ✅ Cloud-Ready Components
- **GitHub Agent** - Valvoo GitHub Actions -workflowja
- **Hybrid Agent** - Integroi trading bot -järjestelmän
- **Telegram Integration** - Reaaliaikaiset hälytykset
- **Multi-Agent Management** - Keskitetty hallinta

## 🚀 GitHub Actions Deployment

### 1. GitHub Secrets Setup

Lisää seuraavat secrets GitHub repositoryyn:

```bash
# GitHub Repository Settings > Secrets and variables > Actions

TELEGRAM_BOT_TOKEN=8468877865:AAFrap3-U3fv2vacVI_yhXm6-hCHbB7SX54
TELEGRAM_CHAT_ID=7939379291
GITHUB_TOKEN=your_github_personal_access_token
HELIUS_API_KEY=6e64d1b6-eead-47c8-9150-2b1d80c3b92a
COINGECKO_API_KEY=CG-NMU9VJoVYYRneDWigEwAjvnN
```

### 2. GitHub Personal Access Token

Luo GitHub Personal Access Token:

1. Mene GitHub > Settings > Developer settings > Personal access tokens
2. Luo uusi token (classic)
3. Valitse scopes:
   - `repo` (full repository access)
   - `workflow` (update GitHub Action workflows)
   - `read:org` (read organization membership)
4. Kopioi token ja lisää se GitHub Secrets:iin

### 3. Workflow Käynnistys

```bash
# Push koodia GitHubiin
git add .
git commit -m "Deploy Agent Leader to cloud"
git push origin main

# Workflow käynnistyy automaattisesti
# Tai käynnistä manuaalisesti: Actions > Agent Leader Cloud Deployment > Run workflow
```

## 📊 Agent Leader Cloud Features

### 🤖 Hallinnoitavat Agenteja

**1. Hybrid Trading Agent**
- Valvoo Solana-token-seulontaa
- Integroi nykyisen trading bot -järjestelmän
- Lähettää Telegram-hälytyksiä kuumista tokeneista

**2. GitHub Agent**
- Valvoo GitHub Actions -workflowja
- Tarkistaa pull requestit ja issuet
- Lähettää hälytyksiä epäonnistuneista workflowista
- Monitoroi turvallisuushälytyksiä

**3. Tulevaisuudessa:**
- Discord Agent
- Slack Agent
- Email Agent
- Database Agent
- Monitoring Agent

### 📱 Telegram-viestit

**Agenttien rekisteröinti:**
```
🤖 **New Agent Registered**
Name: GitHub Actions Monitor
ID: github_agent
Total agents: 2
```

**GitHub Actions -hälytykset:**
```
🚨 **GitHub Workflow Failed**
Workflow: Deploy Agent Leader
Branch: main
URL: https://github.com/user/repo/actions/runs/123
```

**Jaksolliset raportit:**
```
📊 **Cloud Agent Leader Report**
⏱️ Uptime: 2.5h
🤖 Agents: 2
📋 Tasks: 150 (✅145 ❌5)
📈 Success rate: 96.7%
🔄 Pending tasks: 2
🏥 Agent status: healthy: 2
```

## 🔍 Monitoring & Observability

### GitHub Actions Dashboard
- **URL**: https://github.com/jarihiirikoski/matkatiimi/actions
- **Workflows**: Agent Leader Cloud Deployment
- **Status**: Real-time monitoring

### Telegram Notifications
- **Bot**: @your_bot_name
- **Chat ID**: 7939379291
- **Notifications**: Real-time alerts

### Logs
- **GitHub Actions Logs**: Actions tab
- **Agent Leader Logs**: cloud_agent_leader.log
- **Telegram Logs**: telegram_bot_integration logs

## 🛠️ Development & Testing

### Paikallinen testaus

```bash
# Testaa Cloud Agent Leader
python3 cloud_agent_leader.py demo

# Testaa GitHub Agent
export GITHUB_TOKEN=your_token
python3 github_agent.py demo

# Testaa kaikki agenteja
./quick_start_agent_leader.sh
```

### GitHub Actions testaus

```bash
# Push test-muutoksia
git add .
git commit -m "Test Agent Leader deployment"
git push origin main

# Tarkista Actions tab
# Workflow pitäisi käynnistyä automaattisesti
```

## 🔧 Konfiguraatio

### Environment Variables

```bash
# GitHub Actions workflow asettaa automaattisesti:
TELEGRAM_BOT_TOKEN=from_secrets
TELEGRAM_CHAT_ID=from_secrets
GITHUB_TOKEN=from_secrets
HELIUS_API_KEY=from_secrets
COINGECKO_API_KEY=from_secrets
```

### Agent Configuration

```python
# cloud_agent_leader.py
class CloudAgentLeader:
    def __init__(self):
        self.scan_interval = 60  # sekuntia
        self.report_interval = 300  # 5 minuuttia
        
        # Agenteja konfiguraatio
        self.agents = {
            "hybrid": HybridAgentConfig(...),
            "github": GitHubAgentConfig(...)
        }
```

## 🚀 Advanced Features

### 1. Multi-Repository Monitoring

```python
# github_agent.py
repositories = [
    "jarihiirikoski/matkatiimi",
    "jarihiirikoski/other-repo",
    "organization/shared-repo"
]

for repo in repositories:
    await self._monitor_repository(repo)
```

### 2. Custom Webhooks

```python
# GitHub webhook endpoint
@app.route('/webhook/github', methods=['POST'])
async def github_webhook():
    payload = request.json
    await agent_leader.create_task(
        name="github_webhook_process",
        data={"payload": payload}
    )
```

### 3. Auto-Scaling

```yaml
# .github/workflows/agent-leader-cloud.yml
strategy:
  matrix:
    environment: [production, staging, development]
  max-parallel: 3
```

## 🔒 Security

### GitHub Secrets
- Älä koskaan commitoi secrets koodiin
- Käytä GitHub Secrets -toimintoa
- Rotaatio secrets säännöllisesti

### API Keys
- Rajoita API key -oikeuksia
- Käytä environment-muuttujia
- Monitoroi API-käyttöä

### Access Control
- Käytä GitHub Personal Access Tokens
- Rajoita repository-oikeuksia
- Monitoroi käyttöoikeuksia

## 📈 Performance & Scaling

### Resource Limits
```yaml
# GitHub Actions
runs-on: ubuntu-latest
# 2 CPU cores, 7 GB RAM, 14 GB SSD
```

### Optimization
- Käytä caching dependencies
- Optimoi API-kutsut
- Rajoita concurrent tasks

### Monitoring
- GitHub Actions usage
- API rate limits
- Memory usage
- Execution time

## 🆘 Troubleshooting

### Yleisimmät ongelmat

1. **GitHub Token ei toimi**
   ```bash
   # Tarkista token oikeudet
   curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
   ```

2. **Telegram-viestit eivät tule**
   ```bash
   # Tarkista bot token ja chat ID
   python3 get_telegram_chat_id.py
   ```

3. **Workflow epäonnistuu**
   ```bash
   # Tarkista Actions tab
   # Katso logs workflowsta
   ```

### Debug Commands

```bash
# Testaa GitHub API
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/jarihiirikoski/matkatiimi

# Testaa Telegram
python3 -c "
from telegram_bot_integration import TelegramBot
import asyncio
async def test():
    bot = TelegramBot()
    await bot.send_message('Test message')
asyncio.run(test())
"
```

## 🎉 Valmis!

Agent Leader on nyt:

- ✅ **GitHub Actions -integroitu** - Automaattinen deployment
- ✅ **Multi-Agent Management** - Hallinnoi useita agenteja
- ✅ **Real-time Monitoring** - GitHub Actions + Trading bots
- ✅ **Telegram Notifications** - Reaaliaikaiset hälytykset
- ✅ **Cloud-Ready** - Toimii GitHub Actions -pilvessä
- ✅ **Scalable** - Lisää agenteja helposti
- ✅ **Secure** - GitHub Secrets + API key management

### Seuraavat vaiheet:

1. **Aseta GitHub Secrets** - Lisää API keys
2. **Push koodia** - Käynnistä deployment
3. **Monitoroi** - Tarkista Actions tab
4. **Lisää agenteja** - Toteuta uusia ManagedAgent-protokollan mukaan
5. **Skaalaa** - Lisää repositoryja ja agenteja

**Agent Leader on nyt valmis valvomaan ja ohjaamaan GitHub-agnenteja pilvessä!** 🚀
