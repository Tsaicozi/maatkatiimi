import aiohttp, asyncio, base64, os, time, logging
from typing import Optional, Dict, Any
from decimal import Decimal, ROUND_DOWN
from solders.keypair import Keypair
from solders.message import to_bytes_versioned
from solders.transaction import VersionedTransaction
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts, TokenAccountOpts
from solana.rpc.commitment import Confirmed

JUP_BASE = "https://quote-api.jup.ag/v6"  # Jupiter API v6 endpoint

FINALIZED = "finalized"  # vaihtoehdot: processed/confirmed/finalized

def fmt_sol(value: float, places: int = 5) -> str:
    q = Decimal(10) ** -places
    return str(Decimal(value).quantize(q, rounding=ROUND_DOWN))

class Trader:
    def __init__(self, http_rpc_url: str, cfg, logger: Optional[logging.Logger] = None):
        self.http = http_rpc_url
        self.cfg = cfg
        self.log = logger or logging.getLogger(__name__)
        self.JUP_BASE = JUP_BASE  # Jupiter API endpoint
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
    
    async def get_sol_balance(self, *, commitment: str = FINALIZED, min_context_slot: int | None = None) -> float:
        """Get wallet SOL balance in lamports, return as SOL (float)"""
        if not self.kp:
            return 0.0
        try:
            async with await self._sol_client() as c:
                params = [Pubkey.from_string(str(self.kp.pubkey()) if self.kp else os.getenv("TRADER_PUBLIC_KEY",""))]
                opts = {}
                if commitment:
                    opts["commitment"] = commitment
                if min_context_slot is not None:
                    opts["minContextSlot"] = min_context_slot
                # solders AsyncClient ei hyväksy dict-optsia suoraan kaikkiin versioihin -> käytä high-leveliä jos tuettu
                resp = await c.get_balance(params[0], commitment=commitment)
                lamports = int(resp.value)
                return lamports / 1e9
        except Exception as e:
            self.log.error(f"Failed to get SOL balance: {e}")
            return 0.0

    async def get_spendable_lamports(self) -> int:
        """Get spendable lamports (total - fee reserve)"""
        if not self.kp:
            return 0
        try:
            async with await self._sol_client() as c:
                resp = await c.get_balance(self.kp.pubkey(), commitment=FINALIZED)
                total_lamports = int(resp.value)
                # Reserve 0.01 SOL for fees
                fee_reserve_lamports = int(0.01 * 1e9)
                return max(0, total_lamports - fee_reserve_lamports)
        except Exception as e:
            self.log.error(f"Failed to get spendable lamports: {e}")
            return 0

    async def get_token_balance_atoms(self, owner_pubkey: str, mint: str) -> int:
        """Lukee omistajan suurimman token-tilin saldon (atoms)"""
        try:
            async with await self._sol_client() as c:
                resp = await c.get_token_accounts_by_owner(
                    Pubkey.from_string(owner_pubkey),
                    TokenAccountOpts(mint=mint)
                )
                max_amt = 0
                for acc in resp.value:
                    ai = await c.get_token_account_balance(Pubkey.from_string(acc.pubkey))
                    amt = int(ai.value.amount)  # atoms
                    if amt > max_amt:
                        max_amt = amt
                return max_amt
        except Exception as e:
            self.log.error(f"Failed to get token balance: {e}")
            return 0

    async def _confirm_and_fetch_out_amount(self, sig: str, out_mint: str, before_atoms: int) -> int:
        """Odottaa vahvistuksen ja lukee uusimman token-saldon → erotus = toteuma"""
        try:
            # odota confirmed + lue saldo
            async with await self._sol_client() as c:
                await c.confirm_transaction(sig, commitment=Confirmed)
            user_pk = str(self.kp.pubkey()) if self.kp else os.getenv("TRADER_PUBLIC_KEY","")
            after = await self.get_token_balance_atoms(user_pk, out_mint)
            filled = max(0, after - before_atoms)
            return filled
        except Exception as e:
            self.log.error(f"Failed to confirm and fetch out amount: {e}")
            return 0

    async def _jup_quote(self, input_mint: str, output_mint: str, amount: int, swap_mode="ExactIn") -> Optional[Dict]:
        p = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(self.cfg.slippage_bps),
            "restrictIntermediateTokens": "true",  # Vakaampi reitti
            "swapMode": swap_mode,
        }
        url = f"{JUP_BASE}/quote"
        headers = {}  # Ei tarvita Host headeria uudella endpointilla
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url, params=p, headers=headers) as r:
                if r.status != 200:
                    return None
                return await r.json()

    async def _jup_swap_tx(self, quote: Dict, user_pubkey: str) -> Optional[Dict]:
        url = f"{JUP_BASE}/swap"
        headers = {}  # Ei tarvita Host headeria uudella endpointilla
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

    async def _jup_swap_tx(self, quote: dict, user_pk: str) -> dict:
        """Jupiter v6 swap transaction builder"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.JUP_BASE}/swap"
                payload = {
                    "quoteResponse": quote,
                    "userPublicKey": user_pk,
                    "wrapAndUnwrapSol": True,
                    "useSharedAccounts": False,  # Disable shared accounts for simple AMMs
                    "feeAccount": None,
                    "trackingAccount": None,
                    "computeUnitPriceMicroLamports": self.cfg.priority_fee_microlamports,
                    "asLegacyTransaction": False,
                    "useTokenLedger": False,
                    "destinationTokenAccount": None
                }
                headers = {
                    "Content-Type": "application/json"
                }
                self.log.info(f"🔧 Jupiter swap_tx request: {url}")
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    self.log.info(f"🔧 Jupiter swap_tx response: {resp.status}")
                    if resp.status != 200:
                        text = await resp.text()
                        self.log.error(f"Jupiter swap_tx HTTP {resp.status}: {text}")
                        return {}
                    result = await resp.json()
                    self.log.info(f"🔧 Jupiter swap_tx result keys: {list(result.keys()) if result else 'None'}")
                    return result
        except Exception as e:
            self.log.error(f"Jupiter swap_tx error: {e}")
            return {}

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
            
            # 1) mitoitus (wSOL atoms)
            trade_sol = self.cfg.max_trade_usd / max(sol_price_usd or 1.0, 1.0)
            
            # Reserve 0.01 SOL for fees
            required_sol = trade_sol + 0.01
            if sol_balance < required_sol:
                res["reason"] = f"insufficient_balance: have {sol_balance:.4f} SOL, need {required_sol:.4f} SOL"
                self.log.warning(res["reason"])
                return res
            
            lamports = int(trade_sol * 10**9)
            
            # 2) quote
            q = await self._jup_quote(self.cfg.base_asset, token_mint, lamports, "ExactIn")
            if not q or not q.get("routePlan"):
                res["reason"] = "no_quote"
                return res
            
            if self.cfg.require_can_sell_probe:
                cs = await self.can_sell_probe(token_mint, 1)
                if not cs:
                    res["reason"] = "cant_sell_probe_fail"
                    return res
            
            # 3) pre-balance (out mint)
            user_pk = str(self.kp.pubkey()) if self.kp else os.getenv("TRADER_PUBLIC_KEY","")
            before_atoms = await self.get_token_balance_atoms(user_pk, token_mint)
            
            # 4) swap tx build & send
            if not self.kp and not self.cfg.dry_run:
                res["reason"] = "no_keypair"
                return res
            
            sw = await self._jup_swap_tx(q, user_pk)
            if not sw or not sw.get("swapTransaction"):
                res["reason"] = "swap_build_fail"
                return res
            
            sig = await self._send_and_confirm(sw["swapTransaction"])
            
            # Dry-run: palauta arvio
            if sig == "DRYRUN":
                est_out_atoms = int((q.get("outAmount") or 0))
                est_fill_price = (self.cfg.max_trade_usd / max(est_out_atoms, 1)) if est_out_atoms else 0.0
                return {"ok": True, "sig": sig, "route": q, "qty_atoms": est_out_atoms, "fill_price_usd": est_fill_price, "dry_run": True}
            
            # 5) toteuma: luetaan saldoero
            filled_atoms = await self._confirm_and_fetch_out_amount(sig, token_mint, before_atoms)
            if filled_atoms <= 0:
                # fallback: käytä Jupiterin outAmountia
                filled_atoms = int((q.get("outAmount") or 0))
            
            fill_price = self.cfg.max_trade_usd / max(filled_atoms, 1)
            
            res.update({"ok": True, "sig": sig, "route": q,
                        "qty_atoms": filled_atoms,
                        "fill_price_usd": fill_price,
                        "dry_run": False})
            return res
        except Exception as e:
            res["reason"] = f"exception:{e}"
            return res

    async def sell_token_for_base(self, token_mint: str, qty_atoms: int) -> Dict[str, Any]:
        """
        Myy tokenia wSOL:ksi Jupiterin kautta.
        """
        res = {"ok": False, "reason": None}
        try:
            # Check wallet balance first
            sol_balance = await self.get_sol_balance()
            self.log.info(f"💰 Wallet balance: {sol_balance:.4f} SOL")
            
            if qty_atoms <= 0:
                res["reason"] = "no_token_balance"
                return res
            
            # Get quote for selling
            q = await self._jup_quote(token_mint, self.cfg.base_asset, qty_atoms, "ExactIn")
            if not q or not q.get("routePlan"):
                res["reason"] = "no_sell_quote"
                return res
            
            # Build swap transaction
            if not self.kp and not self.cfg.dry_run:
                res["reason"] = "no_keypair"
                return res
            
            user_pk = (str(self.kp.pubkey()) if self.kp else os.getenv("TRADER_PUBLIC_KEY",""))
            sw = await self._jup_swap_tx(q, user_pk)
            if not sw:
                res["reason"] = "swap_build_fail: no response"
                self.log.error("Jupiter swap_tx returned None")
                return res
            if not sw.get("swapTransaction"):
                res["reason"] = f"swap_build_fail: no swapTransaction in response: {sw}"
                self.log.error(f"Jupiter swap_tx response missing swapTransaction: {sw}")
                return res
            
            sig = await self._send_and_confirm(sw["swapTransaction"])
            res.update({"ok": True, "sig": sig, "route": q})
            return res
            
        except Exception as e:
            res["reason"] = f"exception:{e}"
            return res
