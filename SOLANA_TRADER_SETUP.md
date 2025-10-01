# 🚀 Solana Auto Trader - Täydellinen Setup Opas

Automaattinen Solana token trader joka käyttää Jupiter DEX:iä ja Phantom wallet integraatiota.

## 📋 Sisällysluettelo

1. [Ominaisuudet](#ominaisuudet)
2. [Vaatimukset](#vaatimukset)
3. [Asennus](#asennus)
4. [Konfiguraatio](#konfiguraatio)
5. [Käyttö](#käyttö)
6. [GitHub Actions Setup](#github-actions-setup)
7. [Turvallisuus](#turvallisuus)
8. [Troubleshooting](#troubleshooting)

## ✨ Ominaisuudet

### 🔍 Token Skannaus
- **Real-time skannaus**: DexScreener ja Birdeye API integraatio
- **Ultra-fresh tokeneiden tunnistus**: 1-5 minuuttia vanhat tokenit
- **Älykkäät filtterit**: Market cap, volume, liquidity, holder distribution
- **Scoring system**: Social, technical, momentum ja risk skoorit

### 💰 Automaattinen Trading
- **Jupiter DEX integraatio**: Paras hinnoittelu ja likviditeetti
- **Phantom wallet tuki**: Täysi yhteensopivuus
- **Risk management**: Stop-loss, take-profit, max hold time
- **Position hallinta**: Max 3 positiota samanaikaisesti
- **Cooldown system**: 24h per token

### 📊 Seuranta ja Raportointi
- **Telegram ilmoitukset**: Entry/exit signaalit
- **GitHub Actions lokit**: Automaattinen ajaminen
- **Trading statistiikka**: Win rate, PnL, fees
- **State persistence**: Position data säilyy

## 🛠 Vaatimukset

### Ohjelmisto
- Python 3.10+
- Git
- GitHub account (Actions varten)

### API Avaimet
- **Phantom Wallet**: Private key (0.6+ SOL rahoitettu)
- **Telegram Bot** (valinnainen): Bot token ja chat ID
- **Solana RPC** (valinnainen): Custom RPC endpoint

### Riippuvuudet
```bash
pip install aiohttp asyncio python-dotenv solana base58 logging
```

## 🚀 Asennus

### 1. Kloonaa Repository
```bash
git clone <your-repository-url>
cd <repository-name>
```

### 2. Asenna Riippuvuudet
```bash
pip install -r requirements.txt
```

Jos `requirements.txt` ei ole olemassa:
```bash
pip install aiohttp asyncio python-dotenv solana base58
```

### 3. Luo Solana Wallet
```bash
python create_solana_wallet.py
```

Valitse:
- **1**: Luo uusi wallet
- **2**: Tuo olemassa oleva wallet
- **3**: Lataa tallennettu wallet

**⚠️ TÄRKEÄÄ**: Tallenna private key turvalliseen paikkaan!

### 4. Rahoita Wallet
- Lähetä vähintään 0.6 SOL walletiin
- Suositus: 1-2 SOL turvallista tradingiin
- Tarkista balance: `python create_solana_wallet.py` → Valinta 3

## ⚙️ Konfiguraatio

### 1. Luo .env Tiedosto
```bash
cp .env.example .env
```

### 2. Täytä Konfiguraatio
```env
# Phantom Wallet Private Key (Base58 format)
PHANTOM_PRIVATE_KEY=your_private_key_here

# Trading Parameters
POSITION_SIZE_SOL=0.05          # 0.05 SOL per kauppa
MAX_POSITIONS=3                 # Max 3 positiota kerralla
STOP_LOSS_PERCENT=30           # -30% stop loss
TAKE_PROFIT_PERCENT=50         # +50% take profit
MAX_HOLD_HOURS=48              # Max 48h hold
COOLDOWN_HOURS=24              # 24h cooldown per token
MIN_SCORE_THRESHOLD=7.0        # Min 7.0/10 score
SLIPPAGE_BPS=100               # 1% slippage

# Telegram Notifications (valinnainen)
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Solana RPC (valinnainen)
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
```

### 3. Telegram Setup (Valinnainen)

#### Luo Bot
1. Mene [@BotFather](https://t.me/botfather)
2. Lähetä `/newbot`
3. Anna nimi ja username
4. Kopioi token

#### Hae Chat ID
```bash
python get_telegram_chat_id.py
```

## 🎮 Käyttö

### Lokaali Testaus

#### 1. Testaa Token Scanner
```bash
python real_solana_token_scanner.py
```

#### 2. Testaa Trader
```bash
python solana_trader.py
```

#### 3. Aja Yksi Trading Cycle
```bash
python solana_auto_trader.py --once
```

#### 4. Aja Jatkuvasti
```bash
python solana_auto_trader.py
```

### Tuotanto Käyttö

Suositus: Käytä GitHub Actions automaattiseen ajamiseen.

## 🤖 GitHub Actions Setup

### 1. Lisää Secrets
Mene GitHub repository → Settings → Secrets and variables → Actions

Lisää seuraavat secrets:
- `PHANTOM_PRIVATE_KEY`: Wallet private key
- `TELEGRAM_TOKEN`: Bot token (valinnainen)
- `TELEGRAM_CHAT_ID`: Chat ID (valinnainen)

### 2. Aktivoi Workflow
1. Push koodi GitHubiin
2. Mene Actions välilehdelle
3. Workflow alkaa ajamaan automaattisesti joka 30 min

### 3. Manuaalinen Käynnistys
1. Mene Actions → Solana Auto Trader
2. Klikkaa "Run workflow"
3. Valitse "Run only one trading cycle" jos haluat

### 4. Seuranta
- **Logs**: Actions → Workflow run → Job logs
- **Artifacts**: Lataa trading logs ja state
- **Telegram**: Saat ilmoitukset entry/exit:eistä

## 🔒 Turvallisuus

### ⚠️ Kriittiset Turvallisuusohjeet

1. **Private Key Suojaus**
   - ÄLÄ KOSKAAN jaa private keyä
   - Käytä GitHub Secretsejä, älä koodia
   - Säilytä backup turvallisessa paikassa

2. **Testaus Ensin**
   - Aloita pienillä summilla (0.05 SOL)
   - Testaa kaikki toiminnot lokaalisti
   - Seuraa ensimmäisiä kauppoja tarkasti

3. **Risk Management**
   - Älä sijoita enempää kuin voit hävitä
   - Seuraa positioita säännöllisesti
   - Aseta järkevät stop-loss tasot

4. **Monitoring**
   - Tarkista lokit päivittäin
   - Seuraa wallet balanceja
   - Reagoi poikkeamiin nopeasti

### 🛡️ Suojausmekanismit

- **Position limits**: Max 3 positiota
- **Stop-loss**: Automaattinen -30% exit
- **Take-profit**: Automaattinen +50% exit
- **Max hold**: 48h maksimi hold aika
- **Cooldown**: 24h per token
- **Slippage protection**: Max 1% slippage
- **Balance checks**: Riittävä SOL ennen kauppoja

## 📊 Trading Strategia

### Token Valinta Kriteerit
- **Age**: 1-5 minuuttia vanha
- **Market Cap**: $20,000 - $100,000
- **Volume**: Min 80% market capista
- **Liquidity**: Min 20% market capista
- **Score**: Min 7.0/10 kokonaispisteistä

### Entry Signaalit
- Ultra-fresh token löydetty
- Kaikki filtterit läpäisty
- Ei cooldownissa
- Tilaa uudelle positiolle

### Exit Signaalit
- **Stop Loss**: -30% hinta
- **Take Profit**: +50% hinta  
- **Max Hold**: 48 tuntia
- **Manual**: Poikkeustilanteet

## 🔧 Troubleshooting

### Yleiset Ongelmat

#### "PHANTOM_PRIVATE_KEY puuttuu"
```bash
# Tarkista .env tiedosto
cat .env | grep PHANTOM_PRIVATE_KEY

# Luo uudelleen jos puuttuu
python create_solana_wallet.py
```

#### "Ei riittävästi SOL:ia"
```bash
# Tarkista balance
python -c "
from solana_trader import SolanaTrader
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
async def check():
    async with SolanaTrader(os.getenv('PHANTOM_PRIVATE_KEY')) as trader:
        balance = await trader.get_sol_balance()
        print(f'Balance: {balance:.6f} SOL')

asyncio.run(check())
"
```

#### "Jupiter quote virhe"
- Tarkista internet yhteys
- Kokeile myöhemmin (API rate limit)
- Tarkista token address

#### "Transaction epäonnistui"
- Tarkista slippage asetukset
- Varmista riittävä gas fee
- Kokeile pienemmällä summalla

### GitHub Actions Ongelmat

#### Workflow ei käynnisty
1. Tarkista `.github/workflows/solana_trader.yml` on olemassa
2. Varmista että repository on public tai Actions on enabled
3. Tarkista cron syntax

#### Secrets puuttuu
1. Settings → Secrets and variables → Actions
2. Lisää kaikki vaaditut secrets
3. Tarkista secret nimet (case sensitive)

#### Timeout virheet
- Normaalia pitkissä ajoissa
- Workflow jatkaa seuraavalla kerralla
- Tarkista lokit artifacteista

### Lokit ja Debugging

#### Lokaali Debug
```bash
# Verbose logging
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Aja koodi tässä
"
```

#### GitHub Actions Lokit
1. Actions → Workflow run
2. Klikkaa job nimeä
3. Laajenna step lokit
4. Lataa artifacts

## 📈 Optimointi

### Parannus Ehdotuksia

1. **Scoring Algorithm**
   - Lisää holder distribution analyysi
   - Ota huomioon social media signaalit
   - Paranna risk scoring

2. **Risk Management**
   - Dynamic position sizing
   - Trailing stop loss
   - Portfolio correlation analyysi

3. **Performance**
   - Async token scanning
   - Caching mechanisms
   - Batch operations

4. **Monitoring**
   - Grafana dashboard
   - Alert system
   - Performance metrics

## 🆘 Tuki

### Dokumentaatio
- [Solana Docs](https://docs.solana.com/)
- [Jupiter API](https://docs.jup.ag/)
- [GitHub Actions](https://docs.github.com/en/actions)

### Community
- [Solana Discord](https://discord.gg/solana)
- [Jupiter Discord](https://discord.gg/jup)

### Issues
Jos kohtaat ongelmia:
1. Tarkista troubleshooting osio
2. Luo GitHub issue
3. Liitä lokit ja error viestit

---

## 🎉 Valmis!

Solana Auto Trader on nyt valmis käyttöön!

### Seuraavat Askeleet:
1. ✅ Testaa lokaalisti pienillä summilla
2. ✅ Konfiguroi GitHub Actions
3. ✅ Seuraa ensimmäisiä kauppoja
4. ✅ Optimoi asetuksia tuloksien perusteella

**Onnea tradingiin! 🚀💰**

---

*⚠️ Disclaimer: Tämä on koulutus/demo tarkoituksiin. Käytä omalla vastuulla ja älä sijoita enempää kuin voit hävitä.*