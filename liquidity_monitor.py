"""
Likviditeettiseuranta - Riskienhallintasuositusten Implementointi
==============================================================

Tämä moduuli sisältää työkalut likviditeettiriskin seurantaan ja hallintaan.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class LiquidityMonitor:
    """Likviditeettiseuranta -työkalu"""
    
    def __init__(self):
        self.liquidity_thresholds = {
            "high": 0.8,      # Korkea likviditeetti
            "moderate": 0.5,  # Kohtalainen likviditeetti
            "low": 0.2        # Matala likviditeetti
        }
    
    def analyze_liquidity(self, symbols: List[str], period: str = "3mo") -> Dict:
        """
        Analysoi likviditeettiä osakkeille
        
        Args:
            symbols: Osakkeiden symbolit
            period: Aikajakso analyysille
        
        Returns:
            Dict sisältäen likviditeettianalyysin
        """
        try:
            results = {}
            
            for symbol in symbols:
                symbol_analysis = self._analyze_symbol_liquidity(symbol, period)
                results[symbol] = symbol_analysis
            
            # Laske portfolio-likviditeetti
            portfolio_liquidity = self._calculate_portfolio_liquidity(results)
            
            # Anna suositukset
            recommendations = self._get_liquidity_recommendations(results, portfolio_liquidity)
            
            return {
                "individual_analysis": results,
                "portfolio_liquidity": portfolio_liquidity,
                "recommendations": recommendations,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Virhe likviditeettianalyysissä: {str(e)}"}
    
    def _analyze_symbol_liquidity(self, symbol: str, period: str) -> Dict:
        """Analysoi yksittäisen osakkeen likviditeettiä"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                return {"error": f"Ei dataa symbolille {symbol}"}
            
            # Laske volyymimittarit
            volume_metrics = self._calculate_volume_metrics(hist)
            
            # Laske spread-mittarit (arvio)
            spread_metrics = self._estimate_spread_metrics(hist)
            
            # Laske likviditeettipisteet
            liquidity_score = self._calculate_liquidity_score(volume_metrics, spread_metrics)
            
            # Määritä likviditeetin taso
            liquidity_level = self._get_liquidity_level(liquidity_score)
            
            # Laske markkinavaikutuskustannukset
            market_impact = self._estimate_market_impact(volume_metrics, hist)
            
            return {
                "symbol": symbol,
                "liquidity_score": liquidity_score,
                "liquidity_level": liquidity_level,
                "volume_metrics": volume_metrics,
                "spread_metrics": spread_metrics,
                "market_impact": market_impact,
                "recommendations": self._get_symbol_recommendations(liquidity_score, market_impact)
            }
            
        except Exception as e:
            return {"error": f"Virhe analysoitaessa {symbol}: {str(e)}"}
    
    def _calculate_volume_metrics(self, hist: pd.DataFrame) -> Dict:
        """Laske volyymimittarit"""
        volume = hist['Volume']
        price = hist['Close']
        
        # Laske dollar-volyymi
        dollar_volume = (volume * price).mean()
        
        # Laske volyymin volatiliteetti
        volume_volatility = volume.pct_change().std()
        
        # Laske volyymin trendi
        volume_trend = self._calculate_trend(volume)
        
        # Laske keskiarvo volyymi
        avg_volume = volume.mean()
        
        # Laske volyymin johdonmukaisuus
        volume_consistency = 1 - (volume.std() / volume.mean())
        
        return {
            "dollar_volume": dollar_volume,
            "avg_volume": avg_volume,
            "volume_volatility": volume_volatility,
            "volume_trend": volume_trend,
            "volume_consistency": volume_consistency
        }
    
    def _estimate_spread_metrics(self, hist: pd.DataFrame) -> Dict:
        """Arvioi spread-mittarit (koska emme voi saada tarkkoja bid-ask spreadejä)"""
        # Käytä high-low spreadiä likviditeetin indikaattorina
        daily_spread = (hist['High'] - hist['Low']) / hist['Close']
        
        avg_spread = daily_spread.mean()
        spread_volatility = daily_spread.std()
        
        # Arvioi bid-ask spread (yksinkertainen estimaatti)
        estimated_bid_ask_spread = avg_spread * 0.1  # Oletetaan 10% päivittäisestä spreadistä
        
        return {
            "avg_daily_spread": avg_spread,
            "spread_volatility": spread_volatility,
            "estimated_bid_ask_spread": estimated_bid_ask_spread
        }
    
    def _calculate_liquidity_score(self, volume_metrics: Dict, spread_metrics: Dict) -> float:
        """Laske likviditeettipisteet (0-1, 1 = paras likviditeetti)"""
        # Volyymipisteet (0-0.6)
        volume_score = min(0.6, volume_metrics["dollar_volume"] / 10000000)  # 10M$ = täydet pisteet
        
        # Spread-pisteet (0-0.4)
        spread_score = max(0, 0.4 - spread_metrics["estimated_bid_ask_spread"] * 100)
        
        # Johdonmukaisuuspisteet
        consistency_score = volume_metrics["volume_consistency"] * 0.2
        
        total_score = volume_score + spread_score + consistency_score
        return min(1.0, max(0.0, total_score))
    
    def _get_liquidity_level(self, liquidity_score: float) -> str:
        """Määritä likviditeetin taso"""
        if liquidity_score >= self.liquidity_thresholds["high"]:
            return "Korkea"
        elif liquidity_score >= self.liquidity_thresholds["moderate"]:
            return "Kohtalainen"
        else:
            return "Matala"
    
    def _estimate_market_impact(self, volume_metrics: Dict, hist: pd.DataFrame) -> Dict:
        """Arvioi markkinavaikutuskustannukset"""
        avg_volume = volume_metrics["avg_volume"]
        dollar_volume = volume_metrics["dollar_volume"]
        
        # Arvioi eri position kokoille markkinavaikutus
        position_sizes = [1000, 5000, 10000, 50000, 100000]  # Osakkeita
        
        market_impacts = {}
        for size in position_sizes:
            # Yksinkertainen estimaatti: position koko / keskiarvo volyymi
            impact_ratio = size / avg_volume
            
            # Arvioi hintavaikutus (0.1% per 1% volyymista)
            price_impact = impact_ratio * 0.001
            
            # Arvioi toteutusaika (päivinä)
            execution_days = max(1, size / (avg_volume * 0.1))  # 10% päivittäisestä volyymista
            
            market_impacts[f"{size}_shares"] = {
                "price_impact_percent": price_impact * 100,
                "execution_days": execution_days,
                "impact_level": self._get_impact_level(price_impact)
            }
        
        return market_impacts
    
    def _get_impact_level(self, price_impact: float) -> str:
        """Määritä markkinavaikutuksen taso"""
        if price_impact < 0.001:  # < 0.1%
            return "Matala"
        elif price_impact < 0.005:  # < 0.5%
            return "Kohtalainen"
        else:
            return "Korkea"
    
    def _calculate_trend(self, series: pd.Series) -> float:
        """Laske trendi (positiivinen = nouseva, negatiivinen = laskeva)"""
        x = np.arange(len(series))
        y = series.values
        slope = np.polyfit(x, y, 1)[0]
        return slope / series.mean()  # Normalisoi keskiarvolla
    
    def _calculate_portfolio_liquidity(self, individual_results: Dict) -> Dict:
        """Laske portfolio-likviditeetti"""
        valid_results = {k: v for k, v in individual_results.items() if "error" not in v}
        
        if not valid_results:
            return {"error": "Ei validia dataa portfolio-likviditeetin laskemiseen"}
        
        # Laske painotettu keskiarvo likviditeettipisteistä
        liquidity_scores = [result["liquidity_score"] for result in valid_results.values()]
        avg_liquidity_score = np.mean(liquidity_scores)
        
        # Laske portfolio-likviditeetin taso
        portfolio_liquidity_level = self._get_liquidity_level(avg_liquidity_score)
        
        # Laske hajautus
        liquidity_volatility = np.std(liquidity_scores)
        
        # Laske huonoimman osakkeen likviditeetti
        min_liquidity = min(liquidity_scores)
        worst_symbol = min(valid_results.keys(), key=lambda k: valid_results[k]["liquidity_score"])
        
        return {
            "average_liquidity_score": avg_liquidity_score,
            "liquidity_level": portfolio_liquidity_level,
            "liquidity_volatility": liquidity_volatility,
            "min_liquidity_score": min_liquidity,
            "worst_liquidity_symbol": worst_symbol,
            "total_symbols": len(valid_results)
        }
    
    def _get_liquidity_recommendations(self, individual_results: Dict, portfolio_liquidity: Dict) -> List[str]:
        """Anna suositukset likviditeetin perusteella"""
        recommendations = []
        
        if "error" in portfolio_liquidity:
            return ["Virhe portfolio-likviditeetin laskennassa"]
        
        # Portfolio-tason suositukset
        portfolio_level = portfolio_liquidity["liquidity_level"]
        portfolio_score = portfolio_liquidity["average_liquidity_score"]
        
        if portfolio_level == "Matala":
            recommendations.extend([
                "VAROITUS: Matala portfolio-likviditeetti",
                "Harkitse likvidimpien osakkeiden lisäämistä",
                "Vähennä position kokoja volatiliteettikausina",
                "Suunnittele toteutukset huolellisemmin"
            ])
        elif portfolio_level == "Kohtalainen":
            recommendations.extend([
                "Kohtalainen portfolio-likviditeetti",
                "Seuraa likviditeettiä tarkemmin",
                "Harkitse likvidimpien vaihtoehtojen lisäämistä"
            ])
        else:
            recommendations.append("Hyvä portfolio-likviditeetti - jatka nykyistä strategiaa")
        
        # Yksittäisten osakkeiden suositukset
        low_liquidity_symbols = []
        for symbol, result in individual_results.items():
            if "error" not in result and result["liquidity_level"] == "Matala":
                low_liquidity_symbols.append(symbol)
        
        if low_liquidity_symbols:
            recommendations.append(f"Matala likviditeetti: {', '.join(low_liquidity_symbols)}")
            recommendations.append("Harkitse näiden osakkeiden korvaamista likvidimmillä vaihtoehdoilla")
        
        # Markkinavaikutuskustannusten suositukset
        high_impact_symbols = []
        for symbol, result in individual_results.items():
            if "error" not in result:
                market_impact = result["market_impact"]
                # Tarkista 10000 osakkeen markkinavaikutus
                if "10000_shares" in market_impact:
                    impact = market_impact["10000_shares"]["impact_level"]
                    if impact == "Korkea":
                        high_impact_symbols.append(symbol)
        
        if high_impact_symbols:
            recommendations.append(f"Korkea markkinavaikutus: {', '.join(high_impact_symbols)}")
            recommendations.append("Jaa suuret toteutukset useammalle päivälle")
        
        return recommendations
    
    def _get_symbol_recommendations(self, liquidity_score: float, market_impact: Dict) -> List[str]:
        """Anna suositukset yksittäiselle osakkeelle"""
        recommendations = []
        
        if liquidity_score < self.liquidity_thresholds["low"]:
            recommendations.extend([
                "VAROITUS: Matala likviditeetti",
                "Vähennä position kokoja",
                "Jaa toteutukset useammalle päivälle",
                "Harkitse korvaamista likvidimmällä vaihtoehdolla"
            ])
        elif liquidity_score < self.liquidity_thresholds["moderate"]:
            recommendations.extend([
                "Kohtalainen likviditeetti",
                "Seuraa volyymiä tarkemmin",
                "Harkitse pienempiä position kokoja"
            ])
        else:
            recommendations.append("Hyvä likviditeetti - normaali kauppa OK")
        
        # Markkinavaikutuskustannusten suositukset
        if "10000_shares" in market_impact:
            impact_level = market_impact["10000_shares"]["impact_level"]
            if impact_level == "Korkea":
                recommendations.append("Korkea markkinavaikutus - jaa suuret toteutukset")
        
        return recommendations

def main():
    """Esimerkki käytöstä"""
    print("💧 Likviditeettiseuranta - Esimerkki käytöstä")
    print("=" * 50)
    
    monitor = LiquidityMonitor()
    
    # Analysoi likviditeettiä
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
    results = monitor.analyze_liquidity(symbols)
    
    if "error" not in results:
        print(f"\nPortfolio-likviditeetti: {results['portfolio_liquidity']['liquidity_level']}")
        print(f"Likviditeettipisteet: {results['portfolio_liquidity']['average_liquidity_score']:.3f}")
        
        print("\nYksittäisten osakkeiden likviditeetti:")
        for symbol, analysis in results['individual_analysis'].items():
            if "error" not in analysis:
                print(f"{symbol}: {analysis['liquidity_level']} ({analysis['liquidity_score']:.3f})")
        
        print("\nSuositukset:")
        for rec in results['recommendations'][:5]:
            print(f"- {rec}")
    else:
        print(f"Virhe: {results['error']}")

if __name__ == "__main__":
    main()
