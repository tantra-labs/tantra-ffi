# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Chaikin volatility (volatility family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average.averages import Ema
from tantra.types import to_decimal


@indicator(
    "chaikin_volatility",
    "volatility",
    inputs=("high", "low"),
    warmup=lambda s: s.length + s.roc_length,
)
class ChaikinVolatility(Indicator):
    """Chaikin volatility: percent rate of change over ``roc_length`` of the SMA-seeded EMA(high - low, length).

    A zero EMA ``roc_length`` bars ago returns 0.0."""

    def __init__(self, length: int = 10, roc_length: int = 10) -> None:
        self.length, self.roc_length = _check(length), _check(roc_length)
        self._ema = Ema(length)
        self._hist: deque[Decimal] = deque(maxlen=roc_length + 1)

    def update(self, high: Decimal, low: Decimal) -> Decimal | None:
        high, low = to_decimal(high), to_decimal(low)
        e = self._ema.update(high - low)
        if e is None:
            return None
        self._hist.append(e)
        if len(self._hist) <= self.roc_length:
            return None
        old = self._hist[0]
        return Decimal(0) if old == 0 else Decimal(100) * (e - old) / old
