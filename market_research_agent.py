#!/usr/bin/env python3
"""
Market Research Agent - Hakee tuoreinta tietoa uusien tokenien markkinoista
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import os
from dotenv import load_dotenv

# Lataa environment variables
load_dotenv()

# Konfiguroi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Markkinatiedot"""
    timestamp: str
    total_market_cap: float
    total_volume: float
    new_tokens_24h: int
    successful_tokens_24h: int
    avg_token_lifespan: float
    top_performing_strategies: List[str]
    market_sentiment: str
    volatility_index: float
    liquidity_conditions: str
    trending_keywords: List[str]
    social_media_mentions: int
    institutional_activity: str
    regulatory_news: List[str]
    technical_indicators: Dict[str, float]
    risk_factors: List[str]
    opportunities: List[str]

@dataclass
class TokenAnalysis:
    """Token-analyysi"""
    symbol: str
    name: str
    launch_time: str
    current_price: float
    market_cap: float
    volume_24h: float
    price_change_24h: float
    holders: int
    liquidity: float
    social_score: float
    technical_score: float
    risk_score: float
    success_probability: float
    recommended_strategy: str
    key_factors: List[str]

class MarketResearchAgent:
    """Markkinatutkimus-agentti"""
    
    def __init__(self):
        self.session = None
        self.research_data = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def research_market_conditions(self) -> MarketData:
        """Tutki markkinaolosuhteet"""
        logger.info("🔍 Tutkitaan markkinaolosuhteita...")
        
        # Kerää data eri lähteistä
        market_data = await asyncio.gather(
            self._get_dexscreener_data(),
            self._get_coingecko_data(),
            self._get_social_sentiment(),
            self._get_news_sentiment(),
            self._get_technical_indicators(),
            return_exceptions=True
        )
        
        # Yhdistä data
        combined_data = self._combine_market_data(market_data)
        
        return MarketData(
            timestamp=datetime.now().isoformat(),
            total_market_cap=combined_data.get('total_market_cap', 0),
            total_volume=combined_data.get('total_volume', 0),
            new_tokens_24h=combined_data.get('new_tokens_24h', 0),
            successful_tokens_24h=combined_data.get('successful_tokens_24h', 0),
            avg_token_lifespan=combined_data.get('avg_token_lifespan', 0),
            top_performing_strategies=combined_data.get('top_performing_strategies', []),
            market_sentiment=combined_data.get('market_sentiment', 'neutral'),
            volatility_index=combined_data.get('volatility_index', 0.5),
            liquidity_conditions=combined_data.get('liquidity_conditions', 'normal'),
            trending_keywords=combined_data.get('trending_keywords', []),
            social_media_mentions=combined_data.get('social_media_mentions', 0),
            institutional_activity=combined_data.get('institutional_activity', 'low'),
            regulatory_news=combined_data.get('regulatory_news', []),
            technical_indicators=combined_data.get('technical_indicators', {}),
            risk_factors=combined_data.get('risk_factors', []),
            opportunities=combined_data.get('opportunities', [])
        )
    
    async def _get_dexscreener_data(self) -> Dict:
        """Hae data DexScreeneristä"""
        try:
            # Solana pairs
            url = "https://api.dexscreener.com/latest/dex/tokens/solana"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    # Analysoi uudet tokenit
                    new_tokens = [p for p in pairs if self._is_new_token(p)]
                    successful_tokens = [p for p in new_tokens if self._is_successful_token(p)]
                    
                    return {
                        'new_tokens_24h': len(new_tokens),
                        'successful_tokens_24h': len(successful_tokens),
                        'avg_token_lifespan': self._calculate_avg_lifespan(new_tokens),
                        'top_performing_strategies': self._identify_top_strategies(successful_tokens),
                        'volatility_index': self._calculate_volatility_index(pairs),
                        'liquidity_conditions': self._assess_liquidity_conditions(pairs)
                    }
        except Exception as e:
            logger.error(f"Virhe DexScreener datassa: {e}")
            return {}
    
    async def _get_coingecko_data(self) -> Dict:
        """Hae data CoinGeckosta"""
        try:
            # Market data
            url = "https://api.coingecko.com/api/v3/global"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    market_data = data.get('data', {})
                    
                    return {
                        'total_market_cap': market_data.get('total_market_cap', {}).get('usd', 0),
                        'total_volume': market_data.get('total_volume', {}).get('usd', 0),
                        'market_sentiment': self._assess_market_sentiment(market_data)
                    }
        except Exception as e:
            logger.error(f"Virhe CoinGecko datassa: {e}")
            return {}
    
    async def _get_social_sentiment(self) -> Dict:
        """Hae sosiaalisen median sentimentti"""
        try:
            # Simuloi sosiaalisen median data
            return {
                'social_media_mentions': 1250,
                'trending_keywords': ['meme', 'ai', 'gaming', 'defi', 'nft'],
                'market_sentiment': 'bullish'
            }
        except Exception as e:
            logger.error(f"Virhe sosiaalisen median datassa: {e}")
            return {}
    
    async def _get_news_sentiment(self) -> Dict:
        """Hae uutisten sentimentti"""
        try:
            # Simuloi uutisdata
            return {
                'regulatory_news': [
                    'SEC approves new crypto regulations',
                    'EU implements MiCA framework',
                    'Japan eases crypto restrictions'
                ],
                'institutional_activity': 'high',
                'risk_factors': [
                    'Regulatory uncertainty',
                    'Market volatility',
                    'Liquidity concerns'
                ],
                'opportunities': [
                    'Institutional adoption',
                    'DeFi growth',
                    'NFT market expansion'
                ]
            }
        except Exception as e:
            logger.error(f"Virhe uutisdatassa: {e}")
            return {}
    
    async def _get_technical_indicators(self) -> Dict:
        """Hae teknisiä indikaattoreita"""
        try:
            # Simuloi teknisiä indikaattoreita
            return {
                'technical_indicators': {
                    'rsi': 65.5,
                    'macd': 0.02,
                    'bollinger_position': 0.7,
                    'volume_trend': 1.2,
                    'momentum': 0.8
                }
            }
        except Exception as e:
            logger.error(f"Virhe teknisten indikaattoreiden datassa: {e}")
            return {}
    
    def _is_new_token(self, pair: Dict) -> bool:
        """Tarkista onko token uusi (alle 24h)"""
        try:
            # Simuloi uusien tokenien tunnistus
            return pair.get('priceChange', {}).get('h24', 0) > 100  # Yli 100% muutos 24h
        except:
            return False
    
    def _is_successful_token(self, pair: Dict) -> bool:
        """Tarkista onko token menestynyt"""
        try:
            price_change = pair.get('priceChange', {}).get('h24', 0)
            volume = pair.get('volume', {}).get('h24', 0)
            return price_change > 50 and volume > 10000  # Yli 50% nousu ja volume
        except:
            return False
    
    def _calculate_avg_lifespan(self, tokens: List[Dict]) -> float:
        """Laske keskimääräinen token elinikä"""
        # Simuloi elinikä laskenta
        return 2.5  # 2.5 tuntia
    
    def _identify_top_strategies(self, successful_tokens: List[Dict]) -> List[str]:
        """Tunnista parhaat strategiat"""
        return [
            "Ultra-fresh momentum",
            "Volume spike trading",
            "Social sentiment following",
            "Technical breakout",
            "Liquidity hunting"
        ]
    
    def _calculate_volatility_index(self, pairs: List[Dict]) -> float:
        """Laske volatiliteetti-indeksi"""
        # Simuloi volatiliteetti laskenta
        return 0.75  # Korkea volatiliteetti
    
    def _assess_liquidity_conditions(self, pairs: List[Dict]) -> str:
        """Arvioi likviditeetti-olosuhteet"""
        # Simuloi likviditeetti arviointi
        return "high"  # Korkea likviditeetti
    
    def _assess_market_sentiment(self, market_data: Dict) -> str:
        """Arvioi markkinasentimentti"""
        # Simuloi sentimentti arviointi
        return "bullish"  # Nousutrendi
    
    def _combine_market_data(self, data_list: List) -> Dict:
        """Yhdistä markkinadata"""
        combined = {}
        for data in data_list:
            if isinstance(data, dict):
                combined.update(data)
        return combined
    
    async def analyze_specific_tokens(self, token_addresses: List[str]) -> List[TokenAnalysis]:
        """Analysoi tiettyjä tokeneita"""
        logger.info(f"🔍 Analysoidaan {len(token_addresses)} tokenia...")
        
        analyses = []
        for address in token_addresses:
            try:
                analysis = await self._analyze_token(address)
                if analysis:
                    analyses.append(analysis)
            except Exception as e:
                logger.error(f"Virhe tokenin {address} analyysissä: {e}")
        
        return analyses
    
    async def _analyze_token(self, address: str) -> Optional[TokenAnalysis]:
        """Analysoi yksittäinen token"""
        try:
            # Hae token data
            url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    if pairs:
                        pair = pairs[0]  # Ota ensimmäinen pair
                        
                        # Laske skoorit
                        social_score = self._calculate_social_score(pair)
                        technical_score = self._calculate_technical_score(pair)
                        risk_score = self._calculate_risk_score(pair)
                        success_probability = self._calculate_success_probability(pair)
                        
                        return TokenAnalysis(
                            symbol=pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                            name=pair.get('baseToken', {}).get('name', 'Unknown Token'),
                            launch_time=datetime.now().isoformat(),
                            current_price=float(pair.get('priceUsd', 0)),
                            market_cap=float(pair.get('marketCap', 0)),
                            volume_24h=float(pair.get('volume', {}).get('h24', 0)),
                            price_change_24h=float(pair.get('priceChange', {}).get('h24', 0)),
                            holders=1000,  # Simuloi
                            liquidity=float(pair.get('liquidity', {}).get('usd', 0)),
                            social_score=social_score,
                            technical_score=technical_score,
                            risk_score=risk_score,
                            success_probability=success_probability,
                            recommended_strategy=self._recommend_strategy(pair),
                            key_factors=self._identify_key_factors(pair)
                        )
        except Exception as e:
            logger.error(f"Virhe tokenin {address} analyysissä: {e}")
            return None
    
    def _calculate_social_score(self, pair: Dict) -> float:
        """Laske sosiaalinen skoori"""
        # Simuloi sosiaalinen skoori
        return 7.5
    
    def _calculate_technical_score(self, pair: Dict) -> float:
        """Laske tekninen skoori"""
        # Simuloi tekninen skoori
        return 8.2
    
    def _calculate_risk_score(self, pair: Dict) -> float:
        """Laske riski-skoori"""
        # Simuloi riski-skoori
        return 6.0
    
    def _calculate_success_probability(self, pair: Dict) -> float:
        """Laske menestymistodennäköisyys"""
        # Simuloi menestymistodennäköisyys
        return 0.75
    
    def _recommend_strategy(self, pair: Dict) -> str:
        """Suosittele strategia"""
        # Simuloi strategia suositus
        return "Ultra-fresh momentum trading"
    
    def _identify_key_factors(self, pair: Dict) -> List[str]:
        """Tunnista keskeiset tekijät"""
        return [
            "High volume spike",
            "Strong momentum",
            "Low market cap",
            "Fresh liquidity",
            "Social buzz"
        ]
    
    def save_research_data(self, market_data: MarketData, token_analyses: List[TokenAnalysis]):
        """Tallenna tutkimusdata"""
        filename = f"market_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            'market_data': asdict(market_data),
            'token_analyses': [asdict(analysis) for analysis in token_analyses],
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Tutkimusdata tallennettu: {filename}")

async def main():
    """Pääfunktio"""
    async with MarketResearchAgent() as agent:
        try:
            # Tutki markkinaolosuhteet
            market_data = await agent.research_market_conditions()
            
            # Analysoi tiettyjä tokeneita
            token_addresses = [
                "So11111111111111111111111111111111111111112",  # SOL
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"   # BONK
            ]
            
            token_analyses = await agent.analyze_specific_tokens(token_addresses)
            
            # Tallenna data
            agent.save_research_data(market_data, token_analyses)
            
            # Tulosta yhteenveto
            print("\n" + "="*80)
            print("📊 MARKKINATUTKIMUS RAPORTTI")
            print("="*80)
            print(f"📈 Kokonaismarkkina-arvo: ${market_data.total_market_cap:,.0f}")
            print(f"💰 Kokonaisvolume: ${market_data.total_volume:,.0f}")
            print(f"🆕 Uusia tokeneita 24h: {market_data.new_tokens_24h}")
            print(f"✅ Menestyneitä tokeneita: {market_data.successful_tokens_24h}")
            print(f"⏱️ Keskimääräinen elinikä: {market_data.avg_token_lifespan:.1f}h")
            print(f"📊 Markkinasentimentti: {market_data.market_sentiment}")
            print(f"📈 Volatiliteetti: {market_data.volatility_index:.2f}")
            print(f"💧 Likviditeetti: {market_data.liquidity_conditions}")
            
            print("\n🚀 PARHAAT STRATEGIAT:")
            for strategy in market_data.top_performing_strategies:
                print(f"  • {strategy}")
            
            print("\n📱 TRENDING KEYWORDS:")
            for keyword in market_data.trending_keywords:
                print(f"  • {keyword}")
            
            print("\n⚠️ RISKITEKIJÄT:")
            for risk in market_data.risk_factors:
                print(f"  • {risk}")
            
            print("\n💡 MAHDOLLISUUDET:")
            for opportunity in market_data.opportunities:
                print(f"  • {opportunity}")
            
            print(f"\n🔍 ANALYSOITU {len(token_analyses)} TOKENIA")
            for analysis in token_analyses:
                print(f"  • {analysis.symbol}: {analysis.success_probability:.1%} menestymistodennäköisyys")
            
            print("\n" + "="*80)
            print("✅ Markkinatutkimus valmis!")
            print("="*80)
            
        except Exception as e:
            logger.error(f"❌ Virhe markkinatutkimuksessa: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())
