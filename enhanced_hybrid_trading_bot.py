"""
Enhanced Hybrid Trading Bot - Parannettu hybrid trading bot
Yhdistää kaikki edistyneet analyysityökalut parhaan tuloksen saamiseksi
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Tuple
import os
from dotenv import load_dotenv

# Import our enhanced tools
try:
    from advanced_token_screener import AdvancedTokenScreener, AdvancedToken
    from advanced_risk_assessment import AdvancedRiskAssessment
    from ai_sentiment_analysis import AISentimentAnalyzer
    from multi_timeframe_analysis import MultiTimeframeAnalyzer
    from enhanced_pumpportal_integration import EnhancedPumpPortalClient
    from social_media_monitor import SocialMediaMonitor
    ENHANCED_TOOLS_AVAILABLE = True
except ImportError:
    ENHANCED_TOOLS_AVAILABLE = False

# Load environment
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EnhancedTradingDecision:
    """Parannettu kauppapäätös"""
    token_address: str
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    confidence: float
    position_size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    reasoning: List[str]
    risk_score: float
    sentiment_score: float
    technical_score: float
    overall_score: float
    timestamp: datetime
    # Enhanced analysis
    screening_analysis: Dict[str, Any] = None
    risk_assessment: Dict[str, Any] = None
    sentiment_analysis: Dict[str, Any] = None
    timeframe_analysis: Dict[str, Any] = None
    social_media_analysis: Dict[str, Any] = None

@dataclass
class EnhancedPortfolio:
    """Parannettu portfolio"""
    total_value: float
    cash: float
    positions: Dict[str, Dict[str, Any]]
    risk_metrics: Dict[str, float]
    performance_metrics: Dict[str, float]
    recommendations: List[str]
    last_updated: datetime

class EnhancedHybridTradingBot:
    """Parannettu hybrid trading bot"""
    
    def __init__(self):
        self.running = False
        
        # Enhanced tools
        self.screener = None
        self.risk_assessor = None
        self.sentiment_analyzer = None
        self.timeframe_analyzer = None
        self.pump_portal_client = None
        self.social_media_monitor = None
        
        # Portfolio
        self.portfolio = EnhancedPortfolio(
            total_value=10000.0,
            cash=10000.0,
            positions={},
            risk_metrics={},
            performance_metrics={},
            recommendations=[],
            last_updated=datetime.now()
        )
        
        # Configuration
        self.config = {
            'max_positions': 10,
            'max_position_size': 0.1,  # 10% of portfolio
            'min_confidence': 0.6,
            'risk_tolerance': 0.3,
            'rebalance_interval': 3600,  # 1 hour
            'analysis_interval': 300,  # 5 minutes
            'stop_loss_percentage': 0.05,  # 5%
            'take_profit_percentage': 0.15,  # 15%
            'max_daily_trades': 20
        }
        
        # Tracking
        self.daily_trades = 0
        self.last_rebalance = datetime.now()
        self.trading_decisions = []
        self.performance_history = []
        
        # Initialize enhanced tools
        self._initialize_enhanced_tools()
    
    def _initialize_enhanced_tools(self):
        """Alusta edistyneet työkalut"""
        if not ENHANCED_TOOLS_AVAILABLE:
            logger.warning("⚠️ Edistyneet työkalut eivät ole saatavilla")
            return False
        
        try:
            # Alusta työkalut
            self.screener = AdvancedTokenScreener()
            self.risk_assessor = AdvancedRiskAssessment()
            self.sentiment_analyzer = AISentimentAnalyzer()
            self.timeframe_analyzer = MultiTimeframeAnalyzer()
            self.pump_portal_client = EnhancedPumpPortalClient()
            self.social_media_monitor = SocialMediaMonitor()
            
            logger.info("✅ Edistyneet työkalut alustettu")
            return True
        except Exception as e:
            logger.error(f"❌ Virhe edistyneiden työkalujen alustuksessa: {e}")
            return False
    
    async def start(self):
        """Käynnistä bot"""
        if not ENHANCED_TOOLS_AVAILABLE:
            logger.error("❌ Edistyneet työkalut eivät ole saatavilla")
            return
        
        self.running = True
        logger.info("🚀 Käynnistetään Enhanced Hybrid Trading Bot...")
        
        # Alusta edistyneet työkalut
        await self._initialize_enhanced_tools_async()
        
        # Aloita seuranta
        tasks = [
            self._monitor_tokens(),
            self._analyze_portfolio(),
            self._execute_trades(),
            self._update_performance()
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Virhe botin suorituksessa: {e}")
        finally:
            self.running = False
    
    def stop(self):
        """Pysäytä bot"""
        self.running = False
        logger.info("⏹️ Enhanced Hybrid Trading Bot pysäytetty")
    
    async def _initialize_enhanced_tools_async(self):
        """Alusta edistyneet työkalut asynkronisesti"""
        try:
            # Alusta PumpPortal client
            if self.pump_portal_client:
                await self.pump_portal_client.initialize_enhanced_tools()
                await self.pump_portal_client.connect()
                await self.pump_portal_client.subscribe_all_events()
            
            # Alusta social media monitor
            if self.social_media_monitor:
                # Lisää seurattavia kohteita
                self.social_media_monitor.add_tracking(
                    symbols=["BTC", "ETH", "SOL", "DOGE", "SHIB"],
                    hashtags=["#crypto", "#bitcoin", "#ethereum", "#solana"],
                    keywords=["moon", "pump", "bullish", "bearish", "hodl"]
                )
            
            logger.info("✅ Edistyneet työkalut alustettu asynkronisesti")
        except Exception as e:
            logger.error(f"❌ Virhe edistyneiden työkalujen asynkronisessa alustuksessa: {e}")
    
    async def _monitor_tokens(self):
        """Seuraa tokeneita"""
        logger.info("👁️ Aloitetaan token-seuranta...")
        
        while self.running:
            try:
                # Hae uudet tokenit PumpPortal:sta
                if self.pump_portal_client:
                    await self._process_pump_portal_events()
                
                # Hae sosiaalisen median data
                if self.social_media_monitor:
                    await self._process_social_media_data()
                
                await asyncio.sleep(self.config['analysis_interval'])
            except Exception as e:
                logger.error(f"Virhe token-seurannassa: {e}")
                await asyncio.sleep(60)
    
    async def _process_pump_portal_events(self):
        """Käsittele PumpPortal-tapahtumat"""
        try:
            # Hae viimeisimmät eventit
            recent_events = self.pump_portal_client.token_events[-10:] if self.pump_portal_client.token_events else []
            
            for event in recent_events:
                # Analysoi event
                await self._analyze_token_event(event)
        
        except Exception as e:
            logger.error(f"Virhe PumpPortal-tapahtumien käsittelyssä: {e}")
    
    async def _process_social_media_data(self):
        """Käsittele sosiaalisen median data"""
        try:
            # Hae viimeisimmät postit
            recent_posts = self.social_media_monitor.posts[-20:] if self.social_media_monitor.posts else []
            
            for post in recent_posts:
                # Analysoi posti
                await self._analyze_social_media_post(post)
        
        except Exception as e:
            logger.error(f"Virhe sosiaalisen median datan käsittelyssä: {e}")
    
    async def _analyze_token_event(self, event):
        """Analysoi token event"""
        try:
            # Tarkista onko event analysoitu jo
            if hasattr(event, 'analyzed') and event.analyzed:
                return
            
            # Suorita kattava analyysi
            analysis = await self._perform_comprehensive_analysis(event)
            
            if analysis:
                # Tee kauppapäätös
                decision = await self._make_trading_decision(analysis)
                
                if decision:
                    self.trading_decisions.append(decision)
                    logger.info(f"📊 Kauppapäätös: {decision.action} {decision.symbol} (confidence: {decision.confidence:.3f})")
            
            # Merkitse analysoiduksi
            event.analyzed = True
        
        except Exception as e:
            logger.error(f"Virhe token eventin analyysissä: {e}")
    
    async def _analyze_social_media_post(self, post):
        """Analysoi sosiaalisen median posti"""
        try:
            # Tarkista onko posti analysoitu jo
            if hasattr(post, 'analyzed') and post.analyzed:
                return
            
            # Analysoi sentimentti
            if self.sentiment_analyzer:
                sentiment_scores = self.sentiment_analyzer.analyze_text_sentiment(post.content)
                post.sentiment_score = self.sentiment_analyzer.calculate_weighted_sentiment(sentiment_scores)
                post.confidence = self.sentiment_analyzer.calculate_confidence(sentiment_scores)
                post.emotion = self.sentiment_analyzer._classify_emotion(post.sentiment_score)
                post.keywords = self.sentiment_analyzer._extract_keywords(post.content)
            
            # Merkitse analysoiduksi
            post.analyzed = True
        
        except Exception as e:
            logger.error(f"Virhe sosiaalisen median postin analyysissä: {e}")
    
    async def _perform_comprehensive_analysis(self, event) -> Optional[Dict]:
        """Suorita kattava analyysi"""
        try:
            analysis = {
                'event': event,
                'screening_analysis': None,
                'risk_assessment': None,
                'sentiment_analysis': None,
                'timeframe_analysis': None,
                'social_media_analysis': None,
                'overall_score': 0.0,
                'confidence': 0.0
            }
            
            # Token screening
            if self.screener and event.screening_result:
                analysis['screening_analysis'] = event.screening_result
            
            # Risk assessment
            if self.risk_assessor and event.risk_assessment:
                analysis['risk_assessment'] = event.risk_assessment
            
            # Sentiment analysis
            if self.sentiment_analyzer and event.sentiment_analysis:
                analysis['sentiment_analysis'] = event.sentiment_analysis
            
            # Timeframe analysis
            if self.timeframe_analyzer and event.timeframe_analysis:
                analysis['timeframe_analysis'] = event.timeframe_analysis
            
            # Social media analysis
            if self.social_media_monitor:
                analysis['social_media_analysis'] = self._get_social_media_analysis_for_token(event.token_address)
            
            # Laske overall score
            analysis['overall_score'] = self._calculate_comprehensive_score(analysis)
            analysis['confidence'] = self._calculate_comprehensive_confidence(analysis)
            
            return analysis
        
        except Exception as e:
            logger.error(f"Virhe kattavassa analyysissä: {e}")
            return None
    
    def _get_social_media_analysis_for_token(self, token_address: str) -> Dict:
        """Hae sosiaalisen median analyysi tokenille"""
        try:
            # Hae postit jotka mainitsevat tokenin
            relevant_posts = [
                post for post in self.social_media_monitor.posts
                if token_address[:8].upper() in post.content.upper() or
                   any(keyword in post.content.lower() for keyword in ['crypto', 'token', 'coin'])
            ]
            
            if not relevant_posts:
                return {'error': 'Ei relevantteja posteja'}
            
            # Laske sentimentti-mittarit
            sentiment_scores = [post.sentiment_score for post in relevant_posts]
            avg_sentiment = np.mean(sentiment_scores)
            sentiment_std = np.std(sentiment_scores)
            
            # Laske engagement
            total_engagement = sum(post.engagement for post in relevant_posts)
            avg_engagement = total_engagement / len(relevant_posts)
            
            # Laske emotion-jakauma
            emotion_counts = {}
            for post in relevant_posts:
                emotion = post.emotion
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            return {
                'total_posts': len(relevant_posts),
                'average_sentiment': avg_sentiment,
                'sentiment_volatility': sentiment_std,
                'total_engagement': total_engagement,
                'average_engagement': avg_engagement,
                'emotion_distribution': emotion_counts,
                'recent_posts': [
                    {
                        'platform': post.platform,
                        'sentiment_score': post.sentiment_score,
                        'engagement': post.engagement,
                        'timestamp': post.timestamp.isoformat()
                    }
                    for post in relevant_posts[-5:]  # Viimeiset 5 postia
                ]
            }
        
        except Exception as e:
            logger.error(f"Virhe sosiaalisen median analyysissä: {e}")
            return {'error': str(e)}
    
    def _calculate_comprehensive_score(self, analysis: Dict) -> float:
        """Laske kattava score"""
        scores = []
        
        # Screening score
        if analysis['screening_analysis']:
            scores.append(analysis['screening_analysis'].get('overall_score', 0))
        
        # Sentiment score
        if analysis['sentiment_analysis']:
            sentiment = analysis['sentiment_analysis'].get('overall_sentiment', 0)
            scores.append((sentiment + 1) / 2)  # Normalisoi -1,1 -> 0,1
        
        # Timeframe score
        if analysis['timeframe_analysis']:
            trend_strength = analysis['timeframe_analysis'].get('trend_strength', 0)
            scores.append(trend_strength)
        
        # Social media score
        if analysis['social_media_analysis'] and 'average_sentiment' in analysis['social_media_analysis']:
            social_sentiment = analysis['social_media_analysis']['average_sentiment']
            scores.append((social_sentiment + 1) / 2)  # Normalisoi -1,1 -> 0,1
        
        if scores:
            return np.mean(scores)
        
        return 0.0
    
    def _calculate_comprehensive_confidence(self, analysis: Dict) -> float:
        """Laske kattava luottamus"""
        confidences = []
        
        # Screening confidence
        if analysis['screening_analysis']:
            confidences.append(0.8)  # Oletusluottamus
        
        # Sentiment confidence
        if analysis['sentiment_analysis']:
            confidences.append(analysis['sentiment_analysis'].get('confidence', 0.5))
        
        # Timeframe confidence
        if analysis['timeframe_analysis']:
            confidences.append(analysis['timeframe_analysis'].get('trend_confidence', 0.5))
        
        # Social media confidence
        if analysis['social_media_analysis'] and 'total_posts' in analysis['social_media_analysis']:
            posts_count = analysis['social_media_analysis']['total_posts']
            # Enemmän posteja = korkeampi luottamus
            social_confidence = min(posts_count / 10, 1.0)
            confidences.append(social_confidence)
        
        if confidences:
            return np.mean(confidences)
        
        return 0.0
    
    async def _make_trading_decision(self, analysis: Dict) -> Optional[EnhancedTradingDecision]:
        """Tee kauppapäätös"""
        try:
            event = analysis['event']
            overall_score = analysis['overall_score']
            confidence = analysis['confidence']
            
            # Tarkista luottamus
            if confidence < self.config['min_confidence']:
                return None
            
            # Tarkista risk
            risk_score = event.risk_score if hasattr(event, 'risk_score') else 0.5
            if risk_score > self.config['risk_tolerance']:
                return None
            
            # Tarkista päivittäiset kaupat
            if self.daily_trades >= self.config['max_daily_trades']:
                return None
            
            # Määritä toiminto
            action = self._determine_action(overall_score, confidence, risk_score)
            
            if action == 'hold':
                return None
            
            # Laske position koko
            position_size = self._calculate_position_size(overall_score, confidence, risk_score)
            
            # Laske hinnat
            entry_price = event.data.get('price', 0.001)
            stop_loss = entry_price * (1 - self.config['stop_loss_percentage'])
            take_profit = entry_price * (1 + self.config['take_profit_percentage'])
            
            # Generoi perustelut
            reasoning = self._generate_reasoning(analysis, action)
            
            # Luo kauppapäätös
            decision = EnhancedTradingDecision(
                token_address=event.token_address,
                symbol=event.data.get('symbol', event.token_address[:8].upper()),
                action=action,
                confidence=confidence,
                position_size=position_size,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasoning=reasoning,
                risk_score=risk_score,
                sentiment_score=event.sentiment_score if hasattr(event, 'sentiment_score') else 0,
                technical_score=event.technical_score if hasattr(event, 'technical_score') else 0,
                overall_score=overall_score,
                timestamp=datetime.now(),
                screening_analysis=analysis['screening_analysis'],
                risk_assessment=analysis['risk_assessment'],
                sentiment_analysis=analysis['sentiment_analysis'],
                timeframe_analysis=analysis['timeframe_analysis'],
                social_media_analysis=analysis['social_media_analysis']
            )
            
            return decision
        
        except Exception as e:
            logger.error(f"Virhe kauppapäätöksen tekemisessä: {e}")
            return None
    
    def _determine_action(self, overall_score: float, confidence: float, risk_score: float) -> str:
        """Määritä toiminto"""
        # Yhdistä skorit
        combined_score = (overall_score * 0.4 + confidence * 0.3 + (1 - risk_score) * 0.3)
        
        if combined_score > 0.7:
            return 'buy'
        elif combined_score < 0.3:
            return 'sell'
        else:
            return 'hold'
    
    def _calculate_position_size(self, overall_score: float, confidence: float, risk_score: float) -> float:
        """Laske position koko"""
        # Base position size
        base_size = self.config['max_position_size']
        
        # Adjust by score
        score_adjustment = overall_score
        base_size *= score_adjustment
        
        # Adjust by confidence
        confidence_adjustment = confidence
        base_size *= confidence_adjustment
        
        # Adjust by risk
        risk_adjustment = 1 - risk_score
        base_size *= risk_adjustment
        
        # Adjust by portfolio heat
        portfolio_heat = self._calculate_portfolio_heat()
        heat_adjustment = 1 - portfolio_heat
        base_size *= heat_adjustment
        
        return max(0.01, min(base_size, self.config['max_position_size']))
    
    def _calculate_portfolio_heat(self) -> float:
        """Laske portfolio heat"""
        if not self.portfolio.positions:
            return 0.0
        
        total_risk = 0.0
        for position in self.portfolio.positions.values():
            risk = position.get('risk_score', 0.5)
            weight = position.get('weight', 0.1)
            total_risk += risk * weight
        
        return min(total_risk, 1.0)
    
    def _generate_reasoning(self, analysis: Dict, action: str) -> List[str]:
        """Generoi perustelut"""
        reasoning = []
        
        # Overall score
        overall_score = analysis['overall_score']
        if overall_score > 0.7:
            reasoning.append(f"Korkea overall score: {overall_score:.3f}")
        elif overall_score < 0.3:
            reasoning.append(f"Matala overall score: {overall_score:.3f}")
        
        # Confidence
        confidence = analysis['confidence']
        if confidence > 0.8:
            reasoning.append(f"Korkea luottamus: {confidence:.3f}")
        
        # Risk
        if analysis['risk_assessment']:
            reasoning.append("Risk assessment suoritettu")
        
        # Sentiment
        if analysis['sentiment_analysis']:
            sentiment = analysis['sentiment_analysis'].get('overall_sentiment', 0)
            if sentiment > 0.3:
                reasoning.append(f"Positiivinen sentimentti: {sentiment:.3f}")
            elif sentiment < -0.3:
                reasoning.append(f"Negatiivinen sentimentti: {sentiment:.3f}")
        
        # Timeframe
        if analysis['timeframe_analysis']:
            trend = analysis['timeframe_analysis'].get('overall_trend', 'neutral')
            reasoning.append(f"Trend: {trend}")
        
        # Social media
        if analysis['social_media_analysis'] and 'total_posts' in analysis['social_media_analysis']:
            posts_count = analysis['social_media_analysis']['total_posts']
            reasoning.append(f"Sosiaalinen media: {posts_count} postia")
        
        return reasoning
    
    async def _analyze_portfolio(self):
        """Analysoi portfolio"""
        logger.info("📊 Aloitetaan portfolio-analyysi...")
        
        while self.running:
            try:
                # Laske risk-mittarit
                await self._calculate_portfolio_risks()
                
                # Laske performance-mittarit
                await self._calculate_portfolio_performance()
                
                # Generoi suositukset
                await self._generate_portfolio_recommendations()
                
                # Päivitä portfolio
                self.portfolio.last_updated = datetime.now()
                
                await asyncio.sleep(self.config['rebalance_interval'])
            except Exception as e:
                logger.error(f"Virhe portfolio-analyysissä: {e}")
                await asyncio.sleep(300)
    
    async def _calculate_portfolio_risks(self):
        """Laske portfolio-riskit"""
        try:
            if not self.portfolio.positions:
                self.portfolio.risk_metrics = {
                    'total_risk': 0.0,
                    'concentration_risk': 0.0,
                    'volatility_risk': 0.0,
                    'liquidity_risk': 0.0
                }
                return
            
            # Laske perusriskit
            total_risk = 0.0
            position_risks = []
            
            for symbol, position in self.portfolio.positions.items():
                risk = position.get('risk_score', 0.5)
                weight = position.get('weight', 0.1)
                position_risk = risk * weight
                total_risk += position_risk
                position_risks.append(position_risk)
            
            # Laske konsentraatioriski
            position_sizes = [position.get('weight', 0.1) for position in self.portfolio.positions.values()]
            concentration_risk = self._calculate_concentration_risk(position_sizes)
            
            # Laske volatiliteettiriski
            volatility_risk = np.mean([position.get('volatility', 0.3) for position in self.portfolio.positions.values()])
            
            # Laske likviditeettiriski
            liquidity_risk = np.mean([position.get('liquidity_risk', 0.3) for position in self.portfolio.positions.values()])
            
            self.portfolio.risk_metrics = {
                'total_risk': total_risk,
                'concentration_risk': concentration_risk,
                'volatility_risk': volatility_risk,
                'liquidity_risk': liquidity_risk
            }
        
        except Exception as e:
            logger.error(f"Virhe portfolio-riskkien laskennassa: {e}")
    
    def _calculate_concentration_risk(self, position_sizes: List[float]) -> float:
        """Laske konsentraatioriski"""
        if not position_sizes:
            return 0.0
        
        total_value = sum(position_sizes)
        if total_value == 0:
            return 0.0
        
        # Laske HHI
        normalized_sizes = [size / total_value for size in position_sizes]
        hhi = sum(size ** 2 for size in normalized_sizes)
        
        return min(hhi, 1.0)
    
    async def _calculate_portfolio_performance(self):
        """Laske portfolio-performance"""
        try:
            # Laske perusmittarit
            total_value = self.portfolio.total_value
            cash = self.portfolio.cash
            positions_value = sum(position.get('value', 0) for position in self.portfolio.positions.values())
            
            # Laske tuotto
            initial_value = 10000.0  # Oletus
            total_return = (total_value - initial_value) / initial_value
            
            # Laske Sharpe ratio (yksinkertaistettu)
            returns = [position.get('return', 0) for position in self.portfolio.positions.values()]
            if returns:
                avg_return = np.mean(returns)
                return_std = np.std(returns)
                sharpe_ratio = avg_return / return_std if return_std > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Laske max drawdown
            max_drawdown = self._calculate_max_drawdown()
            
            self.portfolio.performance_metrics = {
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'positions_value': positions_value,
                'cash_ratio': cash / total_value if total_value > 0 else 1.0
            }
        
        except Exception as e:
            logger.error(f"Virhe portfolio-performance laskennassa: {e}")
    
    def _calculate_max_drawdown(self) -> float:
        """Laske max drawdown"""
        if not self.performance_history:
            return 0.0
        
        values = [entry['total_value'] for entry in self.performance_history]
        peak = np.maximum.accumulate(values)
        drawdown = (values - peak) / peak
        max_drawdown = abs(np.min(drawdown))
        
        return max_drawdown
    
    async def _generate_portfolio_recommendations(self):
        """Generoi portfolio-suositukset"""
        try:
            recommendations = []
            
            # Risk-suositukset
            total_risk = self.portfolio.risk_metrics.get('total_risk', 0)
            if total_risk > 0.7:
                recommendations.append("Korkea portfolio-riski - vähennä position kokoja")
            elif total_risk < 0.3:
                recommendations.append("Matala portfolio-riski - voit lisätä position kokoja")
            
            # Konsentraatio-suositukset
            concentration_risk = self.portfolio.risk_metrics.get('concentration_risk', 0)
            if concentration_risk > 0.5:
                recommendations.append("Korkea konsentraatioriski - hajauta sijoituksia")
            
            # Performance-suositukset
            total_return = self.portfolio.performance_metrics.get('total_return', 0)
            if total_return < -0.1:
                recommendations.append("Negatiivinen tuotto - harkitse strategian muuttamista")
            elif total_return > 0.2:
                recommendations.append("Hyvä tuotto - jatka nykyistä strategiaa")
            
            # Position-suositukset
            if len(self.portfolio.positions) >= self.config['max_positions']:
                recommendations.append("Maksimi position-määrä saavutettu")
            
            self.portfolio.recommendations = recommendations
        
        except Exception as e:
            logger.error(f"Virhe portfolio-suositusten generoinnissa: {e}")
    
    async def _execute_trades(self):
        """Suorita kaupat"""
        logger.info("💰 Aloitetaan kauppojen suoritus...")
        
        while self.running:
            try:
                # Käsittele kauppapäätökset
                pending_decisions = [d for d in self.trading_decisions if not d.executed]
                
                for decision in pending_decisions:
                    await self._execute_trading_decision(decision)
                
                await asyncio.sleep(60)  # 1 minuutti
            except Exception as e:
                logger.error(f"Virhe kauppojen suorituksessa: {e}")
                await asyncio.sleep(60)
    
    async def _execute_trading_decision(self, decision: EnhancedTradingDecision):
        """Suorita kauppapäätös"""
        try:
            # Tarkista onko jo suoritettu
            if hasattr(decision, 'executed') and decision.executed:
                return
            
            # Simuloi kauppa
            if decision.action == 'buy':
                await self._execute_buy_order(decision)
            elif decision.action == 'sell':
                await self._execute_sell_order(decision)
            
            # Merkitse suoritetuksi
            decision.executed = True
            self.daily_trades += 1
            
            logger.info(f"✅ Kauppa suoritettu: {decision.action} {decision.symbol} ({decision.position_size:.3f})")
        
        except Exception as e:
            logger.error(f"Virhe kauppapäätöksen suorituksessa: {e}")
    
    async def _execute_buy_order(self, decision: EnhancedTradingDecision):
        """Suorita ostokauppa"""
        try:
            # Tarkista rahat
            required_cash = decision.position_size * self.portfolio.total_value
            if required_cash > self.portfolio.cash:
                logger.warning(f"Ei tarpeeksi rahaa ostokauppaan: {decision.symbol}")
                return
            
            # Vähennä käteistä
            self.portfolio.cash -= required_cash
            
            # Lisää position
            self.portfolio.positions[decision.symbol] = {
                'shares': decision.position_size,
                'entry_price': decision.entry_price,
                'current_price': decision.entry_price,
                'value': required_cash,
                'weight': decision.position_size,
                'stop_loss': decision.stop_loss,
                'take_profit': decision.take_profit,
                'risk_score': decision.risk_score,
                'sentiment_score': decision.sentiment_score,
                'technical_score': decision.technical_score,
                'overall_score': decision.overall_score,
                'entry_time': decision.timestamp,
                'return': 0.0,
                'volatility': 0.3,
                'liquidity_risk': 0.3
            }
            
            # Päivitä portfolio arvo
            self.portfolio.total_value = self.portfolio.cash + sum(
                position.get('value', 0) for position in self.portfolio.positions.values()
            )
        
        except Exception as e:
            logger.error(f"Virhe ostokauppaan suorituksessa: {e}")
    
    async def _execute_sell_order(self, decision: EnhancedTradingDecision):
        """Suorita myyntikauppa"""
        try:
            # Tarkista onko position
            if decision.symbol not in self.portfolio.positions:
                logger.warning(f"Ei positionia myytäväksi: {decision.symbol}")
                return
            
            position = self.portfolio.positions[decision.symbol]
            
            # Laske myyntiarvo
            sell_value = position.get('value', 0)
            
            # Lisää käteistä
            self.portfolio.cash += sell_value
            
            # Poista position
            del self.portfolio.positions[decision.symbol]
            
            # Päivitä portfolio arvo
            self.portfolio.total_value = self.portfolio.cash + sum(
                position.get('value', 0) for position in self.portfolio.positions.values()
            )
        
        except Exception as e:
            logger.error(f"Virhe myyntikauppaan suorituksessa: {e}")
    
    async def _update_performance(self):
        """Päivitä performance"""
        logger.info("📈 Aloitetaan performance-päivitys...")
        
        while self.running:
            try:
                # Päivitä position-arvot
                await self._update_position_values()
                
                # Lisää performance-historiaan
                self.performance_history.append({
                    'timestamp': datetime.now(),
                    'total_value': self.portfolio.total_value,
                    'cash': self.portfolio.cash,
                    'positions_count': len(self.portfolio.positions),
                    'daily_trades': self.daily_trades
                })
                
                # Rajoita historia
                if len(self.performance_history) > 1000:
                    self.performance_history = self.performance_history[-1000:]
                
                # Nollaa päivittäiset kaupat
                if datetime.now().date() != self.last_rebalance.date():
                    self.daily_trades = 0
                    self.last_rebalance = datetime.now()
                
                await asyncio.sleep(3600)  # 1 tunti
            except Exception as e:
                logger.error(f"Virhe performance-päivityksessä: {e}")
                await asyncio.sleep(300)
    
    async def _update_position_values(self):
        """Päivitä position-arvot"""
        try:
            for symbol, position in self.portfolio.positions.items():
                # Simuloi hinnanmuutos
                current_price = position.get('current_price', 0)
                volatility = position.get('volatility', 0.3)
                
                # Generoi uusi hinta
                price_change = np.random.normal(0, volatility * 0.01)
                new_price = current_price * (1 + price_change)
                
                # Päivitä position
                position['current_price'] = new_price
                position['value'] = position.get('shares', 0) * new_price
                position['return'] = (new_price - position.get('entry_price', 0)) / position.get('entry_price', 1)
                
                # Päivitä weight
                position['weight'] = position['value'] / self.portfolio.total_value if self.portfolio.total_value > 0 else 0
            
            # Päivitä portfolio arvo
            self.portfolio.total_value = self.portfolio.cash + sum(
                position.get('value', 0) for position in self.portfolio.positions.values()
            )
        
        except Exception as e:
            logger.error(f"Virhe position-arvojen päivityksessä: {e}")
    
    def get_comprehensive_report(self) -> Dict:
        """Hae kattava raportti"""
        return {
            "timestamp": datetime.now().isoformat(),
            "bot_status": {
                "running": self.running,
                "enhanced_tools_available": ENHANCED_TOOLS_AVAILABLE,
                "daily_trades": self.daily_trades,
                "max_daily_trades": self.config['max_daily_trades']
            },
            "portfolio": asdict(self.portfolio),
            "recent_decisions": [
                {
                    "symbol": decision.symbol,
                    "action": decision.action,
                    "confidence": decision.confidence,
                    "position_size": decision.position_size,
                    "overall_score": decision.overall_score,
                    "reasoning": decision.reasoning,
                    "timestamp": decision.timestamp.isoformat()
                }
                for decision in self.trading_decisions[-10:]  # Viimeiset 10 päätöstä
            ],
            "performance_summary": {
                "total_return": self.portfolio.performance_metrics.get('total_return', 0),
                "sharpe_ratio": self.portfolio.performance_metrics.get('sharpe_ratio', 0),
                "max_drawdown": self.portfolio.performance_metrics.get('max_drawdown', 0),
                "total_positions": len(self.portfolio.positions),
                "cash_ratio": self.portfolio.performance_metrics.get('cash_ratio', 1.0)
            },
            "risk_summary": {
                "total_risk": self.portfolio.risk_metrics.get('total_risk', 0),
                "concentration_risk": self.portfolio.risk_metrics.get('concentration_risk', 0),
                "volatility_risk": self.portfolio.risk_metrics.get('volatility_risk', 0),
                "liquidity_risk": self.portfolio.risk_metrics.get('liquidity_risk', 0)
            },
            "enhanced_analysis": {
                "pump_portal_events": len(self.pump_portal_client.token_events) if self.pump_portal_client else 0,
                "social_media_posts": len(self.social_media_monitor.posts) if self.social_media_monitor else 0,
                "hot_tokens_found": len(self.pump_portal_client.hot_tokens) if self.pump_portal_client else 0
            }
        }

# Esimerkki käytöstä
async def example_usage():
    """Esimerkki Enhanced Hybrid Trading Botin käytöstä"""
    bot = EnhancedHybridTradingBot()
    
    try:
        # Käynnistä bot 60 sekunniksi
        await asyncio.wait_for(bot.start(), timeout=60.0)
    except asyncio.TimeoutError:
        print("⏰ 60 sekuntia kulunut")
    finally:
        bot.stop()
        
        # Hae kattava raportti
        report = bot.get_comprehensive_report()
        print(f"Kattava raportti: {json.dumps(report, indent=2, default=str)}")

if __name__ == "__main__":
    asyncio.run(example_usage())
