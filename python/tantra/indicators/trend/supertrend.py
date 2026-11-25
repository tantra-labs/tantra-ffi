# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""SuperTrend."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators.volatility.atr import Atr
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class SupertrendValue:
    value: Decimal
    direction: (
        Decimal  # +1 uptrend (value is the lower band), -1 downtrend (upper band)
    )


@indicator(
    "supertrend",
    "trend",
    inputs=("high", "low", "close"),
    outputs=("value", "direction"),
    warmup=lambda s: s.atr_period,
)
class Supertrend(Indicator):
    """SuperTrend (TradingView): bands = hl2 -/+ factor*ATR (Wilder, first TR = high-low),
    ratcheted against the previous close; direction flips when close crosses the active band.

    The first value starts in a downtrend (TradingView convention), after ``atr_period`` bars.
    """

    def __init__(self, atr_period: int = 10, factor: Decimal = Decimal(3)) -> None:
        factor = to_decimal(factor)
        if factor <= 0:
            raise ValueError(f"factor must be > 0, got {factor}")
        self.atr_period, self.factor = atr_period, factor
        self._atr = Atr(atr_period, include_first_bar=True)
        self._prev_close: Decimal | None = None
        self._lower: Decimal | None = None  # mirror accommodation (gap 0006)
        self._upper: Decimal | None = None
        self._dir = 0

    def update(
        self, high: Decimal, low: Decimal, close: Decimal
    ) -> SupertrendValue | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        pc, self._prev_close = self._prev_close, close
        atr = self._atr.update(high, low, close)
        if atr is None:
            return None
        mid = (high + low) / 2
        lower, upper = mid - self.factor * atr, mid + self.factor * atr
        if self._dir == 0:
            self._dir = -1
        else:
            if (
                self._lower is not None
                and pc is not None
                and not (lower > self._lower or pc < self._lower)
            ):
                lower = self._lower
            if (
                self._upper is not None
                and pc is not None
                and not (upper < self._upper or pc > self._upper)
            ):
                upper = self._upper
            if self._dir == -1:
                self._dir = 1 if close > upper else -1
            else:
                self._dir = -1 if close < lower else 1
        self._lower, self._upper = lower, upper
        return SupertrendValue(
            lower if self._dir == 1 else upper, to_decimal(self._dir)
        )
