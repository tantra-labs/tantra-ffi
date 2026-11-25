# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Average directional index (Wilder)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average.averages import Rma
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class AdxValue:
    adx: Decimal
    plus_di: Decimal
    minus_di: Decimal


@indicator(
    "adx",
    "trend",
    inputs=("high", "low", "close"),
    outputs=("adx", "plus_di", "minus_di"),
    warmup=lambda s: s.di_length + s.adx_smoothing,
)
class Adx(Indicator):
    """ADX/DMI (TradingView ta.dmi): Wilder RMA of TR, +DM, -DM; DI = 100*RMA(DM)/RMA(TR);
    ADX = RMA(100*|+DI - -DI| / (+DI + -DI), adx_smoothing).

    RMAs are SMA-seeded. The first bar only supplies the previous high/low/close, so the DIs
    appear after ``di_length + 1`` bars and ADX after ``di_length + adx_smoothing`` bars.
    A zero DI sum counts as 1 in the denominator (DX = 0).
    """

    def __init__(self, di_length: int = 14, adx_smoothing: int = 14) -> None:
        self.di_length, self.adx_smoothing = _check(di_length), _check(adx_smoothing)
        self._tr, self._pdm, self._mdm = Rma(di_length), Rma(di_length), Rma(di_length)
        self._adx = Rma(adx_smoothing)
        self._prev: tuple[Decimal, Decimal, Decimal] | None = None

    def update(self, high: Decimal, low: Decimal, close: Decimal) -> AdxValue | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        prev, self._prev = self._prev, (high, low, close)
        if prev is None:
            return None
        ph, pl, pc = prev
        up, down = high - ph, pl - low
        pdm = up if up > down and up > 0 else Decimal(0)
        mdm = down if down > up and down > 0 else Decimal(0)
        tr = max(high - low, abs(high - pc), abs(low - pc))
        t, p, m = self._tr.update(tr), self._pdm.update(pdm), self._mdm.update(mdm)
        if t is None or p is None or m is None:
            return None
        pdi = Decimal(100) * p / t if t > 0 else Decimal(0)
        mdi = Decimal(100) * m / t if t > 0 else Decimal(0)
        s = pdi + mdi
        a = self._adx.update(
            Decimal(100) * abs(pdi - mdi) / (s if s != 0 else Decimal(1))
        )
        return None if a is None else AdxValue(a, pdi, mdi)
