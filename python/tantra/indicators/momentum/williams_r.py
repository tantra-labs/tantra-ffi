# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

# mirror: kernel-verbatim port (gap 0006)
from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator(
    "williams_r", "momentum", inputs=("high", "low", "close"), warmup=lambda s: s.length
)
class WilliamsR(Indicator):
    """Williams %R (TradingView): 100 * (close - highest high) / (highest high - lowest low), range -100..0.

    A flat window (zero range) returns -50 (midpoint).
    """

    def __init__(self, length: int = 14) -> None:
        self.length = _check(length)
        self._h: deque[Decimal] = deque(maxlen=length)
        self._l: deque[Decimal] = deque(maxlen=length)

    def update(self, high: Decimal, low: Decimal, close: Decimal) -> Decimal | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        self._h.append(high)
        self._l.append(low)
        if len(self._h) < self.length:
            return None
        hh, ll = max(self._h), min(self._l)
        return Decimal(100) * (close - hh) / (hh - ll) if hh != ll else Decimal(-50)
