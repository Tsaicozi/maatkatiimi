# Testausskriptit

## run_1min_and_collect.sh

Ajaa AutomaticHybridBot:in määritellyn ajan, sammuttaa sen siististi ja kerää raportin sekä artefaktit.

### Käyttö

```bash
# Oletus: 60 sekuntia, portti 9124
bash scripts/run_1min_and_collect.sh

# Mukautettu aika ja portti
bash scripts/run_1min_and_collect.sh 90 9108
```

### Parametrit

1. `DURATION_SEC` (oletus: 60) - Ajoaika sekunneissa
2. `METRICS_PORT` (oletus: 9124) - Prometheus metriikkaportti

### Tuotokset

- `.runtime/run_1min_report_YYYYMMDD_HHMMSS.txt` - Yhteenvetoraportti
- `run_artifacts_YYYYMMDD_HHMMSS.tar.gz` - Arkisto kaikista artefakteista

### Arkisto sisältää

- `automatic_hybrid_bot.log` - Päälogi
- `.runtime/stdout_YYYYMMDD_HHMMSS.log` - Stdout/stderr
- `.runtime/last_cycle.json` - Viimeinen sykli
- `.runtime/cycle_events.ndjson` - Syklitapahtumat
- `.runtime/metrics_snapshot_YYYYMMDD_HHMMSS.txt` - Metriikkasnapshot
- `.runtime/run_1min_report_YYYYMMDD_HHMMSS.txt` - Raportti

### Raportti sisältää

- Ajoaika ja portti
- Viimeinen sykli (jos löytyy)
- Syklitimeline
- Metriikkasnapshot
- TopScore-rivit
- Varoitukset ja virheet

