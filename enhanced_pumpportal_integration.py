"""
Enhanced PumpPortal Integration - Parannettu PumpPortal-integraatio
Yhdistää reaaliaikaisen datan edistyneisiin analyysityökaluihin
"""

import asyncio
import websockets
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Tuple, Callable
import aiohttp
import time
import os
from dotenv import load_dotenv

# Import our advanced tools
try:
    from advanced_token_screener import AdvancedTokenScreener, AdvancedToken
    from advanced_risk_assessment import AdvancedRiskAssessment
    from ai_sentiment_analysis import AISentimentAnalyzer
    from multi_timeframe_analysis import MultiTimeframeAnalyzer
    ADVANCED_TOOLS_AVAILABLE = True
except ImportError:
    ADVANCED_TOOLS_AVAILABLE = False

# Load environment
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EnhancedTokenEvent:
    """Parannettu token event"""
    timestamp: datetime
    event_type: str  # 'creation', 'trade', 'migration'
    token_address: str
    data: Dict[str, Any]
    # Enhanced analysis
    sentiment_score: float = 0.0
    risk_score: float = 0.0
    technical_score: float = 0.0
    overall_score: float = 0.0
    screening_result: Dict[str, Any] = None
    risk_assessment: Dict[str, Any] = None
    sentiment_analysis: Dict[str, Any] = None
    timeframe_analysis: Dict[str, Any] = None

@dataclass
class PumpPortalMetrics:
    """PumpPortal-mittarit"""
    total_tokens_created: int
    total_volume_24h: float
    total_trades_24h: int
    hot_tokens_count: int
    average_token_age: float
    market_heat: float
    momentum_score: float
    risk_distribution: Dict[str, int]
    top_performers: List[Dict[str, Any]]

class EnhancedPumpPortalClient:
    """Parannettu PumpPortal WebSocket client"""
    
    def __init__(self):
        self.websocket = None
        self.uri = "wss://pumpportal.fun/api/data"
        self.is_connected = False
        self.running = False
        
        # Enhanced tools
        self.screener = None
        self.risk_assessor = None
        self.sentiment_analyzer = None
        self.timeframe_analyzer = None
        
        # Data storage
        self.token_events = []
        self.hot_tokens = []
        self.metrics = PumpPortalMetrics(
            total_tokens_created=0,
            total_volume_24h=0.0,
            total_trades_24h=0,
            hot_tokens_count=0,
            average_token_age=0.0,
            market_heat=0.0,
            momentum_score=0.0,
            risk_distribution={},
            top_performers=[]
        )
        
        # Callbacks
        self.callbacks = {
            'on_token_creation': [],
            'on_token_trade': [],
            'on_migration': [],
            'on_hot_token': [],
            'on_analysis_complete': []
        }
        
        # Configuration
        self.config = {
            'max_events': 1000,
            'analysis_interval': 60,  # seconds
            'hot_token_threshold': 100000,  # volume threshold
            'risk_threshold': 0.7,
            'sentiment_threshold': 0.6
        }
    
    async def initialize_enhanced_tools(self):
        """Alusta edistyneet työkalut"""
        if not ADVANCED_TOOLS_AVAILABLE:
            logger.warning("⚠️ Edistyneet työkalut eivät ole saatavilla")
            return False
        
        try:
            # Alusta työkalut
            self.screener = AdvancedTokenScreener()
            self.risk_assessor = AdvancedRiskAssessment()
            self.sentiment_analyzer = AISentimentAnalyzer()
            self.timeframe_analyzer = MultiTimeframeAnalyzer()
            
            logger.info("✅ Edistyneet työkalut alustettu")
            return True
        except Exception as e:
            logger.error(f"❌ Virhe edistyneiden työkalujen alustuksessa: {e}")
            return False
    
    async def connect(self):
        """Yhdistä PumpPortal WebSocket:iin"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.is_connected = True
            logger.info("✅ Yhdistetty PumpPortal WebSocket:iin")
            return True
        except Exception as e:
            logger.error(f"❌ Virhe WebSocket-yhteydessä: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Katkaise WebSocket-yhteys"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("🔌 WebSocket-yhteys katkaistu")
    
    def add_callback(self, event_type: str, callback: Callable):
        """Lisää callback-funktio"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
        else:
            logger.warning(f"Tuntematon event_type: {event_type}")
    
    async def subscribe_all_events(self):
        """Tilaa kaikki tapahtumat"""
        if not self.is_connected:
            logger.error("Ei yhteyttä WebSocket:iin")
            return False
        
        try:
            # Tilaa uusien tokenien luomistapahtumat
            await self.websocket.send(json.dumps({"method": "subscribeNewToken"}))
            logger.info("📝 Tilattu uusien tokenien luomistapahtumat")
            
            # Tilaa migraatiotapahtumat
            await self.websocket.send(json.dumps({"method": "subscribeMigration"}))
            logger.info("🔄 Tilattu migraatiotapahtumat")
            
            # Tilaa tiettyjen tokenien kauppatapahtumat (esimerkki)
            sample_tokens = [
                "91WNez8D22NwBssQbkzjy4s2ipFrzpmn5hfvWVe2aY5p",
                "Bwc4EBE65qXVzZ9ZiieBraj9GZL4Y2d7NN7B9pXENWR2"
            ]
            await self.websocket.send(json.dumps({
                "method": "subscribeTokenTrade",
                "keys": sample_tokens
            }))
            logger.info(f"📈 Tilattu token-kauppatapahtumat: {len(sample_tokens)} tokenille")
            
            return True
        except Exception as e:
            logger.error(f"❌ Virhe tilausten lähettämisessä: {e}")
            return False
    
    async def _handle_message(self, message: str):
        """Käsittele saapunut viesti"""
        try:
            data = json.loads(message)
            event_type = data.get('type', '')
            
            # Luo enhanced event
            enhanced_event = EnhancedTokenEvent(
                timestamp=datetime.now(),
                event_type=event_type,
                token_address=data.get('token_address', ''),
                data=data
            )
            
            # Lisää event listaan
            self.token_events.append(enhanced_event)
            
            # Rajoita event-määrä
            if len(self.token_events) > self.config['max_events']:
                self.token_events = self.token_events[-self.config['max_events']:]
            
            # Analysoi event reaaliajassa
            await self._analyze_event(enhanced_event)
            
            # Kutsu callbackit
            if event_type == 'new_token':
                for callback in self.callbacks['on_token_creation']:
                    await callback(enhanced_event)
            elif event_type == 'token_trade':
                for callback in self.callbacks['on_token_trade']:
                    await callback(enhanced_event)
            elif event_type == 'migration':
                for callback in self.callbacks['on_migration']:
                    await callback(enhanced_event)
            
        except Exception as e:
            logger.error(f"Virhe viestin käsittelyssä: {e}")
    
    async def _analyze_event(self, event: EnhancedTokenEvent):
        """Analysoi event edistyneillä työkaluilla"""
        try:
            # Token screening
            if self.screener:
                await self._perform_token_screening(event)
            
            # Risk assessment
            if self.risk_assessor:
                await self._perform_risk_assessment(event)
            
            # Sentiment analysis
            if self.sentiment_analyzer:
                await self._perform_sentiment_analysis(event)
            
            # Timeframe analysis (jos saatavilla)
            if self.timeframe_analyzer and event.event_type == 'token_trade':
                await self._perform_timeframe_analysis(event)
            
            # Laske overall score
            event.overall_score = self._calculate_overall_score(event)
            
            # Tarkista onko hot token
            if self._is_hot_token(event):
                self.hot_tokens.append(event)
                for callback in self.callbacks['on_hot_token']:
                    await callback(event)
            
        except Exception as e:
            logger.error(f"Virhe event-analyysissä: {e}")
    
    async def _perform_token_screening(self, event: EnhancedTokenEvent):
        """Suorita token screening"""
        try:
            # Luo AdvancedToken objektin event-datasta
            token_data = self._convert_event_to_advanced_token(event)
            if token_data:
                # Laske skorit
                entry_score = self.screener.calculate_advanced_entry_score(token_data)
                risk_score = self.screener.calculate_advanced_risk_score(token_data)
                momentum_score = self.screener.calculate_momentum_score(token_data)
                overall_score = self.screener.calculate_overall_score(token_data)
                
                event.screening_result = {
                    'entry_score': entry_score,
                    'risk_score': risk_score,
                    'momentum_score': momentum_score,
                    'overall_score': overall_score,
                    'screening_strategy': self._determine_screening_strategy(token_data)
                }
                
                event.entry_score = entry_score
                event.risk_score = risk_score
                event.technical_score = momentum_score
                
        except Exception as e:
            logger.error(f"Virhe token screeningissä: {e}")
    
    async def _perform_risk_assessment(self, event: EnhancedTokenEvent):
        """Suorita risk assessment"""
        try:
            # Luo portfolio-muotoinen data
            portfolio = {
                'total_value': 10000,
                'positions': {
                    event.token_address: {
                        'value': 1000,
                        'returns': [0.01, -0.02, 0.03, -0.01, 0.02],
                        'prices': [100, 98, 101, 100, 102],
                        'volume': event.data.get('volume', 0),
                        'market_cap': event.data.get('market_cap', 0),
                        'volatility': 0.3
                    }
                }
            }
            
            market_data = {
                'market_returns': [0.005, -0.01, 0.02, -0.005, 0.01]
            }
            
            # Laske risk-mittarit
            risk_report = self.risk_assessor.generate_risk_report(portfolio, market_data)
            
            event.risk_assessment = {
                'portfolio_risk': risk_report.get('portfolio_summary', {}),
                'position_risks': risk_report.get('position_risks', {}),
                'stress_tests': risk_report.get('stress_tests', {}),
                'recommendations': risk_report.get('recommendations', [])
            }
            
        except Exception as e:
            logger.error(f"Virhe risk assessmentissa: {e}")
    
    async def _perform_sentiment_analysis(self, event: EnhancedTokenEvent):
        """Suorita sentimentti-analyysi"""
        try:
            # Analysoi event-datan sentimenttiä
            text_data = self._extract_text_from_event(event)
            if text_data:
                sentiment_scores = self.sentiment_analyzer.analyze_text_sentiment(text_data)
                overall_sentiment = self.sentiment_analyzer.calculate_weighted_sentiment(sentiment_scores)
                confidence = self.sentiment_analyzer.calculate_confidence(sentiment_scores)
                
                event.sentiment_analysis = {
                    'overall_sentiment': overall_sentiment,
                    'confidence': confidence,
                    'sentiment_scores': sentiment_scores,
                    'emotion': self.sentiment_analyzer._classify_emotion(overall_sentiment),
                    'keywords': self.sentiment_analyzer._extract_keywords(text_data)
                }
                
                event.sentiment_score = overall_sentiment
                
        except Exception as e:
            logger.error(f"Virhe sentimentti-analyysissä: {e}")
    
    async def _perform_timeframe_analysis(self, event: EnhancedTokenEvent):
        """Suorita timeframe-analyysi"""
        try:
            # Analysoi tokenin hinta-kehitystä
            symbol = f"{event.token_address[:8]}-USD"  # Simuloi symbol
            
            # Käytä timeframe analyzeria
            analysis = await self.timeframe_analyzer.analyze_symbol(symbol)
            if analysis:
                event.timeframe_analysis = {
                    'overall_trend': analysis.overall_trend,
                    'trend_strength': analysis.trend_strength,
                    'trend_confidence': analysis.trend_confidence,
                    'entry_signals': analysis.entry_signals,
                    'exit_signals': analysis.exit_signals,
                    'recommendations': analysis.recommendations
                }
                
        except Exception as e:
            logger.error(f"Virhe timeframe-analyysissä: {e}")
    
    def _convert_event_to_advanced_token(self, event: EnhancedTokenEvent) -> Optional[AdvancedToken]:
        """Muunna event AdvancedToken-objektiksi"""
        try:
            data = event.data
            
            # Poimi data event:sta
            symbol = data.get('symbol', event.token_address[:8].upper())
            name = data.get('name', f"Token_{symbol}")
            price = float(data.get('price', 0.001))
            market_cap = float(data.get('market_cap', 10000))
            volume_24h = float(data.get('volume_24h', 1000))
            
            # Generoi muut tiedot
            price_change_24h = float(data.get('price_change_24h', 0))
            price_change_7d = float(data.get('price_change_7d', 0))
            liquidity = float(data.get('liquidity', 10000))
            holders = int(data.get('holders', 100))
            fresh_holders_1d = int(data.get('fresh_holders_1d', 10))
            fresh_holders_7d = int(data.get('fresh_holders_7d', 50))
            age_minutes = int(data.get('age_minutes', 5))
            
            # Generoi skorit
            social_score = float(data.get('social_score', 0.5))
            technical_score = 0.0
            momentum_score = 0.0
            risk_score = 0.0
            entry_score = 0.0
            overall_score = 0.0
            
            # Generoi uudet kentät
            volume_spike = float(data.get('volume_spike', 100))
            holder_growth = float(data.get('holder_growth', 50))
            liquidity_ratio = liquidity / market_cap if market_cap > 0 else 0.1
            price_volatility = abs(price_change_24h) / 100
            social_mentions = int(data.get('social_mentions', 100))
            influencer_mentions = int(data.get('influencer_mentions', 5))
            community_growth = float(data.get('community_growth', 25))
            development_activity = float(data.get('development_activity', 0.5))
            audit_status = data.get('audit_status', 'unverified')
            rug_pull_risk = float(data.get('rug_pull_risk', 0.3))
            
            return AdvancedToken(
                symbol=symbol,
                name=name,
                address=event.token_address,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_24h=price_change_24h,
                price_change_7d=price_change_7d,
                liquidity=liquidity,
                holders=holders,
                fresh_holders_1d=fresh_holders_1d,
                fresh_holders_7d=fresh_holders_7d,
                age_minutes=age_minutes,
                social_score=social_score,
                technical_score=technical_score,
                momentum_score=momentum_score,
                risk_score=risk_score,
                entry_score=entry_score,
                overall_score=overall_score,
                timestamp=event.timestamp.isoformat(),
                real_price=price,
                real_volume=volume_24h,
                real_liquidity=liquidity,
                dex="PumpPortal",
                pair_address=event.token_address,
                volume_spike=volume_spike,
                holder_growth=holder_growth,
                liquidity_ratio=liquidity_ratio,
                price_volatility=price_volatility,
                social_mentions=social_mentions,
                influencer_mentions=influencer_mentions,
                community_growth=community_growth,
                development_activity=development_activity,
                audit_status=audit_status,
                rug_pull_risk=rug_pull_risk
            )
            
        except Exception as e:
            logger.error(f"Virhe event-muunnoksessa: {e}")
            return None
    
    def _extract_text_from_event(self, event: EnhancedTokenEvent) -> str:
        """Poimi teksti event-datasta"""
        text_parts = []
        
        # Lisää event-tyyppi
        text_parts.append(f"Event type: {event.event_type}")
        
        # Lisää token-tiedot
        data = event.data
        if 'symbol' in data:
            text_parts.append(f"Token: {data['symbol']}")
        if 'name' in data:
            text_parts.append(f"Name: {data['name']}")
        if 'description' in data:
            text_parts.append(f"Description: {data['description']}")
        
        # Lisää kaupankäyntitiedot
        if event.event_type == 'token_trade':
            text_parts.append(f"Trade type: {data.get('trade_type', 'unknown')}")
            text_parts.append(f"Volume: {data.get('volume', 0)}")
            text_parts.append(f"Price: {data.get('price', 0)}")
        
        return " ".join(text_parts)
    
    def _determine_screening_strategy(self, token: AdvancedToken) -> str:
        """Määritä sopiva screening-strategia"""
        if token.age_minutes <= 10 and token.market_cap <= 50000:
            return "ultra_fresh"
        elif token.volume_spike > 300:
            return "volume_spike"
        elif token.social_score > 0.7:
            return "social_buzz"
        elif token.risk_score < 0.3:
            return "low_risk"
        else:
            return "general"
    
    def _calculate_overall_score(self, event: EnhancedTokenEvent) -> float:
        """Laske kokonaisscore"""
        scores = []
        
        if event.screening_result:
            scores.append(event.screening_result.get('overall_score', 0))
        
        if event.sentiment_analysis:
            sentiment = event.sentiment_analysis.get('overall_sentiment', 0)
            scores.append((sentiment + 1) / 2)  # Normalisoi -1,1 -> 0,1
        
        if event.timeframe_analysis:
            trend_strength = event.timeframe_analysis.get('trend_strength', 0)
            scores.append(trend_strength)
        
        if scores:
            return np.mean(scores)
        
        return 0.0
    
    def _is_hot_token(self, event: EnhancedTokenEvent) -> bool:
        """Tarkista onko hot token"""
        # Tarkista volyymi
        volume = event.data.get('volume_24h', 0)
        if volume < self.config['hot_token_threshold']:
            return False
        
        # Tarkista overall score
        if event.overall_score < 0.6:
            return False
        
        # Tarkista risk
        if event.risk_score > self.config['risk_threshold']:
            return False
        
        return True
    
    async def listen(self):
        """Kuuntele WebSocket-viestejä"""
        if not self.is_connected:
            logger.error("Ei yhteyttä WebSocket:iin")
            return
        
        self.running = True
        logger.info("🎧 Aloitetaan WebSocket-viestien kuuntelu...")
        
        try:
            async for message in self.websocket:
                if not self.running:
                    break
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket-yhteys suljettu")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Virhe WebSocket-kuuntelussa: {e}")
        finally:
            self.running = False
    
    def stop(self):
        """Pysäytä kuuntelu"""
        self.running = False
        logger.info("⏹️ WebSocket-kuuntelu pysäytetty")
    
    def update_metrics(self):
        """Päivitä PumpPortal-mittarit"""
        try:
            # Laske perusmittarit
            self.metrics.total_tokens_created = len([
                event for event in self.token_events 
                if event.event_type == 'new_token'
            ])
            
            self.metrics.total_trades_24h = len([
                event for event in self.token_events 
                if event.event_type == 'token_trade' and
                event.timestamp > datetime.now() - timedelta(hours=24)
            ])
            
            # Laske volyymi
            recent_trades = [
                event for event in self.token_events 
                if event.event_type == 'token_trade' and
                event.timestamp > datetime.now() - timedelta(hours=24)
            ]
            
            self.metrics.total_volume_24h = sum(
                event.data.get('volume', 0) for event in recent_trades
            )
            
            # Laske hot tokens
            self.metrics.hot_tokens_count = len(self.hot_tokens)
            
            # Laske keskiarvoinen token-ikä
            token_ages = [
                event.data.get('age_minutes', 0) for event in self.token_events
                if event.event_type == 'new_token'
            ]
            self.metrics.average_token_age = np.mean(token_ages) if token_ages else 0
            
            # Laske market heat
            if self.token_events:
                overall_scores = [event.overall_score for event in self.token_events]
                self.metrics.market_heat = np.mean(overall_scores)
            else:
                self.metrics.market_heat = 0.0
            
            # Laske momentum
            if recent_trades:
                momentum_scores = [
                    event.technical_score for event in recent_trades
                    if event.technical_score > 0
                ]
                self.metrics.momentum_score = np.mean(momentum_scores) if momentum_scores else 0.0
            else:
                self.metrics.momentum_score = 0.0
            
            # Laske risk-jakauma
            risk_levels = {'low': 0, 'medium': 0, 'high': 0}
            for event in self.token_events:
                if event.risk_score < 0.3:
                    risk_levels['low'] += 1
                elif event.risk_score < 0.7:
                    risk_levels['medium'] += 1
                else:
                    risk_levels['high'] += 1
            
            self.metrics.risk_distribution = risk_levels
            
            # Laske top performers
            top_events = sorted(
                self.token_events,
                key=lambda x: x.overall_score,
                reverse=True
            )[:10]
            
            self.metrics.top_performers = [
                {
                    'token_address': event.token_address,
                    'overall_score': event.overall_score,
                    'event_type': event.event_type,
                    'timestamp': event.timestamp.isoformat()
                }
                for event in top_events
            ]
            
        except Exception as e:
            logger.error(f"Virhe mittareiden päivittämisessä: {e}")
    
    def get_enhanced_analysis_report(self) -> Dict:
        """Hae parannettu analyysiraportti"""
        self.update_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": asdict(self.metrics),
            "recent_events": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "event_type": event.event_type,
                    "token_address": event.token_address,
                    "overall_score": event.overall_score,
                    "screening_result": event.screening_result,
                    "risk_assessment": event.risk_assessment,
                    "sentiment_analysis": event.sentiment_analysis,
                    "timeframe_analysis": event.timeframe_analysis
                }
                for event in self.token_events[-20:]  # Viimeiset 20 eventiä
            ],
            "hot_tokens": [
                {
                    "token_address": event.token_address,
                    "overall_score": event.overall_score,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data
                }
                for event in self.hot_tokens[-10:]  # Viimeiset 10 hot tokenia
            ],
            "analysis_summary": {
                "total_events_analyzed": len(self.token_events),
                "hot_tokens_found": len(self.hot_tokens),
                "average_overall_score": np.mean([event.overall_score for event in self.token_events]) if self.token_events else 0,
                "enhanced_tools_available": ADVANCED_TOOLS_AVAILABLE
            }
        }

# Esimerkki käytöstä
async def example_usage():
    """Esimerkki enhanced PumpPortal-integraation käytöstä"""
    client = EnhancedPumpPortalClient()
    
    # Alusta edistyneet työkalut
    await client.initialize_enhanced_tools()
    
    # Lisää callbackit
    async def on_hot_token(event):
        print(f"🔥 Hot token löytyi: {event.token_address[:8]}... (score: {event.overall_score:.3f})")
    
    async def on_token_creation(event):
        print(f"🆕 Uusi token: {event.token_address[:8]}...")
    
    client.add_callback('on_hot_token', on_hot_token)
    client.add_callback('on_token_creation', on_token_creation)
    
    # Yhdistä ja tilaa tapahtumat
    if await client.connect():
        await client.subscribe_all_events()
        
        # Kuuntele 60 sekuntia
        try:
            await asyncio.wait_for(client.listen(), timeout=60.0)
        except asyncio.TimeoutError:
            print("⏰ 60 sekuntia kulunut")
        finally:
            client.stop()
            await client.disconnect()
        
        # Hae analyysiraportti
        report = client.get_enhanced_analysis_report()
        print(f"Enhanced analyysiraportti: {json.dumps(report, indent=2, default=str)}")

if __name__ == "__main__":
    asyncio.run(example_usage())
