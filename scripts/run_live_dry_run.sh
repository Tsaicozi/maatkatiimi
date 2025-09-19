#!/usr/bin/env bash
# Pieni dry-run skripti hybrid-botin testaamiseen oikeassa ympäristössä
# Käynnistää botin 3 syklin testimoodissa, watchdogeilla ja selkeällä lokipolulla.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

LOG_DIR="${PROJECT_ROOT}/run_logs"
mkdir -p "${LOG_DIR}"
LOG_SUFFIX="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/live_dry_run_${LOG_SUFFIX}.log"


export HYBRID_BOT_OFFLINE=${HYBRID_BOT_OFFLINE:-0}
export TEST_MAX_CYCLES=${TEST_MAX_CYCLES:-0}
export TEST_MAX_RUNTIME=${TEST_MAX_RUNTIME:-0}
export TEST_ALIGN_NOW=${TEST_ALIGN_NOW:-0}
export STARTUP_WATCHDOG_SEC=${STARTUP_WATCHDOG_SEC:-5}
export TELEGRAM_MINT_COOLDOWN_SECONDS=${TELEGRAM_MINT_COOLDOWN_SECONDS:-1800}
export DISCOVERY_CANDIDATE_TTL_SEC=${DISCOVERY_CANDIDATE_TTL_SEC:-600}
export FORCE_TERM_AFTER_SEC=${FORCE_TERM_AFTER_SEC:-0}

printf "Running live dry-run -> log: %s\n" "$LOG_FILE"

python3 "${PROJECT_ROOT}/automatic_hybrid_bot.py" \
  | tee "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}
printf "\nDry-run finished with exit code %s\n" "$EXIT_CODE"
exit "$EXIT_CODE"
