#!/bin/bash
# Setup cron job for Helius Token Analysis Bot

echo "🕐 Asetetaan cron-ajastus Helius Token Analysis Botille..."

# Luo cron-merkintä (päivittäin klo 12:00)
CRON_JOB="0 12 * * * cd /workspace && /usr/bin/python3 run_helius_analysis.py analyze >> /workspace/cron_analysis.log 2>&1"

# Lisää cron-merkintä
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Cron-ajastus asetettu:"
echo "   - Päivittäiset raportit klo 12:00"
echo "   - Lokitiedosto: /workspace/cron_analysis.log"
echo ""
echo "Näytä nykyiset cron-työt: crontab -l"
echo "Poista cron-työ: crontab -e (poista rivi)"