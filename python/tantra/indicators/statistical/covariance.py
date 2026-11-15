# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Rolling covariance of returns with a benchmark (statistical family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._rolling import RollingPairMoments
from tantra.types import to_decimal


@indicator(
    "covariance",
    "statistical",
    inputs=("close", "benchmark"),
    warmup=lambda s: s.length + 1,
)
class Covariance(Indicator):
    """Sample covariance (divisor n-1) of asset and benchmark simple returns.

    Taken over ``length`` returns.
    O(1) per update (``RollingPairMoments``, ddof=1); NaN while a non-finite or ``|v| > 1e150``
    return is in either window, exact again once it has left.
    """

    def __init__(self, length: int = 20) -> None:
        if length < 2:
            raise ValueError(f"length must be >= 2, got {length}")
        self.length = length
        self._rp = RollingPairMoments(length, ddof=1)
        self._update = self._rp.update_raw
        self._prev: tuple[Decimal, Decimal] | None = None

    def update(self, close: Decimal, benchmark: Decimal) -> Decimal | None:
        close, benchmark = to_decimal(close), to_decimal(benchmark)
        prev, self._prev = self._prev, (close, benchmark)
        if prev is None:
            return None
        # simple_return inlined (hot path): cur / prev - 1, 0.0 when prev <= 0
        m = self._update(
            close / prev[0] - Decimal("1") if prev[0] > 0 else Decimal("0"),
            benchmark / prev[1] - Decimal("1") if prev[1] > 0 else Decimal("0"),
        )
        return None if m is None else m[4]
