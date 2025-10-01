import asyncio, time
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TokenAccountOpts

class ReconcileWorker:
    def __init__(self, http_url, owner_pubkey, positions, interval=90, logger=None, bot=None):
        self.http = http_url
        self.owner = owner_pubkey
        self.positions = positions
        self.itv = interval
        self.log = logger
        self.bot = bot

    async def get_atoms(self, c, mint):
        resp = await c.get_token_accounts_by_owner(Pubkey.from_string(self.owner), TokenAccountOpts(mint=mint))
        tot=0
        for acc in resp.value:
            bal = await c.get_token_account_balance(Pubkey.from_string(acc.pubkey))
            tot += int(bal.value.amount)
        return tot

    async def once(self):
        openpos = {m:p for m,p in self.positions.get_all().items() if p.get("status")=="open"}
        if not openpos: return
        async with AsyncClient(self.http) as c:
            for mint, pos in openpos.items():
                try:
                    atoms = await self.get_atoms(c, mint)
                    want = int(pos.get("qty_atoms",0))
                    if atoms == 0:
                        self.positions.close_position(mint, {"exit_reason":"reconciled_zero_balance"})
                        if self.log: self.log.info("reconcile: closed %s (on-chain=0)", mint)
                        if self.bot: self.bot._send_telegram(f"ℹ️ Reconciled: `{mint}` closed (on-chain balance 0)", parse_mode="Markdown")
                    elif atoms != want:
                        self.positions.update_position(mint, {"qty_atoms":atoms, "reconciled_at": time.time()})
                        if self.log: self.log.info("reconcile: adjusted %s qty %d→%d", mint, want, atoms)
                except Exception as e:
                    if self.log: self.log.warning("reconcile fail %s: %s", mint, e)

    async def run(self):
        while True:
            await self.once()
            await asyncio.sleep(self.itv)
