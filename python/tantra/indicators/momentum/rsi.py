# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""RSI (momentum family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator("rsi", "momentum", warmup=lambda s: s.period + 1)
class Rsi(Indicator):
    """Wilder RSI; first value after ``period + 1`` inputs. A window with no losses is 100."""

    def __init__(self, period: int = 14) -> None:
        self.period = _check(period)
        self._prev: Decimal | None = None
        self._gains: list[Decimal] = []
        self._losses: list[Decimal] = []
        self._avg_gain = self._avg_loss = Decimal("0")
        self.value: Decimal | None = None

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        if self._prev is None:
            self._prev = x
            return None
        change, self._prev = x - self._prev, x
        gain, loss = max(change, Decimal("0")), max(-change, Decimal("0"))
        n = self.period
        if len(self._gains) < n:
            self._gains.append(gain)
            self._losses.append(loss)
            if len(self._gains) < n:
                return None
            self._avg_gain, self._avg_loss = sum(self._gains) / n, sum(self._losses) / n
        else:
            self._avg_gain = (self._avg_gain * (n - 1) + gain) / n
            self._avg_loss = (self._avg_loss * (n - 1) + loss) / n
        if self._avg_loss == 0:
            self.value = Decimal("100")
        else:
            self.value = Decimal("100") - Decimal("100") / (Decimal("1") + self._avg_gain / self._avg_loss)
        return self.value
