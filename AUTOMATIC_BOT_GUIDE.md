# Automaattinen Trading Bot - Käyttöohjeet

## 🚀 Yleiskatsaus

Automaattinen Trading Bot toimii itsenäisesti 24/7 ja lähettää raportit Telegramiin tunnin välein. Bot skannaa uusia tokeneita, analysoi niitä ja tekee automaattisesti kauppoja.

## 📱 Telegram Setup

### 1. Luo Telegram Bot
1. Avaa Telegram ja etsi `@BotFather`
2. Lähetä `/newbot`
3. Anna botille nimi (esim. "My Trading Bot")
4. Anna botille username (esim. "my_trading_bot")
5. Kopioi bot token

### 2. Hae Chat ID
1. Lähetä viesti botillesi
2. Avaa selaimessa: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Etsi `"chat":{"id":` ja kopioi numero

### 3. Aseta API Avaimet
Luo `.env` tiedosto projektin juureen:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# Trading Bot Configuration
INITIAL_CAPITAL=10000.0
SCAN_INTERVAL=300
REPORT_INTERVAL=3600
```

## 🤖 Bot Ominaisuudet

### Automaattinen Toiminta:
- **Skannaus**: 5 minuutin välein uusia tokeneita
- **Raportit**: 1 tunnin välein Telegramiin
- **Kauppat**: Automaattisesti signaalien perusteella
- **Riskienhallinta**: Stop loss ja take profit

### Telegram Ilmoitukset:
- 🚀 **Käynnistys/Sammutus**: Bot tila
- 📡 **Trading signaalit**: Uudet signaalit
- 💼 **Kauppat**: Position avattu/suljettu
- 📊 **Tunnin raportit**: Portfolio ja tilastot
- 📈 **Päivän yhteenveto**: Päivän suorituskyky
- 🚨 **Virhe ilmoitukset**: Ongelmat

## 🚀 Käynnistys

### 1. Asenna Riippuvuudet:
```bash
pip install pandas numpy requests aiohttp asyncio python-dotenv
```

### 2. Käynnistä Bot:
```bash
python3 automatic_trading_bot.py
```

### 3. Sammuta Bot:
```bash
# Paina Ctrl+C tai lähetä SIGTERM signaali
kill <process_id>
```

## 📊 Raportit

### Tunnin Raportti:
```
📊 TUNNIN RAPORTTI

Portfolio:
💰 Arvo: $10,145.32
💵 Käteinen: $9,854.68
📊 Exposure: $145.32
📈 Avoimet: 3
📉 Suljetut: 0
📊 Päivän tuotto: +1.45%

Bot Tilastot:
🔍 Skannauksia: 12
📡 Signaaleja: 8
💼 Kauppoja: 3
✅ Onnistumis%: 100.0%
```

### Päivän Yhteenveto:
```
📊 PÄIVÄN YHTEENVETO

Kauppatilastot:
💼 Yhteensä: 15
🟢 Voittavat: 12
🔴 Häviävät: 3
💰 Kokonais P&L: $245.67

Parhaat/Huonoimmat:
🏆 Paras: $89.45
💸 Huonoin: -$23.12
```

## ⚙️ Konfiguraatio

### Skannaus Aikaväli:
```python
self.scan_interval = 300  # 5 minuuttia
```

### Raportti Aikaväli:
```python
self.report_interval = 3600  # 1 tunti
```

### Riskienhallinta:
```python
self.max_position_size = 0.05  # 5% portfolio per position
self.max_total_exposure = 0.8  # 80% portfolio exposure
self.stop_loss_percentage = 0.1  # 10% stop loss
self.take_profit_percentage = 0.3  # 30% take profit
```

## 📁 Tiedostot

### Log Tiedostot:
- `automatic_trading_bot.log` - Bot lokit
- `demo_trading_bot.log` - Trading lokit
- `telegram_bot.log` - Telegram lokit

### Data Tiedostot:
- `demo_trading_analysis_*.json` - Analyysi tulokset
- `final_stats_*.json` - Lopulliset tilastot
- `portfolio_state_*.json` - Portfolio tila

## 🔧 Vianmääritys

### Bot ei käynnisty:
1. Tarkista `.env` tiedosto
2. Tarkista Python riippuvuudet
3. Tarkista log tiedostot

### Telegram ei toimi:
1. Tarkista bot token
2. Tarkista chat ID
3. Lähetä testi viesti botille

### Ei kauppoja:
1. Tarkista skannaus aikaväli
2. Tarkista token kriteerit
3. Tarkista riskienhallinta säännöt

## 📈 Suorituskyky

### Bot Tilastot:
- **Skannauksia**: Tokeneita analysoitu
- **Signaaleja**: Trading signaaleja generoitu
- **Kauppoja**: Positioneita avattu/suljettu
- **Onnistumisprosentti**: Voittavien kauppojen osuus

### Portfolio Mittarit:
- **Portfolio arvo**: Kokonaisarvo
- **Käteinen**: Vapaat varat
- **Exposure**: Aktiivisten positionien arvo
- **Päivän tuotto**: Päivän tuotto prosentteina

## ⚠️ Tärkeät Huomiot

### Demo vs Täysi Versio:
- **Demo**: Mock data, ei oikeita kauppoja
- **Täysi**: Oikea data, oikeat kaupat (varoitus!)

### Riskit:
- **Korkea riski**: Uudet tokenit ovat epävakaita
- **Likviditeetti**: Pienet tokenit voivat olla vaikeita myydä
- **Volatiliteetti**: Äkilliset hinnanmuutokset
- **Tekninen riski**: Bot voi tehdä virheitä

### Suositukset:
1. **Aloita pienellä pääomalla** (alle 1000€)
2. **Testaa demo versiolla** ensin
3. **Seuraa aktiivisesti** botin toimintaa
4. **Aseta stop loss** kaikille positioneille
5. **Hajauta riskit** useisiin tokeneihin

## 🎯 Käyttötapaukset

### 1. Päivittäinen Seuranta:
- Bot toimii itsenäisesti
- Saat tunnin välein raportteja
- Reaaliaikaiset ilmoitukset kaupoista

### 2. Viikonloppu Trading:
- Bot toimii 24/7
- Ei tarvitse olla paikalla
- Automaattinen riskienhallinta

### 3. Pitkäaikainen Sijoittaminen:
- Jatkuva token skannaus
- Automaattinen position hallinta
- Yksityiskohtaiset tilastot

## 🔮 Tulevaisuuden Kehitykset

### Suunnitellut Parannukset:
1. **Mobile App**: Puhelin sovellus
2. **Web Dashboard**: Web-pohjainen hallintapaneeli
3. **Advanced Analytics**: Syvällisempi analyysi
4. **Multi-Exchange**: Useita pörssejä
5. **Social Trading**: Yhteisö ominaisuudet

## 📞 Tuki

### Dokumentaatio:
- **Koodi kommentit**: Kaikki funktiot dokumentoitu
- **Log tiedostot**: Yksityiskohtaiset lokit
- **JSON raportit**: Analyysi tulokset

### Virheiden Korjaus:
1. **Tarkista logit**: `automatic_trading_bot.log`
2. **API avaimet**: Varmista että ovat oikein
3. **Riippuvuudet**: Asenna kaikki paketit
4. **Internet yhteys**: Tarvitaan API kutsuja varten

## 🎉 Yhteenveto

Automaattinen Trading Bot on täydellinen järjestelmä uusien kryptovaluuttojen tradingiin:

- ✅ **Itsenäinen toiminta** 24/7
- ✅ **Telegram ilmoitukset** reaaliajassa
- ✅ **Tunnin välein raportit** portfolio tilasta
- ✅ **Automaattinen riskienhallinta**
- ✅ **Yksityiskohtaiset tilastot**

**Bot on nyt valmis automaattiseen tradingiin!** 🚀

---

*Kehitetty ideaointi tiimin avulla - Automaattinen trading bot uusille nouseville tokeneille* 🎯
