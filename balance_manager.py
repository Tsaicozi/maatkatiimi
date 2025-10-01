from typing import Dict, Any
import asyncio
import os
from decimal import Decimal, ROUND_DOWN
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts

WSOL_MINT = "So11111111111111111111111111111111111111112"

def _fmt(v: float, p=5):
    q = Decimal(10) ** -p
    return str(Decimal(v).quantize(q, rounding=ROUND_DOWN))

class BalanceManager:
    def __init__(self, trader):
        self.trader = trader

    async def get_sol(self) -> float:
        return await self.trader.get_sol_balance()

    async def get_token_atoms(self, mint: str) -> int:
        user_pk = str(self.trader.kp.pubkey()) if self.trader.kp else ""
        return await self.trader.get_token_balance_atoms(user_pk, mint)

    async def get_wsol_atoms(self, owner_pubkey: str) -> int:
        # lue omistetut token-tilit WSOL-mintille
        async with await self.trader._sol_client() as c:
            resp = await c.get_token_accounts_by_owner(Pubkey.from_string(owner_pubkey),
                              TokenAccountOpts(mint=WSOL_MINT))
            total = 0
            for acc in resp.value:
                bal = await c.get_token_account_balance(Pubkey.from_string(acc.pubkey))
                total += int(bal.value.amount)
            return total

    async def snapshot(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        owner = str(self.trader.kp.pubkey()) if self.trader.kp else os.getenv("TRADER_PUBLIC_KEY","")
        sol_total = await self.trader.get_sol_balance()
        # spendable = total - fee-reserve (sama funktio kuin treiderissä)
        spendable_lamports = await self.trader.get_spendable_lamports()
        spendable = spendable_lamports / 1e9

        wsol_atoms = await self.get_wsol_atoms(owner)
        wsol = wsol_atoms / 1e9  # WSOL 9 desimaalia

        balances = {}
        for mint in positions.keys():
            balances[mint] = await self.get_token_atoms(mint)

        return {
            "sol_total": sol_total,
            "sol_total_display": _fmt(sol_total, 5),     # esim. 0.11937
            "sol_spendable": spendable,
            "sol_spendable_display": _fmt(spendable, 5),
            "wsol": wsol,
            "wsol_display": _fmt(wsol, 5),
            "tokens": balances
        }
