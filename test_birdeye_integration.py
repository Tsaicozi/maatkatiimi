#!/usr/bin/env python3
"""
Testaa Birdeye-integraation toimivuus HybridTradingBotin kanssa
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Lataa .env
if Path(".env").exists():
    load_dotenv()
    print("✅ .env ladattu")

# Aseta lokitus
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_direct_api():
    """Testaa suora API-kutsu vanhalla tavalla"""
    print("\n" + "="*60)
    print("1. TESTAA VANHA TAPA (suora API-avain)")
    print("="*60)
    
    api_key = os.getenv("BIRDEYE_API_KEY")
    if not api_key:
        print("❌ BIRDEYE_API_KEY puuttuu")
        return False
    
    print(f"✅ Löytyi avain: {api_key[:8]}...")
    
    import aiohttp
    url = "https://public-api.birdeye.so/v1/token/list"
    headers = {"X-API-KEY": api_key}
    params = {"chain": "solana", "limit": 1}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                print(f"📡 Status: {response.status}")
                if response.status == 200:
                    print("✅ Vanha tapa toimii")
                    return True
                else:
                    print(f"❌ Virhe: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Virhe: {e}")
        return False


async def test_key_manager():
    """Testaa Key Manager"""
    print("\n" + "="*60)
    print("2. TESTAA KEY MANAGER")
    print("="*60)
    
    try:
        from birdeye_key_manager import BirdeyeKeyManager
        
        manager = BirdeyeKeyManager()
        
        # Lataa avaimet
        if await manager.load_keys():
            status = await manager.get_status()
            print(f"✅ Key Manager toimii")
            print(f"   - Avaimia: {status['total_keys']}")
            print(f"   - Aktiivisia: {status['active_keys']}")
            
            # Hae avain
            key = await manager.get_key()
            if key:
                print(f"✅ Saatiin avain: {key[:8]}...")
                return True
            else:
                print("❌ Ei saatu avainta")
                return False
        else:
            print("❌ Avainten lataus epäonnistui")
            
            # Yritä lisätä .env:stä
            env_key = os.getenv("BIRDEYE_API_KEY")
            if env_key:
                print(f"🔧 Lisätään avain .env:stä...")
                if await manager.add_key(env_key, "env_key"):
                    print("✅ Avain lisätty")
                    await manager.save_keys()
                    return True
            return False
            
    except Exception as e:
        print(f"❌ Key Manager virhe: {e}")
        return False


async def test_integration():
    """Testaa integraatio"""
    print("\n" + "="*60)
    print("3. TESTAA INTEGRAATIO")
    print("="*60)
    
    try:
        from birdeye_integration import birdeye
        
        # Alusta
        if await birdeye.initialize():
            print("✅ Integraatio alustettu")
            
            # Testaa API-kutsu
            usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            token_info = await birdeye.get_token_info(usdc_mint)
            
            if token_info:
                print("✅ API-kutsu toimii")
                data = token_info.get("data", {})
                print(f"   Token: {data.get('symbol', '?')} - {data.get('name', '?')}")
                return True
            else:
                print("❌ API-kutsu epäonnistui")
                return False
        else:
            print("❌ Alustus epäonnistui")
            return False
            
    except Exception as e:
        print(f"❌ Integraatio virhe: {e}")
        return False


async def test_hybrid_bot():
    """Testaa HybridTradingBot-integraatio"""
    print("\n" + "="*60)
    print("4. TESTAA HYBRID BOT INTEGRAATIO")
    print("="*60)
    
    try:
        from hybrid_trading_bot import HybridTradingBot
        
        # Luo minimal config
        import yaml
        config = {
            'telegram': {'bot_token': 'test', 'chat_id': 'test'},
            'trading': {'initial_capital': 10000},
            'discovery': {'enabled': False}
        }
        
        # Alusta botti
        bot = HybridTradingBot(config)
        
        # Tarkista onko integraatio käytössä
        if hasattr(bot, 'birdeye_integration') and bot.birdeye_integration:
            print("✅ Bot käyttää Birdeye-integraatiota")
            
            # Alusta integraatio
            await bot.birdeye_integration.initialize()
            
            # Testaa skannaus
            print("🔍 Testataan _scan_birdeye()...")
            tokens = await bot._scan_birdeye()
            
            if tokens:
                print(f"✅ Löytyi {len(tokens)} tokenia")
                for token in tokens[:3]:
                    print(f"   - {token.symbol}: ${token.real_price:.6f}")
                return True
            else:
                print("⚠️ Ei löytynyt tokeneita (voi olla normaalia)")
                return True
                
        elif bot.birdeye_api_key:
            print(f"⚠️ Bot käyttää vanhaa tapaa (suora avain)")
            print(f"   Avain: {bot.birdeye_api_key[:8]}...")
            return True
        else:
            print("❌ Ei Birdeye-konfiguraatiota")
            return False
            
    except Exception as e:
        print(f"❌ HybridBot virhe: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Pääohjelma"""
    print("="*60)
    print("🧪 BIRDEYE INTEGRATION TESTER")
    print("="*60)
    
    results = []
    
    # 1. Testaa vanha tapa
    results.append(("Vanha tapa", await test_direct_api()))
    
    # 2. Testaa Key Manager
    results.append(("Key Manager", await test_key_manager()))
    
    # 3. Testaa integraatio
    results.append(("Integraatio", await test_integration()))
    
    # 4. Testaa HybridBot
    results.append(("HybridBot", await test_hybrid_bot()))
    
    # Yhteenveto
    print("\n" + "="*60)
    print("📊 YHTEENVETO")
    print("="*60)
    
    all_ok = True
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
        if not result:
            all_ok = False
    
    print("\n" + "="*60)
    
    if all_ok:
        print("✅ KAIKKI TOIMII!")
        print("\nVoit nyt käynnistää botin:")
        print("  python3 hybrid_trading_bot.py")
    else:
        print("⚠️ JOITAIN ONGELMIA HAVAITTU")
        print("\nSuositukset:")
        print("1. Varmista että .env-tiedostossa on BIRDEYE_API_KEY")
        print("2. Aja: python3 setup_birdeye_keys.py")
        print("3. Testaa avain: python3 test_birdeye_key.py")


if __name__ == "__main__":
    asyncio.run(main())