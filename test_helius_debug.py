#!/usr/bin/env python3
"""
Debug script to see what Helius actually sends
"""
import asyncio
import json
import os
import websockets

HELIUS_WS = os.environ.get("HELIUS_WS_URL")
if not HELIUS_WS:
    api_key = os.environ.get("HELIUS_API_KEY")
    if not api_key:
        raise SystemExit("Aseta HELIUS_WS_URL tai HELIUS_API_KEY ympäristöön.")
    HELIUS_WS = f"wss://mainnet.helius-rpc.com/?api-key={api_key}"

async def debug_helius_data():
    """Debug what Helius actually sends"""
    print(f"⏳ Yhdistetään {HELIUS_WS} ...")
    
    try:
        async with websockets.connect(HELIUS_WS) as ws:
            # Subscribe to Tokenkeg program logs
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"]},
                    {"commitment": "confirmed"},
                ],
            }
            await ws.send(json.dumps(subscribe_msg))
            print("✅ Tilaus lähetetty")
            
            message_count = 0
            while message_count < 10:  # Limit to 10 messages
                message = await ws.recv()
                try:
                    event = json.loads(message)
                    
                    # Handle subscription confirmation
                    if "result" in event and isinstance(event["result"], str):
                        print(f"✅ Tilaus vahvistettu: {event['result'][:8]}...")
                        continue
                    
                    # Handle log notifications
                    if "params" in event and "result" in event["params"]:
                        log_data = event["params"]["result"]
                        if "value" in log_data:
                            value = log_data["value"]
                            print(f"\n📥 Message {message_count + 1}:")
                            print(f"   Signature: {value.get('signature', 'N/A')[:8]}...")
                            print(f"   Accounts: {value.get('accounts', [])}")
                            print(f"   Mentions: {value.get('mentions', [])}")
                            print(f"   Logs: {value.get('logs', [])[:3]}...")  # First 3 logs
                            
                            # Check if this looks like a new token
                            logs = value.get("logs", [])
                            if any("InitializeMint" in log for log in logs):
                                print("   🆕 Tämä näyttää uuden tokenin luomiselta!")
                            
                            message_count += 1
                            
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                    continue
                except Exception as e:
                    print(f"Message processing error: {e}")
                    continue
                    
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_helius_data())
