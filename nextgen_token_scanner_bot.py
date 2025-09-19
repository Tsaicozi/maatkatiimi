"""
NextGen Token Scanner Bot - Täydellinen trading bot uusille nouseville tokeneille
Kehitetty ideaointi tiimin avulla - tunnistaa ja treidaa uusimpia nousevia tokeneita
"""

import os
import json
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import logging

# Ladataan API-avaimet
from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TokenData:
    """Token data structure"""
    symbol: str
    name: str
    price: float
    market_cap: float
    volume_24h: float
    price_change_24h: float
    price_change_7d: float
    liquidity: float
    age_days: int
    holders: int
    social_score: float
    technical_score: float
    momentum_score: float
    risk_score: float
    overall_score: float
    timestamp: datetime

@dataclass
class TradingSignal:
    """Trading signal structure"""
    token: TokenData
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    entry_price: float
    target_price: float
    stop_loss: float
    position_size: float
    reasoning: str
    timestamp: datetime

@dataclass
class Portfolio:
    """Portfolio tracking"""
    total_value: float
    positions: Dict[str, Dict]
    daily_pnl: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float

# =============================================================================
# TOKEN SCANNER ENGINE
# =============================================================================

class NextGenTokenScanner:
    """Kehittynyt token skanneri joka löytää uusia nousevia tokeneita"""
    
    def __init__(self):
        self.setup_logging()
        self.api_keys = self.load_api_keys()
        self.scanned_tokens = set()
        self.trading_signals = []
        self.portfolio = Portfolio(0, {}, 0, 0, 0, 0)
        
    def setup_logging(self):
        """Aseta logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('token_scanner.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_api_keys(self):
        """Lataa API-avaimet"""
        return {
            'coingecko': os.getenv('COINGECKO_API_KEY', ''),
            'dexscreener': os.getenv('DEXSCREENER_API_KEY', ''),
            'moralis': os.getenv('MORALIS_API_KEY', ''),
            'telegram': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'discord': os.getenv('DISCORD_WEBHOOK', '')
        }
    
    async def scan_new_tokens(self) -> List[TokenData]:
        """Skannaa uusia tokeneita useista lähteistä"""
        self.logger.info("🔍 Aloitetaan uusien tokenien skannaus...")
        
        tasks = [
            self.scan_coingecko_new_listings(),
            self.scan_dexscreener_new_pairs(),
            self.scan_social_mentions(),
            self.scan_whale_movements()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_tokens = []
        for result in results:
            if isinstance(result, list):
                all_tokens.extend(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Virhe skannauksessa: {result}")
        
        # Poista duplikaatit ja analysoi
        unique_tokens = self.deduplicate_tokens(all_tokens)
        analyzed_tokens = await self.analyze_tokens(unique_tokens)
        
        self.logger.info(f"✅ Löydettiin {len(analyzed_tokens)} uniikkia tokenia")
        return analyzed_tokens
    
    async def scan_coingecko_new_listings(self) -> List[TokenData]:
        """Skannaa CoinGecko uusilistauksia"""
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 100,
                'page': 1,
                'sparkline': False,
                'price_change_percentage': '1h,24h,7d'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
            tokens = []
            for token_data in data:
                # Tarkista onko token uusi (alle 30 päivää)
                if self.is_new_token(token_data):
                    token = TokenData(
                        symbol=token_data.get('symbol', '').upper(),
                        name=token_data.get('name', ''),
                        price=token_data.get('current_price', 0),
                        market_cap=token_data.get('market_cap', 0),
                        volume_24h=token_data.get('total_volume', 0),
                        price_change_24h=token_data.get('price_change_percentage_24h', 0),
                        price_change_7d=token_data.get('price_change_percentage_7d_in_currency', 0),
                        liquidity=0,  # Lasketaan myöhemmin
                        age_days=self.calculate_token_age(token_data),
                        holders=0,  # Haetaan myöhemmin
                        social_score=0,  # Lasketaan myöhemmin
                        technical_score=0,  # Lasketaan myöhemmin
                        momentum_score=0,  # Lasketaan myöhemmin
                        risk_score=0,  # Lasketaan myöhemmin
                        overall_score=0,  # Lasketaan myöhemmin
                        timestamp=datetime.now()
                    )
                    tokens.append(token)
            
            self.logger.info(f"CoinGecko: Löydettiin {len(tokens)} uutta tokenia")
            return tokens
            
        except Exception as e:
            self.logger.error(f"Virhe CoinGecko skannauksessa: {e}")
            return []
    
    async def scan_dexscreener_new_pairs(self) -> List[TokenData]:
        """Skannaa DexScreener uusia pareja"""
        try:
            url = "https://api.dexscreener.com/latest/dex/tokens"
            # Tässä käytetään tunnettuja token addresseja esimerkkinä
            # Todellisessa toteutuksessa haettaisiin uusia pareja
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
            
            tokens = []
            for pair in data.get('pairs', [])[:50]:  # Rajoitetaan 50 paria
                if self.is_new_pair(pair):
                    token = TokenData(
                        symbol=pair.get('baseToken', {}).get('symbol', '').upper(),
                        name=pair.get('baseToken', {}).get('name', ''),
                        price=float(pair.get('priceUsd', 0)),
                        market_cap=float(pair.get('marketCap', 0)),
                        volume_24h=float(pair.get('volume', {}).get('h24', 0)),
                        price_change_24h=float(pair.get('priceChange', {}).get('h24', 0)),
                        price_change_7d=0,  # DexScreener ei tarjoa 7d dataa
                        liquidity=float(pair.get('liquidity', {}).get('usd', 0)),
                        age_days=self.calculate_pair_age(pair),
                        holders=0,
                        social_score=0,
                        technical_score=0,
                        momentum_score=0,
                        risk_score=0,
                        overall_score=0,
                        timestamp=datetime.now()
                    )
                    tokens.append(token)
            
            self.logger.info(f"DexScreener: Löydettiin {len(tokens)} uutta paria")
            return tokens
            
        except Exception as e:
            self.logger.error(f"Virhe DexScreener skannauksessa: {e}")
            return []
    
    async def scan_social_mentions(self) -> List[TokenData]:
        """Skannaa sosiaalisen median mainintoja"""
        # Tämä on esimerkki - todellisessa toteutuksessa käytettäisiin
        # Twitter API, Reddit API, Telegram API jne.
        self.logger.info("Sosiaalisen median skannaus - placeholder")
        return []
    
    async def scan_whale_movements(self) -> List[TokenData]:
        """Skannaa valaiden liikkeitä"""
        # Tämä on esimerkki - todellisessa toteutuksessa käytettäisiin
        # blockchain explorer API:ta
        self.logger.info("Valaiden liikkeiden skannaus - placeholder")
        return []
    
    def is_new_token(self, token_data: dict) -> bool:
        """Tarkista onko token uusi"""
        # Tarkista market cap, volume ja muut kriteerit
        market_cap = token_data.get('market_cap', 0)
        volume = token_data.get('total_volume', 0)
        
        # Uusi token: pieni market cap mutta kasvava volume
        return (market_cap < 100_000_000 and  # Alle 100M market cap
                volume > 1_000_000 and        # Yli 1M volume
                market_cap > 1_000_000)       # Yli 1M market cap
    
    def is_new_pair(self, pair_data: dict) -> bool:
        """Tarkista onko pari uusi"""
        market_cap = float(pair_data.get('marketCap', 0))
        volume = float(pair_data.get('volume', {}).get('h24', 0))
        
        return (market_cap < 50_000_000 and   # Alle 50M market cap
                volume > 500_000 and          # Yli 500K volume
                market_cap > 100_000)         # Yli 100K market cap
    
    def calculate_token_age(self, token_data: dict) -> int:
        """Laske tokenin ikä päivissä"""
        # CoinGecko ei tarjoa suoraan ikää, joten estimoidaan
        # market cap ja volume perusteella
        market_cap = token_data.get('market_cap', 0)
        if market_cap < 10_000_000:
            return 7  # Uusi
        elif market_cap < 100_000_000:
            return 30  # Keski-ikäinen
        else:
            return 90  # Vanha
    
    def calculate_pair_age(self, pair_data: dict) -> int:
        """Laske parin ikä päivissä"""
        # DexScreener ei tarjoa suoraan ikää
        market_cap = float(pair_data.get('marketCap', 0))
        if market_cap < 5_000_000:
            return 3  # Hyvin uusi
        elif market_cap < 20_000_000:
            return 14  # Uusi
        else:
            return 30  # Keski-ikäinen
    
    def deduplicate_tokens(self, tokens: List[TokenData]) -> List[TokenData]:
        """Poista duplikaatit"""
        seen = set()
        unique_tokens = []
        
        for token in tokens:
            key = (token.symbol, token.name)
            if key not in seen:
                seen.add(key)
                unique_tokens.append(token)
        
        return unique_tokens
    
    async def analyze_tokens(self, tokens: List[TokenData]) -> List[TokenData]:
        """Analysoi tokenit ja laske skoorit"""
        self.logger.info(f"🧠 Analysoidaan {len(tokens)} tokenia...")
        
        analyzed_tokens = []
        for token in tokens:
            # Laske eri skoorit
            token.social_score = await self.calculate_social_score(token)
            token.technical_score = await self.calculate_technical_score(token)
            token.momentum_score = await self.calculate_momentum_score(token)
            token.risk_score = await self.calculate_risk_score(token)
            
            # Laske kokonaisskoori
            token.overall_score = self.calculate_overall_score(token)
            
            analyzed_tokens.append(token)
        
        # Järjestä skoorin mukaan
        analyzed_tokens.sort(key=lambda x: x.overall_score, reverse=True)
        
        return analyzed_tokens
    
    async def calculate_social_score(self, token: TokenData) -> float:
        """Laske sosiaalinen skoori"""
        # Placeholder - todellisessa toteutuksessa käytettäisiin
        # Twitter, Reddit, Telegram dataa
        base_score = 5.0
        
        # Simuloi sosiaalista aktiivisuutta
        if token.volume_24h > 10_000_000:
            base_score += 2.0
        if token.price_change_24h > 20:
            base_score += 1.5
        if token.market_cap < 50_000_000:
            base_score += 1.0  # Uudet tokenit saavat bonus
        
        return min(base_score, 10.0)
    
    async def calculate_technical_score(self, token: TokenData) -> float:
        """Laske tekninen skoori"""
        base_score = 5.0
        
        # Volume analyysi
        if token.volume_24h > token.market_cap * 0.1:  # Korkea volume/market cap ratio
            base_score += 2.0
        
        # Hinnanmuutos analyysi
        if 5 < token.price_change_24h < 50:  # Terve kasvu
            base_score += 2.0
        elif token.price_change_24h > 50:  # Liian aggressiivinen
            base_score += 0.5
        
        # Market cap analyysi
        if 1_000_000 < token.market_cap < 100_000_000:  # Optimaalinen koko
            base_score += 1.5
        
        return min(base_score, 10.0)
    
    async def calculate_momentum_score(self, token: TokenData) -> float:
        """Laske momentum skoori"""
        base_score = 5.0
        
        # Positiivinen momentum
        if token.price_change_24h > 0:
            base_score += 1.0
        if token.price_change_7d > 0:
            base_score += 1.0
        
        # Volume momentum
        if token.volume_24h > 5_000_000:
            base_score += 1.5
        
        # Market cap kasvu
        if token.market_cap > 5_000_000:
            base_score += 1.0
        
        return min(base_score, 10.0)
    
    async def calculate_risk_score(self, token: TokenData) -> float:
        """Laske riski skoori (pienempi = vähemmän riskiä)"""
        risk_score = 5.0
        
        # Market cap riski
        if token.market_cap < 1_000_000:
            risk_score += 3.0  # Korkea riski
        elif token.market_cap < 10_000_000:
            risk_score += 1.5  # Keski riski
        
        # Volatiliteetti riski
        if abs(token.price_change_24h) > 50:
            risk_score += 2.0  # Korkea volatiliteetti
        
        # Liquidity riski
        if token.liquidity < 100_000:
            risk_score += 2.0  # Matala likviditeetti
        
        # Age riski
        if token.age_days < 7:
            risk_score += 1.5  # Uusi token
        
        return min(risk_score, 10.0)
    
    def calculate_overall_score(self, token: TokenData) -> float:
        """Laske kokonaisskoori"""
        weights = {
            'social': 0.2,
            'technical': 0.3,
            'momentum': 0.3,
            'risk': -0.2  # Riskit vähentävät skooria
        }
        
        overall = (
            token.social_score * weights['social'] +
            token.technical_score * weights['technical'] +
            token.momentum_score * weights['momentum'] +
            (10 - token.risk_score) * weights['risk']  # Käänteinen riski
        )
        
        return max(0, min(overall, 10))
    
    def generate_trading_signals(self, tokens: List[TokenData]) -> List[TradingSignal]:
        """Generoi trading signaalit"""
        signals = []
        
        for token in tokens:
            if token.overall_score >= 7.0:  # Korkea skoori
                signal = TradingSignal(
                    token=token,
                    signal_type='BUY',
                    confidence=token.overall_score / 10,
                    entry_price=token.price,
                    target_price=token.price * 1.5,  # 50% tuotto
                    stop_loss=token.price * 0.8,     # 20% tappio
                    position_size=self.calculate_position_size(token),
                    reasoning=f"Korkea skoori: {token.overall_score:.1f}/10",
                    timestamp=datetime.now()
                )
                signals.append(signal)
        
        return signals
    
    def calculate_position_size(self, token: TokenData) -> float:
        """Laske position koko"""
        # Risk-adjusted position sizing
        base_size = 0.02  # 2% portfolio
        
        # Säätö riskin mukaan
        if token.risk_score > 7:
            base_size *= 0.5  # Puolita korkean riskin takia
        elif token.risk_score < 4:
            base_size *= 1.5  # Kasvata matalan riskin takia
        
        # Säätö market cap mukaan
        if token.market_cap < 5_000_000:
            base_size *= 0.5  # Pienet market cap = pienempi position
        
        return min(base_size, 0.05)  # Max 5% portfolio
    
    async def run_continuous_scanning(self):
        """Aja jatkuvaa skannausta"""
        self.logger.info("🚀 Käynnistetään jatkuva token skannaus...")
        
        while True:
            try:
                # Skannaa uusia tokeneita
                new_tokens = await self.scan_new_tokens()
                
                if new_tokens:
                    # Generoi signaalit
                    signals = self.generate_trading_signals(new_tokens)
                    
                    if signals:
                        self.logger.info(f"📊 Generoitiin {len(signals)} trading signaalia")
                        
                        # Tallenna signaalit
                        await self.save_signals(signals)
                        
                        # Lähetä ilmoitukset
                        await self.send_notifications(signals)
                
                # Odota seuraavaa skannausta
                await asyncio.sleep(300)  # 5 minuuttia
                
            except Exception as e:
                self.logger.error(f"Virhe jatkuvassa skannauksessa: {e}")
                await asyncio.sleep(60)  # Odota minuutti virheen jälkeen
    
    async def save_signals(self, signals: List[TradingSignal]):
        """Tallenna signaalit"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trading_signals_{timestamp}.json"
        
        signals_data = []
        for signal in signals:
            signal_dict = asdict(signal)
            signal_dict['token'] = asdict(signal.token)
            signal_dict['timestamp'] = signal.timestamp.isoformat()
            signals_data.append(signal_dict)
        
        with open(filename, 'w') as f:
            json.dump(signals_data, f, indent=2)
        
        self.logger.info(f"💾 Signaalit tallennettu: {filename}")
    
    async def send_notifications(self, signals: List[TradingSignal]):
        """Lähetä ilmoitukset"""
        for signal in signals:
            message = f"""
🚀 UUSI TRADING SIGNAALI!

Token: {signal.token.symbol} ({signal.token.name})
Hinta: ${signal.token.price:.6f}
Skoori: {signal.token.overall_score:.1f}/10
Signaali: {signal.signal_type}
Luottamus: {signal.confidence:.1%}
Entry: ${signal.entry_price:.6f}
Target: ${signal.target_price:.6f}
Stop Loss: ${signal.stop_loss:.6f}
Position: {signal.position_size:.1%}

Perustelut: {signal.reasoning}
            """
            
            self.logger.info(f"📱 Ilmoitus: {message}")
            # Tässä voit lisätä Telegram/Discord/SMS ilmoitukset

# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Pääfunktio"""
    print("🚀 NextGen Token Scanner Bot käynnistyy...")
    print("=" * 60)
    
    scanner = NextGenTokenScanner()
    
    # Testaa skannaus
    print("🔍 Testataan token skannausta...")
    tokens = await scanner.scan_new_tokens()
    
    if tokens:
        print(f"✅ Löydettiin {len(tokens)} tokenia")
        
        # Näytä top 5
        print("\n🏆 TOP 5 TOKENIA:")
        print("-" * 60)
        for i, token in enumerate(tokens[:5], 1):
            print(f"{i}. {token.symbol} ({token.name})")
            print(f"   Hinta: ${token.price:.6f}")
            print(f"   Market Cap: ${token.market_cap:,.0f}")
            print(f"   Skoori: {token.overall_score:.1f}/10")
            print(f"   24h Muutos: {token.price_change_24h:+.1f}%")
            print()
        
        # Generoi signaalit
        signals = scanner.generate_trading_signals(tokens)
        if signals:
            print(f"📊 Generoitiin {len(signals)} trading signaalia")
    else:
        print("❌ Ei löytynyt uusia tokeneita")
    
    print("=" * 60)
    print("✅ Skannaus valmis!")

if __name__ == "__main__":
    asyncio.run(main())
