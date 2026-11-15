# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Advance/Decline line (breadth family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.types import to_decimal


@indicator(
    "advance_decline_line",
    "breadth",
    inputs=("advances", "declines"),
    warmup=lambda s: 1,
)
class AdvanceDeclineLine(Indicator):
    """Cumulative sum of (advances - declines); starts at the first bar's net advances."""

    def __init__(self) -> None:
        self._total = Decimal("0")

    def update(self, advances: Decimal, declines: Decimal) -> Decimal:
        advances, declines = to_decimal(advances), to_decimal(declines)
        self._total += advances - declines
        return self._total
