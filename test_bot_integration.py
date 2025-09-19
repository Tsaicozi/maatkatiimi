#!/usr/bin/env python3
"""
HybridTradingBot DiscoveryEngine integraatio testi
"""

import asyncio
from hybrid_trading_bot import HybridTradingBot
from discovery_engine import TokenCandidate
from datetime import datetime
from zoneinfo import ZoneInfo

async def test_bot_integration():
    """Testaa HybridTradingBot DiscoveryEngine integraatio"""
    print("🧪 Testataan HybridTradingBot DiscoveryEngine integraatiota...")
    
    try:
        # Luo bot instance
        bot = HybridTradingBot()
        print('✅ HybridTradingBot luotu onnistuneesti')
        
        # Tarkista DiscoveryEngine
        if bot.discovery_engine is None:
            print('❌ DiscoveryEngine on None')
            return
            
        print('✅ DiscoveryEngine löytyy')
        
        # Käynnistä DiscoveryEngine
        await bot.discovery_engine.start()
        print('✅ DiscoveryEngine käynnistetty')
        
        # Lisää mock kandidatti suoraan queue:een
        mock_candidate = TokenCandidate(
            mint='TEST_MINT_123',
            symbol='TEST',
            name='Test Token',
            source='manual_test',
            liquidity_usd=10000.0,
            age_minutes=2.0,
            mint_authority_renounced=True,
            freeze_authority_renounced=True,
            lp_locked=True,
            top10_holder_share=0.05,
            unique_buyers_5m=75,
            buy_sell_ratio=1.3
        )
        
        await bot.discovery_engine.candidate_queue.put(mock_candidate)
        print('✅ Mock kandidatti lisätty')
        
        # Odota että processor käsittelee sen (lyhyempi testissä)
        await asyncio.sleep(0.5)
        
        # Hae hot candidates
        hot_candidates = bot.discovery_engine.best_candidates(k=5, min_score=0.65)
        print(f'✅ Löydettiin {len(hot_candidates)} hot candidate:ja')
        
        if hot_candidates:
            c = hot_candidates[0]
            print(f'   - {c.symbol}: score={c.overall_score:.2f}, liq=${c.liquidity_usd:,.0f}')
            print(f'     mint_renounced={c.mint_authority_renounced}, lp_locked={c.lp_locked}')
            print(f'     top10_share={c.top10_holder_share:.2%}, buyers_5m={c.unique_buyers_5m}')
        
        # Testaa run_analysis_cycle metodia
        print('🔄 Testataan run_analysis_cycle metodia...')
        result = await bot.run_analysis_cycle()
        
        print('✅ run_analysis_cycle suoritettu')
        print(f'   - Tokeneita skannattu: {result.get("tokens_found", 0)}')
        print(f'   - Hot candidates: {len(result.get("hot_candidates", []))}')
        print(f'   - Signaaleja generoitu: {result.get("signals_generated", 0)}')
        
        # Testaa bot.stop() metodia
        if hasattr(bot, 'stop'):
            await bot.stop()
            print('✅ bot.stop() toimii')
        else:
            # Fallback: sammuta suoraan DiscoveryEngine
            await bot.discovery_engine.stop()
            await bot.discovery_engine.wait_closed(timeout=2.0)
            print('✅ DiscoveryEngine sammutettu suoraan')
        
        print("🎉 Integraatio testi valmis!")
        
    except Exception as e:
        print(f"❌ Virhe: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bot_integration())
