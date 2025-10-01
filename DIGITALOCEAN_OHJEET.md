# 🌊 DigitalOcean Deployment - Helius Scanner Bot

## 📋 **Vaihe 1: Luo Droplet (Jos ei ole vielä)**

Jos sinulla on jo Droplet, hyppää suoraan **Vaihe 2**.

1. **DigitalOcean Console** → Create → Droplets
2. **Image:** Ubuntu 22.04 LTS
3. **Plan:** Basic - Regular ($6/mo tai $12/mo)
   - **Minimum:** 1GB RAM / 1 vCPU (RIITTÄÄ!)
4. **Region:** Frankfurt / Amsterdam (lähellä Eurooppaa, matala latenssi)
5. **Authentication:** SSH Key (suositelluin) TAI Password
6. **Hostname:** `helius-scanner-bot`
7. **Create Droplet**

---

## 🔌 **Vaihe 2: Yhdistä SSH:lla**

```bash
# Lokaalilla koneellasi (macOS):
ssh root@YOUR_DROPLET_IP

# Esim:
ssh root@142.93.100.45
```

**Jos kysyy salasanaa ja sinulla on SSH key:**
```bash
ssh -i ~/.ssh/your_key root@YOUR_DROPLET_IP
```

---

## 🛠️ **Vaihe 3: Päivitä Järjestelmä & Asenna Python**

```bash
# Päivitä paketit
apt update && apt upgrade -y

# Asenna Python 3.11 ja työkalut
apt install -y python3.11 python3.11-venv python3-pip git curl nano

# Tarkista Python versio
python3.11 --version
# Pitäisi näyttää: Python 3.11.x
```

---

## 📁 **Vaihe 4: Siirrä Koodi Dropletille**

### **Vaihtoehto A: SCP (Suora kopiointi - NOPEIN!)**

```bash
# Lokaalilla koneellasi (UUSI TERMINAALI-IKKUNA):
cd /Users/jarihiirikoski/matkatiimi

# Luo pakkaus (ilman logeja ja väliaikaisuuksia)
tar --exclude='*.log' \
    --exclude='*.jsonl' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    -czf helius-bot.tar.gz .

# Siirrä palvelimelle
scp helius-bot.tar.gz root@YOUR_DROPLET_IP:/root/

# Palaa SSH sessioosi ja pura:
# (SSH terminaalissa Dropletilla:)
cd /root
tar -xzf helius-bot.tar.gz -C /root/matkatiimi
cd /root/matkatiimi
```

### **Vaihtoehto B: Git (Jos sinulla on private repo)**

```bash
# Dropletilla (SSH sessio):
cd /root
git clone https://github.com/YOUR_USERNAME/matkatiimi.git
cd matkatiimi
```

---

## 🔐 **Vaihe 5: Luo .env Tiedosto Dropletilla**

```bash
# Dropletilla:
cd /root/matkatiimi
nano .env
```

**Kopioi KAIKKI tämä sisältö .env tiedostoon:**

```bash
# Helius
HELIUS_API_KEY=6e64d1b6-eead-47c8-9150-2b1d80c3b92a
SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=6e64d1b6-eead-47c8-9150-2b1d80c3b92a

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Trading
AUTO_TRADE=1
DRY_RUN=0
TRADE_MAX_USD=20
TRADE_SLIPPAGE_BPS=150
TRADE_PRIORITY_FEE_U=200000
TRADE_CU_LIMIT=600000
TRADE_MIN_SCORE=50
TRADE_MIN_LIQ_USD=10000.0
TRADE_UTIL_MIN=0.35
TRADE_UTIL_MAX=6.0
TRADE_COOLDOWN_SEC=120
TRADE_REQUIRE_CAN_SELL=1
TRADE_TP_PCT=25.0
TRADE_SL_PCT=20.0
SOL_PRICE_FALLBACK=208

# Wallet (TÄRKEÄ!)
TRADER_PRIVATE_KEY_HEX=your_private_key_here_64_bytes_hex

# CoinGecko
COINGECKO_API_KEY=your_coingecko_key

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
```

**Tallenna:** `Ctrl+O` → `Enter` → `Ctrl+X`

**🔒 HUOM:** Korvaa `your_bot_token_here`, `your_private_key_here` jne. oikeilla arvoilla lokaalista `.env` tiedostostasi!

---

## 📦 **Vaihe 6: Asenna Python Riippuvuudet**

```bash
# Dropletilla:
cd /root/matkatiimi

# Luo virtual environment
python3.11 -m venv venv

# Aktivoi venv
source venv/bin/activate

# Päivitä pip
pip install --upgrade pip

# Asenna riippuvuudet
pip install -r requirements.txt

# Tarkista että asennus onnistui
pip list
```

---

## ✅ **Vaihe 7: Testaa Botti**

```bash
# Dropletilla (venv aktivoituna):
cd /root/matkatiimi
python3 run_helius_scanner.py
```

**Odota 5-10 sekuntia ja tarkista:**
- ✅ Ei error viestejä
- ✅ Näkyy: `✅ Real Telegram bot initialized`
- ✅ Näkyy: `💰 Wallet report worker started`
- ✅ **TARKISTA TELEGRAM** - Pitäisi tulla wallet report!

**Jos toimii, paina `Ctrl+C` ja jatka seuraavaan vaiheeseen.**

---

## 🔄 **Vaihe 8: Luo systemd Service (24/7 ajo)**

### **A) Luo service tiedosto:**

```bash
# Dropletilla:
sudo nano /etc/systemd/system/helius-scanner.service
```

**Kopioi tämä sisältö:**

```ini
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

# Limits
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

**Tallenna:** `Ctrl+O` → `Enter` → `Ctrl+X`

### **B) Käynnistä Service:**

```bash
# Lataa systemd konfiguraatio uudelleen
sudo systemctl daemon-reload

# Käynnistä botti
sudo systemctl start helius-scanner

# Tarkista status
sudo systemctl status helius-scanner

# Pitäisi näyttää: "active (running)" vihreällä!

# Aktivoi automaattinen käynnistys bootissa
sudo systemctl enable helius-scanner
```

---

## 📊 **Vaihe 9: Seuraa Lokeja**

```bash
# Reaaliaikaiset lokit
tail -f /root/matkatiimi/helius_scanner.log

# Viimeiset 100 riviä
tail -100 /root/matkatiimi/helius_scanner.log

# Virhelokit
tail -f /root/matkatiimi/helius_scanner_error.log

# systemd lokit
journalctl -u helius-scanner -f

# Etsi auto-trade tapahtumia
tail -f /root/matkatiimi/helius_scanner.log | grep "auto_trade"
```

---

## 🔧 **Hyödylliset Komennot**

### **Botti hallinta:**
```bash
# Pysäytä botti
sudo systemctl stop helius-scanner

# Käynnistä botti
sudo systemctl start helius-scanner

# Uudelleenkäynnistä
sudo systemctl restart helius-scanner

# Tarkista status
sudo systemctl status helius-scanner

# Poista automaattinen käynnistys
sudo systemctl disable helius-scanner
```

### **Päivitä koodi:**
```bash
# Pysäytä botti
sudo systemctl stop helius-scanner

# Päivitä tiedostot
cd /root/matkatiimi

# Jos käytät Git:
git pull

# Jos käytät SCP:
# Lokaalilla koneellasi:
scp -r /Users/jarihiirikoski/matkatiimi/*.py root@YOUR_DROPLET_IP:/root/matkatiimi/

# Dropletilla, käynnistä botti uudelleen:
sudo systemctl start helius-scanner
```

### **Monitorointi:**
```bash
# CPU & RAM käyttö
htop

# Levytila
df -h

# Network
netstat -tuln | grep -E "(8001|9109)"

# Prosessit
ps aux | grep python
```

---

## 🔥 **Firewall (Valinnainen mutta Suositeltava)**

```bash
# Asenna UFW
apt install -y ufw

# Salli SSH
ufw allow 22/tcp

# Salli Prometheus & Health endpoints (valinnainen)
ufw allow 8001/tcp
ufw allow 9109/tcp

# Aktivoi firewall
ufw enable

# Tarkista status
ufw status
```

---

## 🆘 **Ongelmanratkaisu**

### **Botti ei käynnisty:**
```bash
# Tarkista lokit
journalctl -u helius-scanner -n 50

# Tarkista että venv on oikein
ls -la /root/matkatiimi/venv/bin/python3

# Testaa manuaalisesti
cd /root/matkatiimi
source venv/bin/activate
python3 run_helius_scanner.py
```

### **Ei Telegram viestejä:**
```bash
# Tarkista .env
cat /root/matkatiimi/.env | grep TELEGRAM

# Testaa Telegram yhteys
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"
```

### **Muistin loppuminen:**
```bash
# Tarkista RAM
free -h

# Jos RAM loppuu, lisää swap:
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## 📈 **Optimoinnit Tuotantoa Varten**

### **1. Log Rotation:**
```bash
sudo nano /etc/logrotate.d/helius-scanner
```

```
/root/matkatiimi/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        systemctl reload helius-scanner > /dev/null 2>&1 || true
    endscript
}
```

### **2. Automatic Updates (Valinnainen):**
```bash
# Asenna unattended-upgrades
apt install -y unattended-upgrades

# Aktivoi security updates
dpkg-reconfigure -plow unattended-upgrades
```

### **3. Monitoring (UptimeRobot - Ilmainen):**
1. Mene: https://uptimerobot.com
2. Add New Monitor:
   - Type: HTTP(s)
   - URL: `http://YOUR_DROPLET_IP:9109/health`
   - Interval: 5 minutes
3. Saat sähköpostin jos botti kaatuu!

---

## 🎯 **TÄYDELLINEN KOMENTO SARJA (Kopioi & Liitä)**

```bash
# === DROPLETILLA (SSH sessio) ===

# 1. Päivitä järjestelmä
apt update && apt upgrade -y

# 2. Asenna Python ja työkalut
apt install -y python3.11 python3.11-venv python3-pip git curl nano htop

# 3. Luo hakemisto
mkdir -p /root/matkatiimi
cd /root/matkatiimi

# === PYSÄHDY TÄSSÄ ===
# Nyt siirrä tiedostot lokaalilta koneelta (katso alla)
```

---

## 📤 **Tiedostojen Siirto (Lokaalilla Koneellasi)**

```bash
# === LOKAALILLA KONEELLASI (macOS) ===

cd /Users/jarihiirikoski/matkatiimi

# Pakkaa tiedostot (ilman roskaa)
tar --exclude='*.log' \
    --exclude='*.jsonl' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='helius-bot.tar.gz' \
    -czf helius-bot.tar.gz .

# Siirrä palvelimelle (KORVAA YOUR_DROPLET_IP!)
scp helius-bot.tar.gz root@YOUR_DROPLET_IP:/root/

# === PALAA DROPLET SSH SESSIOON ===
```

---

## 📦 **Jatka Dropletilla**

```bash
# === DROPLETILLA (SSH sessio) ===

# Pura tiedostot
cd /root
tar -xzf helius-bot.tar.gz -C /root/matkatiimi
cd /root/matkatiimi

# Luo virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Asenna riippuvuudet
pip install --upgrade pip
pip install -r requirements.txt

# Luo/muokkaa .env tiedostoa
nano .env
# KOPIOI KAIKKI .ENV SISÄLTÖ LOKAALISTA TIEDOSTOSTASI!
# HUOM: Korvaa oikeat arvot (API keys, private key, jne.)
# Tallenna: Ctrl+O, Enter, Ctrl+X

# Testaa botti
python3 run_helius_scanner.py
# Odota 5-10 sekuntia
# Tarkista Telegram että tulee wallet report!
# Jos toimii, paina Ctrl+C
```

---

## 🚀 **Luo systemd Service**

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
systemctl start helius-scanner
systemctl enable helius-scanner

# Tarkista status
systemctl status helius-scanner

# Katso lokeja
tail -f /root/matkatiimi/helius_scanner.log
```

---

## ✅ **VALMIS! Botti Ajaa 24/7!**

### **Tarkista että kaikki toimii:**

1. **Telegram:**
   - ✅ Wallet report tuli (5 sek sisällä)
   - ✅ Token löydöt alkavat tulla

2. **Health Check:**
   ```bash
   curl http://localhost:9109/health
   curl http://localhost:9109/trading
   ```

3. **Lokit:**
   ```bash
   tail -20 /root/matkatiimi/helius_scanner.log
   ```

---

## 🔄 **Päivitä Botti (Tulevaisuudessa)**

```bash
# === LOKAALILLA KONEELLASI ===
cd /Users/jarihiirikoski/matkatiimi

# Tee muutokset koodiin
# ...

# Pakkaa ja lähetä
tar --exclude='*.log' --exclude='*.jsonl' --exclude='venv' --exclude='__pycache__' -czf helius-bot.tar.gz .
scp helius-bot.tar.gz root@YOUR_DROPLET_IP:/root/

# === DROPLETILLA ===
cd /root
systemctl stop helius-scanner
tar -xzf helius-bot.tar.gz -C /root/matkatiimi
cd /root/matkatiimi
source venv/bin/activate
pip install -r requirements.txt
systemctl start helius-scanner

# Tarkista lokit
tail -f /root/matkatiimi/helius_scanner.log
```

---

## 💡 **VINKIT:**

### **Screen/Tmux (Jos haluat käsiseurantaa):**
```bash
# Asenna screen
apt install -y screen

# Käynnistä screen sessio
screen -S helius-bot

# Aja botti
cd /root/matkatiimi
source venv/bin/activate
python3 run_helius_scanner.py

# Irrota screen: Ctrl+A, D
# Liity takaisin: screen -r helius-bot
```

### **Disk Space Seuranta:**
```bash
# Tarkista levytila
df -h

# Tyhjennä vanhat lokit
rm /root/matkatiimi/*.log.old
```

---

## 🎯 **PIKA-CHEAT SHEET:**

```bash
# Yhdistä
ssh root@YOUR_DROPLET_IP

# Katso lokeja
tail -f /root/matkatiimi/helius_scanner.log

# Uudelleenkäynnistä
systemctl restart helius-scanner

# Tarkista status
systemctl status helius-scanner

# Katso virhelokit
tail -f /root/matkatiimi/helius_scanner_error.log
```

---

**Botti on nyt pilvessä ja ajaa 24/7! Koneen sammuminen tai verkon katkeilu ei enää vaikuta!** 🚀☁️

Haluatko että autan yhdistämään Dropletiin ja suorittamaan asennuksen yhdessä? 😊

