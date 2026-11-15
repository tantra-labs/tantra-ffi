# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Rolling Fibonacci retracement levels (support_resistance family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class FibonacciRetracementValue:
    l0: Decimal
    l236: Decimal
    l382: Decimal
    l500: Decimal
    l618: Decimal
    l786: Decimal
    l1000: Decimal


_RATIOS = (
    Decimal("0"),
    Decimal("0.236"),
    Decimal("0.382"),
    Decimal("0.5"),
    Decimal("0.618"),
    Decimal("0.786"),
    Decimal("1"),
)


@indicator(
    "fibonacci_retracement",
    "support_resistance",
    inputs=("high", "low"),
    outputs=("l0", "l236", "l382", "l500", "l618", "l786", "l1000"),
    warmup=lambda s: s.length,
)
class FibonacciRetracement(Indicator):
    """Fibonacci levels of the rolling ``length``-bar range: level = highest high - range * ratio.

    l0 is the highest high, l1000 the lowest low (window includes the current bar).
    """

    def __init__(self, length: int = 100) -> None:
        self.length = _check(length)
        self._h: deque[Decimal] = deque(maxlen=length)
        self._l: deque[Decimal] = deque(maxlen=length)

    def update(self, high: Decimal, low: Decimal) -> FibonacciRetracementValue | None:
        high, low = to_decimal(high), to_decimal(low)
        self._h.append(high)
        self._l.append(low)
        if len(self._h) < self.length:
            return None
        hi, lo = max(self._h), min(self._l)
        rng = hi - lo
        return FibonacciRetracementValue(*(hi - rng * r for r in _RATIOS))
