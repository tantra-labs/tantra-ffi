# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Rolling standard deviation (volatility family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.volatility._stats import RollingStd


@indicator("standard_deviation", "volatility", warmup=lambda s: s.length)
class StandardDeviation(Indicator):
    """Population (biased, divide by n) standard deviation of close over ``length`` bars (TradingView ta.stdev)."""

    def __init__(self, length: int = 5) -> None:
        self.length = _check(length)
        self._s = RollingStd(length)

    def update(self, close: Decimal) -> Decimal | None:
        r = self._s.update(close)
        return None if r is None else r[1]
