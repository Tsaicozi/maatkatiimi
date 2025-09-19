#!/usr/bin/env bash
# Yksinkertainen raportti ilman jq-riippuvuutta
set -euo pipefail

echo "=== SIMPLE BOT REPORT ==="
date +'%Y-%m-%d %H:%M:%S'
echo

# Etsi lokitiedosto
PID="$(pgrep -f automatic_hybrid_bot.py | head -1 || true)"
if [[ -n "${PID}" ]]; then
  LOG="$(lsof -p "$PID" 2>/dev/null | awk '/automatic_hybrid_bot\.log/ {print $9; exit}')"
fi
LOG="${LOG:-automatic_hybrid_bot.log}"

echo "LOG: ${LOG}"
echo

# 1) Viimeisin sykli
if [[ -f .runtime/last_cycle.json ]]; then
  echo "— Viimeisin sykli —"
  cat .runtime/last_cycle.json
  echo
fi

# 2) Viimeiset syklit
echo "— Viimeiset syklit —"
grep -E 'Sykli.*valmis' "$LOG" 2>/dev/null | tail -5 || echo "(ei sykli-rivejä)"
echo

# 3) Hot candidateit
echo "— Hot candidateit —"
grep -E 'hot candidate' "$LOG" 2>/dev/null | tail -5 || echo "(ei hot candidate-rivejä)"
echo

# 4) Virheet/varoitukset
echo "— Viimeiset virheet —"
grep -E 'WARNING|ERROR' "$LOG" 2>/dev/null | tail -10 || echo "(ei virheitä)"
echo

# 5) PumpPortal fetch
echo "— PumpPortal fetch —"
grep -E 'PumpPortal fetch' "$LOG" 2>/dev/null | tail -5 || echo "(ei PumpPortal fetch-rivejä)"
echo

# 6) Yhteenveto
echo "— YHTEENVETO —"
CYCLES="$(grep -c 'Sykli.*valmis' "$LOG" 2>/dev/null || echo 0)"
HOT="$(grep -c 'hot candidate' "$LOG" 2>/dev/null || echo 0)"
TRADES="$(grep -c 'BUY OK' "$LOG" 2>/dev/null || echo 0)"

echo "Syklit: ${CYCLES}"
echo "Hot candidateit: ${HOT}"
echo "Trades: ${TRADES}"
echo

echo "=== RAPORTTI VALMIS ==="
