# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Arnaud Legoux moving average."""
# ruff: noqa: E501
# ruff: noqa: B905
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from decimal import ROUND_FLOOR, Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator("alma", "moving_average", warmup=lambda s: s.period)
class Alma(Indicator):
    """ALMA: Gaussian-weighted MA, w_i = exp(-(i-m)^2 / (2 s^2)), m = floor(offset*(n-1)), s = n/sigma.

    i = 0 is the oldest bar in the window. Weights are normalised to sum to 1.
    """

    def __init__(
        self,
        period: int = 9,
        offset: Decimal = Decimal("0.85"),
        sigma: Decimal = Decimal("6"),
    ) -> None:
        self.period = _check(period)
        offset, sigma = to_decimal(offset), to_decimal(sigma)
        if not Decimal("0") <= offset <= Decimal("1"):
            raise ValueError(f"offset must be in [0, 1], got {offset}")
        if sigma <= 0:
            raise ValueError(f"sigma must be > 0, got {sigma}")
        self.offset, self.sigma = offset, sigma
        m = (offset * (period - 1)).to_integral_value(rounding=ROUND_FLOOR)
        s = Decimal(period) / sigma
        w = [(-((Decimal(i) - m) ** 2) / (2 * s * s)).exp() for i in range(period)]
        tot = sum(w, Decimal("0"))
        self._w = [v / tot for v in w]
        self._x: deque[Decimal] = deque(maxlen=period)

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        self._x.append(x)
        if len(self._x) < self.period:
            return None
        return sum((w * v for w, v in zip(self._w, self._x)), Decimal("0"))
