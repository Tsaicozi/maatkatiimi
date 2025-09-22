from __future__ import annotations

import os
import asyncio
from typing import Any, Dict, Optional
import aiohttp

from helius_token_scanner_bot import DexInfo


DEXSCREENER_BASE = os.getenv("DEXSCREENER_BASE", "https://api.dexscreener.com/latest/dex")
JUPITER_BASE = os.getenv("JUPITER_BASE", "https://quote-api.jup.ag/v6")
SOLSCAN_BASE = os.getenv("SOLSCAN_BASE", "https://public-api.solscan.io")
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")


async def _get_json(url: str, *, headers: Optional[Dict[str, str]] = None, timeout_sec: float = 5.0, tries: int = 2) -> Dict[str, Any]:
	last_exc: Exception | None = None
	backoff = 0.5
	for _ in range(max(1, tries)):
		try:
			timeout = aiohttp.ClientTimeout(total=timeout_sec)
			async with aiohttp.ClientSession(timeout=timeout) as s:
				async with s.get(url, headers=headers) as r:
					if r.status >= 400:
						raise aiohttp.ClientResponseError(r.request_info, r.history, status=r.status, message=await r.text())
					return await r.json(content_type=None)
		except Exception as e:
			last_exc = e
			await asyncio.sleep(backoff)
			backoff = min(3.0, backoff * 2)
	return {"__error__": str(last_exc) if last_exc else "unknown"}


async def fetch_from_dexscreener(mint: str) -> DexInfo:
	"""Query DexScreener by token mint and return best Solana pair by liquidity."""
	url = f"{DEXSCREENER_BASE}/tokens/{mint}"
	data = await _get_json(url, timeout_sec=5.0, tries=2)
	if "__error__" in data:
		return DexInfo(status="error", reason=f"dexscreener_http:{data['__error__']}")
	try:
		pairs = data.get("pairs") or []
		if not isinstance(pairs, list) or not pairs:
			return DexInfo(status="not_found", reason="dexscreener_no_pairs")
		# Filter for Solana and pick max liquidity.usd
		best = None
		best_liq = -1.0
		for p in pairs:
			if not isinstance(p, dict):
				continue
			chain = p.get("chainId") or p.get("chainId")
			if chain and str(chain).lower() != "solana":
				continue
			liquidity = (p.get("liquidity") or {}).get("usd")
			try:
				liq = float(liquidity or 0.0)
			except Exception:
				liq = 0.0
			if liq > best_liq:
				best_liq = liq
				best = p
		if not best:
			# fallback to first
			best = pairs[0]
		dex_id = best.get("dexId") or best.get("dexType") or "dexscreener"
		pair_addr = best.get("pairAddress") or best.get("url") or ""
		if pair_addr:
			return DexInfo(status="ok", dex_name=str(dex_id), pair_address=str(pair_addr), reason="dexscreener_ok")
		return DexInfo(status="not_found", reason="dexscreener_no_pair_address")
	except Exception as e:
		return DexInfo(status="error", reason=f"dexscreener_parse:{e}")


async def fetch_from_jupiter(mint: str) -> DexInfo:
	"""Use Jupiter quote API as a signal that token is tradable and extract market info if available."""
	# Attempt a small exact-in quote to SOL; amount is in base units. Use 1e6 which works for many tokens.
	SOL = "So11111111111111111111111111111111111111112"
	params = "inputMint={}&outputMint={}&amount={}&slippageBps=50&swapMode=ExactIn&onlyDirectRoutes=true".format(mint, SOL, 1_000_000)
	url = f"{JUPITER_BASE}/quote?{params}"
	data = await _get_json(url, timeout_sec=4.0, tries=2)
	if "__error__" in data:
		return DexInfo(status="error", reason=f"jupiter_http:{data['__error__']}")
	try:
		routes = data.get("data") or data.get("routes") or []
		if not routes:
			return DexInfo(status="not_found", reason="jupiter_no_routes")
		first = routes[0]
		# v6 provides marketInfos list; derive pair id / dex label
		infos = first.get("marketInfos") or first.get("routePlan") or []
		if not infos:
			return DexInfo(status="ok", dex_name="jupiter", pair_address=None, reason="jupiter_ok")
		info0 = infos[0] if isinstance(infos, list) else infos
		amm = info0.get("amm") if isinstance(info0, dict) else None
		label = (amm.get("label") if isinstance(amm, dict) else None) or info0.get("label") or "jupiter"
		market_id = info0.get("marketId") or info0.get("id") or info0.get("poolId")
		return DexInfo(status="ok", dex_name=str(label), pair_address=(str(market_id) if market_id else None), reason="jupiter_ok")
	except Exception as e:
		return DexInfo(status="error", reason=f"jupiter_parse:{e}")


async def fetch_from_solscan(mint: str) -> DexInfo:
	"""Use Solscan public API to verify token existence; may not provide a pair."""
	headers = {"accept": "application/json"}
	if SOLSCAN_API_KEY:
		headers["token"] = SOLSCAN_API_KEY
	url = f"{SOLSCAN_BASE}/token/meta?tokenAddress={mint}"
	data = await _get_json(url, headers=headers, timeout_sec=4.0, tries=2)
	if "__error__" in data:
		return DexInfo(status="error", reason=f"solscan_http:{data['__error__']}")
	try:
		# If meta exists and has symbol/name, consider ok (even if no pair)
		if data and (data.get("symbol") or data.get("name") or data.get("mintAuthority") is not None):
			return DexInfo(status="ok", dex_name="solscan", pair_address=None, reason="solscan_ok")
		return DexInfo(status="not_found", reason="solscan_no_meta")
	except Exception as e:
		return DexInfo(status="error", reason=f"solscan_parse:{e}")

