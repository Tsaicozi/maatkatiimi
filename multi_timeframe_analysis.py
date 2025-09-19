"""
Multi-Timeframe Analysis - Edistyneet aikakehys-analyysityökalut
Yhdistää useita aikakehyksiä parhaan analyysin saamiseksi
"""

import asyncio
import aiohttp
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Tuple
import yfinance as yf
import requests
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TimeframeData:
    """Aikakehys-data"""
    timeframe: str
    data: pd.DataFrame
    indicators: Dict[str, float]
    signals: Dict[str, str]
    trend: str
    strength: float
    confidence: float

@dataclass
class MultiTimeframeAnalysis:
    """Multi-timeframe analyysin tulos"""
    symbol: str
    timeframes: Dict[str, TimeframeData]
    overall_trend: str
    trend_strength: float
    trend_confidence: float
    entry_signals: List[str]
    exit_signals: List[str]
    support_resistance: Dict[str, float]
    volatility_analysis: Dict[str, float]
    momentum_analysis: Dict[str, float]
    volume_analysis: Dict[str, float]
    correlation_analysis: Dict[str, float]
    prediction: Dict[str, Any]
    risk_assessment: Dict[str, float]
    recommendations: List[str]

class MultiTimeframeAnalyzer:
    """Multi-timeframe analyysi"""
    
    def __init__(self):
        self.session = None
        self.timeframes = {
            "1m": {"period": "1d", "interval": "1m"},
            "5m": {"period": "1d", "interval": "5m"},
            "15m": {"period": "5d", "interval": "15m"},
            "1h": {"period": "30d", "interval": "1h"},
            "4h": {"period": "90d", "interval": "4h"},
            "1d": {"period": "1y", "interval": "1d"},
            "1w": {"period": "5y", "interval": "1wk"},
            "1M": {"period": "10y", "interval": "1mo"}
        }
        self.indicators = self._initialize_indicators()
        
    def _initialize_indicators(self) -> Dict:
        """Alusta teknisiä indikaattoreita"""
        return {
            "sma": {"periods": [5, 10, 20, 50, 100, 200]},
            "ema": {"periods": [5, 10, 20, 50, 100, 200]},
            "rsi": {"period": 14},
            "macd": {"fast": 12, "slow": 26, "signal": 9},
            "bollinger": {"period": 20, "std": 2},
            "stochastic": {"k_period": 14, "d_period": 3},
            "williams_r": {"period": 14},
            "cci": {"period": 20},
            "atr": {"period": 14},
            "adx": {"period": 14},
            "obv": {},
            "volume_sma": {"period": 20}
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def analyze_symbol(self, symbol: str) -> MultiTimeframeAnalysis:
        """Analysoi symboli useilla aikakehyksillä"""
        logger.info(f"Analysoidaan {symbol} multi-timeframe analyysillä...")
        
        timeframe_data = {}
        
        # Hae data jokaiselle aikakehykselle
        for tf_name, tf_config in self.timeframes.items():
            try:
                data = await self._fetch_timeframe_data(symbol, tf_config)
                if data is not None and not data.empty:
                    indicators = self._calculate_indicators(data)
                    signals = self._generate_signals(data, indicators)
                    trend, strength, confidence = self._analyze_trend(data, indicators)
                    
                    timeframe_data[tf_name] = TimeframeData(
                        timeframe=tf_name,
                        data=data,
                        indicators=indicators,
                        signals=signals,
                        trend=trend,
                        strength=strength,
                        confidence=confidence
                    )
                    
                    logger.info(f"✅ {tf_name}: {trend} (strength: {strength:.2f})")
                else:
                    logger.warning(f"⚠️ Ei dataa aikakehykselle {tf_name}")
            except Exception as e:
                logger.error(f"❌ Virhe aikakehyksessä {tf_name}: {e}")
        
        if not timeframe_data:
            logger.error(f"❌ Ei dataa symbolille {symbol}")
            return None
        
        # Yhdistä analyysit
        overall_analysis = self._combine_timeframe_analyses(symbol, timeframe_data)
        
        return overall_analysis
    
    async def _fetch_timeframe_data(self, symbol: str, config: Dict) -> Optional[pd.DataFrame]:
        """Hae aikakehys-data"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(
                period=config["period"],
                interval=config["interval"]
            )
            
            if data.empty:
                return None
            
            # Varmista että data on oikeassa muodossa
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_columns):
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Virhe datan haussa {symbol}: {e}")
            return None
    
    def _calculate_indicators(self, data: pd.DataFrame) -> Dict[str, float]:
        """Laske teknisiä indikaattoreita"""
        indicators = {}
        
        try:
            # SMA (Simple Moving Average)
            for period in self.indicators["sma"]["periods"]:
                if len(data) >= period:
                    indicators[f"sma_{period}"] = data['Close'].rolling(window=period).mean().iloc[-1]
            
            # EMA (Exponential Moving Average)
            for period in self.indicators["ema"]["periods"]:
                if len(data) >= period:
                    indicators[f"ema_{period}"] = data['Close'].ewm(span=period).mean().iloc[-1]
            
            # RSI (Relative Strength Index)
            if len(data) >= self.indicators["rsi"]["period"] + 1:
                indicators["rsi"] = self._calculate_rsi(data['Close'], self.indicators["rsi"]["period"])
            
            # MACD
            if len(data) >= self.indicators["macd"]["slow"]:
                macd_line, signal_line, histogram = self._calculate_macd(data['Close'])
                indicators["macd"] = macd_line
                indicators["macd_signal"] = signal_line
                indicators["macd_histogram"] = histogram
            
            # Bollinger Bands
            if len(data) >= self.indicators["bollinger"]["period"]:
                bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(data['Close'])
                indicators["bb_upper"] = bb_upper
                indicators["bb_middle"] = bb_middle
                indicators["bb_lower"] = bb_lower
                indicators["bb_width"] = (bb_upper - bb_lower) / bb_middle
            
            # Stochastic
            if len(data) >= self.indicators["stochastic"]["k_period"]:
                k_percent, d_percent = self._calculate_stochastic(data)
                indicators["stoch_k"] = k_percent
                indicators["stoch_d"] = d_percent
            
            # Williams %R
            if len(data) >= self.indicators["williams_r"]["period"]:
                indicators["williams_r"] = self._calculate_williams_r(data)
            
            # CCI (Commodity Channel Index)
            if len(data) >= self.indicators["cci"]["period"]:
                indicators["cci"] = self._calculate_cci(data)
            
            # ATR (Average True Range)
            if len(data) >= self.indicators["atr"]["period"]:
                indicators["atr"] = self._calculate_atr(data)
            
            # ADX (Average Directional Index)
            if len(data) >= self.indicators["adx"]["period"]:
                indicators["adx"] = self._calculate_adx(data)
            
            # OBV (On-Balance Volume)
            indicators["obv"] = self._calculate_obv(data)
            
            # Volume SMA
            if len(data) >= self.indicators["volume_sma"]["period"]:
                indicators["volume_sma"] = data['Volume'].rolling(window=self.indicators["volume_sma"]["period"]).mean().iloc[-1]
            
        except Exception as e:
            logger.error(f"Virhe indikaattoreiden laskennassa: {e}")
        
        return indicators
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Laske RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else 50.0
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[float, float, float]:
        """Laske MACD"""
        fast_ema = prices.ewm(span=self.indicators["macd"]["fast"]).mean()
        slow_ema = prices.ewm(span=self.indicators["macd"]["slow"]).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=self.indicators["macd"]["signal"]).mean()
        histogram = macd_line - signal_line
        
        return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]
    
    def _calculate_bollinger_bands(self, prices: pd.Series) -> Tuple[float, float, float]:
        """Laske Bollinger Bands"""
        period = self.indicators["bollinger"]["period"]
        std = self.indicators["bollinger"]["std"]
        
        sma = prices.rolling(window=period).mean()
        std_dev = prices.rolling(window=period).std()
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band.iloc[-1], sma.iloc[-1], lower_band.iloc[-1]
    
    def _calculate_stochastic(self, data: pd.DataFrame) -> Tuple[float, float]:
        """Laske Stochastic"""
        k_period = self.indicators["stochastic"]["k_period"]
        d_period = self.indicators["stochastic"]["d_period"]
        
        low_min = data['Low'].rolling(window=k_period).min()
        high_max = data['High'].rolling(window=k_period).max()
        
        k_percent = 100 * ((data['Close'] - low_min) / (high_max - low_min))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return k_percent.iloc[-1], d_percent.iloc[-1]
    
    def _calculate_williams_r(self, data: pd.DataFrame) -> float:
        """Laske Williams %R"""
        period = self.indicators["williams_r"]["period"]
        
        high_max = data['High'].rolling(window=period).max()
        low_min = data['Low'].rolling(window=period).min()
        
        williams_r = -100 * ((high_max - data['Close']) / (high_max - low_min))
        
        return williams_r.iloc[-1]
    
    def _calculate_cci(self, data: pd.DataFrame) -> float:
        """Laske CCI (Commodity Channel Index)"""
        period = self.indicators["cci"]["period"]
        
        typical_price = (data['High'] + data['Low'] + data['Close']) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())))
        
        cci = (typical_price - sma_tp) / (0.015 * mad)
        
        return cci.iloc[-1]
    
    def _calculate_atr(self, data: pd.DataFrame) -> float:
        """Laske ATR (Average True Range)"""
        period = self.indicators["atr"]["period"]
        
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        
        return atr.iloc[-1]
    
    def _calculate_adx(self, data: pd.DataFrame) -> float:
        """Laske ADX (Average Directional Index)"""
        period = self.indicators["adx"]["period"]
        
        high_diff = data['High'].diff()
        low_diff = data['Low'].diff()
        
        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
        
        plus_dm = pd.Series(plus_dm, index=data.index)
        minus_dm = pd.Series(minus_dm, index=data.index)
        
        atr = self._calculate_atr(data)
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx.iloc[-1]
    
    def _calculate_obv(self, data: pd.DataFrame) -> float:
        """Laske OBV (On-Balance Volume)"""
        obv = np.where(data['Close'] > data['Close'].shift(), data['Volume'], 
                      np.where(data['Close'] < data['Close'].shift(), -data['Volume'], 0))
        obv = pd.Series(obv, index=data.index).cumsum()
        
        return obv.iloc[-1]
    
    def _generate_signals(self, data: pd.DataFrame, indicators: Dict[str, float]) -> Dict[str, str]:
        """Generoi kauppasignaaleja"""
        signals = {}
        current_price = data['Close'].iloc[-1]
        
        # Trend signals
        if 'sma_20' in indicators and 'sma_50' in indicators:
            if indicators['sma_20'] > indicators['sma_50']:
                signals['trend'] = 'bullish'
            elif indicators['sma_20'] < indicators['sma_50']:
                signals['trend'] = 'bearish'
            else:
                signals['trend'] = 'neutral'
        
        # RSI signals
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if rsi > 70:
                signals['rsi'] = 'overbought'
            elif rsi < 30:
                signals['rsi'] = 'oversold'
            else:
                signals['rsi'] = 'neutral'
        
        # MACD signals
        if 'macd' in indicators and 'macd_signal' in indicators:
            if indicators['macd'] > indicators['macd_signal']:
                signals['macd'] = 'bullish'
            else:
                signals['macd'] = 'bearish'
        
        # Bollinger Bands signals
        if 'bb_upper' in indicators and 'bb_lower' in indicators:
            if current_price > indicators['bb_upper']:
                signals['bollinger'] = 'overbought'
            elif current_price < indicators['bb_lower']:
                signals['bollinger'] = 'oversold'
            else:
                signals['bollinger'] = 'neutral'
        
        # Stochastic signals
        if 'stoch_k' in indicators and 'stoch_d' in indicators:
            if indicators['stoch_k'] > 80 and indicators['stoch_d'] > 80:
                signals['stochastic'] = 'overbought'
            elif indicators['stoch_k'] < 20 and indicators['stoch_d'] < 20:
                signals['stochastic'] = 'oversold'
            else:
                signals['stochastic'] = 'neutral'
        
        # Volume signals
        if 'volume_sma' in indicators:
            current_volume = data['Volume'].iloc[-1]
            if current_volume > indicators['volume_sma'] * 1.5:
                signals['volume'] = 'high'
            elif current_volume < indicators['volume_sma'] * 0.5:
                signals['volume'] = 'low'
            else:
                signals['volume'] = 'normal'
        
        return signals
    
    def _analyze_trend(self, data: pd.DataFrame, indicators: Dict[str, float]) -> Tuple[str, float, float]:
        """Analysoi trendi"""
        if len(data) < 20:
            return "insufficient_data", 0.0, 0.0
        
        # Laske trendi useilla menetelmillä
        trend_scores = []
        
        # Price trend
        price_change = (data['Close'].iloc[-1] - data['Close'].iloc[-20]) / data['Close'].iloc[-20]
        if price_change > 0.05:
            trend_scores.append(1.0)
        elif price_change < -0.05:
            trend_scores.append(-1.0)
        else:
            trend_scores.append(0.0)
        
        # Moving average trend
        if 'sma_20' in indicators and 'sma_50' in indicators:
            if indicators['sma_20'] > indicators['sma_50']:
                trend_scores.append(1.0)
            else:
                trend_scores.append(-1.0)
        
        # MACD trend
        if 'macd' in indicators and 'macd_signal' in indicators:
            if indicators['macd'] > indicators['macd_signal']:
                trend_scores.append(1.0)
            else:
                trend_scores.append(-1.0)
        
        # ADX trend strength
        if 'adx' in indicators:
            adx = indicators['adx']
            if adx > 25:
                trend_scores.append(1.0 if trend_scores[-1] > 0 else -1.0)
            else:
                trend_scores.append(0.0)
        
        # Laske keskiarvo
        avg_trend = np.mean(trend_scores)
        trend_strength = abs(avg_trend)
        
        # Määritä trendi
        if avg_trend > 0.3:
            trend = "bullish"
        elif avg_trend < -0.3:
            trend = "bearish"
        else:
            trend = "neutral"
        
        # Laske luottamus
        confidence = min(trend_strength * 2, 1.0)
        
        return trend, trend_strength, confidence
    
    def _combine_timeframe_analyses(self, symbol: str, timeframe_data: Dict[str, TimeframeData]) -> MultiTimeframeAnalysis:
        """Yhdistä aikakehys-analyysit"""
        # Laske overall trend
        trends = [data.trend for data in timeframe_data.values()]
        trend_counts = {trend: trends.count(trend) for trend in set(trends)}
        overall_trend = max(trend_counts, key=trend_counts.get)
        
        # Laske trend strength
        trend_strengths = [data.strength for data in timeframe_data.values()]
        trend_strength = np.mean(trend_strengths)
        
        # Laske trend confidence
        trend_confidences = [data.confidence for data in timeframe_data.values()]
        trend_confidence = np.mean(trend_confidences)
        
        # Generoi signaalit
        entry_signals = self._generate_entry_signals(timeframe_data)
        exit_signals = self._generate_exit_signals(timeframe_data)
        
        # Laske support ja resistance
        support_resistance = self._calculate_support_resistance(timeframe_data)
        
        # Volatiliteettianalyysi
        volatility_analysis = self._analyze_volatility(timeframe_data)
        
        # Momentum-analyysi
        momentum_analysis = self._analyze_momentum(timeframe_data)
        
        # Volyymi-analyysi
        volume_analysis = self._analyze_volume(timeframe_data)
        
        # Korrelaatio-analyysi
        correlation_analysis = self._analyze_correlations(timeframe_data)
        
        # Ennuste
        prediction = self._generate_prediction(timeframe_data)
        
        # Riskienarviointi
        risk_assessment = self._assess_risks(timeframe_data)
        
        # Suositukset
        recommendations = self._generate_recommendations(
            overall_trend, trend_strength, trend_confidence, 
            entry_signals, exit_signals, risk_assessment
        )
        
        return MultiTimeframeAnalysis(
            symbol=symbol,
            timeframes=timeframe_data,
            overall_trend=overall_trend,
            trend_strength=trend_strength,
            trend_confidence=trend_confidence,
            entry_signals=entry_signals,
            exit_signals=exit_signals,
            support_resistance=support_resistance,
            volatility_analysis=volatility_analysis,
            momentum_analysis=momentum_analysis,
            volume_analysis=volume_analysis,
            correlation_analysis=correlation_analysis,
            prediction=prediction,
            risk_assessment=risk_assessment,
            recommendations=recommendations
        )
    
    def _generate_entry_signals(self, timeframe_data: Dict[str, TimeframeData]) -> List[str]:
        """Generoi entry-signaalit"""
        signals = []
        
        # Tarkista trendi eri aikakehyksissä
        bullish_timeframes = [tf for tf, data in timeframe_data.items() if data.trend == "bullish"]
        bearish_timeframes = [tf for tf, data in timeframe_data.items() if data.trend == "bearish"]
        
        if len(bullish_timeframes) >= 3:
            signals.append("Multi-timeframe bullish alignment")
        
        if len(bearish_timeframes) >= 3:
            signals.append("Multi-timeframe bearish alignment")
        
        # Tarkista RSI oversold/overbought
        oversold_count = 0
        overbought_count = 0
        
        for tf, data in timeframe_data.items():
            if 'rsi' in data.indicators:
                rsi = data.indicators['rsi']
                if rsi < 30:
                    oversold_count += 1
                elif rsi > 70:
                    overbought_count += 1
        
        if oversold_count >= 2:
            signals.append("Multi-timeframe RSI oversold")
        
        if overbought_count >= 2:
            signals.append("Multi-timeframe RSI overbought")
        
        return signals
    
    def _generate_exit_signals(self, timeframe_data: Dict[str, TimeframeData]) -> List[str]:
        """Generoi exit-signaalit"""
        signals = []
        
        # Tarkista trendin kääntyminen
        recent_trends = []
        for tf, data in timeframe_data.items():
            if tf in ['1h', '4h', '1d']:  # Keskipitkät aikakehykset
                recent_trends.append(data.trend)
        
        if len(set(recent_trends)) > 1:  # Trendi kääntyy
            signals.append("Trend divergence detected")
        
        # Tarkista volyymi
        low_volume_count = 0
        for tf, data in timeframe_data.items():
            if 'volume' in data.signals and data.signals['volume'] == 'low':
                low_volume_count += 1
        
        if low_volume_count >= 2:
            signals.append("Low volume across timeframes")
        
        return signals
    
    def _calculate_support_resistance(self, timeframe_data: Dict[str, TimeframeData]) -> Dict[str, float]:
        """Laske support ja resistance"""
        support_resistance = {}
        
        # Käytä 1d aikakehystä support/resistance laskentaan
        if '1d' in timeframe_data:
            data = timeframe_data['1d'].data
            
            # Laske pivot points
            high = data['High'].iloc[-20:].max()
            low = data['Low'].iloc[-20:].min()
            close = data['Close'].iloc[-1]
            
            # Pivot Point
            pivot = (high + low + close) / 3
            
            # Support levels
            support_resistance['support_1'] = 2 * pivot - high
            support_resistance['support_2'] = pivot - (high - low)
            support_resistance['support_3'] = low - 2 * (high - pivot)
            
            # Resistance levels
            support_resistance['resistance_1'] = 2 * pivot - low
            support_resistance['resistance_2'] = pivot + (high - low)
            support_resistance['resistance_3'] = high + 2 * (pivot - low)
            
            # Current price
            support_resistance['current_price'] = close
        
        return support_resistance
    
    def _analyze_volatility(self, timeframe_data: Dict[str, TimeframeData]) -> Dict[str, float]:
        """Analysoi volatiliteettia"""
        volatility_analysis = {}
        
        for tf, data in timeframe_data.items():
            if len(data.data) > 20:
                # Laske ATR
                if 'atr' in data.indicators:
                    volatility_analysis[f'{tf}_atr'] = data.indicators['atr']
                
                # Laske price volatility
                returns = data.data['Close'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)  # Annualized
                volatility_analysis[f'{tf}_volatility'] = volatility
        
        return volatility_analysis
    
    def _analyze_momentum(self, timeframe_data: Dict[str, TimeframeData]) -> Dict[str, float]:
        """Analysoi momentumia"""
        momentum_analysis = {}
        
        for tf, data in timeframe_data.items():
            if 'rsi' in data.indicators:
                momentum_analysis[f'{tf}_rsi'] = data.indicators['rsi']
            
            if 'macd' in data.indicators:
                momentum_analysis[f'{tf}_macd'] = data.indicators['macd']
            
            if 'stoch_k' in data.indicators:
                momentum_analysis[f'{tf}_stoch'] = data.indicators['stoch_k']
        
        return momentum_analysis
    
    def _analyze_volume(self, timeframe_data: Dict[str, TimeframeData]) -> Dict[str, float]:
        """Analysoi volyymiä"""
        volume_analysis = {}
        
        for tf, data in timeframe_data.items():
            if 'volume_sma' in data.indicators:
                current_volume = data.data['Volume'].iloc[-1]
                volume_ratio = current_volume / data.indicators['volume_sma']
                volume_analysis[f'{tf}_volume_ratio'] = volume_ratio
            
            if 'obv' in data.indicators:
                volume_analysis[f'{tf}_obv'] = data.indicators['obv']
        
        return volume_analysis
    
    def _analyze_correlations(self, timeframe_data: Dict[str, TimeframeData]) -> Dict[str, float]:
        """Analysoi korrelaatioita aikakehysten välillä"""
        correlation_analysis = {}
        
        # Kerää hinnat eri aikakehyksistä
        prices = {}
        for tf, data in timeframe_data.items():
            if len(data.data) > 50:
                prices[tf] = data.data['Close'].iloc[-50:].values
        
        # Laske korrelaatiot
        if len(prices) > 1:
            price_df = pd.DataFrame(prices)
            correlation_matrix = price_df.corr()
            
            for tf1 in correlation_matrix.columns:
                for tf2 in correlation_matrix.columns:
                    if tf1 != tf2:
                        correlation_analysis[f'{tf1}_{tf2}'] = correlation_matrix.loc[tf1, tf2]
        
        return correlation_analysis
    
    def _generate_prediction(self, timeframe_data: Dict[str, TimeframeData]) -> Dict[str, Any]:
        """Generoi ennuste"""
        prediction = {
            "short_term": "neutral",  # 1-7 päivää
            "medium_term": "neutral",  # 1-4 viikkoa
            "long_term": "neutral",   # 1-12 kuukautta
            "confidence": 0.0,
            "target_price": 0.0,
            "stop_loss": 0.0
        }
        
        # Käytä 1d aikakehystä ennusteeseen
        if '1d' in timeframe_data:
            data = timeframe_data['1d']
            current_price = data.data['Close'].iloc[-1]
            
            # Yksinkertainen trendi-ennuste
            if data.trend == "bullish" and data.strength > 0.6:
                prediction["short_term"] = "bullish"
                prediction["target_price"] = current_price * 1.1
                prediction["stop_loss"] = current_price * 0.95
            elif data.trend == "bearish" and data.strength > 0.6:
                prediction["short_term"] = "bearish"
                prediction["target_price"] = current_price * 0.9
                prediction["stop_loss"] = current_price * 1.05
            
            prediction["confidence"] = data.confidence
        
        return prediction
    
    def _assess_risks(self, timeframe_data: Dict[str, TimeframeData]) -> Dict[str, float]:
        """Arvioi riskejä"""
        risk_assessment = {
            "volatility_risk": 0.0,
            "trend_risk": 0.0,
            "volume_risk": 0.0,
            "technical_risk": 0.0,
            "overall_risk": 0.0
        }
        
        # Volatiliteettiriski
        volatility_risks = []
        for tf, data in timeframe_data.items():
            if f'{tf}_volatility' in data.indicators:
                volatility_risks.append(data.indicators[f'{tf}_volatility'])
        
        if volatility_risks:
            risk_assessment["volatility_risk"] = min(np.mean(volatility_risks), 1.0)
        
        # Trend-riski
        trend_confidences = [data.confidence for data in timeframe_data.values()]
        risk_assessment["trend_risk"] = 1.0 - np.mean(trend_confidences)
        
        # Volyymi-riski
        volume_risks = []
        for tf, data in timeframe_data.items():
            if 'volume' in data.signals and data.signals['volume'] == 'low':
                volume_risks.append(0.8)
            else:
                volume_risks.append(0.2)
        
        risk_assessment["volume_risk"] = np.mean(volume_risks)
        
        # Tekninen riski
        technical_risks = []
        for tf, data in timeframe_data.items():
            if 'rsi' in data.indicators:
                rsi = data.indicators['rsi']
                if rsi > 80 or rsi < 20:
                    technical_risks.append(0.7)
                else:
                    technical_risks.append(0.3)
        
        if technical_risks:
            risk_assessment["technical_risk"] = np.mean(technical_risks)
        
        # Kokonaisriski
        risk_assessment["overall_risk"] = np.mean([
            risk_assessment["volatility_risk"],
            risk_assessment["trend_risk"],
            risk_assessment["volume_risk"],
            risk_assessment["technical_risk"]
        ])
        
        return risk_assessment
    
    def _generate_recommendations(self, overall_trend: str, trend_strength: float, 
                                trend_confidence: float, entry_signals: List[str], 
                                exit_signals: List[str], risk_assessment: Dict[str, float]) -> List[str]:
        """Generoi suositukset"""
        recommendations = []
        
        # Trend-suositukset
        if overall_trend == "bullish" and trend_strength > 0.6 and trend_confidence > 0.7:
            recommendations.append("Strong bullish trend - consider long position")
        elif overall_trend == "bearish" and trend_strength > 0.6 and trend_confidence > 0.7:
            recommendations.append("Strong bearish trend - consider short position")
        elif trend_strength < 0.3:
            recommendations.append("Weak trend - wait for clearer direction")
        
        # Entry-signaalit
        if "Multi-timeframe bullish alignment" in entry_signals:
            recommendations.append("Multiple timeframes align bullish - strong buy signal")
        if "Multi-timeframe RSI oversold" in entry_signals:
            recommendations.append("RSI oversold across timeframes - potential bounce")
        
        # Exit-signaalit
        if "Trend divergence detected" in exit_signals:
            recommendations.append("Trend divergence - consider reducing position")
        if "Low volume across timeframes" in exit_signals:
            recommendations.append("Low volume - weak conviction")
        
        # Risk-suositukset
        if risk_assessment["overall_risk"] > 0.7:
            recommendations.append("High risk detected - reduce position size")
        elif risk_assessment["overall_risk"] < 0.3:
            recommendations.append("Low risk environment - can increase position size")
        
        return recommendations

# Esimerkki käytöstä
async def example_usage():
    """Esimerkki multi-timeframe analyysin käytöstä"""
    async with MultiTimeframeAnalyzer() as analyzer:
        symbol = "BTC-USD"
        
        # Analysoi symboli
        analysis = await analyzer.analyze_symbol(symbol)
        
        if analysis:
            print(f"Symbol: {analysis.symbol}")
            print(f"Overall Trend: {analysis.overall_trend}")
            print(f"Trend Strength: {analysis.trend_strength:.2f}")
            print(f"Trend Confidence: {analysis.trend_confidence:.2f}")
            print(f"Entry Signals: {analysis.entry_signals}")
            print(f"Exit Signals: {analysis.exit_signals}")
            print(f"Recommendations: {analysis.recommendations}")
        else:
            print("Analyysi epäonnistui")

if __name__ == "__main__":
    asyncio.run(example_usage())
