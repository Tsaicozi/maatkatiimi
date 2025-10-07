# 🚀 Solana Auto Trader

Automaattinen Solana new token trading bot joka:
- 🔍 Skannaa uudet tokenipoolit DexScreeneristä
- 💰 Treidaa Jupiter-aggregaattorin kautta
- 🎯 Hallinnoi positioita automaattisesti (TP/SL/Time exit)
- 📱 Lähettää Telegram-ilmoitukset
- ☁️ Toimii 24/7 pilvipalvelimella

---

## 📚 Dokumentaatio

### Pika-aloitus:
- **[QUICK_START_DROPLET.md](QUICK_START_DROPLET.md)** - 3 minuutissa käyntiin DigitalOceanissa

### Yksityiskohtaiset ohjeet:
- **[DIGITALOCEAN_SOLANA_SETUP.md](DIGITALOCEAN_SOLANA_SETUP.md)** - Täydellinen DigitalOcean-setup
- **[SOLANA_TRADER_SETUP.md](SOLANA_TRADER_SETUP.md)** - GitHub Actions -vaihtoehto

### Kooditiedostot:
- `solana_token_scanner.py` - Token skannaus DexScreeneristä
- `solana_trader.py` - Jupiter swap-integraatio
- `solana_auto_trader.py` - Pääbotti (position management)
- `create_solana_wallet.py` - Lompakon luonti
- `setup_droplet.sh` - Automaattinen asennus-skripti

---

## ⚡ Nopea Käyttöönotto

### Vaihtoehto 1: DigitalOcean Droplet (Suositeltu) 🌊

```bash
# 1. Luo droplet (Ubuntu 22.04, $6/mo)
# 2. SSH ja aja:
ssh root@YOUR_IP
curl -fsSL https://raw.githubusercontent.com/Tsaicozi/maatkatiimi/main/setup_droplet.sh | bash

# 3. Konfiguroi
su - trader
cd maatkatiimi
nano .env2  # Lisää PHANTOM_PRIVATE_KEY, TELEGRAM_TOKEN

# 4. Käynnistä
screen -S solana-trader
source venv/bin/activate
python solana_auto_trader.py
```

### Vaihtoehto 2: Paikallinen Ajo 💻

```bash
# 1. Kloonaa repo
git clone https://github.com/Tsaicozi/maatkatiimi.git
cd maatkatiimi

# 2. Asenna riippuvuudet
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Konfiguroi .env2
cp .env2.example .env2
nano .env2  # Lisää avaimet

# 4. Käynnistä
python solana_auto_trader.py
```

---

## 🔧 Minimikonfiguraatio (.env2)

```env
# Solana RPC
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# Phantom Wallet
PHANTOM_PRIVATE_KEY=your_base58_private_key

# Telegram
TELEGRAM_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789

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
MAX_SLIPPAGE_BPS=500
```

---

## 📊 Miten se toimii?

### 1. Skannaus (joka 5 min)
- Hakee uudet Solana poolit DexScreeneristä
- Filttaa likviditeetin, volyymin, iän perusteella
- Tarkistaa että token on TOKEN/SOL-pari

### 2. Entry
- Kun lupaava token löytyy → avaa position
- Position size lasketaan riskiperusteisesti
- Tallentaa entry-hinnan ja timestampin
- Lähettää Telegram-ilmoituksen

### 3. Position Management
- Tarkistaa positiot joka sykli
- Stop-loss: Myy jos -30% tappiolla
- Take-profit: Myy 50% @ +50%, loput @ +100%
- Time exit: Myy jos pitoaika > 48h
- Trailing stop: Suojaa voittoja

### 4. Cooldown
- Token cooldownissa 24h myymisen jälkeen
- Vältetään hype-pomppu-uudelleenosto

---

## 💰 Kustannukset

| Komponentti | Hinta |
|-------------|-------|
| DigitalOcean Droplet (1GB) | $6/kk |
| Helius RPC (optional, faster) | $0-20/kk |
| Telegram Bot | $0 |
| Gas fees (Solana) | ~$0.00025/tx |

**Minimikustannus: $6/kk + trading capital**

---

## 🎯 Trading-parametrit

### Konservatiivinen (suositeltu aloittelijoille):
```env
POSITION_SIZE_SOL=0.01
MAX_POSITIONS=2
STOP_LOSS_PCT=-20
TAKE_PROFIT_PCT=40
MIN_LIQUIDITY_USD=10000
```

### Aggressiivinen (kokeneet):
```env
POSITION_SIZE_SOL=0.1
MAX_POSITIONS=5
STOP_LOSS_PCT=-40
TAKE_PROFIT_PCT=100
MIN_LIQUIDITY_USD=3000
```

---

## 📈 Seuranta

### Lokit
```bash
# Reaaliaikaiset
tail -f solana_auto_trader.log

# Etsi virheitä
grep ERROR solana_auto_trader.log
```

### Position State
```bash
# Katso nykyiset positiot
cat solana_positions.json | python -m json.tool

# Cooldown-lista
cat solana_cooldown.json | python -m json.tool
```

### Telegram
Botti lähettää automaattisesti:
- ✅ Entry-signaalit (token, hinta, määrä)
- 💰 Exit-signaalit (TP/SL/Time, P&L)
- ⚠️ Virheet ja ongelmat

---

## 🔒 Turvallisuus

### ⚠️ TÄRKEÄÄ:
- **Älä KOSKAAN** jaa `PHANTOM_PRIVATE_KEY`:tä
- Käytä erillistä lompakkoa botille (älä pääomayhtiötä)
- Aloita pienellä summalla (0.1-0.5 SOL)
- Seuraa ensimmäiset 24h tarkasti
- Pidä varmuuskopio private keystä turvallisessa paikassa

### Droplet-turvallisuus:
```bash
# Firewall
sudo ufw allow 22/tcp
sudo ufw enable

# SSH key -autentikointi (poista salasana)
sudo nano /etc/ssh/sshd_config
# PasswordAuthentication no
sudo systemctl restart sshd
```

---

## 🚨 Ongelmanratkaisu

### Botti ei löydä tokeneita?
1. Laske `MIN_LIQUIDITY_USD` → 3000
2. Nosta `MAX_TOKEN_AGE_HOURS` → 48
3. Tarkista `solana_auto_trader.log` debug-viestit

### RPC-ongelmat?
1. Kokeile Helius RPC:tä (nopein, 100k req/päivä ilmaiseksi)
2. TAI Serum: `https://solana-api.projectserum.com`
3. TAI QuickNode (maksullinen, erittäin vakaa)

### "Out of memory"?
```bash
# Lisää swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Swap epäonnistuu?
1. Tarkista slippage: Nosta `MAX_SLIPPAGE_BPS` → 1000
2. Tarkista likviditeetti: Token voi olla liian pieni
3. Katso Jupiter-virheet logeista

---

## 📖 Lisädokumentaatio

### Stratgiat ja Teoria:
- [Trading Strategies](TRADING_STRATEGY_README.md)
- [CoinGecko Screener](CRYPTO_SCREENER_README.md)

### Deployment:
- [GitHub Actions](GITHUB_ACTIONS_OHJEET.md)
- [Manual Deployment](MANUAL_GITHUB_DEPLOYMENT.md)

### Vanhat Botit (referenssi):
- `crypto_new_token_screener_v3.py` - CoinGecko-pohjainen screener
- `crypto_screener_daemon.py` - Daemon-wrapper

---

## 🎓 Oppimismateriaali

### Uuden Tokenin Trading:
- Uudet tokenit ovat erittäin volatileja (±50-200% päivässä)
- Likviditeetti on matala → slippage korkea
- Suurin osa menee -90%, harvat +1000%
- Nopea in-and-out on avain

### Jupiter Aggregator:
- Löytää parhaan reitin DEXeistä (Raydium, Orca, etc.)
- Minimoi slippagen
- Optimoi gas-kulut

### DexScreener API:
- Päivittyy ~30s välein
- `created_at` = poolin luontiaika
- `liquidity.usd` = LP-arvo USD:ssa

---

## 💡 Pro-vinkit

1. **Backtest ensin**: Aja historiallisella datalla ennen live-tradingia
2. **Pieni position size**: 1-2% portfoliosta per kauppa
3. **Diversifioi**: Älä laita kaikkea yhteen tokeniin
4. **Seuraa metrics**: Win rate, avg profit, avg loss
5. **Säädä parametreja**: Optimoi tuloksiin perustuen
6. **Cooldown on tärkeä**: Vältä FOMO-kauppoja
7. **Telegram on ystäväsi**: Seuraa ilmoituksia

---

## 📞 Tuki

Ongelmia? Tarkista:
1. `solana_auto_trader.log` - yksityiskohtaiset lokit
2. `solana_positions.json` - nykyiset positiot
3. Telegram-ilmoitukset - reaaliaikaiset päivitykset

---

## 📜 Lisenssi

MIT License - vapaa käyttö, muokkaus ja levitys.

**⚠️ VASTUUVAPAUSLAUSEKE:**
Tämä on kokeilutyökalu. Käytät omalla vastuullasi. Tekijä ei ole vastuussa mahdollisista tappioista. Treidaa vain summilla joita sinulla on varaa menettää.

---

## 🚀 Aloita nyt!

1. **Lue**: [QUICK_START_DROPLET.md](QUICK_START_DROPLET.md)
2. **Luo droplet**: DigitalOcean ($6/kk)
3. **Konfiguroi**: Lisää avaimet .env2:een
4. **Käynnistä**: `python solana_auto_trader.py`
5. **Seuraa**: Telegram + lokit

**Onnea tradingiin! 🎉📈**

