# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""McGinley Dynamic."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator("mcginley_dynamic", "moving_average", warmup=lambda s: 1)
class McGinleyDynamic(Indicator):
    """McGinley Dynamic: md += (c - md) / (k * n * (c/md)^4), seeded with the first close.

    Convention: if md <= 0 the ratio is taken as 1; if the divisor is 0 (c == 0) md is unchanged.
    """

    def __init__(self, period: int = 14, k: Decimal = Decimal("0.6")) -> None:
        self.period = _check(period)
        k = to_decimal(k)
        if k <= 0:
            raise ValueError(f"k must be > 0, got {k}")
        self.k = k
        self.value: Decimal | None = None

    def update(self, x: Decimal) -> Decimal:
        x = to_decimal(x)
        if self.value is None:
            self.value = x
            return self.value
        md = self.value
        ratio = x / md if md > 0 else Decimal(1)
        den = self.k * self.period * ratio**4
        if den > 0:
            self.value = md + (x - md) / den
        return self.value
