"""
Riskienhallinta Dashboard - Suositusten Implementointi
===================================================

Pääohjelma, joka yhdistää kaikki riskienhallintatyökalut ja tarjoaa
käyttäjäystävällisen käyttöliittymän suositusten toteuttamiseen.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

# Tuo riskienhallintatyökalut
from risk_management_tools import PositionSizingCalculator, StressTestingTool, CorrelationAnalyzer
from liquidity_monitor import LiquidityMonitor
from model_evaluator import ModelEvaluator

class RiskManagementDashboard:
    """Riskienhallinta Dashboard - pääohjelma"""
    
    def __init__(self, portfolio_value: float = 100000):
        """
        Args:
            portfolio_value: Portfolio kokonaisarvo
        """
        self.portfolio_value = portfolio_value
        self.position_calc = PositionSizingCalculator(portfolio_value)
        self.stress_tool = StressTestingTool()
        self.corr_analyzer = CorrelationAnalyzer()
        self.liquidity_monitor = LiquidityMonitor()
        self.model_evaluator = ModelEvaluator()
        
        # Tallenna tulokset
        self.results = {}
    
    def run_comprehensive_analysis(self, symbols: List[str], 
                                 weights: Optional[List[float]] = None) -> Dict:
        """
        Suorita kattava riskianalyysi
        
        Args:
            symbols: Osakkeiden symbolit
            weights: Painotukset (jos None, käytä yhtä suuria)
        
        Returns:
            Dict sisältäen kaikki analyysit
        """
        print("🛡️ Kattava Riskianalyysi")
        print("=" * 50)
        
        if weights is None:
            weights = [1.0 / len(symbols)] * len(symbols)
        
        # 1. Position Sizing -analyysi
        print("\n1. POSITION SIZING -ANALYYSI")
        print("-" * 30)
        position_analysis = self._analyze_position_sizing(symbols)
        
        # 2. Stress Testing
        print("\n2. STRESS TESTING")
        print("-" * 30)
        stress_analysis = self._analyze_stress_testing(symbols, weights)
        
        # 3. Korrelaatioanalyysi
        print("\n3. KORRELAATIOANALYYSI")
        print("-" * 30)
        correlation_analysis = self._analyze_correlations(symbols)
        
        # 4. Likviditeettianalyysi
        print("\n4. LIKVIDITEETTIANALYYSI")
        print("-" * 30)
        liquidity_analysis = self._analyze_liquidity(symbols)
        
        # 5. Mallin arviointi
        print("\n5. MALLIN ARVIOINTI")
        print("-" * 30)
        model_analysis = self._analyze_models(symbols)
        
        # Yhdistä tulokset
        comprehensive_results = {
            "timestamp": datetime.now().isoformat(),
            "portfolio_value": self.portfolio_value,
            "symbols": symbols,
            "weights": weights,
            "position_analysis": position_analysis,
            "stress_analysis": stress_analysis,
            "correlation_analysis": correlation_analysis,
            "liquidity_analysis": liquidity_analysis,
            "model_analysis": model_analysis,
            "overall_recommendations": self._generate_overall_recommendations(
                position_analysis, stress_analysis, correlation_analysis, 
                liquidity_analysis, model_analysis
            )
        }
        
        # Tallenna tulokset
        self.results = comprehensive_results
        self._save_results(comprehensive_results)
        
        return comprehensive_results
    
    def _analyze_position_sizing(self, symbols: List[str]) -> Dict:
        """Analysoi position sizing"""
        results = {}
        
        for symbol in symbols:
            print(f"Analysoidaan {symbol}...")
            
            # Käytä oletusarvoja (käytännössä käyttäjä syöttäisi nämä)
            entry_price = 100.0  # Oletusarvo
            stop_loss = 90.0     # Oletusarvo
            
            result = self.position_calc.calculate_position_size(
                symbol, entry_price, stop_loss
            )
            
            if "error" not in result:
                results[symbol] = result
                print(f"  Position koko: {result['position_size']} osaketta")
                print(f"  Suositus: {result['recommendation']}")
            else:
                results[symbol] = {"error": result["error"]}
                print(f"  Virhe: {result['error']}")
        
        return results
    
    def _analyze_stress_testing(self, symbols: List[str], weights: List[float]) -> Dict:
        """Analysoi stress testing"""
        print("Suoritetaan stress testit...")
        
        result = self.stress_tool.stress_test_portfolio(symbols, weights, self.portfolio_value)
        
        if "error" not in result:
            stress_score = result["stress_score"]
            print(f"Stress Score: {stress_score['stress_score']:.1f}/10")
            print(f"Stress Level: {stress_score['stress_level']}")
            print("Suositukset:")
            for rec in stress_score["recommendations"][:3]:
                print(f"  - {rec}")
        else:
            print(f"Virhe: {result['error']}")
        
        return result
    
    def _analyze_correlations(self, symbols: List[str]) -> Dict:
        """Analysoi korrelaatiot"""
        print("Analysoidaan korrelaatiot...")
        
        result = self.corr_analyzer.analyze_correlations(symbols)
        
        if "error" not in result:
            analysis = result["analysis"]
            print(f"Keskiarvo korrelaatio: {analysis['average_correlation']:.3f}")
            print(f"Korrelaation taso: {analysis['correlation_level']}")
            print("Suositukset:")
            for rec in result["recommendations"][:3]:
                print(f"  - {rec}")
        else:
            print(f"Virhe: {result['error']}")
        
        return result
    
    def _analyze_liquidity(self, symbols: List[str]) -> Dict:
        """Analysoi likviditeetti"""
        print("Analysoidaan likviditeetti...")
        
        result = self.liquidity_monitor.analyze_liquidity(symbols)
        
        if "error" not in result:
            portfolio_liquidity = result["portfolio_liquidity"]
            print(f"Portfolio-likviditeetti: {portfolio_liquidity['liquidity_level']}")
            print(f"Likviditeettipisteet: {portfolio_liquidity['average_liquidity_score']:.3f}")
            print("Suositukset:")
            for rec in result["recommendations"][:3]:
                print(f"  - {rec}")
        else:
            print(f"Virhe: {result['error']}")
        
        return result
    
    def _analyze_models(self, symbols: List[str]) -> Dict:
        """Analysoi mallit"""
        results = {}
        
        for symbol in symbols:
            print(f"Arvioidaan malli {symbol}...")
            
            result = self.model_evaluator.evaluate_model_performance(symbol)
            
            if "error" not in result:
                reliability = result["reliability_score"]
                print(f"  Luotettavuus: {reliability['reliability_level']} ({reliability['reliability_percentage']:.1f}%)")
                results[symbol] = result
            else:
                print(f"  Virhe: {result['error']}")
                results[symbol] = {"error": result["error"]}
        
        return results
    
    def _generate_overall_recommendations(self, position_analysis: Dict, 
                                        stress_analysis: Dict, 
                                        correlation_analysis: Dict, 
                                        liquidity_analysis: Dict, 
                                        model_analysis: Dict) -> List[str]:
        """Generoi yleiset suositukset"""
        recommendations = []
        
        # Stress testing -suositukset
        if "stress_score" in stress_analysis:
            stress_score = stress_analysis["stress_score"]["stress_score"]
            if stress_score > 7:
                recommendations.append("🚨 KORKEA STRESS RISKI - vähennä position kokoja ja lisää diversifikaatiota")
            elif stress_score > 4:
                recommendations.append("⚠️ Kohtalainen stress riski - seuraa markkinoita tarkemmin")
        
        # Korrelaatio-suositukset
        if "analysis" in correlation_analysis:
            corr_level = correlation_analysis["analysis"]["correlation_level"]
            if corr_level == "Korkea":
                recommendations.append("🔗 KORKEA KORRELAATIO - lisää diversifikaatiota eri sektoreista")
        
        # Likviditeetti-suositukset
        if "portfolio_liquidity" in liquidity_analysis:
            liquidity_level = liquidity_analysis["portfolio_liquidity"]["liquidity_level"]
            if liquidity_level == "Matala":
                recommendations.append("💧 MATALA LIKVIDITEETTI - lisää likvidimpien osakkeiden osuus")
        
        # Mallin luotettavuus-suositukset
        low_reliability_count = 0
        for symbol, analysis in model_analysis.items():
            if "reliability_score" in analysis:
                reliability_level = analysis["reliability_score"]["reliability_level"]
                if reliability_level == "Matala":
                    low_reliability_count += 1
        
        if low_reliability_count > len(model_analysis) / 2:
            recommendations.append("🤖 MATALA MALLIN LUOTETTAVUUS - harkitse mallien parantamista")
        
        # Yleiset suositukset
        if not recommendations:
            recommendations.append("✅ Hyvä riskiprofiili - jatka nykyistä strategiaa")
        
        recommendations.append("📊 Suorita analyysi säännöllisesti (esim. kuukausittain)")
        recommendations.append("📈 Seuraa markkinatilannetta ja mukauta strategiaa tarpeen mukaan")
        
        return recommendations
    
    def _save_results(self, results: Dict):
        """Tallenna tulokset tiedostoon"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"risk_analysis_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            print(f"\n💾 Tulokset tallennettu: {filename}")
        except Exception as e:
            print(f"❌ Virhe tallennuksessa: {e}")
    
    def print_summary(self):
        """Tulosta yhteenveto"""
        if not self.results:
            print("❌ Ei analyysituloksia saatavilla")
            return
        
        print("\n" + "="*60)
        print("📊 RISKIANALYYSIN YHTEENVETO")
        print("="*60)
        
        # Stress testing
        if "stress_analysis" in self.results and "stress_score" in self.results["stress_analysis"]:
            stress_score = self.results["stress_analysis"]["stress_score"]
            print(f"🛡️ Stress Score: {stress_score['stress_score']:.1f}/10 ({stress_score['stress_level']})")
        
        # Korrelaatio
        if "correlation_analysis" in self.results and "analysis" in self.results["correlation_analysis"]:
            corr_analysis = self.results["correlation_analysis"]["analysis"]
            print(f"🔗 Korrelaatio: {corr_analysis['correlation_level']} ({corr_analysis['average_correlation']:.3f})")
        
        # Likviditeetti
        if "liquidity_analysis" in self.results and "portfolio_liquidity" in self.results["liquidity_analysis"]:
            liquidity = self.results["liquidity_analysis"]["portfolio_liquidity"]
            print(f"💧 Likviditeetti: {liquidity['liquidity_level']} ({liquidity['average_liquidity_score']:.3f})")
        
        # Mallin luotettavuus
        if "model_analysis" in self.results:
            reliability_scores = []
            for symbol, analysis in self.results["model_analysis"].items():
                if "reliability_score" in analysis:
                    reliability_scores.append(analysis["reliability_score"]["reliability_percentage"])
            
            if reliability_scores:
                avg_reliability = sum(reliability_scores) / len(reliability_scores)
                print(f"🤖 Mallin luotettavuus: {avg_reliability:.1f}%")
        
        # Yleiset suositukset
        if "overall_recommendations" in self.results:
            print(f"\n🎯 YLEISET SUOSITUKSET:")
            for i, rec in enumerate(self.results["overall_recommendations"], 1):
                print(f"{i}. {rec}")

def main():
    """Pääohjelma"""
    print("🛡️ Riskienhallinta Dashboard")
    print("=" * 40)
    
    # Esimerkki käytöstä
    dashboard = RiskManagementDashboard(portfolio_value=100000)
    
    # Analysoi portfolio
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
    weights = [0.2, 0.2, 0.2, 0.2, 0.2]  # Yhtä suuret painotukset
    
    print(f"Portfolio: {', '.join(symbols)}")
    print(f"Portfolio arvo: ${dashboard.portfolio_value:,}")
    
    # Suorita kattava analyysi
    results = dashboard.run_comprehensive_analysis(symbols, weights)
    
    # Tulosta yhteenveto
    dashboard.print_summary()
    
    print(f"\n✅ Analyysi valmis! Tarkista tallennettu tiedosto saadaksesi yksityiskohtaiset tulokset.")

if __name__ == "__main__":
    main()
