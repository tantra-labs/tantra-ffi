# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)
from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator("cci", "momentum", inputs=("high", "low", "close"), warmup=lambda s: s.length)
class Cci(Indicator):
    """Commodity Channel Index (TradingView): (tp - SMA(tp)) / (0.015 * mean absolute deviation), tp = (high+low+close)/3.

    Uses the mean absolute deviation about the SMA (not standard deviation). Zero deviation gives 0.
    """

    def __init__(self, length: int = 20) -> None:
        self.length = _check(length)
        self._w: deque[Decimal] = deque(maxlen=length)

    def update(self, high: Decimal, low: Decimal, close: Decimal) -> Decimal | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        self._w.append((high + low + close) / 3)
        if len(self._w) < self.length:
            return None
        n = self.length
        mean = sum(self._w) / n
        mad = sum(abs(v - mean) for v in self._w) / n
        return (self._w[-1] - mean) / (Decimal("0.015") * mad) if mad != 0 else Decimal("0")
