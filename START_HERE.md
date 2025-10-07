# 🚀 ALOITA TÄSTÄ - Solana Auto Trader

## Mikä tämä on?

**Automaattinen Solana new token trading bot** joka:
- 🔍 Skannaa uudet tokenit automaattisesti (DexScreener)
- 💰 Treidaa Jupiter-aggregaattorin kautta
- 🎯 Hallinnoi positioita (Stop-loss, Take-profit, Time exit)
- 📱 Lähettää Telegram-ilmoitukset
- ☁️ Toimii 24/7 pilvipalvelimella

---

## ⚡ 3 Minuutin Quick Start

### 1️⃣ Kloonaa Repo
```bash
git clone https://github.com/Tsaicozi/maatkatiimi.git
cd maatkatiimi
```

### 2️⃣ Tarkista Setup
```bash
python3 check_setup.py
```

### 3️⃣ Konfiguroi
```bash
cp .env2.example .env2
nano .env2  # Lisää: PHANTOM_PRIVATE_KEY, TELEGRAM_TOKEN, etc.
```

### 4️⃣ Käynnistä
```bash
# Paikallisesti (testaus)
python solana_auto_trader.py

# TAI DigitalOcean pilvipalvelimella (tuotanto)
# Katso: QUICK_START_DROPLET.md
```

---

## 📚 Dokumentaatio

### 🎯 Aloita tästä (suositeltu järjestys):

1. **[SOLANA_README.md](SOLANA_README.md)** 
   - Yleiskatsaus, toimintaperiaate, parametrit
   
2. **[QUICK_START_DROPLET.md](QUICK_START_DROPLET.md)** 
   - 3 minuuttia käyttöönottoon DigitalOceanissa
   
3. **[DIGITALOCEAN_SOLANA_SETUP.md](DIGITALOCEAN_SOLANA_SETUP.md)** 
   - Yksityiskohtainen DigitalOcean-ohje
   
4. **[.env2.example](.env2.example)** 
   - Konfiguraatio-opas kommenteilla

### 🛠️ Työkalut:

- `check_setup.py` - Tarkista että kaikki on kunnossa
- `create_solana_wallet.py` - Luo uusi Phantom-lompakko
- `setup_droplet.sh` - Automaattinen asennus-skripti (DigitalOcean)

### 📦 Kooditiedostot:

- `solana_token_scanner.py` - Token skannaus DexScreeneristä
- `solana_trader.py` - Jupiter swap-integraatio
- `solana_auto_trader.py` - **Pääbotti** (tämä ajaa koko systeemin)
- `solana_rpc_helpers.py` - RPC-apufunktiot

---

## 🔑 Mitä tarvitset?

### Pakolliset:
- ✅ **Python 3.10+**
- ✅ **Phantom Wallet** (private key)
  - Luo: `python create_solana_wallet.py`
  - Rahoita vähintään 0.1 SOL
- ✅ **Telegram Bot**
  - Luo: [BotFather](https://t.me/BotFather)
  - Hae token ja chat ID

### Valinnaiset (mutta suositeltu):
- 🌊 **DigitalOcean Droplet** ($6/kk - 24/7 ajo)
- ⚡ **Helius RPC** (ilmainen, nopea)

---

## 💰 Kustannukset

| Komponentti | Hinta |
|-------------|-------|
| **DigitalOcean** (1GB droplet) | $6/kk |
| **Helius RPC** (100k req/päivä) | $0/kk |
| **Telegram** | $0/kk |
| **Solana gas fees** | ~$0.0003/tx |
| **Trading capital** | Sinun valintasi (aloita 0.1-0.5 SOL) |

**Minimikustannus pilviajossa: $6/kk + trading pääoma**

---

## 🎯 Suositellut Aloitusasetukset

### Konservatiivinen (Aloittelijat):
```env
POSITION_SIZE_SOL=0.01      # Pieni position size
MAX_POSITIONS=2             # Max 2 tokenia kerralla
STOP_LOSS_PCT=-20           # Tiukka stop-loss
TAKE_PROFIT_PCT=40          # Realistinen TP
MIN_LIQUIDITY_USD=10000     # Vain likvidit tokenit
```

### Normaali:
```env
POSITION_SIZE_SOL=0.02
MAX_POSITIONS=3
STOP_LOSS_PCT=-30
TAKE_PROFIT_PCT=50
MIN_LIQUIDITY_USD=5000
```

### Aggressiivinen (Kokeneet):
```env
POSITION_SIZE_SOL=0.05
MAX_POSITIONS=5
STOP_LOSS_PCT=-40
TAKE_PROFIT_PCT=100
MIN_LIQUIDITY_USD=3000
```

---

## 🔒 Turvallisuus - TÄRKEÄÄ!

### ⚠️ Lue huolellisesti:

1. **Älä KOSKAAN jaa `PHANTOM_PRIVATE_KEY`:tä**
   - Älä committaa GitHubiin
   - Älä jaa Discordissa/Telegramissa
   - Pidä varmuuskopio turvallisessa paikassa

2. **Käytä erillistä lompakkoa botille**
   - Älä käytä pääomayhtiötä
   - Luo uusi: `python create_solana_wallet.py`

3. **Aloita pienellä summalla**
   - 0.1-0.5 SOL riittää alkuun
   - Nosta kun olet varma että botti toimii

4. **Seuraa ensimmäiset 24h tarkasti**
   - Tarkista lokit
   - Seuraa Telegram-ilmoituksia
   - Varmista että kaupat toimivat

5. **Muista riskit**
   - Uudet tokenit ovat ERITTÄIN volatileja
   - Suurin osa menee -90%
   - Vain harvat +1000%
   - **Treidaa vain summilla joita sinulla on varaa menettää**

---

## 📊 Mitä seuraavaksi?

### Ensimmäinen 24h:

1. **Käynnistä botti** (paikallisesti tai dropletilla)
2. **Seuraa lokeja**: `tail -f solana_auto_trader.log`
3. **Tarkista Telegram-ilmoitukset**
4. **Katso positiot**: `cat solana_positions.json | python -m json.tool`
5. **Kerää dataa**: Mitkä tokenit voittavat? Miksi?

### Viikon jälkeen:

1. **Analysoi tulokset**: Win rate, avg P&L
2. **Säädä parametreja**: Löysää/tiukkaa suodattimia
3. **Optimoi**: Mikä toimii, mikä ei?
4. **Skaalaa**: Jos tulokset hyviä → nosta position size

### Kuukauden jälkeen:

1. **Pitkän aikavälin data**: Mikä strategia paras?
2. **Backtestaa**: Historiallinen data
3. **Automatisoi**: Lisää sääntöjä, indikaattoreita
4. **Jaa kokemuksia**: Auta muita!

---

## 🚨 Yleisiä Ongelmia

| Ongelma | Ratkaisu |
|---------|----------|
| "Botti ei löydä tokeneita" | Laske `MIN_LIQUIDITY_USD` → 3000, nosta `MAX_TOKEN_AGE_HOURS` → 48 |
| "RPC timeout" | Vaihda Helius RPC:hen tai QuickNode |
| "Out of memory" (droplet) | Lisää swap-tila (katso docs) |
| "Swap failed" | Nosta `MAX_SLIPPAGE_BPS` → 1000 |
| "Telegram ei toimi" | Tarkista token/chat_id, aja `check_setup.py` |
| "Wallet empty" | Lähetä SOL osoitteeseen (katso `check_setup.py`) |

**Enemmän apua:** Katso `SOLANA_README.md` → "🚨 Ongelmanratkaisu"

---

## 💡 Pro-vinkit

1. **Käytä `check_setup.py` ennen käynnistystä** - säästää aikaa
2. **Käynnistä `screen`-sessiossa** - botti jatkaa taustalla
3. **Asenna systemd service** - automaattinen restart
4. **Seuraa metrics** - logeista tai Telegram-ilmoituksista
5. **Backupa private key** - 1Password, USB, etc.
6. **Testaa lokaalisti ensin** - varmista että ymmärrät miten toimii
7. **Lue dokumentaatio** - säästää aikaa pitkässä juoksussa

---

## 📞 Tuki

### Ongelma? Tee näin:

1. **Aja setup checker**: `python check_setup.py`
2. **Tarkista lokit**: `tail -f solana_auto_trader.log | grep ERROR`
3. **Lue FAQ**: `SOLANA_README.md` → "🚨 Ongelmanratkaisu"
4. **Tarkista konfiguraatio**: `.env2` vs `.env2.example`

---

## 🎉 Valmis aloittamaan?

### Vaihtoehto A: Paikallinen Testaus (5 min)
```bash
python check_setup.py      # Tarkista setup
python solana_auto_trader.py  # Käynnistä
```

### Vaihtoehto B: DigitalOcean Pilvi (10 min)
```bash
# Lue ensin: QUICK_START_DROPLET.md
# Sitten:
ssh root@YOUR_DROPLET_IP
curl -fsSL https://raw.githubusercontent.com/Tsaicozi/maatkatiimi/main/setup_droplet.sh | bash
```

---

## 📖 Lisälukemista

- **[SOLANA_TRADER_SETUP.md](SOLANA_TRADER_SETUP.md)** - GitHub Actions -vaihtoehto
- **[TRADING_STRATEGY_README.md](TRADING_STRATEGY_README.md)** - Strategia-teoria
- **[CRYPTO_SCREENER_README.md](CRYPTO_SCREENER_README.md)** - Vanha CoinGecko-botti

---

## 📜 Lisenssi

MIT License - Vapaa käyttö, muokkaus ja levitys.

**⚠️ VASTUUVAPAUSLAUSEKE:**
Tämä on kokeilutyökalu. Käytät omalla vastuullasi. Tekijä ei ole vastuussa mahdollisista tappioista. **Treidaa vain summilla joita sinulla on varaa menettää.**

---

**🚀 Onnea tradingiin!**

Jos pidät projektista, anna ⭐ GitHubissa!

---

**Tarvitsetko apua?** Aloita lukemalla:
1. [SOLANA_README.md](SOLANA_README.md)
2. [QUICK_START_DROPLET.md](QUICK_START_DROPLET.md)
3. Aja `python check_setup.py`

