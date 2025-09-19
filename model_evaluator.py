"""
Mallin Arviointi -järjestelmä - Riskienhallintasuositusten Implementointi
=======================================================================

Tämä moduuli sisältää työkalut mallien luotettavuuden ja tarkkuuden arviointiin.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings('ignore')

class ModelEvaluator:
    """Mallin arviointi -järjestelmä"""
    
    def __init__(self):
        self.evaluation_metrics = {
            "accuracy_threshold": 0.6,      # 60% tarkkuus
            "overfitting_threshold": 0.15,  # 15% ero train/test välillä
            "stability_threshold": 0.1      # 10% vaihtelu ajan myötä
        }
    
    def evaluate_model_performance(self, symbol: str, model_type: str = "ml_prediction", 
                                 period: str = "2y") -> Dict:
        """
        Arvioi mallin suorituskykyä
        
        Args:
            symbol: Osakkeen symboli
            model_type: Mallin tyyppi
            period: Aikajakso analyysille
        
        Returns:
            Dict sisältäen mallin arvioinnin
        """
        try:
            # Hae data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty or len(hist) < 100:
                return {"error": f"Liian vähän dataa symbolille {symbol}"}
            
            # Laske perusmittarit
            basic_metrics = self._calculate_basic_metrics(hist)
            
            # Arvioi mallin tarkkuus
            accuracy_metrics = self._evaluate_accuracy(hist)
            
            # Tarkista overfitting
            overfitting_analysis = self._check_overfitting(hist)
            
            # Arvioi stabiilisuus
            stability_analysis = self._evaluate_stability(hist)
            
            # Laske yleinen luotettavuuspisteet
            reliability_score = self._calculate_reliability_score(
                accuracy_metrics, overfitting_analysis, stability_analysis
            )
            
            # Anna suositukset
            recommendations = self._get_model_recommendations(
                accuracy_metrics, overfitting_analysis, stability_analysis, reliability_score
            )
            
            return {
                "symbol": symbol,
                "model_type": model_type,
                "evaluation_date": datetime.now().isoformat(),
                "basic_metrics": basic_metrics,
                "accuracy_metrics": accuracy_metrics,
                "overfitting_analysis": overfitting_analysis,
                "stability_analysis": stability_analysis,
                "reliability_score": reliability_score,
                "recommendations": recommendations
            }
            
        except Exception as e:
            return {"error": f"Virhe mallin arvioinnissa: {str(e)}"}
    
    def _calculate_basic_metrics(self, hist: pd.DataFrame) -> Dict:
        """Laske perusmittarit"""
        returns = hist['Close'].pct_change().dropna()
        volume = hist['Volume']
        
        return {
            "total_days": len(hist),
            "avg_daily_return": returns.mean(),
            "volatility": returns.std() * np.sqrt(252),
            "sharpe_ratio": (returns.mean() * 252) / (returns.std() * np.sqrt(252)),
            "max_drawdown": self._calculate_max_drawdown(returns),
            "avg_volume": volume.mean(),
            "volume_volatility": volume.pct_change().std()
        }
    
    def _evaluate_accuracy(self, hist: pd.DataFrame) -> Dict:
        """Arvioi mallin tarkkuus"""
        # Yksinkertainen ennustemalli: moving average
        prices = hist['Close']
        
        # Käytä 20 päivän moving averagea ennusteena
        ma_20 = prices.rolling(20).mean()
        predictions = ma_20.shift(1)  # Ennuste seuraavalle päivälle
        
        # Laske virheet
        actual = prices[20:]  # Poista ensimmäiset 20 päivää
        pred = predictions[20:].dropna()
        
        # Yhdistä samat indeksit
        common_idx = actual.index.intersection(pred.index)
        actual = actual.loc[common_idx]
        pred = pred.loc[common_idx]
        
        if len(actual) == 0 or len(pred) == 0:
            return {"error": "Ei dataa tarkkuuden laskemiseen"}
        
        # Laske mittarit
        mse = mean_squared_error(actual, pred)
        mae = mean_absolute_error(actual, pred)
        rmse = np.sqrt(mse)
        
        # Laske suhteellinen virhe
        mape = np.mean(np.abs((actual - pred) / actual)) * 100
        
        # Laske suunta-tarkkuus (nouseva/laskeva)
        actual_direction = np.sign(actual.diff())
        pred_direction = np.sign(pred.diff())
        direction_accuracy = (actual_direction == pred_direction).mean()
        
        # Laske R²
        r2 = r2_score(actual, pred)
        
        return {
            "mse": mse,
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "direction_accuracy": direction_accuracy,
            "r2_score": r2,
            "accuracy_level": self._get_accuracy_level(direction_accuracy, mape)
        }
    
    def _check_overfitting(self, hist: pd.DataFrame) -> Dict:
        """Tarkista overfitting"""
        prices = hist['Close']
        
        # Jaa data train/test -osioihin
        split_point = int(len(prices) * 0.7)
        train_data = prices[:split_point]
        test_data = prices[split_point:]
        
        if len(train_data) < 20 or len(test_data) < 20:
            return {"error": "Liian vähän dataa overfitting-analyysiin"}
        
        # Laske moving average -mallit
        ma_5 = train_data.rolling(5).mean()
        ma_10 = train_data.rolling(10).mean()
        ma_20 = train_data.rolling(20).mean()
        
        # Testaa eri parametreilla
        models = {
            "ma_5": ma_5,
            "ma_10": ma_10,
            "ma_20": ma_20
        }
        
        overfitting_results = {}
        
        for model_name, model in models.items():
            # Laske train-asetukset
            train_predictions = model.shift(1)
            train_actual = train_data[10:]  # Poista ensimmäiset päivät
            
            # Laske test-asetukset
            test_model = test_data.rolling(int(model_name.split('_')[1])).mean()
            test_predictions = test_model.shift(1)
            test_actual = test_data[10:]
            
            # Laske virheet
            train_error = self._calculate_prediction_error(train_actual, train_predictions)
            test_error = self._calculate_prediction_error(test_actual, test_predictions)
            
            # Laske overfitting-mittari
            overfitting_ratio = (test_error - train_error) / train_error if train_error > 0 else 0
            
            overfitting_results[model_name] = {
                "train_error": train_error,
                "test_error": test_error,
                "overfitting_ratio": overfitting_ratio,
                "overfitting_level": self._get_overfitting_level(overfitting_ratio)
            }
        
        # Valitse paras malli
        best_model = min(overfitting_results.keys(), 
                        key=lambda k: overfitting_results[k]["test_error"])
        
        return {
            "model_results": overfitting_results,
            "best_model": best_model,
            "overfitting_risk": self._assess_overfitting_risk(overfitting_results)
        }
    
    def _evaluate_stability(self, hist: pd.DataFrame) -> Dict:
        """Arvioi mallin stabiilisuus ajan myötä"""
        prices = hist['Close']
        
        # Jaa data 4 osaan
        chunk_size = len(prices) // 4
        chunks = [prices[i:i+chunk_size] for i in range(0, len(prices), chunk_size)]
        
        if len(chunks) < 4:
            return {"error": "Liian vähän dataa stabiilisuusanalyysiin"}
        
        # Laske jokaiselle osalle moving average -malli
        chunk_models = []
        for chunk in chunks:
            if len(chunk) >= 20:
                ma_model = chunk.rolling(20).mean()
                chunk_models.append(ma_model)
        
        if len(chunk_models) < 2:
            return {"error": "Liian vähän validia dataa stabiilisuusanalyysiin"}
        
        # Laske mallien välinen vaihtelu
        model_variations = []
        for i in range(len(chunk_models) - 1):
            model1 = chunk_models[i]
            model2 = chunk_models[i + 1]
            
            # Laske korrelaatio
            common_idx = model1.index.intersection(model2.index)
            if len(common_idx) > 10:
                corr = model1.loc[common_idx].corr(model2.loc[common_idx])
                model_variations.append(corr)
        
        if not model_variations:
            return {"error": "Ei dataa stabiilisuusanalyysiin"}
        
        # Laske stabiilisuusmittarit
        avg_correlation = np.mean(model_variations)
        stability_volatility = np.std(model_variations)
        
        return {
            "model_correlations": model_variations,
            "average_correlation": avg_correlation,
            "stability_volatility": stability_volatility,
            "stability_level": self._get_stability_level(avg_correlation, stability_volatility)
        }
    
    def _calculate_prediction_error(self, actual: pd.Series, predictions: pd.Series) -> float:
        """Laske ennustevirhe"""
        common_idx = actual.index.intersection(predictions.index)
        if len(common_idx) == 0:
            return float('inf')
        
        actual_common = actual.loc[common_idx]
        pred_common = predictions.loc[common_idx].dropna()
        
        if len(pred_common) == 0:
            return float('inf')
        
        # Laske MAPE
        mape = np.mean(np.abs((actual_common - pred_common) / actual_common)) * 100
        return mape
    
    def _get_accuracy_level(self, direction_accuracy: float, mape: float) -> str:
        """Määritä tarkkuuden taso"""
        if direction_accuracy > 0.6 and mape < 5:
            return "Korkea"
        elif direction_accuracy > 0.5 and mape < 10:
            return "Kohtalainen"
        else:
            return "Matala"
    
    def _get_overfitting_level(self, overfitting_ratio: float) -> str:
        """Määritä overfittingin taso"""
        if overfitting_ratio > self.evaluation_metrics["overfitting_threshold"]:
            return "Korkea"
        elif overfitting_ratio > 0.05:
            return "Kohtalainen"
        else:
            return "Matala"
    
    def _get_stability_level(self, avg_correlation: float, stability_volatility: float) -> str:
        """Määritä stabiilisuuden taso"""
        if avg_correlation > 0.8 and stability_volatility < 0.1:
            return "Korkea"
        elif avg_correlation > 0.6 and stability_volatility < 0.2:
            return "Kohtalainen"
        else:
            return "Matala"
    
    def _assess_overfitting_risk(self, overfitting_results: Dict) -> str:
        """Arvioi yleinen overfitting-riski"""
        overfitting_ratios = [result["overfitting_ratio"] for result in overfitting_results.values()]
        avg_overfitting = np.mean(overfitting_ratios)
        
        if avg_overfitting > self.evaluation_metrics["overfitting_threshold"]:
            return "Korkea"
        elif avg_overfitting > 0.05:
            return "Kohtalainen"
        else:
            return "Matala"
    
    def _calculate_reliability_score(self, accuracy_metrics: Dict, 
                                   overfitting_analysis: Dict, 
                                   stability_analysis: Dict) -> Dict:
        """Laske yleinen luotettavuuspisteet"""
        # Tarkkuuspisteet (0-40)
        direction_accuracy = accuracy_metrics.get("direction_accuracy", 0)
        mape = accuracy_metrics.get("mape", 100)
        accuracy_score = (direction_accuracy * 20) + max(0, 20 - mape)
        
        # Overfitting-pisteet (0-30)
        overfitting_risk = overfitting_analysis.get("overfitting_risk", "Korkea")
        overfitting_scores = {"Matala": 30, "Kohtalainen": 15, "Korkea": 0}
        overfitting_score = overfitting_scores.get(overfitting_risk, 0)
        
        # Stabiilisuuspisteet (0-30)
        stability_level = stability_analysis.get("stability_level", "Matala")
        stability_scores = {"Korkea": 30, "Kohtalainen": 15, "Matala": 0}
        stability_score = stability_scores.get(stability_level, 0)
        
        total_score = accuracy_score + overfitting_score + stability_score
        max_score = 100
        
        reliability_percentage = (total_score / max_score) * 100
        
        return {
            "accuracy_score": accuracy_score,
            "overfitting_score": overfitting_score,
            "stability_score": stability_score,
            "total_score": total_score,
            "reliability_percentage": reliability_percentage,
            "reliability_level": self._get_reliability_level(reliability_percentage)
        }
    
    def _get_reliability_level(self, reliability_percentage: float) -> str:
        """Määritä luotettavuuden taso"""
        if reliability_percentage >= 80:
            return "Korkea"
        elif reliability_percentage >= 60:
            return "Kohtalainen"
        else:
            return "Matala"
    
    def _get_model_recommendations(self, accuracy_metrics: Dict, 
                                 overfitting_analysis: Dict, 
                                 stability_analysis: Dict, 
                                 reliability_score: Dict) -> List[str]:
        """Anna suositukset mallin perusteella"""
        recommendations = []
        
        # Tarkkuussuositukset
        accuracy_level = accuracy_metrics.get("accuracy_level", "Matala")
        direction_accuracy = accuracy_metrics.get("direction_accuracy", 0)
        mape = accuracy_metrics.get("mape", 100)
        
        if accuracy_level == "Matala":
            recommendations.extend([
                "VAROITUS: Matala mallin tarkkuus",
                "Harkitse mallin parametrien säätämistä",
                "Lisää enemmän dataa koulutukseen",
                "Tarkista datan laatu"
            ])
        elif accuracy_level == "Kohtalainen":
            recommendations.extend([
                "Kohtalainen mallin tarkkuus",
                "Harkitse mallin parantamista",
                "Seuraa suorituskykyä tarkemmin"
            ])
        else:
            recommendations.append("Hyvä mallin tarkkuus - jatka nykyistä strategiaa")
        
        # Overfitting-suositukset
        overfitting_risk = overfitting_analysis.get("overfitting_risk", "Korkea")
        if overfitting_risk == "Korkea":
            recommendations.extend([
                "VAROITUS: Korkea overfitting-riski",
                "Vähennä mallin monimutkaisuutta",
                "Lisää regularisointia",
                "Käytä cross-validationia"
            ])
        elif overfitting_risk == "Kohtalainen":
            recommendations.extend([
                "Kohtalainen overfitting-riski",
                "Seuraa mallin suorituskykyä test-datalla",
                "Harkitse mallin yksinkertaistamista"
            ])
        
        # Stabiilisuussuositukset
        stability_level = stability_analysis.get("stability_level", "Matala")
        if stability_level == "Matala":
            recommendations.extend([
                "VAROITUS: Matala mallin stabiilisuus",
                "Malli vaihtelee paljon ajan myötä",
                "Harkitse adaptiivisia malleja",
                "Seuraa mallin suorituskykyä säännöllisesti"
            ])
        elif stability_level == "Kohtalainen":
            recommendations.extend([
                "Kohtalainen mallin stabiilisuus",
                "Seuraa mallin suorituskykyä",
                "Harkitse säännöllistä uudelleenkoulutusta"
            ])
        
        # Yleiset suositukset
        reliability_level = reliability_score.get("reliability_level", "Matala")
        if reliability_level == "Matala":
            recommendations.append("YLEINEN SUOSITUS: Mallin luotettavuus on matala - harkitse vaihtoehtoja")
        elif reliability_level == "Kohtalainen":
            recommendations.append("YLEINEN SUOSITUS: Mallin luotettavuus on kohtalainen - seuraa tarkemmin")
        else:
            recommendations.append("YLEINEN SUOSITUS: Mallin luotettavuus on hyvä - jatka nykyistä strategiaa")
        
        return recommendations
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Laske maksimi drawdown"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()

def main():
    """Esimerkki käytöstä"""
    print("🔍 Mallin Arviointi - Esimerkki käytöstä")
    print("=" * 45)
    
    evaluator = ModelEvaluator()
    
    # Arvioi mallin suorituskykyä
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    for symbol in symbols:
        print(f"\n{symbol} - Mallin Arviointi:")
        print("-" * 30)
        
        results = evaluator.evaluate_model_performance(symbol)
        
        if "error" not in results:
            reliability = results["reliability_score"]
            print(f"Luotettavuus: {reliability['reliability_level']} ({reliability['reliability_percentage']:.1f}%)")
            
            accuracy = results["accuracy_metrics"]
            print(f"Tarkkuus: {accuracy['accuracy_level']} (Suunta: {accuracy['direction_accuracy']:.3f})")
            
            overfitting = results["overfitting_analysis"]
            print(f"Overfitting-riski: {overfitting['overfitting_risk']}")
            
            stability = results["stability_analysis"]
            print(f"Stabiilisuus: {stability['stability_level']}")
            
            print("Suositukset:")
            for rec in results["recommendations"][:3]:
                print(f"- {rec}")
        else:
            print(f"Virhe: {results['error']}")

if __name__ == "__main__":
    main()
