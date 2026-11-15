# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Average true range (volatility family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator(
    "atr",
    "volatility",
    inputs=("high", "low", "close"),
    warmup=lambda s: s.period + (0 if s.include_first_bar else 1),
)
class Atr(Indicator):
    """Wilder ATR. By default the first true range needs a previous close, so the first
    value appears after ``period + 1`` bars; ``include_first_bar=True`` (Jesse) uses
    high - low for the first bar, giving the first value after ``period`` bars."""

    def __init__(self, period: int = 14, include_first_bar: bool = False) -> None:
        self.period = _check(period)
        self.include_first_bar = include_first_bar
        self._prev_close: Decimal | None = None
        self._trs: list[Decimal] = []
        self.value: Decimal | None = None

    def update(self, high: Decimal, low: Decimal, close: Decimal) -> Decimal | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        prev, self._prev_close = self._prev_close, close
        if prev is None:
            if not self.include_first_bar:
                return None
            tr = high - low
        else:
            tr = max(high - low, abs(high - prev), abs(low - prev))
        if self.value is not None:
            self.value = (self.value * (self.period - 1) + tr) / self.period
        else:
            self._trs.append(tr)
            if len(self._trs) == self.period:
                self.value = sum(self._trs, Decimal("0")) / self.period
        return self.value
