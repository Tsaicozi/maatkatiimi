# PumpPortal Integration - Hybrid Trading Bot

## Yleiskatsaus

PumpPortal WebSocket-integraatio on nyt integroitu Hybrid Trading Bot:iin! Tämä tuo reaaliaikaisen kryptovaluutta-datan osaksi hybrid botin token-skanningia.

## Uudet ominaisuudet

### 🔥 PumpPortal Token Skanning
- **Reaaliaikainen data** - WebSocket-yhteys PumpPortal:iin
- **Hot token -löydöt** - Löydä kuumimmat tokenit markkinoilla
- **Trading activity** - Analysoi kaupankäyntiaktiviteettia
- **Crypto momentum** - Laske markkinamomentum

### 🔄 Hybrid Bot Integraatio
- PumpPortal toimii **täydentävänä** Pump.fun API:lle
- Jos Pump.fun API epäonnistuu (530 virhe), PumpPortal ottaa tilan
- Molemmat API:t toimivat rinnakkain parhaan tuloksen saamiseksi

## Tekniset yksityiskohdat

### WebSocket-yhteys
```
wss://pumpportal.fun/api/data
```

### Tilaamat tapahtumat
- `subscribeNewToken` - Uusien tokenien luomistapahtumat
- `subscribeTokenTrade` - Token-kauppatapahtumat
- `subscribeAccountTrade` - Tili-kauppatapahtumat
- `subscribeMigration` - Token-migraatiotapahtumat

### Data-muunnos
PumpPortal-data muunnetaan `HybridToken`-objekteiksi:
- Token address → Symbol ja name
- Volume data → Price ja market cap
- Buy/sell ratio → Social score
- Trading activity → Technical score

## Käyttö

### Automaattinen käyttö
PumpPortal-integraatio toimii automaattisesti hybrid botissa:

```bash
python hybrid_trading_bot.py
```

### Testaus
Testaa PumpPortal-integraatiota:

```bash
python test_pumpportal_hybrid.py
```

## Log-messages

### Onnistunut integraatio
```
✅ PumpPortal analyzer alustettu
✅ PumpPortal: Löydettiin X tokenia
```

### Virheenkäsittely
```
⚠️ PumpPortal analyzer alustus epäonnistui: [virhe]
PumpPortal API virhe: [virhe]
```

## API Status

Hybrid bot näyttää nyt PumpPortal-statusin:
```
🔑 API avaimet: DexScreener=✅, CMC=✅, CC=✅, PumpPortal=✅
```

## Token Data

### PumpPortal-tokeneita tunnistetaan:
- `dex="PumpPortal"`
- `pair_address` = token address
- Reaaliaikainen volume ja trading data

### Skorit
- **Social Score**: Buy/sell ratio pohjalta
- **Technical Score**: Volume pohjalta  
- **Momentum Score**: Buy/sell ratio
- **Risk Score**: Volume pohjalta (korkea volume = matala riski)

## Riippuvuudet

```bash
pip install websockets
```

## Virheenkäsittely

### WebSocket-yhteys
- Automaattinen reconnection
- Graceful degradation jos yhteys epäonnistuu
- Fallback Pump.fun API:lle

### Data-parsinta
- Turvallinen virheenkäsittely
- Default-arvot puuttuville kentille
- Logging kaikista virheistä

## Performance

### Optimointi
- Yksi WebSocket-yhteys kerrallaan
- Efficient data-parsinta
- Minimal memory usage

### Rate Limiting
- PumpPortal ei vaadi API-avaimia
- Ei rate limit -rajoituksia
- Reaaliaikainen data

## Tulevaisuuden kehitykset

- [ ] Real-time WebSocket streaming
- [ ] Advanced momentum indicators
- [ ] Multi-timeframe analysis
- [ ] Sentiment analysis integration
- [ ] Portfolio optimization

## Troubleshooting

### PumpPortal ei toimi
1. Tarkista websockets-kirjasto: `pip install websockets`
2. Tarkista internet-yhteys
3. Katso log-viestit virheistä

### Ei tokeneita löytynyt
1. PumpPortal saattaa olla tyhjä
2. Tarkista WebSocket-yhteys
3. Fallback Pump.fun API:lle

### Performance-ongelmat
1. Vähennä skanning-frekvenssiä
2. Optimoi WebSocket-yhteys
3. Käytä caching-ratkaisuja

## Esimerkki Output

```
✅ PumpPortal analyzer alustettu
✅ PumpPortal: Löydettiin 5 tokenia
🔍 Analysoidaan token ABC12345: Age=15min, MC=$50,000, Tech=0.85, Risk=0.15, PriceChg=125.3%, Vol=$2,500,000, Social=0.72
```

## Tuki

Jos kohtaat ongelmia:
1. Tarkista `test_pumpportal_hybrid.py` -tulokset
2. Katso `hybrid_bot_output.log` -tiedosto
3. Varmista että websockets on asennettu
4. Tarkista internet-yhteys
