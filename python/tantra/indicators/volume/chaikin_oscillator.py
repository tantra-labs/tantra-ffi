# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Chaikin oscillator."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average import Ema
from tantra.indicators.volume.accumulation_distribution import AccumulationDistribution
from tantra.types import to_decimal


@indicator(
    "chaikin_oscillator",
    "volume",
    inputs=("high", "low", "close", "volume"),
    warmup=lambda s: max(s.fast, s.slow),
)
class ChaikinOscillator(Indicator):
    """Chaikin oscillator: EMA(A/D line, fast) - EMA(A/D line, slow), SMA-seeded EMAs (TradingView)."""

    def __init__(self, fast: int = 3, slow: int = 10) -> None:
        self.fast, self.slow = _check(fast), _check(slow)
        self._ad = AccumulationDistribution()
        self._f, self._s = Ema(fast), Ema(slow)

    def update(
        self, high: Decimal, low: Decimal, close: Decimal, volume: Decimal
    ) -> Decimal | None:
        high, low, close, volume = (
            to_decimal(high),
            to_decimal(low),
            to_decimal(close),
            to_decimal(volume),
        )
        ad = self._ad.update(high, low, close, volume)
        f, s = self._f.update(ad), self._s.update(ad)
        return None if f is None or s is None else f - s
