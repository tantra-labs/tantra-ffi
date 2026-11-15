# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Kaufman adaptive moving average."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator("kama", "moving_average", warmup=lambda s: s.period + 1)
class Kama(Indicator):
    """KAMA: er=|c-c[n]|/sum|dc|; sc=(er*(2/(fast+1)-2/(slow+1))+2/(slow+1))^2; k += sc*(c-k).

    Seeded with the close just before the first computed bar, so the first value
    appears after ``period + 1`` bars. Zero total movement gives er = 0.
    """

    def __init__(self, period: int = 10, fast: int = 2, slow: int = 30) -> None:
        self.period = _check(period)
        if not 0 < _check(fast) < _check(slow):
            raise ValueError(f"fast must be less than slow, got {fast} and {slow}")
        self.fast, self.slow = fast, slow
        self._fa, self._sa = Decimal(2) / (fast + 1), Decimal(2) / (slow + 1)
        self._w: deque[Decimal] = deque(maxlen=period + 1)
        self._path = Decimal("0")  # sum of |diff| over the last `period` steps
        self.value: Decimal | None = None

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        w = self._w
        if len(w) == self.period + 1:
            self._path -= abs(w[1] - w[0])
        if w:
            self._path += abs(x - w[-1])
        w.append(x)
        if len(w) < self.period + 1:
            return None
        er = abs(x - w[0]) / self._path if self._path > Decimal("0") else Decimal("0")
        sc = (er * (self._fa - self._sa) + self._sa) ** 2
        prev = w[-2] if self.value is None else self.value
        self.value = prev + sc * (x - prev)
        return self.value
