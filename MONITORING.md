# Monitoring ja Alerting

## Yleiskuvaus

Hybrid Trading Bot sisältää kattavan monitoring- ja alerting-järjestelmän Prometheus + Grafana + Alertmanager:lla.

## Prometheus Metrics

### Endpoint
```
http://localhost:9108/metrics
```

### Recording Rules
Prometheus laskee automaattisesti nopeammat paneelit:
- `job:cycle_p95:5m` - Trading-syklin P95 kesto (5min)
- `job:rpc_p95:5m` - RPC-kutsun P95 latenssi (5min)  
- `job:telegram_per_min` - Telegram-viestien nopeus/min
- `job:filter_rate_per_min` - Pikafiltterin hylkäysnopeus/min

### Tärkeimmät Metrics:it

**Counters:**
- `hybrid_bot_candidates_seen_total` - Ehdokkaita havaittu yhteensä
- `hybrid_bot_candidates_filtered_total` - Pikafiltteri hylkäsi
- `hybrid_bot_candidates_scored_total` - Ehdokkaita pisteytetty
- `hybrid_bot_telegram_sent_total` - Lähetetyt Telegram-viestit
- `hybrid_bot_rpc_errors_total` - RPC-virheet
- `hybrid_bot_source_errors_total` - Lähdeadapterivirheet

**Gauges:**
- `hybrid_bot_queue_depth` - Candidate-jonon pituus
- `hybrid_bot_engine_running` - DiscoveryEngine käynnissä (1/0)
- `hybrid_bot_hot_candidates` - Hot candidate -määrä
- `hybrid_bot_metrics_health` - Metrics-palvelin OK (1/0)

**Histograms:**
- `hybrid_bot_score_hist` - Score-jakauma
- `hybrid_bot_rpc_latency_sec` - RPC-kutsun kesto
- `hybrid_bot_cycle_duration_sec` - Trading-syklin kesto

## Prometheus Konfiguraatio

### prometheus.yml
```yaml
scrape_configs:
  - job_name: 'hybrid_bot'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:9108']
```

### Käynnistä Prometheus
```bash
# Docker Compose
docker-compose up -d prometheus

# Tai suoraan
docker run -d -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  -v $(pwd)/alert_rules.yml:/etc/prometheus/alert_rules.yml \
  prom/prometheus
```

## Alertit

### alert_rules.yml

**Kriittiset alertit:**
- `MetricsServerDown` - Metrics-palvelin alhaalla
- `DiscoveryEngineDown` - DiscoveryEngine pysähtynyt
- `HighRPCErrors` - RPC-virheitä liikaa (>5/min)

**Varoitukset:**
- `NoHotCandidates` - Ei hot candidate:ja 30 min
- `SlowCycles` - Syklit hitaita (p95 > 5s)
- `HighQueueDepth` - Jonon pituus korkea (>100)
- `NoTelegramMessages` - Ei Telegram-viestejä 15 min

### Alertmanager (valinnainen)
```yaml
# alertmanager.yml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://localhost:5001/'
```

## Grafana Dashboard

### Käynnistä Grafana
```bash
# Docker Compose
docker-compose up -d grafana

# Tai suoraan
docker run -d -p 3000:3000 \
  -v grafana_data:/var/lib/grafana \
  grafana/grafana
```

### Kirjaudu sisään
- URL: http://localhost:3000
- Käyttäjä: admin
- Salasana: admin

### Dashboard
Dashboard sisältää paneelit:

1. **Hot Candidates** - Nykyinen hot candidate -määrä
2. **Score Distribution** - Score-jakauma heatmap:ina
3. **RPC Latency (p95)** - RPC-kutsujen latenssi
4. **Candidates Filtered** - Pikafiltterin hylkäykset/min
5. **Telegram Messages** - Telegram-viestit/min
6. **Queue Depth** - Candidate-jonon pituus
7. **Engine Status** - DiscoveryEngine tila
8. **Cycle Duration (p95)** - Trading-syklien kesto
9. **RPC Errors** - RPC-virheet/min

### PromQL Kyselyt

**Hot candidates:**
```promql
hybrid_bot_hot_candidates
```

**Score-jakauma:**
```promql
sum(rate(hybrid_bot_score_hist_bucket[5m])) by (le)
```

**RPC-latenssi (p95) - Recording Rule:**
```promql
job:rpc_p95:5m
```

**Pikafiltterin hylkäykset (per min) - Recording Rule:**
```promql
job:filter_rate_per_min
```

**Telegram-viestit (per min) - Recording Rule:**
```promql
job:telegram_per_min
```

**Jonon pituus:**
```promql
hybrid_bot_queue_depth
```

**Engine running (1/0):**
```promql
hybrid_bot_engine_running
```

**Cycle Duration (p95) - Recording Rule:**
```promql
job:cycle_p95:5m
```

## Docker Compose

### Käynnistä kaikki
```bash
docker-compose up -d
```

### Palvelut
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Bot Metrics**: http://localhost:9108/metrics

### Healthcheck Status
```bash
# Näe kaikkien palveluiden tila
docker-compose ps

# Tarkista yksittäinen palvelu
docker-compose ps hybrid-bot
docker-compose ps prometheus
docker-compose ps grafana
```

**Healthcheck Status:**
- 🟢 **healthy** - Palvelu toimii normaalisti
- 🟡 **starting** - Palvelu käynnistyy
- 🔴 **unhealthy** - Palvelu ei vastaa

### Sammuta
```bash
docker-compose down
```

## SLO:t (Service Level Objectives)

### Määritellyt SLO:t
- **Cycle Duration**: P95 < 3s 99% ajasta
- **RPC Errors**: < 1/min keskiarvona
- **Availability**: Metrics endpoint 99.9% uptime

### SLO-seuranta
```promql
# Cycle Duration SLO (99% ajasta < 3s)
histogram_quantile(0.99, sum(rate(hybrid_bot_cycle_duration_sec_bucket[1h])) by (le)) < 3

# RPC Errors SLO (< 1/min keskiarvona)
rate(hybrid_bot_rpc_errors_total[1h]) < 1/60

# Availability SLO (99.9% uptime)
avg_over_time(hybrid_bot_metrics_health[1h]) > 0.999
```

## Alert Runbook

### Mitä teen kun...

| Häly                    | Mitä se tarkoittaa           | Ensitoimet                                   | Diagnoosi-komennot                                |
| ----------------------- | ---------------------------- | -------------------------------------------- | ------------------------------------------------- |
| **MetricsServerDown**   | /metrics ei vastaa           | Tarkista prosessi ja portti                  | `ss -lntp \| grep 9108`, `docker logs hybrid-bot` |
| **DiscoveryEngineDown** | Engine ei raportoi           | Tarkista DiscoveryEngine-loki                | Greppaa "Scorer-loop päättyi"                     |
| **HighRPCErrors**       | RPC-virheiden tahti > 1/min  | Vaihda fallback RPC, rajoita lähteitä        | `tail -f automatic_hybrid_bot.log`                |
| **NoHotCandidates**     | Seulonta ei löydä ehdokkaita | Nosta score-kynnystä alas / tarkista lähteet | `curl /metrics` → queue_depth, candidates_seen  |
| **SlowCycles**          | Syklit P95 > 3s (SLO)        | Profilerit, RPC-latenssi, throttlaus         | `top`, `htop`, RPC bucketit                       |

### Yksityiskohtaiset diagnoosi-ohjeet

#### MetricsServerDown
```bash
# Tarkista prosessi
ps aux | grep automatic_hybrid_bot

# Tarkista portti
ss -lntp | grep 9108
netstat -tlnp | grep 9108

# Testaa endpoint
curl -v http://localhost:9108/metrics

# Docker-lokit
docker logs hybrid-bot --tail 50
```

#### DiscoveryEngineDown
```bash
# Etsi scorer-loop virheet
grep -i "scorer-loop" automatic_hybrid_bot.log

# Tarkista engine status
curl -s http://localhost:9108/metrics | grep engine_running

# Viimeisimmät lokit
tail -f automatic_hybrid_bot.log | grep -i "discovery"
```

#### HighRPCErrors
```bash
# RPC-virheiden tahti
curl -s http://localhost:9108/metrics | grep rpc_errors

# Reaaliaikaiset lokit
tail -f automatic_hybrid_bot.log | grep -i "rpc\|error"

# Tarkista RPC-endpoint
curl -s https://api.mainnet-beta.solana.com -w "%{http_code}"
```

#### NoHotCandidates
```bash
# Metrics-tilanne
curl -s http://localhost:9108/metrics | grep -E "(candidates_seen|candidates_scored|hot_candidates)"

# Tarkista score-kynnys
grep -i "score_threshold" config.yaml

# Queue-tilanne
curl -s http://localhost:9108/metrics | grep queue_depth
```

#### SlowCycles
```bash
# Sykli-kestot
curl -s http://localhost:9108/metrics | grep cycle_duration

# RPC-latenssi
curl -s http://localhost:9108/metrics | grep rpc_latency

# Resurssit
top -p $(pgrep -f automatic_hybrid_bot)
htop
```

### Hälyjen kuolettaminen

#### Flappeja vähentävät toimenpiteet:
- **for: viiveet**: Kaikki alertit käyttävät 10-20min viivettä
- **avg_over_time()**: NoHotCandidates käyttää 30min keskiarvoa
- **Ei absent()**: Vältetään turhia "flappeja" kun metriikka puuttuu

#### Alert-viiveet:
- **NoHotCandidates**: 20min (flappeja varten)
- **HighRPCErrors**: 10min (kriittinen, mutta ei liikaa hälytyksiä)
- **SlowCycles**: 15min (SLO-riippuvainen)
- **MetricsServerDown**: 1min (kriittinen)
- **DiscoveryEngineDown**: 5min (tärkeä, mutta ei kriittinen)

## JSON-Structured Logging

### Tuotantolokit
Bot käyttää JSON-rakenteisia lokitiedostoja helppoa korrelaatiota varten:

```json
{
  "level": "INFO",
  "ts": "2025-09-15T17:48:19.123Z",
  "logger": "hybrid_bot",
  "msg": "Cycle started",
  "run_id": "run_20250915_174814_394ac201",
  "cycle_id": "cycle_174819_d3b0708a",
  "cycle_number": 1
}
```

### Korrelaatio-ID:t
- **run_id**: Yksilöllinen tunniste jokaiselle bot-käynnistykselle
- **cycle_id**: Yksilöllinen tunniste jokaiselle analyysi-syklille
- **alert_name**: Hälytyksen nimi (alert-lokissa)
- **token_symbol**: Token-symboli (token-kohtaisissa lokeissa)

### Alert-lokit
```json
{
  "level": "WARNING",
  "ts": "2025-09-15T17:48:19.123Z",
  "logger": "hybrid_bot",
  "msg": "Alert triggered: NoHotCandidates",
  "run_id": "run_20250915_174814_394ac201",
  "cycle_id": "cycle_174819_d3b0708a",
  "alert_name": "NoHotCandidates",
  "severity": "warning",
  "description": "Seulonta saattaa olla rikki tai datalähteet alhaalla"
}
```

### Käyttöönotto
JSON-loggaus on automaattisesti käytössä `automatic_hybrid_bot.py`:ssä. Voit ottaa sen käyttöön myös muissa moduuleissa:

```python
from json_logging import setup_json_logging, generate_run_id, generate_cycle_id

# Setup JSON logger
json_logger = setup_json_logging()
run_id = generate_run_id()
cycle_id = generate_cycle_id()

json_logger.set_run_id(run_id)
json_logger.set_cycle_id(cycle_id)

# Log with correlation IDs
json_logger.info("Operation started", extra={"operation": "token_analysis"})
```

## Konfiguraatio

### Bot Metrics
```yaml
# config.yaml
metrics:
  enabled: true
  host: "0.0.0.0"
  port: 9108
  namespace: hybrid_bot
```

### Ympäristömuuttujat
```bash
export METRICS_ENABLED=true
export METRICS_PORT=9108
```

## Troubleshooting

### Metrics ei näy
1. Tarkista että bot pyörii: `ps aux | grep automatic_hybrid_bot`
2. Tarkista metrics endpoint: `curl http://localhost:9108/metrics`
3. Tarkista Prometheus target: http://localhost:9090/targets

### Alertit eivät toimi
1. Tarkista alert_rules.yml syntaksi: `promtool check rules alert_rules.yml`
2. Tarkista Prometheus logs: `docker logs prometheus`
3. Tarkista alertit: http://localhost:9090/alerts

### Grafana ei näytä dataa
1. Tarkista datasource: http://localhost:3000/datasources
2. Tarkista Prometheus URL: `http://prometheus:9090`
3. Testaa connection: "Test" -nappi

## Tiedostot

- `prometheus.yml` - Prometheus konfiguraatio
- `alert_rules.yml` - Alert-säännöt
- `grafana_dashboard.json` - Grafana dashboard
- `docker-compose.yml` - Docker Compose konfiguraatio
- `config.yaml` - Bot metrics konfiguraatio
