# Solana Auto Trader - GitHub Actions Setup

## 📋 Yleiskatsaus

Tämä projekti sisältää automaattisen Solana-token traderin, joka:
- Skannaa uusia Solana tokeneita DexScreener API:sta
- Analysoi tokenit (likviditeetti, volyymi, momentum)
- Ostaa lupaavimmat tokenit automaattisesti
- Hallitsee positioita (stop-loss, take-profit, time-based exits)
- Lähettää Telegram-ilmoitukset

## 🚀 GitHub Actions Setup

### Vaihe 1: Luo GitHub Repository

1. Luo uusi repository GitHubissa (tai käytä olemassa olevaa)
2. Pushaa koodi repositoryyn:

```bash
git init
git add .
git commit -m "Initial commit: Solana auto trader"
git branch -M main
git remote add origin https://github.com/KÄYTTÄJÄNIMI/REPO_NIMI.git
git push -u origin main
```

### Vaihe 2: Lisää Secrets

Mene GitHub repositoryn asetuksiin:
**Settings → Secrets and variables → Actions → New repository secret**

Lisää seuraavat secretit:

#### Pakolliset:
- `PHANTOM_PRIVATE_KEY`: Solana-lompakon private key (base58)
  ```
  5VK1QhvfNTwjCyYpGzbmL3YnDogCkCMmsQB55DTAAW6zfcPuxHFzy8DTb82cnspiVf9yvU33Sm5A1cPM7LyC3hdV
  ```

- `TELEGRAM_TOKEN`: Telegram bot token
  ```
  8432276350:AAGlIOa-XDBDwRxPlyso-tnJH279EQC7pUI
  ```

- `TELEGRAM_CHAT_ID`: Telegram chat ID
  ```
  7939379291
  ```

#### Valinnaiset (oletusarvot käytössä jos ei aseta):
- `SOLANA_RPC_URL`: `https://api.mainnet-beta.solana.com`
- `HELIUS_API_KEY`: (tyhjä = käytä julkista RPC:tä)
- `MIN_LIQUIDITY_USD`: `5000`
- `MIN_24H_VOLUME_USD_SOLANA`: `2000`
- `MAX_TOKEN_AGE_HOURS`: `168`
- `POSITION_SIZE_SOL`: `0.05`
- `MAX_POSITIONS`: `3`
- `STOP_LOSS_PCT`: `0.30`
- `TAKE_PROFIT_PCT`: `0.50`
- `MAX_HOLD_HOURS`: `48`
- `MAX_SLIPPAGE_BPS`: `300`
- `COOLDOWN_HOURS`: `24`

### Vaihe 3: Aktivoi Workflow

1. Workflow aktivoituu automaattisesti kun pushaat koodin
2. Workflow ajaa joka 30 minuutti (`cron: '*/30 * * * *'`)
3. Voit myös ajaa manuaalisesti:
   - Mene **Actions → Solana Auto Trader → Run workflow**

### Vaihe 4: Seuraa Toimintaa

1. **GitHub Actions lokit:**
   - **Actions**-välilehti repositoryssä
   - Näet jokaisen ajon lokit

2. **Telegram-ilmoitukset:**
   - Entry alerts (uusi positio avattu)
   - Exit alerts (positio suljettu)
   - PnL-seuranta

3. **Trading state:**
   - `solana_positions.json` - Avoimet/suljetut positiot
   - `solana_cooldown.json` - Cooldown-lista
   - Tallennetaan automaattisesti repositoryyn

## 📊 Trading Parametrit

### Position Sizing
- **POSITION_SIZE_SOL**: 0.05 SOL per kauppa (~$7.50)
- **MAX_POSITIONS**: Max 3 avointa positiota kerralla
- **Total exposure**: Max 0.15 SOL (~$22.50)

### Risk Management
- **STOP_LOSS_PCT**: 30% stop-loss
- **TAKE_PROFIT_PCT**: 50% take-profit
- **MAX_HOLD_HOURS**: 48h max hold time
- **COOLDOWN_HOURS**: 24h cooldown per token

### Filtterit
- **MIN_LIQUIDITY_USD**: $5,000 min likviditeetti
- **MIN_24H_VOLUME_USD_SOLANA**: $2,000 min volyymi
- **MAX_TOKEN_AGE_HOURS**: 168h (7 päivää) max ikä
- **MIN_SCORE**: 5/12 min pisteytys

## 🔐 Turvallisuus

### ⚠️ Tärkeää:
1. **Älä koskaan jaa private keyä** julkisesti
2. **Käytä VAIN GitHub Secretsia** - älä laita avaimia koodiin
3. **Käytä erillistä trading wallettia** - älä käytä pääkassaa
4. **Rajoita lompakossa oleva summa** - esim. 1-2 SOL max
5. **Testaa ensin pienillä summilla**

### Private Repository Suositus:
Jos haluat pitää strategiasi yksityisenä, vaihda repository privateksi:
**Settings → General → Danger Zone → Change visibility → Make private**

## 📈 Seuranta ja Optimointi

### GitHub Actions Rajoitukset:
- **Public repo**: Ilmainen
- **Private repo**: 2000 minuuttia/kk ilmaiseksi
- **Yksi ajo**: ~2-5 minuuttia
- **30 min sykli**: ~1440 ajoa/kk = ~2880-7200 min/kk

Jos haluat tiheämmän seurannan (esim. joka 15 min), harkitse:
1. Helius RPC + parempi endpoint
2. Render/Railway/Fly.io continuous deployment

### Optimointi:
1. **Lisää HELIUS_API_KEY** nopeampaan data-hakuun
2. **Säädä filttereitä** löytääksesi parempia tokeneita
3. **Muuta position sizea** riskihalun mukaan
4. **Seuraa PnL:ää** ja säädä parametreja

## 🐛 Vianmääritys

### Workflow ei käynnisty:
1. Tarkista että `.github/workflows/solana_trader.yml` on oikein
2. Varmista että kaikki secretit on lisätty
3. Tarkista Actions-välilehden virhelokit

### "No tokens found":
- Filtterit voivat olla liian tiukat
- Laske `MIN_LIQUIDITY_USD` ja `MIN_24H_VOLUME_USD_SOLANA`
- Nosta `MAX_TOKEN_AGE_HOURS`

### Kaupat eivät mene läpi:
- Tarkista lompakon saldo (min 0.1 SOL suositeltu)
- Nosta `MAX_SLIPPAGE_BPS` jos tarvitaan
- Tarkista että Jupiter API toimii

## 📞 Tuki

Jos kohtaat ongelmia:
1. Tarkista GitHub Actions lokit
2. Tarkista Telegram-ilmoitukset
3. Tarkista `solana_auto_trader.log`

## ⚖️ Vastuuvapauslauseke

Tämä on koulutus-/demonstraatiotarkoitukseen tehty botti. 
Kryptovaluuttakaupankäynti sisältää suuria riskejä. 
Käytä omalla vastuullasi ja vain summilla joita sinulla on varaa menettää.

