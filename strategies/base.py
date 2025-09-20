from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, List, Dict, Any


@dataclass
class StrategySignal:
    type: str  # e.g. "BUY" | "SELL"
    token: Any
    reasoning: str
    confidence: float
    priority: float = 0.0


class Strategy(Protocol):
    """Strategy protocol used by HybridTradingBot.

    A strategy receives analyzed tokens and returns a list of StrategySignal.
    """

    def generate(self, tokens: List[Any], context: Dict[str, Any] | None = None) -> List[StrategySignal]:
        ...

