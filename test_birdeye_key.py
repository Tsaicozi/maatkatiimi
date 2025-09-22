#!/usr/bin/env python3
"""
Testaa Birdeye API-avaimen toimivuus
"""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

# Lataa .env-tiedosto jos on
env_path = Path(".env")
if env_path.exists():
    load_dotenv()
    print("✅ .env-tiedosto ladattu")
else:
    print("⚠️ .env-tiedostoa ei löydy, luodaan se...")


async def test_birdeye_key(api_key: str):
    """Testaa Birdeye API-avaimen toimivuus"""
    print(f"\n🔍 Testataan avainta: {api_key[:8]}...")
    
    # Test 1: Basic API call
    url = "https://public-api.birdeye.so/v1/token/list"
    headers = {"X-API-KEY": api_key}
    params = {"chain": "solana", "limit": 1}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                print(f"📡 Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print("✅ API-avain toimii!")
                    
                    # Näytä ensimmäinen token
                    if data.get("data", {}).get("items"):
                        token = data["data"]["items"][0]
                        print(f"   Esimerkki token: {token.get('symbol', 'Unknown')}")
                    return True
                    
                elif response.status == 401:
                    print("❌ API-avain ei kelpaa (401 Unauthorized)")
                    return False
                    
                elif response.status == 429:
                    print("⚠️ Rate limit saavutettu (429)")
                    print("   Avain toimii, mutta on rate limitissä")
                    return True
                    
                else:
                    text = await response.text()
                    print(f"❌ Odottamaton vastaus: {response.status}")
                    print(f"   Viesti: {text[:200]}")
                    return False
                    
    except Exception as e:
        print(f"❌ Virhe: {e}")
        return False


async def test_websocket(api_key: str = None):
    """Testaa Birdeye WebSocket-yhteys"""
    print("\n🔌 Testataan WebSocket-yhteyttä...")
    
    import websockets
    import json
    
    ws_url = "wss://public-api.birdeye.so/socket"
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("✅ WebSocket-yhteys muodostettu")
            
            # Subscribe to new pairs
            subscribe_msg = {
                "type": "subscribe",
                "channel": "newPairs",
                "params": {
                    "chain": "solana"
                }
            }
            
            if api_key:
                subscribe_msg["apiKey"] = api_key
            
            await ws.send(json.dumps(subscribe_msg))
            print("📤 Tilaus lähetetty")
            
            # Odota vastausta
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(message)
                print(f"📥 Vastaus: {data.get('type', 'unknown')}")
                
                if data.get("type") == "subscribed":
                    print("✅ WebSocket toimii!")
                    return True
                else:
                    print(f"⚠️ Odottamaton vastaus: {data}")
                    return False
                    
            except asyncio.TimeoutError:
                print("⚠️ Ei vastausta 5 sekunnissa")
                return False
                
    except Exception as e:
        print(f"❌ WebSocket-virhe: {e}")
        return False


async def main():
    print("=" * 60)
    print("🐦 BIRDEYE API KEY TESTER 🔑")
    print("=" * 60)
    
    # Tarkista ympäristömuuttujat
    api_key = os.getenv("BIRDEYE_API_KEY")
    
    if not api_key:
        print("\n❌ BIRDEYE_API_KEY ei löydy ympäristömuuttujista!")
        print("\n📝 Ohje:")
        print("1. Luo .env-tiedosto projektikansioon")
        print("2. Lisää sinne: BIRDEYE_API_KEY=your_api_key_here")
        print("3. Aja tämä scripti uudelleen")
        
        # Tarkista onko avain config.yaml:ssa
        if Path("config.yaml").exists():
            import yaml
            with open("config.yaml", "r") as f:
                config = yaml.safe_load(f)
                config_key = config.get("sources", {}).get("birdeye", {}).get("api_key")
                
                if config_key and config_key != "null":
                    print(f"\n⚠️ Löytyi avain config.yaml:sta: {config_key[:8]}...")
                    print("   Tämä ei ole turvallista! Siirrä avain .env-tiedostoon.")
                    
                    # Testaa silti
                    await test_birdeye_key(config_key)
                    await test_websocket(config_key)
        
        return
    
    print(f"\n✅ Löytyi BIRDEYE_API_KEY: {api_key[:8]}...")
    
    # Testaa API
    api_works = await test_birdeye_key(api_key)
    
    # Testaa WebSocket
    ws_works = await test_websocket(api_key)
    
    # Yhteenveto
    print("\n" + "=" * 60)
    print("📊 YHTEENVETO:")
    print("=" * 60)
    
    if api_works and ws_works:
        print("✅ Kaikki toimii! Avain on valmis käytettäväksi.")
        print("\n🚀 Seuraavat vaiheet:")
        print("1. Aja: python3 setup_birdeye_keys.py")
        print("2. Valitse: '1. Aseta uudet API-avaimet'")
        print("3. Avain lisätään automaattisesti hallintaan")
    elif api_works:
        print("✅ REST API toimii")
        print("⚠️ WebSocket ei toimi (voi vaatia API-avaimen)")
    else:
        print("❌ API-avain ei toimi oikein")
        print("\n🔧 Tarkista:")
        print("1. Onko avain oikein kirjoitettu?")
        print("2. Onko avain aktiivinen?")
        print("3. Onko Birdeye API toiminnassa?")


if __name__ == "__main__":
    asyncio.run(main())