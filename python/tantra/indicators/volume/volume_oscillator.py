# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Volume oscillator."""
# ruff: noqa: E741
# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average import Ema
from tantra.types import to_decimal


@indicator(
    "volume_oscillator",
    "volume",
    inputs=("volume",),
    warmup=lambda s: max(s.short, s.long),
)
class VolumeOscillator(Indicator):
    """Volume oscillator: 100 * (EMA(volume, short) - EMA(volume, long)) / EMA(volume, long); 0 if the long EMA is 0."""

    def __init__(self, short: int = 5, long: int = 10) -> None:
        self.short = _check(short)
        self.long = _check(long)
        self._s = Ema(short)
        self._l = Ema(long)

    def update(self, volume: Decimal) -> Decimal | None:
        volume = to_decimal(volume)
        s, l = self._s.update(volume), self._l.update(volume)
        if s is None or l is None:
            return None
        return Decimal("100") * (s - l) / l if l != 0 else Decimal("0")
