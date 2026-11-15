# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Double exponential moving average."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average.averages import Ema
from tantra.types import to_decimal


@indicator("dema", "moving_average", warmup=lambda s: 2 * s.period - 1)
class Dema(Indicator):
    """DEMA = 2*EMA1 - EMA2 where EMA2 = EMA(EMA1); SMA-seeded EMAs, alpha = 2/(n+1)."""

    def __init__(self, period: int = 9) -> None:
        self.period = _check(period)
        self._e1, self._e2 = Ema(period), Ema(period)

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        e1 = self._e1.update(x)
        if e1 is None:
            return None
        e2 = self._e2.update(e1)
        return None if e2 is None else 2 * e1 - e2
