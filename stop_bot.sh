#!/bin/bash

# Helius Token Scanner Bot sammutusskripti
# Tämä skripti sammuttaa botti-prosessit puhtaasti

echo "🛑 Sammutetaan Helius Token Scanner Bot..."

# Etsi botti-prosessit
PIDS=$(pgrep -f "python3 run_helius_scanner.py")

if [ -z "$PIDS" ]; then
    echo "ℹ️  Ei aktiivisia botti-prosesseja"
    exit 0
fi

echo "📋 Löytyi prosessit: $PIDS"

# Lähetä SIGTERM (graceful shutdown)
echo "🔄 Lähetetään graceful shutdown signaali..."
kill -TERM $PIDS

# Odota graceful shutdown
echo "⏳ Odotetaan graceful shutdown (10s)..."
sleep 10

# Tarkista onko prosessit vielä käynnissä
REMAINING=$(pgrep -f "python3 run_helius_scanner.py")

if [ ! -z "$REMAINING" ]; then
    echo "⚠️  Prosessit eivät sammuneet, pakotetaan sammutus..."
    kill -9 $REMAINING
    sleep 2
fi

# Varmista että kaikki on sammutettu
FINAL_CHECK=$(pgrep -f "python3 run_helius_scanner.py")

if [ -z "$FINAL_CHECK" ]; then
    echo "✅ Botti sammutettu onnistuneesti"
else
    echo "❌ Botti-prosesseja vielä käynnissä: $FINAL_CHECK"
    exit 1
fi

# Tarkista porttien vapaus
echo "🔍 Tarkistetaan porttien vapaus..."
lsof -i :8001 -i :8002 -i :8003 -i :8004 -i :8005 -i :9109 -i :9110 -i :9111 -i :9112 2>/dev/null

if [ $? -eq 0 ]; then
    echo "⚠️  Portit ovat edelleen käytössä"
else
    echo "✅ Kaikki portit vapaita"
fi
