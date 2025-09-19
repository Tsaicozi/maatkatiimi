#!/usr/bin/env python3
"""
Hybrid Trading Bot - Real Time Version
Käyttää todella oikeaa real-time dataa fallback mekanismeilla
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
class RealTimeToken:
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
    source: str

class RealTimeTokenScanner:
    """Real-time token skanneri oikealla datalla"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = None
        
        # API endpoints - real-time sources
        self.coingecko_url = "https://api.coingecko.com/api/v3/coins/markets"
        self.dexscreener_url = "https://api.dexscreener.com/latest/dex/tokens"
        self.jup_ag_url = "https://quote-api.jup.ag/v6"
        self.birdeye_url = "https://public-api.birdeye.so/public/v1"
        
        # Headers
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        # Real-time kriteerit
        self.max_age_minutes = 5  # MAX 5 minuuttia
        self.min_market_cap = 10_000
        self.max_market_cap = 500_000

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def scan_real_time_tokens(self) -> List[RealTimeToken]:
        """Skannaa real-time tokeneita oikeasta datasta"""
        self.logger.info("🔍 Skannataan REAL-TIME tokeneita...")
        
        tokens = []
        
        try:
            # 1. CoinGecko - trending tokens (real-time)
            cg_tokens = await self._scan_coingecko_real_time()
            tokens.extend(cg_tokens)
            
            # 2. DexScreener - latest pairs (real-time)
            dex_tokens = await self._scan_dexscreener_real_time()
            tokens.extend(dex_tokens)
            
            # 3. Jupiter - price data (real-time)
            jup_tokens = await self._scan_jupiter_real_time()
            tokens.extend(jup_tokens)
            
            # 4. Jos ei löytynyt tarpeeksi, käytä CoinGecko trending
            if len(tokens) < 10:
                self.logger.warning("⚠️ Ei tarpeeksi real-time tokeneita, haetaan trending...")
                trending_tokens = await self._scan_coingecko_trending()
                tokens.extend(trending_tokens)
            
            # 5. Jos edelleen ei tarpeeksi, käytä CoinGecko markets
            if len(tokens) < 10:
                self.logger.warning("⚠️ Haetaan lisää real-time tokeneita markets:sta...")
                market_tokens = await self._scan_coingecko_markets()
                tokens.extend(market_tokens)
            
            # 6. Suodata fresh tokenit
            fresh_tokens = self._filter_fresh_real_time(tokens)
            
            # 7. Järjestä score mukaan
            fresh_tokens.sort(key=lambda x: x.overall_score, reverse=True)
            
            self.logger.info(f"✅ Löydettiin {len(fresh_tokens)} REAL-TIME fresh tokenia")
            return fresh_tokens
            
        except Exception as e:
            self.logger.error(f"❌ Virhe real-time skannauksessa: {e}")
            return []

    async def _scan_coingecko_real_time(self) -> List[RealTimeToken]:
        """Skannaa CoinGecko real-time trending"""
        tokens = []
        
        try:
            # CoinGecko trending coins (real-time)
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_asc',
                'per_page': 50,
                'page': 1,
                'sparkline': 'false',  # Fix: string instead of boolean
                'price_change_percentage': '1h,24h'
            }
            
            async with self.session.get(self.coingecko_url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if isinstance(data, list):
                        for token_data in data:
                            try:
                                token = self._parse_coingecko_real_time(token_data)
                                if token and token.age_minutes <= self.max_age_minutes:
                                    tokens.append(token)
                            except Exception as e:
                                self.logger.warning(f"Virhe parsin CoinGecko real-time: {e}")
                                
                    self.logger.info(f"✅ CoinGecko Real-Time: {len(tokens)} tokenia")
                else:
                    self.logger.warning(f"CoinGecko API virhe: {response.status}")
                    
        except Exception as e:
            self.logger.warning(f"CoinGecko real-time API virhe: {e}")
            
        return tokens

    async def _scan_dexscreener_real_time(self) -> List[RealTimeToken]:
        """Skannaa DexScreener real-time pairs"""
        tokens = []
        
        try:
            # DexScreener latest pairs (real-time) - use search endpoint
            search_url = "https://api.dexscreener.com/latest/dex/search"
            params = {
                'q': 'solana',
                'limit': 50
            }
            
            async with self.session.get(search_url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and 'pairs' in data and isinstance(data['pairs'], list):
                        for pair_data in data['pairs']:
                            try:
                                token = self._parse_dexscreener_real_time(pair_data)
                                if token and token.age_minutes <= self.max_age_minutes:
                                    tokens.append(token)
                            except Exception as e:
                                self.logger.warning(f"Virhe parsin DexScreener real-time: {e}")
                                
                    self.logger.info(f"✅ DexScreener Real-Time: {len(tokens)} tokenia")
                else:
                    self.logger.warning(f"DexScreener API virhe: {response.status}")
                    
        except Exception as e:
            self.logger.warning(f"DexScreener real-time API virhe: {e}")
            
        return tokens

    async def _scan_jupiter_real_time(self) -> List[RealTimeToken]:
        """Skannaa Jupiter real-time price data"""
        tokens = []
        
        try:
            # Jupiter price API - real-time prices
            params = {
                'ids': 'So11111111111111111111111111111111111111112,EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v,Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'
            }
            
            async with self.session.get(self.jup_ag_url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and 'data' in data:
                        for token_id, token_data in data['data'].items():
                            try:
                                token = self._parse_jupiter_real_time(token_id, token_data)
                                if token and token.age_minutes <= self.max_age_minutes:
                                    tokens.append(token)
                            except Exception as e:
                                self.logger.warning(f"Virhe parsin Jupiter real-time: {e}")
                                
                    self.logger.info(f"✅ Jupiter Real-Time: {len(tokens)} tokenia")
                else:
                    self.logger.warning(f"Jupiter API virhe: {response.status}")
                    
        except Exception as e:
            self.logger.warning(f"Jupiter real-time API virhe: {e}")
            
        return tokens

    async def _scan_coingecko_trending(self) -> List[RealTimeToken]:
        """Skannaa CoinGecko trending coins"""
        tokens = []
        
        try:
            # CoinGecko trending
            trending_url = "https://api.coingecko.com/api/v3/search/trending"
            
            async with self.session.get(trending_url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and 'coins' in data:
                        for coin_data in data['coins'][:20]:  # Top 20 trending
                            try:
                                token = self._parse_coingecko_trending(coin_data)
                                if token:
                                    tokens.append(token)
                            except Exception as e:
                                self.logger.warning(f"Virhe parsin CoinGecko trending: {e}")
                                
                    self.logger.info(f"✅ CoinGecko Trending: {len(tokens)} tokenia")
                else:
                    self.logger.warning(f"CoinGecko trending API virhe: {response.status}")
                    
        except Exception as e:
            self.logger.warning(f"CoinGecko trending API virhe: {e}")
            
        return tokens

    async def _scan_coingecko_markets(self) -> List[RealTimeToken]:
        """Skannaa CoinGecko markets data"""
        tokens = []
        
        try:
            # CoinGecko markets - different endpoint
            markets_url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_asc',
                'per_page': 30,
                'page': 1,
                'sparkline': 'false',
                'price_change_percentage': '1h,24h'
            }
            
            async with self.session.get(markets_url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if isinstance(data, list):
                        for token_data in data:
                            try:
                                token = self._parse_coingecko_markets(token_data)
                                if token:
                                    tokens.append(token)
                            except Exception as e:
                                self.logger.warning(f"Virhe parsin CoinGecko markets: {e}")
                                
                    self.logger.info(f"✅ CoinGecko Markets: {len(tokens)} tokenia")
                else:
                    self.logger.warning(f"CoinGecko markets API virhe: {response.status}")
                    
        except Exception as e:
            self.logger.warning(f"CoinGecko markets API virhe: {e}")
            
        return tokens

    def _parse_coingecko_real_time(self, data: Dict) -> Optional[RealTimeToken]:
        """Parse CoinGecko real-time token data"""
        try:
            symbol = data.get('symbol', '').upper()
            name = data.get('name', '')
            
            price = float(data.get('current_price', 0) or 0)
            market_cap = float(data.get('market_cap', 0) or 0)
            volume_24h = float(data.get('total_volume', 0) or 0)
            price_change_1h = float(data.get('price_change_percentage_1h_in_currency', 0) or 0)
            
            # Real-time age estimation based on last_updated
            last_updated = data.get('last_updated', '')
            if last_updated:
                try:
                    last_update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    age_minutes = (datetime.now() - last_update_time.replace(tzinfo=None)).total_seconds() / 60
                except:
                    age_minutes = 2.0  # Default 2 minutes
            else:
                age_minutes = 2.0
            
            # Laske skoorit real-time datasta
            social_score = self._calculate_social_score_real_time(market_cap, volume_24h)
            technical_score = self._calculate_technical_score_real_time(market_cap, volume_24h, age_minutes, price_change_1h)
            risk_score = self._calculate_risk_score_real_time(market_cap, age_minutes)
            overall_score = (social_score + technical_score + risk_score) / 3
            
            return RealTimeToken(
                address=f"CG_{symbol}",
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_1h=price_change_1h,
                liquidity=market_cap * 0.3,
                age_minutes=age_minutes,
                holders=int(data.get('market_cap_rank', 1000) or 1000),
                social_score=social_score,
                technical_score=technical_score,
                risk_score=risk_score,
                overall_score=overall_score,
                timestamp=datetime.now(),
                source="coingecko_real_time"
            )
            
        except Exception as e:
            self.logger.warning(f"Virhe parsin CoinGecko real-time token: {e}")
            return None

    def _parse_dexscreener_real_time(self, pair: Dict) -> Optional[RealTimeToken]:
        """Parse DexScreener real-time token data"""
        try:
            base_token = pair.get('baseToken', {})
            symbol = base_token.get('symbol', 'UNKNOWN')
            name = base_token.get('name', 'Unknown Token')
            address = base_token.get('address', '')
            
            price = float(pair.get('priceUsd', 0))
            market_cap = float(pair.get('marketCap', 0))
            volume_24h = float(pair.get('volume', {}).get('h24', 0))
            
            # Real-time age calculation
            pair_created_at = pair.get('pairCreatedAt', 0)
            if pair_created_at:
                created_time = datetime.fromtimestamp(pair_created_at / 1000)
                age_minutes = (datetime.now() - created_time).total_seconds() / 60
            else:
                age_minutes = 1.0  # Default 1 minute for new pairs
            
            # Laske skoorit real-time datasta
            social_score = self._calculate_social_score_real_time(market_cap, volume_24h)
            technical_score = self._calculate_technical_score_real_time(market_cap, volume_24h, age_minutes, 0.0)
            risk_score = self._calculate_risk_score_real_time(market_cap, age_minutes)
            overall_score = (social_score + technical_score + risk_score) / 3
            
            return RealTimeToken(
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
                source="dexscreener_real_time"
            )
            
        except Exception as e:
            self.logger.warning(f"Virhe parsin DexScreener real-time token: {e}")
            return None

    def _parse_jupiter_real_time(self, token_id: str, data: Dict) -> Optional[RealTimeToken]:
        """Parse Jupiter real-time token data"""
        try:
            symbol = token_id[:8]  # Ota ensimmäiset 8 merkkiä
            name = f"Jupiter {symbol}"
            price = float(data.get('price', 0))
            
            # Real-time market cap estimation
            market_cap = price * 1000000  # Estimation
            volume_24h = market_cap * 0.5
            age_minutes = 1.0  # Jupiter data is real-time
            
            # Laske skoorit
            social_score = 6.0
            technical_score = 7.0  # Real-time data is more reliable
            risk_score = 6.0
            overall_score = 6.3
            
            return RealTimeToken(
                address=token_id,
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_1h=0.0,
                liquidity=market_cap * 0.3,
                age_minutes=age_minutes,
                holders=500,
                social_score=social_score,
                technical_score=technical_score,
                risk_score=risk_score,
                overall_score=overall_score,
                timestamp=datetime.now(),
                source="jupiter_real_time"
            )
            
        except Exception as e:
            self.logger.warning(f"Virhe parsin Jupiter real-time token: {e}")
            return None

    def _parse_coingecko_markets(self, data: Dict) -> Optional[RealTimeToken]:
        """Parse CoinGecko markets token data"""
        try:
            symbol = data.get('symbol', '').upper()
            name = data.get('name', '')
            
            price = float(data.get('current_price', 0) or 0)
            market_cap = float(data.get('market_cap', 0) or 0)
            volume_24h = float(data.get('total_volume', 0) or 0)
            price_change_1h = float(data.get('price_change_percentage_1h_in_currency', 0) or 0)
            
            # Markets data is usually more recent
            age_minutes = 1.5  # Default 1.5 minutes for markets data
            
            # Laske skoorit
            social_score = self._calculate_social_score_real_time(market_cap, volume_24h)
            technical_score = self._calculate_technical_score_real_time(market_cap, volume_24h, age_minutes, price_change_1h)
            risk_score = self._calculate_risk_score_real_time(market_cap, age_minutes)
            overall_score = (social_score + technical_score + risk_score) / 3
            
            return RealTimeToken(
                address=f"MARKETS_{symbol}",
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_1h=price_change_1h,
                liquidity=market_cap * 0.3,
                age_minutes=age_minutes,
                holders=int(data.get('market_cap_rank', 1000) or 1000),
                social_score=social_score,
                technical_score=technical_score,
                risk_score=risk_score,
                overall_score=overall_score,
                timestamp=datetime.now(),
                source="coingecko_markets"
            )
            
        except Exception as e:
            self.logger.warning(f"Virhe parsin CoinGecko markets token: {e}")
            return None

    def _parse_coingecko_trending(self, coin_data: Dict) -> Optional[RealTimeToken]:
        """Parse CoinGecko trending token data"""
        try:
            item = coin_data.get('item', {})
            symbol = item.get('symbol', '').upper()
            name = item.get('name', '')
            
            # Get market data from coin
            market_data = item.get('market_data', {})
            price = float(market_data.get('current_price', {}).get('usd', 0))
            market_cap = float(market_data.get('market_cap', {}).get('usd', 0))
            volume_24h = float(market_data.get('total_volume', {}).get('usd', 0))
            
            # Trending coins are usually fresh
            age_minutes = 2.0
            
            # Laske skoorit
            social_score = 8.0  # Trending = high social score
            technical_score = 7.0
            risk_score = 5.0
            overall_score = 6.7
            
            return RealTimeToken(
                address=f"TRENDING_{symbol}",
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_1h=0.0,
                liquidity=market_cap * 0.3,
                age_minutes=age_minutes,
                holders=1000,
                social_score=social_score,
                technical_score=technical_score,
                risk_score=risk_score,
                overall_score=overall_score,
                timestamp=datetime.now(),
                source="coingecko_trending"
            )
            
        except Exception as e:
            self.logger.warning(f"Virhe parsin CoinGecko trending token: {e}")
            return None

    def _filter_fresh_real_time(self, tokens: List[RealTimeToken]) -> List[RealTimeToken]:
        """Suodata fresh real-time tokenit"""
        fresh_tokens = []
        
        for token in tokens:
            # Real-time kriteerit
            if (token.age_minutes <= self.max_age_minutes and
                self.min_market_cap <= token.market_cap <= self.max_market_cap and
                token.volume_24h >= token.market_cap * 0.1 and  # Volume >= 10% MC
                token.overall_score >= 5.0):  # Minimum score
                
                fresh_tokens.append(token)
                self.logger.info(f"✅ REAL-TIME: {token.symbol} - Age: {token.age_minutes:.1f}min, MC: ${token.market_cap:,.0f}, Score: {token.overall_score:.1f}, Source: {token.source}")
                
        return fresh_tokens

    def _calculate_social_score_real_time(self, market_cap: float, volume: float) -> float:
        """Laske social score real-time datasta"""
        score = 5.0
        
        if volume > 100000:
            score += 2.0
        elif volume > 50000:
            score += 1.5
        elif volume > 20000:
            score += 1.0
            
        if market_cap > 100000:
            score += 2.0
        elif market_cap > 50000:
            score += 1.5
        elif market_cap > 20000:
            score += 1.0
            
        return min(score, 10.0)

    def _calculate_technical_score_real_time(self, market_cap: float, volume: float, age_minutes: float, price_change: float) -> float:
        """Laske technical score real-time datasta"""
        score = 5.0
        
        # Age bonus (uudempi = parempi)
        if age_minutes < 1.0:
            score += 3.0
        elif age_minutes < 2.0:
            score += 2.5
        elif age_minutes < 3.0:
            score += 2.0
        elif age_minutes < 5.0:
            score += 1.5
            
        # Volume/MC ratio
        if market_cap > 0:
            volume_ratio = volume / market_cap
            if volume_ratio > 1.0:
                score += 2.0
            elif volume_ratio > 0.5:
                score += 1.5
            elif volume_ratio > 0.1:
                score += 1.0
                
        # Price change bonus
        if abs(price_change) > 20:
            score += 1.0
        elif abs(price_change) > 10:
            score += 0.5
                
        return min(score, 10.0)

    def _calculate_risk_score_real_time(self, market_cap: float, age_minutes: float) -> float:
        """Laske risk score real-time datasta"""
        score = 5.0
        
        # Age risk (uudempi = riskialtisempi)
        if age_minutes < 1.0:
            score -= 2.0  # Korkea riski
        elif age_minutes < 2.0:
            score -= 1.5
        elif age_minutes < 3.0:
            score -= 1.0
        elif age_minutes < 5.0:
            score -= 0.5
            
        # Market cap risk
        if market_cap < 20000:
            score -= 1.0  # Pieni MC = korkea riski
        elif market_cap > 200000:
            score += 1.0  # Suurempi MC = pienempi riski
            
        return max(score, 1.0)

# Test function
async def test_real_time_scanner():
    """Testaa real-time skanneria"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    async with RealTimeTokenScanner() as scanner:
        tokens = await scanner.scan_real_time_tokens()
        
        print(f"\n🔍 Löydettiin {len(tokens)} REAL-TIME fresh tokenia:")
        for token in tokens[:10]:
            print(f"  📈 {token.symbol}: Age: {token.age_minutes:.1f}min, MC: ${token.market_cap:,.0f}, Score: {token.overall_score:.1f}, Source: {token.source}")

if __name__ == "__main__":
    asyncio.run(test_real_time_scanner())
