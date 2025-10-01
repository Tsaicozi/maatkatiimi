import asyncio
import json
import logging
from typing import Callable, Dict, Any, Iterable, Optional, Set
import aiohttp
import time

class RaydiumPoolWatcher:
    """
    Kuuntelee Helius/Solana WS:ää Raydium-ohjelmien logeille (logsSubscribe mentions=programId)
    ja emittoi uusia poolikandidaatteja (pair-first).
    Heuristiikat:
      - tunnista poolin luonnit/ensimmäiset LP-lisäykset (Initialize/CreatePool/Deposit/AddLiquidity)
      - poimi base/quote mint -muodot yleisimmistä lokirakenteista (fallback: None)
      - arvioi quote-symboli (USDC/USDT/SOL) tunnetuista minteistä ja suodata allowlistillä
    """
    def __init__(
        self,
        ws_url: str,
        program_ids: Iterable[str],
        on_pair: Callable[[str, Dict[str, Any]], None],
        quote_allowlist: Optional[Set[str]] = None,
        min_quote_usd: float = 0.0,
    ) -> None:
        self.ws_url = ws_url
        self.program_ids = [p for p in program_ids if p]
        self.on_pair = on_pair
        self.quote_allowlist = quote_allowlist or set()
        self.min_quote_usd = float(min_quote_usd or 0.0)
        self.log = logging.getLogger(__name__)
        self._seen_mints: Set[str] = set()
        # Tunnetut quote-mintit (Solana)
        self._QUOTES = {
            # mint -> (symbol, decimals)
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": ("USDC", 6),
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": ("USDT", 6),
            "So11111111111111111111111111111111111111112": ("SOL", 9),  # wSOL
        }
        # Live pricing cache
        self._live_prices: Dict[str, Dict[str, Any]] = {}

    async def run_forever(self) -> None:
        """
        Avaa WS-yhteyden ja tekee logsSubscribe-kyselyt joka programId:lle (mentions-suodatin).
        Pitää reconnect-loopin päällä.
        """
        sub_ids = []
        while True:
            try:
                async with aiohttp.ClientSession() as sess:
                    async with sess.ws_connect(self.ws_url, heartbeat=20) as ws:
                        self.log.info("RaydiumPoolWatcher: connected")
                        # Tilaa logit jokaiselle ohjelmalle
                        req_id = 1
                        for pid in self.program_ids:
                            sub = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "method": "logsSubscribe",
                                "params": [
                                    {"mentions": [pid]},
                                    {"commitment": "confirmed", "filter": {"until": "all"}},
                                ],
                            }
                            await ws.send_str(json.dumps(sub))
                            req_id += 1
                        # Pumppaa viestejä
                        async for msg in ws:
                            if msg.type != aiohttp.WSMsgType.TEXT:
                                continue
                            try:
                                data = json.loads(msg.data)
                            except Exception:
                                continue
                            # logs-notifikaatio?
                            if "method" in data and data.get("method") == "logsNotification":
                                self._handle_logs_notif(data.get("params", {}))
            except Exception as e:
                self.log.warning("RaydiumPoolWatcher reconnect after error: %s", e)
                await asyncio.sleep(3.0)

    def _handle_logs_notif(self, params: Dict[str, Any]) -> None:
        """
        Parsitaan logsNotification -> etsitään "pool events".
        Helius lisää usein parsed-instructions / log-strings — käytämme molempia heuristisesti.
        """
        try:
            value = params.get("result", {})
            sig = (value.get("signature") or "").strip()
            logs = value.get("logs") or []
            # crude hint check
            text = " ".join(logs).lower()
            pool_hint = any(k in text for k in (
                "initializepool", "initialize_pool", "createpool", "create_pool",
                "addliquidity", "add_liquidity", "deposit"
            ))
            if not pool_hint:
                return
            # Yritä poimia minttejä accounts-kentistä jos saatavilla
            # Heliuksen notificationissa on usein "accounts" ja "programId", mutta schema vaihtelee —
            # tehdään best-effort:
            acct_mints = self._extract_mints_from_logs(text)
            base_mint, quote_mint = acct_mints.get("base"), acct_mints.get("quote")
            quote_sym = None
            if quote_mint in self._QUOTES:
                quote_sym = self._QUOTES[quote_mint][0]
            # Suodata quote-allowlistilla jos sellainen on
            if self.quote_allowlist and (quote_sym or "").upper() not in self.quote_allowlist:
                return
            # Jos ei tiedetä kumpi on base/quote, yritetään vähintään löytää "uusi mint"
            # Heuristiikka: jos toinen on tunnettu quote → toinen on base
            candidate_mint = None
            if quote_mint and base_mint and quote_mint in self._QUOTES:
                candidate_mint = base_mint
            else:
                # fallback: etsi "unknown" mint merkkijonoista
                unknowns = [m for m in acct_mints.values() if m and m not in self._QUOTES]
                candidate_mint = (unknowns[0] if unknowns else None)
            if not candidate_mint:
                return
            if candidate_mint in self._seen_mints:
                return
            self._seen_mints.add(candidate_mint)

            # Calculate live pricing if we have pool data
            live_pricing = self._calculate_live_pricing(base_mint, quote_mint, logs)
            
            meta = {
                "raydium": {
                    "signature": sig,
                    "quote": quote_sym,
                    "base_mint": base_mint,
                    "quote_mint": quote_mint,
                    "ts": int(time.time()),
                    "program_hit": True,
                    "logs_excerpt": logs[:5],  # debug
                    **live_pricing  # Add live pricing data
                }
            }
            # emit
            self.on_pair(candidate_mint, meta)
        except Exception as e:
            self.log.debug("parse logs failed: %s", e)

    def _calculate_live_pricing(self, base_mint: str, quote_mint: str, logs: list) -> Dict[str, Any]:
        """Calculate live pricing from Raydium pool logs"""
        try:
            # Try to extract reserve data from logs
            reserve_base = None
            reserve_quote = None
            
            for log in logs:
                # Look for reserve patterns in logs
                if "reserve" in log.lower():
                    # Try to extract numeric values
                    import re
                    numbers = re.findall(r'\d+\.?\d*', log)
                    if len(numbers) >= 2:
                        try:
                            reserve_base = float(numbers[0])
                            reserve_quote = float(numbers[1])
                            break
                        except ValueError:
                            continue
            
            if reserve_base and reserve_quote and reserve_base > 0:
                # Calculate price (quote per base)
                price = reserve_quote / reserve_base
                
                # Calculate liquidity USD (2 * min(reserve_quote, reserve_base * price))
                # For now, assume quote is USD-pegged
                liquidity_usd = 2.0 * min(reserve_quote, reserve_base * price)
                
                return {
                    "live_price": price,
                    "live_liquidity_usd": liquidity_usd,
                    "reserve_base": reserve_base,
                    "reserve_quote": reserve_quote,
                    "dex_status": "raydium_live"
                }
            
        except Exception as e:
            self.log.debug(f"Live pricing calculation failed: {e}")
        
        return {
            "dex_status": "raydium_pending"
        }

    def _extract_mints_from_logs(self, text: str) -> Dict[str, str]:
        """
        Best-effort mint-etsintä Raydiumin logeista:
          - etsii tunnetut quote-mintit
          - ottaa ensimmäisen muun 32-44 merkkiä pitkän base58-näköisen merkkijonon baseksi
        Tämä on tahallaan robusti (logiformaatti elää). Täydentyy rikastajissa myöhemmin.
        """
        import re
        out = {"base": None, "quote": None}
        # etsi mint-osoitteita (base58 suppea heuristiikka)
        candidates = re.findall(r"[1-9A-HJ-NP-Za-km-z]{32,44}", text)
        # map quote
        for c in candidates:
            if c in self._QUOTES:
                out["quote"] = c
                break
        # base = eka joka ei ole quote-listassa
        for c in candidates:
            if c != out.get("quote"):
                out["base"] = c
                break
        return out
