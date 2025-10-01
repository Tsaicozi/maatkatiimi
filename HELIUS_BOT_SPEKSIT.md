# HELIUS SCANNER BOT - TÄYDET SPEKSIT

## 📋 TOKEN SUODATUKSET (Entry Filters)

### 1. Perussuodattimet:
- **Min Score:** 50+ (CoinGecko, Birdeye, DexScreener)
- **Min Liquidity:** $5,000 USD
- **Min Volume:** Ei minimiä (mutta volume exit)
- **DEX Status:** "ok" (tradable)
- **Cooldown:** 120s per token

### 2. Risk Management:
- **Max Trade Size:** $20 USD per trade
- **Wallet Balance Check:** Varmistaa riittävät varat
- **Fee Reserve:** 0.01 SOL fees
- **Honeypot Protection:** Testaa myynti ennen ostoa

### 3. Token Age:
- **Smart Cooldown:** < 2 min = light publish
- **Placeholder Symbols:** Retry queue (5 min, 15 min, 1h, 6h)

## 📈 TRADING STRATEGIA

### 1. AUTO-BUY (Entry):
```python
# Kriteerit ostolle:
if (score >= 50 AND 
    liquidity >= $5000 AND 
    util_min <= util <= util_max AND
    cooldown_ok AND
    can_sell_probe_pass):
    buy_token_for_usd($20)
```

### 2. AUTO-SELL (Exit):
```python
# Take Profit: +100%
if price_change >= 100%:
    sell_position("Take Profit")

# Stop Loss: -30%  
if price_change <= -30%:
    sell_position("Stop Loss")

# Time Exit: 48h
if time_held >= 48h:
    sell_position("Time Exit")

# Volume Exit: <20% of entry
if current_volume < (entry_volume * 0.2):
    sell_position("Volume Exit")

# Liquidity Exit: <50% of entry
if current_liquidity < (entry_liquidity * 0.5):
    sell_position("Liquidity Exit")

# Low Volume Exit: <$1000
if current_volume < $1000:
    sell_position("Low Volume Exit")
```

## 💰 KASSAN TIETOJEN HAKU/PÄIVITYS

### 1. Wallet Balance:
```python
# trader.py - get_sol_balance()
async def get_sol_balance(self) -> float:
    resp = await sol_client.get_balance(wallet_pubkey)
    return resp.value / 1e9  # lamports → SOL
```

### 2. Position Tracking:
```python
# helius_token_scanner_bot.py
self._open_positions = {
    "mint": {
        "entry_price": float,
        "entry_time": timestamp,
        "entry_volume": float,
        "entry_liquidity": float,
        "entry_symbol": str
    }
}
```

### 3. Data Sources:
- **Helius RPC:** `https://mainnet.helius-rpc.com/?api-key=...`
- **Jupiter API:** `https://lite-api.jup.ag/swap/v1`
- **CoinGecko:** `https://pro-api.coingecko.com/api/v3/`
- **Birdeye:** `https://public-api.birdeye.so/`
- **DexScreener:** `https://api.dexscreener.com/`

### 4. Real-time Updates:
```python
# WebSocket sources:
- Helius logsSubscribe (Tokenkeg, Raydium, Orca, Pump.fun)
- Raydium Pool Watcher
- Lookback Sweep (DexScreener)
```

### 5. Wallet Reports:
```python
# Joka 2h:
- SOL balance
- USD value  
- Open positions count
- Total trades
- Trading status
```

## 🔄 POSITION PERSISTENCE

### 1. Save/Load:
```python
# open_positions.json
{
  "mint_address": {
    "entry_price": 0.000123,
    "entry_time": 1695123456.789,
    "entry_volume": 50000.0,
    "entry_liquidity": 10000.0,
    "entry_symbol": "TOKEN"
  }
}
```

### 2. Force Sell on Startup:
```python
# Käynnistyksessä:
if _force_sell_all_on_startup:
    await _force_sell_all_positions()
    # Myy kaikki vanhat positiot
```

## 📊 SCORING SYSTEM

### 1. Token Score:
- **Base Score:** 50 (new token)
- **CoinGecko Bonus:** +10-20
- **Symbol Resolution:** +5-15
- **Social Links:** +5-10
- **Placeholder Penalty:** -10

### 2. Confluence Bonuses:
- **Multiple Sources:** +5 per source
- **High Confidence:** +10
- **Live Pricing:** +5

## ⚙️ ENVIRONMENT VARIABLES

```bash
# Trading
AUTO_TRADE=1
DRY_RUN=0
TRADE_MAX_USD=20.0
TRADE_MIN_SCORE=50
TRADE_MIN_LIQ_USD=5000.0
TRADE_COOLDOWN_SEC=120

# APIs
SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=...
COINGECKO_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Wallet
TRADER_PRIVATE_KEY_HEX=...
SOL_PRICE_FALLBACK=208
```

## 🚀 BOTTI ON TÄYSIN AUTOMATISOITU JA VALMIS!

### Komentoja:
```bash
# Käynnistä botti
sudo systemctl start helius-scanner

# Tarkista status
sudo systemctl status helius-scanner

# Seuraa logit
sudo journalctl -u helius-scanner -f

# Health check
curl http://localhost:9109/health

# Trading status
curl http://localhost:9109/trading
```
