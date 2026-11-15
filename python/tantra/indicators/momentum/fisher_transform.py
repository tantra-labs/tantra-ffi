# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@dataclass(slots=True)
class FisherValue:
    fisher: Decimal
    trigger: Decimal


@indicator(
    "fisher_transform",
    "momentum",
    inputs=("high", "low"),
    outputs=("fisher", "trigger"),
    warmup=lambda s: s.length,
)
class FisherTransform(Indicator):
    """Fisher Transform (TradingView): fisher = 0.5*ln((1+v)/(1-v)) + 0.5*fisher[1]; trigger = fisher[1].

    v = clamp(0.66*((hl2 - low_n)/max(high_n - low_n, 0.001) - 0.5) + 0.67*v[1], -0.999, 0.999), hl2 = (high+low)/2,
    high_n/low_n the extremes of hl2 over ``length``. Previous values start at 0 (Pine ``nz``).
    """

    def __init__(self, length: int = 9) -> None:
        self.length = _check(length)
        self._w: deque[Decimal] = deque(maxlen=length)
        self._v = Decimal("0")
        self._fish = Decimal("0")

    def update(self, high: Decimal, low: Decimal) -> FisherValue | None:
        high, low = to_decimal(high), to_decimal(low)
        hl2 = (high + low) / 2
        self._w.append(hl2)
        if len(self._w) < self.length:
            return None
        hi, lo = max(self._w), min(self._w)
        v = Decimal("0.66") * ((hl2 - lo) / max(hi - lo, Decimal("0.001")) - Decimal("0.5")) + Decimal("0.67") * self._v
        v = Decimal("0.999") if v > Decimal("0.99") else Decimal("-0.999") if v < Decimal("-0.99") else v
        fish = Decimal("0.5") * ((Decimal("1") + v) / (Decimal("1") - v)).ln() + Decimal("0.5") * self._fish
        trigger, self._v, self._fish = self._fish, v, fish
        return FisherValue(fish, trigger)
