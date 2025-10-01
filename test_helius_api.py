#!/usr/bin/env python3
"""
Testi-skripti Helius API-avaimen tarkistamiseen
"""
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def test_helius_api():
    api_key = os.getenv("HELIUS_API_KEY")
    
    if not api_key:
        print("❌ HELIUS_API_KEY ei löydy .env tiedostosta")
        return False
    
    print(f"✅ API-avain löydetty: {api_key[:8]}...{api_key[-4:]}")
    
    # Testaa HTTP API
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    
    test_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getHealth"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"🔍 Testataan HTTP RPC: {rpc_url[:50]}...")
            async with session.post(rpc_url, json=test_payload) as response:
                print(f"📡 HTTP status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ HTTP RPC toimii: {result}")
                    
                    # Testaa WebSocket URL
                    ws_url = f"wss://mainnet.helius-rpc.com/?api-key={api_key}"
                    print(f"🔍 WebSocket URL: {ws_url[:50]}...")
                    
                    return True
                else:
                    print(f"❌ HTTP RPC epäonnistui: {response.status}")
                    text = await response.text()
                    print(f"Virhe: {text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Yhteyden testaus epäonnistui: {e}")
        return False

async def test_websocket():
    api_key = os.getenv("HELIUS_API_KEY")
    # Kokeillaan eri WebSocket URL muotoja
    ws_urls = [
        f"wss://mainnet.helius-rpc.com/?api-key={api_key}",
        f"wss://atlas-mainnet.helius-rpc.com/?api-key={api_key}",
        f"wss://rpc.helius.xyz/?api-key={api_key}"
    ]
    
    try:
        import websockets
        print(f"🔍 Testataan WebSocket-yhteys...")
        
        for i, ws_url in enumerate(ws_urls, 1):
            print(f"  Yritys {i}: {ws_url[:60]}...")
            try:
                async with websockets.connect(ws_url) as websocket:
                    # Lähetä ping
                    await websocket.send('{"jsonrpc":"2.0","id":1,"method":"getHealth"}')
                    response = await websocket.recv()
                    print(f"✅ WebSocket toimii URL:lla {i}: {response}")
                    return True
            except Exception as e:
                print(f"  ❌ URL {i} epäonnistui: {e}")
        
        print("❌ Kaikki WebSocket URL:t epäonnistuivat")
        return False
            
    except Exception as e:
        print(f"❌ WebSocket-testaus epäonnistui: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testataan Helius API-avain...")
    print("=" * 50)
    
    # Tarkista .env tiedosto
    if os.path.exists(".env"):
        print("✅ .env tiedosto löytyy")
    else:
        print("❌ .env tiedosto puuttuu")
    
    # Testaa API
    result = asyncio.run(test_helius_api())
    
    if result:
        print("\n🔍 Testataan WebSocket-yhteys...")
        ws_result = asyncio.run(test_websocket())
        
        if ws_result:
            print("\n🎉 Kaikki testit onnistuivat! API-avain toimii.")
        else:
            print("\n⚠️  HTTP API toimii, mutta WebSocket-yhteys epäonnistui.")
    else:
        print("\n❌ API-avain ei toimi tai on virheellinen.")
