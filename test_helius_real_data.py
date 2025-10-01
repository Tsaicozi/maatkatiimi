#!/usr/bin/env python3
"""
Test script for HeliusLogsNewTokensSource with real Helius data
"""
import asyncio
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sources.helius_logs_newtokens import HeliusTransactionsNewTokensSource

HELIUS_WS = os.environ.get("HELIUS_WS_URL")
if not HELIUS_WS:
    api_key = os.environ.get("HELIUS_API_KEY")
    if not api_key:
        raise SystemExit("Aseta HELIUS_WS_URL tai HELIUS_API_KEY ympäristöön.")
    HELIUS_WS = f"wss://mainnet.helius-rpc.com/?api-key={api_key}"

async def test_real_helius_data():
    """Test with real Helius WebSocket data"""
    print(f"⏳ Yhdistetään {HELIUS_WS} ...")
    
    source = HeliusTransactionsNewTokensSource(HELIUS_WS, ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"])
    
    # Mock queue for testing
    class MockQueue:
        def __init__(self):
            self.tokens = []
        
        def put_nowait(self, token):
            self.tokens.append(token)
            print(f"🆕 Token löydetty: {token.mint[:8]}... ({token.symbol})")
            print(f"   Extraction method: {token.extra.get('extraction_method', 'unknown')}")
            print(f"   Signature: {token.extra.get('signature', 'unknown')[:8]}...")
    
    queue = MockQueue()
    
    # Start the source in a task
    task = asyncio.create_task(source.run(queue))
    
    try:
        # Let it run for 30 seconds
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        print("\n🛑 Keskeytetty käyttäjän toimesta")
    finally:
        await source.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    print(f"\n📊 Yhteensä löydetty {len(queue.tokens)} tokenia")
    
    # Analyze extraction methods
    methods = {}
    for token in queue.tokens:
        method = token.extra.get('extraction_method', 'unknown')
        methods[method] = methods.get(method, 0) + 1
    
    print("📈 Extraction methods:")
    for method, count in methods.items():
        print(f"   {method}: {count}")

if __name__ == "__main__":
    asyncio.run(test_real_helius_data())
