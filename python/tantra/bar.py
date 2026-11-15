# wheel surface (ex 0006): Decimal-canonical domain core (mirrors tantra_examples/_kernel/bar public API)
# stand-in closure for tantra-examples gap 0006

"""Decimal-canonical OHLCV `Bar` for the wheel.

The `_kernel.bar` mirror stored float OHLCV; this wheel surface is
Decimal-canonical (rust_decimal parity): open/high/low/close/volume are
exact `decimal.Decimal` values, non-negative, and `high >= low`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.instrument import InstrumentId
from tantra.types import to_decimal


@dataclass(frozen=True, slots=True)
class Bar:
    instrument_id: InstrumentId
    ts: int  # unix nanoseconds
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "open", to_decimal(self.open))
        object.__setattr__(self, "high", to_decimal(self.high))
        object.__setattr__(self, "low", to_decimal(self.low))
        object.__setattr__(self, "close", to_decimal(self.close))
        object.__setattr__(self, "volume", to_decimal(self.volume))
        if any(p < 0 for p in (self.open, self.high, self.low, self.close)):
            raise ValueError("prices must be >= 0")
        if self.high < self.low:
            raise ValueError("high must be >= low")
        if self.volume < 0:
            raise ValueError("volume must be >= 0")


__all__ = ["Bar"]
