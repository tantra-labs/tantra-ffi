# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

# mirror: kernel-verbatim port (gap 0006)
from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average.averages import Sma
from tantra.types import to_decimal


@indicator(
    "awesome_oscillator",
    "momentum",
    inputs=("high", "low"),
    warmup=lambda s: max(s.fast, s.slow),
)
class AwesomeOscillator(Indicator):
    """Awesome Oscillator: SMA(fast) - SMA(slow) of the median price (high + low) / 2."""

    def __init__(self, fast: int = 5, slow: int = 34) -> None:
        self.fast = _check(fast)
        self.slow = _check(slow)
        self._f, self._s = Sma(fast), Sma(slow)

    def update(self, high: Decimal, low: Decimal) -> Decimal | None:
        high, low = to_decimal(high), to_decimal(low)
        m = (high + low) / 2
        f, s = self._f.update(m), self._s.update(m)
        return f - s if f is not None and s is not None else None
