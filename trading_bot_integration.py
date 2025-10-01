#!/usr/bin/env python3
"""
Trading Bot Integration for Helius Token Scanner
Connects the scanner bot with live trading strategy
"""

import asyncio
import logging
import json
import time
from typing import Dict, Optional
from live_trading_strategy import LiveTradingStrategy, TradingSignal, Position

logger = logging.getLogger(__name__)

class TradingBotIntegration:
    """
    Integrates Helius Token Scanner with Live Trading Strategy
    
    Features:
    - Real-time signal generation from scanner data
    - Position management
    - Risk management
    - Performance tracking
    - Telegram notifications for trades
    """
    
    def __init__(self, telegram_bot=None):
        self.strategy = LiveTradingStrategy()
        self.telegram_bot = telegram_bot
        self.is_trading_enabled = False
        self.max_concurrent_positions = 3
        self.portfolio_value = 10000.0  # Starting portfolio value
        
        # Trading state
        self.active_positions: Dict[str, Position] = {}
        self.pending_signals: Dict[str, TradingSignal] = {}
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset_date = time.strftime("%Y-%m-%d")
        
        logger.info("Trading Bot Integration initialized")
    
    def enable_trading(self):
        """Enable live trading"""
        self.is_trading_enabled = True
        logger.info("Live trading ENABLED")
        self._send_telegram("🚀 Live trading ENABLED! Bot is now actively trading.")
    
    def disable_trading(self):
        """Disable live trading"""
        self.is_trading_enabled = False
        logger.info("Live trading DISABLED")
        self._send_telegram("⏸️ Live trading DISABLED. Bot is in monitoring mode.")
    
    async def process_scanner_data(self, token_data: dict):
        """
        Process token data from Helius scanner and generate trading signals
        
        Args:
            token_data: Token data from scanner bot
        """
        try:
            # Generate trading signal
            signal = self.strategy.analyze_token(token_data)
            
            if not signal:
                return
            
            mint = signal.mint
            
            # Log signal
            logger.info(f"Trading signal: {signal.signal.value} for {signal.symbol} "
                       f"(confidence: {signal.confidence*100:.1f}%)")
            
            # Store signal
            self.pending_signals[mint] = signal
            
            # Send Telegram notification
            self._send_trading_signal_notification(signal)
            
            # Execute trade if enabled
            if self.is_trading_enabled and signal.signal.value == "buy":
                await self._execute_buy_signal(signal)
            
        except Exception as e:
            logger.error(f"Error processing scanner data: {e}")
    
    async def _execute_buy_signal(self, signal: TradingSignal):
        """Execute buy signal (simulated trading)"""
        
        # Check position limits
        if len(self.active_positions) >= self.max_concurrent_positions:
            logger.warning(f"Max positions reached ({self.max_concurrent_positions}), skipping {signal.symbol}")
            return
        
        # Check if already have position
        if signal.mint in self.active_positions:
            logger.warning(f"Already have position in {signal.symbol}, skipping")
            return
        
        # Calculate position size
        position_size = self.portfolio_value * self.strategy.max_position_size
        quantity = position_size / signal.entry_price
        
        # Create position
        position = Position(
            mint=signal.mint,
            symbol=signal.symbol,
            entry_price=signal.entry_price,
            entry_time=time.time(),
            quantity=quantity,
            stop_loss=signal.stop_loss,
            take_profit=signal.target_price,
            current_price=signal.entry_price,
            pnl_percent=0.0,
            status="open"
        )
        
        # Add to active positions
        self.active_positions[signal.mint] = position
        
        # Update statistics
        self.daily_trades += 1
        
        # Log trade
        logger.info(f"BUY executed: {signal.symbol} | "
                   f"Price: ${signal.entry_price:.8f} | "
                   f"Quantity: {quantity:.0f} | "
                   f"Value: ${position_size:.2f}")
        
        # Send Telegram notification
        self._send_trade_execution_notification("BUY", signal, position)
        
        # Start position monitoring
        asyncio.create_task(self._monitor_position(position))
    
    async def _monitor_position(self, position: Position):
        """Monitor position for exit conditions"""
        
        while position.status == "open":
            try:
                # In real implementation, fetch current price from DEX
                # For now, simulate price updates
                current_price = await self._get_current_price(position.mint)
                
                if current_price:
                    # Update position
                    updated_position = self.strategy.update_position(position.mint, current_price)
                    
                    if updated_position and updated_position.status == "closed":
                        # Position closed
                        self._handle_position_closed(updated_position)
                        break
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error monitoring position {position.symbol}: {e}")
                await asyncio.sleep(30)
    
    async def _get_current_price(self, mint: str) -> Optional[float]:
        """
        Get current price for token (simulated)
        In real implementation, this would fetch from DEX APIs
        """
        # Simulate price movement (random walk)
        import random
        
        # Get current position
        if mint not in self.active_positions:
            return None
        
        position = self.active_positions[mint]
        
        # Simulate price movement (-2% to +5% per update)
        price_change = random.uniform(-0.02, 0.05)
        new_price = position.current_price * (1 + price_change)
        
        return new_price
    
    def _handle_position_closed(self, position: Position):
        """Handle closed position"""
        
        # Remove from active positions
        if position.mint in self.active_positions:
            del self.active_positions[position.mint]
        
        # Update daily PnL
        self.daily_pnl += position.pnl_percent * self.strategy.max_position_size * self.portfolio_value
        
        # Update portfolio value
        self.portfolio_value *= (1 + position.pnl_percent * self.strategy.max_position_size)
        
        # Log closure
        logger.info(f"Position closed: {position.symbol} | "
                   f"PnL: {position.pnl_percent*100:.1f}% | "
                   f"Portfolio: ${self.portfolio_value:.2f}")
        
        # Send Telegram notification
        self._send_position_closed_notification(position)
    
    def _send_trading_signal_notification(self, signal: TradingSignal):
        """Send Telegram notification for trading signal"""
        
        if not self.telegram_bot:
            return
        
        emoji = "🚀" if signal.signal.value == "buy" else "⏸️"
        status = "ENABLED" if self.is_trading_enabled else "DISABLED"
        
        message = f"""
{emoji} *Trading Signal*

**Token:** {signal.symbol}
**Signal:** {signal.signal.value.upper()}
**Type:** {signal.token_type.value}
**Confidence:** {signal.confidence*100:.1f}%

**Metrics:**
• Price: ${signal.entry_price:.8f}
• Volume 24h: ${signal.volume_24h:,.0f}
• Liquidity: ${signal.liquidity:,.0f}
• Util: {signal.util:.2f}
• Buyers 30m: {signal.buyers_30m}
• Age: {signal.age_minutes}m

**Price Changes:**
• 5m: {signal.price_change_5m*100:+.1f}%
• 1h: {signal.price_change_1h*100:+.1f}%

**Targets:**
• Take Profit: ${signal.target_price:.8f} (+{((signal.target_price/signal.entry_price)-1)*100:.1f}%)
• Stop Loss: ${signal.stop_loss:.8f} (-{((1-signal.stop_loss/signal.entry_price))*100:.1f}%)

**Reasoning:** {signal.reasoning}

**Trading:** {status}
"""
        
        self.telegram_bot.send_message(message, parse_mode="Markdown")
    
    def _send_trade_execution_notification(self, action: str, signal: TradingSignal, position: Position):
        """Send Telegram notification for trade execution"""
        
        if not self.telegram_bot:
            return
        
        emoji = "💰" if action == "BUY" else "💸"
        
        message = f"""
{emoji} *Trade Executed*

**Action:** {action}
**Token:** {position.symbol}
**Price:** ${position.entry_price:.8f}
**Quantity:** {position.quantity:.0f}
**Value:** ${position.quantity * position.entry_price:.2f}

**Targets:**
• Take Profit: ${position.take_profit:.8f}
• Stop Loss: ${position.stop_loss:.8f}

**Portfolio:** ${self.portfolio_value:.2f}
**Active Positions:** {len(self.active_positions)}
"""
        
        self.telegram_bot.send_message(message, parse_mode="Markdown")
    
    def _send_position_closed_notification(self, position: Position):
        """Send Telegram notification for position closure"""
        
        if not self.telegram_bot:
            return
        
        emoji = "✅" if position.pnl_percent > 0 else "❌"
        pnl_emoji = "📈" if position.pnl_percent > 0 else "📉"
        
        message = f"""
{emoji} *Position Closed*

**Token:** {position.symbol}
**Entry:** ${position.entry_price:.8f}
**Exit:** ${position.current_price:.8f}
{pnl_emoji} **PnL:** {position.pnl_percent*100:+.1f}%

**Hold Time:** {(time.time() - position.entry_time)/60:.1f} minutes

**Portfolio:** ${self.portfolio_value:.2f}
**Daily PnL:** {self.daily_pnl:.2f}
**Daily Trades:** {self.daily_trades}
"""
        
        self.telegram_bot.send_message(message, parse_mode="Markdown")
    
    def _send_telegram(self, message: str):
        """Send simple Telegram message"""
        if self.telegram_bot:
            self.telegram_bot.send_message(message)
    
    def get_trading_status(self) -> dict:
        """Get current trading status"""
        
        # Reset daily stats if new day
        current_date = time.strftime("%Y-%m-%d")
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset_date = current_date
        
        return {
            "trading_enabled": self.is_trading_enabled,
            "portfolio_value": self.portfolio_value,
            "active_positions": len(self.active_positions),
            "max_positions": self.max_concurrent_positions,
            "daily_pnl": self.daily_pnl,
            "daily_trades": self.daily_trades,
            "strategy_stats": self.strategy.get_performance_stats(),
            "recent_signals": self.strategy.get_signal_summary(5)
        }
    
    def get_position_summary(self) -> list:
        """Get summary of active positions"""
        
        positions = []
        for position in self.active_positions.values():
            positions.append({
                "symbol": position.symbol,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "pnl_percent": position.pnl_percent,
                "hold_time_minutes": (time.time() - position.entry_time) / 60,
                "take_profit": position.take_profit,
                "stop_loss": position.stop_loss
            })
        
        return positions

# Example integration with Helius scanner
class HeliusTradingBot:
    """Main trading bot that integrates scanner with trading strategy"""
    
    def __init__(self, scanner_bot, telegram_bot=None):
        self.scanner_bot = scanner_bot
        self.trading_integration = TradingBotIntegration(telegram_bot)
        self.is_running = False
    
    async def start_trading(self):
        """Start the trading bot"""
        self.is_running = True
        self.trading_integration.enable_trading()
        
        logger.info("Helius Trading Bot started")
        
        # Monitor scanner bot for new tokens
        while self.is_running:
            try:
                # In real implementation, this would listen to scanner bot events
                # For now, simulate by checking scanner bot's recent activity
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in trading bot: {e}")
                await asyncio.sleep(5)
    
    async def stop_trading(self):
        """Stop the trading bot"""
        self.is_running = False
        self.trading_integration.disable_trading()
        
        logger.info("Helius Trading Bot stopped")
    
    def get_status(self) -> dict:
        """Get bot status"""
        return {
            "is_running": self.is_running,
            "trading_status": self.trading_integration.get_trading_status(),
            "positions": self.trading_integration.get_position_summary()
        }

if __name__ == "__main__":
    # Example usage
    async def main():
        trading_bot = HeliusTradingBot(None)
        await trading_bot.start_trading()
    
    asyncio.run(main())
