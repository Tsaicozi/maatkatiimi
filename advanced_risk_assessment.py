"""
Advanced Risk Assessment - Edistyneet riskienarviointityökalut
Perustuu kattavaan tutkimukseen riskienhallinnasta
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Tuple
import logging
from scipy import stats
import json

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    """Risk-mittarit"""
    var_95: float  # Value at Risk 95%
    var_99: float  # Value at Risk 99%
    expected_shortfall: float  # Expected Shortfall
    max_drawdown: float  # Maximum Drawdown
    sharpe_ratio: float  # Sharpe Ratio
    sortino_ratio: float  # Sortino Ratio
    calmar_ratio: float  # Calmar Ratio
    volatility: float  # Volatiliteetti
    beta: float  # Beta (markkinasuhteessa)
    correlation: float  # Korrelaatio markkinoiden kanssa
    liquidity_risk: float  # Likviditeettiriski
    concentration_risk: float  # Konsentraatioriski
    tail_risk: float  # Tail risk
    stress_test_score: float  # Stress test score

@dataclass
class PortfolioRisk:
    """Portfolio risk-analyysi"""
    total_risk: float
    systematic_risk: float
    unsystematic_risk: float
    diversification_ratio: float
    portfolio_heat: float
    risk_contribution: Dict[str, float]
    correlation_matrix: Dict[str, Dict[str, float]]
    risk_budget: Dict[str, float]

class AdvancedRiskAssessment:
    """Edistyneet riskienarviointityökalut"""
    
    def __init__(self):
        self.confidence_levels = [0.95, 0.99]
        self.lookback_periods = [1, 7, 30, 90]  # päivät
        self.stress_scenarios = self._initialize_stress_scenarios()
        
    def _initialize_stress_scenarios(self) -> Dict:
        """Alusta stress test -skenaariot"""
        return {
            "market_crash": {
                "description": "Markkinoiden romahdus (-50%)",
                "market_impact": -0.50,
                "volatility_multiplier": 3.0,
                "liquidity_impact": -0.80
            },
            "crypto_winter": {
                "description": "Kryptotalvi (-80%)",
                "market_impact": -0.80,
                "volatility_multiplier": 5.0,
                "liquidity_impact": -0.90
            },
            "regulatory_shock": {
                "description": "Sääntelyshokki (-30%)",
                "market_impact": -0.30,
                "volatility_multiplier": 2.0,
                "liquidity_impact": -0.60
            },
            "liquidity_crisis": {
                "description": "Likviditeettikriisi (-70%)",
                "market_impact": -0.70,
                "volatility_multiplier": 4.0,
                "liquidity_impact": -0.95
            },
            "black_swan": {
                "description": "Mustan joutsenen tapahtuma (-90%)",
                "market_impact": -0.90,
                "volatility_multiplier": 10.0,
                "liquidity_impact": -0.99
            }
        }
    
    def calculate_var(self, returns: List[float], confidence_level: float = 0.95) -> float:
        """Laske Value at Risk (VaR)"""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        var = np.percentile(returns_array, (1 - confidence_level) * 100)
        return abs(var)
    
    def calculate_expected_shortfall(self, returns: List[float], confidence_level: float = 0.95) -> float:
        """Laske Expected Shortfall (ES)"""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        var = self.calculate_var(returns, confidence_level)
        
        # Laske ES (keskimääräinen tappio VaR:n yli)
        tail_returns = returns_array[returns_array <= -var]
        if len(tail_returns) == 0:
            return var
        
        expected_shortfall = abs(np.mean(tail_returns))
        return expected_shortfall
    
    def calculate_max_drawdown(self, prices: List[float]) -> float:
        """Laske Maximum Drawdown"""
        if not prices or len(prices) < 2:
            return 0.0
        
        prices_array = np.array(prices)
        peak = np.maximum.accumulate(prices_array)
        drawdown = (prices_array - peak) / peak
        max_drawdown = abs(np.min(drawdown))
        
        return max_drawdown
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Laske Sharpe Ratio"""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 365)  # Päivittäinen risk-free rate
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(365)
        return sharpe
    
    def calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Laske Sortino Ratio"""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 365)
        
        # Laske downside deviation
        negative_returns = excess_returns[excess_returns < 0]
        if len(negative_returns) == 0:
            return float('inf') if np.mean(excess_returns) > 0 else 0.0
        
        downside_deviation = np.std(negative_returns)
        if downside_deviation == 0:
            return 0.0
        
        sortino = np.mean(excess_returns) / downside_deviation * np.sqrt(365)
        return sortino
    
    def calculate_calmar_ratio(self, returns: List[float], prices: List[float]) -> float:
        """Laske Calmar Ratio"""
        if not returns or not prices:
            return 0.0
        
        annual_return = np.mean(returns) * 365
        max_dd = self.calculate_max_drawdown(prices)
        
        if max_dd == 0:
            return float('inf') if annual_return > 0 else 0.0
        
        calmar = annual_return / max_dd
        return calmar
    
    def calculate_volatility(self, returns: List[float], annualized: bool = True) -> float:
        """Laske volatiliteetti"""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        volatility = np.std(returns_array)
        
        if annualized:
            volatility *= np.sqrt(365)
        
        return volatility
    
    def calculate_beta(self, asset_returns: List[float], market_returns: List[float]) -> float:
        """Laske Beta (markkinasuhteessa)"""
        if not asset_returns or not market_returns or len(asset_returns) != len(market_returns):
            return 1.0
        
        asset_array = np.array(asset_returns)
        market_array = np.array(market_returns)
        
        covariance = np.cov(asset_array, market_array)[0, 1]
        market_variance = np.var(market_array)
        
        if market_variance == 0:
            return 1.0
        
        beta = covariance / market_variance
        return beta
    
    def calculate_correlation(self, returns1: List[float], returns2: List[float]) -> float:
        """Laske korrelaatio"""
        if not returns1 or not returns2 or len(returns1) != len(returns2):
            return 0.0
        
        correlation = np.corrcoef(returns1, returns2)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def calculate_liquidity_risk(self, volume: float, market_cap: float, avg_volume: float) -> float:
        """Laske likviditeettiriski"""
        if market_cap == 0:
            return 1.0
        
        # Volume to market cap ratio
        volume_ratio = volume / market_cap
        
        # Average volume ratio
        avg_volume_ratio = avg_volume / market_cap if market_cap > 0 else 0
        
        # Liquidity risk (korkeampi = riskialtisempi)
        if volume_ratio < 0.001:  # < 0.1% of market cap
            liquidity_risk = 0.8
        elif volume_ratio < 0.005:  # < 0.5% of market cap
            liquidity_risk = 0.6
        elif volume_ratio < 0.01:  # < 1% of market cap
            liquidity_risk = 0.4
        elif volume_ratio < 0.05:  # < 5% of market cap
            liquidity_risk = 0.2
        else:
            liquidity_risk = 0.1
        
        # Adjust by average volume
        if avg_volume_ratio > 0:
            volume_consistency = min(volume_ratio / avg_volume_ratio, 2.0)
            liquidity_risk *= (2.0 - volume_consistency) / 2.0
        
        return min(liquidity_risk, 1.0)
    
    def calculate_concentration_risk(self, position_sizes: List[float]) -> float:
        """Laske konsentraatioriski (Herfindahl-Hirschman Index)"""
        if not position_sizes:
            return 0.0
        
        total_value = sum(position_sizes)
        if total_value == 0:
            return 0.0
        
        # Normalisoi position koot
        normalized_sizes = [size / total_value for size in position_sizes]
        
        # Laske HHI
        hhi = sum(size ** 2 for size in normalized_sizes)
        
        # Muunna risk-mittariksi (0-1, korkeampi = riskialtisempi)
        concentration_risk = min(hhi, 1.0)
        
        return concentration_risk
    
    def calculate_tail_risk(self, returns: List[float]) -> float:
        """Laske tail risk (extreme events)"""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        
        # Laske skewness ja kurtosis
        skewness = stats.skew(returns_array)
        kurtosis = stats.kurtosis(returns_array)
        
        # Tail risk (korkeampi kurtosis = enemmän extreme events)
        tail_risk = abs(skewness) * 0.3 + max(0, kurtosis - 3) * 0.1
        
        return min(tail_risk, 1.0)
    
    def stress_test(self, portfolio: Dict, scenario: str) -> Dict:
        """Suorita stress test"""
        if scenario not in self.stress_scenarios:
            return {"error": f"Tuntematon skenaario: {scenario}"}
        
        stress_params = self.stress_scenarios[scenario]
        results = {
            "scenario": scenario,
            "description": stress_params["description"],
            "portfolio_impact": {},
            "total_loss": 0.0,
            "surviving_positions": 0,
            "failed_positions": 0
        }
        
        total_value = portfolio.get("total_value", 10000)
        positions = portfolio.get("positions", {})
        
        for symbol, position in positions.items():
            current_value = position.get("value", 0)
            
            # Laske stress impact
            market_impact = stress_params["market_impact"]
            volatility_multiplier = stress_params["volatility_multiplier"]
            liquidity_impact = stress_params["liquidity_impact"]
            
            # Simuloi position arvo stressissä
            stressed_value = current_value * (1 + market_impact)
            
            # Lisää volatiliteettiriski
            volatility_impact = np.random.normal(0, 0.1 * volatility_multiplier)
            stressed_value *= (1 + volatility_impact)
            
            # Lisää likviditeettiriski
            if position.get("liquidity", 100000) < 50000:
                stressed_value *= (1 + liquidity_impact)
            
            # Laske tappio
            loss = current_value - stressed_value
            loss_percentage = loss / current_value if current_value > 0 else 0
            
            results["portfolio_impact"][symbol] = {
                "current_value": current_value,
                "stressed_value": stressed_value,
                "loss": loss,
                "loss_percentage": loss_percentage
            }
            
            results["total_loss"] += loss
            
            if stressed_value > current_value * 0.5:  # > 50% arvosta säilyy
                results["surviving_positions"] += 1
            else:
                results["failed_positions"] += 1
        
        results["total_loss_percentage"] = results["total_loss"] / total_value if total_value > 0 else 0
        
        return results
    
    def calculate_portfolio_risk(self, portfolio: Dict, market_data: Dict) -> PortfolioRisk:
        """Laske portfolio risk-analyysi"""
        positions = portfolio.get("positions", {})
        total_value = portfolio.get("total_value", 10000)
        
        # Laske position riskit
        position_risks = {}
        position_values = []
        position_returns = []
        
        for symbol, position in positions.items():
            value = position.get("value", 0)
            returns = position.get("returns", [])
            volatility = position.get("volatility", 0.2)
            
            position_values.append(value)
            position_risks[symbol] = {
                "value": value,
                "weight": value / total_value if total_value > 0 else 0,
                "volatility": volatility,
                "var_95": self.calculate_var(returns, 0.95),
                "var_99": self.calculate_var(returns, 0.99)
            }
            
            if returns:
                position_returns.extend(returns)
        
        # Laske portfolio volatiliteetti
        portfolio_volatility = self.calculate_volatility(position_returns)
        
        # Laske korrelaatiomatriisi
        correlation_matrix = {}
        symbols = list(positions.keys())
        for i, symbol1 in enumerate(symbols):
            correlation_matrix[symbol1] = {}
            for j, symbol2 in enumerate(symbols):
                if i == j:
                    correlation_matrix[symbol1][symbol2] = 1.0
                else:
                    returns1 = positions[symbol1].get("returns", [])
                    returns2 = positions[symbol2].get("returns", [])
                    correlation_matrix[symbol1][symbol2] = self.calculate_correlation(returns1, returns2)
        
        # Laske diversifikaatiosuhde
        weighted_volatility = sum(
            position_risks[symbol]["weight"] * position_risks[symbol]["volatility"]
            for symbol in symbols
        )
        diversification_ratio = weighted_volatility / portfolio_volatility if portfolio_volatility > 0 else 1.0
        
        # Laske risk contribution
        risk_contribution = {}
        for symbol in symbols:
            weight = position_risks[symbol]["weight"]
            volatility = position_risks[symbol]["volatility"]
            risk_contribution[symbol] = weight * volatility
        
        # Laske portfolio heat
        portfolio_heat = sum(risk_contribution.values()) / portfolio_volatility if portfolio_volatility > 0 else 0
        
        # Laske risk budget (suositellut position koot)
        risk_budget = {}
        total_risk = sum(risk_contribution.values())
        for symbol in symbols:
            if total_risk > 0:
                risk_budget[symbol] = risk_contribution[symbol] / total_risk
            else:
                risk_budget[symbol] = 1.0 / len(symbols)
        
        return PortfolioRisk(
            total_risk=portfolio_volatility,
            systematic_risk=portfolio_volatility * 0.7,  # Oletus
            unsystematic_risk=portfolio_volatility * 0.3,  # Oletus
            diversification_ratio=diversification_ratio,
            portfolio_heat=portfolio_heat,
            risk_contribution=risk_contribution,
            correlation_matrix=correlation_matrix,
            risk_budget=risk_budget
        )
    
    def generate_risk_report(self, portfolio: Dict, market_data: Dict) -> Dict:
        """Generoi risk-raportti"""
        positions = portfolio.get("positions", {})
        
        # Laske perusmittarit
        risk_metrics = {}
        for symbol, position in positions.items():
            returns = position.get("returns", [])
            prices = position.get("prices", [])
            volume = position.get("volume", 0)
            market_cap = position.get("market_cap", 0)
            avg_volume = position.get("avg_volume", volume)
            
            risk_metrics[symbol] = RiskMetrics(
                var_95=self.calculate_var(returns, 0.95),
                var_99=self.calculate_var(returns, 0.99),
                expected_shortfall=self.calculate_expected_shortfall(returns, 0.95),
                max_drawdown=self.calculate_max_drawdown(prices),
                sharpe_ratio=self.calculate_sharpe_ratio(returns),
                sortino_ratio=self.calculate_sortino_ratio(returns),
                calmar_ratio=self.calculate_calmar_ratio(returns, prices),
                volatility=self.calculate_volatility(returns),
                beta=self.calculate_beta(returns, market_data.get("market_returns", [])),
                correlation=self.calculate_correlation(returns, market_data.get("market_returns", [])),
                liquidity_risk=self.calculate_liquidity_risk(volume, market_cap, avg_volume),
                concentration_risk=0.0,  # Lasketaan portfolio-tasolla
                tail_risk=self.calculate_tail_risk(returns),
                stress_test_score=0.0  # Lasketaan erikseen
            )
        
        # Laske portfolio risk
        portfolio_risk = self.calculate_portfolio_risk(portfolio, market_data)
        
        # Suorita stress testit
        stress_tests = {}
        for scenario in self.stress_scenarios.keys():
            stress_tests[scenario] = self.stress_test(portfolio, scenario)
        
        # Laske konsentraatioriski
        position_sizes = [position.get("value", 0) for position in positions.values()]
        concentration_risk = self.calculate_concentration_risk(position_sizes)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "portfolio_summary": {
                "total_positions": len(positions),
                "total_value": portfolio.get("total_value", 0),
                "portfolio_volatility": portfolio_risk.total_risk,
                "diversification_ratio": portfolio_risk.diversification_ratio,
                "portfolio_heat": portfolio_risk.portfolio_heat,
                "concentration_risk": concentration_risk
            },
            "position_risks": {
                symbol: asdict(metrics) for symbol, metrics in risk_metrics.items()
            },
            "portfolio_risk": asdict(portfolio_risk),
            "stress_tests": stress_tests,
            "recommendations": self._generate_risk_recommendations(portfolio_risk, risk_metrics)
        }
    
    def _generate_risk_recommendations(self, portfolio_risk: PortfolioRisk, risk_metrics: Dict) -> List[str]:
        """Generoi risk-suositukset"""
        recommendations = []
        
        # Portfolio heat
        if portfolio_risk.portfolio_heat > 0.8:
            recommendations.append("Portfolio heat liian korkea - vähennä position kokoja")
        elif portfolio_risk.portfolio_heat < 0.3:
            recommendations.append("Portfolio heat matala - voit lisätä position kokoja")
        
        # Diversifikaatio
        if portfolio_risk.diversification_ratio < 0.5:
            recommendations.append("Diversifikaatio heikko - lisää erilaisia tokeneita")
        
        # Konsentraatio
        if portfolio_risk.portfolio_heat > 0.7:
            recommendations.append("Konsentraatioriski korkea - hajauta sijoituksia")
        
        # Position-kohtaiset suositukset
        for symbol, metrics in risk_metrics.items():
            if metrics.var_99 > 0.2:
                recommendations.append(f"{symbol}: VaR 99% liian korkea - vähennä position kokoa")
            
            if metrics.liquidity_risk > 0.7:
                recommendations.append(f"{symbol}: Likviditeettiriski korkea - harkitse myyntiä")
            
            if metrics.volatility > 1.0:
                recommendations.append(f"{symbol}: Volatiliteetti liian korkea - lisää riskienhallintaa")
        
        return recommendations

# Esimerkki käytöstä
def example_usage():
    """Esimerkki risk assessmentin käytöstä"""
    risk_assessor = AdvancedRiskAssessment()
    
    # Simuloi portfolio
    portfolio = {
        "total_value": 10000,
        "positions": {
            "TOKEN1": {
                "value": 3000,
                "returns": np.random.normal(0.001, 0.05, 100).tolist(),
                "prices": [100 + i * 0.1 + np.random.normal(0, 5) for i in range(100)],
                "volume": 50000,
                "market_cap": 1000000,
                "avg_volume": 45000,
                "volatility": 0.3
            },
            "TOKEN2": {
                "value": 2000,
                "returns": np.random.normal(0.002, 0.08, 100).tolist(),
                "prices": [50 + i * 0.2 + np.random.normal(0, 3) for i in range(100)],
                "volume": 30000,
                "market_cap": 500000,
                "avg_volume": 25000,
                "volatility": 0.5
            }
        }
    }
    
    market_data = {
        "market_returns": np.random.normal(0.0005, 0.03, 100).tolist()
    }
    
    # Generoi risk-raportti
    report = risk_assessor.generate_risk_report(portfolio, market_data)
    print(f"Risk-raportti: {json.dumps(report, indent=2, default=str)}")

if __name__ == "__main__":
    example_usage()
