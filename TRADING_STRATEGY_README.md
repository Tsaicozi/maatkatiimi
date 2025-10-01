# 🚀 Live Trading Strategy for Helius Token Scanner

## Yleiskatsaus

Tämä livekaupan strategia on optimoitu **nopeille nousuille ja laskuille** Solana-ekosysteemissä. Se integroituu Helius Token Scanner bottiin ja generoi automaattisia kauppasignaaleja korkealaatuisille tokeneille.

## 🎯 Strategian Periaatteet

### "Momentum Breakout + Quick Exit"

1. **Korkea momentum** - Tokeneita joilla on vahva 5min ja 1h nousu
2. **Vahva volyymivahvistus** - 20k+ USD päivittäinen volyymi
3. **Aktiivinen kauppa** - 10+ kauppaa/24h
4. **Nopea sisään/ulos** - 5-30 minuutin positiot
5. **Riskinhallinta** - 2-5% stop loss

## 📊 Token-tyypit ja Strategiat

### 🎪 Pump.fun Tokeneita
- **Korkein riski, korkein tuotto**
- **Confidence bonus:** +10%
- **Take profit:** 22.5% (aggressiivinen)
- **Momentum kynnys:** 8%+ 5minuutissa

### 🐕 Meme Tokeneita  
- **Keskitaso riski/tuotto**
- **Confidence bonus:** +5%
- **Take profit:** 18%
- **Momentum kynnys:** 12%+ 5minuutissa

### 🔧 Utility Tokeneita
- **Alhaisin riski, keskitaso tuotto**
- **Take profit:** 15%
- **Momentum kynnys:** 15%+ 5minuutissa

## ⚙️ Konfiguraatio

### Riskinhallinta
```bash
TRADING_MAX_POSITION_SIZE=0.02    # 2% portfoliosta per kauppa
TRADING_STOP_LOSS=0.03           # 3% stop loss
TRADING_TAKE_PROFIT=0.15         # 15% take profit
TRADING_MAX_HOLD_TIME=1800       # 30 minuuttia max
```

### Sisäänmenokriteerit (synkronoituna scanner bottiin)
```bash
TRADING_MIN_LIQUIDITY=15000      # 15k USD likviditeetti
TRADING_MIN_VOLUME_24H=20000     # 20k USD volyymi
TRADING_MIN_UTIL=0.4             # Min util-suhde
TRADING_MAX_UTIL=6.0             # Max util-suhde
TRADING_MIN_TRADES_24H=10        # 10+ kauppaa/24h
TRADING_MIN_BUYERS_30M=5         # 5+ ostajaa/30min
```

### Momentum-kriteerit
```bash
TRADING_MIN_PRICE_CHANGE_5M=0.05  # 5% nousu 5minuutissa
TRADING_MIN_PRICE_CHANGE_1H=0.10  # 10% nousu 1 tunnissa
TRADING_MAX_AGE_MINUTES=120       # Max 2 tuntia vanha
```

## 🎛️ Valmiit Strategiat

### 1. Balanced Strategy (Suositeltu)
- **Position size:** 2%
- **Stop loss:** 3%
- **Take profit:** 15%
- **Max hold:** 30 min
- **Confidence kynnys:** 60%

### 2. Aggressive Strategy
- **Position size:** 5%
- **Stop loss:** 5%
- **Take profit:** 25%
- **Max hold:** 15 min
- **Confidence kynnys:** 50%

### 3. Conservative Strategy
- **Position size:** 1%
- **Stop loss:** 2%
- **Take profit:** 10%
- **Max hold:** 60 min
- **Confidence kynnys:** 70%

## 🧠 Confidence-laskenta

Confidence-pisteet (0-100%):

### Momentum (40% paino)
- 5min nousu >10%: +40 pistettä
- 5min nousu >5%: +20 pistettä
- 1h nousu >20%: +30 pistettä
- 1h nousu >10%: +15 pistettä

### Volyymi/Likviditeetti (30% paino)
- Volyymi 100k+: +30 pistettä
- Likviditeetti 50k+: +30 pistettä

### Aktiivisuus (20% paino)
- 20+ ostajaa/30min: +20 pistettä
- Optimaalinen util (0.5-5.0): +20 pistettä

### Ikä (10% paino)
- Uudempi = parempi (max 2h)

### Token-tyyppi bonus
- Pump.fun: +10 pistettä
- Meme: +5 pistettä

## 📈 Esimerkki Signaaleista

### ✅ Hyvä Signaali
```
Token: PUMP (Pump.fun)
Confidence: 76.0%
Entry: $0.00012300
Target: $0.00015068 (+22.5%)
Stop Loss: $0.00011931 (-3.0%)
Reasoning: Strong momentum: 12.5% in 5m, 25.3% in 1h
```

### ❌ Hylätty Signaali
```
Token: LOW
Reason: Low momentum (1.2% in 5m, 3.5% in 1h)
Confidence: 24.7% (below 60% threshold)
```

## 🔄 Position Management

### Automaattiset Exittit
1. **Take Profit** - Saavutetaan tavoitehinta
2. **Stop Loss** - Tappio raja ylitetty
3. **Time Exit** - Max hold time ylitetty

### Reaaliaikainen Seuranta
- Hinta-päivitykset 30s välein
- Automaattinen position sulkeminen
- PnL seuranta ja raportointi

## 📱 Telegram Integraatio

### Signaali-ilmoitukset
- Reaaliaikaiset kauppasignaalit
- Confidence-pisteet ja perustelut
- Entry/target/stop loss hinnat

### Kauppa-ilmoitukset
- BUY/SELL toteutukset
- Position avaus/sulkeminen
- PnL ja portfolio tilanne

### Päivittäiset raportit
- Voittoprosentti
- Päivittäinen PnL
- Aktiiviset positiot

## 🚀 Käynnistys

### 1. Konfiguraatio
```bash
# Kopioi .env tiedosto ja täytä API-avaimet
cp .env.example .env

# Muokkaa trading-asetuksia
nano .env
```

### 2. Testaus
```bash
# Testaa strategiaa
python3 test_trading_strategy.py
```

### 3. Paper Trading
```bash
# Käynnistä paper trading (ei oikeita kauppoja)
TRADING_PAPER_MODE=true python3 trading_bot_integration.py
```

### 4. Live Trading
```bash
# Varoitus: Oikeat rahat riskissä!
TRADING_ENABLED=true python3 trading_bot_integration.py
```

## ⚠️ Riskit ja Varoitukset

### Korkea Riskitaso
- **Kryptovaluutat ovat erittäin volatiliteettia**
- **Mahdollinen täydellinen tappio**
- **Testaa aina paper tradingilla ensin**

### Tekniset Riskit
- **API-virheet voivat aiheuttaa tappioita**
- **Verkko-ongelmat voivat estää exitit**
- **DEX-likviditeetti voi loppua**

### Suositukset
1. **Aloita pienellä summalla**
2. **Testaa paper tradingilla**
3. **Seuraa aktiivisesti**
4. **Aseta stop lossit**
5. **Älä sijoita enempää kuin voit menettää**

## 📊 Performance Tracking

### Metriikat
- **Win rate** - Voittoprosentti
- **Avg PnL per trade** - Keskimääräinen tuotto
- **Max drawdown** - Suurin tappio
- **Sharpe ratio** - Risk-sopeutettu tuotto

### Raportointi
- Reaaliaikainen seuranta
- Päivittäiset yhteenvedot
- Viikoittaiset analyysit

## 🔧 Kehitys

### Tulevat Ominaisuudet
- **Birdeye buyers30m provider** - Parempi ostajien erottelu
- **Top holders analyysi** - Keskittyneisyyden tarkistus
- **Fresh 1D/7D signaalit** - Trendianalyysi
- **DexScreener trending poller** - Lisäkonfluenssi

### AB-testaus
- **Kynnysarvojen optimointi**
- **24h telemetria**
- **Conversion tracking**
- **Canary-tila** - Vertailu löysemmillä rajoilla

## 📞 Tuki

Jos sinulla on kysymyksiä tai ongelmia:
1. Tarkista logit: `tail -f helius_token_scanner_stdout.log`
2. Testaa strategiaa: `python3 test_trading_strategy.py`
3. Tarkista konfiguraatio: `.env` tiedosto

---

**Muista: Kryptovaluuttakaupankäynti on riskialtista. Sijoita vain sen verran kuin voit menettää!** ⚠️
