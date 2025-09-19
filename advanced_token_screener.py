"""
Advanced Token Screener - Parannettu token-screening algoritmi
Perustuu kattavaan tutkimukseen tehokkaimmista token-screening menetelmistä
"""

import asyncio
import aiohttp
import json
import logging
import time
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Tuple
import random
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AdvancedToken:
    """Parannettu token dataclass"""
    symbol: str
    name: str
    address: str
    price: float
    market_cap: float
    volume_24h: float
    price_change_24h: float
    price_change_7d: float
    liquidity: float
    holders: int
    fresh_holders_1d: int
    fresh_holders_7d: int
    age_minutes: int
    social_score: float
    technical_score: float
    momentum_score: float
    risk_score: float
    entry_score: float
    overall_score: float
    timestamp: str
    # Oikeat markkina tiedot
    real_price: float
    real_volume: float
    real_liquidity: float
    dex: str
    pair_address: str
    # Uudet kentät
    volume_spike: float
    holder_growth: float
    liquidity_ratio: float
    price_volatility: float
    social_mentions: int
    influencer_mentions: int
    community_growth: float
    development_activity: float
    audit_status: str
    rug_pull_risk: float

class AdvancedTokenScreener:
    """Parannettu token screener optimoiduilla kriteereillä"""
    
    def __init__(self):
        self.session = None
        self.screening_criteria = self._initialize_criteria()
        self.risk_weights = self._initialize_risk_weights()
        
    def _initialize_criteria(self) -> Dict:
        """Alusta optimoidut screening-kriteerit"""
        return {
            # Ultra-Fresh Token Hunting
            "ultra_fresh": {
                "age_minutes": (1, 10),
                "market_cap": (1000, 50000),
                "volume_24h": (1000, 100000),
                "price_change_24h": (20, 500),
                "social_score": (0.6, 1.0),
                "liquidity": (10000, 100000),
                "holders": (50, 1000)
            },
            # Volume Spike Detection
            "volume_spike": {
                "volume_spike": (300, 1000),  # % increase
                "price_momentum": (50, 200),
                "liquidity": (50000, 500000),
                "holder_growth": (100, 500),
                "social_mentions": (100, 1000)
            },
            # Social Buzz Strategy
            "social_buzz": {
                "social_score": (0.7, 1.0),
                "social_mentions": (1000, 10000),
                "influencer_mentions": (10, 100),
                "community_growth": (50, 200),
                "development_activity": (0.8, 1.0)
            },
            # Low Risk High Potential
            "low_risk": {
                "risk_score": (0.0, 0.3),
                "liquidity_ratio": (0.1, 0.5),
                "audit_status": "verified",
                "rug_pull_risk": (0.0, 0.2),
                "development_activity": (0.6, 1.0)
            }
        }
    
    def _initialize_risk_weights(self) -> Dict:
        """Alusta risk-painot"""
        return {
            "age_risk": 0.15,
            "liquidity_risk": 0.25,
            "volume_risk": 0.20,
            "social_risk": 0.15,
            "development_risk": 0.15,
            "rug_pull_risk": 0.10
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def calculate_advanced_entry_score(self, token: AdvancedToken) -> float:
        """Laske edistynyt entry score optimoiduilla kriteereillä"""
        score = 0.0
        
        # 1. Age Bonus (Ultra-fresh tokens)
        if 1 <= token.age_minutes <= 5:
            score += 0.30  # Paras range
        elif 6 <= token.age_minutes <= 10:
            score += 0.25
        elif 11 <= token.age_minutes <= 30:
            score += 0.15
        elif 31 <= token.age_minutes <= 60:
            score += 0.10
        
        # 2. Market Cap Optimization
        if 1000 <= token.market_cap <= 10000:
            score += 0.30  # Sweet spot
        elif 10000 <= token.market_cap <= 50000:
            score += 0.25
        elif 50000 <= token.market_cap <= 200000:
            score += 0.20
        elif 200000 <= token.market_cap <= 500000:
            score += 0.15
        
        # 3. Volume Analysis (Enhanced)
        if token.volume_24h > 50000:
            score += 0.25
        elif token.volume_24h > 20000:
            score += 0.20
        elif token.volume_24h > 10000:
            score += 0.15
        elif token.volume_24h > 5000:
            score += 0.10
        
        # 4. Volume Spike Detection
        if token.volume_spike > 500:
            score += 0.20
        elif token.volume_spike > 300:
            score += 0.15
        elif token.volume_spike > 200:
            score += 0.10
        
        # 5. Price Momentum (Enhanced)
        if token.price_change_24h > 100:
            score += 0.25
        elif token.price_change_24h > 50:
            score += 0.20
        elif token.price_change_24h > 30:
            score += 0.15
        elif token.price_change_24h > 15:
            score += 0.10
        
        # 6. Social Score (Enhanced)
        if token.social_score > 0.8:
            score += 0.20
        elif token.social_score > 0.6:
            score += 0.15
        elif token.social_score > 0.4:
            score += 0.10
        
        # 7. Social Mentions
        if token.social_mentions > 5000:
            score += 0.15
        elif token.social_mentions > 2000:
            score += 0.12
        elif token.social_mentions > 1000:
            score += 0.10
        elif token.social_mentions > 500:
            score += 0.08
        
        # 8. Influencer Mentions
        if token.influencer_mentions > 50:
            score += 0.15
        elif token.influencer_mentions > 20:
            score += 0.12
        elif token.influencer_mentions > 10:
            score += 0.10
        
        # 9. Liquidity Analysis
        if token.liquidity > 100000:
            score += 0.15
        elif token.liquidity > 50000:
            score += 0.12
        elif token.liquidity > 20000:
            score += 0.10
        elif token.liquidity > 10000:
            score += 0.08
        
        # 10. Holder Growth
        if token.holder_growth > 200:
            score += 0.15
        elif token.holder_growth > 100:
            score += 0.12
        elif token.holder_growth > 50:
            score += 0.10
        
        # 11. Community Growth
        if token.community_growth > 100:
            score += 0.12
        elif token.community_growth > 50:
            score += 0.10
        elif token.community_growth > 25:
            score += 0.08
        
        # 12. Development Activity
        if token.development_activity > 0.8:
            score += 0.10
        elif token.development_activity > 0.6:
            score += 0.08
        elif token.development_activity > 0.4:
            score += 0.05
        
        return min(score, 1.0)
    
    def calculate_advanced_risk_score(self, token: AdvancedToken) -> float:
        """Laske edistynyt risk score"""
        risk = 0.0
        
        # Age Risk (uudempi = riskialtisempi)
        if token.age_minutes < 5:
            risk += 0.20 * self.risk_weights["age_risk"]
        elif token.age_minutes < 15:
            risk += 0.15 * self.risk_weights["age_risk"]
        elif token.age_minutes < 30:
            risk += 0.10 * self.risk_weights["age_risk"]
        
        # Liquidity Risk
        if token.liquidity < 5000:
            risk += 0.40 * self.risk_weights["liquidity_risk"]
        elif token.liquidity < 20000:
            risk += 0.30 * self.risk_weights["liquidity_risk"]
        elif token.liquidity < 50000:
            risk += 0.20 * self.risk_weights["liquidity_risk"]
        
        # Volume Risk
        if token.volume_24h < 1000:
            risk += 0.35 * self.risk_weights["volume_risk"]
        elif token.volume_24h < 5000:
            risk += 0.25 * self.risk_weights["volume_risk"]
        elif token.volume_24h < 20000:
            risk += 0.15 * self.risk_weights["volume_risk"]
        
        # Social Risk
        if token.social_score < 0.2:
            risk += 0.30 * self.risk_weights["social_risk"]
        elif token.social_score < 0.4:
            risk += 0.20 * self.risk_weights["social_risk"]
        elif token.social_score < 0.6:
            risk += 0.10 * self.risk_weights["social_risk"]
        
        # Development Risk
        if token.development_activity < 0.3:
            risk += 0.25 * self.risk_weights["development_risk"]
        elif token.development_activity < 0.5:
            risk += 0.15 * self.risk_weights["development_risk"]
        elif token.development_activity < 0.7:
            risk += 0.10 * self.risk_weights["development_risk"]
        
        # Rug Pull Risk
        risk += token.rug_pull_risk * self.risk_weights["rug_pull_risk"]
        
        return min(risk, 1.0)
    
    def calculate_momentum_score(self, token: AdvancedToken) -> float:
        """Laske momentum score"""
        momentum = 0.0
        
        # Price momentum
        if token.price_change_24h > 100:
            momentum += 0.30
        elif token.price_change_24h > 50:
            momentum += 0.25
        elif token.price_change_24h > 30:
            momentum += 0.20
        elif token.price_change_24h > 15:
            momentum += 0.15
        
        # Volume momentum
        if token.volume_spike > 500:
            momentum += 0.25
        elif token.volume_spike > 300:
            momentum += 0.20
        elif token.volume_spike > 200:
            momentum += 0.15
        
        # Social momentum
        if token.social_mentions > 5000:
            momentum += 0.20
        elif token.social_mentions > 2000:
            momentum += 0.15
        elif token.social_mentions > 1000:
            momentum += 0.10
        
        # Community momentum
        if token.community_growth > 100:
            momentum += 0.15
        elif token.community_growth > 50:
            momentum += 0.10
        elif token.community_growth > 25:
            momentum += 0.05
        
        # Holder momentum
        if token.holder_growth > 200:
            momentum += 0.10
        elif token.holder_growth > 100:
            momentum += 0.08
        elif token.holder_growth > 50:
            momentum += 0.05
        
        return min(momentum, 1.0)
    
    def calculate_overall_score(self, token: AdvancedToken) -> float:
        """Laske kokonaisscore"""
        entry_score = token.entry_score
        risk_score = token.risk_score
        momentum_score = token.momentum_score
        
        # Painotetut skorit
        overall = (
            entry_score * 0.40 +      # Entry potential
            (1 - risk_score) * 0.35 + # Risk-adjusted return
            momentum_score * 0.25     # Momentum
        )
        
        return min(overall, 1.0)
    
    def screen_tokens_by_strategy(self, tokens: List[AdvancedToken], strategy: str) -> List[AdvancedToken]:
        """Seuloa tokeneita strategian mukaan"""
        if strategy not in self.screening_criteria:
            logger.warning(f"Tuntematon strategia: {strategy}")
            return tokens
        
        criteria = self.screening_criteria[strategy]
        filtered_tokens = []
        
        for token in tokens:
            if self._matches_criteria(token, criteria):
                filtered_tokens.append(token)
        
        # Järjestä overall score:n mukaan
        filtered_tokens.sort(key=lambda x: x.overall_score, reverse=True)
        
        return filtered_tokens
    
    def _matches_criteria(self, token: AdvancedToken, criteria: Dict) -> bool:
        """Tarkista täyttääkö token kriteerit"""
        for key, value_range in criteria.items():
            if hasattr(token, key):
                token_value = getattr(token, key)
                
                if isinstance(value_range, tuple):
                    if not (value_range[0] <= token_value <= value_range[1]):
                        return False
                elif isinstance(value_range, str):
                    if token_value != value_range:
                        return False
                else:
                    if token_value < value_range:
                        return False
        
        return True
    
    def analyze_token_portfolio_fit(self, token: AdvancedToken, portfolio: Dict) -> Dict:
        """Analysoi sopiiko token portfolioon"""
        analysis = {
            "fits_portfolio": True,
            "reasons": [],
            "warnings": [],
            "recommended_position_size": 0.0
        }
        
        # Tarkista portfolio heat
        portfolio_heat = portfolio.get("heat", 0.0)
        if portfolio_heat > 0.8:
            analysis["warnings"].append("Portfolio heat liian korkea")
            analysis["recommended_position_size"] = 0.01  # Pieni position
        
        # Tarkista risk-taso
        if token.risk_score > 0.7:
            analysis["warnings"].append("Korkea riski")
            analysis["recommended_position_size"] = min(analysis["recommended_position_size"], 0.02)
        
        # Tarkista likviditeetti
        if token.liquidity < 10000:
            analysis["warnings"].append("Matala likviditeetti")
            analysis["recommended_position_size"] = min(analysis["recommended_position_size"], 0.01)
        
        # Laske suositeltu position koko
        if not analysis["recommended_position_size"]:
            # Base position size
            base_size = 0.05
            
            # Adjust by risk
            risk_adjustment = 1 - token.risk_score
            base_size *= risk_adjustment
            
            # Adjust by overall score
            score_adjustment = token.overall_score
            base_size *= score_adjustment
            
            # Adjust by portfolio heat
            heat_adjustment = 1 - portfolio_heat
            base_size *= heat_adjustment
            
            analysis["recommended_position_size"] = max(0.01, min(base_size, 0.10))
        
        # Positiiviset syyt
        if token.overall_score > 0.8:
            analysis["reasons"].append("Erinomainen kokonaisscore")
        if token.risk_score < 0.3:
            analysis["reasons"].append("Matala riski")
        if token.momentum_score > 0.7:
            analysis["reasons"].append("Vahva momentum")
        if token.liquidity > 50000:
            analysis["reasons"].append("Hyvä likviditeetti")
        
        return analysis
    
    def generate_screening_report(self, tokens: List[AdvancedToken]) -> Dict:
        """Generoi screening-raportti"""
        if not tokens:
            return {"error": "Ei tokeneita analysoitavaksi"}
        
        # Laske tilastot
        total_tokens = len(tokens)
        avg_entry_score = np.mean([t.entry_score for t in tokens])
        avg_risk_score = np.mean([t.risk_score for t in tokens])
        avg_momentum_score = np.mean([t.momentum_score for t in tokens])
        avg_overall_score = np.mean([t.overall_score for t in tokens])
        
        # Top performers
        top_tokens = sorted(tokens, key=lambda x: x.overall_score, reverse=True)[:10]
        
        # Risk distribution
        low_risk = len([t for t in tokens if t.risk_score < 0.3])
        medium_risk = len([t for t in tokens if 0.3 <= t.risk_score < 0.7])
        high_risk = len([t for t in tokens if t.risk_score >= 0.7])
        
        # Age distribution
        ultra_fresh = len([t for t in tokens if t.age_minutes <= 10])
        fresh = len([t for t in tokens if 10 < t.age_minutes <= 60])
        mature = len([t for t in tokens if t.age_minutes > 60])
        
        return {
            "summary": {
                "total_tokens": total_tokens,
                "avg_entry_score": round(avg_entry_score, 3),
                "avg_risk_score": round(avg_risk_score, 3),
                "avg_momentum_score": round(avg_momentum_score, 3),
                "avg_overall_score": round(avg_overall_score, 3)
            },
            "top_performers": [
                {
                    "symbol": t.symbol,
                    "overall_score": round(t.overall_score, 3),
                    "entry_score": round(t.entry_score, 3),
                    "risk_score": round(t.risk_score, 3),
                    "momentum_score": round(t.momentum_score, 3),
                    "age_minutes": t.age_minutes,
                    "market_cap": t.market_cap
                }
                for t in top_tokens
            ],
            "risk_distribution": {
                "low_risk": low_risk,
                "medium_risk": medium_risk,
                "high_risk": high_risk
            },
            "age_distribution": {
                "ultra_fresh": ultra_fresh,
                "fresh": fresh,
                "mature": mature
            },
            "timestamp": datetime.now().isoformat()
        }

# Esimerkki käytöstä
async def example_usage():
    """Esimerkki advanced token screenerin käytöstä"""
    async with AdvancedTokenScreener() as screener:
        # Simuloi tokenit
        tokens = []
        for i in range(10):
            token = AdvancedToken(
                symbol=f"TOKEN{i}",
                name=f"Token {i}",
                address=f"address_{i}",
                price=random.uniform(0.001, 1.0),
                market_cap=random.uniform(1000, 1000000),
                volume_24h=random.uniform(1000, 100000),
                price_change_24h=random.uniform(-50, 200),
                price_change_7d=random.uniform(-80, 500),
                liquidity=random.uniform(10000, 500000),
                holders=random.randint(50, 5000),
                fresh_holders_1d=random.randint(5, 500),
                fresh_holders_7d=random.randint(20, 2000),
                age_minutes=random.randint(1, 120),
                social_score=random.uniform(0.0, 1.0),
                technical_score=0.0,
                momentum_score=0.0,
                risk_score=0.0,
                entry_score=0.0,
                overall_score=0.0,
                timestamp=datetime.now().isoformat(),
                real_price=0.0,
                real_volume=0.0,
                real_liquidity=0.0,
                dex="Test",
                pair_address="",
                volume_spike=random.uniform(100, 1000),
                holder_growth=random.uniform(10, 300),
                liquidity_ratio=random.uniform(0.1, 0.8),
                price_volatility=random.uniform(0.1, 2.0),
                social_mentions=random.randint(100, 10000),
                influencer_mentions=random.randint(5, 100),
                community_growth=random.uniform(10, 200),
                development_activity=random.uniform(0.0, 1.0),
                audit_status="unverified",
                rug_pull_risk=random.uniform(0.0, 0.5)
            )
            
            # Laske skorit
            token.entry_score = screener.calculate_advanced_entry_score(token)
            token.risk_score = screener.calculate_advanced_risk_score(token)
            token.momentum_score = screener.calculate_momentum_score(token)
            token.overall_score = screener.calculate_overall_score(token)
            
            tokens.append(token)
        
        # Seuloa ultra-fresh strategialla
        ultra_fresh_tokens = screener.screen_tokens_by_strategy(tokens, "ultra_fresh")
        print(f"Ultra-fresh tokeneita: {len(ultra_fresh_tokens)}")
        
        # Generoi raportti
        report = screener.generate_screening_report(tokens)
        print(f"Screening raportti: {json.dumps(report, indent=2)}")

if __name__ == "__main__":
    asyncio.run(example_usage())
