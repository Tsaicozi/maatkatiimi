"""
Simple strategies package for HybridTradingBot.

Exports base Strategy protocol and concrete strategies.
"""

from .base import Strategy
from .momentum import MomentumStrategy
from .volume_spike import VolumeSpikeStrategy

__all__ = [
    "Strategy",
    "MomentumStrategy",
    "VolumeSpikeStrategy",
]

