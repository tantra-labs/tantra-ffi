"""Shared helpers and re-exports for Tantra core domain types.

The compiled ``tantra._tantra`` extension exposes canonical value objects
(``Price``, ``Quantity``, ``InstrumentId``, ...) with exact decimal arithmetic.
This module adds small ergonomic helpers on top of that surface.
"""
from decimal import Decimal

from tantra import _tantra

# --- Re-exports of the compiled core types -----------------------------------
Price = _tantra.Price
Quantity = _tantra.Quantity
Currency = _tantra.Currency
Exchange = _tantra.Exchange
InstrumentId = _tantra.InstrumentId
OrderSide = _tantra.OrderSide
OrderStatus = _tantra.OrderStatus
TimeInForce = _tantra.TimeInForce
DepthLevel = _tantra.DepthLevel
Bar = _tantra.Bar
Tick = _tantra.Tick
OrderRequest = _tantra.OrderRequest
OrderAck = _tantra.OrderAck
FillReport = _tantra.FillReport
OrderEvent = _tantra.OrderEvent
Decision = _tantra.Decision
RiskEngine = _tantra.RiskEngine
StrategyRunner = _tantra.StrategyRunner
RiskRefused = _tantra.RiskRefused
ConversionError = _tantra.ConversionError

DEFAULT_EXCHANGE = "NSE"

__all__ = [
    "DEFAULT_EXCHANGE",
    "Bar",
    "ConversionError",
    "Currency",
    "Decision",
    "DepthLevel",
    "Exchange",
    "FillReport",
    "InstrumentId",
    "OrderAck",
    "OrderEvent",
    "OrderRequest",
    "OrderSide",
    "OrderStatus",
    "Price",
    "Quantity",
    "RiskEngine",
    "RiskRefused",
    "StrategyRunner",
    "Tick",
    "TimeInForce",
    "instrument_id",
    "to_decimal",
]


def to_decimal(value: Decimal | str | Price | Quantity) -> Decimal:
    """Coerce ``value`` into an exact ``decimal.Decimal``.

    Accepts ``Decimal``, ``str``, and the compiled ``Price``/``Quantity`` value
    objects (converted via ``.to_str()`` so the ``Price(10)`` repr pitfall never
    leaks into arithmetic).
    """
    if isinstance(value, Decimal):
        return value
    to_str = getattr(value, "to_str", None)
    if to_str is not None:
        return Decimal(to_str())
    return Decimal(str(value))


def instrument_id(symbol: str) -> InstrumentId:
    """Build an :class:`InstrumentId` from ``"EXCHANGE:SYMBOL"`` or ``"SYMBOL"``.

    Symbols without an exchange prefix default to ``NSE``.
    """
    if ":" in symbol:
        return InstrumentId.from_str(symbol)
    return InstrumentId(DEFAULT_EXCHANGE, symbol)
