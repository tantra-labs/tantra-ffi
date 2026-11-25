# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

# mirror: kernel-verbatim port (gap 0006)
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.momentum.rsi import Rsi
from tantra.indicators.moving_average.averages import Sma
from tantra.types import to_decimal


@dataclass(slots=True)
class StochRsiValue:
    k: Decimal
    d: Decimal


@indicator(
    "stoch_rsi",
    "momentum",
    outputs=("k", "d"),
    warmup=lambda s: s.rsi_length + s.stoch_length + s.k_smooth + s.d_smooth - 2,
)
class StochRsi(Indicator):
    """Stochastic RSI (TradingView): stochastic of Wilder RSI over ``stoch_length``, K = SMA(raw, k_smooth), D = SMA(K, d_smooth).

    raw = 100 * (rsi - min rsi) / (max rsi - min rsi); a flat RSI window gives 0.
    """

    def __init__(
        self,
        rsi_length: int = 14,
        stoch_length: int = 14,
        k_smooth: int = 3,
        d_smooth: int = 3,
    ) -> None:
        self.rsi_length = _check(rsi_length)
        self.stoch_length = _check(stoch_length)
        self.k_smooth = _check(k_smooth)
        self.d_smooth = _check(d_smooth)
        self._rsi = Rsi(rsi_length)
        self._w: deque[Decimal] = deque(maxlen=stoch_length)
        self._k, self._d = Sma(k_smooth), Sma(d_smooth)

    def update(self, close: Decimal) -> StochRsiValue | None:
        close = to_decimal(close)
        r = self._rsi.update(close)
        if r is None:
            return None
        self._w.append(r)
        if len(self._w) < self.stoch_length:
            return None
        hi, lo = max(self._w), min(self._w)
        k = self._k.update(
            Decimal(100) * (r - lo) / (hi - lo) if hi != lo else Decimal(0)
        )
        d = self._d.update(k) if k is not None else None
        if k is None or d is None:
            return None
        return StochRsiValue(k, d)
