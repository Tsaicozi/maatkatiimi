# Crypto New Token Screener

A Python bot that screens for new cryptocurrency tokens using CoinGecko API and sends notifications via Telegram.

## Features

- Fetches new tokens from CoinGecko API
- Analyzes tokens using technical indicators (RSI, EMA, volatility)
- Identifies breakout and HTF (Higher Time Frame) opportunities
- Sends formatted notifications to Telegram
- Logs all activities for monitoring

## Setup

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Configure Environment Variables

The bot uses its own `.env2` file for configuration. Edit the `.env2` file and add your API keys:

```bash
nano .env2
```

Required environment variables:
- `COINGECKO_PRO_KEY`: Your CoinGecko PRO API key
- `TELEGRAM_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID

### 3. Get API Keys

#### CoinGecko PRO API Key
1. Visit [CoinGecko API Pricing](https://www.coingecko.com/en/api/pricing)
2. Subscribe to PRO plan
3. Get your API key from the dashboard

#### Telegram Bot Setup
1. Message @BotFather on Telegram
2. Create a new bot with `/newbot`
3. Get your bot token
4. Get your chat ID by messaging your bot and visiting:
   `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`

## Usage

Run the screener:

```bash
python3 crypto_new_token_screener.py
```

## Configuration

You can modify these parameters in the script:

- `momentum_threshold_24h`: Minimum 24h price change % (default: 10.0%)
- `vol_increase_threshold`: Volume increase multiplier (default: 1.5x)
- `nousu_60d_threshold`: 60-day price increase threshold (default: 90%)
- `max_retracement_threshold`: Maximum retracement allowed (default: 25%)
- `min_data_len`: Minimum data points required (default: 15 days)

## Output

The bot will:
1. Log all activities to `crypto_new_token_screener_log.log`
2. Save found tokens to `found_new_tokens.json`
3. Send formatted notifications to Telegram
4. Display results in the console

## Logs

- Main log: `crypto_new_token_screener_log.log`
- Found tokens: `found_new_tokens.json`

## Notes

- The bot respects CoinGecko API rate limits
- Requires CoinGecko PRO API for new token data
- Telegram notifications are optional (bot will warn if not configured)
- All calculations use 90 days of historical data
