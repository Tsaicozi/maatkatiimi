#!/usr/bin/env python3
"""
HybridTradingBot DiscoveryEngine testi
"""

import asyncio
from hybrid_trading_bot import HybridTradingBot

async def test_hybrid_bot():
    """Testaa HybridTradingBot DiscoveryEngine integraatio"""
    print("🧪 Testataan HybridTradingBot DiscoveryEngine integraatiota...")
    
    try:
        # Luo bot instance
        bot = HybridTradingBot()
        print('✅ HybridTradingBot luotu onnistuneesti')
        
        # Tarkista discovery_engine
        if hasattr(bot, 'discovery_engine'):
            print('✅ DiscoveryEngine kenttä löytyy')
            if bot.discovery_engine is None:
                print('⚠️ DiscoveryEngine on None')
            else:
                print('✅ DiscoveryEngine on alustettu')
                print(f'   - RPC endpoint: {bot.discovery_engine.rpc_endpoint}')
                print(f'   - Market sources: {len(bot.discovery_engine.market_sources)}')
                print(f'   - Min liquidity: ${bot.discovery_engine.min_liq_usd:,.0f}')
                print(f'   - Running: {bot.discovery_engine.running}')
        else:
            print('❌ DiscoveryEngine kenttä puuttuu')
            
        # Tarkista run_analysis_cycle metodi
        if hasattr(bot, 'run_analysis_cycle'):
            print('✅ run_analysis_cycle metodi löytyy')
        else:
            print('❌ run_analysis_cycle metodi puuttuu')
            
        # Tarkista hot_candidates käsittely
        if hasattr(bot, '_convert_token_candidate_to_dict'):
            print('✅ _convert_token_candidate_to_dict metodi löytyy')
        else:
            print('❌ _convert_token_candidate_to_dict metodi puuttuu')
            
        if hasattr(bot, '_send_hot_candidates_telegram'):
            print('✅ _send_hot_candidates_telegram metodi löytyy')
        else:
            print('❌ _send_hot_candidates_telegram metodi puuttuu')
            
        # Tarkista stop() metodi
        if hasattr(bot, 'stop'):
            print('✅ stop() metodi löytyy')
            # Testaa stop() metodia
            await bot.stop()
            print('✅ stop() metodi toimii')
        else:
            print('❌ stop() metodi puuttuu')
            
        print("🎉 HybridTradingBot testi valmis!")
        
    except Exception as e:
        print(f"❌ Virhe: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_hybrid_bot())