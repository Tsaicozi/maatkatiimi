#!/usr/bin/env python3
"""
Live Trading Strategy for Helius Token Scanner Bot
Optimized for fast pumps and dumps in the Solana ecosystem

Strategy: "Momentum Breakout + Quick Exit"
- Target: Tokens with high momentum and liquidity
- Entry: Breakout above resistance with volume confirmation
- Exit: Quick profit taking or stop loss
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json

logger = logging.getLogger(__name__)

class TradeSignal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    SKIP = "skip"

class TokenType(Enum):
    PUMP_FUN = "pump_fun"  # Pump.fun tokens (high risk, high reward)
    MEME = "meme"          # Meme tokens
    UTILITY = "utility"    # Utility tokens
    UNKNOWN = "unknown"

@dataclass
class TradingSignal:
    mint: str
    symbol: str
    signal: TradeSignal
    token_type: TokenType
    entry_price: float
    target_price: float
    stop_loss: float
    confidence: float  # 0-1
    reasoning: str
    timestamp: float
    volume_24h: float
    liquidity: float
    util: float
    buyers_30m: int
    age_minutes: int
    price_change_5m: float
    price_change_1h: float

@dataclass
class Position:
    mint: str
    symbol: str
    entry_price: float
    entry_time: float
    quantity: float
    stop_loss: float
    take_profit: float
    current_price: float
    pnl_percent: float
    status: str  # "open", "closed", "stopped"

class LiveTradingStrategy:
    """
    Momentum Breakout Strategy for Solana tokens
    
    Core Principles:
    1. High momentum tokens (util 0.4-6.0)
    2. Strong volume confirmation (20k+ USD)
    3. Active trading (10+ trades/24h)
    4. Quick entry/exit (5-30 min holds)
    5. Risk management (2-5% stop loss)
    """
    
    def __init__(self):
        # Risk Management
        self.max_position_size = 0.02  # 2% of portfolio per trade
        self.stop_loss_percent = 0.03  # 3% stop loss
        self.take_profit_percent = 0.15  # 15% take profit
        self.max_hold_time = 1800  # 30 minutes max hold
        
        # Entry Criteria (aligned with bot filters)
        self.min_liquidity = 15000  # USD
        self.min_volume_24h = 20000  # USD
        self.min_util = 0.4
        self.max_util = 6.0
        self.min_trades_24h = 10
        self.min_buyers_30m = 5
        
        # Momentum Criteria
        self.min_price_change_5m = 0.05  # 5% in 5 minutes
        self.min_price_change_1h = 0.10  # 10% in 1 hour
        self.max_age_minutes = 120  # Max 2 hours old
        
        # Position tracking
        self.positions: Dict[str, Position] = {}
        self.signal_history: List[TradingSignal] = []
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
    def analyze_token(self, token_data: dict) -> Optional[TradingSignal]:
        """
        Analyze token data and generate trading signal
        
        Args:
            token_data: Token data from Helius scanner bot
            
        Returns:
            TradingSignal if conditions are met, None otherwise
        """
        try:
            mint = token_data.get("mint", "")
            symbol = token_data.get("symbol", "")
            dex_data = token_data.get("dex", {})
            metadata = token_data.get("metadata", {})
            
            # Extract key metrics
            liquidity = dex_data.get("liq_usd", 0)
            volume_24h = dex_data.get("vol_h24", 0)
            util = dex_data.get("util", 0)
            buyers_30m = dex_data.get("buyers30m", 0)
            age_minutes = dex_data.get("age_min", 0)
            price_usd = dex_data.get("price_usd", 0)
            
            # Price changes
            price_changes = dex_data.get("priceChange", {})
            change_5m = price_changes.get("m5", 0) / 100  # Convert to decimal
            change_1h = price_changes.get("h1", 0) / 100
            
            # Determine token type
            token_type = self._classify_token(mint, symbol, token_data)
            
            # Check basic filters (aligned with bot)
            if not self._passes_basic_filters(liquidity, volume_24h, util, buyers_30m, age_minutes):
                return None
            
            # Generate signal based on momentum
            signal = self._generate_momentum_signal(
                mint, symbol, token_type, price_usd, change_5m, change_1h,
                liquidity, volume_24h, util, buyers_30m, age_minutes
            )
            
            if signal:
                self.signal_history.append(signal)
                logger.info(f"Generated signal: {signal.signal.value} for {symbol} ({mint[:8]}...)")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing token: {e}")
            return None
    
    def _classify_token(self, mint: str, symbol: str, token_data: dict) -> TokenType:
        """Classify token type for strategy selection"""
        
        # Pump.fun detection
        if mint.endswith("pump") or "pump" in symbol.lower():
            return TokenType.PUMP_FUN
        
        # Meme token patterns
        meme_keywords = ["dog", "cat", "moon", "rocket", "pepe", "shib", "floki", "elon"]
        if any(keyword in symbol.lower() for keyword in meme_keywords):
            return TokenType.MEME
        
        # Utility tokens (less common in our scanner)
        utility_keywords = ["dao", "defi", "swap", "farm", "stake", "vote"]
        if any(keyword in symbol.lower() for keyword in utility_keywords):
            return TokenType.UTILITY
        
        return TokenType.UNKNOWN
    
    def _passes_basic_filters(self, liquidity: float, volume_24h: float, util: float, 
                            buyers_30m: int, age_minutes: int) -> bool:
        """Check if token passes basic trading filters"""
        
        return (
            liquidity >= self.min_liquidity and
            volume_24h >= self.min_volume_24h and
            self.min_util <= util <= self.max_util and
            buyers_30m >= self.min_buyers_30m and
            age_minutes <= self.max_age_minutes
        )
    
    def _generate_momentum_signal(self, mint: str, symbol: str, token_type: TokenType,
                                price: float, change_5m: float, change_1h: float,
                                liquidity: float, volume_24h: float, util: float,
                                buyers_30m: int, age_minutes: int) -> Optional[TradingSignal]:
        """Generate trading signal based on momentum analysis"""
        
        # Calculate confidence score
        confidence = self._calculate_confidence(
            change_5m, change_1h, liquidity, volume_24h, util, buyers_30m, age_minutes, token_type
        )
        
        # Minimum confidence threshold
        if confidence < 0.6:
            return None
        
        # Determine signal type
        signal_type = self._determine_signal_type(change_5m, change_1h, token_type, confidence)
        
        if signal_type == TradeSignal.SKIP:
            return None
        
        # Calculate entry, target, and stop loss
        entry_price = price
        target_price = self._calculate_target_price(price, signal_type, token_type)
        stop_loss = self._calculate_stop_loss(price, signal_type)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            signal_type, token_type, change_5m, change_1h, confidence, util, buyers_30m
        )
        
        return TradingSignal(
            mint=mint,
            symbol=symbol,
            signal=signal_type,
            token_type=token_type,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            confidence=confidence,
            reasoning=reasoning,
            timestamp=time.time(),
            volume_24h=volume_24h,
            liquidity=liquidity,
            util=util,
            buyers_30m=buyers_30m,
            age_minutes=age_minutes,
            price_change_5m=change_5m,
            price_change_1h=change_1h
        )
    
    def _calculate_confidence(self, change_5m: float, change_1h: float, liquidity: float,
                            volume_24h: float, util: float, buyers_30m: int,
                            age_minutes: int, token_type: TokenType) -> float:
        """Calculate confidence score (0-1) for the signal"""
        
        confidence = 0.0
        
        # Momentum score (40% weight)
        momentum_score = 0.0
        if change_5m > 0.1:  # 10%+ in 5 minutes
            momentum_score += 0.4
        elif change_5m > 0.05:  # 5%+ in 5 minutes
            momentum_score += 0.2
        
        if change_1h > 0.2:  # 20%+ in 1 hour
            momentum_score += 0.3
        elif change_1h > 0.1:  # 10%+ in 1 hour
            momentum_score += 0.15
        
        confidence += momentum_score * 0.4
        
        # Volume/Liquidity score (30% weight)
        volume_score = min(volume_24h / 100000, 1.0)  # Normalize to 100k
        liquidity_score = min(liquidity / 50000, 1.0)  # Normalize to 50k
        confidence += (volume_score + liquidity_score) / 2 * 0.3
        
        # Activity score (20% weight)
        buyers_score = min(buyers_30m / 20, 1.0)  # Normalize to 20 buyers
        util_score = 1.0 if 0.5 <= util <= 5.0 else 0.5  # Optimal util range
        confidence += (buyers_score + util_score) / 2 * 0.2
        
        # Age score (10% weight)
        age_score = max(0, 1.0 - (age_minutes / 120))  # Prefer newer tokens
        confidence += age_score * 0.1
        
        # Token type bonus
        if token_type == TokenType.PUMP_FUN:
            confidence += 0.1  # Pump.fun tokens often have explosive moves
        elif token_type == TokenType.MEME:
            confidence += 0.05  # Meme tokens can be volatile
        
        return min(confidence, 1.0)
    
    def _determine_signal_type(self, change_5m: float, change_1h: float, 
                             token_type: TokenType, confidence: float) -> TradeSignal:
        """Determine the type of trading signal"""
        
        # Strong momentum signals
        if change_5m > 0.15 and confidence > 0.7:  # 15%+ in 5 min
            return TradeSignal.BUY
        elif change_5m > 0.1 and change_1h > 0.2 and confidence > 0.65:  # 10%+ 5m, 20%+ 1h
            return TradeSignal.BUY
        
        # Pump.fun specific signals (more aggressive)
        if token_type == TokenType.PUMP_FUN:
            if change_5m > 0.08 and confidence > 0.6:  # 8%+ in 5 min
                return TradeSignal.BUY
            elif change_1h > 0.15 and confidence > 0.65:  # 15%+ in 1 hour
                return TradeSignal.BUY
        
        # Meme token signals
        if token_type == TokenType.MEME:
            if change_5m > 0.12 and confidence > 0.7:  # 12%+ in 5 min
                return TradeSignal.BUY
        
        return TradeSignal.SKIP
    
    def _calculate_target_price(self, current_price: float, signal: TradeSignal, 
                              token_type: TokenType) -> float:
        """Calculate target price for take profit"""
        
        if signal != TradeSignal.BUY:
            return current_price
        
        # Different targets based on token type
        if token_type == TokenType.PUMP_FUN:
            return current_price * (1 + self.take_profit_percent * 1.5)  # 22.5% target
        elif token_type == TokenType.MEME:
            return current_price * (1 + self.take_profit_percent * 1.2)  # 18% target
        else:
            return current_price * (1 + self.take_profit_percent)  # 15% target
    
    def _calculate_stop_loss(self, current_price: float, signal: TradeSignal) -> float:
        """Calculate stop loss price"""
        
        if signal != TradeSignal.BUY:
            return current_price
        
        return current_price * (1 - self.stop_loss_percent)  # 3% stop loss
    
    def _generate_reasoning(self, signal: TradeSignal, token_type: TokenType,
                          change_5m: float, change_1h: float, confidence: float,
                          util: float, buyers_30m: int) -> str:
        """Generate human-readable reasoning for the signal"""
        
        reasons = []
        
        if signal == TradeSignal.BUY:
            reasons.append(f"Strong momentum: {change_5m*100:.1f}% in 5m, {change_1h*100:.1f}% in 1h")
            reasons.append(f"High confidence: {confidence*100:.1f}%")
            reasons.append(f"Token type: {token_type.value}")
            reasons.append(f"Util: {util:.2f}, Buyers: {buyers_30m}")
        
        return " | ".join(reasons)
    
    def update_position(self, mint: str, current_price: float) -> Optional[Position]:
        """Update position with current price and check exit conditions"""
        
        if mint not in self.positions:
            return None
        
        position = self.positions[mint]
        position.current_price = current_price
        position.pnl_percent = (current_price - position.entry_price) / position.entry_price
        
        # Check exit conditions
        if self._should_exit_position(position):
            position.status = "closed"
            self._close_position(position)
        
        return position
    
    def _should_exit_position(self, position: Position) -> bool:
        """Check if position should be closed"""
        
        # Take profit
        if position.current_price >= position.take_profit:
            logger.info(f"Take profit hit for {position.symbol}: {position.pnl_percent*100:.1f}%")
            return True
        
        # Stop loss
        if position.current_price <= position.stop_loss:
            logger.info(f"Stop loss hit for {position.symbol}: {position.pnl_percent*100:.1f}%")
            return True
        
        # Time-based exit
        hold_time = time.time() - position.entry_time
        if hold_time > self.max_hold_time:
            logger.info(f"Time exit for {position.symbol}: {hold_time/60:.1f} minutes")
            return True
        
        return False
    
    def _close_position(self, position: Position):
        """Close position and update statistics"""
        
        self.total_trades += 1
        self.total_pnl += position.pnl_percent
        
        if position.pnl_percent > 0:
            self.winning_trades += 1
        
        logger.info(f"Closed position: {position.symbol} | PnL: {position.pnl_percent*100:.1f}% | "
                   f"Win rate: {self.winning_trades/self.total_trades*100:.1f}%")
    
    def get_performance_stats(self) -> dict:
        """Get trading performance statistics"""
        
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "win_rate_percent": win_rate,
            "total_pnl_percent": self.total_pnl * 100,
            "avg_pnl_per_trade": (self.total_pnl / self.total_trades * 100) if self.total_trades > 0 else 0,
            "active_positions": len([p for p in self.positions.values() if p.status == "open"])
        }
    
    def get_signal_summary(self, limit: int = 10) -> List[dict]:
        """Get recent signal summary"""
        
        recent_signals = self.signal_history[-limit:]
        
        return [
            {
                "symbol": s.symbol,
                "signal": s.signal.value,
                "token_type": s.token_type.value,
                "confidence": f"{s.confidence*100:.1f}%",
                "reasoning": s.reasoning,
                "timestamp": time.strftime("%H:%M:%S", time.localtime(s.timestamp))
            }
            for s in recent_signals
        ]

# Example usage and integration
async def main():
    """Example usage of the trading strategy"""
    
    strategy = LiveTradingStrategy()
    
    # Example token data (from Helius scanner)
    example_token = {
        "mint": "BEWU9JSZ984f8sy1xFvpharm9qKXPrGQH6GaJ184pump",
        "symbol": "PUMP",
        "dex": {
            "liq_usd": 25000,
            "vol_h24": 45000,
            "util": 1.8,
            "buyers30m": 15,
            "age_min": 45,
            "price_usd": 0.000123,
            "priceChange": {"m5": 12.5, "h1": 25.3}
        },
        "metadata": {}
    }
    
    # Analyze token
    signal = strategy.analyze_token(example_token)
    
    if signal:
        print(f"Signal: {signal.signal.value}")
        print(f"Confidence: {signal.confidence*100:.1f}%")
        print(f"Reasoning: {signal.reasoning}")
        print(f"Target: {signal.target_price:.8f}")
        print(f"Stop Loss: {signal.stop_loss:.8f}")
    else:
        print("No signal generated")

if __name__ == "__main__":
    asyncio.run(main())
