"""
PumpPortal Demo - Testaa reaaliaikainen kryptodata
"""

import asyncio
import json
from datetime import datetime
from pumpportal_integration import PumpPortalAnalyzer

async def demo_pumpportal():
    """Demo PumpPortal-integraatiosta"""
    print("🚀 PumpPortal Demo - Reaaliaikainen kryptodata")
    print("=" * 60)
    
    # Luo analyzer
    analyzer = PumpPortalAnalyzer()
    
    if not analyzer.client.available:
        print("❌ PumpPortal ei ole saatavilla")
        return
    
    print("✅ PumpPortal analyzer luotu")
    
    # Yhdistä WebSocket:iin
    print("🔌 Yhdistetään PumpPortal WebSocket:iin...")
    if not await analyzer.client.connect():
        print("❌ Yhteys epäonnistui")
        return
    
    print("✅ Yhdistetty PumpPortal:iin")
    
    # Tilaa tapahtumat
    print("📝 Tilataan tapahtumat...")
    
    # Tilaa uusien tokenien luomistapahtumat
    await analyzer.client.subscribe_new_tokens()
    print("✅ Tilattu uusien tokenien luomistapahtumat")
    
    # Tilaa migraatiotapahtumat
    await analyzer.client.subscribe_migrations()
    print("✅ Tilattu migraatiotapahtumat")
    
    # Tilaa tiettyjen tokenien kauppatapahtumat
    tokens_to_watch = [
        "91WNez8D22NwBssQbkzjy4s2ipFrzpmn5hfvWVe2aY5p",
        "Bwc4EBE65qXVzZ9ZiieBraj9GZL4Y2d7NN7B9pXENWR2"
    ]
    await analyzer.client.subscribe_token_trades(tokens_to_watch)
    print(f"✅ Tilattu token-kauppatapahtumat: {len(tokens_to_watch)} tokenille")
    
    # Tilaa tiettyjen tilien kauppatapahtumat
    accounts_to_watch = [
        "AArPXm8JatJiuyEffuC1un2Sc835SULa4uQqDcaGpAjV"
    ]
    await analyzer.client.subscribe_account_trades(accounts_to_watch)
    print(f"✅ Tilattu tili-kauppatapahtumat: {len(accounts_to_watch)} tilille")
    
    print("\n🎧 Kuunnellaan tapahtumia 30 sekuntia...")
    print("(Paina Ctrl+C lopettaaksesi)")
    
    try:
        # Kuuntele 30 sekuntia
        await asyncio.wait_for(analyzer.client.listen(), timeout=30.0)
    except asyncio.TimeoutError:
        print("\n⏰ 30 sekuntia kulunut, lopetetaan kuuntelu")
    except KeyboardInterrupt:
        print("\n⏹️ Käyttäjä lopetti kuuntelun")
    finally:
        # Pysäytä kuuntelu
        analyzer.client.stop()
        await analyzer.client.disconnect()
        print("🔌 Yhteys suljettu")
    
    # Analysoi kerätty data
    print("\n📊 Analysoidaan kerättyä dataa...")
    
    # Hae kuumimmat tokenit
    hot_tokens = analyzer.get_hot_tokens(5)
    print(f"\n🔥 Kuumimmat tokenit ({len(hot_tokens)}):")
    for i, token in enumerate(hot_tokens, 1):
        print(f"{i}. {token['token_address'][:8]}... - Volyymi: ${token['volume_24h']:,.0f}")
    
    # Hae kaupankäyntiaktiviteetti
    activity = analyzer.get_trading_activity(24)
    print(f"\n📈 Kaupankäyntiaktiviteetti (24h):")
    print(f"   - Kokonaiskauppat: {activity['total_trades']}")
    print(f"   - Kokonaisvolyymi: ${activity['total_volume']:,.0f}")
    print(f"   - Uniikit tokenit: {activity['unique_tokens']}")
    print(f"   - Keskimääräinen kauppakoko: ${activity['avg_trade_size']:,.0f}")
    
    # Tallenna data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"pumpportal_demo_{timestamp}.json"
    
    demo_data = {
        "timestamp": timestamp,
        "hot_tokens": hot_tokens,
        "trading_activity": activity,
        "total_tokens_created": len(analyzer.token_data),
        "total_trades": len(analyzer.trade_data)
    }
    
    with open(output_file, 'w') as f:
        json.dump(demo_data, f, indent=2, default=str)
    
    print(f"\n💾 Demo-data tallennettu: {output_file}")
    print("=" * 60)
    print("✅ PumpPortal demo valmis!")

if __name__ == "__main__":
    # Käynnistä demo
    asyncio.run(demo_pumpportal())
