# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Aroon."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class AroonValue:
    up: Decimal
    down: Decimal
    oscillator: Decimal


@indicator(
    "aroon",
    "trend",
    inputs=("high", "low"),
    outputs=("up", "down", "oscillator"),
    warmup=lambda s: s.length + 1,
)
class Aroon(Indicator):
    """Aroon over the last ``length + 1`` bars: up = 100*(length - bars since highest high)/length
    (down likewise with lowest low), oscillator = up - down. Ties resolve to the most recent bar.
    """

    def __init__(self, length: int = 14) -> None:
        self.length = _check(length)
        self._h: deque[Decimal] = deque(maxlen=length + 1)
        self._l: deque[Decimal] = deque(maxlen=length + 1)

    def update(self, high: Decimal, low: Decimal) -> AroonValue | None:
        high, low = to_decimal(high), to_decimal(low)
        self._h.append(high)
        self._l.append(low)
        if len(self._h) <= self.length:
            return None
        n = self.length
        hh, ll = max(self._h), min(self._l)
        since_h = next(i for i, v in enumerate(reversed(self._h)) if v == hh)
        since_l = next(i for i, v in enumerate(reversed(self._l)) if v == ll)
        up, down = Decimal("100") * (n - since_h) / n, Decimal("100") * (n - since_l) / n
        return AroonValue(up, down, up - down)
