#!/bin/bash

# Helius Token Scanner Bot käynnistysskripti
# Tämä skripti varmistaa että vanhat prosessit sammutetaan ennen uuden käynnistystä

echo "🔍 Tarkistetaan vanhat botti-prosessit..."

# Tapa kaikki vanhat botti-prosessit
pkill -f "python3 run_helius_scanner.py" 2>/dev/null

# Odota että prosessit sammuvat
sleep 2

# Tarkista että portit ovat vapaita
echo "🔍 Tarkistetaan porttien vapaus..."
lsof -i :8001 -i :8002 -i :8003 -i :8004 -i :8005 -i :9109 -i :9110 -i :9111 -i :9112 2>/dev/null

if [ $? -eq 0 ]; then
    echo "⚠️  Portit ovat edelleen käytössä, tappaan prosessit pakolla..."
    lsof -ti :8001 -ti :8002 -ti :8003 -ti :8004 -ti :8005 -ti :9109 -ti :9110 -ti :9111 -ti :9112 | xargs kill -9 2>/dev/null
    sleep 1
fi

echo "✅ Käynnistetään botti..."

# Käynnistä botti uusilla porteilla
SCANNER_BUYERS30M_SOFT_MODE=1 \
SCANNER_MIN_BUYERS30M=0 \
SCANNER_ENFORCE_ACTIVE_POOL=0 \
SCANNER_UTIL_ENABLED=0 \
SCANNER_SCORE_MIN=10 \
SCANNER_STRICT_PLACEHOLDER=0 \
SCANNER_PLACEHOLDER_PENALTY=10 \
SCANNER_METRICS_PORT=8001 \
SCANNER_HEALTH_PORT=9109 \
python3 run_helius_scanner.py > helius_token_scanner_stdout.log 2>&1 &

echo "✅ Botti käynnistetty! PID: $!"
echo "📊 Metrics: http://localhost:8001"
echo "🏥 Health: http://localhost:9109/health"
echo "📝 Logit: tail -f helius_token_scanner_stdout.log"
