# 🌊 DigitalOcean Setup - Aloita Tästä!

## 📋 **VAIHE 1: Pakkaa Tiedostot**

Aja tämä lokaalilla koneellasi (macOS):

```bash
cd /Users/jarihiirikoski/matkatiimi

# Pakkaa kaikki tiedostot (ilman roskaa)
tar --exclude='*.log' \
    --exclude='*.jsonl' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.tar.gz' \
    --exclude='.env.backup*' \
    -czf helius-bot.tar.gz .

# Tarkista että pakkaus onnistui
ls -lh helius-bot.tar.gz
# Pitäisi näyttää esim: 245K tai vastaava
```

---

## 🌐 **VAIHE 2: Luo DigitalOcean Droplet**

1. **Kirjaudu:** https://cloud.digitalocean.com
2. **Create → Droplets**
3. **Valitse:**
   - **Image:** Ubuntu 22.04 LTS
   - **Plan:** Basic - Regular
   - **CPU options:** Regular ($6/mo tai $12/mo)
     - **$6/mo:** 1GB RAM, 1 vCPU, 25GB SSD ← **Riittää hyvin!**
   - **Region:** Frankfurt (FRA1) tai Amsterdam (AMS3)
   - **Authentication:** 
     - **SSH Key** (suositelluin) TAI
     - **Password** (helpompi aloittelijalle)
   - **Hostname:** `helius-scanner-bot`
4. **Create Droplet**
5. **Odota 60 sekuntia** - Droplet käynnistyy
6. **Kopioi IP-osoite** - Esim: `142.93.100.45`

---

## 🔌 **VAIHE 3: Yhdistä SSH:lla**

### **Jos valitsit SSH Key:**
```bash
ssh root@YOUR_DROPLET_IP
```

### **Jos valitsit Password:**
```bash
ssh root@YOUR_DROPLET_IP
# Syötä salasana (DigitalOcean lähetti sähköpostiin)
# Ensimmäisellä kerralla pyytää vaihtamaan salasanan
```

**Kun olet sisällä, pitäisi näkyä:**
```
Welcome to Ubuntu 22.04.x LTS
root@helius-scanner-bot:~#
```

---

## 📦 **VAIHE 4: Siirrä Tiedostot**

### **UUSI TERMINAALI-IKKUNA** (lokaalilla koneellasi):

```bash
# Siirrä pakkaus Dropletille
cd /Users/jarihiirikoski/matkatiimi
scp helius-bot.tar.gz root@YOUR_DROPLET_IP:/root/

# Esim:
# scp helius-bot.tar.gz root@142.93.100.45:/root/
```

**Syötä salasana jos kysyy.**

---

## 🛠️ **VAIHE 5: Asenna Dropletilla**

**Palaa SSH terminaaliin (Dropletilla):**

```bash
# Päivitä järjestelmä
apt update && apt upgrade -y

# Asenna Python ja työkalut
apt install -y python3.11 python3.11-venv python3-pip git curl nano htop

# Luo hakemisto ja pura tiedostot
mkdir -p /root/matkatiimi
cd /root
tar -xzf helius-bot.tar.gz -C /root/matkatiimi
cd /root/matkatiimi

# Luo virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Asenna riippuvuudet
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🔐 **VAIHE 6: Luo .env Tiedosto**

**Dropletilla:**

```bash
cd /root/matkatiimi
nano .env
```

**KOPIOI TÄMÄ POHJA JA TÄYTÄ OMAT ARVOT:**

```bash
# Helius
HELIUS_API_KEY=6e64d1b6-eead-47c8-9150-2b1d80c3b92a
SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=6e64d1b6-eead-47c8-9150-2b1d80c3b92a

# Telegram (KORVAA OMAT ARVOT!)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-1001234567890

# Trading
AUTO_TRADE=1
DRY_RUN=0
TRADE_MAX_USD=20
TRADE_MIN_SCORE=50
TRADE_MIN_LIQ_USD=10000.0
TRADE_UTIL_MIN=0.35
TRADE_UTIL_MAX=6.0
TRADE_COOLDOWN_SEC=120
TRADE_REQUIRE_CAN_SELL=1
SOL_PRICE_FALLBACK=208
TRADE_SLIPPAGE_BPS=150
TRADE_PRIORITY_FEE_U=200000
TRADE_CU_LIMIT=600000
TRADE_TP_PCT=25.0
TRADE_SL_PCT=20.0

# Wallet - TÄRKEÄ! (KORVAA OMA PRIVATE KEY!)
TRADER_PRIVATE_KEY_HEX=your_64_byte_hex_private_key_here

# CoinGecko (KORVAA OMA KEY!)
COINGECKO_API_KEY=your_coingecko_api_key

# Solana Programs
SPL_TOKEN22_PROGRAM=TokenzQdBNbLqP5VEhGz1vK5ja2V21w8bJ5vYvGphL9u
RAYDIUM_AMM_PROGRAM=RVKd61ztZW9yK21G4xMqi6nG5iG6JdzDyxN1q6i1dV4
RAYDIUM_CLMM_PROGRAM=CAMMCzo5YL8CKqQCDx9hcQzYbx8jG9LXNhtzK1Zx6UeD
ORCA_WHIRLPOOLS_PROGRAM=whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc
PUMP_FUN_PROGRAM=6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P

# Scanner
SCANNER_ENABLE_RAYDIUM_WATCHER=true
SCANNER_RAYDIUM_QUOTES=SOL,USDC,USDT
SCANNER_RAYDIUM_MIN_QUOTE_USD=5000

# API Keys (jos sinulla on)
BIRDEYE_API_KEY=
DEXSCREENER_API_KEY=
```

**Tallenna:** `Ctrl+O` → `Enter` → `Ctrl+X`

**🔒 MUISTA KORVATA:**
- `TELEGRAM_BOT_TOKEN` - Oma bot token
- `TELEGRAM_CHAT_ID` - Oma chat ID
- `TRADER_PRIVATE_KEY_HEX` - Oma private key (64 tavua hex)
- `COINGECKO_API_KEY` - Oma CoinGecko key

---

## ✅ **VAIHE 7: Testaa Botti**

```bash
cd /root/matkatiimi
source venv/bin/activate
python3 run_helius_scanner.py
```

**Odota 5-10 sekuntia ja tarkista:**
- ✅ Ei ERROR viestejä
- ✅ Näkyy: `✅ Real Telegram bot initialized`
- ✅ **TARKISTA TELEGRAM** - Wallet report pitäisi tulla!

**Jos toimii, paina `Ctrl+C`**

---

## 🚀 **VAIHE 8: Luo systemd Service**

```bash
# Luo service tiedosto
cat > /etc/systemd/system/helius-scanner.service << 'EOF'
[Unit]
Description=Helius Token Scanner Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/matkatiimi
Environment="PATH=/root/matkatiimi/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/root/matkatiimi/venv/bin/python3 run_helius_scanner.py
Restart=always
RestartSec=10
StandardOutput=append:/root/matkatiimi/helius_scanner.log
StandardError=append:/root/matkatiimi/helius_scanner_error.log
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# Käynnistä service
systemctl daemon-reload
systemctl enable helius-scanner
systemctl start helius-scanner

# Tarkista status
systemctl status helius-scanner
```

**Pitäisi näyttää:** `active (running)` vihreällä!

---

## 📊 **VAIHE 9: Seuraa Lokeja**

```bash
# Reaaliaikaiset lokit
tail -f /root/matkatiimi/helius_scanner.log

# Tai systemd lokit
journalctl -u helius-scanner -f

# Paina Ctrl+C lopettaaksesi seurannan
```

---

## ✅ **VALMIS! Botti Ajaa Nyt 24/7!**

### **Tarkista:**

1. **Telegram:**
   - Wallet report tuli? ✅
   - Token löydöt alkavat tulla? ✅

2. **Health check:**
   ```bash
   curl http://localhost:9109/health
   ```

3. **Trading status:**
   ```bash
   curl http://localhost:9109/trading
   ```

---

## 🔄 **HYÖDYLLISET KOMENNOT:**

```bash
# Uudelleenkäynnistä botti
systemctl restart helius-scanner

# Pysäytä botti
systemctl stop helius-scanner

# Katso status
systemctl status helius-scanner

# Katso lokeja
tail -100 /root/matkatiimi/helius_scanner.log

# Etsi kauppoja
grep "auto_trade" /root/matkatiimi/helius_scanner.log

# Etsi Telegram viestejä
grep "Telegram" /root/matkatiimi/helius_scanner.log
```

---

## 🆘 **APUA TARVITSET?**

**Kerro minulle missä kohdassa olet ja autan!** 😊

Seuraavaksi: **Aja VAIHE 1** (pakkaa tiedostot) ja kerro kun olet valmis!

