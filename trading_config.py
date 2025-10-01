from dataclasses import dataclass

@dataclass
class TradingConfig:
    enabled: bool = False              # AUTO_TRADE=1 -> True
    dry_run: bool = True               # DRY_RUN=1 (oletus turvallisesti päälle)
    # Position sizing
    base_asset: str = "So11111111111111111111111111111111111111112"  # wSOL mint
    quote_asset: str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" # USDC mint
    max_trade_usd: float = 100.0       # ostokoko USD
    max_positions: int = 5
    # Execution controls
    slippage_bps: int = 150            # 1.50% slippage
    priority_fee_microlamports: int = 200_000  # ~0.0002 SOL / CU price tip fallback
    compute_unit_limit: int = 600_000
    # Strategy thresholds
    min_score_to_buy: int = 50
    min_liq_usd_to_buy: float = 10_000
    util_min: float = 0.35
    util_max: float = 6.0
    # Exits (stub – voit hienosäätää myöhemmin)
    take_profit_pct: float = 25.0      # +25% TP
    stop_loss_pct: float = 20.0        # -20% SL
    cooldown_sec: int = 120            # per-mint cooldown ennen uutta ostoa
    # Safety checks
    require_can_sell_probe: bool = True  # simulaatio: token->wSOL quote ennen ostoa