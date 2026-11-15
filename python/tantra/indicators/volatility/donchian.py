# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Donchian channel (volatility family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class DonchianValue:
    upper: Decimal
    lower: Decimal


@indicator(
    "donchian",
    "volatility",
    inputs=("high", "low"),
    outputs=("upper", "lower"),
    warmup=lambda s: s.period,
)
class Donchian(Indicator):
    """Highest high / lowest low over the last ``period`` bars, including the current one."""

    def __init__(self, period: int = 20) -> None:
        self.period = _check(period)
        self._h: deque[Decimal] = deque(maxlen=period)
        self._l: deque[Decimal] = deque(maxlen=period)

    def update(self, high: Decimal, low: Decimal) -> DonchianValue | None:
        high, low = to_decimal(high), to_decimal(low)
        self._h.append(high)
        self._l.append(low)
        if len(self._h) < self.period:
            return None
        return DonchianValue(max(self._h), min(self._l))
