# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)
from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._rolling import RollingSum
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator("cmo", "momentum", warmup=lambda s: s.length + 1)
class ChandeMomentum(Indicator):
    """Chande Momentum Oscillator (TradingView): 100 * (sum of gains - sum of losses) / (sum of gains + sum of losses) over ``length`` changes.

    Simple sums (no Wilder smoothing); range -100..100. No movement at all gives 0.
    """

    def __init__(self, length: int = 9) -> None:
        self.length = _check(length)
        self._prev: Decimal | None = None
        self._up = RollingSum(length)
        self._dn = RollingSum(length)

    def update(self, close: Decimal) -> Decimal | None:
        close = to_decimal(close)
        prev, self._prev = self._prev, close
        if prev is None:
            return None
        d = close - prev
        up = self._up.update(d if d > 0 else Decimal("0"))
        dn = self._dn.update(-d if d < 0 else Decimal("0"))
        if up is None or dn is None:
            return None
        return Decimal("100") * (up - dn) / (up + dn) if up + dn != 0 else Decimal("0")
