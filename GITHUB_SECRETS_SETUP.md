# 🔐 GitHub Secrets Setup - Solana Auto Trader

Tämä ohje näyttää miten lisätään tarvittavat secrets GitHub Actions:ille.

## 📋 Tarvittavat Secrets

### 🔑 Pakolliset Secrets:
1. **`PHANTOM_PRIVATE_KEY`** - Solana wallet private key
2. **`TELEGRAM_TOKEN`** - Telegram bot token (valinnainen)
3. **`TELEGRAM_CHAT_ID`** - Telegram chat ID (valinnainen)

## 🚀 Vaihe-vaihe Ohje

### 1. 🔐 Hanki Phantom Private Key

#### Vaihtoehto A: Luo Uusi Wallet (Suositeltu)
```bash
# Lokaalisti
python3 simple_wallet_creator.py
# Valitse: 1 (Luo uusi wallet)
# Tallenna private key turvalliseen paikkaan
# Rahoita wallet 0.6+ SOL
```

#### Vaihtoehto B: Vie Olemassa Oleva Phantom Wallet
1. Avaa Phantom wallet
2. Settings → Export Private Key
3. Syötä salasana
4. Kopioi private key (Base58 format)

⚠️ **VAROITUS**: Älä koskaan jaa private keyä julkisesti!

### 2. 📱 Hanki Telegram Credentials (Valinnainen)

#### Luo Telegram Bot:
1. Mene [@BotFather](https://t.me/botfather) Telegramissa
2. Lähetä `/newbot`
3. Anna bot nimi: `Solana Auto Trader Bot`
4. Anna username: `solana_auto_trader_bot` (tai muu vapaa)
5. Kopioi bot token (esim: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Hae Chat ID:
```bash
# Lokaalisti
python3 get_telegram_chat_id.py
# Syötä bot token
# Lähetä viesti botille Telegramissa
# Kopioi chat ID
```

### 3. 🔧 Lisää Secrets GitHubiin

#### Siirry GitHub Repository:yn:
1. Mene repository sivulle GitHubissa
2. Klikkaa **Settings** välilehteä
3. Vasemmalta valikosta **Secrets and variables** → **Actions**

#### Lisää Secrets:

##### A. PHANTOM_PRIVATE_KEY
1. Klikkaa **"New repository secret"**
2. Name: `PHANTOM_PRIVATE_KEY`
3. Secret: `[sinun_private_key_tässä]`
4. Klikkaa **"Add secret"**

##### B. TELEGRAM_TOKEN (Valinnainen)
1. Klikkaa **"New repository secret"**
2. Name: `TELEGRAM_TOKEN`
3. Secret: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
4. Klikkaa **"Add secret"**

##### C. TELEGRAM_CHAT_ID (Valinnainen)
1. Klikkaa **"New repository secret"**
2. Name: `TELEGRAM_CHAT_ID`
3. Secret: `123456789` (numerosarja)
4. Klikkaa **"Add secret"**

### 4. ✅ Varmista Secrets

Secrets sivulla pitäisi näkyä:
```
✅ PHANTOM_PRIVATE_KEY
✅ TELEGRAM_TOKEN (valinnainen)
✅ TELEGRAM_CHAT_ID (valinnainen)
```

## 🚀 Aktivoi GitHub Actions

### 1. Push Koodi
```bash
git add .
git commit -m "Add Solana Auto Trader with GitHub Actions"
git push origin main
```

### 2. Tarkista Actions
1. Mene **Actions** välilehdelle
2. Näet **"Solana Auto Trader"** workflow
3. Se alkaa ajamaan automaattisesti joka 30 min

### 3. Manuaalinen Käynnistys
1. Actions → **"Solana Auto Trader"**
2. Klikkaa **"Run workflow"**
3. Valitse **"Run only one trading cycle"** (suositeltu ensimmäisellä kerralla)
4. Klikkaa **"Run workflow"**

## 📊 Seuranta

### GitHub Actions Lokit:
1. Actions → Workflow run
2. Klikkaa job nimeä
3. Laajenna step lokit
4. Lataa artifacts (trading logs)

### Telegram Ilmoitukset:
Jos konfiguroitu, saat viestejä:
```
🤖 Solana Auto Trader
Status: ✅ ONNISTUI
Type: Continuous
Run: #123
```

## 🔒 Turvallisuus

### ✅ Hyvät Käytännöt:
- ✅ Käytä erillistä walletia tradingiin
- ✅ Aloita pienillä summilla (0.05 SOL)
- ✅ Seuraa ensimmäisiä ajoja tarkasti
- ✅ Tarkista lokit säännöllisesti

### ❌ Älä Koskaan:
- ❌ Jaa private keyä kenenkään kanssa
- ❌ Commitoi private keyä koodiin
- ❌ Käytä pääwallettiasi
- ❌ Sijoita enempää kuin voit hävitä

## 🛠 Troubleshooting

### "PHANTOM_PRIVATE_KEY puuttuu"
- Tarkista secret nimi (case sensitive)
- Varmista että secret on lisätty oikeaan repositoryyn
- Kokeile lisätä secret uudelleen

### "Workflow ei käynnisty"
- Tarkista että `.github/workflows/solana_trader.yml` on olemassa
- Varmista että repository on public tai Actions on enabled
- Tarkista YAML syntaksi

### "Transaction epäonnistui"
- Tarkista wallet balance
- Varmista että private key on oikein
- Kokeile pienemmällä summalla

### "Telegram ei toimi"
- Tarkista bot token ja chat ID
- Varmista että lähetit viestin botille
- Telegram secrets ovat valinnaisia

## 🎯 Seuraavat Vaiheet

1. ✅ Lisää secrets
2. ✅ Push koodi GitHubiin  
3. ✅ Testaa manuaalinen ajo
4. ✅ Seuraa automaattista ajamista
5. ✅ Optimoi asetuksia tuloksien perusteella

---

**🎉 GitHub Actions on nyt valmis! Onnea automaattiseen tradingiin! 💰**

*⚠️ Disclaimer: Käytä omalla vastuulla. Testaa aina pienillä summilla ensin.*