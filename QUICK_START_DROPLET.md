# ⚡ Pika-aloitus: Solana Trader DigitalOceanissa

## 3 minuutissa käyntiin! 🚀

### 1️⃣ Luo Droplet (2 min)
1. Mene [DigitalOcean](https://cloud.digitalocean.com/droplets/new)
2. Valitse:
   - **Ubuntu 22.04 LTS**
   - **Basic - $6/mo** (1GB RAM)
   - **Frankfurt** datacenter
3. **Create Droplet**
4. Kopioi IP-osoite

### 2️⃣ Yhdistä SSH:lla
```bash
ssh root@YOUR_DROPLET_IP
```

### 3️⃣ Aja Automaattinen Setup-skripti
```bash
curl -fsSL https://raw.githubusercontent.com/Tsaicozi/maatkatiimi/main/setup_droplet.sh | bash
```

**TAI** manuaalinen asennus:
```bash
# Päivitä
apt update && apt upgrade -y

# Asenna työkalut
apt install -y python3.10 python3.10-venv python3-pip git screen

# Luo käyttäjä
adduser --disabled-password --gecos "" trader
su - trader

# Kloonaa repo
git clone https://github.com/Tsaicozi/maatkatiimi.git
cd maatkatiimi

# Asenna riippuvuudet
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4️⃣ Konfiguroi .env2
```bash
nano .env2
```

Minimikonfiguraatio:
```env
# Solana
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
PHANTOM_PRIVATE_KEY=your_private_key_here

# Telegram
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading (aloita pienellä!)
POSITION_SIZE_SOL=0.02
MAX_POSITIONS=3
STOP_LOSS_PCT=-30
TAKE_PROFIT_PCT=50
MAX_HOLD_HOURS=48

# Filters
MIN_LIQUIDITY_USD=5000
MIN_24H_VOLUME_USD_SOLANA=10000
MAX_TOKEN_AGE_HOURS=24
```

Tallenna: `CTRL+O`, `ENTER`, `CTRL+X`

### 5️⃣ Käynnistä Botti
```bash
# Screen-sessio (suositeltu aloittelijoille)
screen -S solana-trader
source venv/bin/activate
python solana_auto_trader.py

# Poistu screenistä (botti jatkaa taustalla)
# Paina: CTRL+A, sitten D
```

### 6️⃣ Seuranta
```bash
# Palaa screen-sessioon
screen -r solana-trader

# TAI katso lokeja
tail -f /home/trader/maatkatiimi/solana_auto_trader.log
```

---

## 🎯 Tärkeät komennot

```bash
# Palaa trader-käyttäjäksi
su - trader

# Siirry projektikansioon
cd maatkatiimi

# Päivitä botti
git pull origin main
pip install -r requirements.txt

# Pysäytä botti (screen-sessiossa)
screen -r solana-trader
# Paina CTRL+C

# Käynnistä uudelleen
python solana_auto_trader.py

# Poistu screenistä
# CTRL+A, sitten D

# Katso kaikki screen-sessiot
screen -ls

# Tapa screen-sessio
screen -X -S solana-trader quit
```

---

## 💡 Pro-vinkit

### Automaattinen Restart (systemd)
Jos haluat että botti käynnistyy aina uudelleen kaatumisen jälkeen:

```bash
# Luo service
sudo nano /etc/systemd/system/solana-trader.service
```

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

```bash
# Aktivoi
sudo systemctl daemon-reload
sudo systemctl start solana-trader
sudo systemctl enable solana-trader

# Tarkista
sudo systemctl status solana-trader

# Lokit
journalctl -u solana-trader -f
```

### Lisää Swap-tila (jos muisti loppuu)
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Firewall (turvallisempi)
```bash
sudo ufw allow 22/tcp
sudo ufw enable
```

---

## 🚨 Ongelmanratkaisu

### Botti ei löydä tokeneita?
```bash
# Laske suodattimia .env2:ssa:
MIN_LIQUIDITY_USD=3000
MAX_TOKEN_AGE_HOURS=12
```

### "Out of memory"?
- Lisää swap-tila (yllä)
- TAI päivitä droplet 2GB RAM:iin ($12/mo)

### RPC-yhteysongelmat?
```bash
# Kokeile Helius RPC:tä (nopein):
SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY

# TAI Serum:
SOLANA_RPC_URL=https://solana-api.projectserum.com
```

### Botti kaatuu?
```bash
# Tarkista lokit
tail -n 100 solana_auto_trader.log | grep ERROR

# Käynnistä debug-tilassa
python solana_auto_trader.py --debug
```

---

## 📊 Mitä seurata?

### Ensimmäiset 24h:
- ✅ Löytääkö botti tokeneita? (Telegram-ilmoitukset)
- ✅ Avaako kauppoja? (check `solana_positions.json`)
- ✅ Sulkeeko kauppoja oikein? (TP/SL toimii)
- ✅ Onko virheitä lokeissa?

### Viikon jälkeen:
- 📈 Mikä on voitto/tappio-suhde?
- 💰 Paljonko keskimäärin voittaa/häviää per kauppa?
- ⏱️ Mikä on keskimääräinen pitoaika?
- 🎯 Mitkä tokenien ominaisuudet korreloivat voittoon?

---

## 💰 Kustannukset

| Komponentti | Hinta/kk |
|-------------|----------|
| DigitalOcean Droplet (1GB) | $6 |
| Helius RPC (ilmainen tier) | $0 |
| Telegram Bot | $0 |
| **YHTEENSÄ** | **$6/kk** |

**Eli halvempi kuin yksi kahvi! ☕**

---

## 🎉 Valmis!

Botti pyörii nyt 24/7 pilvipalvelimella ja:
- 🔍 Skannaa uudet Solana tokenit
- 💰 Avaa ja sulkee kauppoja automaattisesti
- 📱 Lähettää Telegram-ilmoitukset
- 💾 Tallentaa position state
- 🔄 Käynnistyy uudelleen kaatumisen jälkeen (systemd)

**Muista:**
- Aloita pienellä position sizella (0.01-0.02 SOL)
- Seuraa ensimmäiset 24h tarkasti
- Säädä parametreja tulosten perusteella
- Pidä private key turvassa!

**Onnea tradingiin! 🚀**

Kysymyksiä? Tarkista `DIGITALOCEAN_SOLANA_SETUP.md` yksityiskohtaisempia ohjeita varten.

