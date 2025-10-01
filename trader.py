import aiohttp, asyncio, base64, os, time, logging
from typing import Optional, Dict, Any
from solders.keypair import Keypair
from solders.message import to_bytes_versioned
from solders.transaction import VersionedTransaction
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Confirmed

JUP_BASE = "http://172.67.196.212"  # Jupiter API IP-osoite HTTP:llä (DNS-ongelman kierto)

class Trader:
    def __init__(self, http_rpc_url: str, cfg, logger: Optional[logging.Logger] = None):
        self.http = http_rpc_url
        self.cfg = cfg
        self.log = logger or logging.getLogger(__name__)
        # Lompakko (varmista turvallinen lataus!)
        sk = os.getenv("TRADER_PRIVATE_KEY_B58", "").strip()
        if not sk and os.getenv("TRADER_PRIVATE_KEY_HEX"):
            # salli myös hex
            sk = os.getenv("TRADER_PRIVATE_KEY_HEX").strip()
            try:
                secret = bytes.fromhex(sk)
                self.kp = Keypair.from_bytes(secret)
            except ValueError:
                self.log.warning("Invalid hex private key format")
                self.kp = None
        elif sk:
            try:
                import base58
                secret = base58.b58decode(sk)
                self.kp = Keypair.from_bytes(secret)
            except Exception as e:
                self.log.warning(f"Invalid base58 private key format: {e}")
                self.kp = None
        else:
            # Dry-run sallitaan ilman avainta
            self.kp = None

    async def _sol_client(self):
        return AsyncClient(self.http, commitment=Confirmed)
    
    async def get_sol_balance(self) -> float:
        """Get wallet SOL balance in lamports, return as SOL (float)"""
        if not self.kp:
            return 0.0
        try:
            async with await self._sol_client() as c:
                resp = await c.get_balance(self.kp.pubkey())
                lamports = resp.value if resp and hasattr(resp, 'value') else 0
                return lamports / 1e9  # Convert lamports to SOL
        except Exception as e:
            self.log.error(f"Failed to get SOL balance: {e}")
            return 0.0

    async def _jup_quote(self, input_mint: str, output_mint: str, amount: int, swap_mode="ExactIn") -> Optional[Dict]:
        p = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(self.cfg.slippage_bps),
            "onlyDirectRoutes": "false",
            "swapMode": swap_mode,
            "asLegacyTransaction": "false",
        }
        url = f"{JUP_BASE}/v6/quote"
        headers = {"Host": "quote-api.jup.ag"} if JUP_BASE.startswith("https://104.") or JUP_BASE.startswith("https://172.") or JUP_BASE.startswith("http://172.") else {}
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url, params=p, headers=headers) as r:
                if r.status != 200:
                    return None
                return await r.json()

    async def _jup_swap_tx(self, quote: Dict, user_pubkey: str) -> Optional[Dict]:
        url = f"{JUP_BASE}/v6/swap"
        headers = {"Host": "quote-api.jup.ag"} if JUP_BASE.startswith("https://104.") or JUP_BASE.startswith("https://172.") or JUP_BASE.startswith("http://172.") else {}
        payload = {
            "quoteResponse": quote,
            "userPublicKey": user_pubkey,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": self.cfg.priority_fee_microlamports,  # optional
            "useSharedAccounts": True,
        }
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
            async with s.post(url, json=payload, headers=headers) as r:
                if r.status != 200:
                    return None
                return await r.json()

    async def _send_and_confirm(self, swap_tx_b64: str) -> Optional[str]:
        if self.cfg.dry_run or not self.kp:
            self.log.info("[DRY-RUN] Swap tx prepared (not sent).")
            return "DRYRUN"
        raw = base64.b64decode(swap_tx_b64)
        vt = VersionedTransaction.from_bytes(raw)
        # Sign
        signed = VersionedTransaction(vt.message, [self.kp])
        async with await self._sol_client() as c:
            sig = await c.send_raw_transaction(bytes(signed), opts=TxOpts(skip_preflight=False, max_retries=3))
            sigstr = sig.value
            # Confirm
            await c.confirm_transaction(sigstr, commitment=Confirmed)
            return sigstr

    async def can_sell_probe(self, token_mint: str, min_amount_atoms: int = 1) -> bool:
        """
        Honeypot-suoja: varmista, että löytyy reitti token -> wSOL edes minimaalisella määrällä.
        """
        try:
            q = await self._jup_quote(token_mint, self.cfg.base_asset, min_amount_atoms, "ExactIn")
            return bool(q and q.get("routePlan"))
        except Exception:
            return False

    async def buy_token_for_usd(self, token_mint: str, price_in_usd: float, sol_price_usd: float) -> Dict[str, Any]:
        """
        Ostaa tokenia wSOL:lla Jupiterin kautta summalla `max_trade_usd`.
        Edellyttää arviota SOL-hinnasta (voit lukea Birdeyeltä/CG:ltä). Jos ei ole, tee konservatiivinen oletus.
        """
        res = {"ok": False, "reason": None}
        try:
            # Check wallet balance first
            sol_balance = await self.get_sol_balance()
            self.log.info(f"💰 Wallet balance: {sol_balance:.4f} SOL")
            
            # laske wSOL atomit (lamports) – käytetään wSOL 9 decimals
            trade_sol = self.cfg.max_trade_usd / max(sol_price_usd or 1.0, 1.0)
            
            # Reserve 0.01 SOL for fees
            required_sol = trade_sol + 0.01
            if sol_balance < required_sol:
                res["reason"] = f"insufficient_balance: have {sol_balance:.4f} SOL, need {required_sol:.4f} SOL"
                self.log.warning(res["reason"])
                return res
            
            lamports = int(trade_sol * 10**9)
            q = await self._jup_quote(self.cfg.base_asset, token_mint, lamports, "ExactIn")
            if not q or not q.get("routePlan"):
                res["reason"] = "no_quote"
                return res
            if self.cfg.require_can_sell_probe:
                cs = await self.can_sell_probe(token_mint, 1)
                if not cs:
                    res["reason"] = "cant_sell_probe_fail"
                    return res
            # rakenna swap-tx
            if not self.kp and not self.cfg.dry_run:
                res["reason"] = "no_keypair"
                return res
            user_pk = (str(self.kp.pubkey()) if self.kp else os.getenv("TRADER_PUBLIC_KEY",""))
            sw = await self._jup_swap_tx(q, user_pk)
            if not sw or not sw.get("swapTransaction"):
                res["reason"] = "swap_build_fail"
                return res
            sig = await self._send_and_confirm(sw["swapTransaction"])
            res.update({"ok": True, "sig": sig, "route": q})
            return res
        except Exception as e:
            res["reason"] = f"exception:{e}"
            return res

    async def sell_token_for_base(self, token_mint: str, amount_atoms: int) -> Dict[str, Any]:
        res = {"ok": False, "reason": None}
        try:
            q = await self._jup_quote(token_mint, self.cfg.base_asset, amount_atoms, "ExactIn")
            if not q or not q.get("routePlan"):
                res["reason"] = "no_quote_sell"
                return res
            user_pk = (str(self.kp.pubkey()) if self.kp else os.getenv("TRADER_PUBLIC_KEY",""))
            sw = await self._jup_swap_tx(q, user_pk)
            if not sw or not sw.get("swapTransaction"):
                res["reason"] = "swap_build_fail"
                return res
            sig = await self._send_and_confirm(sw["swapTransaction"])
            res.update({"ok": True, "sig": sig, "route": q})
            return res
        except Exception as e:
            res["reason"] = f"exception:{e}"
            return res
