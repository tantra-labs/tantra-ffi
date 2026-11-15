# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Least-squares (linear regression) moving average."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.types import to_decimal


def linreg_fit(ys: Sequence[Decimal]) -> tuple[Decimal, Decimal]:
    """Least-squares line through (0, ys[0]) .. (n-1, ys[-1]) as (intercept, slope); n >= 2."""
    n = len(ys)
    sx = Decimal(n * (n - 1)) / 2
    sxx = Decimal((n - 1) * n * (2 * n - 1)) / 6
    sy = sxy = Decimal("0")
    for i, y in enumerate(ys):
        y = to_decimal(y)
        sy += y
        sxy += i * y
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    return (sy - slope * sx) / n, slope


@indicator("lsma", "moving_average", warmup=lambda s: s.period)
class Lsma(Indicator):
    """LSMA: endpoint of the least-squares line over ``period`` bars, shifted by ``offset`` bars.

    value = intercept + slope * (period - 1 - offset) (TradingView ta.linreg).
    """

    def __init__(self, period: int = 25, offset: int = 0) -> None:
        if period < 2:
            raise ValueError(f"period must be >= 2, got {period}")
        self.period, self.offset = period, offset
        self._w: deque[Decimal] = deque(maxlen=period)
        self._k = period - 1 - offset

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        self._w.append(x)
        if len(self._w) < self.period:
            return None
        if any(not v.is_finite() for v in self._w):
            return Decimal("NaN")
        b, m = linreg_fit(self._w)
        return b + m * self._k
