"""Tests for the Decimal-canonical wheel `tantra.money` (gap 0006 root slice)."""

from decimal import Decimal

import pytest

from tantra.money import Currency, MinorUnit, Money


def test_from_major() -> None:
    m = Money.from_major("123.45", Currency.INR)
    assert m.amount == Decimal("123.45")
    assert m.currency is Currency.INR
    assert m.to_major() == Decimal("123.45")


def test_zero() -> None:
    z = Money.zero(Currency.USD)
    assert z.amount == Decimal(0)
    assert z.currency is Currency.USD


def test_arithmetic() -> None:
    a = Money.from_major("100.00", Currency.USD)
    b = Money.from_major("23.50", Currency.USD)
    assert (a + b).amount == Decimal("123.50")
    assert (a - b).amount == Decimal("76.50")
    assert (-a).amount == Decimal("-100.00")


def test_currency_mismatch_raises() -> None:
    usd = Money.from_major("1", Currency.USD)
    inr = Money.from_major("1", Currency.INR)
    with pytest.raises(ValueError):
        usd + inr


def test_combining_non_money_raises() -> None:
    m = Money.from_major("1", Currency.INR)
    with pytest.raises(TypeError):
        m + 1  # type: ignore[operator]


def test_str_renders_two_decimals() -> None:
    assert str(Money.from_major("123.45", Currency.INR)) == "INR 123.45"
    assert str(Money.from_major("123.456", Currency.INR)) == "INR 123.46"


def test_format_minor() -> None:
    assert Money.from_major("12.50", Currency.INR).format_minor() == "1,250 paise"
    assert Money.from_major("0.01", Currency.INR).format_minor() == "1 paisa"
    assert Money.from_major("12.50", Currency.USD).format_minor() == "1,250 cents"
    assert Money.from_major("12.50", Currency.EUR).format_minor() == "1,250 cents"
    assert Money.from_major("12.50", Currency.GBP).format_minor() == "1,250 pence"


def test_currency_minor_metadata() -> None:
    assert Currency.INR.minor_exponent == 2
    assert Currency.USD.minor_per_major == 100
    assert Currency.GBP.minor_unit == MinorUnit("penny", "pence")
    assert Currency.EUR.minor_unit.singular == "cent"
    assert {c.value for c in Currency} == {"INR", "USD", "EUR", "GBP"}


def test_mul_qty_exact_decimal() -> None:
    m = Money.mul_qty(Decimal("7"), Decimal("0.33"), Currency.INR)
    assert m.amount == Decimal("2.31")
    assert m.currency is Currency.INR


def test_non_numeric_rejected() -> None:
    with pytest.raises(TypeError):
        Money("abc", Currency.INR)


def test_equality_is_value_based() -> None:
    assert Money.from_major("10.00", Currency.INR) == Money.from_major("10", Currency.INR)
    assert Money.from_major("10.00", Currency.INR) != Money.from_major("10.00", Currency.USD)
