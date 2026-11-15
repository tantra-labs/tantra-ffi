from decimal import Decimal

import pytest

from tantra.instrument import InstrumentId
from tantra.order import (
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
    validate_intent,
)

IID = InstrumentId("RELIANCE", "NSE")


def test_enum_values() -> None:
    assert OrderSide.BUY.value == "buy"
    assert OrderStatus.FILLED.value == "filled"
    assert TimeInForce.IOC.value == "ioc"
    assert OrderType.STOP is OrderType.STOP_MARKET
    assert OrderType("stop") is OrderType.STOP_MARKET


def test_market_buy_coerces_decimal() -> None:
    intent = OrderIntent.market_buy(IID, "10")
    assert intent.quantity == Decimal("10")
    assert intent.side is OrderSide.BUY
    assert intent.order_type is OrderType.MARKET
    assert intent.price is None


def test_limit_buy_price() -> None:
    intent = OrderIntent.limit_buy(IID, "10", "2450.50")
    assert intent.quantity == Decimal("10")
    assert intent.price == Decimal("2450.50")
    assert intent.order_type is OrderType.LIMIT


def test_stop_sell_trigger_price() -> None:
    intent = OrderIntent.stop_sell(IID, "5", "2400")
    assert intent.trigger_price == Decimal("2400")
    assert intent.order_type is OrderType.STOP_MARKET
    with pytest.raises(ValueError):
        OrderIntent(IID, OrderSide.SELL, "5", OrderType.STOP_MARKET,
                    price="2400", trigger_price="2400")


def test_trailing_stop_exactly_one_of() -> None:
    intent = OrderIntent.trailing_stop_sell(IID, "5", trail_amount="50")
    assert intent.trail_amount == Decimal("50")
    assert intent.trail_percent is None
    with pytest.raises(ValueError):
        OrderIntent.trailing_stop_sell(IID, "5")
    with pytest.raises(ValueError):
        OrderIntent.trailing_stop_sell(IID, "5", trail_amount="50", trail_percent="1")


def test_validate_intent_rejections() -> None:
    with pytest.raises(ValueError):
        validate_intent(OrderSide.BUY, "0", OrderType.MARKET)
    with pytest.raises(ValueError):
        validate_intent(OrderSide.BUY, "-1", OrderType.MARKET)
    with pytest.raises(ValueError):
        validate_intent(OrderSide.NO_ORDER_SIDE, "1", OrderType.MARKET)
    with pytest.raises(ValueError):
        OrderIntent(IID, OrderSide.BUY, "1", OrderType.MARKET, price="100")
    with pytest.raises(ValueError):
        OrderIntent(IID, OrderSide.BUY, "1", OrderType.LIMIT)


def test_int_and_str_quantity_equal() -> None:
    assert OrderIntent.market_buy(IID, 10) == OrderIntent.market_buy(IID, "10")
