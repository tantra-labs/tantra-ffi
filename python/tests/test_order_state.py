from decimal import Decimal

import pytest

from tantra.order import OrderStatus
from tantra.order_state import (
    FillMismatch,
    IllegalTransition,
    InvalidQuantity,
    OrderEvent,
    OrderEventKind,
    OrderState,
    Overfill,
    QTY_EPS,
)


def test_submit_accept_fill_complete() -> None:
    st = OrderState()
    assert st.apply(OrderEvent.submitted(Decimal("10"))) is True
    assert st.status is OrderStatus.SUBMITTED
    assert st.quantity == Decimal("10")
    assert st.apply(OrderEvent.accepted()) is True
    assert st.status is OrderStatus.ACCEPTED
    assert st.apply(OrderEvent.fill(Decimal("10"), True)) is True
    assert st.status is OrderStatus.FILLED
    assert st.filled_qty == Decimal("10")


def test_partial_fill_then_complete() -> None:
    st = OrderState()
    st.apply(OrderEvent.submitted(Decimal("10")))
    st.apply(OrderEvent.accepted())
    assert st.apply(OrderEvent.fill(Decimal("4"), False)) is True
    assert st.status is OrderStatus.PARTIALLY_FILLED
    assert st.filled_qty == Decimal("4")
    assert st.apply(OrderEvent.fill(Decimal("6"), True)) is True
    assert st.status is OrderStatus.FILLED
    assert st.filled_qty == Decimal("10")


def test_overfill_raises_and_state_unchanged() -> None:
    st = OrderState()
    st.apply(OrderEvent.submitted(Decimal("10")))
    st.apply(OrderEvent.accepted())
    with pytest.raises(Overfill):
        st.apply(OrderEvent.fill(Decimal("12"), True))
    assert st.status is OrderStatus.ACCEPTED
    assert st.filled_qty == Decimal("0")


def test_fill_mismatch() -> None:
    st = OrderState()
    st.apply(OrderEvent.submitted(Decimal("10")))
    st.apply(OrderEvent.accepted())
    with pytest.raises(FillMismatch):
        st.apply(OrderEvent.fill(Decimal("10"), False))


def test_reject_and_duplicate_terminal_noop() -> None:
    st = OrderState()
    assert st.apply(OrderEvent.rejected()) is True
    assert st.status is OrderStatus.REJECTED
    assert st.apply(OrderEvent.rejected()) is False
    assert st.status is OrderStatus.REJECTED


def test_cancel_requested_then_cancelled() -> None:
    st = OrderState()
    st.apply(OrderEvent.submitted(Decimal("10")))
    st.apply(OrderEvent.accepted())
    assert st.apply(OrderEvent.cancel_requested()) is True
    assert st.cancel_requested is True
    assert st.apply(OrderEvent.cancel_requested()) is False
    assert st.apply(OrderEvent.cancelled()) is True
    assert st.status is OrderStatus.CANCELLED
    assert st.cancel_requested is False


def test_can_transition_table() -> None:
    assert OrderState.can_transition(
        (OrderStatus.INITIALIZED, False), OrderEventKind.SUBMITTED
    ) is True
    assert OrderState.can_transition(
        (OrderStatus.INITIALIZED, False), OrderEventKind.REJECTED
    ) is True
    assert OrderState.can_transition(
        (OrderStatus.INITIALIZED, False), OrderEventKind.ACCEPTED
    ) is False
    assert OrderState.can_transition(
        (OrderStatus.ACCEPTED, False), OrderEventKind.SUBMITTED
    ) is False
    assert OrderState.can_transition(
        (OrderStatus.FILLED, False), OrderEventKind.CANCELLED
    ) is False
    assert OrderState.can_transition(
        (OrderStatus.CANCELLED, False), OrderEventKind.CANCELLED
    ) is True


def test_invalid_quantity() -> None:
    st = OrderState()
    with pytest.raises(InvalidQuantity):
        st.apply(OrderEvent.submitted(Decimal("0")))
    with pytest.raises(InvalidQuantity):
        st.apply(OrderEvent.submitted(Decimal("-1")))
    assert isinstance(InvalidQuantity(Decimal("0")), IllegalTransition)


def test_illegal_transition_raises_and_state_unchanged() -> None:
    from tantra.order_state import IllegalStatusTransition

    # CANCEL_REQUESTED is illegal from INITIALIZED (can_transition table).
    st = OrderState()
    with pytest.raises(IllegalStatusTransition):
        st.apply(OrderEvent.cancel_requested())
    assert st.status is OrderStatus.INITIALIZED
    assert st.cancel_requested is False

    # ACCEPTED is illegal from INITIALIZED.
    st = OrderState()
    with pytest.raises(IllegalStatusTransition):
        st.apply(OrderEvent.accepted())

    # SUBMITTED is illegal from a working state.
    st = OrderState()
    st.apply(OrderEvent.submitted(Decimal("10")))
    with pytest.raises(IllegalStatusTransition):
        st.apply(OrderEvent.submitted(Decimal("10")))

    # A FILL before the order is working is illegal.
    st = OrderState()
    with pytest.raises(IllegalStatusTransition):
        st.apply(OrderEvent.fill(Decimal("1"), True))


def test_terminal_status_accepts_only_matching_terminal_kind() -> None:
    from tantra.order_state import IllegalStatusTransition

    # A rejected order accepts a repeated REJECTED (no-op) but not CANCELLED.
    st = OrderState()
    assert st.apply(OrderEvent.rejected()) is True
    with pytest.raises(IllegalStatusTransition):
        st.apply(OrderEvent.cancelled())
    assert st.status is OrderStatus.REJECTED

    # A filled order rejects a FILL (overfill) and any non-matching terminal.
    st = OrderState()
    st.apply(OrderEvent.submitted(Decimal("10")))
    st.apply(OrderEvent.accepted())
    st.apply(OrderEvent.fill(Decimal("10"), True))
    with pytest.raises(IllegalStatusTransition):
        st.apply(OrderEvent.cancelled())


def test_qty_eps() -> None:
    assert QTY_EPS == Decimal("1e-9")
