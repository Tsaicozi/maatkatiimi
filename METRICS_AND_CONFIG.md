# Metrics ja Konfiguraatio

## Yleiskuvaus

Lisätty Prometheus metrics keräys ja YAML-pohjainen konfiguraatio botin havaittavuuden ja konfiguroitavuuden parantamiseksi.

## Konfiguraatio (config.yaml)

### Discovery
- `min_liq_usd`: Minimilikviditeetti USD (oletus: 3000)
- `score_threshold`: Pisteytys kynnys (oletus: 0.65)
- `max_queue`: Maksimijonon koko (oletus: 2000)
- `sources`: Lähdeadapterien feature flagit
  - `raydium`: true/false
  - `orca`: true/false
  - `pumpfun`: true/false

### Risk
- `require_lp_locked`: Vaadi LP lukittu/poltettu (oletus: true)
- `max_top10_share`: Maksimi top10 holder share (oletus: 0.90)
- `require_renounced`: Vaadi authorityt renounced (oletus: true)

### Telegram
- `cooldown_seconds`: Viestejen cooldown (oletus: 900)
- `batch_summary`: Lähetä batch yhteenveto (oletus: true)

### I/O
- `rpc_timeout_sec`: RPC timeout (oletus: 3)
- `ws_connect_timeout_sec`: WebSocket connect timeout (oletus: 5)
- `retry_max`: Maksimi retry määrä (oletus: 4)

### Metrics
- `enabled`: Metrics käytössä (oletus: true)
- `port`: Metrics server portti (oletus: 9108)
- `namespace`: Metrics namespace (oletus: "hybrid_bot")

### Runtime
- `timezone`: Aikavyöhyke (oletus: "Europe/Helsinki")
- `test_max_cycles`: Testimoodi max syklejä (oletus: null)
- `test_max_runtime_sec`: Testimoodi max aika sekunneissa (oletus: null)

## Metrics

### Counters
- `hybrid_bot_candidates_seen_total`: Ehdokkaita havaittu yhteensä
- `hybrid_bot_candidates_filtered_total`: Pikafiltteri hylkäsi
- `hybrid_bot_candidates_scored_total`: Ehdokkaita pisteytetty
- `hybrid_bot_telegram_sent_total`: Lähetetyt Telegram-viestit
- `hybrid_bot_rpc_errors_total`: RPC-virheet
- `hybrid_bot_source_errors_total`: Lähdeadapterivirheet
- `hybrid_bot_scorer_loop_restarts_total`: Scorer-loop restartit

### Gauges
- `hybrid_bot_queue_depth`: Candidate-jonon pituus
- `hybrid_bot_engine_running`: DiscoveryEngine käynnissä (1/0)
- `hybrid_bot_hot_candidates`: Hot candidate -määrä

### Histograms
- `hybrid_bot_score_hist`: Score-jakauma (buckets: 0.2,0.4,0.6,0.7,0.8,0.9,1.0)
- `hybrid_bot_rpc_latency_sec`: RPC-kutsun kesto (buckets: 0.05,0.1,0.2,0.5,1,2,5)
- `hybrid_bot_cycle_duration_sec`: Trading-syklin kesto (buckets: 0.1,0.5,1,2,3,5,10)

## Käyttö

### Konfiguraation lukeminen
```python
from config import load_config

# Koko konfiguraatio
config = load_config()

# Tietty osa
print(f"Min liquidity: {config.discovery.min_liq_usd}")
print(f"Score threshold: {config.discovery.score_threshold}")
print(f"Metrics enabled: {config.metrics.enabled}")
```

### Metrics käyttö
```python
from metrics import init_metrics, metrics

# Alusta metrics
init_metrics(namespace="hybrid_bot", port=9108, enabled=True)

# Käytä metrics:ia
if metrics:
    metrics.candidates_seen.inc()
    metrics.queue_depth.set(5)
    metrics.score_hist.observe(0.75)
    metrics.cycle_duration.observe(2.5)
```

### Metrics server
Metrics server käynnistyy automaattisesti portissa 9108 (konfiguroitavissa).

Prometheus endpoint: `http://localhost:9108/metrics`

## Ympäristömuuttujien Override

Tärkeimmät konfiguraatio parametrit voidaan ylikirjoittaa ympäristömuuttujilla:

```bash
# Metrics
export METRICS_ENABLED=false
export METRICS_PORT=9109

# Discovery
export DISCOVERY_SCORE_THRESHOLD=0.7
export DISCOVERY_MIN_LIQ_USD=5000

# Testimoodi
export TEST_MAX_CYCLES=5
export TEST_MAX_RUNTIME=60
```

## Testaus

```bash
# Testaa konfiguraatiota
python3 -c "from config import load_config; print(load_config())"

# Testaa ympäristömuuttujien override:a
DISCOVERY_MIN_LIQ_USD=5000 python3 -c "from config import load_config; print(load_config().discovery.min_liq_usd)"

# Testaa metrics:ia
python3 test_metrics.py

# Tarkista metrics endpoint
curl http://localhost:9108/metrics

# Testaa koko integraatiota
python3 test_discovery_manual.py
python3 test_hybrid_bot.py
```

## Asennus

```bash
pip3 install prometheus-client PyYAML
```

## Tiedostot

- `config.yaml`: Konfiguraatiotiedosto
- `config.py`: Kevyt konfiguraation lukija + ympäristömuuttujien override
- `metrics.py`: Prometheus metrics
- `requirements.txt`: Päivitetty riippuvuuksilla
