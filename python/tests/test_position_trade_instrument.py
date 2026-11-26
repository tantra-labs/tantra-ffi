"""Tests for the Decimal-canonical wheel domain core (gap 0006 root slice)."""

from decimal import Decimal
from typing import cast

import pytest
from tantra.instrument import Instrument, InstrumentId, InstrumentKind, OptionType
from tantra.money import Currency, Money
from tantra.position import Position, PositionSide
from tantra.trade import Trade
from tantra.types import OrderSide


def _position(
    side: PositionSide = PositionSide.LONG, qty: str = "100", px: str = "500"
) -> Position:
    p = Position(instrument_id=InstrumentId("RELIANCE"), currency=Currency.INR)
    p.apply_fill(side, qty, px)
    return p


def test_apply_fill_open_and_weighted_average() -> None:
    p = _position()
    assert p.side is PositionSide.LONG
    assert p.quantity == Decimal(100)
    assert p.avg_price == Decimal(500)
    assert not p.is_flat
    p.apply_fill(PositionSide.LONG, "100", "600")
    assert p.quantity == Decimal(200)
    assert p.avg_price == Decimal(550)  # (100*500 + 100*600) / 200


def test_apply_fill_partial_close() -> None:
    p = _position()
    p.apply_fill(PositionSide.SHORT, "40", "550")
    assert p.side is PositionSide.LONG
    assert p.quantity == Decimal(60)
    assert p.avg_price == Decimal(500)
    assert p.realized_pnl.amount == Decimal(2000)  # 40 * (550 - 500)


def test_apply_fill_full_close() -> None:
    p = _position()
    p.apply_fill(PositionSide.SHORT, "100", "550")
    assert p.is_flat
    assert p.quantity == Decimal(0)
    assert p.realized_pnl.amount == Decimal(5000)  # 100 * (550 - 500)


def test_apply_fill_reverse_long_to_short() -> None:
    p = _position()
    p.apply_fill(PositionSide.SHORT, "150", "450")
    assert p.side is PositionSide.SHORT
    assert p.quantity == Decimal(50)
    assert p.avg_price == Decimal(450)
    assert p.realized_pnl.amount == Decimal(-5000)  # 100 * (450 - 500)


def test_apply_fill_short_partial_close() -> None:
    p = _position(side=PositionSide.SHORT, qty="100", px="500")
    p.apply_fill(PositionSide.LONG, "50", "450")
    assert p.side is PositionSide.SHORT
    assert p.quantity == Decimal(50)
    assert p.avg_price == Decimal(500)
    assert p.realized_pnl.amount == Decimal(2500)  # 50 * (500 - 450)


def test_signed_quantity_and_validation() -> None:
    p = _position()
    assert p.signed_quantity == Decimal(100)
    p2 = _position(side=PositionSide.SHORT)
    assert p2.signed_quantity == Decimal(-100)
    assert PositionSide.LONG.opposite is PositionSide.SHORT
    with pytest.raises(ValueError):
        p.apply_fill(PositionSide.LONG, "0", "500")
    with pytest.raises(ValueError):
        p.apply_fill(PositionSide.LONG, "10", "-5")


def test_trade_costs_coercion() -> None:
    t = Trade(
        instrument_id=InstrumentId("RELIANCE"),
        side=OrderSide("BUY"),
        quantity=cast(Decimal, "10"),
        price=cast(Decimal, "500"),
        costs=cast(Money, 25),
    )
    assert t.quantity == Decimal(10)
    assert t.price == Decimal(500)
    assert t.costs == Money.from_major("25", Currency.INR)
    t_decimal = Trade(
        instrument_id=InstrumentId("RELIANCE"),
        side=OrderSide("SELL"),
        quantity=cast(Decimal, 10),
        price=cast(Decimal, 500),
        costs=cast(Money, Decimal(25)),
    )
    assert t_decimal.costs == Money.from_major("25", Currency.INR)


def test_trade_costs_str_is_rejected() -> None:
    with pytest.raises(TypeError):
        Trade(
            instrument_id=InstrumentId("RELIANCE"),
            side=OrderSide("BUY"),
            quantity=cast(Decimal, "10"),
            price=cast(Decimal, "500"),
            costs=cast(Money, "25"),
        )


def test_trade_costs_type_error() -> None:
    with pytest.raises(TypeError):
        Trade(
            instrument_id=InstrumentId("RELIANCE"),
            side=OrderSide("SELL"),
            quantity=cast(Decimal, 10),
            price=cast(Decimal, 500),
            costs=cast(Money, object()),
        )


def _equity() -> Instrument:
    return Instrument(
        instrument_id=InstrumentId("RELIANCE"),
        kind=InstrumentKind.EQUITY,
        lot_size=Decimal(1),
        tick_size=Decimal("0.05"),
    )


def _option() -> Instrument:
    return Instrument(
        instrument_id=InstrumentId("NIFTY", "NFO"),
        kind=InstrumentKind.OPTION,
        lot_size=Decimal(75),
        tick_size=Decimal("0.05"),
        currency="INR",
        strike=Decimal(24000),
        option_type=OptionType.CALL,
        underlying="NIFTY",
    )


def test_instrument_id_str() -> None:
    assert str(InstrumentId("RELIANCE")) == "RELIANCE.NSE"
    assert str(InstrumentId("NIFTY", "NFO")) == "NIFTY.NFO"


def test_instrument_kind_and_derivative() -> None:
    assert _equity().is_derivative is False
    assert _option().is_derivative is True


def test_stake_quantity_rounds_up_to_lot() -> None:
    opt = _option()
    assert opt.stake_quantity(Decimal(100)) == Decimal(150)
    assert opt.stake_quantity(Decimal(150)) == Decimal(150)
    assert opt.stake_quantity(Decimal(1)) == Decimal(75)


def test_is_on_tick() -> None:
    ins = _equity()
    assert ins.is_on_tick(Decimal("123.50")) is True
    assert ins.is_on_tick(Decimal("123.51")) is False


def test_settle_notional() -> None:
    ins = _equity()
    assert ins.settle_notional(Decimal(10), Decimal("100.00")) == Money.from_major(
        "1000.00", Currency.INR
    )
    with pytest.raises(ValueError):
        ins.settle_notional(Decimal(10), Decimal("100.01"))


def test_instrument_validation() -> None:
    with pytest.raises(ValueError):
        Instrument(
            instrument_id=InstrumentId("X"),
            kind=InstrumentKind.EQUITY,
            lot_size=Decimal(0),
            tick_size=Decimal("0.05"),
        )
    with pytest.raises(ValueError):
        Instrument(
            instrument_id=InstrumentId("X"),
            kind=InstrumentKind.EQUITY,
            lot_size=Decimal(1),
            tick_size=Decimal(0),
        )


def test_option_type_code_and_from_code() -> None:
    assert OptionType.CALL.code == "CE"
    assert OptionType.PUT.code == "PE"
    assert OptionType.from_code("CE") is OptionType.CALL
    assert OptionType.from_code("CALL") is OptionType.CALL
    assert OptionType.from_code("pe") is OptionType.PUT
    assert OptionType.from_code("PUT") is OptionType.PUT
    with pytest.raises(ValueError):
        OptionType.from_code("XX")
