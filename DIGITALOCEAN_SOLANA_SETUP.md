# 🚀 Solana Auto Trader - DigitalOcean Droplet Setup

## Vaihtoehto 1: Nopea Setup (Suositeltu)

### 1️⃣ Luo Droplet
1. Kirjaudu [DigitalOcean](https://cloud.digitalocean.com/)
2. **Create → Droplets**
3. Valitse:
   - **Image:** Ubuntu 22.04 LTS
   - **Size:** Basic - $6/mo (1GB RAM, 1 vCPU) riittää
   - **Datacenter:** Frankfurt (lähinnä)
   - **Authentication:** SSH key (tai Password)
4. Nimeä: `solana-trader`
5. **Create Droplet**

### 2️⃣ Yhdistä Dropletiin
```bash
ssh root@YOUR_DROPLET_IP
```

### 3️⃣ Asenna Riippuvuudet
```bash
# Päivitä järjestelmä
apt update && apt upgrade -y

# Asenna Python 3.10+
apt install -y python3.10 python3.10-venv python3-pip git

# Asenna screen (jotta botti jatkaa taustalla)
apt install -y screen
```

### 4️⃣ Kloonaa Repository
```bash
# Luo käyttäjä botille (turvallisempi kuin root)
adduser --disabled-password --gecos "" trader
su - trader

# Kloonaa repo
git clone https://github.com/Tsaicozi/maatkatiimi.git
cd maatkatiimi
```

### 5️⃣ Luo Virtual Environment
```bash
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6️⃣ Konfiguroi .env2
```bash
nano .env2
```

Lisää:
```env
# Solana RPC
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
HELIUS_API_KEY=your_helius_key_here

# Phantom Wallet
PHANTOM_PRIVATE_KEY=your_private_key_here

# Telegram
TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Parameters
POSITION_SIZE_SOL=0.05
MAX_POSITIONS=3
STOP_LOSS_PCT=-30
TAKE_PROFIT_PCT=50
MAX_HOLD_HOURS=48

# Filters
MIN_LIQUIDITY_USD=5000
MIN_24H_VOLUME_USD_SOLANA=10000
MAX_TOKEN_AGE_HOURS=24
MAX_SLIPPAGE_BPS=500

# State Files
SOLANA_POSITIONS_FILE=solana_positions.json
SOLANA_COOLDOWN_FILE=solana_cooldown.json
```

Tallenna: `CTRL+O`, `ENTER`, `CTRL+X`

### 7️⃣ Käynnistä Botti Screen-Sessiossa
```bash
# Luo screen-sessio
screen -S solana-trader

# Aktivoi venv ja käynnistä
source venv/bin/activate
python solana_auto_trader.py

# Poistu screenistä (botti jatkaa taustalla)
# Paina: CTRL+A, sitten D
```

### 8️⃣ Seuranta
```bash
# Palaa screen-sessioon
screen -r solana-trader

# Katso lokit
tail -f solana_auto_trader.log

# Listaa kaikki screen-sessiot
screen -ls
```

---

## Vaihtoehto 2: Systemd Service (Automaattinen uudelleenkäynnistys)

### 1️⃣ Luo Service-tiedosto
```bash
sudo nano /etc/systemd/system/solana-trader.service
```

Lisää:
```ini
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
```

### 2️⃣ Aktivoi ja Käynnistä
```bash
# Lataa service
sudo systemctl daemon-reload

# Käynnistä
sudo systemctl start solana-trader

# Käynnisty automaattisesti bootissa
sudo systemctl enable solana-trader

# Tarkista status
sudo systemctl status solana-trader
```

### 3️⃣ Hallinta
```bash
# Pysäytä
sudo systemctl stop solana-trader

# Käynnistä uudelleen
sudo systemctl restart solana-trader

# Katso lokit
journalctl -u solana-trader -f
```

---

## 📊 Seuranta ja Ylläpito

### Lokit
```bash
# Reaaliaikaiset lokit
tail -f /home/trader/maatkatiimi/solana_auto_trader.log

# Viimeiset 100 riviä
tail -n 100 /home/trader/maatkatiimi/solana_auto_trader.log

# Etsi virheitä
grep "ERROR" /home/trader/maatkatiimi/solana_auto_trader.log
```

### Position State
```bash
# Katso nykyiset positiot
cat /home/trader/maatkatiimi/solana_positions.json | python -m json.tool

# Katso cooldown-lista
cat /home/trader/maatkatiimi/solana_cooldown.json | python -m json.tool
```

### Git Update (päivitä botti)
```bash
cd /home/trader/maatkatiimi
git pull origin main
source venv/bin/activate
pip install -r requirements.txt

# Jos käytät screeniä:
screen -r solana-trader
# Pysäytä: CTRL+C
# Käynnistä uudelleen: python solana_auto_trader.py

# Jos käytät systemd:
sudo systemctl restart solana-trader
```

---

## 🔒 Turvallisuus

### Firewall (UFW)
```bash
# Asenna ja aktivoi
sudo apt install -y ufw

# Salli SSH
sudo ufw allow 22/tcp

# Aktivoi
sudo ufw enable

# Tarkista status
sudo ufw status
```

### SSH Key -autentikointi
```bash
# Poista salasana-kirjautuminen käytöstä
sudo nano /etc/ssh/sshd_config
# Muuta: PasswordAuthentication no
sudo systemctl restart sshd
```

### Automaattiset Päivitykset
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 💰 Kustannukset

| Droplet Size | RAM | vCPU | SSD | Hinta/kk |
|--------------|-----|------|-----|----------|
| Basic        | 1GB | 1    | 25GB| $6       |
| Basic        | 2GB | 1    | 50GB| $12      |
| Basic        | 4GB | 2    | 80GB| $24      |

**Suositus:** 1GB riittää hyvin tälle botille (ei raskas datankäsittely).

---

## 🚨 Yleisiä Ongelmia

### "Out of Memory"
```bash
# Lisää swap-tila
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### "Connection refused" (RPC)
- Tarkista `SOLANA_RPC_URL` .env2:ssa
- Kokeile vaihtoehtoisia RPC:itä:
  - `https://api.mainnet-beta.solana.com`
  - `https://solana-api.projectserum.com`
  - Helius RPC (nopein)

### Botti ei löydä tokeneita
- Tarkista `MAX_TOKEN_AGE_HOURS` (laske 12h → 6h)
- Tarkista `MIN_LIQUIDITY_USD` (laske 5000 → 3000)
- Katso debug-lokit

---

## 📈 Monitoring

### Yksinkertainen Health Check
```bash
# Luo simple health check script
cat > /home/trader/check_health.sh << 'EOF'
#!/bin/bash
if ! pgrep -f "solana_auto_trader.py" > /dev/null; then
    echo "Bot is DOWN! Restarting..."
    cd /home/trader/maatkatiimi
    source venv/bin/activate
    nohup python solana_auto_trader.py &
fi
EOF

chmod +x /home/trader/check_health.sh

# Lisää crontab (tarkista joka 5 min)
(crontab -l 2>/dev/null; echo "*/5 * * * * /home/trader/check_health.sh") | crontab -
```

### Telegram Status Alert
Botti lähettää jo automaattisesti:
- ✅ Uudet entry-signaalit
- 💰 Kauppojen sulkemiset (TP/SL/Time)
- ⚠️ Virheet

---

## 🎯 Suositellut Seuraavat Askeleet

1. **Käynnistä pienellä position sizella** (0.01-0.02 SOL)
2. **Seuraa 24h** ja tarkista että kaikki toimii
3. **Nosta position size** jos tulokset hyviä
4. **Lisää SOL lompakkoon** tarpeen mukaan
5. **Backup private key** turvalliseen paikkaan (1Password, USB)

---

## 📞 Tuki

Jos ongelmia:
1. Tarkista lokit: `tail -f solana_auto_trader.log`
2. Tarkista RPC-yhteys: `curl -X POST $SOLANA_RPC_URL`
3. Testaa manuaalisesti: `python solana_token_scanner.py`
4. Telegram-ilmoitukset kertovat reaaliajassa ongelmista

**Valmis! Botti pyörii nyt 24/7 pilvipalvelimella.** 🚀

