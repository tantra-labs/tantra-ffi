# wheel surface (ex 0006 / market 0007): Decimal-canonical ADR% indicator

"""Average Daily Range Percent (volatility family)."""

from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal

_HUNDRED = Decimal(100)
_ONE = Decimal(1)
_ZERO = Decimal(0)


@indicator(
    "adr_pct",
    "volatility",
    inputs=("high", "low"),
    warmup=lambda s: s.period,
)
class AdrPct(Indicator):
    """Average Daily Range %: ``100 * (mean(high / low) - 1)`` over ``period`` bars."""

    def __init__(self, period: int = 20) -> None:
        self.period = _check(period)
        self._ratios: deque[Decimal] = deque(maxlen=period)
        self.value: Decimal | None = None

    def update(self, high: Decimal, low: Decimal) -> Decimal | None:  # type: ignore[override]
        high, low = to_decimal(high), to_decimal(low)
        if low <= _ZERO:
            return None
        self._ratios.append(high / low)
        if len(self._ratios) < self.period:
            return None
        mean_ratio = sum(self._ratios, _ZERO) / Decimal(self.period)
        self.value = (mean_ratio - _ONE) * _HUNDRED
        return self.value
