#!/usr/bin/env python3
"""
Test PumpPortal integration in Hybrid Trading Bot
"""

import asyncio
import logging
from datetime import datetime
from hybrid_trading_bot import HybridTokenScanner

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_pumpportal_integration():
    """Test PumpPortal integration in hybrid bot"""
    print("🚀 Testataan PumpPortal-integraatiota Hybrid Trading Botissa...")
    print("=" * 70)
    
    async with HybridTokenScanner() as scanner:
        print("✅ HybridTokenScanner alustettu")
        
        # Testaa PumpPortal-analyzer
        if scanner.pump_portal_analyzer:
            print("✅ PumpPortal analyzer löytyi")
            
            # Testaa hot tokens
            print("🔍 Testataan hot tokens...")
            hot_tokens_result = scanner.pump_portal_analyzer.get_hot_tokens(5)
            
            if 'error' in hot_tokens_result:
                print(f"❌ Hot tokens virhe: {hot_tokens_result['error']}")
            else:
                hot_tokens = hot_tokens_result.get('hot_tokens', [])
                print(f"✅ Löydettiin {len(hot_tokens)} hot tokenia")
                
                for i, token in enumerate(hot_tokens[:3], 1):
                    print(f"  {i}. {token['token_address'][:8]}... - Volyymi: ${token['volume_24h']:,.0f}")
            
            # Testaa trading activity
            print("\n📈 Testataan trading activity...")
            activity_result = scanner.pump_portal_analyzer.get_trading_activity(24)
            
            if 'error' in activity_result:
                print(f"❌ Trading activity virhe: {activity_result['error']}")
            else:
                activity = activity_result.get('trading_activity', {})
                print(f"✅ 24h aktiviteetti:")
                print(f"   - Kokonaiskauppat: {activity.get('total_trades', 0)}")
                print(f"   - Kokonaisvolyymi: ${activity.get('total_volume', 0):,.0f}")
                print(f"   - Uniikit tokenit: {activity.get('unique_tokens', 0)}")
            
            # Testaa crypto momentum
            print("\n🚀 Testataan crypto momentum...")
            momentum_result = scanner.pump_portal_analyzer.analyze_crypto_momentum()
            
            if 'error' in momentum_result:
                print(f"❌ Crypto momentum virhe: {momentum_result['error']}")
            else:
                print(f"✅ Crypto momentum:")
                print(f"   - Momentum score: {momentum_result.get('momentum_score', 0):.3f}")
                print(f"   - Market heat: {momentum_result.get('market_heat', 'Tuntematon')}")
                print(f"   - Hot tokens: {momentum_result.get('hot_tokens_count', 0)}")
            
            # Testaa PumpPortal skanning
            print("\n🔍 Testataan PumpPortal skanning...")
            pump_portal_tokens = await scanner._scan_pump_portal()
            print(f"✅ PumpPortal skanning löysi {len(pump_portal_tokens)} tokenia")
            
            if pump_portal_tokens:
                for i, token in enumerate(pump_portal_tokens[:3], 1):
                    print(f"  {i}. {token.symbol} - MC: ${token.market_cap:,.0f}, Vol: ${token.volume_24h:,.0f}")
                    print(f"     Age: {token.age_minutes}min, Risk: {token.risk_score:.2f}")
        else:
            print("❌ PumpPortal analyzer ei ole käytettävissä")
        
        # Testaa koko skanning-prosessi
        print("\n🔄 Testataan koko skanning-prosessi...")
        all_tokens = await scanner.scan_ultra_fresh_tokens()
        print(f"✅ Koko skanning löysi {len(all_tokens)} tokenia")
        
        # Laske PumpPortal-tokeneita
        pump_portal_count = sum(1 for token in all_tokens if token.dex == "PumpPortal")
        print(f"   - PumpPortal tokeneita: {pump_portal_count}")
        
        # Näytä top 3 tokenia
        if all_tokens:
            print("\n🏆 Top 3 tokenia:")
            for i, token in enumerate(all_tokens[:3], 1):
                print(f"  {i}. {token.symbol} ({token.dex})")
                print(f"     MC: ${token.market_cap:,.0f}, Vol: ${token.volume_24h:,.0f}")
                print(f"     Age: {token.age_minutes}min, Risk: {token.risk_score:.2f}")
                print(f"     Tech: {token.technical_score:.2f}, Social: {token.social_score:.2f}")

async def main():
    """Main test function"""
    try:
        await test_pumpportal_integration()
        print("\n" + "=" * 70)
        print("✅ PumpPortal-integraation testi valmis!")
    except Exception as e:
        print(f"\n❌ Testi epäonnistui: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
