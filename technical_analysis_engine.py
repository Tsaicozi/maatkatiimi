"""
Technical Analysis Engine - Kehittynyt tekninen analyysi ja trendi tunnistus
Täydentää NextGen Token Scanner Bot:ia
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
# import talib  # Kommentoitu pois koska ei ole asennettu
from datetime import datetime, timedelta
import logging

@dataclass
class TechnicalIndicators:
    """Tekniset indikaattorit"""
    sma_20: float
    sma_50: float
    ema_12: float
    ema_26: float
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    bollinger_upper: float
    bollinger_middle: float
    bollinger_lower: float
    volume_sma: float
    atr: float
    stoch_k: float
    stoch_d: float
    williams_r: float
    cci: float
    adx: float
    obv: float

@dataclass
class TrendAnalysis:
    """Trendi analyysi"""
    trend_direction: str  # 'BULLISH', 'BEARISH', 'SIDEWAYS'
    trend_strength: float  # 0-100
    support_levels: List[float]
    resistance_levels: List[float]
    breakout_probability: float
    reversal_signals: List[str]
    momentum_score: float

@dataclass
class PatternRecognition:
    """Kuvio tunnistus"""
    patterns: List[str]
    pattern_confidence: List[float]
    breakout_targets: List[float]
    stop_loss_levels: List[float]

class TechnicalAnalysisEngine:
    """Kehittynyt tekninen analyysi moottori"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_rsi_simple(self, prices, period=14):
        """Laske RSI yksinkertaistettu"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_atr_simple(self, ohlcv_data, period=14):
        """Laske ATR yksinkertaistettu"""
        high = ohlcv_data['high']
        low = ohlcv_data['low']
        close = ohlcv_data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    def calculate_stochastic_simple(self, ohlcv_data, k_period=14, d_period=3):
        """Laske Stochastic yksinkertaistettu"""
        low_min = ohlcv_data['low'].rolling(window=k_period).min()
        high_max = ohlcv_data['high'].rolling(window=k_period).max()
        
        k_percent = 100 * ((ohlcv_data['close'] - low_min) / (high_max - low_min))
        return k_percent
    
    def calculate_williams_r_simple(self, ohlcv_data, period=14):
        """Laske Williams %R yksinkertaistettu"""
        high_max = ohlcv_data['high'].rolling(window=period).max()
        low_min = ohlcv_data['low'].rolling(window=period).min()
        
        williams_r = -100 * ((high_max - ohlcv_data['close']) / (high_max - low_min))
        return williams_r
    
    def calculate_cci_simple(self, ohlcv_data, period=14):
        """Laske CCI yksinkertaistettu"""
        typical_price = (ohlcv_data['high'] + ohlcv_data['low'] + ohlcv_data['close']) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())))
        
        cci = (typical_price - sma_tp) / (0.015 * mad)
        return cci
    
    def calculate_adx_simple(self, ohlcv_data, period=14):
        """Laske ADX yksinkertaistettu"""
        high = ohlcv_data['high']
        low = ohlcv_data['low']
        close = ohlcv_data['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        dm_plus = high.diff()
        dm_minus = -low.diff()
        
        dm_plus = dm_plus.where((dm_plus > dm_minus) & (dm_plus > 0), 0)
        dm_minus = dm_minus.where((dm_minus > dm_plus) & (dm_minus > 0), 0)
        
        # Smoothed values
        tr_smooth = tr.rolling(window=period).mean()
        dm_plus_smooth = dm_plus.rolling(window=period).mean()
        dm_minus_smooth = dm_minus.rolling(window=period).mean()
        
        # DI values
        di_plus = 100 * (dm_plus_smooth / tr_smooth)
        di_minus = 100 * (dm_minus_smooth / tr_smooth)
        
        # ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    def calculate_obv_simple(self, ohlcv_data):
        """Laske OBV yksinkertaistettu"""
        close = ohlcv_data['close']
        volume = ohlcv_data['volume']
        
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    def calculate_technical_indicators(self, ohlcv_data: pd.DataFrame) -> TechnicalIndicators:
        """Laske kaikki tekniset indikaattorit"""
        try:
            # Perusindikaattorit (yksinkertaistettu toteutus ilman talib)
            sma_20 = ohlcv_data['close'].rolling(window=20).mean().iloc[-1]
            sma_50 = ohlcv_data['close'].rolling(window=50).mean().iloc[-1]
            ema_12 = ohlcv_data['close'].ewm(span=12).mean().iloc[-1]
            ema_26 = ohlcv_data['close'].ewm(span=26).mean().iloc[-1]
            
            # RSI (yksinkertaistettu)
            rsi = self.calculate_rsi_simple(ohlcv_data['close']).iloc[-1]
            
            # MACD (yksinkertaistettu)
            macd = ema_12 - ema_26
            macd_signal = pd.Series([macd]).ewm(span=9).mean().iloc[-1]
            macd_histogram = macd - macd_signal
            
            # Bollinger Bands (yksinkertaistettu)
            bb_middle = sma_20
            bb_std = ohlcv_data['close'].rolling(window=20).std().iloc[-1]
            bb_upper = bb_middle + (bb_std * 2)
            bb_lower = bb_middle - (bb_std * 2)
            
            # Volume
            volume_sma = ohlcv_data['volume'].rolling(window=20).mean().iloc[-1]
            
            # ATR (yksinkertaistettu)
            atr = self.calculate_atr_simple(ohlcv_data).iloc[-1]
            
            # Stochastic (yksinkertaistettu)
            stoch_k = self.calculate_stochastic_simple(ohlcv_data).iloc[-1]
            stoch_d = pd.Series([stoch_k]).rolling(window=3).mean().iloc[-1]
            
            # Williams %R (yksinkertaistettu)
            williams_r = self.calculate_williams_r_simple(ohlcv_data).iloc[-1]
            
            # CCI (yksinkertaistettu)
            cci = self.calculate_cci_simple(ohlcv_data).iloc[-1]
            
            # ADX (yksinkertaistettu)
            adx = self.calculate_adx_simple(ohlcv_data).iloc[-1]
            
            # OBV (yksinkertaistettu)
            obv = self.calculate_obv_simple(ohlcv_data).iloc[-1]
            
            return TechnicalIndicators(
                sma_20=sma_20,
                sma_50=sma_50,
                ema_12=ema_12,
                ema_26=ema_26,
                rsi=rsi,
                macd=macd,
                macd_signal=macd_signal,
                macd_histogram=macd_histogram,
                bollinger_upper=bb_upper,
                bollinger_middle=bb_middle,
                bollinger_lower=bb_lower,
                volume_sma=volume_sma,
                atr=atr,
                stoch_k=stoch_k,
                stoch_d=stoch_d,
                williams_r=williams_r,
                cci=cci,
                adx=adx,
                obv=obv
            )
            
        except Exception as e:
            self.logger.error(f"Virhe teknisen analyysin laskennassa: {e}")
            return None
    
    def analyze_token(self, token) -> Dict:
        """Analysoi token mock datalla"""
        try:
            # Simuloi teknistä analyysiä - varmista että kaikki arvot ovat float
            analysis = {
                "rsi": float(np.random.uniform(20, 80)),
                "macd": float(np.random.uniform(-0.01, 0.01)),
                "macd_signal": float(np.random.uniform(-0.01, 0.01)),
                "sma_20": float(token.price * np.random.uniform(0.95, 1.05)),
                "sma_50": float(token.price * np.random.uniform(0.90, 1.10)),
                "bollinger_upper": float(token.price * 1.1),
                "bollinger_lower": float(token.price * 0.9),
                "volume_sma": float(token.volume_24h * np.random.uniform(0.8, 1.2)),
                "atr": float(token.price * 0.05),
                "trend_direction": str(np.random.choice(["BULLISH", "BEARISH", "SIDEWAYS"])),
                "trend_strength": float(np.random.uniform(30, 90)),
                "momentum_score": float(np.random.uniform(5.0, 9.0)),
                "volatility": float(np.random.uniform(0.1, 0.5)),
                "support_level": float(token.price * 0.8),
                "resistance_level": float(token.price * 1.3),
                "breakout_probability": float(np.random.uniform(0.3, 0.8))
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Virhe tokenin analyysissä: {e}")
            return {
                "rsi": 50.0,
                "macd": 0.0,
                "macd_signal": 0.0,
                "sma_20": token.price,
                "sma_50": token.price,
                "bollinger_upper": token.price * 1.1,
                "bollinger_lower": token.price * 0.9,
                "volume_sma": token.volume_24h,
                "atr": token.price * 0.05,
                "trend_direction": "SIDEWAYS",
                "trend_strength": 50.0,
                "momentum_score": 5.0,
                "volatility": 0.3,
                "support_level": token.price * 0.8,
                "resistance_level": token.price * 1.3,
                "breakout_probability": 0.5
            }

    def analyze_trend(self, ohlcv_data: pd.DataFrame, indicators: TechnicalIndicators) -> TrendAnalysis:
        """Analysoi trendi"""
        try:
            current_price = ohlcv_data['close'].iloc[-1]
            
            # Trendi suunta
            trend_direction = self.determine_trend_direction(ohlcv_data, indicators)
            
            # Trendi voima
            trend_strength = self.calculate_trend_strength(ohlcv_data, indicators)
            
            # Tuki ja vastustasot
            support_levels = self.find_support_levels(ohlcv_data)
            resistance_levels = self.find_resistance_levels(ohlcv_data)
            
            # Breakout todennäköisyys
            breakout_probability = self.calculate_breakout_probability(ohlcv_data, indicators)
            
            # Kääntymis signaalit
            reversal_signals = self.detect_reversal_signals(ohlcv_data, indicators)
            
            # Momentum skoori
            momentum_score = self.calculate_momentum_score(ohlcv_data, indicators)
            
            return TrendAnalysis(
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                breakout_probability=breakout_probability,
                reversal_signals=reversal_signals,
                momentum_score=momentum_score
            )
            
        except Exception as e:
            self.logger.error(f"Virhe trendi analyysissä: {e}")
            return None
    
    def determine_trend_direction(self, ohlcv_data: pd.DataFrame, indicators: TechnicalIndicators) -> str:
        """Määritä trendi suunta"""
        current_price = ohlcv_data['close'].iloc[-1]
        
        # SMA trendi
        sma_trend = 1 if current_price > indicators.sma_20 > indicators.sma_50 else -1
        
        # EMA trendi
        ema_trend = 1 if indicators.ema_12 > indicators.ema_26 else -1
        
        # MACD trendi
        macd_trend = 1 if indicators.macd > indicators.macd_signal else -1
        
        # Bollinger Bands trendi
        bb_trend = 1 if current_price > indicators.bollinger_middle else -1
        
        # Yhdistä signaalit
        total_trend = sma_trend + ema_trend + macd_trend + bb_trend
        
        if total_trend >= 2:
            return 'BULLISH'
        elif total_trend <= -2:
            return 'BEARISH'
        else:
            return 'SIDEWAYS'
    
    def calculate_trend_strength(self, ohlcv_data: pd.DataFrame, indicators: TechnicalIndicators) -> float:
        """Laske trendi voima"""
        try:
            # ADX indikaattori (0-100)
            adx_strength = indicators.adx if not np.isnan(indicators.adx) else 50
            
            # Price momentum
            price_momentum = self.calculate_price_momentum(ohlcv_data)
            
            # Volume confirmation
            volume_confirmation = self.calculate_volume_confirmation(ohlcv_data, indicators)
            
            # Yhdistä tekijät
            trend_strength = (adx_strength * 0.4 + price_momentum * 0.3 + volume_confirmation * 0.3)
            
            return min(max(trend_strength, 0), 100)
            
        except Exception as e:
            self.logger.error(f"Virhe trendi voiman laskennassa: {e}")
            return 50.0
    
    def calculate_price_momentum(self, ohlcv_data: pd.DataFrame) -> float:
        """Laske hinnan momentum"""
        try:
            # 20 päivän momentum
            momentum_20 = (ohlcv_data['close'].iloc[-1] - ohlcv_data['close'].iloc[-20]) / ohlcv_data['close'].iloc[-20] * 100
            
            # 5 päivän momentum
            momentum_5 = (ohlcv_data['close'].iloc[-1] - ohlcv_data['close'].iloc[-5]) / ohlcv_data['close'].iloc[-5] * 100
            
            # Yhdistä momentumit
            combined_momentum = (momentum_20 * 0.6 + momentum_5 * 0.4)
            
            # Normalisoi 0-100 skaalalle
            return min(max(50 + combined_momentum, 0), 100)
            
        except Exception as e:
            self.logger.error(f"Virhe momentum laskennassa: {e}")
            return 50.0
    
    def calculate_volume_confirmation(self, ohlcv_data: pd.DataFrame, indicators: TechnicalIndicators) -> float:
        """Laske volyymi vahvistus"""
        try:
            current_volume = ohlcv_data['volume'].iloc[-1]
            avg_volume = indicators.volume_sma
            
            if avg_volume > 0:
                volume_ratio = current_volume / avg_volume
                
                # Normalisoi 0-100 skaalalle
                if volume_ratio > 2:
                    return 100
                elif volume_ratio > 1.5:
                    return 80
                elif volume_ratio > 1:
                    return 60
                else:
                    return 40
            
            return 50
            
        except Exception as e:
            self.logger.error(f"Virhe volyymi vahvistuksen laskennassa: {e}")
            return 50.0
    
    def find_support_levels(self, ohlcv_data: pd.DataFrame) -> List[float]:
        """Löydä tuki tasot"""
        try:
            # Käytä pivot point analyysiä
            lows = ohlcv_data['low'].rolling(window=5, center=True).min()
            support_levels = []
            
            for i in range(5, len(lows) - 5):
                if lows.iloc[i] == ohlcv_data['low'].iloc[i]:
                    # Tarkista onko tämä todellinen tuki
                    if self.is_valid_support_level(ohlcv_data, lows.iloc[i], i):
                        support_levels.append(lows.iloc[i])
            
            # Järjestä ja palauta top 3
            support_levels.sort(reverse=True)
            return support_levels[:3]
            
        except Exception as e:
            self.logger.error(f"Virhe tuki tasojen löytämisessä: {e}")
            return []
    
    def find_resistance_levels(self, ohlcv_data: pd.DataFrame) -> List[float]:
        """Löydä vastustasot"""
        try:
            # Käytä pivot point analyysiä
            highs = ohlcv_data['high'].rolling(window=5, center=True).max()
            resistance_levels = []
            
            for i in range(5, len(highs) - 5):
                if highs.iloc[i] == ohlcv_data['high'].iloc[i]:
                    # Tarkista onko tämä todellinen vastustaso
                    if self.is_valid_resistance_level(ohlcv_data, highs.iloc[i], i):
                        resistance_levels.append(highs.iloc[i])
            
            # Järjestä ja palauta top 3
            resistance_levels.sort()
            return resistance_levels[:3]
            
        except Exception as e:
            self.logger.error(f"Virhe vastustasojen löytämisessä: {e}")
            return []
    
    def is_valid_support_level(self, ohlcv_data: pd.DataFrame, level: float, index: int) -> bool:
        """Tarkista onko tuki taso validi"""
        try:
            # Tarkista kuinka monta kertaa hinta on koskenut tätä tasoa
            touches = 0
            tolerance = level * 0.02  # 2% toleranssi
            
            for i in range(max(0, index - 20), min(len(ohlcv_data), index + 20)):
                if abs(ohlcv_data['low'].iloc[i] - level) <= tolerance:
                    touches += 1
            
            return touches >= 2
            
        except Exception as e:
            return False
    
    def is_valid_resistance_level(self, ohlcv_data: pd.DataFrame, level: float, index: int) -> bool:
        """Tarkista onko vastustaso validi"""
        try:
            # Tarkista kuinka monta kertaa hinta on koskenut tätä tasoa
            touches = 0
            tolerance = level * 0.02  # 2% toleranssi
            
            for i in range(max(0, index - 20), min(len(ohlcv_data), index + 20)):
                if abs(ohlcv_data['high'].iloc[i] - level) <= tolerance:
                    touches += 1
            
            return touches >= 2
            
        except Exception as e:
            return False
    
    def calculate_breakout_probability(self, ohlcv_data: pd.DataFrame, indicators: TechnicalIndicators) -> float:
        """Laske breakout todennäköisyys"""
        try:
            current_price = ohlcv_data['close'].iloc[-1]
            
            # Bollinger Bands breakout
            bb_breakout = 0
            if current_price > indicators.bollinger_upper:
                bb_breakout = 0.3
            elif current_price < indicators.bollinger_lower:
                bb_breakout = 0.3
            
            # Volume breakout
            volume_breakout = 0
            current_volume = ohlcv_data['volume'].iloc[-1]
            if current_volume > indicators.volume_sma * 1.5:
                volume_breakout = 0.3
            
            # Trend continuation
            trend_continuation = 0
            if indicators.macd > indicators.macd_signal and indicators.rsi > 50:
                trend_continuation = 0.4
            
            total_probability = bb_breakout + volume_breakout + trend_continuation
            return min(max(total_probability, 0), 1)
            
        except Exception as e:
            self.logger.error(f"Virhe breakout todennäköisyyden laskennassa: {e}")
            return 0.5
    
    def detect_reversal_signals(self, ohlcv_data: pd.DataFrame, indicators: TechnicalIndicators) -> List[str]:
        """Tunnista kääntymis signaalit"""
        signals = []
        
        try:
            # RSI divergence
            if indicators.rsi > 70 and indicators.macd_histogram < 0:
                signals.append("RSI_OVERBOUGHT_DIVERGENCE")
            elif indicators.rsi < 30 and indicators.macd_histogram > 0:
                signals.append("RSI_OVERSOLD_DIVERGENCE")
            
            # MACD crossover
            if indicators.macd > indicators.macd_signal and indicators.macd_histogram > 0:
                signals.append("MACD_BULLISH_CROSSOVER")
            elif indicators.macd < indicators.macd_signal and indicators.macd_histogram < 0:
                signals.append("MACD_BEARISH_CROSSOVER")
            
            # Bollinger Bands squeeze
            bb_width = (indicators.bollinger_upper - indicators.bollinger_lower) / indicators.bollinger_middle
            if bb_width < 0.1:  # Kapea Bollinger Bands
                signals.append("BOLLINGER_SQUEEZE")
            
            # Volume spike
            current_volume = ohlcv_data['volume'].iloc[-1]
            if current_volume > indicators.volume_sma * 2:
                signals.append("VOLUME_SPIKE")
            
            # Stochastic oversold/overbought
            if indicators.stoch_k < 20 and indicators.stoch_d < 20:
                signals.append("STOCH_OVERSOLD")
            elif indicators.stoch_k > 80 and indicators.stoch_d > 80:
                signals.append("STOCH_OVERBOUGHT")
            
        except Exception as e:
            self.logger.error(f"Virhe kääntymis signaalien tunnistamisessa: {e}")
        
        return signals
    
    def calculate_momentum_score(self, ohlcv_data: pd.DataFrame, indicators: TechnicalIndicators) -> float:
        """Laske momentum skoori"""
        try:
            # RSI momentum
            rsi_momentum = 0
            if 30 < indicators.rsi < 70:
                rsi_momentum = 0.3
            elif indicators.rsi > 70:
                rsi_momentum = 0.1  # Ylimyynti
            elif indicators.rsi < 30:
                rsi_momentum = 0.1  # Ylimyynti
            
            # MACD momentum
            macd_momentum = 0
            if indicators.macd > indicators.macd_signal:
                macd_momentum = 0.3
            else:
                macd_momentum = 0.1
            
            # Price momentum
            price_momentum = 0
            current_price = ohlcv_data['close'].iloc[-1]
            sma_20 = indicators.sma_20
            
            if current_price > sma_20:
                price_momentum = 0.4
            else:
                price_momentum = 0.1
            
            total_momentum = (rsi_momentum + macd_momentum + price_momentum) * 100
            return min(max(total_momentum, 0), 100)
            
        except Exception as e:
            self.logger.error(f"Virhe momentum skoorin laskennassa: {e}")
            return 50.0
    
    def recognize_patterns(self, ohlcv_data: pd.DataFrame) -> PatternRecognition:
        """Tunnista kuvioita"""
        patterns = []
        pattern_confidence = []
        breakout_targets = []
        stop_loss_levels = []
        
        try:
            # Head and Shoulders
            if self.detect_head_and_shoulders(ohlcv_data):
                patterns.append("HEAD_AND_SHOULDERS")
                pattern_confidence.append(0.7)
                breakout_targets.append(ohlcv_data['close'].iloc[-1] * 0.9)
                stop_loss_levels.append(ohlcv_data['close'].iloc[-1] * 1.05)
            
            # Double Top/Bottom
            if self.detect_double_top(ohlcv_data):
                patterns.append("DOUBLE_TOP")
                pattern_confidence.append(0.6)
                breakout_targets.append(ohlcv_data['close'].iloc[-1] * 0.9)
                stop_loss_levels.append(ohlcv_data['close'].iloc[-1] * 1.03)
            
            if self.detect_double_bottom(ohlcv_data):
                patterns.append("DOUBLE_BOTTOM")
                pattern_confidence.append(0.6)
                breakout_targets.append(ohlcv_data['close'].iloc[-1] * 1.1)
                stop_loss_levels.append(ohlcv_data['close'].iloc[-1] * 0.97)
            
            # Triangle patterns
            if self.detect_ascending_triangle(ohlcv_data):
                patterns.append("ASCENDING_TRIANGLE")
                pattern_confidence.append(0.8)
                breakout_targets.append(ohlcv_data['close'].iloc[-1] * 1.15)
                stop_loss_levels.append(ohlcv_data['close'].iloc[-1] * 0.95)
            
            if self.detect_descending_triangle(ohlcv_data):
                patterns.append("DESCENDING_TRIANGLE")
                pattern_confidence.append(0.8)
                breakout_targets.append(ohlcv_data['close'].iloc[-1] * 0.85)
                stop_loss_levels.append(ohlcv_data['close'].iloc[-1] * 1.05)
            
            # Flag and Pennant
            if self.detect_flag_pattern(ohlcv_data):
                patterns.append("FLAG")
                pattern_confidence.append(0.7)
                breakout_targets.append(ohlcv_data['close'].iloc[-1] * 1.2)
                stop_loss_levels.append(ohlcv_data['close'].iloc[-1] * 0.9)
            
        except Exception as e:
            self.logger.error(f"Virhe kuvioiden tunnistamisessa: {e}")
        
        return PatternRecognition(
            patterns=patterns,
            pattern_confidence=pattern_confidence,
            breakout_targets=breakout_targets,
            stop_loss_levels=stop_loss_levels
        )
    
    def detect_head_and_shoulders(self, ohlcv_data: pd.DataFrame) -> bool:
        """Tunnista Head and Shoulders kuvio"""
        try:
            # Yksinkertainen toteutus - tarkista 3 huippua
            highs = ohlcv_data['high'].rolling(window=5, center=True).max()
            peaks = []
            
            for i in range(5, len(highs) - 5):
                if highs.iloc[i] == ohlcv_data['high'].iloc[i]:
                    peaks.append((i, highs.iloc[i]))
            
            if len(peaks) >= 3:
                # Tarkista onko keskimmäinen huippu korkein
                middle_peak = peaks[len(peaks)//2]
                left_peak = peaks[0]
                right_peak = peaks[-1]
                
                return (middle_peak[1] > left_peak[1] and 
                        middle_peak[1] > right_peak[1] and
                        abs(left_peak[1] - right_peak[1]) / left_peak[1] < 0.05)
            
            return False
            
        except Exception as e:
            return False
    
    def detect_double_top(self, ohlcv_data: pd.DataFrame) -> bool:
        """Tunnista Double Top kuvio"""
        try:
            highs = ohlcv_data['high'].rolling(window=5, center=True).max()
            peaks = []
            
            for i in range(5, len(highs) - 5):
                if highs.iloc[i] == ohlcv_data['high'].iloc[i]:
                    peaks.append((i, highs.iloc[i]))
            
            if len(peaks) >= 2:
                # Tarkista onko kaksi huippua samalla tasolla
                last_two_peaks = peaks[-2:]
                price_diff = abs(last_two_peaks[0][1] - last_two_peaks[1][1]) / last_two_peaks[0][1]
                return price_diff < 0.03  # 3% toleranssi
            
            return False
            
        except Exception as e:
            return False
    
    def detect_double_bottom(self, ohlcv_data: pd.DataFrame) -> bool:
        """Tunnista Double Bottom kuvio"""
        try:
            lows = ohlcv_data['low'].rolling(window=5, center=True).min()
            valleys = []
            
            for i in range(5, len(lows) - 5):
                if lows.iloc[i] == ohlcv_data['low'].iloc[i]:
                    valleys.append((i, lows.iloc[i]))
            
            if len(valleys) >= 2:
                # Tarkista onko kaksi pohjaa samalla tasolla
                last_two_valleys = valleys[-2:]
                price_diff = abs(last_two_valleys[0][1] - last_two_valleys[1][1]) / last_two_valleys[0][1]
                return price_diff < 0.03  # 3% toleranssi
            
            return False
            
        except Exception as e:
            return False
    
    def detect_ascending_triangle(self, ohlcv_data: pd.DataFrame) -> bool:
        """Tunnista Ascending Triangle kuvio"""
        try:
            # Yksinkertainen toteutus - tarkista nouseva tuki ja vaakasuora vastustaso
            recent_data = ohlcv_data.tail(20)
            
            # Tarkista nouseva tuki
            lows = recent_data['low']
            if len(lows) >= 3:
                # Laske trendi alimmille hinnoille
                low_trend = np.polyfit(range(len(lows)), lows, 1)[0]
                return low_trend > 0  # Positiivinen trendi
            
            return False
            
        except Exception as e:
            return False
    
    def detect_descending_triangle(self, ohlcv_data: pd.DataFrame) -> bool:
        """Tunnista Descending Triangle kuvio"""
        try:
            # Yksinkertainen toteutus - tarkista laskeva vastustaso ja vaakasuora tuki
            recent_data = ohlcv_data.tail(20)
            
            # Tarkista laskeva vastustaso
            highs = recent_data['high']
            if len(highs) >= 3:
                # Laske trendi ylimmille hinnoille
                high_trend = np.polyfit(range(len(highs)), highs, 1)[0]
                return high_trend < 0  # Negatiivinen trendi
            
            return False
            
        except Exception as e:
            return False
    
    def detect_flag_pattern(self, ohlcv_data: pd.DataFrame) -> bool:
        """Tunnista Flag kuvio"""
        try:
            # Yksinkertainen toteutus - tarkista nopea liike ja konsolidointi
            recent_data = ohlcv_data.tail(15)
            
            # Tarkista onko ollut nopea liike
            price_range = recent_data['high'].max() - recent_data['low'].min()
            avg_price = recent_data['close'].mean()
            
            if price_range / avg_price > 0.1:  # Yli 10% liike
                # Tarkista konsolidointi
                recent_volatility = recent_data['close'].std() / recent_data['close'].mean()
                return recent_volatility < 0.05  # Matala volatiliteetti
            
            return False
            
        except Exception as e:
            return False
    
    def generate_trading_signals(self, ohlcv_data: pd.DataFrame, indicators: TechnicalIndicators, 
                                trend_analysis: TrendAnalysis, patterns: PatternRecognition) -> List[Dict]:
        """Generoi trading signaalit"""
        signals = []
        
        try:
            current_price = ohlcv_data['close'].iloc[-1]
            
            # Bullish signals
            if (trend_analysis.trend_direction == 'BULLISH' and 
                indicators.rsi < 70 and 
                indicators.macd > indicators.macd_signal):
                
                signal = {
                    'type': 'BUY',
                    'confidence': min(trend_analysis.trend_strength / 100, 0.9),
                    'entry_price': current_price,
                    'target_price': current_price * 1.2,
                    'stop_loss': current_price * 0.9,
                    'reasoning': f"Bullish trend, RSI: {indicators.rsi:.1f}, MACD bullish"
                }
                signals.append(signal)
            
            # Bearish signals
            if (trend_analysis.trend_direction == 'BEARISH' and 
                indicators.rsi > 30 and 
                indicators.macd < indicators.macd_signal):
                
                signal = {
                    'type': 'SELL',
                    'confidence': min(trend_analysis.trend_strength / 100, 0.9),
                    'entry_price': current_price,
                    'target_price': current_price * 0.8,
                    'stop_loss': current_price * 1.1,
                    'reasoning': f"Bearish trend, RSI: {indicators.rsi:.1f}, MACD bearish"
                }
                signals.append(signal)
            
            # Pattern-based signals
            for i, pattern in enumerate(patterns.patterns):
                if pattern in ['ASCENDING_TRIANGLE', 'DOUBLE_BOTTOM']:
                    signal = {
                        'type': 'BUY',
                        'confidence': patterns.pattern_confidence[i],
                        'entry_price': current_price,
                        'target_price': patterns.breakout_targets[i],
                        'stop_loss': patterns.stop_loss_levels[i],
                        'reasoning': f"Pattern: {pattern}"
                    }
                    signals.append(signal)
                
                elif pattern in ['DESCENDING_TRIANGLE', 'DOUBLE_TOP', 'HEAD_AND_SHOULDERS']:
                    signal = {
                        'type': 'SELL',
                        'confidence': patterns.pattern_confidence[i],
                        'entry_price': current_price,
                        'target_price': patterns.breakout_targets[i],
                        'stop_loss': patterns.stop_loss_levels[i],
                        'reasoning': f"Pattern: {pattern}"
                    }
                    signals.append(signal)
            
        except Exception as e:
            self.logger.error(f"Virhe trading signaalien generoinnissa: {e}")
        
        return signals

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_sample_ohlcv_data(days: int = 100) -> pd.DataFrame:
    """Luo esimerkki OHLCV dataa testausta varten"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), end=datetime.now(), freq='D')
    
    # Simuloi hinta dataa
    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, len(dates))  # 0.1% keskimääräinen tuotto, 2% volatiliteetti
    
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Luo OHLCV data
    ohlcv_data = pd.DataFrame({
        'date': dates,
        'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': [np.random.randint(1000000, 10000000) for _ in range(len(dates))]
    })
    
    ohlcv_data.set_index('date', inplace=True)
    return ohlcv_data

# =============================================================================
# TESTING
# =============================================================================

def test_technical_analysis():
    """Testaa teknistä analyysiä"""
    print("🧪 Testataan teknistä analyysiä...")
    
    # Luo testi data
    ohlcv_data = create_sample_ohlcv_data(100)
    
    # Luo analyysi moottori
    engine = TechnicalAnalysisEngine()
    
    # Laske indikaattorit
    indicators = engine.calculate_technical_indicators(ohlcv_data)
    if indicators:
        print(f"✅ Indikaattorit laskettu:")
        print(f"   RSI: {indicators.rsi:.2f}")
        print(f"   MACD: {indicators.macd:.4f}")
        print(f"   SMA 20: {indicators.sma_20:.2f}")
        print(f"   SMA 50: {indicators.sma_50:.2f}")
    
    # Analysoi trendi
    trend_analysis = engine.analyze_trend(ohlcv_data, indicators)
    if trend_analysis:
        print(f"✅ Trendi analyysi:")
        print(f"   Suunta: {trend_analysis.trend_direction}")
        print(f"   Voima: {trend_analysis.trend_strength:.1f}%")
        print(f"   Momentum: {trend_analysis.momentum_score:.1f}")
    
    # Tunnista kuvioita
    patterns = engine.recognize_patterns(ohlcv_data)
    if patterns.patterns:
        print(f"✅ Löydetyt kuvioita: {patterns.patterns}")
    
    # Generoi signaalit
    signals = engine.generate_trading_signals(ohlcv_data, indicators, trend_analysis, patterns)
    if signals:
        print(f"✅ Generoitiin {len(signals)} trading signaalia")
        for signal in signals:
            print(f"   {signal['type']}: {signal['reasoning']}")

if __name__ == "__main__":
    test_technical_analysis()
