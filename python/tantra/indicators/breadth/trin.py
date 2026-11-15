# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Arms index / TRIN (breadth family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.types import to_decimal


@indicator(
    "trin",
    "breadth",
    inputs=("advances", "declines", "adv_volume", "dec_volume"),
    warmup=lambda s: 1,
)
class Trin(Indicator):
    """Arms index: (advances/declines) / (adv_volume/dec_volume).

    Convention: if declines, adv_volume or dec_volume is <= 0 the ratio is undefined and
    the neutral value 1.0 is returned. Values > 1 are bearish, < 1 bullish.
    """

    def __init__(self) -> None:
        pass

    def update(
        self,
        advances: Decimal,
        declines: Decimal,
        adv_volume: Decimal,
        dec_volume: Decimal,
    ) -> Decimal:
        advances, declines, adv_volume, dec_volume = (
            to_decimal(advances),
            to_decimal(declines),
            to_decimal(adv_volume),
            to_decimal(dec_volume),
        )
        if declines <= 0 or adv_volume <= 0 or dec_volume <= 0:
            return Decimal("1")
        return (advances / declines) / (adv_volume / dec_volume)
