# wheel surface (ex 0006): Decimal-canonical domain core (mirrors tantra_examples/_kernel/order public API)
# stand-in closure for tantra-examples gap 0006
"""Decimal-canonical order domain types for the ``tantra`` wheel.

Mirrors the public API of ``tantra_examples._kernel.order`` under the
zero-float policy: every financial quantity is an exact ``Decimal``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from tantra.instrument import InstrumentId
from tantra.types import to_decimal


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"
    NO_ORDER_SIDE = "no_order_side"  # wire value only; intents reject it


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    STOP = "stop_market"  # noqa: PIE796

    @classmethod
    def _missing_(cls, value: object) -> OrderType | None:
        return cls.STOP_MARKET if value == "stop" else None


class TimeInForce(Enum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"
    GTD = "gtd"


class OrderStatus(Enum):
    INITIALIZED = "initialized"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


_PRICE_RULES: dict[OrderType, tuple[bool, bool]] = {
    OrderType.MARKET: (False, False),
    OrderType.LIMIT: (True, False),
    OrderType.STOP_MARKET: (False, True),
    OrderType.STOP_LIMIT: (True, True),
    OrderType.TRAILING_STOP: (False, False),
}


def validate_intent(side, quantity, order_type, price=None, trigger_price=None,
                    trail_amount=None, trail_percent=None) -> None:
    """Validate an order intent, raising ``ValueError`` on any violation."""
    if side not in (OrderSide.BUY, OrderSide.SELL):
        raise ValueError(f"side must be OrderSide.BUY or OrderSide.SELL, got {side!r}")
    quantity = to_decimal(quantity)
    if not (quantity.is_finite() and quantity > 0):
        raise ValueError(f"quantity must be finite and > 0, got {quantity}")
    if price is not None:
        price = to_decimal(price)
        if not price.is_finite():
            raise ValueError(f"price must be finite, got {price}")
    if trigger_price is not None:
        trigger_price = to_decimal(trigger_price)
        if not trigger_price.is_finite():
            raise ValueError(f"trigger_price must be finite, got {trigger_price}")
    if trail_amount is not None:
        trail_amount = to_decimal(trail_amount)
        if not (trail_amount.is_finite() and trail_amount > 0):
            raise ValueError(f"trail_amount must be finite and > 0, got {trail_amount}")
    if trail_percent is not None:
        trail_percent = to_decimal(trail_percent)
        if not (trail_percent.is_finite() and trail_percent > 0 and trail_percent < 100):
            raise ValueError(f"trail_percent must be finite and in (0, 100), got {trail_percent}")

    needs_price, needs_trigger = _PRICE_RULES[order_type]
    if needs_price and price is None:
        raise ValueError(f"{order_type.value} requires a price")
    if not needs_price and price is not None:
        raise ValueError(f"{order_type.value} does not accept a price")
    if needs_trigger and trigger_price is None:
        raise ValueError(f"{order_type.value} requires a trigger price")
    if not needs_trigger and trigger_price is not None:
        raise ValueError(f"{order_type.value} does not accept a trigger price")

    if order_type is OrderType.TRAILING_STOP:
        if (trail_amount is None) == (trail_percent is None):
            raise ValueError(
                "trailing_stop requires exactly one of trail_amount or trail_percent"
            )
    else:
        if trail_amount is not None or trail_percent is not None:
            raise ValueError(f"{order_type.value} does not accept trail_amount or trail_percent")


@dataclass(frozen=True, slots=True)
class OrderIntent:
    instrument_id: InstrumentId
    side: OrderSide
    quantity: Decimal
    order_type: OrderType = OrderType.MARKET
    price: Decimal | None = None
    time_in_force: TimeInForce = TimeInForce.DAY
    trigger_price: Decimal | None = None
    trail_amount: Decimal | None = None
    trail_percent: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantity", to_decimal(self.quantity))
        if self.price is not None:
            object.__setattr__(self, "price", to_decimal(self.price))
        if self.trigger_price is not None:
            object.__setattr__(self, "trigger_price", to_decimal(self.trigger_price))
        if self.trail_amount is not None:
            object.__setattr__(self, "trail_amount", to_decimal(self.trail_amount))
        if self.trail_percent is not None:
            object.__setattr__(self, "trail_percent", to_decimal(self.trail_percent))
        validate_intent(
            self.side,
            self.quantity,
            self.order_type,
            price=self.price,
            trigger_price=self.trigger_price,
            trail_amount=self.trail_amount,
            trail_percent=self.trail_percent,
        )

    @classmethod
    def market_buy(cls, instrument_id, quantity) -> OrderIntent:
        return cls(instrument_id, OrderSide.BUY, quantity)

    @classmethod
    def market_sell(cls, instrument_id, quantity) -> OrderIntent:
        return cls(instrument_id, OrderSide.SELL, quantity)

    @classmethod
    def limit_buy(cls, instrument_id, quantity, price) -> OrderIntent:
        return cls(instrument_id, OrderSide.BUY, quantity, OrderType.LIMIT, price)

    @classmethod
    def limit_sell(cls, instrument_id, quantity, price) -> OrderIntent:
        return cls(instrument_id, OrderSide.SELL, quantity, OrderType.LIMIT, price)

    @classmethod
    def stop_buy(cls, instrument_id, quantity, trigger_price) -> OrderIntent:
        return cls(instrument_id, OrderSide.BUY, quantity, OrderType.STOP_MARKET,
                   trigger_price=trigger_price)

    @classmethod
    def stop_sell(cls, instrument_id, quantity, trigger_price) -> OrderIntent:
        return cls(instrument_id, OrderSide.SELL, quantity, OrderType.STOP_MARKET,
                   trigger_price=trigger_price)

    @classmethod
    def stop_limit_buy(cls, instrument_id, quantity, trigger_price, limit_price) -> OrderIntent:
        return cls(instrument_id, OrderSide.BUY, quantity, OrderType.STOP_LIMIT,
                   limit_price, trigger_price=trigger_price)

    @classmethod
    def stop_limit_sell(cls, instrument_id, quantity, trigger_price, limit_price) -> OrderIntent:
        return cls(instrument_id, OrderSide.SELL, quantity, OrderType.STOP_LIMIT,
                   limit_price, trigger_price=trigger_price)

    @classmethod
    def trailing_stop_sell(cls, instrument_id, quantity, *, trail_amount=None,
                           trail_percent=None) -> OrderIntent:
        return cls(instrument_id, OrderSide.SELL, quantity, OrderType.TRAILING_STOP,
                   trail_amount=trail_amount, trail_percent=trail_percent)

    @classmethod
    def trailing_stop_buy(cls, instrument_id, quantity, *, trail_amount=None,
                          trail_percent=None) -> OrderIntent:
        return cls(instrument_id, OrderSide.BUY, quantity, OrderType.TRAILING_STOP,
                   trail_amount=trail_amount, trail_percent=trail_percent)


__all__ = [
    "OrderIntent",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "TimeInForce",
    "validate_intent",
]
