# wheel surface (ex 0006): Decimal-canonical domain core (mirrors tantra_examples/_kernel/tick public API)
# stand-in closure for tantra-examples gap 0006

"""Decimal-canonical market-data ticks for the wheel.

The `_kernel.tick` mirror stored float prices/sizes; this wheel surface is
Decimal-canonical (rust_decimal parity): prices and sizes are exact
`decimal.Decimal` values. `ts` is unix nanoseconds.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from tantra.instrument import InstrumentId
from tantra.types import to_decimal


class AggressorSide(Enum):
    """Which side initiated a market trade."""

    BUYER = "buyer"
    SELLER = "seller"
    NO_AGGRESSOR = "no_aggressor"


def _to_decimal_checked(name: str, value) -> Decimal:
    d = to_decimal(value)
    if not d.is_finite():
        raise ValueError(f"{name} must be finite, got {value!r}")
    return d


@dataclass(frozen=True, slots=True)
class QuoteTick:
    """Top of book; `bid_price <= ask_price`, prices and sizes `>= 0`."""

    instrument_id: InstrumentId
    ts: int  # unix nanoseconds
    bid_price: Decimal
    ask_price: Decimal
    bid_size: Decimal
    ask_size: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "bid_price", _to_decimal_checked("bid_price", self.bid_price))
        object.__setattr__(self, "ask_price", _to_decimal_checked("ask_price", self.ask_price))
        object.__setattr__(self, "bid_size", _to_decimal_checked("bid_size", self.bid_size))
        object.__setattr__(self, "ask_size", _to_decimal_checked("ask_size", self.ask_size))
        if self.bid_price < 0 or self.ask_price < 0:
            raise ValueError("prices must be >= 0")
        if self.bid_price > self.ask_price:
            raise ValueError("bid_price must be <= ask_price")
        if self.bid_size < 0 or self.ask_size < 0:
            raise ValueError("sizes must be >= 0")

    @property
    def mid_price(self) -> Decimal:
        """Exact mid price: `(bid + ask) / 2`."""
        return (self.bid_price + self.ask_price) / Decimal(2)


@dataclass(frozen=True, slots=True)
class TradeTick:
    """A trade printed on the market (not the strategy's own fill)."""

    instrument_id: InstrumentId
    ts: int  # unix nanoseconds
    price: Decimal
    size: Decimal
    aggressor_side: AggressorSide
    trade_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "price", _to_decimal_checked("price", self.price))
        object.__setattr__(self, "size", _to_decimal_checked("size", self.size))
        if self.price < 0:
            raise ValueError("price must be >= 0")
        if self.size < 0:
            raise ValueError("size must be >= 0")


__all__ = ["AggressorSide", "QuoteTick", "TradeTick"]
