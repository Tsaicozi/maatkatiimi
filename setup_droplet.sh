#!/bin/bash
# Solana Auto Trader - DigitalOcean Droplet Setup Script
# Aja tämä uudessa Ubuntu 22.04 dropletissa rootina

set -e

echo "🚀 Asennetaan Solana Auto Trader..."

# Värit
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Päivitä järjestelmä
echo -e "${BLUE}[1/8] Päivitetään järjestelmä...${NC}"
apt update && apt upgrade -y

# 2. Asenna riippuvuudet
echo -e "${BLUE}[2/8] Asennetaan Python ja työkalut...${NC}"
apt install -y python3.10 python3.10-venv python3-pip git screen curl ufw

# 3. Luo trader-käyttäjä
echo -e "${BLUE}[3/8] Luodaan trader-käyttäjä...${NC}"
if id "trader" &>/dev/null; then
    echo "Käyttäjä 'trader' on jo olemassa."
else
    adduser --disabled-password --gecos "" trader
    echo -e "${GREEN}✅ Käyttäjä 'trader' luotu${NC}"
fi

# 4. Konfiguroi firewall
echo -e "${BLUE}[4/8] Konfiguroidaan firewall...${NC}"
ufw --force enable
ufw allow 22/tcp
echo -e "${GREEN}✅ Firewall aktivoitu (SSH sallittu)${NC}"

# 5. Lisää swap-tila (jos ei ole)
echo -e "${BLUE}[5/8] Lisätään swap-tila...${NC}"
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo -e "${GREEN}✅ 2GB swap luotu${NC}"
else
    echo "Swap on jo olemassa."
fi

# 6. Vaihda trader-käyttäjäksi ja kloonaa repo
echo -e "${BLUE}[6/8] Kloonataan repository...${NC}"
su - trader << 'TRADER_SETUP'
    cd ~
    if [ -d "maatkatiimi" ]; then
        echo "Repository on jo kloonattu, päivitetään..."
        cd maatkatiimi
        git pull origin main
    else
        git clone https://github.com/Tsaicozi/maatkatiimi.git
        cd maatkatiimi
    fi
    
    # Luo virtual environment
    python3.10 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "✅ Python-ympäristö valmis"
TRADER_SETUP

# 7. Luo systemd service
echo -e "${BLUE}[7/8] Luodaan systemd service...${NC}"
cat > /etc/systemd/system/solana-trader.service << 'EOF'
[Unit]
Description=Solana Auto Trader Bot
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/home/trader/maatkatiimi
Environment="PATH=/home/trader/maatkatiimi/venv/bin"
ExecStart=/home/trader/maatkatiimi/venv/bin/python solana_auto_trader.py
Restart=always
RestartSec=60
StandardOutput=append:/home/trader/maatkatiimi/solana_auto_trader.log
StandardError=append:/home/trader/maatkatiimi/solana_auto_trader.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo -e "${GREEN}✅ Systemd service luotu${NC}"

# 8. Ohjeita
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Asennus valmis!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Seuraavat askeleet:${NC}"
echo ""
echo "1️⃣  Vaihda trader-käyttäjäksi:"
echo "   su - trader"
echo ""
echo "2️⃣  Siirry projektikansioon:"
echo "   cd maatkatiimi"
echo ""
echo "3️⃣  Konfiguroi .env2:"
echo "   nano .env2"
echo "   (Lisää PHANTOM_PRIVATE_KEY, TELEGRAM_TOKEN, jne.)"
echo ""
echo "4️⃣  Käynnistä botti (2 vaihtoehtoa):"
echo ""
echo "   A) Screen-sessio (yksinkertaisin):"
echo "      screen -S solana-trader"
echo "      source venv/bin/activate"
echo "      python solana_auto_trader.py"
echo "      # Poistu: CTRL+A, sitten D"
echo "      # Palaa: screen -r solana-trader"
echo ""
echo "   B) Systemd service (automaattinen restart):"
echo "      sudo systemctl start solana-trader"
echo "      sudo systemctl enable solana-trader"
echo "      sudo systemctl status solana-trader"
echo ""
echo "5️⃣  Seuraa lokeja:"
echo "   tail -f solana_auto_trader.log"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "${RED}⚠️  MUISTA:${NC}"
echo "   - Varmista että .env2 on konfiguroitu"
echo "   - Aloita pienellä POSITION_SIZE_SOL (0.01-0.02)"
echo "   - Seuraa ensimmäiset 24h tarkasti"
echo ""
echo -e "${GREEN}🚀 Onnea tradingiin!${NC}"
echo ""

