# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Moving-average envelope (volatility family)."""
# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average.averages import Ema, Sma
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class EnvelopeValue:
    upper: Decimal
    middle: Decimal
    lower: Decimal


@indicator(
    "envelope",
    "volatility",
    outputs=("upper", "middle", "lower"),
    warmup=lambda s: s.length,
)
class Envelope(Indicator):
    """Envelope: MA(close, length) * (1 +/- percent/100); ``ma_type`` is 'sma' (default) or 'ema' (SMA-seeded)."""

    def __init__(
        self, length: int = 20, percent: Decimal = Decimal("10"), ma_type: str = "sma"
    ) -> None:
        self.length = _check(length)
        percent = to_decimal(percent)
        if percent < 0:
            raise ValueError("percent must be >= 0")
        if ma_type not in ("sma", "ema"):
            raise ValueError(f"ma_type must be 'sma' or 'ema', got {ma_type!r}")
        self.percent, self.ma_type = percent, ma_type
        self._ma = Sma(length) if ma_type == "sma" else Ema(length)

    def update(self, close: Decimal) -> EnvelopeValue | None:
        close = to_decimal(close)
        m = self._ma.update(close)
        if m is None:
            return None
        k = self.percent / Decimal("100")
        return EnvelopeValue(m * (1 + k), m, m * (1 - k))
