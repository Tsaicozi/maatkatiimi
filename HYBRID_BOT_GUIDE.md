# 🤖 Hybrid Trading Bot - Oikeat Tokenit, Demo Valuutta

## 📋 Yleiskatsaus

Hybrid Trading Bot on edistynyt trading järjestelmä joka yhdistää **oikeat markkina tiedot** **demo tradingin** kanssa. Bot skannaa oikeita Solana tokeneita oikeista markkinoista mutta käyttää demo valuuttaa kaupoissa.

## 🎯 Pääominaisuudet

### 🔍 **Oikeat Markkina Tiedot**
- **DexScreener API**: Hakee oikeita Solana token pareja
- **Birdeye API**: Hakee trending tokeneita
- **Real-time hinnat**: Oikeat markkina hinnat ja volyymit
- **Oikeat DEX tiedot**: Pair addressit ja DEX tiedot

### 💰 **Demo Trading**
- **$10,000 demo portfolio**: Turvallinen testaus
- **Simuloidut kaupat**: Ei oikeita kauppoja
- **Realistiset hinnat**: Käyttää oikeita markkina hintoja
- **Performance tracking**: Tarkka suorituskyvyn seuranta

### ⚡ **Ultra-Fresh Kriteerit**
- **Ikä**: 1-5 minuuttia
- **Market Cap**: $10K - $500K
- **Volume**: Minimi $10K
- **Liquidity**: Minimi $10K

### 🎯 **Optimoitu Strategia**
- **Entry Score**: Tekninen analyysi (0-1)
- **Risk Score**: Riskien arviointi (0-1)
- **Momentum Score**: Liikkeen analyysi (0-1)
- **Overall Score**: Yhdistetty arviointi

## 🚀 Käynnistys

### 1. **Yksittäinen Testi**
```bash
python3 hybrid_trading_bot.py
```

### 2. **Automaattinen Bot**
```bash
python3 automatic_hybrid_bot.py
```

## 📊 Botin Toiminta

### **1. Token Skannaus**
```
🔍 Skannataan oikeita Solana tokeneita oikeista markkinoista...
✅ DexScreener: Löydettiin X tokenia
✅ Birdeye: Löydettiin Y tokenia
✅ Löydettiin Z ultra-fresh Solana tokenia
```

### **2. Analyysi**
- **Entry Score**: Age, market cap, volume, momentum
- **Risk Score**: Liquidity, holders, concentration
- **Momentum Score**: Price change, volume, fresh holders

### **3. Trading Signaalit**
- **BUY**: Entry score > 0.6, Risk score < 0.7
- **SELL**: Take profit 30%, Stop loss 15%, Time limit 15min

### **4. Portfolio Management**
- **Max positions**: 15
- **Position size**: $100 per position
- **Portfolio rotation**: Automaattinen vanhojen positioiden sulkeminen

## 📈 Performance Metriikat

### **Trading Metriikat**
- **Win Rate**: Voittavien kauppojen prosentti
- **Total PnL**: Kokonaisvoitto/tappio
- **Profit Factor**: Voittojen/tappioiden suhde
- **Max Drawdown**: Suurin tappio

### **Portfolio Metriikat**
- **Total Value**: Portfolio kokonaisarvo
- **Active Positions**: Aktiivisten positioiden määrä
- **Cash**: Vapaana oleva raha
- **PnL**: Realisoitu voitto/tappio

## 📱 Telegram Integraatio

### **Reaaliaikaiset Ilmoitukset**
- **Position avattu**: Token, hinta, määrä, FDV
- **Position suljettu**: PnL, syy, kesto
- **Portfolio update**: Arvo, PnL, positioita

### **Raportit**
- **Tunni raportti**: Performance, muutokset, tilastot
- **Päivittäinen raportti**: Kokonaiskuva, analyysi
- **Error ilmoitukset**: Virheet ja varoitukset

## 🔧 Konfiguraatio

### **Environment Variables**
```bash
# .env tiedosto
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
BIRDEYE_API_KEY=your_birdeye_key  # Vapaaehtoinen
```

### **Trading Parametrit**
```python
# hybrid_trading_bot.py
self.max_positions = 15        # Max positioita
self.position_size = 100.0     # $100 per position
self.take_profit = 0.30        # 30% take profit
self.stop_loss = 0.15          # 15% stop loss
self.max_age_minutes = 5       # Max ikä minuutteina
```

## 📁 Tiedostot

### **Päämoduulit**
- `hybrid_trading_bot.py`: Pää trading bot
- `automatic_hybrid_bot.py`: Automaattinen versio
- `telegram_bot_integration.py`: Telegram integraatio

### **Data Tiedostot**
- `hybrid_trading_analysis_YYYYMMDD_HHMMSS.json`: Analyysi tulokset
- `hybrid_trading_bot.log`: Bot logit
- `automatic_hybrid_bot.log`: Automaattinen bot logit

## 🎯 Hybrid Botin Edut

### **1. Realistinen Testaus**
- Oikeat markkina tiedot
- Realistiset hinnat ja volyymit
- Oikeat token nimet ja addressit

### **2. Turvallinen**
- Ei oikeita kauppoja
- Demo valuutta
- Ei riskejä

### **3. Kattava**
- Useita API:ita
- Fallback mock data
- Robust error handling

### **4. Seurattava**
- Yksityiskohtaiset logit
- Performance metriikat
- Telegram ilmoitukset

## 🔍 Token Skannaus

### **DexScreener API**
- Hakee oikeita Solana token pareja
- Real-time hinnat ja volyymit
- DEX tiedot ja pair addressit

### **Birdeye API**
- Trending tokeneita
- Market cap ja volume data
- Price change tiedot

### **Fallback Mock Data**
- Jos API:t eivät toimi
- Realistisia Solana token nimiä
- Oikeat markkina arvot

## 📊 Analyysi Metodit

### **Entry Score (0-1)**
```python
# Age bonus (1-5 minuuttia)
if 1 <= token.age_minutes <= 5:
    score += 0.3

# Market cap (20K-100K)
if 20000 <= token.market_cap <= 100000:
    score += 0.2

# Volume spike
if token.volume_24h > 10000:
    score += 0.2

# Price momentum
if token.price_change_24h > 50:
    score += 0.2
```

### **Risk Score (0-1, alempi = parempi)**
```python
# Market cap risk
if token.market_cap < 10000:
    risk += 0.3

# Liquidity risk
if token.liquidity < 10000:
    risk += 0.3

# Holder concentration risk
if token.holders < 100:
    risk += 0.2
```

### **Momentum Score (0-1)**
```python
# Price momentum
if token.price_change_24h > 100:
    momentum += 0.4

# Volume momentum
if token.volume_24h > 100000:
    momentum += 0.3

# Fresh holders
if token.fresh_holders_1d > 20:
    momentum += 0.2
```

## 🎯 Trading Kriteerit

### **BUY Signaalit**
- Entry score > 0.6
- Risk score < 0.7
- Age 1-5 minuuttia
- Market cap $10K-$500K
- Portfolio rajoitukset OK

### **SELL Signaalit**
- Take profit 30%
- Stop loss 15%
- Time limit 15 minuuttia
- Portfolio rotation

## 📈 Performance Seuranta

### **Real-time Metriikat**
- Portfolio arvo
- PnL seuranta
- Win rate
- Profit factor

### **Historical Data**
- JSON analyysi tiedostot
- Log tiedostot
- Performance trends

## 🚨 Error Handling

### **API Virheet**
- Graceful fallback mock dataan
- Retry logiikka
- Error logging

### **Trading Virheet**
- Position validation
- Portfolio checks
- Error recovery

## 🔧 Kehitys

### **Tulevat Ominaisuudet**
- Lisää API:ita
- Parannettu analyysi
- Machine learning
- Backtesting

### **Optimointi**
- Performance parannukset
- Memory optimization
- Async improvements

## 📞 Tuki

Jos sinulla on kysymyksiä tai ongelmia:

1. **Tarkista logit**: `hybrid_trading_bot.log`
2. **Tarkista analyysi**: `hybrid_trading_analysis_*.json`
3. **Tarkista Telegram**: Bot ilmoitukset
4. **Tarkista environment**: `.env` tiedosto

---

**🎯 Hybrid Trading Bot - Oikeat tokenit, Demo valuutta, Realistinen testaus!**
