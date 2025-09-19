# 🤖 Hybrid Trading Bot KehitysTiimi

**VAIN hybrid trading bot kehitys - ei muita koodeja**

## 📋 VALTUUDET

### ✅ **SALLITTU:**
- `hybrid_trading_bot.py` - Pääbot
- `real_solana_token_scanner.py` - Token skanneri  
- `automatic_hybrid_bot.py` - Automaattinen bot
- `telegram_bot_integration.py` - Telegram ilmoitukset

### 🚫 **KIELETTY:**
- Kaikki muut koodit
- Muut projektit
- Ulkoiset tiedostot

## 🛡️ TIUKAT SÄÄNNÖT

### 🚫 **KIELLETTY: TESTI TOKENIEN KÄYTTÖ**

**EI SAA KÄYTTÄÄ MISSÄÄN TILANTEESSA:**
- `TEST_TOKEN`, `test_token`, `TestToken`
- `DUMMY_TOKEN`, `dummy_token`, `DummyToken`
- `FAKE_TOKEN`, `fake_token`, `FakeToken`
- `MOCK_TOKEN`, `mock_token`, `MockToken`
- `SAMPLE_TOKEN`, `sample_token`, `SampleToken`
- `DEMO_TOKEN`, `demo_token`, `DemoToken`
- `UNKNOWN_TOKEN`, `unknown_token`, `UnknownToken`
- `PLACEHOLDER_TOKEN`, `placeholder_token`, `PlaceholderToken`

**ENFORCEMENT:**
- 🔍 **Automaattinen tarkistus** jokaisen tiedoston käsittelyn yhteydessä
- 🚫 **Hylkää tiedostot** joissa on testi tokeneita
- ⚠️ **Ei käsittelyä** jos testi tokeneita löytyy
- 📊 **Raportoi** testi tokenien löytymiset

## 🚀 Käyttö

### Käynnistys
```bash
python3 hybrid_bot_development_team.py
```

### Valinnat:
1. **Yksi hybrid bot kehityssykli** - Suorita kerran
2. **Automaattinen hybrid bot kehitys** - 24h välein
3. **Jatkuva hybrid bot seuranta** - 1h välein  
4. **Aktiivinen hybrid bot seuranta** - 15min välein

## 🤖 Automaattiset Toiminnot

### 🔍 **Botin Suorituskykyn Seuranta**
- Analysoi `hybrid_bot_output.log`
- Seuraa botin performancea
- Havaitse ongelmat

### 📁 **Tiedostojen Seuranta**
- Havaitsi muutokset VAIN hybrid bot tiedostoissa
- Ohittaa kaikki muut tiedostot
- Automaattinen muutosten tunnistus

### 🔧 **Automaattinen Kehitys**
- Analysoi hybrid bot koodin
- Parantaa suorituskykyä
- Korjaa turvallisuusongelmat
- Optimoi arkkitehtuuria

### 💾 **Raportointi**
- `hybrid_bot_development_sessions_YYYYMMDD_HHMMSS.json`
- `hybrid_bot_development_cycle_YYYYMMDD_HHMMSS.json`

## 📊 Seuratut Tiedostot

### 1. **hybrid_trading_bot.py**
- Pääbot logiikka
- Trading algoritmit
- Risk management
- Portfolio management

### 2. **real_solana_token_scanner.py**
- Token skannaus
- API integraatiot
- Data processing
- Token filtering

### 3. **automatic_hybrid_bot.py**
- Automaattinen käynnistys
- Scheduling
- Error handling
- Monitoring

### 4. **telegram_bot_integration.py**
- Telegram ilmoitukset
- Bot status raportit
- Trading signaalit
- Error notifications

## 🔄 KehitysSykli

### Vaihe 1: Botin Suorituskykyn Analyysi
- Analysoi lokitiedostot
- Havaitse ongelmat
- Mittaa performance

### Vaihe 2: Tiedostojen Muutosten Tunnistus
- Havaitsi muuttuneet hybrid bot tiedostot
- Ohittaa muut tiedostot
- Luo kehityslista

### Vaihe 3: Automaattinen Analyysi ja Parannus
- GPT-5 analysoi koodin
- Identifioi parannusmahdollisuudet
- Implementoi parannukset

### Vaihe 4: Raportointi ja Tallennus
- Tallenna kehityssessiot
- Luo yhteenveto
- Päivitä historia

## 📈 Botin Suorituskykyn Seuranta

### Seuratut Metriikat:
- **Win Rate** - Voittavien kauppojen prosentti
- **Total PnL** - Kokonaistuotto
- **Total Trades** - Kauppojen määrä
- **Profit Factor** - Tuottokerroin
- **Portfolio Value** - Portfolio arvo
- **Active Positions** - Aktiiviset positiot

### Analysoidut Ongelmat:
- **API Virheet** - DexScreener, Birdeye, CoinGecko
- **Token Ongelmat** - UNKNOWN tokenit
- **Market Cap Rajat** - Liian suuret/pienet market capit
- **Volume Rajat** - Volume ongelmat
- **Signaali Ongelmat** - Ei signaaleja

## 🛡️ Turvallisuus

### Valtuudet:
- ✅ Vain hybrid bot tiedostot
- ✅ Vain lukuoikeudet muihin tiedostoihin
- ✅ Ei muutoksia muihin koodeihin
- ✅ Lokitiedostojen analyysi

### Rajoitukset:
- 🚫 Ei muutoksia muihin tiedostoihin
- 🚫 Ei pääsyä muihin projekteihin
- 🚫 Ei ulkoisia API kutsuja (paitsi OpenAI)
- 🚫 Ei järjestelmätason muutoksia

## 📊 Raportit

### KehitysSessiot
```json
{
  "timestamp": "2025-09-14T22:58:57",
  "file_path": "automatic_hybrid_bot.py",
  "improvement_focus": "Hybrid trading bot optimointi",
  "original_analysis": {...},
  "improvement_result": {...}
}
```

### Syklin Raportti
```json
{
  "cycle_number": 1,
  "timestamp": "2025-09-14T22:58:57",
  "authorized_files": [...],
  "last_improvements": {...},
  "performance_analysis": {...}
}
```

## 🔧 Konfiguraatio

### Environment Variables
```bash
# OpenAI API avain (pakollinen)
OPENAI_API_KEY=your_api_key_here

# Telegram bot (jos käytät)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Seuranta Asetukset
- **Cycle Interval**: 24 tuntia (oletus)
- **Check Interval**: 60 minuuttia (oletus)
- **Active Monitoring**: 15 minuuttia
- **Log Analysis**: 100 viimeistä riviä

## 🚨 Troubleshooting

### Rate Limit Ongelmat
```bash
# Vähennä analyysi määrää
# Käytä pienempiä tiedostoja
# Odota ennen uutta analyysiä
```

### Context Length Ongelmat
```bash
# Vähennä max_completion_tokens
# Jaa suuret tiedostot osiin
# Käytä streaming analyysiä
```

### Tiedosto Ongelmat
```bash
# Tarkista tiedostojen oikeudet
# Varmista että tiedostot löytyvät
# Tarkista tiedostojen polut
```

## 📞 Tuki

Jos kohtaat ongelmia:
1. Tarkista että tiedostot ovat hybrid bot tiedostoja
2. Varmista OpenAI API avain
3. Tarkista tiedostojen oikeudet
4. Katso logitiedostot

---

**Hybrid Trading Bot KehitysTiimi - Vain Botin Kehitys!** 🤖📈
