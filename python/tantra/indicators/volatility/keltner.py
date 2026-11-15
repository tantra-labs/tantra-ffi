# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Keltner channels (volatility family)."""
# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average.averages import Ema
from tantra.indicators.volatility.atr import Atr
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class KeltnerValue:
    upper: Decimal
    middle: Decimal
    lower: Decimal


@indicator(
    "keltner",
    "volatility",
    inputs=("high", "low", "close"),
    outputs=("upper", "middle", "lower"),
    warmup=lambda s: max(s.length, s.atr_length + 1),
)
class Keltner(Indicator):
    """Keltner channels: EMA(close, length) +/- mult * Wilder ATR(atr_length) (TradingView defaults).

    The EMA is SMA-seeded; ATR needs a previous close so it appears after ``atr_length + 1`` bars."""

    def __init__(
        self, length: int = 20, atr_length: int = 10, mult: Decimal = Decimal("2")
    ) -> None:
        self.length, self.atr_length = _check(length), _check(atr_length)
        mult = to_decimal(mult)
        if mult < 0:
            raise ValueError("mult must be >= 0")
        self.mult = mult
        self._ema, self._atr = Ema(length), Atr(atr_length)

    def update(self, high: Decimal, low: Decimal, close: Decimal) -> KeltnerValue | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        mid, atr = self._ema.update(close), self._atr.update(high, low, close)
        if mid is None or atr is None:
            return None
        return KeltnerValue(mid + self.mult * atr, mid, mid - self.mult * atr)
