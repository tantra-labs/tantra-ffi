# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Bollinger bands (volatility family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._rolling import RollingMoments
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class BollingerValue:
    upper: Decimal
    middle: Decimal
    lower: Decimal


@indicator(
    "bollinger",
    "volatility",
    outputs=("upper", "middle", "lower"),
    warmup=lambda s: s.period,
)
class Bollinger(Indicator):
    """Bands at ``mult`` (upper) and ``mult_lower`` (default ``mult``) population
    standard deviations around the SMA."""

    def __init__(
        self,
        period: int = 20,
        mult: Decimal = Decimal(2),
        mult_lower: Decimal | None = None,
    ) -> None:
        self.period = _check(period)
        mult = to_decimal(mult)
        self.mult_lower = mult if mult_lower is None else to_decimal(mult_lower)
        if mult < 0 or self.mult_lower < 0:
            raise ValueError("band multipliers must be >= 0")
        self.mult = mult
        self._m = RollingMoments(period)
        self._update = self._m.update_raw

    def update(self, x: Decimal) -> BollingerValue | None:
        r = self._update(x)
        if r is None:
            return None
        mean, _, std = r
        return BollingerValue(
            mean + self.mult * std, mean, mean - self.mult_lower * std
        )
