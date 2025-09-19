"""
AI-Pohjainen Sentimentti-Analyysi - Edistyneet sentimentti-analyysityökalut
Yhdistää useita sentimentti-analyysimenetelmiä parhaan tuloksen saamiseksi
"""

import asyncio
import aiohttp
import json
import logging
import re
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Tuple
import requests
from collections import Counter
import os
from dotenv import load_dotenv

# Sentiment analysis libraries
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# Load environment
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SentimentData:
    """Sentimentti-data"""
    text: str
    timestamp: datetime
    source: str
    author: str
    engagement: int
    sentiment_score: float
    confidence: float
    emotion: str
    keywords: List[str]
    language: str

@dataclass
class SentimentAnalysis:
    """Sentimentti-analyysin tulos"""
    overall_sentiment: float  # -1 to 1
    confidence: float  # 0 to 1
    emotion_distribution: Dict[str, float]
    keyword_sentiment: Dict[str, float]
    source_sentiment: Dict[str, float]
    temporal_sentiment: List[Tuple[datetime, float]]
    volume_weighted_sentiment: float
    influencer_sentiment: float
    community_sentiment: float
    news_sentiment: float
    social_sentiment: float
    technical_sentiment: float
    risk_sentiment: float

class AISentimentAnalyzer:
    """AI-pohjainen sentimentti-analyysi"""
    
    def __init__(self):
        self.session = None
        self.sentiment_models = self._initialize_models()
        self.crypto_keywords = self._initialize_crypto_keywords()
        self.emotion_keywords = self._initialize_emotion_keywords()
        self.risk_keywords = self._initialize_risk_keywords()
        
        # API keys
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
        self.reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        
    def _initialize_models(self) -> Dict:
        """Alusta sentimentti-mallit"""
        models = {}
        
        if TEXTBLOB_AVAILABLE:
            models['textblob'] = True
            logger.info("✅ TextBlob saatavilla")
        else:
            models['textblob'] = False
            logger.warning("⚠️ TextBlob ei ole saatavilla")
        
        if NLTK_AVAILABLE:
            try:
                # Lataa tarvittavat NLTK data
                nltk.download('vader_lexicon', quiet=True)
                models['vader'] = SentimentIntensityAnalyzer()
                logger.info("✅ NLTK VADER saatavilla")
            except Exception as e:
                models['vader'] = False
                logger.warning(f"⚠️ NLTK VADER ei ole saatavilla: {e}")
        else:
            models['vader'] = False
            logger.warning("⚠️ NLTK ei ole saatavilla")
        
        return models
    
    def _initialize_crypto_keywords(self) -> Dict[str, float]:
        """Alusta kryptovaluutta-avainsanat sentimentti-painotuksilla"""
        return {
            # Positiiviset
            "moon": 0.8, "bullish": 0.9, "pump": 0.7, "hodl": 0.6, "diamond hands": 0.8,
            "breakout": 0.7, "rally": 0.8, "surge": 0.7, "rocket": 0.8, "gem": 0.6,
            "adoption": 0.7, "partnership": 0.6, "upgrade": 0.5, "innovation": 0.6,
            "deflationary": 0.5, "scarcity": 0.4, "utility": 0.5, "ecosystem": 0.4,
            
            # Negatiiviset
            "dump": -0.8, "bearish": -0.9, "crash": -0.9, "rug pull": -1.0, "scam": -1.0,
            "fud": -0.7, "panic": -0.8, "sell": -0.6, "exit": -0.5, "dead": -0.8,
            "hack": -0.9, "exploit": -0.8, "vulnerability": -0.7, "risk": -0.4,
            "regulation": -0.3, "ban": -0.8, "restriction": -0.5, "tax": -0.3,
            
            # Neutraalit
            "analysis": 0.0, "technical": 0.0, "fundamental": 0.0, "chart": 0.0,
            "price": 0.0, "volume": 0.0, "market": 0.0, "trading": 0.0
        }
    
    def _initialize_emotion_keywords(self) -> Dict[str, List[str]]:
        """Alusta emotion-avainsanat"""
        return {
            "excitement": ["excited", "thrilled", "amazing", "incredible", "fantastic", "wow"],
            "fear": ["scared", "worried", "afraid", "terrified", "panic", "anxiety"],
            "anger": ["angry", "furious", "mad", "rage", "outrage", "frustrated"],
            "sadness": ["sad", "depressed", "disappointed", "devastated", "heartbroken"],
            "surprise": ["surprised", "shocked", "stunned", "amazed", "unexpected"],
            "trust": ["trust", "confident", "reliable", "secure", "safe", "stable"],
            "anticipation": ["waiting", "expecting", "hoping", "anticipating", "eager"]
        }
    
    def _initialize_risk_keywords(self) -> Dict[str, float]:
        """Alusta risk-avainsanat"""
        return {
            "high_risk": ["risky", "dangerous", "volatile", "unstable", "uncertain"],
            "low_risk": ["safe", "stable", "secure", "reliable", "conservative"],
            "scam_indicators": ["scam", "rug", "honeypot", "fake", "fraud", "ponzi"],
            "technical_risks": ["bug", "exploit", "vulnerability", "hack", "breach"],
            "regulatory_risks": ["regulation", "ban", "restriction", "compliance", "legal"]
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def analyze_text_sentiment(self, text: str) -> Dict[str, float]:
        """Analysoi tekstin sentimenttiä useilla menetelmillä"""
        sentiment_scores = {}
        
        # TextBlob sentiment
        if self.sentiment_models.get('textblob'):
            try:
                blob = TextBlob(text)
                sentiment_scores['textblob'] = blob.sentiment.polarity
            except Exception as e:
                logger.warning(f"TextBlob virhe: {e}")
                sentiment_scores['textblob'] = 0.0
        
        # VADER sentiment
        if self.sentiment_models.get('vader'):
            try:
                vader_scores = self.sentiment_models['vader'].polarity_scores(text)
                sentiment_scores['vader'] = vader_scores['compound']
            except Exception as e:
                logger.warning(f"VADER virhe: {e}")
                sentiment_scores['vader'] = 0.0
        
        # Custom crypto sentiment
        sentiment_scores['crypto'] = self._analyze_crypto_sentiment(text)
        
        # Emotion analysis
        sentiment_scores['emotion'] = self._analyze_emotions(text)
        
        # Risk analysis
        sentiment_scores['risk'] = self._analyze_risk_sentiment(text)
        
        return sentiment_scores
    
    def _analyze_crypto_sentiment(self, text: str) -> float:
        """Analysoi kryptovaluutta-spesifinen sentimentti"""
        text_lower = text.lower()
        sentiment_score = 0.0
        keyword_count = 0
        
        for keyword, weight in self.crypto_keywords.items():
            if keyword in text_lower:
                sentiment_score += weight
                keyword_count += 1
        
        # Normalisoi keyword countin mukaan
        if keyword_count > 0:
            sentiment_score /= keyword_count
        
        # Normalisoi -1 to 1 range
        sentiment_score = max(-1.0, min(1.0, sentiment_score))
        
        return sentiment_score
    
    def _analyze_emotions(self, text: str) -> float:
        """Analysoi emotionit"""
        text_lower = text.lower()
        emotion_scores = {}
        
        for emotion, keywords in self.emotion_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            emotion_scores[emotion] = score
        
        # Laske emotion-painotettu sentimentti
        emotion_weights = {
            "excitement": 0.8,
            "fear": -0.8,
            "anger": -0.6,
            "sadness": -0.7,
            "surprise": 0.3,
            "trust": 0.6,
            "anticipation": 0.4
        }
        
        weighted_sentiment = 0.0
        total_weight = 0.0
        
        for emotion, score in emotion_scores.items():
            if score > 0:
                weight = emotion_weights.get(emotion, 0.0)
                weighted_sentiment += score * weight
                total_weight += score
        
        if total_weight > 0:
            return weighted_sentiment / total_weight
        
        return 0.0
    
    def _analyze_risk_sentiment(self, text: str) -> float:
        """Analysoi risk-sentimentti"""
        text_lower = text.lower()
        risk_score = 0.0
        risk_count = 0
        
        for risk_type, keywords in self.risk_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if risk_type == "high_risk":
                        risk_score += 0.8
                    elif risk_type == "low_risk":
                        risk_score -= 0.6
                    elif risk_type == "scam_indicators":
                        risk_score += 1.0
                    elif risk_type == "technical_risks":
                        risk_score += 0.7
                    elif risk_type == "regulatory_risks":
                        risk_score += 0.5
                    risk_count += 1
        
        if risk_count > 0:
            risk_score /= risk_count
        
        return max(-1.0, min(1.0, risk_score))
    
    def calculate_weighted_sentiment(self, sentiment_scores: Dict[str, float], weights: Dict[str, float] = None) -> float:
        """Laske painotettu sentimentti"""
        if not weights:
            weights = {
                'textblob': 0.2,
                'vader': 0.2,
                'crypto': 0.3,
                'emotion': 0.2,
                'risk': 0.1
            }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for method, score in sentiment_scores.items():
            if method in weights:
                weighted_sum += score * weights[method]
                total_weight += weights[method]
        
        if total_weight > 0:
            return weighted_sum / total_weight
        
        return 0.0
    
    def calculate_confidence(self, sentiment_scores: Dict[str, float]) -> float:
        """Laske sentimentti-luottamus"""
        scores = list(sentiment_scores.values())
        if not scores:
            return 0.0
        
        # Laske standard deviation
        mean_score = np.mean(scores)
        variance = np.mean([(score - mean_score) ** 2 for score in scores])
        std_dev = np.sqrt(variance)
        
        # Luottamus on käänteinen standard deviation
        confidence = max(0.0, 1.0 - std_dev)
        
        return confidence
    
    async def analyze_social_media_sentiment(self, symbol: str, hours: int = 24) -> Dict:
        """Analysoi sosiaalisen median sentimenttiä"""
        sentiment_data = []
        
        # Twitter sentiment
        twitter_sentiment = await self._analyze_twitter_sentiment(symbol, hours)
        if twitter_sentiment:
            sentiment_data.extend(twitter_sentiment)
        
        # Reddit sentiment
        reddit_sentiment = await self._analyze_reddit_sentiment(symbol, hours)
        if reddit_sentiment:
            sentiment_data.extend(reddit_sentiment)
        
        # Telegram sentiment (simuloidaan)
        telegram_sentiment = await self._analyze_telegram_sentiment(symbol, hours)
        if telegram_sentiment:
            sentiment_data.extend(telegram_sentiment)
        
        return self._aggregate_sentiment_data(sentiment_data)
    
    async def _analyze_twitter_sentiment(self, symbol: str, hours: int) -> List[SentimentData]:
        """Analysoi Twitter sentimenttiä"""
        if not self.twitter_bearer_token:
            logger.warning("Twitter Bearer Token puuttuu")
            return []
        
        try:
            # Twitter API v2 search
            url = "https://api.twitter.com/2/tweets/search/recent"
            headers = {
                "Authorization": f"Bearer {self.twitter_bearer_token}",
                "Content-Type": "application/json"
            }
            
            # Hae viimeiset 24h tweetit
            query = f"{symbol} -is:retweet lang:en"
            params = {
                "query": query,
                "max_results": 100,
                "tweet.fields": "created_at,public_metrics,author_id"
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    tweets = data.get("data", [])
                    
                    sentiment_data = []
                    for tweet in tweets:
                        text = tweet.get("text", "")
                        created_at = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
                        metrics = tweet.get("public_metrics", {})
                        engagement = metrics.get("like_count", 0) + metrics.get("retweet_count", 0)
                        
                        sentiment_scores = self.analyze_text_sentiment(text)
                        overall_sentiment = self.calculate_weighted_sentiment(sentiment_scores)
                        confidence = self.calculate_confidence(sentiment_scores)
                        
                        sentiment_data.append(SentimentData(
                            text=text,
                            timestamp=created_at,
                            source="twitter",
                            author=tweet.get("author_id", ""),
                            engagement=engagement,
                            sentiment_score=overall_sentiment,
                            confidence=confidence,
                            emotion=self._classify_emotion(overall_sentiment),
                            keywords=self._extract_keywords(text),
                            language="en"
                        ))
                    
                    return sentiment_data
                else:
                    logger.warning(f"Twitter API virhe: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Twitter sentiment virhe: {e}")
            return []
    
    async def _analyze_reddit_sentiment(self, symbol: str, hours: int) -> List[SentimentData]:
        """Analysoi Reddit sentimenttiä"""
        if not self.reddit_client_id or not self.reddit_client_secret:
            logger.warning("Reddit API avaimet puuttuvat")
            return []
        
        try:
            # Reddit API access
            auth_url = "https://www.reddit.com/api/v1/access_token"
            auth_data = {
                "grant_type": "client_credentials"
            }
            auth_headers = {
                "User-Agent": "CryptoBot/1.0"
            }
            
            async with self.session.post(
                auth_url, 
                data=auth_data, 
                headers=auth_headers,
                auth=aiohttp.BasicAuth(self.reddit_client_id, self.reddit_client_secret)
            ) as response:
                if response.status == 200:
                    auth_data = await response.json()
                    access_token = auth_data.get("access_token")
                    
                    # Hae Reddit postit
                    search_url = f"https://oauth.reddit.com/search"
                    headers = {
                        "Authorization": f"bearer {access_token}",
                        "User-Agent": "CryptoBot/1.0"
                    }
                    params = {
                        "q": symbol,
                        "sort": "new",
                        "limit": 100,
                        "t": "day"
                    }
                    
                    async with self.session.get(search_url, headers=headers, params=params) as search_response:
                        if search_response.status == 200:
                            data = await search_response.json()
                            posts = data.get("data", {}).get("children", [])
                            
                            sentiment_data = []
                            for post in posts:
                                post_data = post.get("data", {})
                                text = post_data.get("selftext", "") or post_data.get("title", "")
                                created_at = datetime.fromtimestamp(post_data.get("created_utc", 0))
                                engagement = post_data.get("score", 0) + post_data.get("num_comments", 0)
                                
                                sentiment_scores = self.analyze_text_sentiment(text)
                                overall_sentiment = self.calculate_weighted_sentiment(sentiment_scores)
                                confidence = self.calculate_confidence(sentiment_scores)
                                
                                sentiment_data.append(SentimentData(
                                    text=text,
                                    timestamp=created_at,
                                    source="reddit",
                                    author=post_data.get("author", ""),
                                    engagement=engagement,
                                    sentiment_score=overall_sentiment,
                                    confidence=confidence,
                                    emotion=self._classify_emotion(overall_sentiment),
                                    keywords=self._extract_keywords(text),
                                    language="en"
                                ))
                            
                            return sentiment_data
                        else:
                            logger.warning(f"Reddit search virhe: {search_response.status}")
                            return []
                else:
                    logger.warning(f"Reddit auth virhe: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Reddit sentiment virhe: {e}")
            return []
    
    async def _analyze_telegram_sentiment(self, symbol: str, hours: int) -> List[SentimentData]:
        """Analysoi Telegram sentimenttiä (simuloidaan)"""
        # Simuloi Telegram data
        sentiment_data = []
        
        for i in range(20):
            # Simuloi Telegram viestejä
            messages = [
                f"{symbol} going to the moon! 🚀",
                f"Just bought more {symbol}, diamond hands! 💎",
                f"{symbol} chart looks bullish 📈",
                f"Be careful with {symbol}, might be a rug pull",
                f"{symbol} community is amazing!",
                f"Selling {symbol}, too risky for me",
                f"{symbol} partnership announced! Bullish!",
                f"{symbol} price action is crazy today"
            ]
            
            text = np.random.choice(messages)
            created_at = datetime.now() - timedelta(hours=np.random.uniform(0, hours))
            engagement = np.random.randint(1, 100)
            
            sentiment_scores = self.analyze_text_sentiment(text)
            overall_sentiment = self.calculate_weighted_sentiment(sentiment_scores)
            confidence = self.calculate_confidence(sentiment_scores)
            
            sentiment_data.append(SentimentData(
                text=text,
                timestamp=created_at,
                source="telegram",
                author=f"user_{i}",
                engagement=engagement,
                sentiment_score=overall_sentiment,
                confidence=confidence,
                emotion=self._classify_emotion(overall_sentiment),
                keywords=self._extract_keywords(text),
                language="en"
            ))
        
        return sentiment_data
    
    def _classify_emotion(self, sentiment_score: float) -> str:
        """Luokittele emotion sentimentti-scoren perusteella"""
        if sentiment_score > 0.6:
            return "excitement"
        elif sentiment_score > 0.3:
            return "positive"
        elif sentiment_score > -0.3:
            return "neutral"
        elif sentiment_score > -0.6:
            return "negative"
        else:
            return "fear"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Poimi avainsanat tekstistä"""
        text_lower = text.lower()
        keywords = []
        
        for keyword in self.crypto_keywords.keys():
            if keyword in text_lower:
                keywords.append(keyword)
        
        return keywords
    
    def _aggregate_sentiment_data(self, sentiment_data: List[SentimentData]) -> SentimentAnalysis:
        """Yhdistä sentimentti-data"""
        if not sentiment_data:
            return SentimentAnalysis(
                overall_sentiment=0.0,
                confidence=0.0,
                emotion_distribution={},
                keyword_sentiment={},
                source_sentiment={},
                temporal_sentiment=[],
                volume_weighted_sentiment=0.0,
                influencer_sentiment=0.0,
                community_sentiment=0.0,
                news_sentiment=0.0,
                social_sentiment=0.0,
                technical_sentiment=0.0,
                risk_sentiment=0.0
            )
        
        # Laske perusmittarit
        sentiments = [data.sentiment_score for data in sentiment_data]
        confidences = [data.confidence for data in sentiment_data]
        engagements = [data.engagement for data in sentiment_data]
        
        overall_sentiment = np.mean(sentiments)
        confidence = np.mean(confidences)
        
        # Volume-weighted sentiment
        total_engagement = sum(engagements)
        if total_engagement > 0:
            volume_weighted_sentiment = sum(
                data.sentiment_score * data.engagement for data in sentiment_data
            ) / total_engagement
        else:
            volume_weighted_sentiment = overall_sentiment
        
        # Emotion distribution
        emotions = [data.emotion for data in sentiment_data]
        emotion_distribution = dict(Counter(emotions))
        total_emotions = sum(emotion_distribution.values())
        emotion_distribution = {
            emotion: count / total_emotions 
            for emotion, count in emotion_distribution.items()
        }
        
        # Source sentiment
        source_sentiment = {}
        for source in set(data.source for data in sentiment_data):
            source_data = [data for data in sentiment_data if data.source == source]
            source_sentiment[source] = np.mean([data.sentiment_score for data in source_data])
        
        # Temporal sentiment
        temporal_sentiment = [
            (data.timestamp, data.sentiment_score) 
            for data in sentiment_data
        ]
        temporal_sentiment.sort(key=lambda x: x[0])
        
        # Keyword sentiment
        keyword_sentiment = {}
        for data in sentiment_data:
            for keyword in data.keywords:
                if keyword not in keyword_sentiment:
                    keyword_sentiment[keyword] = []
                keyword_sentiment[keyword].append(data.sentiment_score)
        
        keyword_sentiment = {
            keyword: np.mean(scores) 
            for keyword, scores in keyword_sentiment.items()
        }
        
        # Eri tyyppien sentimentti
        social_sentiment = np.mean([
            data.sentiment_score for data in sentiment_data 
            if data.source in ['twitter', 'reddit', 'telegram']
        ])
        
        # Simuloi muut sentimentit
        news_sentiment = overall_sentiment * 0.8  # Uutiset yleensä neutraalimmat
        technical_sentiment = overall_sentiment * 0.6  # Tekninen analyysi neutraalimpi
        risk_sentiment = -abs(overall_sentiment) * 0.5  # Risk-sentimentti negatiivisempi
        
        # Influencer sentiment (simuloi)
        influencer_sentiment = overall_sentiment * 1.2  # Influencerit yleensä äärimmäisempiä
        community_sentiment = overall_sentiment * 0.9  # Yhteisö hieman neutraalimpi
        
        return SentimentAnalysis(
            overall_sentiment=overall_sentiment,
            confidence=confidence,
            emotion_distribution=emotion_distribution,
            keyword_sentiment=keyword_sentiment,
            source_sentiment=source_sentiment,
            temporal_sentiment=temporal_sentiment,
            volume_weighted_sentiment=volume_weighted_sentiment,
            influencer_sentiment=influencer_sentiment,
            community_sentiment=community_sentiment,
            news_sentiment=news_sentiment,
            social_sentiment=social_sentiment,
            technical_sentiment=technical_sentiment,
            risk_sentiment=risk_sentiment
        )
    
    async def analyze_news_sentiment(self, symbol: str, hours: int = 24) -> Dict:
        """Analysoi uutisten sentimenttiä"""
        # Simuloi uutisdata
        news_data = [
            f"{symbol} announces new partnership with major tech company",
            f"{symbol} price surges 50% after positive earnings report",
            f"Regulatory concerns weigh on {symbol} as new rules proposed",
            f"{symbol} community celebrates milestone achievement",
            f"Analysts raise price target for {symbol} citing strong fundamentals"
        ]
        
        sentiment_data = []
        for i, headline in enumerate(news_data):
            created_at = datetime.now() - timedelta(hours=np.random.uniform(0, hours))
            engagement = np.random.randint(100, 1000)
            
            sentiment_scores = self.analyze_text_sentiment(headline)
            overall_sentiment = self.calculate_weighted_sentiment(sentiment_scores)
            confidence = self.calculate_confidence(sentiment_scores)
            
            sentiment_data.append(SentimentData(
                text=headline,
                timestamp=created_at,
                source="news",
                author=f"news_source_{i}",
                engagement=engagement,
                sentiment_score=overall_sentiment,
                confidence=confidence,
                emotion=self._classify_emotion(overall_sentiment),
                keywords=self._extract_keywords(headline),
                language="en"
            ))
        
        return self._aggregate_sentiment_data(sentiment_data)
    
    def generate_sentiment_report(self, symbol: str, social_analysis: SentimentAnalysis, news_analysis: SentimentAnalysis) -> Dict:
        """Generoi sentimentti-raportti"""
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "social_media": asdict(social_analysis),
            "news": asdict(news_analysis),
            "combined_sentiment": {
                "overall": (social_analysis.overall_sentiment + news_analysis.overall_sentiment) / 2,
                "confidence": (social_analysis.confidence + news_analysis.confidence) / 2,
                "volume_weighted": (social_analysis.volume_weighted_sentiment + news_analysis.volume_weighted_sentiment) / 2
            },
            "recommendations": self._generate_sentiment_recommendations(social_analysis, news_analysis)
        }
    
    def _generate_sentiment_recommendations(self, social_analysis: SentimentAnalysis, news_analysis: SentimentAnalysis) -> List[str]:
        """Generoi sentimentti-suositukset"""
        recommendations = []
        
        combined_sentiment = (social_analysis.overall_sentiment + news_analysis.overall_sentiment) / 2
        
        if combined_sentiment > 0.7:
            recommendations.append("Erittäin positiivinen sentimentti - harkitse position lisäämistä")
        elif combined_sentiment > 0.3:
            recommendations.append("Positiivinen sentimentti - hyvä entry point")
        elif combined_sentiment > -0.3:
            recommendations.append("Neutraali sentimentti - odota selkeämpää signaalia")
        elif combined_sentiment > -0.7:
            recommendations.append("Negatiivinen sentimentti - harkitse position vähentämistä")
        else:
            recommendations.append("Erittäin negatiivinen sentimentti - harkitse myyntiä")
        
        if social_analysis.confidence < 0.5:
            recommendations.append("Matala luottamus sosiaalisen median sentimenttiin - varovainen")
        
        if news_analysis.confidence < 0.5:
            recommendations.append("Matala luottamus uutisten sentimenttiin - varovainen")
        
        if social_analysis.risk_sentiment < -0.5:
            recommendations.append("Korkea risk-sentimentti - lisää riskienhallintaa")
        
        return recommendations

# Esimerkki käytöstä
async def example_usage():
    """Esimerkki AI sentimentti-analyysin käytöstä"""
    async with AISentimentAnalyzer() as analyzer:
        symbol = "BTC"
        
        # Analysoi sosiaalisen median sentimenttiä
        social_analysis = await analyzer.analyze_social_media_sentiment(symbol, 24)
        print(f"Sosiaalisen median sentimentti: {social_analysis.overall_sentiment:.3f}")
        
        # Analysoi uutisten sentimenttiä
        news_analysis = await analyzer.analyze_news_sentiment(symbol, 24)
        print(f"Uutisten sentimentti: {news_analysis.overall_sentiment:.3f}")
        
        # Generoi raportti
        report = analyzer.generate_sentiment_report(symbol, social_analysis, news_analysis)
        print(f"Sentimentti-raportti: {json.dumps(report, indent=2, default=str)}")

if __name__ == "__main__":
    asyncio.run(example_usage())
