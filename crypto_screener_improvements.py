# Crypto Screener Bot - Parannusehdotukset
# Tämä tiedosto sisältää parannuksia alkuperäiseen botiin

import pandas as pd
import numpy as np
import logging
import time
import os
import json
from pycoingecko import CoinGeckoAPI
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import requests
from typing import Dict, List, Optional, Tuple
import asyncio
import aiohttp

# PARANNUS 1: Konfiguraatiotiedosto
class Config:
    def __init__(self):
        self.momentum_threshold_24h = float(os.getenv('MOMENTUM_THRESHOLD', '10.0'))
        self.vol_increase_threshold = float(os.getenv('VOL_INCREASE_THRESHOLD', '1.5'))
        self.nousu_60d_threshold = float(os.getenv('NOUSU_60D_THRESHOLD', '0.9'))
        self.max_retracement_threshold = float(os.getenv('MAX_RETRACEMENT_THRESHOLD', '0.25'))
        self.min_data_len_new = int(os.getenv('MIN_DATA_LEN_NEW', '1'))
        self.min_data_len_old = int(os.getenv('MIN_DATA_LEN_OLD', '15'))
        self.min_volume_usd = float(os.getenv('MIN_VOLUME_USD', '10000'))  # Min volyymi USD
        self.max_holder_share = float(os.getenv('MAX_HOLDER_SHARE', '0.1'))  # Max 10% yhdellä holderilla

# PARANNUS 2: Parannettu uusien tokenien analyysi
def analyze_new_token_advanced(coin_data: Dict, df: pd.DataFrame) -> Dict:
    """Parannettu analyysi uusille tokeneille"""
    market_data = coin_data.get('market_data', {})
    
    # Peruskriteerit
    current_price = market_data.get('current_price', {}).get('usd', 0)
    volume_24h = market_data.get('total_volume', {}).get('usd', 0)
    market_cap = market_data.get('market_cap', {}).get('usd', 0)
    
    # Turvallisuustarkistukset
    security_score = 0
    security_issues = []
    
    # 1. Volyymi-tarkistus
    if volume_24h < config.min_volume_usd:
        security_issues.append(f"Liian pieni volyymi: ${volume_24h:,.0f}")
    else:
        security_score += 1
    
    # 2. Market cap -tarkistus
    if market_cap < 100000:  # Alle 100k USD
        security_issues.append(f"Liian pieni market cap: ${market_cap:,.0f}")
    else:
        security_score += 1
    
    # 3. Hinta-volatiliteetti
    if len(df) >= 2:
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]
        if abs(price_change) > 0.5:  # Yli 50% muutos
            security_issues.append(f"Korkea volatiliteetti: {price_change:.1%}")
        else:
            security_score += 1
    
    # 4. Volyymi-konsistenssi
    if len(df) >= 3:
        recent_volumes = df['volume'].tail(3)
        if recent_volumes.std() / recent_volumes.mean() > 2:  # Korkea volyymi-vaihtelu
            security_issues.append("Epätasainen volyymi")
        else:
            security_score += 1
    
    # Lopullinen arvio
    is_safe = security_score >= 3 and len(security_issues) <= 1
    confidence = security_score / 4
    
    return {
        'is_safe': is_safe,
        'confidence': confidence,
        'security_issues': security_issues,
        'security_score': security_score,
        'volume_24h': volume_24h,
        'market_cap': market_cap
    }

# PARANNUS 3: Batch API-kutsut
async def fetch_multiple_coins_batch(coin_ids: List[str]) -> List[Dict]:
    """Hae useita kolikoita kerralla"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for coin_id in coin_ids:
            task = fetch_single_coin_async(session, coin_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict)]

async def fetch_single_coin_async(session: aiohttp.ClientSession, coin_id: str) -> Optional[Dict]:
    """Hae yksi kolikko asynkronisesti"""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        headers = {'x-cg-pro-api-key': os.getenv('COINGECKO_PRO_KEY')}
        
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
    except Exception as e:
        logging.error(f"Virhe kolikon {coin_id} haussa: {e}")
    return None

# PARANNUS 4: Parannettu Telegram-viesti
def create_enhanced_telegram_message(results_df: pd.DataFrame) -> str:
    """Luo parannetun Telegram-viestin"""
    if results_df.empty:
        return "💡 Seulonta suoritettu.\nEi potentiaalisia kryptoja löydynt."
    
    # Ryhmittele kategorioittain
    new_tokens = results_df[results_df['Category'] == 'New']
    old_tokens = results_df[results_df['Category'] == 'Old']
    
    message = "💡 Seulonta suoritettu.\n\n"
    
    if not new_tokens.empty:
        message += f"🆕 UUSIA TOKENEITA ({len(new_tokens)} kpl):\n"
        for _, row in new_tokens.iterrows():
            message += f"• {row['Ticker']} - Vol: ${row.get('Volume_24h', 0):,.0f}\n"
        message += "\n"
    
    if not old_tokens.empty:
        message += f"📈 VANHOJA TOKENEITA ({len(old_tokens)} kpl):\n"
        for _, row in old_tokens.iterrows():
            message += f"• {row['Ticker']} - RSI: {row['RSI']:.1f}\n"
        message += "\n"
    
    # Lisää yhteenveto
    total_found = len(results_df)
    high_confidence = len(results_df[results_df.get('Confidence', 0) > 0.7])
    
    message += f"📊 Yhteenveto:\n"
    message += f"├ Löydetty: {total_found} tokenia\n"
    message += f"├ Korkea luottamus: {high_confidence} tokenia\n"
    message += f"└ Aika: {datetime.now(ZoneInfo('Europe/Helsinki')).strftime('%H:%M')}\n"
    
    return message

# PARANNUS 5: Jatkuva seuranta
class ContinuousScreener:
    def __init__(self, config: Config):
        self.config = config
        self.found_tokens = set()
        self.last_run = None
        
    async def run_continuous_scan(self, interval_minutes: int = 30):
        """Aja seulonta jatkuvasti"""
        while True:
            try:
                print(f"Aloitetaan seulonta: {datetime.now()}")
                results = await self.scan_tokens()
                
                # Tarkista uudet tokenit
                new_findings = self.check_new_findings(results)
                if new_findings:
                    self.send_alert(new_findings)
                
                self.last_run = datetime.now()
                print(f"Seulonta valmis. Seuraava ajastus: {interval_minutes} min")
                
                await asyncio.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("Sammutetaan seulonta...")
                break
            except Exception as e:
                logging.error(f"Virhe jatkuvassa seulonnassa: {e}")
                await asyncio.sleep(60)  # Odota minuutti ennen uudelleenyritystä
    
    def check_new_findings(self, results: pd.DataFrame) -> List[Dict]:
        """Tarkista uudet löydökset"""
        new_findings = []
        for _, row in results.iterrows():
            token_id = f"{row['Ticker']}_{row['Coin ID']}"
            if token_id not in self.found_tokens:
                self.found_tokens.add(token_id)
                new_findings.append(row.to_dict())
        return new_findings

# PARANNUS 6: Parannettu logging
def setup_enhanced_logging():
    """Aseta parannettu lokitus"""
    # Luo lokikansio jos ei ole
    os.makedirs('logs', exist_ok=True)
    
    # Päälogi
    main_handler = logging.FileHandler('logs/crypto_screener.log')
    main_handler.setLevel(logging.INFO)
    
    # Virhelogi
    error_handler = logging.FileHandler('logs/crypto_screener_errors.log')
    error_handler.setLevel(logging.ERROR)
    
    # Formaatti
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    main_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)
    
    # Logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(main_handler)
    logger.addHandler(error_handler)
    
    return logger

# PARANNUS 7: Konfiguraatiotiedosto
CONFIG_TEMPLATE = """
# Crypto Screener Bot Configuration
# Kopioi tämä .env2 tiedostoon ja täytä arvot

# API Keys
COINGECKO_PRO_KEY=your_key_here
TELEGRAM_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Seulontakriteerit
MOMENTUM_THRESHOLD=10.0
VOL_INCREASE_THRESHOLD=1.5
NOUSU_60D_THRESHOLD=0.9
MAX_RETRACEMENT_THRESHOLD=0.25

# Data-vaatimukset
MIN_DATA_LEN_NEW=1
MIN_DATA_LEN_OLD=15
MIN_VOLUME_USD=10000
MAX_HOLDER_SHARE=0.1

# Seuranta
SCAN_INTERVAL_MINUTES=30
ENABLE_CONTINUOUS_SCAN=true
"""

if __name__ == "__main__":
    print("Crypto Screener Bot - Parannusehdotukset")
    print("=" * 50)
    print("1. Konfiguraatiotiedosto - helpompi säätö")
    print("2. Parannettu uusien tokenien analyysi")
    print("3. Batch API-kutsut - nopeampi")
    print("4. Turvallisuustarkistukset")
    print("5. Jatkuva seuranta")
    print("6. Parannettu lokitus")
    print("7. Parannettu Telegram-viestit")
    print("\nHaluatko toteuttaa jotain näistä parannuksista?")

