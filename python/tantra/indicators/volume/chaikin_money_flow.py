# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Chaikin money flow."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._rolling import RollingSum
from tantra.indicators._util import check as _check
from tantra.indicators.volume.accumulation_distribution import clv_volume
from tantra.types import to_decimal


@indicator(
    "chaikin_money_flow",
    "volume",
    inputs=("high", "low", "close", "volume"),
    warmup=lambda s: s.period,
)
class ChaikinMoneyFlow(Indicator):
    """Chaikin money flow: sum(CLV*volume, n) / sum(volume, n); 0 when the window volume is 0."""

    def __init__(self, period: int = 20) -> None:
        self.period = _check(period)
        self._mf = RollingSum(period)
        self._vol = RollingSum(period)

    def update(self, high: Decimal, low: Decimal, close: Decimal, volume: Decimal) -> Decimal | None:
        high, low, close, volume = (
            to_decimal(high),
            to_decimal(low),
            to_decimal(close),
            to_decimal(volume),
        )
        mf = self._mf.update(clv_volume(high, low, close, volume))
        vol = self._vol.update(volume)
        if mf is None or vol is None:
            return None
        return mf / vol if vol != 0 else Decimal("0")
