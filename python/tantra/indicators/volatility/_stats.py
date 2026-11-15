# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Shared rolling helpers for the volatility family (O(1) per update, numerically stable)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._rolling import RollingMoments


class RollingStd:
    """Population (biased, /n) standard deviation and mean over the last ``period`` values."""

    def __init__(self, period: int) -> None:
        self.period = period
        self._m = RollingMoments(period)
        self._update = self._m.update_raw

    def update(self, x: Decimal) -> tuple[Decimal, Decimal] | None:
        """Returns ``(mean, stdev)`` once ``period`` values are seen, else None."""
        r = self._update(x)
        return None if r is None else (r[0], r[2])
