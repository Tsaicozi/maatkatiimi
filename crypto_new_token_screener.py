import pandas as pd
import numpy as np
import logging
import time
import os
import json
from pycoingecko import CoinGeckoAPI  # Lisätty momentum-hakuun
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv  # Lisätty .env-tiedoston lataamiseen
import requests  # Lisätty Telegram-lähetykseen

load_dotenv('.env2')  # Lataa .env2-tiedosto crypto screener botille

logging.basicConfig(filename='crypto_new_token_screener_log.log', level=logging.INFO, format='%(asctime)s - %(message)s')
# CoinGecko API - Käytetään PRO-avainta .env:stä
cg = CoinGeckoAPI(api_key=os.getenv('COINGECKO_PRO_KEY'))
timeframe = '1d'  # Päivittäinen data seulontaan
history_days = '90'  # Muutettu '90':een (sallittu arvo OHLC:lle), merkkijonona
rsi_period = 14
ema_short_span = 5
ema_long_span = 20
momentum_threshold_24h = 10.0  # % nousu 24h - Laske testiksi 5.0:aan jos haluat enemmän tuloksia
vol_increase_threshold = 1.5  # Volyymi > 1.5x keskiarvo
nousu_60d_threshold = 0.9  # >90% nousu 60d HTF:lle
max_retracement_threshold = 0.25  # <25% lasku 20d
wait_time = 120  # Sekuntia loopissa
found_tickers_file = 'found_new_tokens.json'
min_data_len_new = 1  # Uusille tokeneille: hyväksy vähän dataa
min_data_len_old = 15  # Vanhemmille tokeneille: vaadi enemmän dataa
min_volume_usd = 10000  # Min volyymi USD uusille tokeneille
min_market_cap_usd = 50000  # Min market cap USD uusille tokeneille
max_volatility_threshold = 0.8  # Max 80% päivittäinen volatiliteetti
max_holder_share = 0.15  # Max 15% yhdellä holderilla
min_liquidity_usd = 20000  # Min likviditeetti USD

def load_found_tickers():
    if os.path.exists(found_tickers_file):
        with open(found_tickers_file, 'r') as f:
            return json.load(f)
    return {}

def save_found_tickers(found_tickers):
    with open(found_tickers_file, 'w') as f:
        json.dump(found_tickers, f)

def get_new_tokens(limit=20):  # Vähennetty 50:stä 20:een
    try:
        new_coins = cg.get_coins_list_new()  # Hae viimeisimmät 200 lisättyä kolikkoa (toimii nyt PRO:lla)
        # Hae markkinadata uusille kolikoille (vain ID:t saatavilla, joten hae /coins/{id} tai /coins/markets ID:llä)
        coins_data = []
        for coin in new_coins[:limit * 2]:  # Hae ylimääräisiä, koska kaikki eivät ole kauppakelpoisia
            try:
                coin_data = cg.get_coin_by_id(id=coin['id'])
                if 'market_data' in coin_data and coin_data['market_data']['price_change_percentage_24h'] is not None:
                    coins_data.append(coin_data)
            except Exception as e:
                print(f"Virhe kolikon {coin['id']} datan haussa: {str(e)}")
            time.sleep(0.5)  # Vähennetty 2s:stä 0.5s:een
        # Järjestä data paikallisesti price_change_percentage_24h desc
        data_sorted = sorted(coins_data, key=lambda x: x['market_data']['price_change_percentage_24h'] if x['market_data']['price_change_percentage_24h'] is not None else -float('inf'), reverse=True)
        # Lisätty print debuggaukseen: Näyttää raaka data konsolissa (top 20 sorted)
        print("Fetched and sorted new tokens from CoinGecko (top 20 by 24h % change):")
        for coin in data_sorted[:20]:
            print(f"{coin['symbol'].upper()}: {coin['market_data']['price_change_percentage_24h']}%")
        # Ohita None-arvot ja suodata yli threshold
        coins = [{'id': coin['id'], 'symbol': coin['symbol'].upper()} for coin in data_sorted if coin['market_data']['price_change_percentage_24h'] is not None and coin['market_data']['price_change_percentage_24h'] > momentum_threshold_24h]
        logging.info(f"Haettiin {len(coins)} uutta potentiaalista tokenia CoinGeckosta: {[c['symbol'] for c in coins]}")
        # Lisätty print: Näyttää löydetyt kolikot konsolissa
        print(f"Löydetyt uudet tokenit yli {momentum_threshold_24h}% nousulla: {[c['symbol'] for c in coins]}")
        return coins[:limit]  # Rajoita haluttuun limittiin
    except Exception as e:
        logging.error(f"Virhe uusien tokenien haussa: {str(e)}")
        return []

def fetch_historical_data(coin_id):
    try:
        # Hae OHLC (open, high, low, close) - päivittäinen '90' päivälle
        ohlc_data = cg.get_coin_ohlc_by_id(id=coin_id, vs_currency='usd', days=history_days)
        df_ohlc = pd.DataFrame(ohlc_data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df_ohlc['date'] = pd.to_datetime(df_ohlc['timestamp'], unit='ms').dt.date
        
        time.sleep(0.3)  # Vähennetty 2s:stä 0.3s:een
        
        # Hae volyymit (aggregated) - tunneittainen '90' päivälle
        market_data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=int(history_days))
        df_volume = pd.DataFrame(market_data['total_volumes'], columns=['timestamp', 'volume'])
        df_volume['date'] = pd.to_datetime(df_volume['timestamp'], unit='ms').dt.date
        
        # Resample volyymi päivittäiseksi: ota päivän viimeinen arvo (edustaa 24h volyymia)
        df_volume_daily = df_volume.groupby('date')['volume'].last().reset_index(name='volume')
        
        # Yhdistä date:n perusteella (päivittäinen data)
        df = pd.merge(df_ohlc, df_volume_daily, on='date', how='inner')
        df['Date'] = pd.to_datetime(df['date'])
        df = df.drop(columns=['date'])  # Poista apusarake
        print(f"Datan pituus kolikolle {coin_id}: {len(df)} päivää")  # Lisätty debug-print
        return df
    except Exception as e:
        logging.error(f"Virhe datan haussa {coin_id}: {str(e)}")
        print(f"Virhe datan haussa kolikolle {coin_id}: {str(e)}")  # Lisätty print konsoliin
        return pd.DataFrame()

def calculate_rsi(df, periods=rsi_period):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 0  # Korjattu NaN-käsittely

def calculate_volatility(df):
    high_low_range = (df['high'].iloc[-20:] - df['low'].iloc[-20:]).mean()
    avg_price = df['close'].iloc[-20:].mean()
    return (high_low_range / avg_price) * 100 if avg_price > 0 else 0

def check_token_security(coin_data):
    """Tarkista tokenin turvallisuus - mint authority, LP-lukitus, holder-jakauma"""
    security_issues = []
    security_score = 0
    
    if not coin_data or 'market_data' not in coin_data:
        return security_issues, 0
    
    market_data = coin_data['market_data']
    
    # 1. Mint Authority tarkistus (CoinGecko ei tarjoa tätä suoraan, mutta voidaan tarkistaa muilla tavoilla)
    # Tarkista onko token "verified" CoinGeckossa
    if coin_data.get('verified', False):
        security_score += 1
    else:
        security_issues.append("Token ei ole verifioitu CoinGeckossa")
    
    # 2. Liquidity tarkistus
    liquidity_score = market_data.get('liquidity_score', 0)
    if liquidity_score > 0.7:  # Korkea likviditeetti
        security_score += 1
    elif liquidity_score > 0.3:  # Keskitaso
        security_score += 0.5
        security_issues.append(f"Alhainen likviditeetti: {liquidity_score:.2f}")
    else:
        security_issues.append(f"Erittäin alhainen likviditeetti: {liquidity_score:.2f}")
    
    # 3. Market cap vs Volume suhde (terve markkina)
    market_cap = market_data.get('market_cap', {}).get('usd', 0)
    volume_24h = market_data.get('total_volume', {}).get('usd', 0)
    
    if market_cap > 0 and volume_24h > 0:
        volume_market_cap_ratio = volume_24h / market_cap
        if 0.01 <= volume_market_cap_ratio <= 0.5:  # 1-50% on terve
            security_score += 1
        elif volume_market_cap_ratio > 0.5:
            security_issues.append(f"Liian korkea volyymi/market cap suhde: {volume_market_cap_ratio:.1%}")
        else:
            security_issues.append(f"Liian alhainen volyymi/market cap suhde: {volume_market_cap_ratio:.1%}")
    
    # 4. Price change volatility (ei liian äärimmäistä)
    price_change_24h = market_data.get('price_change_percentage_24h', 0)
    if price_change_24h is not None:
        if abs(price_change_24h) <= 100:  # Alle 100% muutos 24h
            security_score += 1
        elif abs(price_change_24h) <= 200:  # 100-200% on varoitus
            security_score += 0.5
            security_issues.append(f"Korkea 24h volatiliteetti: {price_change_24h:.1f}%")
        else:
            security_issues.append(f"Erittäin korkea 24h volatiliteetti: {price_change_24h:.1f}%")
    
    # 5. Community trust indicators
    community_score = coin_data.get('community_score', 0)
    if community_score > 0.5:
        security_score += 1
    elif community_score > 0.2:
        security_score += 0.5
        security_issues.append(f"Alhainen community score: {community_score:.2f}")
    else:
        security_issues.append(f"Erittäin alhainen community score: {community_score:.2f}")
    
    return security_issues, security_score

def calculate_indicators(df, is_new_token=False, coin_data=None):
    current_price = df['close'].iloc[-1]
    
    # Uusille tokeneille: parannetut kriteerit
    if is_new_token:
        # Peruskriteerit
        is_positive = current_price > 0
        has_volume = df['volume'].iloc[-1] > 0 if len(df) > 0 else False
        
        # Peruskriteerit
        basic_security_score = 0
        basic_security_issues = []
        
        # 1. Volyymi-tarkistus (USD)
        if coin_data and 'market_data' in coin_data:
            volume_24h = coin_data['market_data'].get('total_volume', {}).get('usd', 0)
            if volume_24h >= min_volume_usd:
                basic_security_score += 1
            else:
                basic_security_issues.append(f"Liian pieni volyymi: ${volume_24h:,.0f}")
        else:
            basic_security_issues.append("Volyymi-data puuttuu")
        
        # 2. Market cap -tarkistus
        if coin_data and 'market_data' in coin_data:
            market_cap = coin_data['market_data'].get('market_cap', {}).get('usd', 0)
            if market_cap >= min_market_cap_usd:
                basic_security_score += 1
            else:
                basic_security_issues.append(f"Liian pieni market cap: ${market_cap:,.0f}")
        else:
            basic_security_issues.append("Market cap -data puuttuu")
        
        # 3. Volatiliteetti-tarkistus (jos dataa riittää)
        if len(df) >= 2:
            price_change = abs((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2])
            if price_change <= max_volatility_threshold:
                basic_security_score += 1
            else:
                basic_security_issues.append(f"Korkea volatiliteetti: {price_change:.1%}")
        else:
            basic_security_score += 1  # Hyväksy jos ei dataa
        
        # 4. Volyymi-konsistenssi (jos dataa riittää)
        if len(df) >= 3:
            recent_volumes = df['volume'].tail(3)
            if recent_volumes.std() / recent_volumes.mean() <= 2:  # Alle 200% vaihtelu
                basic_security_score += 1
            else:
                basic_security_issues.append("Epätasainen volyymi")
        else:
            basic_security_score += 1  # Hyväksy jos ei dataa
        
        # 5. Lisätyt turvallisuustarkistukset
        advanced_security_issues, advanced_security_score = check_token_security(coin_data)
        
        # Yhdistä tulokset
        total_security_score = basic_security_score + advanced_security_score
        all_security_issues = basic_security_issues + advanced_security_issues
        
        # Lopullinen arvio (vaadi vähintään 6/9 pistettä ja max 2 ongelmaa)
        is_safe = total_security_score >= 6 and len(all_security_issues) <= 2
        breakout = is_positive and has_volume and is_safe
        htf = False  # Uusille tokeneille ei HTF-analyysiä
        rsi = 50  # Oletusarvo uusille
        volatility = price_change * 100 if len(df) >= 2 else 0
        predicted_change = 0
        
        print(f"Uusi token: Breakout={breakout} (turvallisuus: {total_security_score}/9, ongelmat: {len(all_security_issues)})")
        if all_security_issues:
            print(f"  Peruskriteerit: {basic_security_score}/4, Lisätyt: {advanced_security_score:.1f}/5")
            print(f"  Turvallisuusongelmat: {', '.join(all_security_issues[:3])}")  # Näytä max 3 ongelmaa
        
        return current_price, predicted_change, rsi, volatility, breakout, htf
    
    # Vanhemmille tokeneille: täydellinen analyysi
    df['ema_short'] = df['close'].ewm(span=ema_short_span, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=ema_long_span, adjust=False).mean()
    predicted_change = ((df['ema_short'].iloc[-1] - df['ema_long'].iloc[-1]) / df['ema_long'].iloc[-1]) * 100 if not pd.isna(df['ema_long'].iloc[-1]) else 0
    rsi = calculate_rsi(df)
    volatility = calculate_volatility(df)
    avg_volume = df['volume'].rolling(window=20).mean().iloc[-1] if len(df) >=20 else df['volume'].mean()
    current_volume = df['volume'].iloc[-1]
    
    # HTF-analyysi vain vanhemmille tokeneille
    if len(df) > 60:
        nousu_60d = (current_price / df['close'].shift(60).iloc[-1] - 1)
    else:
        nousu_60d = 0
    high_rolling = df['high'].rolling(20).max().iloc[-1] if len(df) >=20 else df['high'].max()
    low_rolling = df['low'].rolling(20).min().iloc[-1] if len(df) >=20 else df['low'].min()
    max_retracement = (high_rolling - low_rolling) / high_rolling if high_rolling > 0 else 0
    breakout = current_volume > vol_increase_threshold * avg_volume
    htf = nousu_60d > nousu_60d_threshold and max_retracement < max_retracement_threshold
    print(f"Vanha token: Breakout={breakout} (vol: {current_volume} > {vol_increase_threshold} * {avg_volume}), HTF={htf} (nousu_60d={nousu_60d}, max_retracement={max_retracement})")
    return current_price, predicted_change, rsi, volatility, breakout, htf

def laheta_telegram_ilmoitus(tulokset_df):
    if tulokset_df.empty:
        viesti = "💡 Seulonta suoritettu.\nEi potentiaalisia kryptoja löydynt."
    else:
        viesti = "💡 Seulonta suoritettu.\nPotentiaalisia kryptoja löydynt:\n\n"
        for _, row in tulokset_df.iterrows():
            # Määritä kategoria
            category_emoji = "🆕" if row['Category'] == 'New' else "📈"
            category_text = "UUSI TOKEN" if row['Category'] == 'New' else "VANHA TOKEN"
            
            viesti += f"{category_emoji} {category_text}\n"
            viesti += f"💊 {row['Ticker']} (${row['Ticker']})\n"
            viesti += f"├ {row['Coin ID']}\n"
            viesti += "└ #SOL | 🌱 N/A | 👁️ N/A\n\n"
            viesti += "📊 Token Stats\n"
            viesti += f"├ Breakout: {row['Breakout']}\n"
            viesti += f"├ HTF: {row['HTF']}\n"
            viesti += f"├ RSI: {row['RSI']:.2f}\n"
            viesti += f"├ Volatility: {row['Volatility']:.2f}%\n\n"
            viesti += "🔗 Links\n"
            viesti += f"└ [CoinGecko](https://www.coingecko.com/en/coins/{row['Coin ID']})\n\n"
            viesti += "🔒 Security\n"
            viesti += "├ N/A\n\n"
    
    bot_token = os.getenv('TELEGRAM_TOKEN')  # Ladataan .env2:sta
    chat_id = os.getenv('TELEGRAM_CHAT_ID')  # Ladataan .env2:sta
    
    if not bot_token or not chat_id:
        print("Varoitus: Telegram-asetukset puuttuvat .env2-tiedostosta")
        logging.warning("Varoitus: Telegram-asetukset puuttuvat .env2-tiedostosta")
        return
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {"chat_id": chat_id, "text": viesti, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("Telegram-viesti lähetetty onnistuneesti.")
            logging.info("Telegram-viesti lähetetty onnistuneesti.")
        else:
            print(f"Virhe Telegram-lähetyksessä: {response.text}")
            logging.error(f"Virhe Telegram-lähetyksessä: {response.text}")
    except Exception as e:
        print(f"Virhe Telegram-lähetyksessä: {str(e)}")
        logging.error(f"Virhe Telegram-lähetyksessä: {str(e)}")

def prosessoi_uudet_tokenit():
    coins = get_new_tokens()
    tulokset = []
    total_coins = len(coins)
    
    print(f"Prosessoidaan {total_coins} tokenia...")
    print(f"Arvioitu aika: {total_coins * 2} sekuntia ({total_coins * 2 / 60:.1f} min)")
    
    for i, coin in enumerate(coins, 1):
        print(f"[{i}/{total_coins}] Prosessoidaan {coin['symbol']} ({coin['id']})...")
        df = fetch_historical_data(coin['id'])
        
        # Hae coin_data uusille tokeneille turvallisuustarkistuksia varten
        coin_data = None
        if len(df) < min_data_len_old and len(df) >= min_data_len_new:
            try:
                coin_data = cg.get_coin_by_id(id=coin['id'])
                time.sleep(0.2)  # Vähennetty 1s:stä 0.2s:een
            except Exception as e:
                print(f"Virhe coin_data haussa {coin['id']}: {e}")
        
        # Määritä kategoria datan mukaan
        if len(df) < min_data_len_old:
            # Uusi token: hyväksy vähän dataa
            if len(df) >= min_data_len_new:
                print(f"Kolikko {coin['symbol']}: Uusi token ({len(df)} päivää dataa)")
                current_price, predicted_change, rsi, volatility, breakout, htf = calculate_indicators(df, is_new_token=True, coin_data=coin_data)
                category = 'New'
            else:
                print(f"Kolikko {coin['symbol']}: Ei riittävästi dataa (alle {min_data_len_new} päivää). Ohitetaan.")
                continue
        else:
            # Vanha token: täydellinen analyysi
            print(f"Kolikko {coin['symbol']}: Vanha token ({len(df)} päivää dataa)")
            current_price, predicted_change, rsi, volatility, breakout, htf = calculate_indicators(df, is_new_token=False)
            category = 'Old'
        
        # Lisää tuloksiin jos täyttää kriteerit
        if breakout or htf:
            print(f"Lisätään tuloksiin kolikko {coin['symbol']} (Kategoria: {category}, Breakout={breakout}, HTF={htf})")
            tulokset.append({
                'Ticker': coin['symbol'],
                'Coin ID': coin['id'],
                'Category': category,
                'Breakout': breakout,
                'HTF': htf,
                'RSI': rsi,
                'Volatility': volatility
            })
        
        time.sleep(0.5)  # Vähennetty 5s:stä 0.5s:een
    
    tulokset_df = pd.DataFrame(tulokset)
    logging.info(f"Lopputulokset:\n{tulokset_df.to_string()}")
    print("Lopputulokset:\n", tulokset_df.to_string() if not tulokset_df.empty else "Ei tuloksia.")
    laheta_telegram_ilmoitus(tulokset_df)
    return tulokset_df

if __name__ == "__main__":
    print("Skripti käynnistyi - Hakee dataa...")
    prosessoi_uudet_tokenit()
    print("Skripti suoritettu.")
