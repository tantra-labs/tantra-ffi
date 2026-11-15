# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Bollinger %B (volatility family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.volatility._stats import RollingStd
from tantra.types import to_decimal


@indicator("bollinger_percent_b", "volatility", warmup=lambda s: s.period)
class BollingerPercentB(Indicator):
    """Bollinger %B = (close - lower) / (upper - lower), SMA +/- mult population stdev.

    0 = at the lower band, 1 = at the upper band. Zero-width bands (flat window) return 0.5."""

    def __init__(self, period: int = 20, mult: Decimal = Decimal("2")) -> None:
        self.period = _check(period)
        mult = to_decimal(mult)
        if mult < 0:
            raise ValueError("mult must be >= 0")
        self.mult = mult
        self._s = RollingStd(period)

    def update(self, close: Decimal) -> Decimal | None:
        close = to_decimal(close)
        r = self._s.update(close)
        if r is None:
            return None
        mean, sd = r
        width = 2 * self.mult * sd
        if width == 0:
            return Decimal("0.5")
        return (close - (mean - self.mult * sd)) / width
