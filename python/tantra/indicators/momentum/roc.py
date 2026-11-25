# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

# mirror: kernel-verbatim port (gap 0006)
from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator("roc", "momentum", warmup=lambda s: s.length + 1)
class Roc(Indicator):
    """Rate of change (TradingView): 100 * (x - x[length]) / x[length], in percent.

    A zero base value gives 0.
    """

    def __init__(self, length: int = 9) -> None:
        self.length = _check(length)
        self._w: deque[Decimal] = deque(maxlen=length + 1)

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        self._w.append(x)
        if len(self._w) < self.length + 1:
            return None
        base = self._w[0]
        return Decimal(100) * (x - base) / base if base != 0 else Decimal(0)
