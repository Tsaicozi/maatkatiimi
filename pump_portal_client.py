#!/usr/bin/env python3
"""
PumpPortal Trading & Data client (drop-in)

- Local trading (sign & send yourself):
  POST https://pumpportal.fun/api/trade-local
  Docs: https://pumpportal.fun/local-trading-api/trading-api/

- Discovery WS:
  wss://pumpportal.fun/api/data
  Docs: https://pumpportal.fun/data-api/real-time/

Turva:
- ÄLÄ kovakoodaa privakeytä. Lue KEY ympäristöstä (BASE58) tai tiedostosta.
- Käytä omaa, luotettavaa RPC:tä (palkatut solmut >> public).
"""
from __future__ import annotations
import os, json, asyncio, logging, time, contextlib
from typing import Iterable, Optional, Callable, Awaitable, Dict, Any

import aiohttp
import websockets
from base58 import b58decode

# solders (virallinen datarakenteiden toteutus)
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.rpc.requests import SendVersionedTransaction
from solders.rpc.config import RpcSendTransactionConfig
from solders.commitment_config import CommitmentLevel

logger = logging.getLogger(__name__)


# -------------------------------
# Helpers: avaimen lataus
# -------------------------------
def load_keypair_from_env(env_var: str = "PUMP_TRADER_PRIVATE_KEY") -> Keypair:
    """
    Lue yksityisavain:
      - BASE58 (Phantom/Backpack export) suoraan envistä
      - polku JSON-keypair tiedostoon (solana-keygen 64 bytes array)

    Esim:
      export PUMP_TRADER_PRIVATE_KEY="3ab...base58..."
      TAI
      export PUMP_TRADER_PRIVATE_KEY="/path/to/id.json"
    """
    val = os.getenv(env_var)
    if not val:
        raise ValueError(f"{env_var} ei ole asetettu")

    # jos näyttää tiedostopolulta
    if os.path.exists(val):
        with open(val, "r", encoding="utf-8") as f:
            arr = json.load(f)
        if not (isinstance(arr, list) and len(arr) in (64, 32)):
            raise ValueError("Keypair JSON ei ole 64/32 byte array")
        return Keypair.from_bytes(bytes(arr))

    # muuten olettaa base58 secret
    try:
        sk = b58decode(val)
        return Keypair.from_bytes(sk if len(sk) in (64, 32) else sk[:64])
    except Exception as e:
        raise ValueError("PUMP_TRADER_PRIVATE_KEY ei ole kelvollinen base58 tai polku JSON:iin") from e


# -------------------------------
# Trading client
# -------------------------------
class PumpPortalTradingClient:
    """
    Local trade -klientti:
      - hakee tx:n pumpportalista
      - allekirjoittaa lokaalisti
      - lähettää sinun RPC:lle
    """
    def __init__(
        self,
        rpc_url: str,
        keypair: Keypair,
        *,
        base_url: str = "https://pumpportal.fun",
        session: Optional[aiohttp.ClientSession] = None,
        default_slippage: float = 10.0,
        default_priority_fee: float = 0.00001,
        default_pool: str = "auto",
        commitment: CommitmentLevel = CommitmentLevel.Confirmed,
        skip_preflight: bool = False,
    ):
        self.rpc_url = rpc_url
        self.keypair = keypair
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.default_slippage = default_slippage
        self.default_priority_fee = default_priority_fee
        self.default_pool = default_pool
        self.commitment = commitment
        self.skip_preflight = skip_preflight

    @classmethod
    def from_env(cls) -> "PumpPortalTradingClient":
        rpc = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        kp = load_keypair_from_env()
        return cls(rpc_url=rpc, keypair=kp)

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session and not self.session.closed:
            return self.session
        self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _trade_local_bytes(
        self,
        *,
        action: str,
        mint: str,
        amount: float | str,
        denominated_in_sol: bool,
        slippage: Optional[float] = None,
        priority_fee: Optional[float] = None,
        pool: Optional[str] = None,
    ) -> bytes:
        """
        Hakee serialisoidun VersionedTransactionin pumpportalilta.
        Palauttaa tx-bytes (valmis allekirjoitettavaksi).

        API: POST {base}/api/trade-local
        Pakolliset kentät (docs):
          publicKey, action ("buy"/"sell"), mint, amount, denominatedInSol ("true"/"false"), slippage, priorityFee, pool?
        """
        url = f"{self.base_url}/api/trade-local"
        sess = await self._ensure_session()
        if isinstance(amount, (int, float)):
            amt_value: float | str = float(amount)
        else:
            amt_value = str(amount)

        payload = {
            "publicKey": str(self.keypair.pubkey()),
            "action": action,
            "mint": mint,
            "amount": amt_value,
            "denominatedInSol": "true" if denominated_in_sol else "false",
            "slippage": float(slippage if slippage is not None else self.default_slippage),
            "priorityFee": float(priority_fee if priority_fee is not None else self.default_priority_fee),
            "pool": (pool or self.default_pool),
        }
        headers = {"Content-Type": "application/json"}
        async with sess.post(url, headers=headers, data=json.dumps(payload), timeout=10) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"PumpPortal trade-local status={resp.status} body={text}")
            tx_bytes = await resp.read()
            return tx_bytes

    async def _sign_and_send(self, tx_bytes: bytes) -> str:
        """
        Deserialisoi, allekirjoita ja lähetä VersionedTransaction RPC:lle.
        """
        # Deserialisoi -> rakenna signereillä
        vt = VersionedTransaction.from_bytes(tx_bytes)
        tx = VersionedTransaction(vt.message, [self.keypair])

        cfg = RpcSendTransactionConfig(
            skip_preflight=self.skip_preflight,
            preflight_commitment=self.commitment,
        )
        payload = SendVersionedTransaction(tx, cfg).to_json()
        headers = {"Content-Type": "application/json"}

        sess = await self._ensure_session()
        async with sess.post(self.rpc_url, headers=headers, data=payload, timeout=15) as r:
            j = await r.json()
            if "error" in j:
                raise RuntimeError(f"RPC send error: {j['error']}")
            sig = j.get("result")
            if not sig:
                raise RuntimeError(f"RPC response missing result: {j}")
            return sig

    # ---------- Public API ----------
    async def buy(
        self,
        mint: str,
        *,
        amount_sol: float,
        slippage: Optional[float] = None,
        priority_fee: Optional[float] = None,
        pool: Optional[str] = None,
    ) -> str:
        txb = await self._trade_local_bytes(
            action="buy",
            mint=mint,
            amount=float(amount_sol),
            denominated_in_sol=True,
            slippage=slippage,
            priority_fee=priority_fee,
            pool=pool,
        )
        return await self._sign_and_send(txb)

    async def sell(
        self,
        mint: str,
        *,
        amount_tokens: float | str,
        slippage: Optional[float] = None,
        priority_fee: Optional[float] = None,
        pool: Optional[str] = None,
    ) -> str:
        txb = await self._trade_local_bytes(
            action="sell",
            mint=mint,
            amount=amount_tokens,                 # HUOM: tokenimäärä tai esim. "100%"
            denominated_in_sol=False,
            slippage=slippage,
            priority_fee=priority_fee,
            pool=pool,
        )
        return await self._sign_and_send(txb)


# -------------------------------
# Data (WS) – hyvin kevyt discovery
# -------------------------------
class PumpPortalDataClient:
    """
    Yksinkertainen WS-klientti discoveryyn.
    Käytä yhtä WS-yhteyttä ja lähetä useita subscribe-viestejä (docs).
    """
    def __init__(self):
        self._ws = None

    async def connect(self):
        self._ws = await websockets.connect("wss://pumpportal.fun/api/data")

    async def close(self):
        if self._ws:
            await self._ws.close()

    async def subscribe_new_tokens(self):
        await self._ws.send(json.dumps({"method": "subscribeNewToken"}))

    async def subscribe_token_trades(self, mints: Iterable[str]):
        await self._ws.send(json.dumps({"method": "subscribeTokenTrade", "keys": list(mints)}))

    async def subscribe_account_trades(self, accounts: Iterable[str]):
        await self._ws.send(json.dumps({"method": "subscribeAccountTrade", "keys": list(accounts)}))

    async def recv_loop(self, on_message: Callable[[Dict[str, Any]], Awaitable[None]]):
        async for raw in self._ws:
            with contextlib.suppress(Exception):
                await on_message(json.loads(raw))


# -------------------------------
# pika-demo
# -------------------------------
async def _demo():
    """
    Käyttöesimerkki:
      export PUMP_TRADER_PRIVATE_KEY="base58 tai /polku/id.json"
      export SOLANA_RPC_URL="https://api.mainnet-beta.solana.com"
    """
    logging.basicConfig(level=logging.INFO)
    client = PumpPortalTradingClient.from_env()

    # OSTA 0.01 SOL edestä
    # sig = await client.buy(mint="TOKEN_MINT_HERE", amount_sol=0.01, slippage=10, priority_fee=0.00001)
    # print("buy signature:", sig)

    # MYY 5000 tokenia
    # sig = await client.sell(mint="TOKEN_MINT_HERE", amount_tokens=5000, slippage=10, priority_fee=0.00001)
    # print("sell signature:", sig)

    await client.close()

if __name__ == "__main__":
    asyncio.run(_demo())
