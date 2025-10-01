from __future__ import annotations

import os
import time
import asyncio
from typing import Any, Dict, Optional
import aiohttp

from helius_token_scanner_bot import DexInfo
from dotenv import load_dotenv

load_dotenv()


DEXSCREENER_BASE = os.getenv("DEXSCREENER_BASE", "https://api.dexscreener.com/latest/dex")
JUPITER_BASE = os.getenv("JUPITER_BASE", "https://quote-api.jup.ag/v6")
SOLSCAN_BASE = os.getenv("SOLSCAN_BASE", "https://public-api.solscan.io")
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")
COINGECKO_BASE = os.getenv("COINGECKO_BASE", "https://pro-api.coingecko.com/api/v3")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY") or os.getenv("COINGECKO_PRO_KEY") or os.getenv("COINGECKO_PRO_API_KEY")
BIRDEYE_BASE = os.getenv("BIRDEYE_BASE", "https://public-api.birdeye.so")
def get_birdeye_api_key():
    """Get Birdeye API key dynamically to allow for runtime updates"""
    # Force reload environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    key = (
        os.getenv("BIRDEYE_API_KEY")
        or os.getenv("BIRDEYE_PRO_KEY")
        or os.getenv("BIRDEYE_KEY")
    )
    return key

BIRDEYE_API_KEY = get_birdeye_api_key()


def _safe_float(*values: Any) -> Optional[float]:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


async def _get_json(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout_sec: float = 8.0,
    tries: int = 4,
) -> Dict[str, Any]:
    last_exc: Exception | None = None
    backoff = 0.5
    for _ in range(max(1, tries)):
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_sec)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status >= 400:
                        raise aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=response.status,
                            message=await response.text(),
                        )
                    return await response.json(content_type=None)
        except Exception as exc:
            last_exc = exc
            await asyncio.sleep(backoff)
            backoff = min(3.0, backoff * 2)
    return {"__error__": str(last_exc) if last_exc else "unknown"}


async def fetch_birdeye_price(mint: str) -> Optional[float]:
    """Fetch current price from Birdeye for a specific mint"""
    api_key = get_birdeye_api_key()
    if not api_key:
        return None
    
    headers = {
        "accept": "application/json",
        "x-api-key": api_key,
    }
    
    overview_url = f"{BIRDEYE_BASE.rstrip('/')}/defi/token_overview?address={mint}"
    try:
        data = await _get_json(overview_url, headers=headers, timeout_sec=8.0, tries=3)
        
        if "__error__" in data:
            return None
        
        payload = data.get("data") or {}
        if not isinstance(payload, dict) or not payload:
            return None
        
        price = _safe_float(payload.get("price"))
        return price
        
    except Exception:
        return None

async def fetch_from_birdeye(mint: str) -> DexInfo:
    """Fetch market metrics from Birdeye Pro token overview endpoint."""
    api_key = get_birdeye_api_key()
    if not api_key:
        return DexInfo(status="error", reason="birdeye_api_key_missing")

    headers = {
        "accept": "application/json",
        "x-api-key": api_key,
    }

    overview_url = f"{BIRDEYE_BASE.rstrip('/')}/defi/token_overview?address={mint}"
    data = await _get_json(overview_url, headers=headers, timeout_sec=8.0, tries=3)
    if "__error__" in data:
        return DexInfo(status="error", reason=f"birdeye_http:{data['__error__']}")

    payload = data.get("data") or {}
    if not isinstance(payload, dict) or not payload:
        return DexInfo(status="not_found", reason="birdeye_no_data")

    metadata: Dict[str, Any] = {}

    liquidity = _safe_float(
        payload.get("liquidity"),
        payload.get("liquidityUsd"),
        payload.get("liquidityUSD"),
    )
    if liquidity is not None:
        metadata["liquidity_usd"] = liquidity

    volume = _safe_float(
        payload.get("volume24h"),
        payload.get("volume24hUsd"),
        payload.get("volume24hUSD"),
        payload.get("v24hUSD"),
    )
    if volume is not None:
        metadata["volume_24h_usd"] = volume

    price = _safe_float(payload.get("price"))
    if price is not None:
        metadata["price_usd"] = price

    fdv = _safe_float(payload.get("fdv"), payload.get("fullyDilutedValuation"))
    if fdv is not None:
        metadata["fdv"] = fdv

    market_cap = _safe_float(payload.get("marketCap"), payload.get("mc"))
    if market_cap is not None:
        metadata["market_cap"] = market_cap

    holders = payload.get("holders") or payload.get("holder")
    if holders is not None:
        try:
            metadata["holders"] = int(holders)
        except (TypeError, ValueError):
            metadata["holders_raw"] = holders

    buyers30 = (
        payload.get("buyers30m")
        or payload.get("buyers_30m")
        or payload.get("uniqueBuyers30m")
        or payload.get("txnBuyerCount30m")
    )
    if buyers30 is not None:
        try:
            metadata["buyers_30m"] = int(buyers30)
        except (TypeError, ValueError):
            metadata["buyers_30m_raw"] = buyers30

    price_change: Dict[str, Any] = {}
    for key, fields in {
        "m5": ("priceChange5mPercent", "priceChange5m"),
        "h1": ("priceChange1hPercent", "priceChange1h"),
        "h6": ("priceChange6hPercent", "priceChange6h"),
        "h24": ("priceChange24hPercent", "priceChange24h"),
    }.items():
        for field in fields:
            value = _safe_float(payload.get(field))
            if value is not None:
                price_change[key] = value
                break
    if price_change:
        metadata["price_change"] = price_change

    pair_created = payload.get("createdAt") or payload.get("createdTime") or payload.get("launchTime")
    if pair_created is not None:
        ts = _safe_float(pair_created)
        if ts is not None:
            metadata["pair_created_at"] = ts if ts > 1e12 else ts * 1000
        else:
            metadata["pair_created_at_raw"] = pair_created

    pools = payload.get("topMarkets") or payload.get("markets") or payload.get("pairs") or []
    alt_pairs: list[str] = []
    pair_address: Optional[str] = None
    dex_name = payload.get("dexId") or payload.get("dexName") or "birdeye"

    if isinstance(pools, list):
        sorted_pools = sorted(
            (p for p in pools if isinstance(p, dict)),
            key=lambda p: _safe_float(p.get("liquidity"), p.get("liquidityUsd"), p.get("liquidityUSD"))
            or 0.0,
            reverse=True,
        )
        for idx, pool in enumerate(sorted_pools):
            addr = (
                pool.get("pairAddress")
                or pool.get("address")
                or pool.get("poolAddress")
                or pool.get("lpAddress")
            )
            if addr:
                addr_str = str(addr)
                if pair_address is None:
                    pair_address = addr_str
                alt_pairs.append(addr_str)
            if idx == 0:
                dex_candidate = pool.get("dex") or pool.get("dexId") or pool.get("marketName")
                if dex_candidate:
                    dex_name = str(dex_candidate)
                if "pair_created_at" not in metadata:
                    created = pool.get("createdAt") or pool.get("createdTime")
                    ts = _safe_float(created)
                    if ts is not None:
                        metadata["pair_created_at"] = ts if ts > 1e12 else ts * 1000
                    elif created is not None:
                        metadata["pair_created_at_raw"] = created
                if liquidity is None:
                    pool_liq = _safe_float(pool.get("liquidity"), pool.get("liquidityUsd"), pool.get("liquidityUSD"))
                    if pool_liq is not None:
                        metadata["liquidity_usd"] = pool_liq
                if volume is None:
                    pool_vol = _safe_float(
                        pool.get("volume24h"),
                        pool.get("volume24hUsd"),
                        pool.get("volume24hUSD"),
                        pool.get("v24hUSD"),
                    )
                    if pool_vol is not None:
                        metadata["volume_24h_usd"] = pool_vol
                if "buyers_30m" not in metadata:
                    pool_buyers = (
                        pool.get("buyers30m")
                        or pool.get("buyers")
                        or pool.get("txnBuyers30m")
                    )
                    pool_buyers_val = _safe_float(pool_buyers)
                    if pool_buyers_val is not None:
                        metadata["buyers_30m"] = int(pool_buyers_val)
                pool_trades = pool.get("txn24h") or pool.get("trades24h") or pool.get("txns24h")
                trades_val = _safe_float(pool_trades)
                if trades_val is not None:
                    metadata["trades_24h"] = int(trades_val)
                if pool.get("lastTradeTime") or pool.get("lastTrade"):
                    last_trade_val = _safe_float(
                        pool.get("lastTradeTime"),
                        pool.get("lastTrade"),
                        pool.get("lastTradeUnix"),
                    )
                    if last_trade_val is not None:
                        ts = last_trade_val
                        if ts > 1e12:
                            ts /= 1000.0
                        metadata["last_trade_minutes"] = max(0.0, (time.time() - ts) / 60.0)
                if pool.get("url") and "pair_url" not in metadata:
                    metadata["pair_url"] = pool.get("url")
            if idx >= 4:
                break

    if pair_address and pair_address in alt_pairs:
        alt_pairs = [p for p in alt_pairs if p != pair_address]

    if pair_address is None:
        fallback_addr = (
            payload.get("pairAddress")
            or payload.get("poolAddress")
            or payload.get("lpAddress")
            or payload.get("address")
        )
        if fallback_addr:
            pair_address = str(fallback_addr)
            alt_pairs = [p for p in alt_pairs if p != pair_address]
        elif alt_pairs:
            pair_address = alt_pairs[0]
            alt_pairs = alt_pairs[1:]

    return DexInfo(
        status="ok",
        dex_name=str(dex_name or "birdeye"),
        pair_address=pair_address,
        reason="birdeye_ok",
        alt_pairs=alt_pairs,
        metadata=metadata,
    )


async def fetch_from_dexscreener(mint: str) -> DexInfo:
	"""Query DexScreener by token mint and return best Solana pair by liquidity.

	Primary endpoint: /latest/dex/tokens/{mint}
	Fallback:        /latest/dex/search?q={mint} (when 404 or pairs are empty)
	"""
	url = f"{DEXSCREENER_BASE}/tokens/{mint}"
	data = await _get_json(url, timeout_sec=6.0, tries=2)  # Vähennä timeout ja retry-määrää
	
	# Check for 404 or other errors - fallback to search
	if "__error__" in data or (isinstance(data, dict) and not data.get("pairs")):
		# Try search endpoint as fallback
		search_url = f"{DEXSCREENER_BASE}/search?q={mint}"
		data_search = await _get_json(search_url, timeout_sec=6.0, tries=2)
		if "__error__" not in data_search:
			spairs = data_search.get("pairs") or []
			# Heuristiikka: poimi Solana-parit, joissa baseToken.address == mint
			candidates = []
			for p in spairs if isinstance(spairs, list) else []:
				if not isinstance(p, dict):
					continue
				chain = p.get("chainId")
				if chain and str(chain).lower() != "solana":
					continue
				base = p.get("baseToken") or {}
				if isinstance(base, dict) and (str(base.get("address") or "").strip() == mint):
					candidates.append(p)
			# Jos löytyi kandidaatteja, käytä niitä jatkoparsinnassa
			if candidates:
				data = {"pairs": candidates}
			else:
				# Return empty result instead of error - let Birdeye data be used
				return DexInfo(status="not_found", reason="dexscreener_no_pairs_fallback")
		else:
			# Both endpoints failed - return empty result instead of error
			return DexInfo(status="not_found", reason="dexscreener_both_endpoints_failed")
	
	try:
		tpairs = data.get("pairs") or []
		# Additional fallback to search if token endpoint returns empty/null pairs
		if not isinstance(tpairs, list) or not tpairs:
			search_url = f"{DEXSCREENER_BASE}/search?q={mint}"
			data_search = await _get_json(search_url, timeout_sec=6.0, tries=2)
			if "__error__" not in data_search:
				spairs = data_search.get("pairs") or []
				# Heuristiikka: poimi Solana-parit, joissa baseToken.address == mint
				candidates = []
				for p in spairs if isinstance(spairs, list) else []:
					if not isinstance(p, dict):
						continue
					chain = p.get("chainId")
					if chain and str(chain).lower() != "solana":
						continue
					base = p.get("baseToken") or {}
					if isinstance(base, dict) and (str(base.get("address") or "").strip() == mint):
						candidates.append(p)
				# Jos löytyi kandidaatteja, käytä niitä jatkoparsinnassa
				if candidates:
					tpairs = candidates
			if not isinstance(tpairs, list) or not tpairs:
				return DexInfo(status="not_found", reason="dexscreener_no_pairs")
		# Filter for Solana and pick max liquidity.usd
		best = None
		best_liq = -1.0
		alt_pairs: list[str] = []
		low_activity = False
		for p in tpairs:
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
			txns = (p.get("txns") or {}).get("m5") or {}
			buys = int(txns.get("buys") or 0)
			sells = int(txns.get("sells") or 0)
			trades5m = buys + sells
			buyers5m = int(txns.get("buyers") or txns.get("uniqueBuyers") or 0)
			if not buyers5m:
				buyers5m = int((p.get("buyers") or {}).get("m5") if isinstance(p.get("buyers"), dict) else (p.get("buyers") or 0))
			# Alenna kynnyksiä uusille tokeneille
			if trades5m < 1 or buyers5m < 1:
				low_activity = True
				continue
			pair_addr = p.get("pairAddress") or p.get("url") or ""
			if pair_addr:
				alt_pairs.append(str(pair_addr))
			if liq > best_liq:
				best_liq = liq
				best = p
		if not best:
			if low_activity:
				return DexInfo(status="not_found", reason="dexscreener_low_activity")
			# fallback to first
			best = tpairs[0]
			try:
				best_liq = float(((best.get("liquidity") or {}).get("usd")) or 0.0)
			except Exception:
				best_liq = 0.0
			dex_id = best.get("dexId") or best.get("dexType") or "dexscreener"
			pair_addr = best.get("pairAddress") or best.get("url") or ""
			if pair_addr and pair_addr in alt_pairs:
				alt_pairs.remove(pair_addr)
			metadata: Dict[str, Any] = {}
			price = best.get("priceUsd") or best.get("priceNative")
			if price is not None:
				try:
					metadata["price_usd"] = float(price)
				except Exception:
					metadata["price_usd_raw"] = price
			fdv = (
				best.get("fdv")
				or best.get("fullyDilutedValuation")
				or (best.get("marketCap") or {}).get("fdv")
			)
			base_token = best.get("baseToken") if isinstance(best.get("baseToken"), dict) else {}
			if isinstance(base_token, dict) and base_token.get("decimals") is not None:
				metadata["decimals"] = base_token.get("decimals")
			supply = base_token.get("supply") or base_token.get("totalSupply")
			# Tallenna symboli ja nimi mikäli saatavilla
			bsym = base_token.get("symbol")
			bname = base_token.get("name")
			if isinstance(bsym, str) and bsym:
				metadata["resolved_symbol"] = bsym.strip().upper()
				metadata["base_symbol"] = bsym
			if isinstance(bname, str) and bname:
				metadata["base_name"] = bname
			if fdv is not None:
				try:
					metadata["fdv"] = float(fdv)
				except Exception:
					metadata["fdv_raw"] = fdv
			if not supply and fdv:
				metadata["fdv_note"] = "fdv: n/a (supply missing)"
			elif supply:
				metadata["supply"] = supply
			if best_liq is not None:
				metadata["liquidity_usd"] = best_liq
			volume_payload = best.get("volume") or {}
			volume_24h = volume_payload.get("h24") or volume_payload.get("hour24")
			try:
				if volume_24h is not None:
					metadata["volume_24h_usd"] = float(volume_24h)
			except Exception:
				metadata["volume_24h_raw"] = volume_24h
			buyers_payload = best.get("buyers")
			buyers_30m = None
			if isinstance(buyers_payload, dict):
				buyers_30m = buyers_payload.get("m30") or buyers_payload.get("m15") or buyers_payload.get("h1")
			elif buyers_payload is not None:
				buyers_30m = buyers_payload
			if buyers_30m is not None:
				try:
					metadata["buyers_30m"] = int(buyers_30m)
				except Exception:
					metadata["buyers_30m_raw"] = buyers_30m
			pair_created_at = best.get("pairCreatedAt") or best.get("pairCreatedAtMs") or best.get("createdAt")
			try:
				if pair_created_at:
					ts = float(pair_created_at)
					if ts > 1e12:
						ts /= 1000.0
					metadata["pair_created_at"] = ts
			except Exception:
				metadata["pair_created_at_raw"] = pair_created_at
			price_change = best.get("priceChange")
			if isinstance(price_change, dict):
				metadata["price_change"] = {
					"m5": price_change.get("m5"),
					"h1": price_change.get("h1"),
					"h6": price_change.get("h6"),
					"h24": price_change.get("h24"),
				}

			txns_payload = best.get("txns") or {}
			txns_h24 = txns_payload.get("h24") or {}
			trades_24h = txns_h24.get("txns") or txns_h24.get("count")
			try:
				if trades_24h is not None:
					metadata["trades_24h"] = int(trades_24h)
			except Exception:
				metadata["trades_24h_raw"] = trades_24h

			last_trade_ms = (
				best.get("updatedAt")
				or best.get("lastTradeAt")
				or best.get("lastTrade")
			)
			try:
				if last_trade_ms:
					ts = float(last_trade_ms)
					if ts > 1e12:
						ts /= 1000.0
					metadata["last_trade_minutes"] = max(0.0, (time.time() - ts) / 60.0)
			except Exception:
				metadata["last_trade_minutes_raw"] = last_trade_ms

			if best.get("url"):
				metadata["pair_url"] = best.get("url")
			if pair_addr:
				return DexInfo(
					status="ok",
					dex_name=str(dex_id),
					pair_address=str(pair_addr),
					reason="dexscreener_ok",
					alt_pairs=alt_pairs,
					metadata=metadata,
				)
		return DexInfo(status="not_found", reason="dexscreener_no_pair_address")
	except Exception as e:
		return DexInfo(status="error", reason=f"dexscreener_parse:{e}")


async def fetch_from_jupiter(mint: str) -> DexInfo:
	"""Use Jupiter quote API as a signal that token is tradable and extract market info if available."""
	# Attempt a small exact-in quote to SOL; amount is in base units. Use 1e6 which works for many tokens.
	SOL = "So11111111111111111111111111111111111111112"
	params = "inputMint={}&outputMint={}&amount={}&slippageBps=50&swapMode=ExactIn&onlyDirectRoutes=true".format(mint, SOL, 1_000_000)
	url = f"{JUPITER_BASE}/quote?{params}"
	data = await _get_json(url, timeout_sec=6.0, tries=2)  # Vähennä retry-määrää
	if "__error__" in data:
		error_msg = data['__error__']
		# Tarkista onko kyse "TOKEN_NOT_TRADABLE" virheestä
		if "TOKEN_NOT_TRADABLE" in str(error_msg) or "not tradable" in str(error_msg).lower():
			return DexInfo(status="not_found", reason="jupiter_token_not_tradable")
		return DexInfo(status="error", reason=f"jupiter_http:{error_msg}")
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
	# Solscan public API ei vaadi API-avainta
	url = f"{SOLSCAN_BASE}/token/meta?tokenAddress={mint}"
	data = await _get_json(url, headers=headers, timeout_sec=6.0, tries=4)
	if "__error__" in data:
		return DexInfo(status="error", reason=f"solscan_http:{data['__error__']}")
	try:
		# If meta exists and has symbol/name, consider ok (even if no pair)
		if data and (data.get("symbol") or data.get("name") or data.get("mintAuthority") is not None):
			return DexInfo(status="ok", dex_name="solscan", pair_address=None, reason="solscan_ok")
		return DexInfo(status="not_found", reason="solscan_no_meta")
	except Exception as e:
		return DexInfo(status="error", reason=f"solscan_parse:{e}")


async def fetch_from_coingecko(mint: str) -> DexInfo:
	"""Hae CoinGecko Pro API:sta token metadata ja markkinadata."""
	if not COINGECKO_API_KEY:
		return DexInfo(status="error", reason="coingecko_api_key_missing")
	headers = {
		"accept": "application/json",
		"x-cg-pro-api-key": COINGECKO_API_KEY,
	}
	url = f"{COINGECKO_BASE}/coins/solana/contract/{mint}"
	data = await _get_json(url, headers=headers, timeout_sec=8.0, tries=3)
	if "__error__" in data:
		return DexInfo(status="error", reason=f"coingecko_http:{data['__error__']}")
	try:
		if not data or data.get("error"):
			msg = data.get("error") if isinstance(data, dict) else "coingecko_empty"
			return DexInfo(status="not_found", reason=str(msg))
		name = data.get("name") or "coingecko"
		market_data = data.get("market_data") or {}
		liq = market_data.get("total_value_locked") or market_data.get("total_volume", {}).get("usd")
		if liq:
			try:
				liq_val = float(liq)
			except Exception:
				liq_val = None
		else:
			liq_val = None
		reason = "coingecko_ok"
		if liq_val is not None:
			reason += f"_tvl:{liq_val:.0f}"
		return DexInfo(status="ok", dex_name=str(name), pair_address=None, reason=reason)
	except Exception as e:
		return DexInfo(status="error", reason=f"coingecko_parse:{e}")
