# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Put/Call ratio (breadth family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average.averages import Sma
from tantra.types import to_decimal


@indicator(
    "put_call_ratio",
    "breadth",
    inputs=("put_volume", "call_volume"),
    warmup=lambda s: s.smoothing,
)
class PutCallRatio(Indicator):
    """SMA(smoothing) of the per-bar put_volume / call_volume; smoothing=1 is the raw ratio.

    Convention: bars with call_volume <= 0 count as neutral 1.0.
    """

    def __init__(self, smoothing: int = 1) -> None:
        self.smoothing = _check(smoothing)
        self._sma = Sma(smoothing)

    def update(self, put_volume: Decimal, call_volume: Decimal) -> Decimal | None:
        put_volume, call_volume = to_decimal(put_volume), to_decimal(call_volume)
        return self._sma.update(put_volume / call_volume if call_volume > 0 else Decimal("1"))
