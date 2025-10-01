# 🚀 Solana Auto Trader - Deployment Guide

Nopea ohje Solana Auto Trader:n käyttöönottoon GitHub Actions:lla.

## ⚡ Pika-deployment (5 minuuttia)

### 1. 🔐 Luo Wallet & Hanki Private Key
```bash
python3 simple_wallet_creator.py
# Valitse: 1 (Luo uusi)
# Kopioi private key
# Rahoita wallet 0.6+ SOL
```

### 2. 📱 Luo Telegram Bot (Valinnainen)
1. [@BotFather](https://t.me/botfather) → `/newbot`
2. Anna nimi ja username
3. Kopioi bot token

```bash
python3 get_telegram_chat_id.py
# Syötä bot token
# Lähetä viesti botille
# Kopioi chat ID
```

### 3. 🔧 Lisää GitHub Secrets
Repository → Settings → Secrets and variables → Actions

**Lisää secrets:**
- `PHANTOM_PRIVATE_KEY`: [wallet_private_key]
- `TELEGRAM_TOKEN`: [bot_token] (valinnainen)
- `TELEGRAM_CHAT_ID`: [chat_id] (valinnainen)

### 4. 🚀 Aktivoi
```bash
git add .
git commit -m "Deploy Solana Auto Trader"
git push origin main
```

### 5. 🎯 Testaa
1. GitHub → Actions → "Solana Auto Trader"
2. "Run workflow" → "Run only one trading cycle" ✅
3. Seuraa lokeja

## 📊 Trading Asetukset

Workflow käyttää näitä asetuksia:
```yaml
Position Size: 0.05 SOL per kauppa
Max Positions: 3 kerralla
Stop Loss: -30%
Take Profit: +50%
Max Hold: 48h
Cooldown: 24h per token
Ajaminen: Joka 30 min
```

## 🔍 Seuranta

### GitHub Actions:
- **Lokit**: Actions → Workflow run → Job logs
- **Artifacts**: Lataa trading logs ja state
- **Schedule**: Automaattinen ajo joka 30 min

### Telegram (jos konfiguroitu):
```
🤖 Solana Auto Trader
Status: ✅ ONNISTUI  
Type: Continuous
Run: #123
```

## ⚠️ Turvallisuus

### Ennen Tuotantoa:
1. ✅ Testaa demo versioilla ensin
2. ✅ Aloita pienillä summilla (0.05 SOL)
3. ✅ Seuraa ensimmäisiä kauppoja
4. ✅ Tarkista wallet balance säännöllisesti

### Älä Koskaan:
- ❌ Jaa private keyä
- ❌ Käytä pääwallettiasi
- ❌ Sijoita enempää kuin voit hävitä

## 🛠 Troubleshooting

| Ongelma | Ratkaisu |
|---------|----------|
| "Private key puuttuu" | Tarkista GitHub Secrets |
| "Workflow ei käynnisty" | Tarkista YAML syntaksi |
| "Transaction epäonnistui" | Tarkista wallet balance |
| "Telegram ei toimi" | Secrets ovat valinnaisia |

## 📈 Optimointi

Muokkaa asetuksia `.github/workflows/solana_trader.yml`:
```yaml
POSITION_SIZE_SOL=0.05      # Pienennä/suurenna position kokoa
MAX_POSITIONS=3             # Muuta max positioiden määrää
STOP_LOSS_PERCENT=30        # Säädä stop loss
TAKE_PROFIT_PERCENT=50      # Säädä take profit
MIN_SCORE_THRESHOLD=7.0     # Muuta token score kynnystä
```

## 🎉 Valmis!

Solana Auto Trader on nyt käynnissä ja ajaa automaattisesti joka 30 minuutti!

**Seuraavat vaiheet:**
1. ✅ Seuraa ensimmäisiä ajoja
2. ✅ Optimoi asetuksia
3. ✅ Skaalaa onnistumisen mukaan

---

**💰 Onnea automaattiseen tradingiin! 🚀**

*Lue täydellinen dokumentaatio: [SOLANA_TRADER_SETUP.md](SOLANA_TRADER_SETUP.md)*