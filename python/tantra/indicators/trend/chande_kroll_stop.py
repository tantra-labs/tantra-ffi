# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Chande Kroll stop."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._atr import _Atr as Atr  # stand-in for volatility Atr (ex 0006 later wave)
from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class ChandeKrollStopValue:
    long_stop: Decimal
    short_stop: Decimal


@indicator(
    "chande_kroll_stop",
    "trend",
    inputs=("high", "low", "close"),
    outputs=("long_stop", "short_stop"),
    warmup=lambda s: s.p + s.q - 1,
)
class ChandeKrollStop(Indicator):
    """Chande Kroll stop: long_stop = highest(highest(high,p) - x*ATR(p), q);
    short_stop = lowest(lowest(low,p) + x*ATR(p), q). ATR is Wilder (first TR = high-low).

    Note TradingView labels these two series the other way round ("stop short" is the higher one).
    """

    def __init__(self, p: int = 10, x: Decimal = Decimal("1"), q: int = 9) -> None:
        self.p, self.q = _check(p), _check(q)
        x = to_decimal(x)
        if x <= 0:
            raise ValueError(f"x must be > 0, got {x}")
        self.x = x
        self._atr = Atr(p, include_first_bar=True)
        self._h: deque[Decimal] = deque(maxlen=p)
        self._l: deque[Decimal] = deque(maxlen=p)
        self._hs: deque[Decimal] = deque(maxlen=q)
        self._ls: deque[Decimal] = deque(maxlen=q)

    def update(self, high: Decimal, low: Decimal, close: Decimal) -> ChandeKrollStopValue | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        self._h.append(high)
        self._l.append(low)
        atr = self._atr.update(high, low, close)
        if atr is None:
            return None
        self._hs.append(max(self._h) - self.x * atr)
        self._ls.append(min(self._l) + self.x * atr)
        if len(self._hs) < self.q:
            return None
        return ChandeKrollStopValue(max(self._hs), min(self._ls))
