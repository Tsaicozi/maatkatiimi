"""
Riskienhallintatyökalut - Suositusten Implementointi
==================================================

Tämä moduuli sisältää työkalut riskienhallintasuositusten toteuttamiseen:
1. Position Sizing -kalkulaattori
2. Stress Testing -työkalu
3. Korrelaatioanalyysi
4. Likviditeettiseuranta
5. Mallin arviointi
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import warnings
warnings.filterwarnings('ignore')

class PositionSizingCalculator:
    """Position sizing -kalkulaattori riskienhallintaan"""
    
    def __init__(self, portfolio_value: float, max_risk_per_trade: float = 0.02):
        """
        Args:
            portfolio_value: Portfolio kokonaisarvo
            max_risk_per_trade: Maksimiriski per kauppa (2% oletus)
        """
        self.portfolio_value = portfolio_value
        self.max_risk_per_trade = max_risk_per_trade
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                              stop_loss: float, confidence_level: float = 0.95) -> Dict:
        """
        Laske optimaalinen position koko
        
        Args:
            symbol: Osakkeen symboli
            entry_price: Sisäänmenohinta
            stop_loss: Stop loss -hinta
            confidence_level: Luottamustaso (95% oletus)
        
        Returns:
            Dict sisältäen position koon ja riskimittarit
        """
        try:
            # Hae historiallinen data volatiliteetin laskemiseen
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y")
            
            if hist.empty:
                return {"error": f"Ei dataa symbolille {symbol}"}
            
            # Laske päivittäiset tuotot
            returns = hist['Close'].pct_change().dropna()
            
            # Laske volatiliteetti
            volatility = returns.std() * np.sqrt(252)  # Vuosittainen volatiliteetti
            
            # Laske VaR
            var_95 = np.percentile(returns, 5) * np.sqrt(252)
            
            # Laske riski per osake
            risk_per_share = abs(entry_price - stop_loss)
            
            # Laske maksimimäärä osakkeita
            max_risk_amount = self.portfolio_value * self.max_risk_per_trade
            max_shares = int(max_risk_amount / risk_per_share)
            
            # Laske position arvo
            position_value = max_shares * entry_price
            position_percentage = (position_value / self.portfolio_value) * 100
            
            # Laske odotettu tuotto (yksinkertainen estimaatti)
            expected_return = returns.mean() * 252
            
            # Laske Sharpe ratio (oletetaan risk-free rate 2%)
            risk_free_rate = 0.02
            sharpe_ratio = (expected_return - risk_free_rate) / volatility
            
            return {
                "symbol": symbol,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "position_size": max_shares,
                "position_value": position_value,
                "position_percentage": position_percentage,
                "risk_per_share": risk_per_share,
                "max_risk_amount": max_risk_amount,
                "volatility": volatility,
                "var_95": var_95,
                "expected_return": expected_return,
                "sharpe_ratio": sharpe_ratio,
                "recommendation": self._get_recommendation(sharpe_ratio, volatility)
            }
            
        except Exception as e:
            return {"error": f"Virhe position sizing -laskennassa: {str(e)}"}
    
    def _get_recommendation(self, sharpe_ratio: float, volatility: float) -> str:
        """Anna suositus position koosta"""
        if sharpe_ratio > 1.0 and volatility < 0.3:
            return "SUOSITUS: Hyvä riski-tuotto -suhde, position koko OK"
        elif sharpe_ratio > 0.5:
            return "VAROITUS: Kohtalainen riski-tuotto -suhde, harkitse pienempää position kokoa"
        else:
            return "VAROITUS: Huono riski-tuotto -suhde, suosittelemme pienempää position kokoa"

class StressTestingTool:
    """Stress testing -työkalu eri markkinaskenaarioille"""
    
    def __init__(self):
        self.crisis_scenarios = {
            "2008_financial_crisis": {
                "market_decline": -0.37,  # 37% markkinoiden lasku
                "volatility_increase": 2.5,  # Volatiliteetin kasvu
                "correlation_increase": 0.8  # Korrelaation kasvu
            },
            "covid_19_shock": {
                "market_decline": -0.34,  # 34% markkinoiden lasku
                "volatility_increase": 3.0,
                "correlation_increase": 0.7
            },
            "interest_rate_shock": {
                "market_decline": -0.15,  # 15% markkinoiden lasku
                "volatility_increase": 1.5,
                "correlation_increase": 0.6
            }
        }
    
    def stress_test_portfolio(self, symbols: List[str], weights: List[float], 
                            portfolio_value: float) -> Dict:
        """
        Suorita stress test portfolioille
        
        Args:
            symbols: Osakkeiden symbolit
            weights: Painotukset (summa = 1.0)
            portfolio_value: Portfolio arvo
        
        Returns:
            Dict sisältäen stress test -tulokset
        """
        try:
            results = {}
            
            # Hae historiallinen data
            data = {}
            for symbol in symbols:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2y")
                if not hist.empty:
                    data[symbol] = hist['Close'].pct_change().dropna()
            
            if not data:
                return {"error": "Ei dataa saatavilla"}
            
            # Laske baseline-mittarit
            baseline_returns = self._calculate_portfolio_returns(data, weights)
            baseline_volatility = baseline_returns.std() * np.sqrt(252)
            baseline_var_95 = np.percentile(baseline_returns, 5)
            
            results["baseline"] = {
                "annual_return": baseline_returns.mean() * 252,
                "annual_volatility": baseline_volatility,
                "var_95": baseline_var_95,
                "sharpe_ratio": (baseline_returns.mean() * 252) / baseline_volatility
            }
            
            # Suorita stress testit
            for scenario_name, scenario_params in self.crisis_scenarios.items():
                stress_results = self._simulate_stress_scenario(
                    data, weights, scenario_params
                )
                results[scenario_name] = stress_results
            
            # Laske yleinen stress test -pisteet
            results["stress_score"] = self._calculate_stress_score(results)
            
            return results
            
        except Exception as e:
            return {"error": f"Virhe stress testingissä: {str(e)}"}
    
    def _calculate_portfolio_returns(self, data: Dict, weights: List[float]) -> pd.Series:
        """Laske portfolio-tuotot"""
        portfolio_returns = pd.Series(0, index=list(data.values())[0].index)
        
        for i, (symbol, returns) in enumerate(data.items()):
            if i < len(weights):
                portfolio_returns += returns * weights[i]
        
        return portfolio_returns
    
    def _simulate_stress_scenario(self, data: Dict, weights: List[float], 
                                 scenario_params: Dict) -> Dict:
        """Simuloi stress-skenaario"""
        # Lisää volatiliteettia ja korrelaatiota
        stressed_data = {}
        
        for symbol, returns in data.items():
            # Lisää volatiliteettia
            volatility_multiplier = scenario_params["volatility_increase"]
            stressed_returns = returns * volatility_multiplier
            
            # Lisää markkinoiden laskua
            market_decline = scenario_params["market_decline"] / 252  # Päivittäinen
            stressed_returns += market_decline
            
            stressed_data[symbol] = stressed_returns
        
        # Laske stress-testatuille tuotoille
        stressed_portfolio_returns = self._calculate_portfolio_returns(stressed_data, weights)
        
        return {
            "annual_return": stressed_portfolio_returns.mean() * 252,
            "annual_volatility": stressed_portfolio_returns.std() * np.sqrt(252),
            "var_95": np.percentile(stressed_portfolio_returns, 5),
            "max_drawdown": self._calculate_max_drawdown(stressed_portfolio_returns),
            "recovery_time_days": self._estimate_recovery_time(stressed_portfolio_returns)
        }
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Laske maksimi drawdown"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def _estimate_recovery_time(self, returns: pd.Series) -> int:
        """Arvioi toipumisaika päivinä"""
        cumulative = (1 + returns).cumprod()
        max_dd = self._calculate_max_drawdown(returns)
        
        # Yksinkertainen estimaatti: oletetaan 5% vuosittainen tuotto
        daily_recovery_rate = 0.05 / 252
        recovery_days = abs(max_dd) / daily_recovery_rate
        
        return int(recovery_days)
    
    def _calculate_stress_score(self, results: Dict) -> Dict:
        """Laske yleinen stress test -pisteet"""
        baseline = results["baseline"]
        
        # Laske jokaisen skenaarion vaikutus
        stress_impacts = {}
        for scenario in ["2008_financial_crisis", "covid_19_shock", "interest_rate_shock"]:
            if scenario in results:
                scenario_data = results[scenario]
                
                # Laske tuoton lasku
                return_decline = (baseline["annual_return"] - scenario_data["annual_return"]) / abs(baseline["annual_return"])
                
                # Laske volatiliteetin kasvu
                volatility_increase = (scenario_data["annual_volatility"] - baseline["annual_volatility"]) / baseline["annual_volatility"]
                
                # Laske VaR:n huononeminen
                var_decline = (baseline["var_95"] - scenario_data["var_95"]) / abs(baseline["var_95"])
                
                stress_impacts[scenario] = {
                    "return_decline": return_decline,
                    "volatility_increase": volatility_increase,
                    "var_decline": var_decline,
                    "overall_impact": (return_decline + volatility_increase + var_decline) / 3
                }
        
        # Laske keskiarvo
        avg_impact = np.mean([impact["overall_impact"] for impact in stress_impacts.values()])
        
        # Anna stress score (1-10, 10 = korkein riski)
        stress_score = min(10, max(1, avg_impact * 10))
        
        return {
            "stress_score": stress_score,
            "stress_level": "Korkea" if stress_score > 7 else "Kohtalainen" if stress_score > 4 else "Matala",
            "recommendations": self._get_stress_recommendations(stress_score, stress_impacts)
        }
    
    def _get_stress_recommendations(self, stress_score: float, stress_impacts: Dict) -> List[str]:
        """Anna suositukset stress test -tulosten perusteella"""
        recommendations = []
        
        if stress_score > 7:
            recommendations.extend([
                "VAROITUS: Korkea stress riski - vähennä position kokoja",
                "Lisää diversifikaatiota portfolioon",
                "Harkitse hedge-strategioita",
                "Seuraa markkinoita tarkemmin"
            ])
        elif stress_score > 4:
            recommendations.extend([
                "Kohtalainen stress riski - harkitse position koon vähentämistä",
                "Lisää korrelaatioanalyysiä",
                "Valmistaudu volatiliteettikausiin"
            ])
        else:
            recommendations.extend([
                "Matala stress riski - portfolio on hyvin diversifioitu",
                "Jatka nykyistä strategiaa",
                "Seuraa säännöllisesti markkinatilannetta"
            ])
        
        return recommendations

class CorrelationAnalyzer:
    """Korrelaatioanalyysi -työkalu diversifikaation optimointiin"""
    
    def __init__(self):
        self.correlation_thresholds = {
            "low": 0.3,
            "moderate": 0.6,
            "high": 0.8
        }
    
    def analyze_correlations(self, symbols: List[str], period: str = "1y") -> Dict:
        """
        Analysoi korrelaatiot osakkeiden välillä
        
        Args:
            symbols: Osakkeiden symbolit
            period: Aikajakso analyysille
        
        Returns:
            Dict sisältäen korrelaatioanalyysin
        """
        try:
            # Hae data
            data = {}
            for symbol in symbols:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                if not hist.empty:
                    data[symbol] = hist['Close'].pct_change().dropna()
            
            if len(data) < 2:
                return {"error": "Tarvitaan vähintään 2 osaketta korrelaatioanalyysiin"}
            
            # Laske korrelaatiomatriisi
            returns_df = pd.DataFrame(data)
            correlation_matrix = returns_df.corr()
            
            # Analysoi korrelaatiot
            analysis = self._analyze_correlation_matrix(correlation_matrix)
            
            # Laske diversifikaation hyödyt
            diversification_benefits = self._calculate_diversification_benefits(returns_df)
            
            # Anna suositukset
            recommendations = self._get_correlation_recommendations(analysis, diversification_benefits)
            
            return {
                "correlation_matrix": correlation_matrix.to_dict(),
                "analysis": analysis,
                "diversification_benefits": diversification_benefits,
                "recommendations": recommendations
            }
            
        except Exception as e:
            return {"error": f"Virhe korrelaatioanalyysissä: {str(e)}"}
    
    def _analyze_correlation_matrix(self, correlation_matrix: pd.DataFrame) -> Dict:
        """Analysoi korrelaatiomatriisi"""
        # Laske keskiarvo korrelaatio
        upper_triangle = correlation_matrix.where(
            np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool)
        )
        avg_correlation = upper_triangle.stack().mean()
        
        # Laske korkeimmat korrelaatiot
        high_correlations = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr_value = correlation_matrix.iloc[i, j]
                if corr_value > self.correlation_thresholds["high"]:
                    high_correlations.append({
                        "pair": f"{correlation_matrix.columns[i]} - {correlation_matrix.columns[j]}",
                        "correlation": corr_value
                    })
        
        # Laske diversifikaation tehokkuus
        diversification_efficiency = 1 - avg_correlation
        
        return {
            "average_correlation": avg_correlation,
            "high_correlations": high_correlations,
            "diversification_efficiency": diversification_efficiency,
            "correlation_level": self._get_correlation_level(avg_correlation)
        }
    
    def _get_correlation_level(self, avg_correlation: float) -> str:
        """Määritä korrelaation taso"""
        if avg_correlation < self.correlation_thresholds["low"]:
            return "Matala"
        elif avg_correlation < self.correlation_thresholds["moderate"]:
            return "Kohtalainen"
        else:
            return "Korkea"
    
    def _calculate_diversification_benefits(self, returns_df: pd.DataFrame) -> Dict:
        """Laske diversifikaation hyödyt"""
        # Laske yksittäisten osakkeiden volatiliteetit
        individual_volatilities = returns_df.std() * np.sqrt(252)
        
        # Laske portfolio volatiliteetti (yhtä suuret painotukset)
        equal_weights = np.ones(len(returns_df.columns)) / len(returns_df.columns)
        portfolio_returns = (returns_df * equal_weights).sum(axis=1)
        portfolio_volatility = portfolio_returns.std() * np.sqrt(252)
        
        # Laske diversifikaation hyöty
        avg_individual_volatility = individual_volatilities.mean()
        diversification_benefit = (avg_individual_volatility - portfolio_volatility) / avg_individual_volatility
        
        return {
            "individual_volatilities": individual_volatilities.to_dict(),
            "portfolio_volatility": portfolio_volatility,
            "diversification_benefit": diversification_benefit,
            "benefit_percentage": diversification_benefit * 100
        }
    
    def _get_correlation_recommendations(self, analysis: Dict, diversification_benefits: Dict) -> List[str]:
        """Anna suositukset korrelaatioanalyysin perusteella"""
        recommendations = []
        
        avg_corr = analysis["average_correlation"]
        high_corrs = analysis["high_correlations"]
        diversification_benefit = diversification_benefits["diversification_benefit"]
        
        if avg_corr > self.correlation_thresholds["high"]:
            recommendations.extend([
                "VAROITUS: Korkea korrelaatio - lisää diversifikaatiota",
                "Harkitse eri sektoreiden osakkeita",
                "Lisää kansainvälisiä osakkeita",
                "Harkitse vaihtoehtoisia sijoituskohteita"
            ])
        elif avg_corr > self.correlation_thresholds["moderate"]:
            recommendations.extend([
                "Kohtalainen korrelaatio - harkitse lisää diversifikaatiota",
                "Tarkista sektorijakauma",
                "Harkitse eri markkina-arvojen osakkeita"
            ])
        else:
            recommendations.append("Hyvä diversifikaatio - jatka nykyistä strategiaa")
        
        if high_corrs:
            recommendations.append(f"Korkeat korrelaatiot löytyi: {len(high_corrs)} paria")
            for corr in high_corrs[:3]:  # Näytä 3 korkeinta
                recommendations.append(f"- {corr['pair']}: {corr['correlation']:.2f}")
        
        if diversification_benefit < 0.1:
            recommendations.append("VAROITUS: Pieni diversifikaation hyöty - harkitse portfolio-rakenteen muuttamista")
        
        return recommendations

def main():
    """Esimerkki käytöstä"""
    print("🛠️ Riskienhallintatyökalut - Esimerkki käytöstä")
    print("=" * 60)
    
    # Esimerkki position sizing -laskennasta
    print("\n1. POSITION SIZING -KALKULAATTORI")
    print("-" * 40)
    
    portfolio_value = 100000  # 100k€ portfolio
    position_calc = PositionSizingCalculator(portfolio_value, max_risk_per_trade=0.02)
    
    # Laske position koko AAPL:lle
    result = position_calc.calculate_position_size(
        symbol="AAPL",
        entry_price=150.0,
        stop_loss=140.0
    )
    
    if "error" not in result:
        print(f"Symbol: {result['symbol']}")
        print(f"Position koko: {result['position_size']} osaketta")
        print(f"Position arvo: ${result['position_value']:,.2f}")
        print(f"Position %: {result['position_percentage']:.2f}%")
        print(f"Suositus: {result['recommendation']}")
    else:
        print(f"Virhe: {result['error']}")
    
    # Esimerkki stress testingistä
    print("\n2. STRESS TESTING")
    print("-" * 40)
    
    stress_tool = StressTestingTool()
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    weights = [0.25, 0.25, 0.25, 0.25]  # Yhtä suuret painotukset
    
    stress_results = stress_tool.stress_test_portfolio(symbols, weights, portfolio_value)
    
    if "error" not in stress_results:
        print(f"Stress Score: {stress_results['stress_score']['stress_score']:.1f}/10")
        print(f"Stress Level: {stress_results['stress_score']['stress_level']}")
        print("Suositukset:")
        for rec in stress_results['stress_score']['recommendations'][:3]:
            print(f"- {rec}")
    else:
        print(f"Virhe: {stress_results['error']}")
    
    # Esimerkki korrelaatioanalyysistä
    print("\n3. KORRELAATIOANALYYSI")
    print("-" * 40)
    
    corr_analyzer = CorrelationAnalyzer()
    corr_results = corr_analyzer.analyze_correlations(symbols)
    
    if "error" not in corr_results:
        analysis = corr_results['analysis']
        print(f"Keskiarvo korrelaatio: {analysis['average_correlation']:.3f}")
        print(f"Korrelaation taso: {analysis['correlation_level']}")
        print(f"Diversifikaation tehokkuus: {analysis['diversification_efficiency']:.3f}")
        print("Suositukset:")
        for rec in corr_results['recommendations'][:3]:
            print(f"- {rec}")
    else:
        print(f"Virhe: {corr_results['error']}")

if __name__ == "__main__":
    main()
