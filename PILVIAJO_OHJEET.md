# 🚀 Helius Scanner Bot - Pilviajo Ohjeet

Botti pysäytetty onnistuneesti! Tässä ohjeet botin ajamiseen pilvessä 24/7.

---

## 📋 **Vaihtoehto 1: AWS EC2 (Suositelluin)**

### **Edut:**
- ✅ Luotettava 99.99% uptime
- ✅ Edullinen ($5-10/kk)
- ✅ Täysi kontrolli
- ✅ Helppo ylläpitää

### **Asennus:**

#### 1. **Luo AWS Tili & EC2 Instanssi**
```bash
# AWS Console → EC2 → Launch Instance
# - Valitse: Ubuntu 22.04 LTS
# - Tyyppi: t3.micro (1 vCPU, 1GB RAM) - RIITTÄÄ!
# - Storage: 8GB
# - Security Group: Avaa portit 8001, 9109 (Prometheus & Health)
```

#### 2. **Yhdistä SSH:lla**
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

#### 3. **Asenna Python & Riippuvuudet**
```bash
# Päivitä pakettilista
sudo apt update && sudo apt upgrade -y

# Asenna Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip git

# Kloonaa repo tai siirrä tiedostot
# Vaihtoehto A: Git (JOS sinulla on private repo)
git clone https://github.com/your-username/matkatiimi.git
cd matkatiimi

# Vaihtoehto B: SCP (kopioi lokaalista koneesta)
# Lokaalilla koneellasi:
scp -i your-key.pem -r /Users/jarihiirikoski/matkatiimi ubuntu@your-ec2-ip:~/
```

#### 4. **Luo Virtual Environment & Asenna Riippuvuudet**
```bash
cd matkatiimi
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Asenna kaikki riippuvuudet
pip install aiohttp websockets python-dotenv prometheus-client solders solana base58
```

#### 5. **Kopioi .env Tiedosto Turvallisesti**
```bash
# Lokaalilla koneellasi:
scp -i your-key.pem /Users/jarihiirikoski/matkatiimi/.env ubuntu@your-ec2-ip:~/matkatiimi/

# TAI luo .env tiedosto suoraan EC2:lla:
nano .env
# Kopioi kaikki ympäristömuuttujat (API avaimet, private key, jne.)
```

#### 6. **Testaa Botti**
```bash
cd ~/matkatiimi
source venv/bin/activate
python3 run_helius_scanner.py
# Paina Ctrl+C jos toimii
```

#### 7. **Asenna systemd Service (24/7 ajo)**
```bash
# Luo service tiedosto
sudo nano /etc/systemd/system/helius-scanner.service
```

**Sisältö:**
```ini
[Unit]
Description=Helius Token Scanner Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/matkatiimi
Environment="PATH=/home/ubuntu/matkatiimi/venv/bin:/usr/bin"
ExecStart=/home/ubuntu/matkatiimi/venv/bin/python3 run_helius_scanner.py
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/matkatiimi/helius_scanner.log
StandardError=append:/home/ubuntu/matkatiimi/helius_scanner_error.log

[Install]
WantedBy=multi-user.target
```

#### 8. **Käynnistä Service**
```bash
# Lataa uudelleen systemd
sudo systemctl daemon-reload

# Käynnistä botti
sudo systemctl start helius-scanner

# Tarkista status
sudo systemctl status helius-scanner

# Aktivoi automaattinen käynnistys bootissa
sudo systemctl enable helius-scanner

# Katso lokeja reaaliajassa
tail -f ~/matkatiimi/helius_scanner.log
```

#### 9. **Hyödylliset Komennot**
```bash
# Pysäytä botti
sudo systemctl stop helius-scanner

# Uudelleenkäynnistä
sudo systemctl restart helius-scanner

# Katso viimeisimmät lokit
journalctl -u helius-scanner -n 100 -f

# Päivitä koodi (jos teit muutoksia)
cd ~/matkatiimi
git pull  # TAI scp päivitetyt tiedostot
sudo systemctl restart helius-scanner
```

---

## 📋 **Vaihtoehto 2: DigitalOcean Droplet**

### **Edut:**
- ✅ Helpompi UI kuin AWS
- ✅ Kiinteä hinta ($6/kk)
- ✅ Hyvä aloittelijoille

### **Asennus:**

1. **Luo Droplet:**
   - OS: Ubuntu 22.04 LTS
   - Plan: Basic ($6/kk)
   - Region: Frankfurt/Amsterdam (lähellä Eurooppaa)

2. **Seuraa samoja ohjeita kuin AWS EC2** (kohdat 2-9)

---

## 📋 **Vaihtoehto 3: Railway.app (Helpoin!)**

### **Edut:**
- ✅ **HELPOIN** - ei tarvitse SSH:ta
- ✅ Ilmainen $5/kk kreditti
- ✅ Automaattiset deploymentit
- ⚠️ Kalliimpi ($10-20/kk)

### **Asennus:**

1. **Luo Railway Tili:** https://railway.app
2. **Luo Uusi Projekti:**
   - "New Project" → "Deploy from GitHub repo"
   - TAI "Empty Project" → "Deploy from Local"

3. **Lisää .env Muuttujat:**
   - Settings → Variables
   - Kopioi kaikki .env sisältö (API avaimet, private key, jne.)

4. **Luo `Procfile`:**
```bash
# Lokaalilla koneellasi:
cd /Users/jarihiirikoski/matkatiimi
echo "web: python3 run_helius_scanner.py" > Procfile
```

5. **Luo `requirements.txt`:**
```bash
echo "aiohttp
websockets
python-dotenv
prometheus-client
solders
solana
base58" > requirements.txt
```

6. **Deploy:**
   - Railway detektoi automaattisesti Python projektin
   - Se asentaa riippuvuudet `requirements.txt`:stä
   - Se ajaa `Procfile`:n

7. **Katso Lokeja:**
   - Railway UI → Deployments → Logs

---

## 📋 **Vaihtoehto 4: Docker + DigitalOcean/AWS**

### **Edut:**
- ✅ Helppo siirtää palvelimelta toiselle
- ✅ Yhdenmukainen ympäristö
- ✅ Helppo päivittää

### **Asennus:**

1. **Luo `Dockerfile`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Kopioi tiedostot
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Aja botti
CMD ["python3", "run_helius_scanner.py"]
```

2. **Luo `docker-compose.yml`:**
```yaml
version: '3.8'
services:
  helius-scanner:
    build: .
    restart: always
    env_file: .env
    ports:
      - "8001:8001"
      - "9109:9109"
    volumes:
      - ./logs:/app/logs
```

3. **Käynnistä:**
```bash
docker-compose up -d
docker-compose logs -f
```

---

## 🔒 **TURVALLISUUS - TÄRKEÄÄ!**

### **Private Key Suojaus:**

**ÄLÄ KOSKAAN:**
- ❌ Committaa `.env` tiedostoa GitHubiin
- ❌ Jaa private keytä kenellekään
- ❌ Tallenna private keytä selkotekstinä

**SUOSITUS:**
1. **Käytä AWS Secrets Manager tai Railway Variables**
2. **Luo uusi lompakko vain botille** (älä käytä pääsalkku)
3. **Pidä vain pieni määrä SOL:ia** (esim. 1-2 SOL)
4. **Seuraa saldoa 2h välein** (Telegram raportit)

---

## 📊 **Monitorointi Pilvessä**

### **Health Check:**
```bash
curl http://your-server-ip:9109/health
curl http://your-server-ip:9109/trading
```

### **Prometheus Metrics:**
```bash
curl http://your-server-ip:8001/metrics
```

### **Uptime Monitoring (Ilmainen):**
- **UptimeRobot:** https://uptimerobot.com
  - Seuraa `/health` endpointia 5 min välein
  - Lähettää sähköpostin jos botti kaatuu

---

## 💰 **HINTA-ARVIO:**

| Palvelu | Hinta/kk | Vaikeus | Suositus |
|---------|----------|---------|----------|
| **AWS EC2 t3.micro** | $8-10 | Keskivaikea | ⭐⭐⭐⭐⭐ Paras! |
| **DigitalOcean Droplet** | $6 | Helppo | ⭐⭐⭐⭐ |
| **Railway.app** | $10-20 | Erittäin helppo | ⭐⭐⭐ |
| **VPS (Hetzner)** | €4 | Keskivaikea | ⭐⭐⭐⭐ |

---

## 🚀 **NOPEIN TAPA (Railway.app):**

```bash
# 1. Luo tiedostot
cd /Users/jarihiirikoski/matkatiimi

# 2. Luo requirements.txt
cat > requirements.txt << 'EOF'
aiohttp
websockets
python-dotenv
prometheus-client
solders
solana
base58
EOF

# 3. Luo Procfile
echo "web: python3 run_helius_scanner.py" > Procfile

# 4. Luo .gitignore
cat > .gitignore << 'EOF'
.env
*.log
*.jsonl
__pycache__/
*.pyc
venv/
EOF

# 5. Mene Railway.app ja deploy!
# - Vedä koko /matkatiimi kansio Railway:hin
# - Lisää .env muuttujat Railway Variables:iin
# - Deploy!
```

---

## ✅ **YHTEENVETO:**

**SUOSITUS AWS EC2:**
1. Luo EC2 t3.micro Ubuntu instanssi
2. Asenna Python & riippuvuudet
3. Kopioi koodi & .env
4. Luo systemd service
5. **VALMIS!** Botti ajaa 24/7 luotettavasti

**Kustannus:** ~$8/kk
**Aika:** ~30 min setup
**Vaatii:** Perustason Linux osaamista

---

Haluatko että autan sinua yksityiskohtaisesti jonkin vaihtoehdon kanssa? 🚀
