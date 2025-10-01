#!/usr/bin/env python3
"""
Test script for Live Trading Strategy
Tests the strategy with sample token data
"""

import asyncio
import json
import time
from live_trading_strategy import LiveTradingStrategy, TokenType, TradeSignal
from trading_config import TradingConfig, get_strategy_config

def create_sample_token_data():
    """Create sample token data for testing"""
    
    # High momentum Pump.fun token
    pump_token = {
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
    
    # Meme token with strong momentum
    meme_token = {
        "mint": "DOGE1234567890abcdefghijklmnopqrstuvwxyz",
        "symbol": "DOGE",
        "dex": {
            "liq_usd": 30000,
            "vol_h24": 60000,
            "util": 2.0,
            "buyers30m": 25,
            "age_min": 30,
            "price_usd": 0.000045,
            "priceChange": {"m5": 15.2, "h1": 35.7}
        },
        "metadata": {}
    }
    
    # Low momentum token (should be rejected)
    low_momentum_token = {
        "mint": "LOW1234567890abcdefghijklmnopqrstuvwxyz",
        "symbol": "LOW",
        "dex": {
            "liq_usd": 5000,
            "vol_h24": 8000,
            "util": 1.6,
            "buyers30m": 2,
            "age_min": 180,
            "price_usd": 0.000001,
            "priceChange": {"m5": 1.2, "h1": 3.5}
        },
        "metadata": {}
    }
    
    # High liquidity, low momentum
    stable_token = {
        "mint": "STABLE1234567890abcdefghijklmnopqrstuvwxyz",
        "symbol": "STABLE",
        "dex": {
            "liq_usd": 100000,
            "vol_h24": 50000,
            "util": 0.5,
            "buyers30m": 50,
            "age_min": 60,
            "price_usd": 0.001,
            "priceChange": {"m5": 0.5, "h1": 2.1}
        },
        "metadata": {}
    }
    
    return [pump_token, meme_token, low_momentum_token, stable_token]

async def test_strategy():
    """Test the trading strategy with sample data"""
    
    print("🚀 Testing Live Trading Strategy")
    print("=" * 50)
    
    # Test different strategy configurations
    strategies = {
        "Balanced": get_strategy_config("balanced"),
        "Aggressive": get_strategy_config("aggressive"),
        "Conservative": get_strategy_config("conservative")
    }
    
    sample_tokens = create_sample_token_data()
    
    for strategy_name, config in strategies.items():
        print(f"\n📊 Testing {strategy_name} Strategy")
        print("-" * 30)
        
        # Create strategy instance with config
        strategy = LiveTradingStrategy()
        
        # Update strategy parameters
        strategy.max_position_size = config.max_position_size
        strategy.stop_loss_percent = config.stop_loss_percent
        strategy.take_profit_percent = config.take_profit_percent
        strategy.max_hold_time = config.max_hold_time
        strategy.min_liquidity = config.min_liquidity
        strategy.min_volume_24h = config.min_volume_24h
        strategy.min_util = config.min_util
        strategy.max_util = config.max_util
        strategy.min_trades_24h = config.min_trades_24h
        strategy.min_buyers_30m = config.min_buyers_30m
        strategy.min_price_change_5m = config.min_price_change_5m
        strategy.min_price_change_1h = config.min_price_change_1h
        strategy.max_age_minutes = config.max_age_minutes
        
        signals_generated = 0
        
        for token_data in sample_tokens:
            signal = strategy.analyze_token(token_data)
            
            if signal:
                signals_generated += 1
                print(f"✅ Signal: {signal.signal.value.upper()} for {signal.symbol}")
                print(f"   Type: {signal.token_type.value}")
                print(f"   Confidence: {signal.confidence*100:.1f}%")
                print(f"   Entry: ${signal.entry_price:.8f}")
                print(f"   Target: ${signal.target_price:.8f} (+{((signal.target_price/signal.entry_price)-1)*100:.1f}%)")
                print(f"   Stop Loss: ${signal.stop_loss:.8f} (-{((1-signal.stop_loss/signal.entry_price))*100:.1f}%)")
                print(f"   Reasoning: {signal.reasoning}")
            else:
                print(f"❌ No signal for {token_data['symbol']}")
        
        print(f"\n📈 {strategy_name} Results:")
        print(f"   Signals generated: {signals_generated}/{len(sample_tokens)}")
        print(f"   Success rate: {signals_generated/len(sample_tokens)*100:.1f}%")

async def test_position_management():
    """Test position management functionality"""
    
    print("\n\n🎯 Testing Position Management")
    print("=" * 50)
    
    strategy = LiveTradingStrategy()
    
    # Create a test position
    test_token = create_sample_token_data()[0]  # Pump token
    signal = strategy.analyze_token(test_token)
    
    if signal and signal.signal == TradeSignal.BUY:
        print(f"✅ Created test position for {signal.symbol}")
        
        # Simulate position updates
        for i in range(5):
            # Simulate price movement
            price_change = 0.02 * (i + 1)  # 2%, 4%, 6%, 8%, 10%
            new_price = signal.entry_price * (1 + price_change)
            
            position = strategy.update_position(signal.mint, new_price)
            
            if position:
                print(f"   Update {i+1}: Price ${new_price:.8f} | PnL: {position.pnl_percent*100:+.1f}% | Status: {position.status}")
                
                if position.status == "closed":
                    print(f"   🎉 Position closed with {position.pnl_percent*100:+.1f}% PnL")
                    break
            else:
                print(f"   Update {i+1}: No position found")
    
    # Show performance stats
    stats = strategy.get_performance_stats()
    print(f"\n📊 Performance Stats:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

async def test_confidence_calculation():
    """Test confidence calculation with different scenarios"""
    
    print("\n\n🧠 Testing Confidence Calculation")
    print("=" * 50)
    
    strategy = LiveTradingStrategy()
    
    # Test scenarios
    scenarios = [
        {
            "name": "Perfect Storm",
            "change_5m": 0.15,  # 15%
            "change_1h": 0.25,  # 25%
            "liquidity": 50000,
            "volume_24h": 100000,
            "util": 2.0,
            "buyers_30m": 30,
            "age_minutes": 30,
            "token_type": TokenType.PUMP_FUN
        },
        {
            "name": "Good Momentum",
            "change_5m": 0.08,  # 8%
            "change_1h": 0.15,  # 15%
            "liquidity": 25000,
            "volume_24h": 50000,
            "util": 2.0,
            "buyers_30m": 15,
            "age_minutes": 60,
            "token_type": TokenType.MEME
        },
        {
            "name": "Weak Signal",
            "change_5m": 0.03,  # 3%
            "change_1h": 0.08,  # 8%
            "liquidity": 15000,
            "volume_24h": 25000,
            "util": 1.5,
            "buyers_30m": 8,
            "age_minutes": 90,
            "token_type": TokenType.UNKNOWN
        }
    ]
    
    for scenario in scenarios:
        confidence = strategy._calculate_confidence(
            scenario["change_5m"],
            scenario["change_1h"],
            scenario["liquidity"],
            scenario["volume_24h"],
            scenario["util"],
            scenario["buyers_30m"],
            scenario["age_minutes"],
            scenario["token_type"]
        )
        
        print(f"📊 {scenario['name']}: {confidence*100:.1f}% confidence")
        print(f"   Momentum: {scenario['change_5m']*100:.1f}% (5m), {scenario['change_1h']*100:.1f}% (1h)")
        print(f"   Volume: ${scenario['volume_24h']:,} | Liquidity: ${scenario['liquidity']:,}")
        print(f"   Util: {scenario['util']:.1f} | Buyers: {scenario['buyers_30m']} | Age: {scenario['age_minutes']}m")
        print(f"   Type: {scenario['token_type'].value}")

async def main():
    """Main test function"""
    
    print("🧪 Live Trading Strategy Test Suite")
    print("=" * 60)
    
    await test_strategy()
    await test_position_management()
    await test_confidence_calculation()
    
    print("\n\n✅ All tests completed!")
    print("\n💡 Key Insights:")
    print("   • Pump.fun tokens get confidence bonus")
    print("   • Strong momentum (5m + 1h) increases confidence")
    print("   • High volume/liquidity improves signal quality")
    print("   • Position management handles exits automatically")
    print("   • Different strategies suit different risk profiles")

if __name__ == "__main__":
    asyncio.run(main())
