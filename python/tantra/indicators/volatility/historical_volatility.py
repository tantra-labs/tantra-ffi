# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Historical volatility (volatility family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._india import TRADING_DAYS_PER_YEAR
from tantra.indicators._util import check as _check
from tantra.indicators.volatility._stats import RollingStd
from tantra.types import to_decimal


@indicator("historical_volatility", "volatility", warmup=lambda s: s.length + 1)
class HistoricalVolatility(Indicator):
    """Annualised historical volatility in percent: 100 * stdev(ln(close/prev), length) * sqrt(periods_per_year).

    Population stdev of log returns. ``periods_per_year`` defaults to 252 NSE/BSE trading days
    (pass bars per year for intraday data). A non-positive price yields a 0.0 log return."""

    def __init__(
        self,
        length: int = 10,
        periods_per_year: Decimal = Decimal(TRADING_DAYS_PER_YEAR),
    ) -> None:
        self.length = _check(length)
        periods_per_year = to_decimal(periods_per_year)
        if periods_per_year <= 0:
            raise ValueError("periods_per_year must be > 0")
        self.periods_per_year = periods_per_year
        self._prev: Decimal | None = None
        self._s = RollingStd(length)

    def update(self, close: Decimal) -> Decimal | None:
        close = to_decimal(close)
        prev, self._prev = self._prev, close
        if prev is None:
            return None
        r = (close / prev).ln() if close > 0 and prev > 0 else Decimal(0)
        out = self._s.update(r)
        return (
            None
            if out is None
            else Decimal(100) * out[1] * self.periods_per_year.sqrt()
        )
