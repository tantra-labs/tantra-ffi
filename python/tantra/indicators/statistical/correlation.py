# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Rolling Pearson correlation of price with a benchmark (statistical family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._rolling import RollingPairMoments
from tantra.types import to_decimal


@indicator(
    "correlation",
    "statistical",
    inputs=("close", "benchmark"),
    warmup=lambda s: s.length,
)
class Correlation(Indicator):
    """Pearson correlation of close vs benchmark PRICES over ``length`` bars.

    Matches TradingView ``ta.correlation``.
    Returns 0.0 when either window has zero variance. O(1) per update (``RollingPairMoments``);
    NaN while a non-finite or ``|v| > 1e150`` value is in either window (the old O(n) code
    returned 1.0 there by accident of ``min``/``max`` with NaN), exact again once it has left.
    """

    def __init__(self, length: int = 20) -> None:
        if length < 2:
            raise ValueError(f"length must be >= 2, got {length}")
        self.length = length
        self._rp = RollingPairMoments(length)
        self._update = self._rp.update_raw

    def update(self, close: Decimal, benchmark: Decimal) -> Decimal | None:
        close, benchmark = to_decimal(close), to_decimal(benchmark)
        m = self._update(close, benchmark)
        if m is None:
            return None
        cov, vx, vy = m[4], m[2], m[3]
        if cov.is_nan():
            return Decimal("NaN")
        if vx <= 0 or vy <= 0:
            return Decimal(0)
        r = cov / (vx * vy).sqrt()
        return Decimal(1) if r > Decimal(1) else max(r, Decimal(-1))
