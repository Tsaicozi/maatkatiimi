from __future__ import annotations

from typing import List, Dict, Any
from .base import Strategy, StrategySignal


class VolumeSpikeStrategy:
    """Volume spike strategy.

    Buys when 24h volume is strong for small caps and price momentum is decent.
    """

    def __init__(self, *, max_signals: int = 2):
        self.max_signals = max_signals

    def generate(self, tokens: List[Any], context: Dict[str, Any] | None = None) -> List[StrategySignal]:
        context = context or {}
        ranked = sorted(
            tokens,
            key=lambda t: (getattr(t, "volume_24h", 0.0) / max(1.0, getattr(t, "market_cap", 1.0))),
            reverse=True,
        )
        signals: List[StrategySignal] = []
        for token in ranked:
            mc = float(getattr(token, "market_cap", 0.0) or 0.0)
            vol = float(getattr(token, "volume_24h", 0.0) or 0.0)
            chg = float(getattr(token, "price_change_24h", 0.0) or 0.0)
            liq = float(getattr(token, "liquidity", 0.0) or 0.0)
            age = float(getattr(token, "age_minutes", 0.0) or 0.0)

            if not (0.5 <= age <= 20):
                continue
            if not (5000 <= mc <= 150000):
                continue
            if liq < 8000:
                continue
            if chg < 5.0:
                continue
            if vol < 10000:
                continue

            vol_to_mc = vol / max(mc, 1.0)
            conf = min(1.0, 0.5 + min(0.5, vol_to_mc))
            prio = min(1.0, 0.6 * min(1.0, vol_to_mc) + 0.4 * min(1.0, chg / 20.0))
            signals.append(StrategySignal(
                type="BUY",
                token=token,
                reasoning=f"Vol/MC {vol_to_mc:.2f}, vol ${vol:,.0f}, Δ24h {chg:.1f}%",
                confidence=conf,
                priority=prio,
            ))
            if len(signals) >= self.max_signals:
                break
        return signals

