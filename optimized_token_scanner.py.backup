#!/usr/bin/env python3
"""
Optimized Solana Token Scanner
Keskittyy VAIN todella uusiin tokeneihin (< 2 minuuttia)
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class UltraFreshToken:
    address: str
    symbol: str
    name: str
    price: float
    market_cap: float
    volume_24h: float
    price_change_1h: float
    liquidity: float
    age_minutes: float
    holders: int
    social_score: float
    technical_score: float
    risk_score: float
    overall_score: float
    timestamp: datetime
    source: str  # API source

class OptimizedTokenScanner:
    """Optimoitu token skanneri - VAIN todella uusia tokeneita"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = None
        
        # API endpoints - optimoitu uusille tokeneille
        self.pump_fun_url = "https://frontend-api.pump.fun/coins"
        self.jupiter_url = "https://quote-api.jup.ag/v6"
        self.dexscreener_url = "https://api.dexscreener.com/latest/dex/tokens/solana"
        self.birdeye_url = "https://public-api.birdeye.so/public/v1/tokenlist"
        self.raydium_url = "https://api.raydium.io/v2/main/price"
        
        # Headers
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://pump.fun/"
        }
        
        # Tiukat kriteerit uusille tokeneille
        self.max_age_minutes = 2  # MAX 2 minuuttia
        self.min_market_cap = 10_000
        self.max_market_cap = 50_000
        self.min_volume_ratio = 1.0  # Volume >= Market Cap
        self.min_liquidity_ratio = 0.3  # Liquidity >= 30% of MC

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def scan_ultra_fresh_tokens(self) -> List[UltraFreshToken]:
        """Skannaa VAIN todella uusia tokeneita (< 2 min)"""
        self.logger.info("🚀 Skannataan ULTRA-FRESH tokeneita (< 2 min)...")
        
        tokens = []
        
        try:
            # 1. Pump.fun - paras lähde uusille tokeneille
            pump_tokens = await self._scan_pump_fun()
            tokens.extend(pump_tokens)
            
            # 2. DexScreener - suodatettu uusille
            dexscreener_tokens = await self._scan_dexscreener_fresh()
            tokens.extend(dexscreener_tokens)
            
            # 3. Jupiter - uusimmat
            jupiter_tokens = await self._scan_jupiter_fresh()
            tokens.extend(jupiter_tokens)
            
            # 4. Suodata ultra-fresh (max 2 minuuttia)
            ultra_fresh = self._filter_ultra_fresh(tokens)
            
            # 5. Järjestä score mukaan
            ultra_fresh.sort(key=lambda x: x.overall_score, reverse=True)
            
            self.logger.info(f"✅ Löydettiin {len(ultra_fresh)} ULTRA-FRESH tokenia (< 2 min)")
            return ultra_fresh
            
        except Exception as e:
            self.logger.error(f"❌ Virhe ultra-fresh skannauksessa: {e}")
            return []

    async def _scan_pump_fun(self) -> List[UltraFreshToken]:
        """Skannaa Pump.fun - paras lähde uusille tokeneille"""
        tokens = []
        
        try:
            # Pump.fun API - uusimmat tokeneet
            url = f"{self.pump_fun_url}?sort=created_timestamp&order=desc&limit=50"
            
            async with self.session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and 'data' in data:
                        for token_data in data['data']:
                            try:
                                token = self._parse_pump_fun_token(token_data)
                                if token and token.age_minutes <= self.max_age_minutes:
                                    tokens.append(token)
                            except Exception as e:
                                self.logger.warning(f"Virhe parsin Pump.fun token: {e}")
                                
                    self.logger.info(f"✅ Pump.fun: Löydettiin {len(tokens)} ultra-fresh tokenia")
                else:
                    self.logger.warning(f"Pump.fun API virhe: {response.status}")
                    
        except Exception as e:
            self.logger.warning(f"Pump.fun API virhe: {e}")
            
        return tokens

    async def _scan_dexscreener_fresh(self) -> List[UltraFreshToken]:
        """Skannaa DexScreener - suodatettu uusille"""
        tokens = []
        
        try:
            # DexScreener - uusimmat Solana tokenit
            url = f"{self.dexscreener_url}?sort=createdAt&order=desc"
            
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and 'pairs' in data:
                        for pair_data in data['pairs']:
                            try:
                                token = self._parse_dexscreener_fresh(pair_data)
                                if token and token.age_minutes <= self.max_age_minutes:
                                    tokens.append(token)
                            except Exception as e:
                                self.logger.warning(f"Virhe parsin DexScreener fresh: {e}")
                                
                    self.logger.info(f"✅ DexScreener Fresh: Löydettiin {len(tokens)} ultra-fresh tokenia")
                else:
                    self.logger.warning(f"DexScreener API virhe: {response.status}")
                    
        except Exception as e:
            self.logger.warning(f"DexScreener API virhe: {e}")
            
        return tokens

    async def _scan_jupiter_fresh(self) -> List[UltraFreshToken]:
        """Skannaa Jupiter - uusimmat"""
        tokens = []
        
        try:
            # Jupiter API - trending tokens
            url = f"{self.jupiter_url}/tokens"
            
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and isinstance(data, list):
                        for token_data in data[:20]:  # Top 20
                            try:
                                token = self._parse_jupiter_fresh(token_data)
                                if token and token.age_minutes <= self.max_age_minutes:
                                    tokens.append(token)
                            except Exception as e:
                                self.logger.warning(f"Virhe parsin Jupiter fresh: {e}")
                                
                    self.logger.info(f"✅ Jupiter Fresh: Löydettiin {len(tokens)} ultra-fresh tokenia")
                else:
                    self.logger.warning(f"Jupiter API virhe: {response.status}")
                    
        except Exception as e:
            self.logger.warning(f"Jupiter API virhe: {e}")
            
        return tokens

    def _parse_pump_fun_token(self, data: Dict) -> Optional[UltraFreshToken]:
        """Parse Pump.fun token data"""
        try:
            address = data.get('mint', '')
            symbol = data.get('symbol', 'UNKNOWN')
            name = data.get('name', 'Unknown Token')
            
            # Hae hinta ja market cap
            price = float(data.get('usd_market_cap', 0)) / float(data.get('total_supply', 1))
            market_cap = float(data.get('usd_market_cap', 0))
            volume_24h = float(data.get('volume_24h', 0))
            
            # Laske age
            created_timestamp = data.get('created_timestamp', 0)
            created_time = datetime.fromtimestamp(created_timestamp)
            age_minutes = (datetime.now() - created_time).total_seconds() / 60
            
            # Laske skoorit
            social_score = self._calculate_social_score_pump(data)
            technical_score = self._calculate_technical_score(market_cap, volume_24h, age_minutes)
            risk_score = self._calculate_risk_score(market_cap, age_minutes)
            overall_score = (social_score + technical_score + risk_score) / 3
            
            return UltraFreshToken(
                address=address,
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_1h=0.0,  # Ei dataa
                liquidity=market_cap * 0.5,  # Arvio
                age_minutes=age_minutes,
                holders=int(data.get('holder_count', 0)),
                social_score=social_score,
                technical_score=technical_score,
                risk_score=risk_score,
                overall_score=overall_score,
                timestamp=datetime.now(),
                source="pump.fun"
            )
            
        except Exception as e:
            self.logger.warning(f"Virhe parsin Pump.fun token: {e}")
            return None

    def _parse_dexscreener_fresh(self, pair: Dict) -> Optional[UltraFreshToken]:
        """Parse DexScreener fresh token data"""
        try:
            base_token = pair.get('baseToken', {})
            address = base_token.get('address', '')
            symbol = base_token.get('symbol', 'UNKNOWN')
            name = base_token.get('name', 'Unknown Token')
            
            price = float(pair.get('priceUsd', 0))
            market_cap = float(pair.get('marketCap', 0))
            volume_24h = float(pair.get('volume', {}).get('h24', 0))
            
            # Laske age
            pair_created_at = pair.get('pairCreatedAt', 0)
            if pair_created_at:
                created_time = datetime.fromtimestamp(pair_created_at / 1000)
                age_minutes = (datetime.now() - created_time).total_seconds() / 60
            else:
                age_minutes = 0.5  # Arvio
            
            # Laske skoorit
            social_score = self._calculate_social_score_dex(pair)
            technical_score = self._calculate_technical_score(market_cap, volume_24h, age_minutes)
            risk_score = self._calculate_risk_score(market_cap, age_minutes)
            overall_score = (social_score + technical_score + risk_score) / 3
            
            return UltraFreshToken(
                address=address,
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_1h=float(pair.get('priceChange', {}).get('h1', 0)),
                liquidity=float(pair.get('liquidity', {}).get('usd', 0)),
                age_minutes=age_minutes,
                holders=int(pair.get('info', {}).get('holders', 0)),
                social_score=social_score,
                technical_score=technical_score,
                risk_score=risk_score,
                overall_score=overall_score,
                timestamp=datetime.now(),
                source="dexscreener"
            )
            
        except Exception as e:
            self.logger.warning(f"Virhe parsin DexScreener fresh: {e}")
            return None

    def _parse_jupiter_fresh(self, data: Dict) -> Optional[UltraFreshToken]:
        """Parse Jupiter fresh token data"""
        try:
            address = data.get('address', '')
            symbol = data.get('symbol', 'UNKNOWN')
            name = data.get('name', 'Unknown Token')
            
            # Jupiter ei anna suoraan market cap dataa
            price = 0.0
            market_cap = 0.0
            volume_24h = 0.0
            
            # Arvio age (ei tarkkaa dataa)
            age_minutes = 1.0  # Arvio 1 minuutti
            
            # Laske skoorit
            social_score = 5.0  # Arvio
            technical_score = 5.0  # Arvio
            risk_score = 5.0  # Arvio
            overall_score = 5.0
            
            return UltraFreshToken(
                address=address,
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_1h=0.0,
                liquidity=0.0,
                age_minutes=age_minutes,
                holders=0,
                social_score=social_score,
                technical_score=technical_score,
                risk_score=risk_score,
                overall_score=overall_score,
                timestamp=datetime.now(),
                source="jupiter"
            )
            
        except Exception as e:
            self.logger.warning(f"Virhe parsin Jupiter fresh: {e}")
            return None

    def _filter_ultra_fresh(self, tokens: List[UltraFreshToken]) -> List[UltraFreshToken]:
        """Suodata ULTRA-FRESH tokenit (max 2 minuuttia)"""
        ultra_fresh = []
        
        for token in tokens:
            # TIUKAT kriteerit uusille tokeneille
            if (token.age_minutes <= self.max_age_minutes and  # MAX 2 minuuttia
                self.min_market_cap <= token.market_cap <= self.max_market_cap and  # 10k-50k MC
                token.volume_24h >= token.market_cap * self.min_volume_ratio and  # Volume >= MC
                token.liquidity >= token.market_cap * self.min_liquidity_ratio):  # Liquidity >= 30% MC
                
                ultra_fresh.append(token)
                self.logger.info(f"✅ ULTRA-FRESH: {token.symbol} - Age: {token.age_minutes:.1f}min, MC: ${token.market_cap:,.0f}")
                
        return ultra_fresh

    def _calculate_social_score_pump(self, data: Dict) -> float:
        """Laske social score Pump.fun datasta"""
        score = 5.0
        
        # Holder count
        holders = int(data.get('holder_count', 0))
        if holders > 100:
            score += 2.0
        elif holders > 50:
            score += 1.0
            
        # Volume activity
        volume = float(data.get('volume_24h', 0))
        if volume > 10000:
            score += 1.5
        elif volume > 5000:
            score += 1.0
            
        return min(score, 10.0)

    def _calculate_social_score_dex(self, pair: Dict) -> float:
        """Laske social score DexScreener datasta"""
        score = 5.0
        
        # Volume activity
        volume = float(pair.get('volume', {}).get('h24', 0))
        if volume > 10000:
            score += 2.0
        elif volume > 5000:
            score += 1.5
            
        # Liquidity
        liquidity = float(pair.get('liquidity', {}).get('usd', 0))
        if liquidity > 5000:
            score += 1.5
        elif liquidity > 2000:
            score += 1.0
            
        return min(score, 10.0)

    def _calculate_technical_score(self, market_cap: float, volume: float, age_minutes: float) -> float:
        """Laske technical score"""
        score = 5.0
        
        # Age bonus (uudempi = parempi)
        if age_minutes < 0.5:  # Alle 30 sekuntia
            score += 3.0
        elif age_minutes < 1.0:  # Alle 1 minuutti
            score += 2.0
        elif age_minutes < 2.0:  # Alle 2 minuuttia
            score += 1.0
            
        # Volume/MC ratio
        if market_cap > 0:
            volume_ratio = volume / market_cap
            if volume_ratio > 2.0:
                score += 2.0
            elif volume_ratio > 1.0:
                score += 1.0
                
        return min(score, 10.0)

    def _calculate_risk_score(self, market_cap: float, age_minutes: float) -> float:
        """Laske risk score (pienempi = parempi)"""
        score = 5.0
        
        # Age risk (uudempi = riskialtisempi)
        if age_minutes < 0.5:
            score -= 2.0  # Korkea riski
        elif age_minutes < 1.0:
            score -= 1.0  # Keskitaso riski
            
        # Market cap risk
        if market_cap < 15000:
            score -= 1.0  # Pieni MC = korkea riski
        elif market_cap > 40000:
            score += 1.0  # Suurempi MC = pienempi riski
            
        return max(score, 1.0)

# Test function
async def test_optimized_scanner():
    """Testaa optimoitua skanneria"""
    logging.basicConfig(level=logging.INFO)
    
    async with OptimizedTokenScanner() as scanner:
        tokens = await scanner.scan_ultra_fresh_tokens()
        
        print(f"\n🚀 Löydettiin {len(tokens)} ULTRA-FRESH tokenia (< 2 min):")
        for token in tokens[:10]:  # Näytä top 10
            print(f"  🆕 {token.symbol}: Age: {token.age_minutes:.1f}min, MC: ${token.market_cap:,.0f}, Score: {token.overall_score:.1f}, Source: {token.source}")

if __name__ == "__main__":
    asyncio.run(test_optimized_scanner())
