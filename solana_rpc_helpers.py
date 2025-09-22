import os
import aiohttp
from typing import Any, Dict

SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

async def rpc_get_tx(signature: str) -> Dict[str, Any]:
	payload = {
		"jsonrpc": "2.0",
		"id": 1,
		"method": "getTransaction",
		"params": [
			signature,
			{
				"encoding": "json",
				"commitment": "confirmed",
				"maxSupportedTransactionVersion": 0
			}
		]
	}
	timeout = aiohttp.ClientTimeout(total=6)
	async with aiohttp.ClientSession(timeout=timeout) as s:
		async with s.post(SOLANA_RPC_URL, json=payload) as r:
			r.raise_for_status()
			data = await r.json()
			return data.get("result") or {}