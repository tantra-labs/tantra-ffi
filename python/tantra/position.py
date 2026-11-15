# wheel surface (ex 0006): Decimal-canonical domain core (mirrors tantra_examples/_kernel/position public API)
# stand-in closure for tantra-examples gap 0006

"""Decimal-canonical Position aggregate: FIFO-style averaging with exact Decimal math."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

from tantra.instrument import InstrumentId
from tantra.money import Currency, Money


class PositionSide(Enum):
    LONG = "long"
    SHORT = "short"

    @property
    def sign(self) -> Decimal:
        return Decimal("1") if self is PositionSide.LONG else Decimal("-1")

    @property
    def opposite(self) -> "PositionSide":
        return (
            PositionSide.SHORT if self is PositionSide.LONG else PositionSide.LONG
        )


@dataclass(slots=True)
class Position:
    instrument_id: InstrumentId
    currency: Currency = Currency.INR
    side: PositionSide = PositionSide.LONG
    quantity: Decimal = Decimal(0)
    avg_price: Decimal = Decimal(0)
    realized_pnl: Money = field(default_factory=lambda: Money.zero(Currency.INR))

    def __post_init__(self) -> None:
        self.quantity = Decimal(str(self.quantity))
        self.avg_price = Decimal(str(self.avg_price))
        if self.quantity < 0:
            raise ValueError("quantity must be >= 0")
        if self.avg_price < 0:
            raise ValueError("avg_price must be >= 0")
        if not isinstance(self.realized_pnl, Money):
            raise TypeError("realized_pnl must be Money")

    @property
    def is_flat(self) -> bool:
        return self.quantity == 0

    @property
    def signed_quantity(self) -> Decimal:
        return self.quantity * self.side.sign

    def apply_fill(
        self,
        fill_side: PositionSide,
        fill_qty: Decimal | int | str,
        fill_px: Decimal | int | str,
    ) -> None:
        """State machine: flat->open, same side->weighted avg, opposite side->close/partial/reverse."""
        fill_qty = Decimal(str(fill_qty))
        fill_px = Decimal(str(fill_px))
        if fill_qty <= 0:
            raise ValueError("fill_qty must be > 0")
        if fill_px <= 0:
            raise ValueError("fill_px must be > 0")

        if self.is_flat:
            self.side = fill_side
            self.quantity = fill_qty
            self.avg_price = fill_px
            return

        if fill_side is self.side:
            new_qty = self.quantity + fill_qty
            self.avg_price = (
                (self.quantity * self.avg_price + fill_qty * fill_px) / new_qty
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            self.quantity = new_qty
            return

        # Opposite side: close, partial close, or reverse.
        closed_qty = min(self.quantity, fill_qty)
        realized = closed_qty * (fill_px - self.avg_price)
        if self.side is PositionSide.SHORT:
            realized = -realized
        self.realized_pnl = self.realized_pnl + Money.from_major(
            realized, self.currency
        )

        if fill_qty < self.quantity:
            self.quantity -= fill_qty
        elif fill_qty == self.quantity:
            self.quantity = Decimal(0)
            self.avg_price = Decimal(0)
        else:
            self.side = fill_side
            self.quantity = fill_qty - self.quantity
            self.avg_price = fill_px
