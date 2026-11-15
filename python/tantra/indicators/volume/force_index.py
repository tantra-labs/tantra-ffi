# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Force index."""
# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average import Ema
from tantra.types import to_decimal


@indicator("force_index", "volume", inputs=("close", "volume"), warmup=lambda s: s.period + 1)
class ForceIndex(Indicator):
    """Elder force index: EMA(change(close) * volume, n), SMA-seeded; first value after ``period + 1`` bars."""

    def __init__(self, period: int = 13) -> None:
        self.period = _check(period)
        self._ema = Ema(period)
        self._prev: Decimal | None = None

    def update(self, close: Decimal, volume: Decimal) -> Decimal | None:
        close, volume = to_decimal(close), to_decimal(volume)
        prev, self._prev = self._prev, close
        if prev is None:
            return None
        return self._ema.update((close - prev) * volume)
