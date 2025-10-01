#!/usr/bin/env python3
"""
Testaa antamasi Helius WebSocket-osoite
"""
import asyncio
import websockets
import json

async def test_helius_ws():
    ws_url = "wss://mainnet.helius-rpc.com/?api-key=e0da0308-2f9b-43aa-bb8f-84d7deab8b2d"
    
    print(f"🔍 Testataan WebSocket: {ws_url[:60]}...")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket-yhteys onnistui!")
            
            # Testaa getHealth
            health_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getHealth"
            })
            
            await websocket.send(health_msg)
            response = await websocket.recv()
            print(f"📡 getHealth vastaus: {response}")
            
            # Testaa transactionSubscribe
            subscribe_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "transactionSubscribe",
                "params": [
                    {"commitment": "confirmed"},
                    {
                        "commitment": "confirmed",
                        "encoding": "json",
                        "transactionDetails": "full",
                        "showRewards": False,
                        "maxSupportedTransactionVersion": 0
                    }
                ]
            })
            
            await websocket.send(subscribe_msg)
            subscribe_response = await websocket.recv()
            print(f"📡 transactionSubscribe vastaus: {subscribe_response}")
            
            print("🎉 WebSocket toimii täydellisesti!")
            return True
            
    except Exception as e:
        print(f"❌ WebSocket-yhteys epäonnistui: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_helius_ws())
    if result:
        print("\n✅ Voit käynnistää botin - WebSocket-yhteys toimii!")
    else:
        print("\n❌ WebSocket-yhteys ei toimi - tarkista API-avain.")

