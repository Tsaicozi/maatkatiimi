#!/usr/bin/env bash
# scripts/run_1min_and_collect.sh
# Aja bottia ~1 minuutti, sammuta siististi ja kerää raportti + artefaktit.
# Käyttö:
#   bash scripts/run_1min_and_collect.sh [DURATION_SEC=60] [METRICS_PORT=9124]
set -euo pipefail

DUR="${1:-60}"
PORT="${2:-${METRICS_PORT:-9124}}"
TS="$(date +'%Y%m%d_%H%M%S')"
RUNDIR=".runtime"
REPORT="${RUNDIR}/run_1min_report_${TS}.txt"
MET_SNAP="${RUNDIR}/metrics_snapshot_${TS}.txt"
ARCHIVE="run_artifacts_${TS}.tar.gz"

mkdir -p "$RUNDIR"

echo "=== run_1min_and_collect: start @ $(date +'%F %T') ==="
echo "Duration: ${DUR}s, Metrics port: ${PORT}"

# Varmista puhdas tila
rm -f /tmp/hybrid_bot.KILL || true

# Käynnistä botti taustalle – immediate start, paper-mode, metriikat päälle
echo "[*] Starting bot..."
TEST_ALIGN_NOW=1 \
TEST_MAX_CYCLES=0 \
TRADING_ENABLED=true \
TRADING_PAPER_TRADE=true \
METRICS_ENABLED=1 \
METRICS_PORT="${PORT}" \
python3 automatic_hybrid_bot.py > "${RUNDIR}/stdout_${TS}.log" 2>&1 &

PID=$!
echo "[*] Bot PID=${PID}"
sleep 1

# Selvitä logipolku
LOG="$(lsof -p "$PID" 2>/dev/null | awk '/automatic_hybrid_bot\.log/ {print $9; exit}')"
LOG="${LOG:-automatic_hybrid_bot.log}"
echo "[*] LOG=${LOG}"

# Odota 1. sykliä enintään 20 s
echo "[*] Waiting for first cycle (max 20s)..."
t0=$(date +%s)
while true; do
  if [[ -f "${RUNDIR}/last_cycle.json" ]]; then
    break
  fi
  if (( $(date +%s) - t0 > 20 )); then
    echo "[!] No cycle detected within 20s (continuing anyway)" | tee -a "$REPORT"
    break
  fi
  sleep 1
done

# Aja ~1 min
echo "[*] Running for ${DUR}s..."
sleep "${DUR}"

# Sammuta siististi: kill-switch → odota, sitten TERM → KILL
echo "[*] Stopping bot (kill-switch)..."
touch /tmp/hybrid_bot.KILL || true

# odota max 15s
for i in {1..15}; do
  if ! kill -0 "$PID" 2>/dev/null; then
    break
  fi
  sleep 1
done

if kill -0 "$PID" 2>/dev/null; then
  echo "[!] Still running → SIGTERM"
  kill -TERM "$PID" || true
  sleep 5
fi

if kill -0 "$PID" 2>/dev/null; then
  echo "[!] Still running → SIGKILL"
  kill -KILL "$PID" || true
fi

echo "[*] Bot stopped."

# Kerää metriikat (jos portti kuuntelee)
echo "[*] Snapshot metrics (port ${PORT})..."
if command -v curl >/dev/null 2>&1; then
  (curl -fsS "http://127.0.0.1:${PORT}/metrics" || true) > "${MET_SNAP}" || true
else
  echo "(curl puuttuu, ohitetaan metriikat)" > "${MET_SNAP}"
fi

# Rakenna raportti
echo "[*] Building report..."
{
  echo "=== 1-MIN RUN REPORT ==="
  date +'%F %T'
  echo "Duration: ${DUR}s"
  echo "Metrics port: ${PORT}"
  echo "LOG: ${LOG}"
  echo

  echo "— Last cycle (if any) —"
  if [[ -f "${RUNDIR}/last_cycle.json" ]]; then
    if command -v jq >/dev/null 2>&1; then
      jq '.' "${RUNDIR}/last_cycle.json" || cat "${RUNDIR}/last_cycle.json"
    else
      cat "${RUNDIR}/last_cycle.json"
    fi
  else
    echo "(no last_cycle.json)"
  fi
  echo

  echo "— Cycles timeline (from cycle_events.ndjson) —"
  if [[ -f "${RUNDIR}/cycle_events.ndjson" ]]; then
    if command -v jq >/dev/null 2>&1; then
      RUNID=$(tail -n 2000 "${RUNDIR}/cycle_events.ndjson" | jq -r 'select(.evt=="cycle_start" or .evt=="cycle_end") | .run_id' | tail -1)
      if [[ -n "${RUNID}" && "${RUNID}" != "null" ]]; then
        jq -r --arg rid "$RUNID" '
          [ inputs | select(.run_id==$rid) ] as $ev
          | {
              run_id:$rid,
              starts: ($ev|map(select(.evt=="cycle_start"))|length),
              ends:   ($ev|map(select(.evt=="cycle_end"))|length),
              last_end: ($ev|map(select(.evt=="cycle_end"))|.[-1])
            }' "${RUNDIR}/cycle_events.ndjson"
      else
        tail -n 10 "${RUNDIR}/cycle_events.ndjson"
      fi
    else
      tail -n 10 "${RUNDIR}/cycle_events.ndjson"
    fi
  else
    echo "(no cycle_events.ndjson)"
  fi
  echo

  echo "— Metrics snapshot —"
  if [[ -s "${MET_SNAP}" ]]; then
    awk '
      /hybrid_bot_min_score_effective/ {print "min_score_effective: "$2}
      /hybrid_bot_hot_candidates /     {print "hot_candidates (gauge): "$2}
    ' "${MET_SNAP}" | sed '/^$/d' || true

    echo "candidates_in_total by source:"
    awk -F'[{} ,"]+' '/^hybrid_bot_candidates_in_total\{/ {for(i=1;i<=NF;i++)if($i=="source"){print $(i+2),$NF}}' "${MET_SNAP}" \
      | awk '{printf "  - %-22s %s\n",$1,$2}' | sort || true

    echo "filtered_reason_total:"
    awk -F'[{} ,"]+' '/^hybrid_bot_candidates_filtered_reason_total\{/ {for(i=1;i<=NF;i++)if($i=="reason"){print $(i+2),$NF}}' "${MET_SNAP}" \
      | awk '{printf "  - %-25s %s\n",$1,$2}' | sort || true

    grep -E '^hybrid_bot_fresh_pass_total' "${MET_SNAP}" || true
  else
    echo "(no metrics snapshot)"
  fi
  echo

  echo "— Last TopScore rows —"
  if [[ -r "${LOG}" ]]; then
    if command -v jq >/dev/null 2>&1; then
      jq -r 'select(.msg|test("TopScore ")) | .msg' "${LOG}" | tail -n 12 || true
    else
      grep -E "TopScore " "${LOG}" | tail -n 12 || true
    fi
  fi
  echo

  echo "— Last warnings/errors —"
  if [[ -r "${LOG}" ]]; then
    if command -v jq >/dev/null 2>&1; then
      jq -r 'select(.level=="WARNING" or .level=="ERROR") | "\(.ts) \(.level) \(.logger) — \(.msg)"' "${LOG}" | tail -n 20 || true
    else
      grep -E '"level": "WARNING"|"level": "ERROR"' "${LOG}" | tail -n 20 || true
    fi
  fi
  echo

  echo "=== END REPORT ==="
} > "${REPORT}"

# Pakkaa artefaktit
echo "[*] Archiving artifacts → ${ARCHIVE}"
tar -czf "${ARCHIVE}" \
  "${LOG}" \
  "${RUNDIR}/stdout_${TS}.log" \
  "${RUNDIR}/last_cycle.json" \
  "${RUNDIR}/cycle_events.ndjson" \
  "${MET_SNAP}" \
  "${REPORT}" 2>/dev/null || true

echo "✔ Done."
echo "Report : ${REPORT}"
echo "Archive: ${ARCHIVE}"
