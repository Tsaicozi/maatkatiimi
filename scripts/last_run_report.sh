#!/usr/bin/env bash
# Kattaa viimeisimmän botin ajon: run-id, syklit, lähteet, metriikat, virheet, TopScoret, treidit.
# Käyttö: bash scripts/last_run_report.sh [METRICS_PORT]
set -euo pipefail

PORT="${1:-${METRICS_PORT:-9108}}"

# Selvitä ajossa olevan prosessin lokipolku (rotaatiot huomioiden)
PID="$(pgrep -f automatic_hybrid_bot.py | head -1 || true)"
if [[ -n "${PID}" ]]; then
  LOG="$(lsof -p "$PID" 2>/dev/null | awk '/automatic_hybrid_bot\.log/ {print $9; exit}')"
fi
LOG="${LOG:-automatic_hybrid_bot.log}"

has_jq() { command -v jq >/dev/null 2>&1; }

echo "=== LAST RUN REPORT ==="
date +'%Y-%m-%d %H:%M:%S'
echo "LOG: ${LOG}"
echo

# 1) Viimeisin syklitila (Cursor-ystävälliset tiedostot)
if [[ -f .runtime/last_cycle.json ]] && has_jq; then
  echo "— last_cycle.json —"
  jq '.' .runtime/last_cycle.json || true
  echo
fi

# 2) Cycle-timeline / run-id yhteenvedot
if [[ -f .runtime/cycle_events.ndjson ]] && has_jq; then
  RID="$(tail -n 2000 .runtime/cycle_events.ndjson | jq -r 'select(.evt=="cycle_start" or .evt=="cycle_end") | .run_id' | tail -1)"
  if [[ -n "${RID}" && "${RID}" != "null" ]]; then
    echo "— cycles (run_id=${RID}) —"
    jq -r --arg rid "$RID" '
      [ inputs | select(.run_id==$rid) ] as $evts
      | {
          run_id:$rid,
          starts: ($evts | map(select(.evt=="cycle_start")) | length),
          ends:   ($evts | map(select(.evt=="cycle_end"))   | length),
          first:  ($evts | map(select(.evt=="cycle_start")) | .[0].ts),
          last:   ($evts | map(select(.evt=="cycle_end"))   | .[-1].ts),
          last_hot: ($evts | map(select(.evt=="cycle_end")) | .[-1].hot // 0)
        }
    ' .runtime/cycle_events.ndjson
    echo
  fi
fi

# 3) Metriikkasnapshot (jos päällä)
METRICS="$(curl -fsS "http://127.0.0.1:${PORT}/metrics" 2>/dev/null || true)"
if [[ -n "$METRICS" ]]; then
  echo "— metrics (port ${PORT}) —"
  MIN_SCORE="$(awk '/^hybrid_bot_min_score_effective/ {print $2; exit}' <<<"$METRICS")"
  HOT_GAUGE="$(awk '/^hybrid_bot_hot_candidates / {print $2; exit}' <<<"$METRICS")"
  echo "min_score_effective: ${MIN_SCORE:-n/a}"
  echo "hot_candidates gauge: ${HOT_GAUGE:-n/a}"

  echo "candidates_in_total by source:"
  awk -F'[{} ,"]+' '/^hybrid_bot_candidates_in_total\{/ {for(i=1;i<=NF;i++)if($i=="source"){print $(i+2),$NF}}' <<<"$METRICS" \
    | awk '{printf "  - %-20s %s\n",$1,$2}' | sort || true

  echo "filtered_reason_total:"
  awk -F'[{} ,"]+' '/^hybrid_bot_candidates_filtered_reason_total\{/ {for(i=1;i<=NF;i++)if($i=="reason"){print $(i+2),$NF}}' <<<"$METRICS" \
    | awk '{printf "  - %-25s %s\n",$1,$2}' | sort || true
  echo
else
  echo "(metrics ei saatavilla portissa ${PORT})"
  echo
fi

# 4) Viimeiset virheet/varoitukset
if [[ -r "$LOG" ]] && has_jq; then
  echo "— viimeiset WARNING/ERROR —"
  grep -E '^\{"level": "(WARNING|ERROR)"' "$LOG" | jq -r 'select(.level=="WARNING" or .level=="ERROR") | "\(.ts) \(.level) \(.logger) — \(.msg)"' | tail -20 || true
  echo
fi

# 5) TopScore snapshot
if [[ -r "$LOG" ]] && has_jq; then
  echo "— TopScore (viimeiset 10) —"
  grep -E '^\{"level":' "$LOG" | jq -r 'select(.msg|test("TopScore ")) | .msg' | tail -10 || echo "(ei TopScore-rivejä)"
  echo
fi

# 6) Trade-logit (paper/live)
if [[ -r "$LOG" ]] && has_jq; then
  echo "— Trades (viimeiset 10) —"
  grep -E '^\{"level":' "$LOG" | jq -r 'select(.msg|test("\\[PAPER\\] BUY|BUY OK")) | "\(.ts) \(.msg)"' | tail -10 || echo "(ei trade-rivejä)"
  echo
fi

# 7) PumpPortal fetch -näytteet
if [[ -r "$LOG" ]] && has_jq; then
  echo "— PumpPortal fetch (näytteet) —"
  grep -E '^\{"level":' "$LOG" | jq -r 'select(.msg|test("PumpPortal fetch")) | "\(.ts) \(.msg)"' | tail -10 || echo "(ei PumpPortal fetch-rivejä)"
  echo
fi

# 8) DiscoveryEngine tilanne
if [[ -r "$LOG" ]] && has_jq; then
  echo "— DiscoveryEngine (viimeiset 10) —"
  grep -E '^\{"level":' "$LOG" | jq -r 'select(.logger=="discovery_engine") | "\(.ts) \(.msg)"' | tail -10 || echo "(ei DiscoveryEngine-rivejä)"
  echo
fi

# 9) WebSocket-lähteiden tila
if [[ -r "$LOG" ]] && has_jq; then
  echo "— WebSocket sources —"
  grep -E '^\{"level":' "$LOG" | jq -r 'select(.msg|test("WS|WebSocket|subscribe")) | "\(.ts) \(.logger) — \(.msg)"' | tail -10 || echo "(ei WebSocket-rivejä)"
  echo
fi

# 10) Yhteenveto
if [[ -r "$LOG" ]] && has_jq; then
  echo "— YHTEENVETO —"
  TOTAL_CYCLES="$(grep -E '^\{"level":' "$LOG" | jq -r 'select(.msg|test("Sykli.*valmis")) | .msg' | wc -l)"
  TOTAL_HOT="$(grep -E '^\{"level":' "$LOG" | jq -r 'select(.msg|test("hot candidate")) | .msg' | wc -l)"
  TOTAL_TRADES="$(grep -E '^\{"level":' "$LOG" | jq -r 'select(.msg|test("\\[PAPER\\] BUY|BUY OK")) | .msg' | wc -l)"
  LAST_CYCLE="$(grep -E '^\{"level":' "$LOG" | jq -r 'select(.msg|test("Sykli.*valmis")) | .msg' | tail -1)"
  
  echo "Kokonaissyklit: ${TOTAL_CYCLES}"
  echo "Hot candidateit: ${TOTAL_HOT}"
  echo "Trades: ${TOTAL_TRADES}"
  echo "Viimeisin sykli: ${LAST_CYCLE:-ei löytynyt}"
  echo
fi

echo "=== RAPORTTI VALMIS ==="
