#!/usr/bin/env python3
"""
Mock PumpPortal serveri kehitykseen
Palvelee /recent endpointia mock-datalla
"""

import asyncio
import json
import time
import random
import string
from aiohttp import web

async def recent(request):
    """Palauta mock token-dataa"""
    limit = int(request.query.get("limit", "50"))
    now = time.time()
    items = []
    
    for i in range(limit):
        mint = "Mock" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        items.append({
            "mint": mint,
            "symbol": f"MOCK{i}",
            "name": f"Mock Token {i}",
            "poolAddress": f"Pool{i}",
            "firstTradeAt": now - random.randint(5, 600),  # 5s - 10min sitten
            "liquidityUsd": random.uniform(1200, 25000),
            "top10Share": random.uniform(0.1, 0.9)
        })
    
    return web.json_response(items)

def main():
    """Käynnistä mock-serveri"""
    app = web.Application()
    app.router.add_get("/recent", recent)
    
    print("🚀 Mock PumpPortal serveri käynnistyy...")
    print("📍 Endpoint: http://127.0.0.1:9999/recent")
    print("⏹️  Lopeta: Ctrl+C")
    
    web.run_app(app, host="127.0.0.1", port=9999)

if __name__ == "__main__":
    main()
