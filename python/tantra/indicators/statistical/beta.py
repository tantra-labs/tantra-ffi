# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Rolling beta against a benchmark (statistical family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._rolling import RollingPairMoments
from tantra.types import to_decimal


@indicator("beta", "statistical", inputs=("close", "benchmark"), warmup=lambda s: s.length + 1)
class Beta(Indicator):
    """Slope of asset simple returns on benchmark simple returns over ``length`` returns.

    beta = cov(asset, bench) / var(bench); needs length+1 prices. Returns 0.0 if the
    benchmark return variance is zero. Benchmark is e.g. NIFTY 50.

    O(1) per update (``RollingPairMoments`` over the returns); NaN while a non-finite or
    ``|v| > 1e150`` return is in either window (the old code returned 0.0 when only the benchmark
    window was non-finite), exact again once it has left.
    """

    def __init__(self, length: int = 60) -> None:
        if length < 2:
            raise ValueError(f"length must be >= 2, got {length}")
        self.length = length
        self._rp = RollingPairMoments(length)
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
        if m is None:
            return None
        cov, vy = m[4], m[3]
        if cov != cov:
            return Decimal("NaN")
        return cov / vy if vy > 0 else Decimal("0")
