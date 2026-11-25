# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Accumulation/distribution line."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.types import to_decimal


def clv_volume(high: Decimal, low: Decimal, close: Decimal, volume: Decimal) -> Decimal:
    """Money-flow volume ``((C-L)-(H-C))/(H-L) * V``; 0 when ``high == low``."""
    rng = high - low
    if rng == 0:
        return Decimal(0)
    return ((close - low) - (high - close)) / rng * volume


@indicator(
    "accumulation_distribution",
    "volume",
    inputs=("high", "low", "close", "volume"),
    warmup=lambda s: 1,
)
class AccumulationDistribution(Indicator):
    """Accumulation/distribution: cumulative close-location-value times volume (CLV = 0 when high == low)."""

    def __init__(self) -> None:
        self.value = Decimal(0)

    def update(
        self, high: Decimal, low: Decimal, close: Decimal, volume: Decimal
    ) -> Decimal:
        high, low, close, volume = (
            to_decimal(high),
            to_decimal(low),
            to_decimal(close),
            to_decimal(volume),
        )
        self.value += clv_volume(high, low, close, volume)
        return self.value
