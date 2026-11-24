# wheel surface (ex 0006 / market 0007): Decimal-canonical Chandelier Exit indicator

"""Chandelier Exit (volatility family)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.volatility.atr import Atr
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class ChandelierExitValue:
    long_stop: Decimal
    short_stop: Decimal


@indicator(
    "chandelier_exit",
    "volatility",
    inputs=("high", "low", "close"),
    outputs=("long_stop", "short_stop"),
    warmup=lambda s: s.period + (0 if s.include_first_bar else 1),
)
class ChandelierExit(Indicator):
    """Chandelier Exit: ``long_stop = highest_high(period) - mult * ATR``,
    ``short_stop = lowest_low(period) + mult * ATR``.

    Defaults match Wilder/Rust ``Atr`` seeding (``include_first_bar=True``).
    """

    def __init__(
        self,
        period: int = 22,
        mult: Decimal = Decimal(3),
        include_first_bar: bool = True,
    ) -> None:
        self.period = _check(period)
        mult = to_decimal(mult)
        if mult < 0:
            raise ValueError(f"mult must be >= 0, got {mult}")
        self.mult = mult
        self.include_first_bar = include_first_bar
        self._atr = Atr(period, include_first_bar=include_first_bar)
        self._h: deque[Decimal] = deque(maxlen=period)
        self._l: deque[Decimal] = deque(maxlen=period)
        self.value: ChandelierExitValue | None = None

    def update(  # type: ignore[override]
        self, high: Decimal, low: Decimal, close: Decimal
    ) -> ChandelierExitValue | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        self._h.append(high)
        self._l.append(low)
        atr = self._atr.update(high, low, close)
        if atr is None or len(self._h) < self.period:
            return None
        offset = self.mult * atr
        self.value = ChandelierExitValue(max(self._h) - offset, min(self._l) + offset)
        return self.value
