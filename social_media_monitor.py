"""
Social Media Monitor - Sosiaalisen median seuranta
Seuraa Twitter, Reddit, Telegram ja Discord -kanavia reaaliajassa
"""

import asyncio
import aiohttp
import json
import logging
import re
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Tuple, Callable
import requests
from collections import defaultdict, Counter
import os
from dotenv import load_dotenv

# Import our AI sentiment analyzer
try:
    from ai_sentiment_analysis import AISentimentAnalyzer
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

# Load environment
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SocialMediaPost:
    """Sosiaalisen median posti"""
    id: str
    platform: str
    author: str
    content: str
    timestamp: datetime
    engagement: int
    url: str
    hashtags: List[str]
    mentions: List[str]
    sentiment_score: float
    confidence: float
    emotion: str
    keywords: List[str]
    language: str
    is_retweet: bool = False
    is_reply: bool = False
    parent_id: Optional[str] = None

@dataclass
class SocialMediaMetrics:
    """Sosiaalisen median mittarit"""
    total_posts: int
    total_engagement: int
    sentiment_distribution: Dict[str, int]
    emotion_distribution: Dict[str, int]
    top_hashtags: List[Tuple[str, int]]
    top_mentions: List[Tuple[str, int]]
    top_keywords: List[Tuple[str, int]]
    platform_distribution: Dict[str, int]
    engagement_rate: float
    sentiment_trend: List[Tuple[datetime, float]]
    viral_posts: List[SocialMediaPost]
    influencer_posts: List[SocialMediaPost]

class SocialMediaMonitor:
    """Sosiaalisen median seuranta"""
    
    def __init__(self):
        self.session = None
        self.sentiment_analyzer = None
        self.running = False
        
        # Data storage
        self.posts = []
        self.metrics = SocialMediaMetrics(
            total_posts=0,
            total_engagement=0,
            sentiment_distribution={},
            emotion_distribution={},
            top_hashtags=[],
            top_mentions=[],
            top_keywords=[],
            platform_distribution={},
            engagement_rate=0.0,
            sentiment_trend=[],
            viral_posts=[],
            influencer_posts=[]
        )
        
        # Configuration
        self.config = {
            'max_posts': 10000,
            'viral_threshold': 1000,  # engagement threshold
            'influencer_threshold': 10000,  # follower threshold
            'update_interval': 300,  # 5 minutes
            'sentiment_update_interval': 60,  # 1 minute
            'trending_window': 3600,  # 1 hour
            'max_hashtags': 20,
            'max_mentions': 20,
            'max_keywords': 50
        }
        
        # API keys
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
        self.reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
        
        # Callbacks
        self.callbacks = {
            'on_new_post': [],
            'on_viral_post': [],
            'on_sentiment_change': [],
            'on_trending_hashtag': [],
            'on_influencer_post': []
        }
        
        # Tracking
        self.tracked_symbols = set()
        self.tracked_hashtags = set()
        self.tracked_keywords = set()
        self.influencer_list = set()
        
        # Initialize sentiment analyzer
        if SENTIMENT_AVAILABLE:
            self.sentiment_analyzer = AISentimentAnalyzer()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def add_callback(self, event_type: str, callback: Callable):
        """Lisää callback-funktio"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
        else:
            logger.warning(f"Tuntematon event_type: {event_type}")
    
    def add_tracking(self, symbols: List[str] = None, hashtags: List[str] = None, 
                    keywords: List[str] = None, influencers: List[str] = None):
        """Lisää seurattavia kohteita"""
        if symbols:
            self.tracked_symbols.update(symbols)
            logger.info(f"Lisätty seurattavat symbolit: {symbols}")
        
        if hashtags:
            self.tracked_hashtags.update(hashtags)
            logger.info(f"Lisätty seurattavat hashtagit: {hashtags}")
        
        if keywords:
            self.tracked_keywords.update(keywords)
            logger.info(f"Lisätty seurattavat avainsanat: {keywords}")
        
        if influencers:
            self.influencer_list.update(influencers)
            logger.info(f"Lisätty seurattavat influencerit: {influencers}")
    
    async def start_monitoring(self):
        """Aloita seuranta"""
        self.running = True
        logger.info("🎧 Aloitetaan sosiaalisen median seuranta...")
        
        # Aloita seuranta eri alustoilla
        tasks = []
        
        if self.twitter_bearer_token:
            tasks.append(self._monitor_twitter())
        
        if self.reddit_client_id and self.reddit_client_secret:
            tasks.append(self._monitor_reddit())
        
        if self.telegram_bot_token:
            tasks.append(self._monitor_telegram())
        
        if self.discord_bot_token:
            tasks.append(self._monitor_discord())
        
        # Aloita metrikkien päivitys
        tasks.append(self._update_metrics_loop())
        
        # Aloita sentimentti-trendin seuranta
        if self.sentiment_analyzer:
            tasks.append(self._monitor_sentiment_trends())
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Virhe seurannassa: {e}")
        finally:
            self.running = False
    
    def stop_monitoring(self):
        """Pysäytä seuranta"""
        self.running = False
        logger.info("⏹️ Sosiaalisen median seuranta pysäytetty")
    
    async def _monitor_twitter(self):
        """Seuraa Twitteriä"""
        logger.info("🐦 Aloitetaan Twitter-seuranta...")
        
        while self.running:
            try:
                # Hae viimeisimmät tweetit
                await self._fetch_twitter_posts()
                await asyncio.sleep(60)  # 1 minuutti
            except Exception as e:
                logger.error(f"Virhe Twitter-seurannassa: {e}")
                await asyncio.sleep(300)  # 5 minuuttia virheen jälkeen
    
    async def _monitor_reddit(self):
        """Seuraa Redditiä"""
        logger.info("🔴 Aloitetaan Reddit-seuranta...")
        
        while self.running:
            try:
                # Hae viimeisimmät postit
                await self._fetch_reddit_posts()
                await asyncio.sleep(120)  # 2 minuuttia
            except Exception as e:
                logger.error(f"Virhe Reddit-seurannassa: {e}")
                await asyncio.sleep(300)  # 5 minuuttia virheen jälkeen
    
    async def _monitor_telegram(self):
        """Seuraa Telegramia"""
        logger.info("📱 Aloitetaan Telegram-seuranta...")
        
        while self.running:
            try:
                # Hae viimeisimmät viestit
                await self._fetch_telegram_posts()
                await asyncio.sleep(180)  # 3 minuuttia
            except Exception as e:
                logger.error(f"Virhe Telegram-seurannassa: {e}")
                await asyncio.sleep(300)  # 5 minuuttia virheen jälkeen
    
    async def _monitor_discord(self):
        """Seuraa Discordia"""
        logger.info("💬 Aloitetaan Discord-seuranta...")
        
        while self.running:
            try:
                # Hae viimeisimmät viestit
                await self._fetch_discord_posts()
                await asyncio.sleep(240)  # 4 minuuttia
            except Exception as e:
                logger.error(f"Virhe Discord-seurannassa: {e}")
                await asyncio.sleep(300)  # 5 minuuttia virheen jälkeen
    
    async def _fetch_twitter_posts(self):
        """Hae Twitter-postit"""
        if not self.twitter_bearer_token:
            return
        
        try:
            # Rakenna hakuquery
            query_parts = []
            
            if self.tracked_symbols:
                symbols_query = " OR ".join([f"${symbol}" for symbol in self.tracked_symbols])
                query_parts.append(f"({symbols_query})")
            
            if self.tracked_hashtags:
                hashtags_query = " OR ".join([f"#{hashtag}" for hashtag in self.tracked_hashtags])
                query_parts.append(f"({hashtags_query})")
            
            if self.tracked_keywords:
                keywords_query = " OR ".join(self.tracked_keywords)
                query_parts.append(f"({keywords_query})")
            
            if not query_parts:
                return
            
            query = " OR ".join(query_parts) + " -is:retweet lang:en"
            
            # Twitter API v2 search
            url = "https://api.twitter.com/2/tweets/search/recent"
            headers = {
                "Authorization": f"Bearer {self.twitter_bearer_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "query": query,
                "max_results": 100,
                "tweet.fields": "created_at,public_metrics,author_id,context_annotations",
                "user.fields": "public_metrics,verified"
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    tweets = data.get("data", [])
                    users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}
                    
                    for tweet in tweets:
                        user = users.get(tweet.get("author_id", ""), {})
                        await self._process_twitter_post(tweet, user)
                else:
                    logger.warning(f"Twitter API virhe: {response.status}")
        
        except Exception as e:
            logger.error(f"Virhe Twitter-postien haussa: {e}")
    
    async def _fetch_reddit_posts(self):
        """Hae Reddit-postit"""
        if not self.reddit_client_id or not self.reddit_client_secret:
            return
        
        try:
            # Hae access token
            auth_url = "https://www.reddit.com/api/v1/access_token"
            auth_data = {"grant_type": "client_credentials"}
            auth_headers = {"User-Agent": "CryptoBot/1.0"}
            
            async with self.session.post(
                auth_url,
                data=auth_data,
                headers=auth_headers,
                auth=aiohttp.BasicAuth(self.reddit_client_id, self.reddit_client_secret)
            ) as response:
                if response.status == 200:
                    auth_data = await response.json()
                    access_token = auth_data.get("access_token")
                    
                    # Hae postit
                    for symbol in self.tracked_symbols:
                        await self._fetch_reddit_posts_for_symbol(symbol, access_token)
        
        except Exception as e:
            logger.error(f"Virhe Reddit-postien haussa: {e}")
    
    async def _fetch_reddit_posts_for_symbol(self, symbol: str, access_token: str):
        """Hae Reddit-postit symbolille"""
        try:
            search_url = "https://oauth.reddit.com/search"
            headers = {
                "Authorization": f"bearer {access_token}",
                "User-Agent": "CryptoBot/1.0"
            }
            
            params = {
                "q": symbol,
                "sort": "new",
                "limit": 25,
                "t": "day"
            }
            
            async with self.session.get(search_url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    posts = data.get("data", {}).get("children", [])
                    
                    for post in posts:
                        post_data = post.get("data", {})
                        await self._process_reddit_post(post_data)
        
        except Exception as e:
            logger.error(f"Virhe Reddit-postien haussa symbolille {symbol}: {e}")
    
    async def _fetch_telegram_posts(self):
        """Hae Telegram-viestit (simuloidaan)"""
        # Simuloi Telegram-viestejä
        for i in range(5):
            post = SocialMediaPost(
                id=f"telegram_{i}_{int(time.time())}",
                platform="telegram",
                author=f"user_{i}",
                content=f"Just bought some {list(self.tracked_symbols)[0] if self.tracked_symbols else 'BTC'}! 🚀",
                timestamp=datetime.now() - timedelta(minutes=i),
                engagement=np.random.randint(10, 100),
                url=f"https://t.me/channel/{i}",
                hashtags=["#crypto", "#trading"],
                mentions=[],
                sentiment_score=0.0,
                confidence=0.0,
                emotion="neutral",
                keywords=[],
                language="en"
            )
            
            await self._process_post(post)
    
    async def _fetch_discord_posts(self):
        """Hae Discord-viestit (simuloidaan)"""
        # Simuloi Discord-viestejä
        for i in range(3):
            post = SocialMediaPost(
                id=f"discord_{i}_{int(time.time())}",
                platform="discord",
                author=f"user_{i}",
                content=f"Market analysis: {list(self.tracked_symbols)[0] if self.tracked_symbols else 'BTC'} looking bullish 📈",
                timestamp=datetime.now() - timedelta(minutes=i*2),
                engagement=np.random.randint(5, 50),
                url=f"https://discord.com/channels/{i}",
                hashtags=[],
                mentions=[],
                sentiment_score=0.0,
                confidence=0.0,
                emotion="neutral",
                keywords=[],
                language="en"
            )
            
            await self._process_post(post)
    
    async def _process_twitter_post(self, tweet: Dict, user: Dict):
        """Käsittele Twitter-posti"""
        try:
            # Poimi tiedot
            content = tweet.get("text", "")
            metrics = tweet.get("public_metrics", {})
            engagement = (
                metrics.get("like_count", 0) +
                metrics.get("retweet_count", 0) +
                metrics.get("reply_count", 0) +
                metrics.get("quote_count", 0)
            )
            
            # Poimi hashtagit ja mentions
            hashtags = re.findall(r'#\w+', content)
            mentions = re.findall(r'@\w+', content)
            
            # Tarkista onko retweet
            is_retweet = "RT @" in content
            
            post = SocialMediaPost(
                id=tweet.get("id", ""),
                platform="twitter",
                author=user.get("username", ""),
                content=content,
                timestamp=datetime.fromisoformat(tweet.get("created_at", "").replace("Z", "+00:00")),
                engagement=engagement,
                url=f"https://twitter.com/{user.get('username', '')}/status/{tweet.get('id', '')}",
                hashtags=hashtags,
                mentions=mentions,
                sentiment_score=0.0,
                confidence=0.0,
                emotion="neutral",
                keywords=[],
                language="en",
                is_retweet=is_retweet
            )
            
            await self._process_post(post)
        
        except Exception as e:
            logger.error(f"Virhe Twitter-postin käsittelyssä: {e}")
    
    async def _process_reddit_post(self, post_data: Dict):
        """Käsittele Reddit-posti"""
        try:
            content = post_data.get("selftext", "") or post_data.get("title", "")
            engagement = post_data.get("score", 0) + post_data.get("num_comments", 0)
            
            post = SocialMediaPost(
                id=post_data.get("id", ""),
                platform="reddit",
                author=post_data.get("author", ""),
                content=content,
                timestamp=datetime.fromtimestamp(post_data.get("created_utc", 0)),
                engagement=engagement,
                url=f"https://reddit.com{post_data.get('permalink', '')}",
                hashtags=[],
                mentions=[],
                sentiment_score=0.0,
                confidence=0.0,
                emotion="neutral",
                keywords=[],
                language="en"
            )
            
            await self._process_post(post)
        
        except Exception as e:
            logger.error(f"Virhe Reddit-postin käsittelyssä: {e}")
    
    async def _process_post(self, post: SocialMediaPost):
        """Käsittele posti"""
        try:
            # Analysoi sentimentti
            if self.sentiment_analyzer:
                sentiment_scores = self.sentiment_analyzer.analyze_text_sentiment(post.content)
                post.sentiment_score = self.sentiment_analyzer.calculate_weighted_sentiment(sentiment_scores)
                post.confidence = self.sentiment_analyzer.calculate_confidence(sentiment_scores)
                post.emotion = self.sentiment_analyzer._classify_emotion(post.sentiment_score)
                post.keywords = self.sentiment_analyzer._extract_keywords(post.content)
            
            # Lisää posti listaan
            self.posts.append(post)
            
            # Rajoita post-määrä
            if len(self.posts) > self.config['max_posts']:
                self.posts = self.posts[-self.config['max_posts']:]
            
            # Tarkista onko viral
            if post.engagement >= self.config['viral_threshold']:
                self.metrics.viral_posts.append(post)
                for callback in self.callbacks['on_viral_post']:
                    await callback(post)
            
            # Tarkista onko influencer
            if self._is_influencer_post(post):
                self.metrics.influencer_posts.append(post)
                for callback in self.callbacks['on_influencer_post']:
                    await callback(post)
            
            # Kutsu callbackit
            for callback in self.callbacks['on_new_post']:
                await callback(post)
        
        except Exception as e:
            logger.error(f"Virhe postin käsittelyssä: {e}")
    
    def _is_influencer_post(self, post: SocialMediaPost) -> bool:
        """Tarkista onko influencer-posti"""
        # Tarkista onko author influencer-listassa
        if post.author in self.influencer_list:
            return True
        
        # Tarkista engagement (yksinkertainen heuristiikka)
        if post.engagement >= self.config['influencer_threshold']:
            return True
        
        # Tarkista platform-kohtaiset kriteerit
        if post.platform == "twitter" and post.engagement >= 1000:
            return True
        elif post.platform == "reddit" and post.engagement >= 500:
            return True
        
        return False
    
    async def _update_metrics_loop(self):
        """Päivitä metrikit säännöllisesti"""
        while self.running:
            try:
                self._update_metrics()
                await asyncio.sleep(self.config['update_interval'])
            except Exception as e:
                logger.error(f"Virhe metrikkien päivittämisessä: {e}")
                await asyncio.sleep(60)
    
    def _update_metrics(self):
        """Päivitä metrikit"""
        try:
            # Perusmittarit
            self.metrics.total_posts = len(self.posts)
            self.metrics.total_engagement = sum(post.engagement for post in self.posts)
            
            # Sentimentti-jakauma
            sentiment_counts = defaultdict(int)
            for post in self.posts:
                if post.sentiment_score > 0.3:
                    sentiment_counts['positive'] += 1
                elif post.sentiment_score < -0.3:
                    sentiment_counts['negative'] += 1
                else:
                    sentiment_counts['neutral'] += 1
            
            self.metrics.sentiment_distribution = dict(sentiment_counts)
            
            # Emotion-jakauma
            emotion_counts = Counter(post.emotion for post in self.posts)
            self.metrics.emotion_distribution = dict(emotion_counts)
            
            # Top hashtagit
            all_hashtags = []
            for post in self.posts:
                all_hashtags.extend(post.hashtags)
            hashtag_counts = Counter(all_hashtags)
            self.metrics.top_hashtags = hashtag_counts.most_common(self.config['max_hashtags'])
            
            # Top mentions
            all_mentions = []
            for post in self.posts:
                all_mentions.extend(post.mentions)
            mention_counts = Counter(all_mentions)
            self.metrics.top_mentions = mention_counts.most_common(self.config['max_mentions'])
            
            # Top keywords
            all_keywords = []
            for post in self.posts:
                all_keywords.extend(post.keywords)
            keyword_counts = Counter(all_keywords)
            self.metrics.top_keywords = keyword_counts.most_common(self.config['max_keywords'])
            
            # Platform-jakauma
            platform_counts = Counter(post.platform for post in self.posts)
            self.metrics.platform_distribution = dict(platform_counts)
            
            # Engagement rate
            if self.metrics.total_posts > 0:
                self.metrics.engagement_rate = self.metrics.total_engagement / self.metrics.total_posts
            else:
                self.metrics.engagement_rate = 0.0
            
            # Päivitä sentimentti-trendi
            self._update_sentiment_trend()
            
        except Exception as e:
            logger.error(f"Virhe metrikkien päivittämisessä: {e}")
    
    def _update_sentiment_trend(self):
        """Päivitä sentimentti-trendi"""
        try:
            # Ryhmittele postit aikaväleihin
            now = datetime.now()
            time_windows = []
            
            for i in range(12):  # 12 x 5 min = 1 tunti
                window_start = now - timedelta(minutes=(i+1)*5)
                window_end = now - timedelta(minutes=i*5)
                
                window_posts = [
                    post for post in self.posts
                    if window_start <= post.timestamp <= window_end
                ]
                
                if window_posts:
                    avg_sentiment = np.mean([post.sentiment_score for post in window_posts])
                    time_windows.append((window_end, avg_sentiment))
            
            self.metrics.sentiment_trend = time_windows
            
        except Exception as e:
            logger.error(f"Virhe sentimentti-trendin päivittämisessä: {e}")
    
    async def _monitor_sentiment_trends(self):
        """Seuraa sentimentti-trendejä"""
        while self.running:
            try:
                # Tarkista sentimentti-muutokset
                if len(self.metrics.sentiment_trend) >= 2:
                    recent_sentiment = self.metrics.sentiment_trend[-1][1]
                    previous_sentiment = self.metrics.sentiment_trend[-2][1]
                    
                    sentiment_change = recent_sentiment - previous_sentiment
                    
                    # Jos sentimentti muuttuu merkittävästi
                    if abs(sentiment_change) > 0.2:
                        for callback in self.callbacks['on_sentiment_change']:
                            await callback({
                                'change': sentiment_change,
                                'recent_sentiment': recent_sentiment,
                                'previous_sentiment': previous_sentiment
                            })
                
                await asyncio.sleep(self.config['sentiment_update_interval'])
            
            except Exception as e:
                logger.error(f"Virhe sentimentti-trendien seurannassa: {e}")
                await asyncio.sleep(60)
    
    def get_analysis_report(self) -> Dict:
        """Hae analyysiraportti"""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": asdict(self.metrics),
            "recent_posts": [
                {
                    "id": post.id,
                    "platform": post.platform,
                    "author": post.author,
                    "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
                    "timestamp": post.timestamp.isoformat(),
                    "engagement": post.engagement,
                    "sentiment_score": post.sentiment_score,
                    "emotion": post.emotion,
                    "hashtags": post.hashtags,
                    "keywords": post.keywords
                }
                for post in self.posts[-20:]  # Viimeiset 20 postia
            ],
            "trending_analysis": {
                "trending_hashtags": self.metrics.top_hashtags[:10],
                "trending_keywords": self.metrics.top_keywords[:10],
                "sentiment_trend": self.metrics.sentiment_trend[-10:],  # Viimeiset 10 aikaväliä
                "viral_posts_count": len(self.metrics.viral_posts),
                "influencer_posts_count": len(self.metrics.influencer_posts)
            },
            "tracking_info": {
                "tracked_symbols": list(self.tracked_symbols),
                "tracked_hashtags": list(self.tracked_hashtags),
                "tracked_keywords": list(self.tracked_keywords),
                "influencer_list": list(self.influencer_list)
            }
        }
    
    def get_sentiment_summary(self) -> Dict:
        """Hae sentimentti-yhteenveto"""
        if not self.posts:
            return {"error": "Ei posteja analysoitavaksi"}
        
        recent_posts = [
            post for post in self.posts
            if post.timestamp > datetime.now() - timedelta(hours=24)
        ]
        
        if not recent_posts:
            return {"error": "Ei viimeisen 24h posteja"}
        
        # Laske sentimentti-mittarit
        sentiment_scores = [post.sentiment_score for post in recent_posts]
        avg_sentiment = np.mean(sentiment_scores)
        sentiment_std = np.std(sentiment_scores)
        
        # Laske emotion-jakauma
        emotion_counts = Counter(post.emotion for post in recent_posts)
        total_posts = len(recent_posts)
        emotion_distribution = {
            emotion: count / total_posts
            for emotion, count in emotion_counts.items()
        }
        
        # Laske platform-kohtaiset sentimentit
        platform_sentiments = {}
        for platform in set(post.platform for post in recent_posts):
            platform_posts = [post for post in recent_posts if post.platform == platform]
            platform_sentiments[platform] = np.mean([post.sentiment_score for post in platform_posts])
        
        return {
            "timestamp": datetime.now().isoformat(),
            "period": "24h",
            "total_posts": total_posts,
            "average_sentiment": avg_sentiment,
            "sentiment_volatility": sentiment_std,
            "emotion_distribution": emotion_distribution,
            "platform_sentiments": platform_sentiments,
            "sentiment_trend": self.metrics.sentiment_trend[-24:],  # Viimeiset 24 aikaväliä
            "recommendations": self._generate_sentiment_recommendations(avg_sentiment, sentiment_std)
        }
    
    def _generate_sentiment_recommendations(self, avg_sentiment: float, sentiment_std: float) -> List[str]:
        """Generoi sentimentti-suositukset"""
        recommendations = []
        
        if avg_sentiment > 0.5:
            recommendations.append("Erittäin positiivinen sentimentti - harkitse position lisäämistä")
        elif avg_sentiment > 0.2:
            recommendations.append("Positiivinen sentimentti - hyvä entry point")
        elif avg_sentiment > -0.2:
            recommendations.append("Neutraali sentimentti - odota selkeämpää signaalia")
        elif avg_sentiment > -0.5:
            recommendations.append("Negatiivinen sentimentti - harkitse position vähentämistä")
        else:
            recommendations.append("Erittäin negatiivinen sentimentti - harkitse myyntiä")
        
        if sentiment_std > 0.5:
            recommendations.append("Korkea sentimentti-volatiliteetti - varovainen")
        
        return recommendations

# Esimerkki käytöstä
async def example_usage():
    """Esimerkki sosiaalisen median seurannan käytöstä"""
    async with SocialMediaMonitor() as monitor:
        # Lisää seurattavia kohteita
        monitor.add_tracking(
            symbols=["BTC", "ETH", "SOL"],
            hashtags=["#crypto", "#bitcoin", "#ethereum"],
            keywords=["moon", "pump", "bullish", "bearish"],
            influencers=["elonmusk", "VitalikButerin", "naval"]
        )
        
        # Lisää callbackit
        async def on_viral_post(post):
            print(f"🔥 Viral post: {post.platform} - {post.author} ({post.engagement} engagement)")
        
        async def on_sentiment_change(data):
            print(f"📊 Sentimentti muuttui: {data['change']:.3f}")
        
        monitor.add_callback('on_viral_post', on_viral_post)
        monitor.add_callback('on_sentiment_change', on_sentiment_change)
        
        # Aloita seuranta 60 sekunniksi
        try:
            await asyncio.wait_for(monitor.start_monitoring(), timeout=60.0)
        except asyncio.TimeoutError:
            print("⏰ 60 sekuntia kulunut")
        finally:
            monitor.stop_monitoring()
        
        # Hae analyysiraportti
        report = monitor.get_analysis_report()
        print(f"Analyysiraportti: {json.dumps(report, indent=2, default=str)}")
        
        # Hae sentimentti-yhteenveto
        sentiment_summary = monitor.get_sentiment_summary()
        print(f"Sentimentti-yhteenveto: {json.dumps(sentiment_summary, indent=2, default=str)}")

if __name__ == "__main__":
    asyncio.run(example_usage())
