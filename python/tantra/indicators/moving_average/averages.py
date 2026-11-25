# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Moving averages."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from decimal import Decimal
from typing import Any  # mirror accommodation (gap 0006)

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator("sma", "moving_average", warmup=lambda s: s.period)
class Sma(Indicator):
    def __init__(self, period: int = 5) -> None:
        self.period = _check(period)
        self._w: deque[Decimal] = deque(maxlen=period)
        self._sum = Decimal(0)

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        if len(self._w) == self.period:
            self._sum -= self._w[0]
        self._w.append(x)
        self._sum += x
        return self._sum / self.period if len(self._w) == self.period else None


@indicator(
    "ema", "moving_average", warmup=lambda s: 1 if s.seed == "first" else s.period
)
class Ema(Indicator):
    """EMA with alpha = 2/(period+1).

    ``seed="sma"`` (TA-Lib) starts from the SMA of the first ``period`` values;
    ``seed="first"`` (Jesse) starts from the first value, so it is valid from bar 0.
    """

    def __init__(self, period: int = 5, seed: str = "sma") -> None:
        self.period = _check(period)
        if seed not in ("sma", "first"):
            raise ValueError(f"seed must be 'sma' or 'first', got {seed!r}")
        self.seed = seed
        self._alpha = Decimal(2) / (period + 1)
        self._seed = Sma(period) if seed == "sma" else None
        self.value: Decimal | None = None

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        if self.value is None:
            self.value = self._seed.update(x) if self._seed else x
        else:
            self.value = x * self._alpha + self.value * (1 - self._alpha)
        return self.value


@indicator("rma", "moving_average", warmup=lambda s: s.period)
class Rma(Indicator):
    """Wilder's smoothing: SMA seed, then ``(prev * (n - 1) + x) / n``."""

    def __init__(self, period: int = 14) -> None:
        self.period = _check(period)
        self._seed = Sma(period)
        self.value: Decimal | None = None

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        if self.value is None:
            self.value = self._seed.update(x)
        else:
            self.value = (self.value * (self.period - 1) + x) / self.period
        return self.value


@indicator("wma", "moving_average", warmup=lambda s: s.period)
class Wma(Indicator):
    """Linearly weighted moving average (newest value has the largest weight).

    Weights are ``1..period`` oldest to newest. Exact under ``Decimal``: a non-finite
    value in the window makes the result NaN until it has left the window; totals are
    then rebuilt exactly (the float-only drift/overflow guards are unnecessary here).
    """

    def __init__(self, period: int = 5) -> None:
        self.period = _check(period)
        self._w: deque[Decimal] = deque(maxlen=period)
        self._den = Decimal(period * (period + 1) // 2)

    def update(self, x: Decimal) -> Decimal | None:
        x = to_decimal(x)
        self._w.append(x)
        if len(self._w) < self.period:
            return None
        if any(not v.is_finite() for v in self._w):
            return Decimal("NaN")
        num = sum((k * v for k, v in enumerate(self._w, 1)), Decimal(0))
        return num / self._den


_MA_KINDS = {"sma": Sma, "ema": Ema, "rma": Rma, "wma": Wma}


def make_ma(kind: str, period: int) -> Any:  # mirror accommodation (gap 0006)
    """Moving-average factory: ``kind`` is one of sma, ema, rma (Wilder), wma."""
    try:
        return _MA_KINDS[kind](period)
    except KeyError:
        raise ValueError(
            f"unknown moving average {kind!r}; choose from {sorted(_MA_KINDS)}"
        ) from None
