# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Private rolling helpers (kernel ``_rolling`` mirror): exact ``Decimal`` running sums and an O(1) least-squares fit."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._util import check as _check
from tantra.types import to_decimal

_LARGE = Decimal("1e150")


class RollingSum:
    """Sum of the last ``period`` values; ``None`` until the window is full."""

    def __init__(self, period: int) -> None:
        self.period = _check(period)
        self._w: deque[Decimal] = deque(maxlen=period)
        self._sum = Decimal("0")

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        if len(self._w) == self.period:
            self._sum -= self._w[0]
        self._w.append(x)
        self._sum += x
        return self._sum if len(self._w) == self.period else None


class RollingLinReg:
    """O(1) least-squares fit of the last ``length`` values, indexed 0..length-1.

    ``update_raw(x)`` returns ``(intercept, slope, sse)`` or ``None`` until the
    window is full. A non-finite or ``|v| > 1e150`` value makes the fit NaN while
    it is in the window; running sums are frozen then, and rebuilt exactly once the
    value has left (the float-only drift/overflow guards are unnecessary here).
    """

    def __init__(self, length: int) -> None:
        if length < 2:
            raise ValueError(f"length must be >= 2, got {length}")
        self.length = length
        self._w: deque[Decimal] = deque(maxlen=length)
        self._sx = Decimal("0")
        self._sxx = Decimal("0")
        self._sxt = Decimal("0")
        self._bad = 0
        self._dirty = False
        n = length
        self._st = Decimal(n * (n - 1) // 2)
        self._stt = Decimal((n - 1) * n * (2 * n - 1) // 6)

    def update_raw(self, x: Decimal) -> tuple[Decimal, Decimal, Decimal] | None:
        x = to_decimal(x)
        good = x.is_finite() and abs(x) <= _LARGE
        full = len(self._w) == self.length
        if full and not (self._w[0].is_finite() and abs(self._w[0]) <= _LARGE):
            self._bad -= 1
        if good and not self._dirty and not self._bad:
            if full:  # slide: drop oldest, shift weights down by one
                old = self._w[0]
                self._sxt -= self._sx - old
                self._sx -= old
                self._sxx -= old * old
            self._w.append(x)
            self._sx += x
            self._sxx += x * x
            self._sxt += (len(self._w) - 1) * x
        else:
            if not good:
                self._bad += 1
            self._dirty = True
            self._w.append(x)
        if len(self._w) < self.length:
            return None
        if self._bad:
            return (Decimal("NaN"), Decimal("NaN"), Decimal("NaN"))
        if self._dirty:
            self._sx = self._sxx = self._sxt = Decimal("0")
            for i, v in enumerate(self._w):
                self._sx += v
                self._sxx += v * v
                self._sxt += i * v
            self._dirty = False
        n = self.length
        denom = n * self._stt - self._st * self._st
        slope = (n * self._sxt - self._sx * self._st) / denom
        intercept = (self._sx - slope * self._st) / n
        sse = self._sxx - intercept * self._sx - slope * self._sxt
        if sse < 0:
            sse = Decimal("0")
        return intercept, slope, sse
