# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Wilder ATR stand-in (unregistered).

The kernel's ``Atr`` belongs to the volatility family, which ships in a later ex 0006
wave; ``supertrend`` and ``chande_kroll_stop`` (trend) need it now. This private copy is
deliberately NOT registered, so the later volatility wave can register the real ``atr``.
"""
# stand-in for tantra-examples/_kernel/indicators/volatility/atr.py (ex 0006 later wave)
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._util import check as _check
from tantra.indicators.moving_average.averages import Rma
from tantra.types import to_decimal


class _Atr:
    """Wilder ATR: TR = max(high-low, |high-pc|, |low-pc|), smoothed by Wilder RMA.

    ``include_first_bar=True`` seeds the very first TR as ``high - low`` (there is no
    previous close), matching the kernel's ``Atr(period, include_first_bar=True)``.
    """

    def __init__(self, period: int = 14, include_first_bar: bool = False) -> None:
        self.period = _check(period)
        self.include_first_bar = include_first_bar
        self._prev_close: Decimal | None = None
        self._smooth = Rma(period)

    def update(self, high: Decimal, low: Decimal, close: Decimal) -> Decimal | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        if self._prev_close is None:
            self._prev_close = close
            if not self.include_first_bar:
                return None
            tr = high - low
        else:
            pc = self._prev_close
            self._prev_close = close
            tr = max(high - low, abs(high - pc), abs(low - pc))
        return self._smooth.update(tr)
