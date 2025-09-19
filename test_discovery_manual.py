#!/usr/bin/env python3
"""
Manuaalinen DiscoveryEngine testi
"""

import asyncio
from discovery_engine import DiscoveryEngine, TokenCandidate
from datetime import datetime
from zoneinfo import ZoneInfo

async def test_discovery():
    """Testaa DiscoveryEngine perustoiminnallisuus"""
    print("🧪 Aloitetaan DiscoveryEngine testi...")
    
    # Luo DiscoveryEngine ilman sources:ia
    engine = DiscoveryEngine(
        rpc_endpoint='https://api.mainnet-beta.solana.com',
        market_sources=[],
        min_liq_usd=3000.0
    )
    
    print('✅ DiscoveryEngine luotu onnistuneesti')
    
    # Käynnistä engine
    await engine.start()
    print('✅ DiscoveryEngine käynnistetty')
    
    # Lisää mock kandidatti suoraan
    candidate = TokenCandidate(
        mint='TEST_MINT_123',
        symbol='TEST',
        name='Test Token',
        source='manual_test',
        liquidity_usd=10000.0,
        age_minutes=2.0
    )
    
    # Lisää kandidatti queue:een
    await engine.candidate_queue.put(candidate)
    print('✅ Mock kandidatti lisätty')
    
    # Odota että processor käsittelee sen (käytä run_until_idle)
    await engine.run_until_idle(idle_seconds=0.5, max_wait=2.0)
    print('✅ Odotettu että processor käsitteli kandidatin')
    
    # Hae parhaat kandidatit
    candidates = engine.best_candidates(k=5, min_score=0.65)
    print(f'✅ Löydettiin {len(candidates)} kandidattia')
    
    if candidates:
        c = candidates[0]
        print(f'   - {c.symbol}: score={c.overall_score:.2f}, liq=${c.liquidity_usd:,.0f}')
        print(f'     mint_renounced={c.mint_authority_renounced}, lp_locked={c.lp_locked}')
        print(f'     top10_share={c.top10_holder_share:.2%}, buyers_5m={c.unique_buyers_5m}')
    
    # Sammuta engine
    await engine.stop()
    await engine.wait_closed(timeout=2.0)
    print('✅ DiscoveryEngine sammutettu')
    print("🎉 Testi valmis!")

if __name__ == "__main__":
    asyncio.run(test_discovery())
