# ⚡ NOPEA PILVIAJO - Railway.app (5 minuuttia)

## 🚀 Helpoin ja nopein tapa saada botti pilveen!

---

## 📝 **Vaihe 1: Valmistele Tiedostot (JO TEHTY!)**

✅ `requirements.txt` - Luotu
✅ `Procfile` - Luotu
✅ `.gitignore` - Luotu
✅ `Dockerfile` - Luotu (valinnainen)
✅ `docker-compose.yml` - Luotu (valinnainen)

---

## 🌐 **Vaihe 2: Luo Railway Tili**

1. Mene: **https://railway.app**
2. Kirjaudu GitHub tilillä
3. Saat **$5 ilmaista** kuukaudessa

---

## 📦 **Vaihe 3: Deploy Projekti**

### **Vaihtoehto A: GitHub (Suositeltu)**

1. **Luo GitHub repo:**
   ```bash
   cd /Users/jarihiirikoski/matkatiimi
   git init
   git add .
   git commit -m "Initial commit - Helius Scanner Bot"
   gh repo create matkatiimi --private --source=. --push
   ```

2. **Railway:**
   - "New Project" → "Deploy from GitHub repo"
   - Valitse `matkatiimi` repo
   - Railway deployaa automaattisesti!

### **Vaihtoehto B: Railway CLI (Nopein!)**

```bash
# Asenna Railway CLI
npm install -g @railway/cli

# Kirjaudu
railway login

# Luo projekti
cd /Users/jarihiirikoski/matkatiimi
railway init

# Deploy!
railway up

# Avaa dashboard
railway open
```

---

## 🔐 **Vaihe 4: Lisää Ympäristömuuttujat**

Railway Dashboard → Variables:

```bash
# Kopioi KAIKKI nämä .env tiedostostasi:
HELIUS_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
SOLANA_RPC_URL=...
TRADER_PRIVATE_KEY_HEX=...
AUTO_TRADE=1
DRY_RUN=0
TRADE_MAX_USD=20
# ... jne. KAIKKI muuttujat!
```

**TÄRKEÄÄ:**
- ✅ Älä lisää lainausmerkkejä
- ✅ Jokainen muuttuja omalle rivilleen
- ✅ Tarkista että `TRADER_PRIVATE_KEY_HEX` on oikein

---

## ✅ **Vaihe 5: Käynnistä & Seuraa**

1. **Käynnistä:**
   - Railway deployaa automaattisesti kun lisäät muuttujat
   - TAI: Click "Redeploy"

2. **Katso lokeja:**
   - Railway UI → Deployments → View Logs
   - Etsi: `✅ Real Telegram bot initialized`
   - Etsi: `💰 Wallet report sent`

3. **Tarkista Telegram:**
   - Pitäisi tulla wallet report 5 sek sisällä
   - Token löydöt alkavat tulla

---

## 🔧 **Vaihe 6: Päivitä Koodi**

```bash
# Lokaalilla koneellasi tee muutoksia
cd /Users/jarihiirikoski/matkatiimi

# Committaa muutokset
git add .
git commit -m "Update: parempi scoring"
git push

# Railway deployaa AUTOMAATTISESTI!
```

---

## 📊 **Kulut Railway.app:**

- **Ilmainen:** $5/kk (500 tuntia)
- **Hobby:** $5/kk lisää ($10 total)
- **Arvio tälle botille:** ~$8-12/kk

---

## 🆘 **Ongelmanratkaisu:**

### **Botti ei käynnisty:**
```bash
# Tarkista lokit Railway UI:ssa
# Etsi ERROR viestejä
# Tarkista että KAIKKI env muuttujat on lisätty
```

### **Ei yhteys Telegramiin:**
```bash
# Tarkista:
TELEGRAM_BOT_TOKEN=correct_token_here
TELEGRAM_CHAT_ID=correct_chat_id_here
```

### **Trading ei toimi:**
```bash
# Tarkista:
TRADER_PRIVATE_KEY_HEX=full_64_byte_hex_key
AUTO_TRADE=1
DRY_RUN=0
```

---

## ⚡ **TODELLA NOPEA TAPA (5 min):**

```bash
# 1. Asenna Railway CLI
npm install -g @railway/cli

# 2. Kirjaudu
cd /Users/jarihiirikoski/matkatiimi
railway login

# 3. Luo projekti
railway init

# 4. Lisää .env muuttujat Railway dashboardiin
# Mene: railway open
# Variables → Raw Editor → Kopioi koko .env sisältö

# 5. Deploy!
railway up

# 6. VALMIS! Katso lokeja:
railway logs
```

---

## 🎯 **SUOSITUS:**

**AWS EC2 = Paras pitkällä aikavälillä** (edullinen, luotettava)
**Railway.app = Nopein aloitus** (5 min deployment)

**Aloita Railway:llä, siirrä EC2:lle kun tarvitset lisää tehoa!** 🚀

