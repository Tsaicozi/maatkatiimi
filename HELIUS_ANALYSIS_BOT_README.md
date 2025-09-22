# 🔍 Helius Token Analysis Bot

Kattava Solana token-analyysi botti joka hyödyntää Helius API:a real-time token-seurantaan ja analysointiin. Luo automaattisesti päivittäisiä raportteja klo 12:00 tai pyynnöstä.

## ✨ Ominaisuudet

### 🎯 Token Analyysi
- **Real-time seuranta** Helius WebSocket API:n kautta
- **Kattava metadata-analyysi** (nimi, symboli, kuvaus, linkit)
- **Hintatiedot ja markkinadata** (hinta, markkina-arvo, volyymi)
- **Likviditeettianalyysi** (poolit, likviditeetti USD)
- **Turvallisuusanalyysi** (authority renounced, LP locked/burned)
- **Holder-analyysi** (jakelu, konsentraatioriski)
- **Aktiviteettimetriikat** (ostajat, myyjät, kaupat)

### 📊 Raportointi
- **Päivittäiset automaattiset raportit** klo 12:00 (Helsinki)
- **Pyydettävät raportit** milloin tahansa
- **JSON ja tekstimuotoinen** tallentaminen
- **Top-listat** (voittajat, häviäjät, uusimmat, riskialtteimmat)
- **Markkinayhteenveto** ja suositukset
- **Riskianalyysi** ja turvallisuusarviot

### 🔧 Integraatiot
- **DiscoveryEngine integraatio** olemassa olevan järjestelmän kanssa
- **Helius API** (DAS, WebSocket, RPC)
- **Telegram-ilmoitukset** (tulossa)
- **Metrics ja monitoring** (Prometheus yhteensopiva)

### 🛡️ Turvallisuus ja Luotettavuus
- **Lokien rotaatio** (5MB, 3 varmuuskopiota)
- **Graceful shutdown** signaalien käsittely
- **Error handling** ja automaattinen uudelleenyhteys
- **Rate limiting** API-kutsuille

## 🚀 Asennus ja Konfiguraatio

### Vaatimukset
- Python 3.10+
- Helius API-avain
- Riippuvuudet: `aiohttp`, `websockets`, `pyyaml`

### 1. Helius API-avaimen hankinta
1. Rekisteröidy osoitteessa [https://www.helius.dev/](https://www.helius.dev/)
2. Luo uusi projekti ja kopioi API-avain

### 2. Konfiguraatio
Päivitä `config.yaml` tiedosto:

```yaml
io:
  rpc:
    api_key: "your-helius-api-key"
    url: "https://mainnet.helius-rpc.com/?api-key=your-key"
    ws_url: "wss://mainnet.helius-rpc.com/?api-key=your-key"

discovery:
  helius_programs:
    - "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"  # SPL Token
  sources:
    helius_logs: true

telegram:
  # Telegram-asetukset (valinnainen)
  cooldown_seconds: 900
```

Tai käytä ympäristömuuttujia:
```bash
export HELIUS_API_KEY="your-api-key"
export HELIUS_HOST="mainnet.helius-rpc.com"
```

## 📋 Käyttö

### Peruskomennot

```bash
# Luo raportti heti
python run_helius_analysis.py analyze

# Käynnistä daemon-tila (päivittäiset raportit)
python run_helius_analysis.py daemon

# Näytä ohje
python run_helius_analysis.py help
```

### Cron-ajastus (päivittäiset raportit klo 12:00)

```bash
# Aseta automaattinen cron-ajastus
./setup_cron.sh

# Tai manuaalisesti:
crontab -e
# Lisää rivi:
0 12 * * * cd /workspace && python3 run_helius_analysis.py analyze >> cron_analysis.log 2>&1
```

### Systemd-palvelu (daemon)

```bash
# Kopioi service-tiedosto
sudo cp helius-analysis-bot.service /etc/systemd/system/

# Käynnistä palvelu
sudo systemctl enable helius-analysis-bot
sudo systemctl start helius-analysis-bot

# Tarkista status
sudo systemctl status helius-analysis-bot

# Katso lokeja
journalctl -u helius-analysis-bot -f
```

## 📁 Tiedostorakenne

```
/workspace/
├── helius_token_analysis_bot.py    # Pääbotti
├── run_helius_analysis.py          # CLI-käynnistin
├── config.yaml                     # Konfiguraatio
├── helius_analysis_bot.log         # Lokitiedosto
├── helius-analysis-bot.service     # Systemd-palvelu
├── setup_cron.sh                   # Cron-asetus
├── reports/                        # Raportit
│   ├── helius_analysis_YYYYMMDD_HHMMSS.json
│   └── helius_analysis_YYYYMMDD_HHMMSS.txt
└── sources/
    └── helius_logs_newtokens.py    # Helius WebSocket source
```

## 📊 Raportin Sisältö

### Yhteenveto
- Analysoitujen tokenien määrä
- Korkean riskin tokeneiden määrä
- Lupaavien tokeneiden määrä
- Markkinatilanne (keskimääräinen hinnanmuutos, kokonaisvolyymi)

### Top-listat
- **Top Voittajat** - Suurimmat hinnankorotukset 24h
- **Top Häviäjät** - Suurimmat hinnanlasku 24h
- **Uusimmat Tokenit** - Äskettäin löydetyt tokenit
- **Korkean Riskin Tokenit** - Riskialtteimmat tokenit
- **Lupaavimmat Tokenit** - Parhaat kokonaispistemäärät

### Analyysikomponentit
- **Novelty Score** - Tokenin tuoreus
- **Liquidity Score** - Likviditeettipistemäärä
- **Distribution Score** - Holder-jakauman laatu
- **Rug Risk Score** - Rug pull -riski
- **Overall Score** - Kokonaispistemäärä (0-1)

### Turvallisuusanalyysi
- Mint/Freeze authority renounced
- LP locked/burned status
- Holder-konsentraatio
- Dev-lompakon aktiviteetti

## 🎯 API Integraatiot

### Helius API Endpoints
- `getAsset` - Token metadata
- `getTokenAccountsByOwner` - Omistustiedot
- `searchAssets` - Token-haku
- `logsSubscribe` (WebSocket) - Real-time seuranta

### DiscoveryEngine Integraatio
- Automaattinen uusien tokenien löytäminen
- Pisteytys ja filtteröinti
- Multi-source data yhdistäminen

## 🔧 Kehitys ja Mukauttaminen

### Uusien Analyysien Lisääminen
```python
# TokenAnalyzer-luokassa
async def _enrich_analysis(self, analysis: TokenAnalysis):
    # Lisää uusia analyysejä tähän
    analysis.custom_metric = await self.calculate_custom_metric(analysis.mint)
```

### Uusien Raporttien Luominen
```python
# ReportGenerator-luokassa
def generate_custom_report(self, analyses: List[TokenAnalysis]) -> CustomReport:
    # Luo mukautettu raportti
    pass
```

### Telegram-integraation Lisääminen
```python
async def send_telegram_alert(self, analysis: TokenAnalysis):
    # Lähetä Telegram-ilmoitus
    pass
```

## 📈 Metriikat ja Monitoring

Botti tuottaa Prometheus-yhteensopivia metriikoita:
- `candidates_seen_total` - Nähdyt ehdokkaat
- `candidates_filtered_total` - Filtteröidyt ehdokkaat
- `analysis_duration_seconds` - Analyysin kesto
- `api_requests_total` - API-kutsut

## 🐛 Vianmääritys

### Yleiset ongelmat

**"Helius API key puuttuu"**
```bash
# Tarkista konfiguraatio
grep -A5 "rpc:" config.yaml
# Tai aseta ympäristömuuttuja
export HELIUS_API_KEY="your-key"
```

**"WebSocket connection failed"**
```bash
# Tarkista verkko ja API-avain
curl "https://mainnet.helius-rpc.com/?api-key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}'
```

**"Permission denied" cron-asetuksessa**
```bash
# Tarkista oikeudet
ls -la setup_cron.sh
chmod +x setup_cron.sh
```

### Lokien Tarkistus
```bash
# Botin lokitiedosto
tail -f helius_analysis_bot.log

# Cron-lokitiedosto
tail -f cron_analysis.log

# Systemd-lokitiedosto
journalctl -u helius-analysis-bot -f
```

## 🔄 Päivitykset ja Ylläpito

### Säännöllinen Ylläpito
- Tarkista lokitiedostojen koko (rotaatio 5MB)
- Seuraa API-käyttöä ja rajoituksia
- Päivitä riippuvuudet säännöllisesti
- Varmista että raportit generoituvat oikein

### Versionhallinta
- Tallenna konfiguraatiomuutokset
- Testaa uudet ominaisuudet ensin test-ympäristössä
- Pidä varmuuskopiot tärkeistä raporteista

## 📞 Tuki ja Kehitys

### Helius Dokumentaatio
- [Helius API Docs](https://docs.helius.dev/)
- [DAS API](https://docs.helius.dev/compression-and-das-api)
- [WebSocket API](https://docs.helius.dev/websockets-and-webhooks)

### Kehitysideoita
- [ ] Telegram-bot integraatio
- [ ] Web-käyttöliittymä raporteille
- [ ] Automaattinen kaupankäynti (varovainen!)
- [ ] Machine learning -pohjaiset ennusteet
- [ ] Multi-chain tuki (Ethereum, BSC)

---

**⚠️ Vastuuvapauslauseke**
Tämä työkalu on tarkoitettu vain tiedonsaantiin ja analyysiin. Älä tee sijoituspäätöksiä pelkästään näiden raporttien perusteella. Tee aina oma tutkimus ja konsultoi ammattilaisia ennen sijoittamista.

**🔒 Turvallisuus**
Älä jaa API-avaimiasi tai private key -avaimiasi kenenkään kanssa. Pidä ne turvassa ympäristömuuttujissa tai salattuina konfiguraatiotiedostoina.