# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Rescaled-range Hurst exponent (statistical family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from decimal import Decimal
from itertools import pairwise

from tantra.indicators._base import Indicator, indicator
from tantra.types import to_decimal


@indicator("hurst_exponent", "statistical", warmup=lambda s: s.length)
class HurstExponent(Indicator):
    """Single-window R/S Hurst estimate over the last ``length`` closes.

    Uses the n = length-1 price increments: R = max - min of the cumulative mean-adjusted
    sums, S = population stdev of increments, H = ln(R/S) / ln(n), clamped to [0, 1].
    Returns 0.5 (random walk) when S or R is 0. Simple estimator, biased for short windows.
    """

    def __init__(self, length: int = 100) -> None:
        if length < 8:
            raise ValueError(f"length must be >= 8, got {length}")
        self.length = length
        self._w: deque[Decimal] = deque(maxlen=length)

    def update(self, close: Decimal) -> Decimal | None:
        close = to_decimal(close)
        self._w.append(close)
        if len(self._w) < self.length:
            return None
        w = list(self._w)
        d = [b - a for a, b in pairwise(w)]
        n = len(d)
        m = sum(d) / n
        s = (sum((v - m) ** 2 for v in d) / n).sqrt()
        cum, lo, hi = Decimal("0"), Decimal("0"), Decimal("0")
        for v in d:
            cum += v - m
            lo, hi = min(lo, cum), max(hi, cum)
        r = hi - lo
        if s <= 0 or r <= 0:
            return Decimal("0.5")
        return max(Decimal("0"), min(Decimal("1"), (r / s).ln() / Decimal(n).ln()))
