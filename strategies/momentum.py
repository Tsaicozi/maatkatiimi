from __future__ import annotations

from typing import List, Dict, Any
from .base import Strategy, StrategySignal


class MomentumStrategy:
    """Simple momentum-based BUY strategy.

    Prefers tokens with high momentum_score, positive price change, and acceptable risk.
    """

    def __init__(self, *, max_signals: int = 3):
        self.max_signals = max_signals

    def generate(self, tokens: List[Any], context: Dict[str, Any] | None = None) -> List[StrategySignal]:
        context = context or {}
        # Sort by (momentum - risk) primarily, fall back to technical score
        ranked = sorted(
            tokens,
            key=lambda t: (getattr(t, "momentum_score", 0.0) - getattr(t, "risk_score", 0.0), getattr(t, "technical_score", 0.0)),
            reverse=True,
        )
        signals: List[StrategySignal] = []
        for token in ranked:
            mom = float(getattr(token, "momentum_score", 0.0) or 0.0)
            risk = float(getattr(token, "risk_score", 0.0) or 0.0)
            chg = float(getattr(token, "price_change_24h", 0.0) or 0.0)
            age = float(getattr(token, "age_minutes", 0.0) or 0.0)

            if not (0.5 <= age <= 15):
                continue
            if mom < 0.55 or chg < 8.0 or risk > 0.3:
                continue

            conf = min(1.0, mom * 0.6 + max(0.0, chg) / 100.0 * 0.4)
            prio = min(1.0, mom * 0.7 + (1.0 - risk) * 0.3)
            signals.append(StrategySignal(
                type="BUY",
                token=token,
                reasoning=f"Momentum {mom:.2f}, Δ24h {chg:.1f}%, risk {risk:.2f}",
                confidence=conf,
                priority=prio,
            ))

            if len(signals) >= self.max_signals:
                break
        return signals

