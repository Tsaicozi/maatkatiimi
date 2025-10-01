#!/usr/bin/env python3
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

PROGRAMS = [
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
]

async def main():
    print(f"⏳ Yhdistetään {HELIUS_WS} ...")
    async with websockets.connect(HELIUS_WS) as ws:
        for program in PROGRAMS:
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": [program]},
                    {"commitment": "confirmed"},
                ],
            }
            await ws.send(json.dumps(subscribe_msg))
            print(f"➡️ Lähetetty subscribe {program[:8]}...")

        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            print("📥", json.dumps(data, indent=2))

asyncio.run(main())
