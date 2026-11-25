# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Volatility stop (volatility family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.volatility.atr import Atr
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class VolatilityStopValue:
    value: Decimal
    direction: Decimal


@indicator(
    "volatility_stop",
    "volatility",
    inputs=("high", "low", "close"),
    outputs=("value", "direction"),
    warmup=lambda s: s.length,
)
class VolatilityStop(Indicator):
    """ATR trailing volatility stop (TradingView 'Volatility Stop'); direction +1 = uptrend (stop below), -1 = downtrend.

    Stop trails the extreme close since the last flip by ``mult * ATR`` (Wilder ATR, first TR = high - low);
    it only ratchets in the trend direction and flips when close crosses it. Starts as an uptrend at the first ATR bar."""

    def __init__(self, length: int = 20, mult: Decimal = Decimal(2)) -> None:
        self.length = _check(length)
        mult = to_decimal(mult)
        if mult <= 0:
            raise ValueError("mult must be > 0")
        self.mult = mult
        self._atr = Atr(length, include_first_bar=True)
        self._started = False
        self._up = True
        self._max = self._min = self._stop = Decimal(0)

    def update(
        self, high: Decimal, low: Decimal, close: Decimal
    ) -> VolatilityStopValue | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        atr = self._atr.update(high, low, close)
        if atr is None:
            return None
        m = self.mult * atr
        if not self._started:
            self._started = True
            self._max = self._min = close
            self._stop = close - m  # uptrend seed: below the close by mult * ATR
        self._max, self._min = max(self._max, close), min(self._min, close)
        if self._up:
            self._stop = max(self._stop, self._max - m)
        else:
            self._stop = min(self._stop, self._min + m)
        up = close - self._stop >= 0
        if up != self._up:
            self._max = self._min = close
            self._stop = close - m if up else close + m
            self._up = up
        return VolatilityStopValue(self._stop, Decimal(1) if self._up else Decimal(-1))
