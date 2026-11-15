# wheel surface (ex 0006): Decimal-canonical domain core facade
# stand-in closure for tantra-examples gap 0006

"""Facade re-exporting the wheel's Decimal-canonical domain core.

Note: `tantra.money.Currency` (the domain enum with minor-unit metadata) is a
separate type from the compiled top-level `tantra.Currency` (the broker-facing
enum). Domain code uses the former; wire-facing code uses the latter.
"""

from __future__ import annotations

from tantra.instrument import Instrument, InstrumentId, InstrumentKind, OptionType
from tantra.money import Currency, MinorUnit, Money
from tantra.position import Position, PositionSide
from tantra.trade import Trade
from tantra.types import (
    Bar,
    FillReport,
    OrderEvent,
    OrderRequest,
    OrderSide,
    Price,
    Quantity,
    Tick,
)

__all__ = [
    "Bar",
    "Currency",
    "FillReport",
    "Instrument",
    "InstrumentId",
    "InstrumentKind",
    "MinorUnit",
    "Money",
    "OptionType",
    "OrderEvent",
    "OrderRequest",
    "OrderSide",
    "Position",
    "PositionSide",
    "Price",
    "Quantity",
    "Tick",
    "Trade",
]
