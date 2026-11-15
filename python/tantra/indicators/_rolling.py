# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Private rolling helpers (kernel ``_rolling`` mirror): exact ``Decimal`` running sums,
an O(1) least-squares fit, and exact O(1)-per-update window moments (mean/variance/std
and pair means/variances/covariance)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from decimal import Decimal
from typing import NamedTuple

from tantra.indicators._util import check as _check
from tantra.types import to_decimal

_LARGE = Decimal("1e150")
_NAN = Decimal("NaN")


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


class Moments(NamedTuple):
    mean: Decimal
    variance: Decimal
    std: Decimal


_NAN_RAW3 = (_NAN, _NAN, _NAN)
_NAN_MOMENTS = Moments(_NAN, _NAN, _NAN)


class RollingMoments:
    """Mean / variance / std over the last ``period`` values, O(1) amortised per update.

    Exact under ``Decimal`` (no Welford needed): the window sum and sum of squares are
    maintained incrementally and rebuilt exactly from the window whenever a non-finite or
    ``|v| > 1e150`` value leaves it. While such a value is in the window every moment is
    NaN, so it can never poison later results. ``ddof`` follows numpy (0 = population);
    a window of identical values reports variance exactly 0.

    ``update_raw`` returns a plain ``(mean, variance, std)`` tuple; ``update`` wraps it
    in a :class:`Moments`.
    """

    def __init__(self, period: int, ddof: int = 0) -> None:
        self.period = _check(period)
        if ddof < 0 or period - ddof < 1:
            raise ValueError(
                f"ddof must satisfy 0 <= ddof < period, got ddof={ddof}, period={period}"
            )
        self.ddof = ddof
        self._w: deque[Decimal] = deque(maxlen=period)
        self._sum = Decimal("0")
        self._sum2 = Decimal("0")
        self._bad = 0  # unsafe (non-finite or huge) values currently in the window
        self._dirty = False  # running totals not trustworthy; rebuild once the window is safe
        self._d = period - ddof

    def update_raw(self, x: Decimal) -> tuple[Decimal, Decimal, Decimal] | None:
        """``(mean, variance, std)`` as a plain tuple (``None`` during warm-up)."""
        x = to_decimal(x)
        good = x.is_finite() and abs(x) <= _LARGE
        w = self._w
        full = len(w) == self.period
        if full and not (w[0].is_finite() and abs(w[0]) <= _LARGE):
            self._bad -= 1
        if good and not self._dirty and not self._bad:
            if full:
                old = w[0]
                self._sum -= old
                self._sum2 -= old * old
            w.append(x)
            self._sum += x
            self._sum2 += x * x
        else:
            if not good:
                self._bad += 1
            self._dirty = True
            w.append(x)
        if len(w) < self.period:
            return None
        if self._bad:
            return _NAN_RAW3
        if self._dirty:  # exact rebuild once the last unsafe value has left
            self._sum = self._sum2 = Decimal("0")
            for v in w:
                self._sum += v
                self._sum2 += v * v
            self._dirty = False
        n = self.period
        mean = self._sum / n
        var = (self._sum2 - self._sum * self._sum / n) / self._d
        if var < 0:
            var = Decimal("0")
        return mean, var, var.sqrt()

    def update(self, x: Decimal) -> Moments | None:
        r = self.update_raw(x)
        return None if r is None else Moments(*r)


class PairMoments(NamedTuple):
    mean_x: Decimal
    mean_y: Decimal
    var_x: Decimal
    var_y: Decimal
    cov: Decimal


_NAN_RAW5 = (_NAN, _NAN, _NAN, _NAN, _NAN)
_NAN_PAIR = PairMoments(_NAN, _NAN, _NAN, _NAN, _NAN)


class RollingPairMoments:
    """Means, variances and covariance of (x, y) over the last ``period`` pairs, O(1) amortised.

    Exact under ``Decimal``: sliding sums of x, y, x*x, y*y and x*y, rebuilt exactly when a
    pair with a non-finite or ``|v| > 1e150`` component leaves the window (while such a pair
    is inside, every field is NaN). Divisors are ``period - ddof`` (numpy convention); a
    window constant in x (or y) has exactly zero variance and covariance.

    ``update_raw`` returns a plain ``(mean_x, mean_y, var_x, var_y, cov)`` tuple; ``update``
    wraps it in a :class:`PairMoments`.
    """

    def __init__(self, period: int, ddof: int = 0) -> None:
        self.period = _check(period)
        if ddof < 0 or period - ddof < 1:
            raise ValueError(
                f"ddof must satisfy 0 <= ddof < period, got ddof={ddof}, period={period}"
            )
        self.ddof = ddof
        self._wx: deque[Decimal] = deque(maxlen=period)
        self._wy: deque[Decimal] = deque(maxlen=period)
        self._sx = self._sy = Decimal("0")
        self._sx2 = self._sy2 = self._sxy = Decimal("0")
        self._bad = 0
        self._dirty = False
        self._d = period - ddof

    @staticmethod
    def _unsafe(x: Decimal, y: Decimal) -> bool:
        return not (
            x.is_finite() and abs(x) <= _LARGE and y.is_finite() and abs(y) <= _LARGE
        )

    def update_raw(
        self, x: Decimal, y: Decimal
    ) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal] | None:
        """``(mean_x, mean_y, var_x, var_y, cov)`` as a plain tuple (``None`` during warm-up)."""
        x, y = to_decimal(x), to_decimal(y)
        good = not self._unsafe(x, y)
        wx, wy = self._wx, self._wy
        full = len(wx) == self.period
        if full and self._unsafe(wx[0], wy[0]):
            self._bad -= 1
        if good and not self._dirty and not self._bad:
            if full:
                ox, oy = wx[0], wy[0]
                self._sx -= ox
                self._sy -= oy
                self._sx2 -= ox * ox
                self._sy2 -= oy * oy
                self._sxy -= ox * oy
            wx.append(x)
            wy.append(y)
            self._sx += x
            self._sy += y
            self._sx2 += x * x
            self._sy2 += y * y
            self._sxy += x * y
        else:
            if not good:
                self._bad += 1
            self._dirty = True
            wx.append(x)
            wy.append(y)
        if len(wx) < self.period:
            return None
        if self._bad:
            return _NAN_RAW5
        if self._dirty:  # exact rebuild once the last unsafe pair has left
            self._sx = self._sy = self._sx2 = self._sy2 = self._sxy = Decimal("0")
            for a, b in zip(wx, wy):
                self._sx += a
                self._sy += b
                self._sx2 += a * a
                self._sy2 += b * b
                self._sxy += a * b
            self._dirty = False
        n = self.period
        d = self._d
        mx, my = self._sx / n, self._sy / n
        vx = (self._sx2 - self._sx * self._sx / n) / d
        vy = (self._sy2 - self._sy * self._sy / n) / d
        if vx < 0:
            vx = Decimal("0")
        if vy < 0:
            vy = Decimal("0")
        cov = (self._sxy - self._sx * self._sy / n) / d
        return mx, my, vx, vy, cov

    def update(self, x: Decimal, y: Decimal) -> PairMoments | None:
        r = self.update_raw(x, y)
        return None if r is None else PairMoments(*r)
