# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Volume-weighted moving average."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator("vwma", "moving_average", inputs=("close", "volume"), warmup=lambda s: s.period)
class Vwma(Indicator):
    """VWMA: sum(close*volume) / sum(volume) over ``period`` bars.

    Convention: if the window's total volume is 0, returns the latest close.
    """

    def __init__(self, period: int = 20) -> None:
        self.period = _check(period)
        self._cv: deque[Decimal] = deque(maxlen=period)
        self._vol: deque[Decimal] = deque(maxlen=period)

    def update(self, close: Decimal, volume: Decimal) -> Decimal | None:
        close, volume = to_decimal(close), to_decimal(volume)
        self._cv.append(close * volume)
        self._vol.append(volume)
        if len(self._cv) < self.period:
            return None
        num = sum(self._cv, Decimal("0"))
        vol = sum(self._vol, Decimal("0"))
        return close if vol == 0 else num / vol
