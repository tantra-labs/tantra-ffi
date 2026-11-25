# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Session-anchored VWAP with standard-deviation bands."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._india import ist_session_day
from tantra.types import to_decimal


@dataclass(slots=True)
class VwapValue:
    vwap: Decimal
    upper: Decimal
    lower: Decimal


@indicator(
    "vwap",
    "volume",
    inputs=("high", "low", "close", "volume", "ts"),
    outputs=("vwap", "upper", "lower"),
    warmup=None,
)
class Vwap(Indicator):
    """Session VWAP on hlc3, reset each IST session day; bands = vwap +/- band_mult * volume-weighted stdev.
    Valid from the first bar of every session. Convention: while cumulative session volume is 0, vwap is
    the latest hlc3 and the stdev is 0."""

    def __init__(self, band_mult: Decimal = Decimal(1)) -> None:
        band_mult = to_decimal(band_mult)
        if band_mult < 0:
            raise ValueError(f"band_mult must be >= 0, got {band_mult}")
        self.band_mult = band_mult
        self._day: int | None = None
        self._v = self._pv = self._pv2 = Decimal(0)

    @property
    def warmup(self) -> None:
        return (
            None  # session-anchored: a value exists from the first bar of each session
        )

    def update(
        self, high: Decimal, low: Decimal, close: Decimal, volume: Decimal, ts: int
    ) -> VwapValue:
        high, low, close, volume = (
            to_decimal(high),
            to_decimal(low),
            to_decimal(close),
            to_decimal(volume),
        )
        day = ist_session_day(int(ts))
        if day != self._day:
            self._day = day
            self._v = self._pv = self._pv2 = Decimal(0)
        tp = (high + low + close) / 3
        self._v += volume
        self._pv += tp * volume
        self._pv2 += tp * tp * volume
        if self._v == 0:
            return VwapValue(tp, tp, tp)
        vw = self._pv / self._v
        sd = (max(Decimal(0), self._pv2 / self._v - vw * vw)).sqrt()
        return VwapValue(vw, vw + self.band_mult * sd, vw - self.band_mult * sd)
