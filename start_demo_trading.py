#!/usr/bin/env python3
"""
Demo Trading Bot Starter
Käynnistää Helius scanner botin demo kaupankäynnillä
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
from demo_trading_config import setup_demo_trading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('demo_trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main demo trading bot function"""
    
    print("🎯 DEMO TRADING BOT STARTUP")
    print("=" * 50)
    
    # Setup demo trading configuration
    demo_config = setup_demo_trading()
    
    # Import and start the main bot
    try:
        from run_helius_scanner import main as run_scanner_main
        
        print(f"\n🚀 Starting Helius Scanner Bot with Demo Trading...")
        print(f"💰 Demo Account: {demo_config.config['demo_account_id']}")
        print(f"💵 Starting Capital: ${demo_config.config['portfolio_value']:.2f}")
        print(f"📊 Max Positions: {demo_config.config['max_positions']}")
        print(f"⚠️  Risk per Trade: {demo_config.config['risk_per_trade']*100:.1f}%")
        print(f"🛡️  Stop Loss: {demo_config.config['stop_loss_pct']*100:.1f}%")
        print(f"🎯 Take Profit 1: {demo_config.config['take_profit_1_pct']*100:.1f}%")
        print(f"🎯 Take Profit 2: {demo_config.config['take_profit_2_pct']*100:.1f}%")
        print(f"🔄 Trailing Stop: {demo_config.config['trailing_stop_pct']*100:.1f}%")
        print(f"🧪 Demo Mode: {demo_config.config['demo_mode']}")
        print(f"🔒 Dry Run: {demo_config.config['dry_run']}")
        
        print("\n" + "=" * 50)
        print("🎮 DEMO TRADING ACTIVE - NO REAL MONEY AT RISK!")
        print("=" * 50)
        
        # Start the scanner bot
        await run_scanner_main()
        
    except KeyboardInterrupt:
        print("\n🛑 Demo trading bot stopped by user")
        logger.info("Demo trading bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting demo trading bot: {e}")
        logger.error(f"Error starting demo trading bot: {e}")
        sys.exit(1)

def show_demo_stats():
    """Show demo trading statistics"""
    try:
        from demo_trading_config import DemoTradingConfig
        config = DemoTradingConfig()
        print(config.get_stats_summary())
    except Exception as e:
        print(f"Error loading demo stats: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        show_demo_stats()
    else:
        asyncio.run(main())
