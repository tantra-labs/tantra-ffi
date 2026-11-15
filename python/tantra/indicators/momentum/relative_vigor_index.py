# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average.averages import Sma
from tantra.types import to_decimal


@dataclass(slots=True)
class RvgiValue:
    rvgi: Decimal
    signal: Decimal


def _swma(a: Decimal, b: Decimal, c: Decimal, d: Decimal) -> Decimal:
    return (a + 2 * b + 2 * c + d) / 6


@indicator(
    "relative_vigor_index",
    "momentum",
    inputs=("open", "high", "low", "close"),
    outputs=("rvgi", "signal"),
    warmup=lambda s: s.length + 6,
)
class RelativeVigorIndex(Indicator):
    """Relative Vigor Index (TradingView RVGI): SMA(SWMA(close-open), n) / SMA(SWMA(high-low), n); signal = SWMA(rvgi).

    SWMA weights the last four values 1,2,2,1 (/6, newest last). A zero denominator gives 0.
    """

    def __init__(self, length: int = 10) -> None:
        self.length = _check(length)
        self._co: deque[Decimal] = deque(maxlen=4)
        self._hl: deque[Decimal] = deque(maxlen=4)
        self._num, self._den = Sma(length), Sma(length)
        self._r: deque[Decimal] = deque(maxlen=4)

    def update(self, open: Decimal, high: Decimal, low: Decimal, close: Decimal) -> RvgiValue | None:
        open, high, low, close = to_decimal(open), to_decimal(high), to_decimal(low), to_decimal(close)
        self._co.append(close - open)
        self._hl.append(high - low)
        if len(self._co) < 4:
            return None
        n = self._num.update(_swma(*self._co))
        d = self._den.update(_swma(*self._hl))
        if n is None or d is None:
            return None
        self._r.append(n / d if d != 0 else Decimal("0"))
        if len(self._r) < 4:
            return None
        return RvgiValue(self._r[-1], _swma(*self._r))
