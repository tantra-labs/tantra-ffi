# wheel surface (ex 0006): Decimal-canonical domain core (mirrors tantra_examples/_kernel/trade public API)
# stand-in closure for tantra-examples gap 0006

"""Decimal-canonical Trade record."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from tantra.instrument import InstrumentId
from tantra.money import Currency, Money
from tantra.types import OrderSide


@dataclass(frozen=True, slots=True)
class Trade:
    instrument_id: InstrumentId
    side: OrderSide
    quantity: Decimal
    price: Decimal
    ts: int = 0
    order_id: str | None = None
    costs: Money = field(default_factory=lambda: Money.zero(Currency.INR))

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantity", Decimal(str(self.quantity)))
        object.__setattr__(self, "price", Decimal(str(self.price)))
        costs = self.costs
        if isinstance(costs, (int, Decimal)):
            costs = Money.from_major(costs, Currency.INR)
        if not isinstance(costs, Money):
            raise TypeError("costs must be Money")
        object.__setattr__(self, "costs", costs)
