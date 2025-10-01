import asyncio, time

class ExitWorker:
    def __init__(self, bot, trader, positions, dex_fetcher, interval=30):
        self.bot = bot
        self.trader = trader
        self.positions = positions
        self.dex_fetcher = dex_fetcher
        self.interval = interval
        self.running = False

    async def price_usd_now(self, mint: str, qty_atoms: int) -> float:
        # Jupiter quote token -> USDC (ExactIn)
        q = await self.trader._jup_quote(mint, self.trader.cfg.quote_asset, max(qty_atoms,1), "ExactIn")
        if q and q.get("outAmount"):
            usdc_atoms = int(q["outAmount"])
            return usdc_atoms / 1e6  # USDC 6 decimals
        return 0.0

    async def once(self):
        pos = self.positions.get_all()
        for mint, p in pos.items():
            if p.get("status") != "open":
                continue

            qty_atoms = int(p.get("qty_atoms", 0))
            entry_px = float(p.get("entry_price_usd", 0.0))
            entry_vol = float(p.get("entry_volume", 0.0))
            entry_liq = float(p.get("entry_liquidity", 0.0))
            held = time.time() - float(p.get("entry_time", 0.0))

            # Hinta nyt (USD per atom → per token)
            # koska quote antaa "usd for whole qty": tee yksikköhinta
            usdc_for_all = await self.price_usd_now(mint, qty_atoms)
            px_now = (usdc_for_all / max(qty_atoms,1)) if qty_atoms>0 else 0.0
            change = (px_now/entry_px - 1.0) if entry_px>0 else 0.0

            # Tuore DEX-data
            dex = await self.dex_fetcher.fetch(mint, timeout=8.0)
            liq = float(((dex.get("dexscreener") or {}).get("bestLiqUsd") or dex.get("liq_usd") or entry_liq or 0.0))
            vol = float(((dex.get("dexscreener") or {}).get("bestVol24h") or dex.get("vol_h24") or entry_vol or 0.0))

            reason = None
            if change >= 1.0:              reason = "TP_100pct"
            elif change <= -0.30:          reason = "SL_30pct"
            elif held >= 48*3600:          reason = "TIME_48h"
            elif vol < entry_vol * 0.2:    reason = "VOL_20pct"
            elif liq < entry_liq * 0.5:    reason = "LIQ_50pct"
            elif vol < 1000.0:             reason = "LOW_VOL_<1k"

            if not reason:
                continue

            # MYY
            sell_res = await self.trader.sell_token_for_base(mint, qty_atoms)
            if sell_res.get("ok"):
                proceeds = await self.price_usd_now(mint, 1) * qty_atoms  # likimääräinen USD (vaihtoehtoisesti lue USDC saldoero)
                pnl = proceeds - (entry_px * qty_atoms)
                self.positions.close_position(mint, {"exit_reason": reason, "exit_sig": sell_res.get("sig"), "pnl_usd": pnl})
                self.bot._send_telegram(f"🔴 *SELL* `{mint}` reason={reason} pnl=${pnl:,.2f} sig=`{sell_res.get('sig')}`", parse_mode="Markdown")
            else:
                self.bot._send_telegram(f"⚠️ *SELL FAIL* `{mint}` reason={sell_res.get('reason')}", parse_mode="Markdown")

    async def run(self):
        self.running = True
        while self.running:
            try:
                await self.once()
            except Exception as e:
                self.bot._log_exception("exit_worker_once_failed", e)
            await asyncio.sleep(self.interval)
