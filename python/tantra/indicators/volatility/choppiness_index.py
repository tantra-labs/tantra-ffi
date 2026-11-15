# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Choppiness index (volatility family)."""
# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.types import to_decimal


@indicator(
    "choppiness_index",
    "volatility",
    inputs=("high", "low", "close"),
    warmup=lambda s: s.length,
)
class ChoppinessIndex(Indicator):
    """Choppiness index = 100 * log10(sum(TR, n) / (highest high - lowest low)) / log10(n).

    The first bar's true range is high - low (TradingView). Values near 100 are choppy, near 0 trending.
    A zero-range window returns 0.0. ``length`` must be >= 2."""

    def __init__(self, length: int = 14) -> None:
        if length < 2:
            raise ValueError(f"length must be >= 2, got {length}")
        self.length = length
        self._prev: Decimal | None = None
        self._tr: deque[Decimal] = deque(maxlen=length)
        self._h: deque[Decimal] = deque(maxlen=length)
        self._l: deque[Decimal] = deque(maxlen=length)

    def update(self, high: Decimal, low: Decimal, close: Decimal) -> Decimal | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        prev, self._prev = self._prev, close
        tr = high - low if prev is None else max(high - low, abs(high - prev), abs(low - prev))
        self._tr.append(tr)
        self._h.append(high)
        self._l.append(low)
        if len(self._tr) < self.length:
            return None
        rng = max(self._h) - min(self._l)
        total = sum(self._tr, Decimal("0"))
        if rng <= 0 or total <= 0:
            return Decimal("0")
        return Decimal("100") * (total / rng).log10() / Decimal(self.length).log10()
