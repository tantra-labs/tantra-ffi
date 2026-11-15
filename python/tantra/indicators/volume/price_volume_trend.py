# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Price volume trend."""
# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.types import to_decimal


@indicator("price_volume_trend", "volume", inputs=("close", "volume"), warmup=lambda s: 1)
class PriceVolumeTrend(Indicator):
    """Price volume trend: cumulative (close - prev_close) / prev_close * volume (first bar = 0; term 0 if prev_close is 0)."""

    def __init__(self) -> None:
        self._prev: Decimal | None = None
        self.value = Decimal("0")

    def update(self, close: Decimal, volume: Decimal) -> Decimal:
        close, volume = to_decimal(close), to_decimal(volume)
        if self._prev:
            self.value += (close - self._prev) / self._prev * volume
        self._prev = close
        return self.value
