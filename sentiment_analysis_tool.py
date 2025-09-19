"""
Sentimentti-analyysi työkalu sosiaalisen median datalle
Enhanced Ideation Crew v2.0 - Osa 1
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
from textblob import TextBlob
import numpy as np

class SentimentAnalysisTool:
    """Sentimentti-analyysi sosiaalisen median datalle"""
    
    def __init__(self):
        self.news_api_key = None  # Lisää News API key jos haluat
        self.reddit_client_id = None  # Lisää Reddit API credentials jos haluat
    
    def analyze_news_sentiment(self, symbol: str, days: int = 7) -> Dict:
        """Analysoi uutisten sentimenttiä symbolille"""
        try:
            # Simuloi uutisdata (korvaa oikealla News API:lla)
            mock_news = self._get_mock_news_data(symbol, days)
            
            sentiments = []
            for article in mock_news:
                sentiment = self._calculate_sentiment(article['title'] + ' ' + article['content'])
                sentiments.append({
                    'title': article['title'],
                    'sentiment': sentiment,
                    'date': article['date']
                })
            
            # Laske keskiarvo
            avg_sentiment = np.mean([s['sentiment'] for s in sentiments])
            
            return {
                'symbol': symbol,
                'period_days': days,
                'total_articles': len(sentiments),
                'average_sentiment': float(avg_sentiment),
                'sentiment_score': self._sentiment_to_score(avg_sentiment),
                'articles': sentiments[:5]  # Top 5 artikelia
            }
            
        except Exception as e:
            return {'error': f'Virhe uutisten sentimentti-analyysissä: {str(e)}'}
    
    def analyze_social_media_sentiment(self, symbol: str, platform: str = 'twitter') -> Dict:
        """Analysoi sosiaalisen median sentimenttiä"""
        try:
            if platform == 'twitter':
                return self._analyze_twitter_sentiment(symbol)
            elif platform == 'reddit':
                return self._analyze_reddit_sentiment(symbol)
            else:
                return {'error': f'Tuntematon alusta: {platform}'}
                
        except Exception as e:
            return {'error': f'Virhe sosiaalisen median analyysissä: {str(e)}'}
    
    def _get_mock_news_data(self, symbol: str, days: int) -> List[Dict]:
        """Simuloi uutisdata (korvaa oikealla News API:lla)"""
        mock_articles = [
            {
                'title': f'{symbol} Reports Strong Quarterly Earnings',
                'content': f'{symbol} has exceeded analyst expectations with robust revenue growth and improved margins.',
                'date': datetime.now() - timedelta(days=1)
            },
            {
                'title': f'{symbol} Faces Market Volatility',
                'content': f'Recent market conditions have created challenges for {symbol} stock performance.',
                'date': datetime.now() - timedelta(days=2)
            },
            {
                'title': f'{symbol} Announces New Product Launch',
                'content': f'{symbol} is set to launch innovative products that could drive future growth.',
                'date': datetime.now() - timedelta(days=3)
            }
        ]
        return mock_articles
    
    def _analyze_twitter_sentiment(self, symbol: str) -> Dict:
        """Analysoi Twitter-sentimenttiä (simuloi)"""
        # Simuloi Twitter-data
        mock_tweets = [
            f"{symbol} is looking bullish today! 🚀",
            f"Not sure about {symbol} right now, seems overvalued",
            f"{symbol} earnings were amazing!",
            f"{symbol} stock is too volatile for my taste",
            f"Long term bullish on {symbol}"
        ]
        
        sentiments = []
        for tweet in mock_tweets:
            sentiment = self._calculate_sentiment(tweet)
            sentiments.append(sentiment)
        
        avg_sentiment = np.mean(sentiments)
        
        return {
            'platform': 'twitter',
            'symbol': symbol,
            'total_tweets': len(mock_tweets),
            'average_sentiment': float(avg_sentiment),
            'sentiment_score': self._sentiment_to_score(avg_sentiment),
            'sample_tweets': mock_tweets[:3]
        }
    
    def _analyze_reddit_sentiment(self, symbol: str) -> Dict:
        """Analysoi Reddit-sentimenttiä (simuloi)"""
        # Simuloi Reddit-data
        mock_posts = [
            f"DD: Why {symbol} is undervalued and ready to moon",
            f"{symbol} earnings call was disappointing",
            f"Technical analysis shows {symbol} breaking resistance",
            f"{symbol} management team is solid, long term hold",
            f"Market manipulation affecting {symbol} price"
        ]
        
        sentiments = []
        for post in mock_posts:
            sentiment = self._calculate_sentiment(post)
            sentiments.append(sentiment)
        
        avg_sentiment = np.mean(sentiments)
        
        return {
            'platform': 'reddit',
            'symbol': symbol,
            'total_posts': len(mock_posts),
            'average_sentiment': float(avg_sentiment),
            'sentiment_score': self._sentiment_to_score(avg_sentiment),
            'sample_posts': mock_posts[:3]
        }
    
    def _calculate_sentiment(self, text: str) -> float:
        """Laske sentimentti-tekstille käyttäen TextBlob"""
        try:
            blob = TextBlob(text)
            return blob.sentiment.polarity  # -1 (negatiivinen) to 1 (positiivinen)
        except:
            return 0.0
    
    def _sentiment_to_score(self, sentiment: float) -> str:
        """Muunna sentimentti-luku selkeäksi arvioksi"""
        if sentiment > 0.3:
            return "Erittäin positiivinen"
        elif sentiment > 0.1:
            return "Positiivinen"
        elif sentiment > -0.1:
            return "Neutraali"
        elif sentiment > -0.3:
            return "Negatiivinen"
        else:
            return "Erittäin negatiivinen"
    
    def get_market_sentiment_summary(self, symbols: List[str]) -> Dict:
        """Hae markkinoiden sentimentti-yhteenveto useille symboleille"""
        try:
            results = {}
            total_sentiment = 0
            
            for symbol in symbols:
                news_sentiment = self.analyze_news_sentiment(symbol, days=3)
                social_sentiment = self.analyze_social_media_sentiment(symbol)
                
                if 'error' not in news_sentiment and 'error' not in social_sentiment:
                    combined_sentiment = (news_sentiment['average_sentiment'] + 
                                        social_sentiment['average_sentiment']) / 2
                    results[symbol] = {
                        'news_sentiment': news_sentiment['sentiment_score'],
                        'social_sentiment': social_sentiment['sentiment_score'],
                        'combined_sentiment': self._sentiment_to_score(combined_sentiment),
                        'sentiment_value': float(combined_sentiment)
                    }
                    total_sentiment += combined_sentiment
            
            avg_market_sentiment = total_sentiment / len(symbols) if symbols else 0
            
            return {
                'market_overview': {
                    'total_symbols': len(symbols),
                    'average_market_sentiment': self._sentiment_to_score(avg_market_sentiment),
                    'sentiment_value': float(avg_market_sentiment)
                },
                'individual_sentiments': results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'Virhe markkinoiden sentimentti-yhteenvedossa: {str(e)}'}

# Testaa työkalu
if __name__ == "__main__":
    sentiment_tool = SentimentAnalysisTool()
    
    # Testaa uutisten sentimentti
    print("=== UUTISTEN SENTIMENTTI ===")
    news_result = sentiment_tool.analyze_news_sentiment("AAPL", days=7)
    print(json.dumps(news_result, indent=2, default=str))
    
    # Testaa sosiaalisen median sentimentti
    print("\n=== SOSIAALISEN MEDIAN SENTIMENTTI ===")
    social_result = sentiment_tool.analyze_social_media_sentiment("AAPL", "twitter")
    print(json.dumps(social_result, indent=2, default=str))
    
    # Testaa markkinoiden yhteenveto
    print("\n=== MARKKINOIDEN SENTIMENTTI-YHTEENVETO ===")
    market_result = sentiment_tool.get_market_sentiment_summary(["AAPL", "MSFT", "GOOGL"])
    print(json.dumps(market_result, indent=2, default=str))


