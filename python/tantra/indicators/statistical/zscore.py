# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Rolling z-score (statistical family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._rolling import RollingMoments
from tantra.types import to_decimal


@indicator("zscore", "statistical", warmup=lambda s: s.length)
class ZScore(Indicator):
    """(close - SMA) / population stdev over ``length`` bars (like ta.stdev, biased).

    0.0 if the stdev is 0.
    """

    def __init__(self, length: int = 20) -> None:
        if length < 2:
            raise ValueError(f"length must be >= 2, got {length}")
        self.length = length
        self._m = RollingMoments(length)
        self._update = self._m.update_raw

    def update(self, close: Decimal) -> Decimal | None:
        close = to_decimal(close)
        r = self._update(close)
        if r is None:
            return None
        std = r[2]
        return (close - r[0]) / std if std > 0 else Decimal("0")
