# wheel surface (ex 0006): Decimal-canonical domain core (mirrors tantra_examples/_kernel/instrument public API)
# stand-in closure for tantra-examples gap 0006

"""Decimal-canonical instrument model: symbol, kind, lot/tick, and derivative math."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_CEILING
from enum import Enum

from tantra.money import Currency, Money


@dataclass(frozen=True, slots=True)
class InstrumentId:
    """Wheel-domain instrument identifier (canonical form `SYMBOL.EXCHANGE`)."""

    symbol: str
    exchange: str = "NSE"

    def __str__(self) -> str:
        return f"{self.symbol}.{self.exchange}"

    def to_compiled(self):
        from tantra.types import InstrumentId as Compiled

        return Compiled(self.exchange, self.symbol)


class InstrumentKind(Enum):
    EQUITY = "equity"
    ETF = "etf"
    BOND = "bond"
    IPO = "ipo"
    FUTURE = "future"
    OPTION = "option"
    FX = "fx"
    INDEX = "index"
    MUTUAL_FUND = "mutual_fund"


class OptionType(Enum):
    CALL = "call"
    PUT = "put"

    @property
    def code(self) -> str:
        return "CE" if self is OptionType.CALL else "PE"

    @classmethod
    def from_code(cls, code: str) -> "OptionType":
        code = code.upper()
        if code in ("CE", "CALL"):
            return cls.CALL
        if code in ("PE", "PUT"):
            return cls.PUT
        raise ValueError(f"unknown option code: {code!r}")


@dataclass(frozen=True, slots=True)
class Instrument:
    instrument_id: InstrumentId
    kind: InstrumentKind
    lot_size: Decimal
    tick_size: Decimal
    currency: str = "INR"
    expiry: date | None = None
    strike: Decimal | None = None
    option_type: OptionType | None = None
    underlying: str | None = None

    def __post_init__(self) -> None:
        lot = Decimal(str(self.lot_size))
        tick = Decimal(str(self.tick_size))
        if lot <= 0:
            raise ValueError("lot_size must be > 0")
        if tick <= 0:
            raise ValueError("tick_size must be > 0")
        object.__setattr__(self, "lot_size", lot)
        object.__setattr__(self, "tick_size", tick)
        if self.strike is not None:
            object.__setattr__(self, "strike", Decimal(str(self.strike)))

    @property
    def is_derivative(self) -> bool:
        return self.kind in (InstrumentKind.FUTURE, InstrumentKind.OPTION)

    def stake_quantity(self, quantity: Decimal) -> Decimal:
        q = Decimal(str(quantity))
        lots = (q / self.lot_size).to_integral_value(rounding=ROUND_CEILING)
        return lots * self.lot_size

    def is_on_tick(self, price: Decimal) -> bool:
        p = Decimal(str(price))
        quotient = p / self.tick_size
        return quotient == quotient.to_integral_value()

    def settle_notional(self, quantity: Decimal, price: Decimal) -> Money:
        p = Decimal(str(price))
        if not self.is_on_tick(p):
            raise ValueError(f"price {p} not on tick {self.tick_size}")
        return Money.mul_qty(quantity, p, Currency(self.currency))
