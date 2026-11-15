# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Williams fractals (support_resistance family)."""
# ruff: noqa: E741
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class WilliamsFractalsValue:
    up: Decimal
    down: Decimal


@indicator(
    "williams_fractals",
    "support_resistance",
    inputs=("high", "low"),
    outputs=("up", "down"),
    warmup=lambda s: 5,
)
class WilliamsFractals(Indicator):
    """5-bar Williams fractals, confirmed two bars late; flags 1.0/0.0 refer to bar t-2.

    up = 1.0 if high[t-2] is strictly greater than the two highs on each side;
    down = 1.0 if low[t-2] is strictly lower than the two lows on each side.
    """

    def __init__(self) -> None:
        self._h: deque[Decimal] = deque(maxlen=5)
        self._l: deque[Decimal] = deque(maxlen=5)

    def update(self, high: Decimal, low: Decimal) -> WilliamsFractalsValue | None:
        high, low = to_decimal(high), to_decimal(low)
        self._h.append(high)
        self._l.append(low)
        if len(self._h) < 5:
            return None
        h, l = self._h, self._l
        up = all(h[2] > h[i] for i in (0, 1, 3, 4))
        down = all(l[2] < l[i] for i in (0, 1, 3, 4))
        return WilliamsFractalsValue(
            Decimal("1") if up else Decimal("0"),
            Decimal("1") if down else Decimal("0"),
        )
