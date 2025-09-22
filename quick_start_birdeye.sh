#!/bin/bash
# Quick Start script for Birdeye Key Manager

echo "======================================"
echo "🚀 BIRDEYE KEY MANAGER - QUICK START"
echo "======================================"
echo ""

# Tarkista Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 ei löydy!"
    exit 1
fi

echo "✅ Python3 löytyy: $(python3 --version)"

# Tarkista .env
if [ -f ".env" ]; then
    echo "✅ .env-tiedosto löytyy"
    
    # Tarkista onko BIRDEYE_API_KEY
    if grep -q "BIRDEYE_API_KEY" .env; then
        echo "✅ BIRDEYE_API_KEY löytyy .env-tiedostosta"
        
        # Näytä avain (sensuroituna)
        KEY=$(grep "^BIRDEYE_API_KEY=" .env | cut -d'=' -f2)
        if [ ! -z "$KEY" ]; then
            echo "   Avain: ${KEY:0:8}..."
        fi
    else
        echo "⚠️ BIRDEYE_API_KEY puuttuu .env-tiedostosta"
        echo ""
        echo "Haluatko lisätä sen nyt? (y/n)"
        read -r response
        if [ "$response" = "y" ]; then
            python3 create_env.py
        fi
    fi
else
    echo "⚠️ .env-tiedostoa ei löydy"
    echo ""
    echo "Luodaan .env-tiedosto..."
    python3 create_env.py
fi

echo ""
echo "======================================"
echo "📋 VALIKKO"
echo "======================================"
echo "1. Testaa Birdeye-avain"
echo "2. Käynnistä Key Manager Bot"
echo "3. Interaktiivinen setup"
echo "4. Näytä status"
echo "5. Integroi botteihin"
echo "0. Lopeta"
echo ""
echo -n "Valinta: "
read choice

case $choice in
    1)
        echo ""
        echo "🧪 Testataan Birdeye-avain..."
        python3 test_birdeye_key.py
        ;;
    2)
        echo ""
        echo "🚀 Käynnistetään Key Manager Bot..."
        echo "Pysäytä painamalla Ctrl+C"
        python3 birdeye_key_manager.py
        ;;
    3)
        echo ""
        echo "🔧 Interaktiivinen setup..."
        python3 setup_birdeye_keys.py
        ;;
    4)
        echo ""
        echo "📊 Näytetään status..."
        python3 birdeye_integration.py status
        ;;
    5)
        echo ""
        echo "🔌 Integroidaan botteihin..."
        python3 birdeye_integration.py patch
        ;;
    0)
        echo "👋 Hei hei!"
        exit 0
        ;;
    *)
        echo "❌ Virheellinen valinta"
        exit 1
        ;;
esac