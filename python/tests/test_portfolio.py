"""Tests for the Decimal-canonical wheel `tantra.portfolio` (T13 surface)."""

from decimal import Decimal

import pytest
from tantra.instrument import InstrumentId
from tantra.money import Currency, Money
from tantra.portfolio import Account, Portfolio
from tantra.position import Position


def _inr(major: str) -> Money:
    return Money.from_major(major, Currency.INR)


def test_credit_debit_arithmetic() -> None:
    account = Account(name="main")
    account.credit(_inr("1000"))
    account.debit(_inr("400"))
    assert account.cash.amount == Decimal(600)
    assert isinstance(account.cash.amount, Decimal)


def test_debit_overdraw_raises() -> None:
    account = Account(name="main", cash=_inr("100"))
    with pytest.raises(ValueError):
        account.debit(_inr("400"))
    assert account.cash.amount == Decimal(100)


def test_negative_credit_raises_and_leaves_balance() -> None:
    account = Account(name="main", cash=_inr("100"))
    with pytest.raises(ValueError):
        account.credit(_inr("-50"))
    assert account.cash.amount == Decimal(100)


def test_negative_debit_raises_and_leaves_balance() -> None:
    account = Account(name="main", cash=_inr("100"))
    with pytest.raises(ValueError):
        account.debit(_inr("-50"))
    assert account.cash.amount == Decimal(100)


def test_upsert_position_round_trip() -> None:
    account = Account(name="main")
    pos = Position(
        instrument_id=InstrumentId("RELIANCE"),
        quantity=Decimal(10),
        avg_price=Decimal("2450.00"),
    )
    account.upsert_position(pos)
    assert account.get_position(InstrumentId("RELIANCE")) is pos
    assert account.get_position(InstrumentId("HDFCBANK")) is None


def test_portfolio_add_account_round_trip() -> None:
    portfolio = Portfolio()
    account = Account(name="main")
    portfolio.add_account(account)
    assert portfolio.account("main") is account
    assert portfolio.account("missing") is None
