# wheel surface (ex 0006): Decimal-canonical domain core (mirrors tantra_examples/_kernel/money public API)
# stand-in closure for tantra-examples gap 0006

"""Decimal-canonical `Money` value object for the wheel.

The `_kernel.money` module stored integer minor units; this wheel surface is
Decimal major units (rust_decimal parity): `Money.amount` is an exact
`decimal.Decimal` in major units, and `format_minor()` projects it to an
integer minor-unit string for display.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum


@dataclass(frozen=True)
class MinorUnit:
    """Name of a currency's minor unit."""

    singular: str
    plural: str


class Currency(Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

    @property
    def minor_exponent(self) -> int:
        return _MINOR_UNITS[self][0]

    @property
    def minor_per_major(self) -> int:
        return 10**self.minor_exponent

    @property
    def minor_unit(self) -> MinorUnit:
        _, singular, plural = _MINOR_UNITS[self]
        return MinorUnit(singular, plural)


# Pinned minor-unit table. Sourced from the canonical tantra-core currency
# table: INR/USD/EUR/GBP are all exponent 2 (100 minor per major). The wheel
# `Money` pins its own table because the compiled `_tantra` exposes `Currency`
# but no `currency_minor_units` table.
_MINOR_UNITS: dict[Currency, tuple[int, str, str]] = {
    Currency.INR: (2, "paisa", "paise"),
    Currency.USD: (2, "cent", "cents"),
    Currency.EUR: (2, "cent", "cents"),
    Currency.GBP: (2, "penny", "pence"),
}


@dataclass(frozen=True, slots=True)
class Money:
    """Exact major-unit money value pinned to a `Currency`.

    Zero-floats invariant: the amount is always a `decimal.Decimal`; floats are
    rejected rather than silently truncated.
    """

    amount: Decimal
    currency: Currency = Currency.INR

    def __post_init__(self) -> None:
        amount = self.amount
        if not isinstance(amount, Decimal):
            try:
                amount = Decimal(str(amount))
            except (ValueError, ArithmeticError):
                raise TypeError(
                    f"Money.amount must be numeric, got {self.amount!r}"
                ) from None
        object.__setattr__(self, "amount", amount)

    @staticmethod
    def from_major(
        major: Decimal | int | str, currency: Currency = Currency.INR
    ) -> "Money":
        return Money(major, currency)

    @staticmethod
    def zero(currency: Currency = Currency.INR) -> "Money":
        return Money(Decimal(0), currency)

    @staticmethod
    def mul_qty(
        quantity: Decimal | int | str,
        price: Decimal | int | str,
        currency: Currency = Currency.INR,
    ) -> "Money":
        """Exact `quantity * price` in major units (Decimal arithmetic)."""
        return Money(Decimal(str(quantity)) * Decimal(str(price)), currency)

    def to_major(self) -> Decimal:
        return self.amount

    def _checked(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            raise TypeError(f"cannot combine Money with {type(other).__name__}")
        if other.currency is not self.currency:
            raise ValueError(
                f"currency mismatch: {self.currency} vs {other.currency}"
            )
        return other

    def __add__(self, other: "Money") -> "Money":
        o = self._checked(other)
        return Money(self.amount + o.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        o = self._checked(other)
        return Money(self.amount - o.amount, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def __str__(self) -> str:
        return (
            f"{self.currency.value} "
            f"{self.amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"
        )

    def format_minor(self) -> str:
        minor = int(self.amount * self.currency.minor_per_major)
        unit = self.currency.minor_unit
        name = unit.singular if minor == 1 else unit.plural
        return f"{minor:,} {name}"
