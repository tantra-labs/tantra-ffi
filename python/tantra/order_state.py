# wheel surface (ex 0006): Decimal-canonical domain core (mirrors tantra_examples/_kernel/order_state public API)
# stand-in closure for tantra-examples gap 0006
"""Decimal-canonical order lifecycle FSM for the ``tantra`` wheel.

Mirrors the public API of ``tantra_examples._kernel.order_state`` under the
zero-float policy: every financial quantity is an exact ``Decimal``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from tantra.order import OrderStatus
from tantra.types import to_decimal

QTY_EPS = Decimal("1e-9")  # ADR 0016 tolerance


class OrderEventKind(Enum):
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FILL = "fill"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class OrderEvent:
    kind: OrderEventKind
    quantity: Decimal = Decimal(0)
    last_qty: Decimal = Decimal(0)
    complete: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantity", to_decimal(self.quantity))
        object.__setattr__(self, "last_qty", to_decimal(self.last_qty))

    @classmethod
    def submitted(cls, quantity) -> OrderEvent:
        return cls(OrderEventKind.SUBMITTED, quantity=quantity)

    @classmethod
    def accepted(cls) -> OrderEvent:
        return cls(OrderEventKind.ACCEPTED)

    @classmethod
    def rejected(cls) -> OrderEvent:
        return cls(OrderEventKind.REJECTED)

    @classmethod
    def fill(cls, last_qty, complete: bool) -> OrderEvent:
        return cls(OrderEventKind.FILL, last_qty=last_qty, complete=complete)

    @classmethod
    def cancel_requested(cls) -> OrderEvent:
        return cls(OrderEventKind.CANCEL_REQUESTED)

    @classmethod
    def cancelled(cls) -> OrderEvent:
        return cls(OrderEventKind.CANCELLED)

    @classmethod
    def expired(cls) -> OrderEvent:
        return cls(OrderEventKind.EXPIRED)


class IllegalTransition(ValueError):
    """Base class for illegal order state transitions (state unchanged)."""


class IllegalStatusTransition(IllegalTransition):
    def __init__(self, status: OrderStatus, cancel_requested: bool, event: OrderEventKind) -> None:
        self.status = status
        self.cancel_requested = cancel_requested
        self.event = event
        super().__init__(
            f"illegal transition: {event.value} in status {_status_name(status)} "
            f"(cancel_requested={'true' if cancel_requested else 'false'})"
        )


class Overfill(IllegalTransition):
    def __init__(self, quantity: Decimal, filled_qty: Decimal, last_qty: Decimal) -> None:
        self.quantity = quantity
        self.filled_qty = filled_qty
        self.last_qty = last_qty
        super().__init__(
            f"overfill: filled {filled_qty} + last {last_qty} exceeds quantity {quantity}"
        )


class FillMismatch(IllegalTransition):
    def __init__(self, claimed_complete: bool, derived_complete: bool) -> None:
        self.claimed_complete = claimed_complete
        self.derived_complete = derived_complete
        super().__init__(
            f"fill mismatch: claimed complete={claimed_complete}, derived complete={derived_complete}"
        )


class InvalidQuantity(IllegalTransition):
    def __init__(self, value: Decimal) -> None:
        self.value = value
        super().__init__(f"invalid quantity: {value}")


_TERMINAL = frozenset(
    {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED}
)

_TERMINAL_KIND: dict[OrderStatus, OrderEventKind] = {
    OrderStatus.CANCELLED: OrderEventKind.CANCELLED,
    OrderStatus.REJECTED: OrderEventKind.REJECTED,
    OrderStatus.EXPIRED: OrderEventKind.EXPIRED,
}

_KIND_TO_TERMINAL: dict[OrderEventKind, OrderStatus] = {
    OrderEventKind.CANCELLED: OrderStatus.CANCELLED,
    OrderEventKind.REJECTED: OrderStatus.REJECTED,
    OrderEventKind.EXPIRED: OrderStatus.EXPIRED,
}

_WORKING = frozenset(
    {OrderStatus.SUBMITTED, OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}
)


def _status_name(status: OrderStatus) -> str:
    """PascalCase of the wire status value (``partially_filled`` -> ``PartiallyFilled``)."""
    return "".join(part.capitalize() for part in status.value.split("_"))


@dataclass(slots=True)
class OrderState:
    status: OrderStatus = OrderStatus.INITIALIZED
    quantity: Decimal = Decimal(0)
    filled_qty: Decimal = Decimal(0)
    cancel_requested: bool = False

    def __post_init__(self) -> None:
        self.quantity = to_decimal(self.quantity)
        self.filled_qty = to_decimal(self.filled_qty)

    @staticmethod
    def can_transition(frm: tuple[OrderStatus, bool], via: OrderEventKind) -> bool:
        status, _ = frm
        if status is OrderStatus.INITIALIZED:
            return via in (OrderEventKind.SUBMITTED, OrderEventKind.REJECTED)
        if status in _WORKING:
            return via is not OrderEventKind.SUBMITTED
        if status is OrderStatus.FILLED:
            return False
        return _TERMINAL_KIND.get(status) is via

    def apply(self, ev: OrderEvent) -> bool:
        """Apply ``ev``; returns True on transition, False on duplicate no-op."""
        kind = ev.kind
        # A repeated fill after completion is indistinguishable from an overfill.
        if self.status is OrderStatus.FILLED and kind is OrderEventKind.FILL:
            self._check_qty(ev.last_qty)
            raise Overfill(self.quantity, self.filled_qty, ev.last_qty)
        if not self.can_transition((self.status, self.cancel_requested), kind):
            raise IllegalStatusTransition(self.status, self.cancel_requested, kind)
        if kind is OrderEventKind.SUBMITTED:
            self._check_qty(ev.quantity)
            self.quantity = ev.quantity
            self.status = OrderStatus.SUBMITTED
            return True
        if kind is OrderEventKind.ACCEPTED:
            if self.status is not OrderStatus.SUBMITTED:
                return False
            self.status = OrderStatus.ACCEPTED
            return True
        if kind in (OrderEventKind.REJECTED, OrderEventKind.CANCELLED, OrderEventKind.EXPIRED):
            if self.status in _TERMINAL:
                return False
            self._terminate(_KIND_TO_TERMINAL[kind])
            return True
        if kind is OrderEventKind.CANCEL_REQUESTED:
            if self.cancel_requested:
                return False
            self.cancel_requested = True
            return True
        self._fill(ev)
        return True

    def _fill(self, ev: OrderEvent) -> None:
        self._check_qty(ev.last_qty)
        cum = self.filled_qty + ev.last_qty
        if cum > self.quantity + QTY_EPS:
            raise Overfill(self.quantity, self.filled_qty, ev.last_qty)
        derived = cum + QTY_EPS >= self.quantity
        if ev.complete != derived:
            raise FillMismatch(ev.complete, derived)
        self.filled_qty = cum
        if derived:
            self._terminate(OrderStatus.FILLED)
        else:
            self.status = OrderStatus.PARTIALLY_FILLED

    def _terminate(self, status: OrderStatus) -> None:
        self.status = status
        self.cancel_requested = False

    def _check_qty(self, value) -> None:
        value = to_decimal(value)
        if not (value.is_finite() and value > 0):
            raise InvalidQuantity(value)


__all__ = [
    "OrderEventKind",
    "OrderEvent",
    "OrderState",
    "IllegalTransition",
    "IllegalStatusTransition",
    "Overfill",
    "FillMismatch",
    "InvalidQuantity",
    "QTY_EPS",
]
