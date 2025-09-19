#!/usr/bin/env python3
"""
Testaa että CancelledError käsittely toimii oikein lähdeadaptereissa
"""

import asyncio
import contextlib
from sources.raydium_newpools import RaydiumNewPoolsSource

async def test_cancelled_error_handling():
    """Testaa että CancelledError kuplii ulos oikein"""
    print("🧪 Testataan CancelledError käsittelyä...")
    
    # Mock WebSocket client joka heittää CancelledError:in
    class MockWSClient:
        async def subscribe_new_pools(self):
            print("Mock: Tilattu new pools")
        
        async def unsubscribe_new_pools(self):
            print("Mock: Tilaus peruttu")
        
        async def listen(self):
            # Simuloi että WebSocket heittää CancelledError:in
            await asyncio.sleep(0.1)
            raise asyncio.CancelledError("WebSocket peruttu")
    
    # Luo source ja testaa
    ws_client = MockWSClient()
    source = RaydiumNewPoolsSource(ws_client)
    
    queue = asyncio.Queue()
    
    try:
        await source.start()
        
        # Aja source ja odota että se heittää CancelledError:in
        task = asyncio.create_task(source.run(queue))
        
        # Odota että task päättyy
        try:
            await task
            print("❌ Task ei heittänyt CancelledError:ia")
        except asyncio.CancelledError:
            print("✅ CancelledError kuplii ulos oikein")
        
        # Tarkista että task on todella päättynyt
        if task.done():
            print("✅ Task päättyi oikein")
        else:
            print("❌ Task ei päättynyt")
            
    except Exception as e:
        print(f"❌ Odottamaton virhe: {e}")
    finally:
        await source.stop()
    
    print("🎉 CancelledError testi valmis!")

if __name__ == "__main__":
    asyncio.run(test_cancelled_error_handling())


