# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

# mirror: kernel-verbatim port (gap 0006)
from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator("momentum", "momentum", warmup=lambda s: s.length + 1)
class Momentum(Indicator):
    """Momentum (TradingView): x - x[length] (price difference, not percent)."""

    def __init__(self, length: int = 10) -> None:
        self.length = _check(length)
        self._w: deque[Decimal] = deque(maxlen=length + 1)

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        self._w.append(x)
        return x - self._w[0] if len(self._w) == self.length + 1 else None
