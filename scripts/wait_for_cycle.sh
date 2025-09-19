#!/usr/bin/env bash
# Odota max N sek, että botti kirjoittaa .runtime/last_cycle.json tai tulostaa ASCII-markkerin.
set -euo pipefail
TIMEOUT="${1:-120}"
echo "[wait_for_cycle] timeout=${TIMEOUT}s"
# 1) STDOUT-markkeri (jos ajetaan samassa sessiossa): ei luoteta tähän Cursorissa → jatka kohtaan 2
# 2) Status-tiedosto
t0=$(date +%s)
while true; do
  if [[ -f .runtime/last_cycle.json ]]; then
    echo "[wait_for_cycle] last_cycle:"
    cat .runtime/last_cycle.json
    exit 0
  fi
  if (( $(date +%s) - t0 >= TIMEOUT )); then
    echo "[wait_for_cycle] NO CYCLE within ${TIMEOUT}s"
    exit 1
  fi
  sleep 1
done
