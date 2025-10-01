# 🚀 Solana Auto Trader

Automaattinen Solana token trader joka käyttää Jupiter DEX:iä ja Phantom wallet integraatiota.

## ⚡ Pika-aloitus

1. **Luo wallet**:
   ```bash
   python3 create_solana_wallet.py
   ```

2. **Konfiguroi**:
   ```bash
   cp .env.example .env
   # Muokkaa .env tiedostoa
   ```

3. **Testaa**:
   ```bash
   python3 solana_auto_trader.py --once
   ```

4. **Aja jatkuvasti**:
   ```bash
   python3 solana_auto_trader.py
   ```

## 📚 Täydellinen dokumentaatio

**👉 Lue [SOLANA_TRADER_SETUP.md](SOLANA_TRADER_SETUP.md) täydellinen setup opas!**

## 🎯 Ominaisuudet

- ✅ **Real-time token skannaus** (DexScreener + Birdeye)
- ✅ **Jupiter DEX integraatio** (paras hinnoittelu)
- ✅ **Phantom wallet tuki** (täysi yhteensopivuus)
- ✅ **Risk management** (stop-loss, take-profit, cooldown)
- ✅ **Telegram ilmoitukset** (entry/exit signaalit)
- ✅ **GitHub Actions** (automaattinen ajaminen)
- ✅ **Position monitoring** (real-time seuranta)

## 💰 Trading Strategia

- **Position size**: 0.05 SOL per kauppa
- **Max positions**: 3 kerralla
- **Stop-loss**: -30%
- **Take-profit**: +50%
- **Max hold**: 48h
- **Cooldown**: 24h per token

## 📁 Tiedostot

- `solana_trader.py` - Jupiter swap integraatio
- `solana_auto_trader.py` - Automaattinen trader
- `real_solana_token_scanner.py` - Token skannaus
- `create_solana_wallet.py` - Wallet hallinta
- `get_telegram_chat_id.py` - Telegram setup
- `.github/workflows/solana_trader.yml` - GitHub Actions
- `SOLANA_TRADER_SETUP.md` - Täydellinen dokumentaatio

## ⚠️ Turvallisuus

- **Testaa pienillä summilla ensin**
- **Älä jaa private keyä kenenkään kanssa**
- **Käytä GitHub Secretsejä tuotannossa**
- **Seuraa positioita säännöllisesti**

## 🆘 Tuki

Jos kohtaat ongelmia:
1. Lue [SOLANA_TRADER_SETUP.md](SOLANA_TRADER_SETUP.md) troubleshooting osio
2. Tarkista lokit
3. Luo GitHub issue

---

**🎉 Onnea tradingiin! 💰**

*⚠️ Disclaimer: Käytä omalla vastuulla. Älä sijoita enempää kuin voit hävitä.*