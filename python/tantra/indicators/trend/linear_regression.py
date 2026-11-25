# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Linear regression channel."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._rolling import RollingLinReg
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class LinearRegressionValue:
    value: Decimal
    slope: Decimal
    upper: Decimal
    lower: Decimal


@indicator(
    "linear_regression",
    "trend",
    outputs=("value", "slope", "upper", "lower"),
    warmup=lambda s: s.length,
)
class LinearRegression(Indicator):
    """Linear regression channel over ``length`` closes.

    value = end of the least-squares line, slope per bar, upper/lower = value +/- deviation *
    population std of the residuals. O(1) per update (``RollingLinReg``); NaN while a non-finite
    or ``|v| > 1e150`` close is in the window. The residual std is ``sqrt(sse / n)`` with ``sse``
    from running sums, so a near-perfect fit has std error up to ~2.9e-8 window standard
    deviations.
    """

    def __init__(
        self,
        length: int = 100,
        upper_deviation: Decimal = Decimal(2),
        lower_deviation: Decimal = Decimal(2),
    ) -> None:
        if length < 2:
            raise ValueError(f"length must be >= 2, got {length}")
        upper_deviation, lower_deviation = (
            to_decimal(upper_deviation),
            to_decimal(lower_deviation),
        )
        if upper_deviation < 0 or lower_deviation < 0:
            raise ValueError("deviations must be >= 0")
        self.length = length
        self.upper_deviation, self.lower_deviation = upper_deviation, lower_deviation
        self._reg = RollingLinReg(length)
        self._update = self._reg.update_raw
        self._last = length - 1

    def update(self, x: Decimal) -> LinearRegressionValue | None:
        fit = self._update(x)
        if fit is None:
            return None
        intercept, slope, sse = fit
        std = (sse / self.length).sqrt()
        end = intercept + slope * self._last
        return LinearRegressionValue(
            end,
            slope,
            end + self.upper_deviation * std,
            end - self.lower_deviation * std,
        )
