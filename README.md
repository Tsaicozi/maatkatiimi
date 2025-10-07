# 🚀 Solana Auto Trader

**Automaattinen Solana new token trading bot - Löydä, treidaa ja voita!**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DigitalOcean](https://img.shields.io/badge/Deploy-DigitalOcean-0080FF.svg)](https://www.digitalocean.com/)

---

## 🎯 Mitä Tämä On?

Täysin automaattinen trading bot joka:

- 🔍 **Skannaa** uudet Solana-tokenit reaaliajassa (DexScreener API)
- 💰 **Treidaa** Jupiter-aggregaattorin kautta (paras hinta + reitti)
- 🎯 **Hallinnoi** positioita automaattisesti (Stop-loss, Take-profit, Trailing stop)
- 📱 **Ilmoittaa** Telegramissa kaikista kaupoista
- ☁️ **Toimii 24/7** pilvipalvelimella ($6/kk)

**Miksi tämä on hyvä?**
- ✅ Uudet tokenit = maksimi volatiliteetti = suuret voittomahdollisuudet
- ✅ Jupiter löytää parhaan reitin DEXeistä (Raydium, Orca, etc.)
- ✅ Automaattinen riskinhalliinta (ei tunteita, ei FOMO:a)
- ✅ Toimii 24/7 kun sinä nukut/työskentelet

---

## ⚡ Pika-aloitus (3 Minuuttia)

### 1. Kloonaa Repository
```bash
git clone https://github.com/Tsaicozi/maatkatiimi.git
cd maatkatiimi
```

### 2. Tarkista Setup
```bash
python3 check_setup.py
```

### 3. Konfiguroi
```bash
cp .env2.example .env2
nano .env2  # Lisää: PHANTOM_PRIVATE_KEY, TELEGRAM_TOKEN
```

### 4. Käynnistä
```bash
# Paikallisesti (testaus)
python solana_auto_trader.py

# TAI DigitalOcean (tuotanto 24/7)
# Katso: QUICK_START_DROPLET.md
```

**📖 Yksityiskohtaiset ohjeet:** [START_HERE.md](START_HERE.md)

---

## 🌟 Ominaisuudet

### Token Skannaus
- DexScreener API integraatio
- Raydium, Orca, Jupiter poolit
- Filtterointi: likviditeetti, volyymi, ikä
- Päivittyy joka 5 min

### Jupiter DEX Trading
- Paras swap-reitti automaattisesti
- Slippage-suojaus
- Priority fees (nopeampi vahvistus)
- Transaction retry -logiikka

### Position Management
- **Stop-loss**: Myy automaattisesti tappiolla (esim. -30%)
- **Take-profit**: Myy voitolla (esim. +50%)
- **Trailing stop**: Suojaa voittoja kun hinta nousee
- **Time exit**: Pakkomyynti tietyn ajan jälkeen (esim. 48h)
- **Cooldown**: Estää saman tokenin välittömän uudellenoston

### Riskinhalliinta
- Position sizing (esim. 0.02 SOL per kauppa)
- Max positioita kerralla (esim. 3)
- Slippage-rajoitukset
- Likviditeetti-tarkistukset

### Telegram Ilmoitukset
- ✅ Entry-signaalit (token, hinta, määrä)
- 💰 Exit-signaalit (TP/SL/Time, P&L)
- ⚠️ Virheet ja ongelmat

---

## 📊 Miten Se Toimii?

```
1. SKANNAUS (joka 5 min)
   ↓
   Hae uudet poolit DexScreeneristä
   ↓
   Filttää: likviditeetti, volyymi, ikä
   ↓
   
2. ENTRY
   ↓
   Jos lupaava token → avaa position
   ↓
   Tallenna entry-hinta, aika
   ↓
   Telegram-ilmoitus
   ↓
   
3. POSITION MANAGEMENT
   ↓
   Tarkista hinta joka sykli
   ↓
   If (hinta < SL) → Myy tappiolla
   If (hinta > TP) → Myy voitolla
   If (aika > Max) → Myy ajalla
   ↓
   Telegram-ilmoitus (P&L)
   ↓
   
4. COOLDOWN (24h)
   ↓
   Estä saman tokenin uudelleenosto
```

---

## 💰 Kustannukset

| Komponentti | Hinta |
|-------------|-------|
| **DigitalOcean Droplet** (1GB) | **$6/kk** |
| Helius RPC (100k req/päivä) | $0/kk |
| Telegram Bot | $0/kk |
| Solana gas fees | ~$0.0003/tx |
| **Trading Capital** | **Sinun valintasi** |

**Minimikustannus: $6/kk + trading pääoma (0.1-0.5 SOL riittää alkuun)**

---

## 🚀 Deployment-vaihtoehdot

### Vaihtoehto 1: DigitalOcean (Suositeltu)
**✅ 24/7 ajo pilvipalvelimella**

```bash
# 1. Luo droplet (Ubuntu 22.04, $6/mo)
# 2. SSH ja aja:
ssh root@YOUR_IP
curl -fsSL https://raw.githubusercontent.com/Tsaicozi/maatkatiimi/main/setup_droplet.sh | bash

# 3. Konfiguroi .env2 ja käynnistä
su - trader
cd maatkatiimi
nano .env2
screen -S solana-trader
source venv/bin/activate
python solana_auto_trader.py
```

**📖 Yksityiskohtaiset ohjeet:** [QUICK_START_DROPLET.md](QUICK_START_DROPLET.md)

### Vaihtoehto 2: Paikallinen Ajo
**✅ Testaus ja kehitys**

```bash
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env2.example .env2
nano .env2
python solana_auto_trader.py
```

---

## 🔧 Konfiguraatio

### Minimikonfiguraatio (.env2):

```env
# Solana RPC
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# Phantom Wallet (luo: python create_solana_wallet.py)
PHANTOM_PRIVATE_KEY=your_base58_private_key

# Telegram
TELEGRAM_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789

# Trading (konservatiivinen)
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

**📖 Täydellinen konfiguraatio-opas:** [.env2.example](.env2.example)

---

## 📚 Dokumentaatio

| Tiedosto | Kuvaus |
|----------|--------|
| **[START_HERE.md](START_HERE.md)** | 👈 **Aloita tästä!** Kattava aloitusopas |
| [SOLANA_README.md](SOLANA_README.md) | Yksityiskohtainen README |
| [QUICK_START_DROPLET.md](QUICK_START_DROPLET.md) | 3 min DigitalOcean setup |
| [DIGITALOCEAN_SOLANA_SETUP.md](DIGITALOCEAN_SOLANA_SETUP.md) | Pitkä DigitalOcean-ohje |
| [DEPLOYMENT_COMPLETE.md](DEPLOYMENT_COMPLETE.md) | Deployment-yhteenveto |
| [.env2.example](.env2.example) | Konfiguraatio-opas |

---

## 🛠️ Työkalut

| Työkalu | Kuvaus |
|---------|--------|
| `check_setup.py` | Tarkista että kaikki on kunnossa ennen käynnistystä |
| `create_solana_wallet.py` | Luo uusi Phantom-lompakko |
| `setup_droplet.sh` | Automaattinen asennus-skripti DigitalOceaniin |

---

## 🔒 Turvallisuus

### ⚠️ TÄRKEÄÄ - Lue tämä:

1. **Älä KOSKAAN jaa `PHANTOM_PRIVATE_KEY`:tä**
   - Ei GitHubiin, Discordiin, Telegramiin
   - Pidä varmuuskopio turvallisessa paikassa (1Password, USB)

2. **Käytä erillistä lompakkoa botille**
   - Luo uusi: `python create_solana_wallet.py`
   - Älä käytä pääomayhtiötä

3. **Aloita pienellä summalla**
   - 0.1-0.5 SOL riittää alkuun
   - Nosta kun olet varma että botti toimii

4. **Seuraa ensimmäiset 24h tarkasti**
   - Lokit: `tail -f solana_auto_trader.log`
   - Telegram-ilmoitukset

5. **Muista riskit**
   - Uudet tokenit ovat ERITTÄIN volatileja
   - Suurin osa menee -90%
   - Vain harvat +1000%
   - **Treidaa vain summilla joita sinulla on varaa menettää**

---

## 📈 Suositellut Parametrit

### Konservatiivinen (Aloittelijat):
```env
POSITION_SIZE_SOL=0.01
MAX_POSITIONS=2
STOP_LOSS_PCT=-20
TAKE_PROFIT_PCT=40
MIN_LIQUIDITY_USD=10000
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

## 🚨 Ongelmanratkaisu

| Ongelma | Ratkaisu |
|---------|----------|
| "Botti ei löydä tokeneita" | Laske `MIN_LIQUIDITY_USD=3000`, nosta `MAX_TOKEN_AGE_HOURS=48` |
| "RPC timeout" | Hanki Helius API key (ilmainen, nopea) |
| "Out of memory" (droplet) | Lisää swap-tila (katso docs) |
| "Swap failed" | Nosta `MAX_SLIPPAGE_BPS=1000` |
| "Telegram ei toimi" | Tarkista token/chat_id, aja `check_setup.py` |

**Enemmän apua:** [SOLANA_README.md](SOLANA_README.md) → "🚨 Ongelmanratkaisu"

---

## 💡 Pro-vinkit

1. **Käytä `check_setup.py`** - tarkistaa konfiguraation automaattisesti
2. **Käynnistä `screen`-sessiossa** - botti jatkaa taustalla
3. **Asenna systemd service** - automaattinen restart kaatumisen jälkeen
4. **Seuraa metriikoita** - win rate, avg P&L, hold time
5. **Backupa private key** - 1Password, USB, etc.
6. **Testaa lokaalisti ensin** - ymmärrä miten toimii
7. **Säädä parametreja** - optimoi tuloksiin perustuen

---

## 📊 Mitä Odottaa?

### Ensimmäinen Päivä:
- 1-5 entry-signaalia (riippuu markkinasta)
- Jotkut TP ✅, jotkut SL ❌
- Kerää dataa

### Ensimmäinen Viikko:
- 5-20 kauppaa
- Win rate ~30-50% (normaali uusille tokeneille)
- Näet mitkä parametrit toimivat

### Kuukauden Jälkeen:
- Riittävästi dataa optimointiin
- Säädä parametreja
- Skaalaa jos tulokset hyviä

**Realistiset odotukset:**
- Win rate: 30-50%
- Avg profit: +50-100% per voitto
- Avg loss: -20-40% per tappio
- Net result: Riippuu markkinasta ja parametreista

---

## 🤝 Contributing

Pull requestit tervetulleita! Isoja muutoksia varten avaa ensin issue.

---

## 📜 Lisenssi

MIT License - Vapaa käyttö, muokkaus ja levitys.

**⚠️ VASTUUVAPAUSLAUSEKE:**

Tämä on kokeilutyökalu. Käytät omalla vastuullasi. Tekijä ei ole vastuussa mahdollisista tappioista.

**TREIDAA VAIN SUMMILLA JOITA SINULLA ON VARAA MENETTÄÄ.**

---

## 🎓 Oppimismateriaali

### Solana
- [Solana Docs](https://docs.solana.com/)
- [Solana Cookbook](https://solanacookbook.com/)

### Jupiter
- [Jupiter Docs](https://docs.jup.ag/)
- [Jupiter API](https://station.jup.ag/docs/apis/swap-api)

### DexScreener
- [DexScreener API](https://docs.dexscreener.com/)

---

## 🌟 Anna Tähti!

Jos pidät projektista, anna ⭐ GitHubissa!

---

## 📞 Tuki

**Ongelma?**

1. Lue [START_HERE.md](START_HERE.md)
2. Aja `python check_setup.py`
3. Tarkista lokit: `tail -f solana_auto_trader.log`
4. Etsi virheitä: `grep ERROR solana_auto_trader.log`
5. Lue [SOLANA_README.md](SOLANA_README.md) → "🚨 Ongelmanratkaisu"

---

## 🚀 Aloita Nyt!

```bash
# Kloonaa
git clone https://github.com/Tsaicozi/maatkatiimi.git
cd maatkatiimi

# Lue ohjeet
cat START_HERE.md

# Tarkista setup
python check_setup.py

# Käynnistä
python solana_auto_trader.py
```

**Onnea tradingiin! 🎉📈💰**

---

<div align="center">

Made with ❤️ by crypto traders, for crypto traders

[⬆ Takaisin ylös](#-solana-auto-trader)

</div>

