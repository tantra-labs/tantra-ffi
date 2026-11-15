# wheel surface (ex 0006): Decimal-canonical tick tests
# stand-in closure for tantra-examples gap 0006

"""Tests for the Decimal-canonical tick wheel surface."""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from tantra.instrument import InstrumentId
from tantra.tick import AggressorSide, QuoteTick, TradeTick


def test_quote_tick_coerces_values_to_decimal() -> None:
    q = QuoteTick(InstrumentId("RELIANCE"), 1, "2500.5", 2501, "10", 20)
    assert isinstance(q.bid_price, Decimal)
    assert isinstance(q.ask_price, Decimal)
    assert isinstance(q.bid_size, Decimal)
    assert isinstance(q.ask_size, Decimal)
    assert q.bid_price == Decimal("2500.5")
    assert q.ask_price == Decimal("2501")
    assert q.bid_size == Decimal("10")
    assert q.ask_size == Decimal("20")
    assert q.ts == 1
    assert isinstance(q.ts, int)
    assert str(q.instrument_id) == "RELIANCE.NSE"


def test_quote_tick_mid_price_is_exact() -> None:
    q = QuoteTick(InstrumentId("RELIANCE"), 1, "2500.00", "2500.10", "10", "10")
    assert q.mid_price == Decimal("2500.05")


def test_quote_tick_rejects_inverted_book() -> None:
    with pytest.raises(ValueError):
        QuoteTick(InstrumentId("RELIANCE"), 1, "2500.10", "2500.00", "10", "10")


def test_quote_tick_rejects_negative_prices() -> None:
    with pytest.raises(ValueError):
        QuoteTick(InstrumentId("RELIANCE"), 1, "-1", "2500.00", "10", "10")
    with pytest.raises(ValueError):
        QuoteTick(InstrumentId("RELIANCE"), 1, "2500.00", "-1", "10", "10")


def test_quote_tick_rejects_negative_sizes() -> None:
    with pytest.raises(ValueError):
        QuoteTick(InstrumentId("RELIANCE"), 1, "2500.00", "2500.10", "-1", "10")
    with pytest.raises(ValueError):
        QuoteTick(InstrumentId("RELIANCE"), 1, "2500.00", "2500.10", "10", "-1")


def test_trade_tick_coerces_values_to_decimal() -> None:
    t = TradeTick(InstrumentId("RELIANCE"), 2, "2500.75", "5", AggressorSide.BUYER, "tid-1")
    assert isinstance(t.price, Decimal)
    assert isinstance(t.size, Decimal)
    assert t.price == Decimal("2500.75")
    assert t.size == Decimal("5")
    assert t.aggressor_side is AggressorSide.BUYER
    assert t.trade_id == "tid-1"
    assert t.ts == 2
    assert isinstance(t.ts, int)


def test_trade_tick_rejects_negative_price_or_size() -> None:
    with pytest.raises(ValueError):
        TradeTick(InstrumentId("RELIANCE"), 2, "-1", "5", AggressorSide.SELLER, "tid-2")
    with pytest.raises(ValueError):
        TradeTick(InstrumentId("RELIANCE"), 2, "2500.75", "-1", AggressorSide.SELLER, "tid-3")


def test_aggressor_side_enum_members() -> None:
    assert AggressorSide.BUYER.value == "buyer"
    assert AggressorSide.SELLER.value == "seller"
    assert AggressorSide.NO_AGGRESSOR.value == "no_aggressor"
    assert len(AggressorSide) == 3


def test_ticks_are_frozen() -> None:
    q = QuoteTick(InstrumentId("RELIANCE"), 1, "2500.00", "2500.10", "10", "10")
    with pytest.raises(dataclasses.FrozenInstanceError):
        q.bid_price = Decimal("2501.00")  # type: ignore[misc]
    t = TradeTick(InstrumentId("RELIANCE"), 2, "2500.75", "5", AggressorSide.BUYER, "tid-4")
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.price = Decimal("2501.00")  # type: ignore[misc]
