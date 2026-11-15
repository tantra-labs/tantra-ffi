# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Ease of movement."""
# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average import Sma
from tantra.types import to_decimal


@indicator(
    "ease_of_movement",
    "volume",
    inputs=("high", "low", "close", "volume"),
    warmup=lambda s: s.period + 1,
)
class EaseOfMovement(Indicator):
    """Ease of movement (TradingView): SMA(divisor * change(hl2) * (high-low) / volume, n); a bar with zero volume contributes 0."""

    def __init__(self, period: int = 14, divisor: Decimal = Decimal("10000")) -> None:
        self.period = _check(period)
        divisor = to_decimal(divisor)
        if divisor <= 0:
            raise ValueError(f"divisor must be > 0, got {divisor}")
        self.divisor = divisor
        self._sma = Sma(period)
        self._prev: Decimal | None = None

    def update(self, high: Decimal, low: Decimal, close: Decimal, volume: Decimal) -> Decimal | None:
        high, low, close, volume = (
            to_decimal(high),
            to_decimal(low),
            to_decimal(close),
            to_decimal(volume),
        )
        hl2 = (high + low) / 2
        prev, self._prev = self._prev, hl2
        if prev is None:
            return None
        eom = self.divisor * (hl2 - prev) * (high - low) / volume if volume != 0 else Decimal("0")
        return self._sma.update(eom)
