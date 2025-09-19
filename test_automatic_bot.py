#!/usr/bin/env python3
"""
AutomaticHybridBot DiscoveryEngine testi
"""

import asyncio
from automatic_hybrid_bot import AutomaticHybridBot

async def test_automatic_bot():
    """Testaa AutomaticHybridBot DiscoveryEngine integraatio"""
    print("🧪 Testataan AutomaticHybridBot DiscoveryEngine integraatiota...")
    
    try:
        # Luo bot instance testimoodissa (max 2 sykliä, max 30 sekuntia)
        bot = AutomaticHybridBot(max_cycles=2, max_runtime_sec=30.0)
        print('✅ AutomaticHybridBot luotu onnistuneesti (testimoodi: max 2 sykliä, 30s)')
        
        # Tarkista että se voi luoda HybridTradingBot:in
        if hasattr(bot, 'trading_bot_class'):
            print('✅ trading_bot_class löytyy')
            trading_bot = bot.trading_bot_class()
            if hasattr(trading_bot, 'discovery_engine'):
                print('✅ DiscoveryEngine löytyy trading bot:ista')
                if trading_bot.discovery_engine is not None:
                    print('✅ DiscoveryEngine on alustettu')
                    print(f'   - RPC endpoint: {trading_bot.discovery_engine.rpc_endpoint}')
                    print(f'   - Market sources: {len(trading_bot.discovery_engine.market_sources)}')
                    print(f'   - Min liquidity: ${trading_bot.discovery_engine.min_liq_usd:,.0f}')
                else:
                    print('⚠️ DiscoveryEngine on None')
            else:
                print('❌ DiscoveryEngine puuttuu trading bot:ista')
        else:
            print('❌ trading_bot_class puuttuu')
            
        # Tarkista että bot voi käynnistää DiscoveryEngine:in
        if hasattr(bot, 'trading_bot') and bot.trading_bot:
            if hasattr(bot.trading_bot, 'discovery_engine') and bot.trading_bot.discovery_engine:
                print('✅ DiscoveryEngine löytyy bot.trading_bot:ista')
                # Käynnistä DiscoveryEngine
                await bot.trading_bot.discovery_engine.start()
                print('✅ DiscoveryEngine käynnistetty')
                
                # Testaa bot.stop() metodia
                if hasattr(bot.trading_bot, 'stop'):
                    await bot.trading_bot.stop()
                    print('✅ trading_bot.stop() toimii')
                else:
                    # Fallback: sammuta suoraan DiscoveryEngine
                    await bot.trading_bot.discovery_engine.stop()
                    print('✅ DiscoveryEngine sammutettu suoraan')
            else:
                print('⚠️ DiscoveryEngine puuttuu bot.trading_bot:ista')
        else:
            print('⚠️ bot.trading_bot puuttuu')
        
        # Testaa testimoodi - käynnistä bot lyhyeksi ajaksi
        print('🔄 Testataan testimoodia - käynnistetään bot...')
        try:
            # Käynnistä bot taustalla
            bot_task = asyncio.create_task(bot.run())
            
            # Odota että bot lopettaa testimoodissa
            await bot_task
            print('✅ Bot lopetti testimoodissa onnistuneesti')
            
        except Exception as e:
            print(f'⚠️ Bot testimoodi virhe: {e}')
            # Varmista että bot pysähtyy
            bot.stop()
            
        print("🎉 AutomaticHybridBot testi valmis!")
        
    except Exception as e:
        print(f"❌ Virhe: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_automatic_bot())
