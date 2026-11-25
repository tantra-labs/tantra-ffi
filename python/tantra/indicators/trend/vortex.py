# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Vortex indicator."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._rolling import RollingSum
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class VortexValue:
    plus: Decimal
    minus: Decimal


@indicator(
    "vortex",
    "trend",
    inputs=("high", "low", "close"),
    outputs=("plus", "minus"),
    warmup=lambda s: s.period + 1,
)
class Vortex(Indicator):
    """Vortex: VI+ = sum|high - prev low| / sum TR, VI- = sum|low - prev high| / sum TR over ``period`` bars.

    Needs a previous bar, so the first value appears after ``period + 1`` bars. Zero TR sum gives 0.
    """

    def __init__(self, period: int = 14) -> None:
        self.period = _check(period)
        self._prev: tuple[Decimal, Decimal, Decimal] | None = None
        self._plus = RollingSum(period)
        self._minus = RollingSum(period)
        self._tr = RollingSum(period)

    def update(self, high: Decimal, low: Decimal, close: Decimal) -> VortexValue | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        prev, self._prev = self._prev, (high, low, close)
        if prev is None:
            return None
        ph, pl, pc = prev
        p = self._plus.update(abs(high - pl))
        m = self._minus.update(abs(low - ph))
        t = self._tr.update(max(high - low, abs(high - pc), abs(low - pc)))
        if p is None or m is None or t is None:
            return None
        if t <= 0:
            return VortexValue(Decimal(0), Decimal(0))
        return VortexValue(p / t, m / t)
