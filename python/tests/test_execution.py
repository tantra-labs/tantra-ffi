# wheel surface (ex 0006): Decimal-canonical execution tests
# stand-in closure for tantra-examples gap 0006

"""Tests for the Decimal-canonical execution wheel surface."""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from tantra.execution import (
    Accepted,
    AdaptedPort,
    BaseExecutionPort,
    CancelRequested,
    Cancelled,
    ExecutionEvent,
    Expired,
    Fill,
    LegacyPortEvents,
    OrderRejection,
    Rejected,
    Submitted,
    adapt_port,
    cancel_order,
    event_from_rejection,
    event_order_id,
    events_from_native,
    order_event,
    rejection_from_event,
)
from tantra.instrument import InstrumentId
from tantra.money import Currency, Money
from tantra.order import OrderIntent, OrderSide
from tantra.order_state import OrderEvent
from tantra.trade import Trade


def _intent(qty: str | Decimal = "10") -> OrderIntent:
    return OrderIntent(InstrumentId("RELIANCE", "NSE"), OrderSide.BUY, qty)


def _trade(
    qty: str | Decimal = "10",
    price: str | Decimal = "2500.50",
    order_id: str = "o1",
) -> Trade:
    return Trade(
        InstrumentId("RELIANCE", "NSE"), OrderSide.BUY, qty, price, ts=42, order_id=order_id
    )


def test_all_event_dataclasses_are_frozen() -> None:
    intent = _intent()
    trade = _trade()
    cases: list[tuple[ExecutionEvent, str]] = [
        (Submitted("o1", intent, 1), "order_id"),
        (Accepted("o1", intent, 1), "order_id"),
        (Rejected("o1", intent, "bad", 1), "order_id"),
        (Fill(trade, Decimal("10"), True), "cum_qty"),
        (CancelRequested("o1", 1), "order_id"),
        (Cancelled("o1", intent, 1), "order_id"),
        (Expired("o1", intent, 1), "order_id"),
    ]
    for ev, field in cases:
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(ev, field, "nope")


def test_fill_quantities_are_decimal() -> None:
    fill = Fill(_trade(Decimal("5")), Decimal("5"), False)
    assert isinstance(fill.trade.quantity, Decimal)
    assert isinstance(fill.cum_qty, Decimal)
    assert fill.trade.quantity == Decimal("5")
    assert fill.cum_qty == Decimal("5")


def test_order_rejection_rejects_empty_order_id() -> None:
    with pytest.raises(ValueError):
        OrderRejection("", _intent(), "bad")


def test_order_rejection_cancelled_reason_agreement() -> None:
    intent = _intent()
    with pytest.raises(ValueError):
        OrderRejection("o1", intent, "bad", cancelled=True)
    with pytest.raises(ValueError):
        OrderRejection("o1", intent, "cancelled", cancelled=False)
    cancelled = OrderRejection("o1", intent, "cancelled", cancelled=True)
    assert cancelled.cancelled and cancelled.reason == "cancelled"
    rejected = OrderRejection("o1", intent, "bad")
    assert not rejected.cancelled and rejected.reason == "bad"


def test_order_event_projection() -> None:
    intent = _intent()
    trade = _trade(Decimal("4"))
    assert order_event(Submitted("o1", intent, 1)) == OrderEvent.submitted(Decimal("10"))
    assert order_event(Accepted("o1", intent, 1)) == OrderEvent.accepted()
    assert order_event(Rejected("o1", intent, "bad", 1)) == OrderEvent.rejected()
    assert order_event(Fill(trade, Decimal("10"), False)) == OrderEvent.fill(Decimal("4"), False)
    assert order_event(Fill(trade, Decimal("10"), True)) == OrderEvent.fill(Decimal("4"), True)
    assert order_event(CancelRequested("o1", 1)) == OrderEvent.cancel_requested()
    assert order_event(Cancelled("o1", intent, 1)) == OrderEvent.cancelled()
    assert order_event(Expired("o1", intent, 1)) == OrderEvent.expired()


def test_events_from_native_fill_round_trip() -> None:
    events = events_from_native(
        [
            {
                "kind": "fill",
                "order_id": "o1",
                "symbol": "RELIANCE",
                "exchange": "NSE",
                "side": "buy",
                "quantity": "10",
                "price": "2500.50",
                "costs": 253,
                "cum_qty": "10",
                "complete": True,
                "ts": 42,
                "venue_order_id": "V1",
            }
        ]
    )
    assert len(events) == 1
    fill = events[0]
    assert isinstance(fill, Fill)
    assert str(fill.trade.instrument_id) == "RELIANCE.NSE"
    assert fill.trade.side is OrderSide.BUY
    assert isinstance(fill.trade.quantity, Decimal)
    assert isinstance(fill.trade.price, Decimal)
    assert fill.trade.quantity == Decimal("10")
    assert fill.trade.price == Decimal("2500.50")
    assert fill.trade.ts == 42
    assert fill.trade.order_id == "o1"
    assert isinstance(fill.trade.costs, Money)
    assert fill.trade.costs.amount == Decimal("2.53")
    assert fill.trade.costs.currency is Currency.INR
    assert isinstance(fill.cum_qty, Decimal)
    assert fill.cum_qty == Decimal("10")
    assert fill.complete is True
    assert fill.venue_order_id == "V1"


def test_events_from_native_usd_costs_minor_units() -> None:
    events = events_from_native(
        [
            {
                "kind": "fill",
                "order_id": "o1",
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "side": "buy",
                "quantity": "10",
                "price": "100.00",
                "costs": 10000,
                "cum_qty": "10",
                "complete": True,
                "ts": 1,
            }
        ],
        currency=Currency.USD,
    )
    fill = events[0]
    assert isinstance(fill, Fill)
    assert fill.trade.costs.amount == Decimal("100.00")
    assert fill.trade.costs.currency is Currency.USD


def test_events_from_native_rejection_carries_reason() -> None:
    events = events_from_native(
        [
            {
                "kind": "rejected",
                "order_id": "o1",
                "symbol": "RELIANCE",
                "exchange": "NSE",
                "side": "sell",
                "quantity": "5",
                "reason": "insufficient margin",
                "ts": 7,
            }
        ]
    )
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, Rejected)
    assert ev.reason == "insufficient margin"
    assert ev.intent.side is OrderSide.SELL
    assert ev.intent.quantity == Decimal("5")


def test_events_from_native_cancel_requested() -> None:
    events = events_from_native([{"kind": "cancel_requested", "order_id": "o1", "ts": 9}])
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, CancelRequested)
    assert ev.order_id == "o1"
    assert ev.ts == 9


def test_events_from_native_user_id_mapping() -> None:
    events = events_from_native(
        [{"kind": "cancel_requested", "order_id": "ENG-1", "ts": 3}],
        user_id=lambda oid: oid.removeprefix("ENG-"),
    )
    assert events[0].order_id == "1"


def test_events_from_native_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        events_from_native(
            [
                {
                    "kind": "bogus",
                    "order_id": "o1",
                    "symbol": "RELIANCE",
                    "exchange": "NSE",
                    "side": "buy",
                    "quantity": "10",
                    "ts": 1,
                }
            ]
        )


def test_rejection_from_event_parity() -> None:
    intent = _intent()
    rejected = rejection_from_event(Rejected("o1", intent, "bad", 5))
    assert isinstance(rejected, OrderRejection)
    assert (rejected.order_id, rejected.reason, rejected.ts, rejected.cancelled) == (
        "o1",
        "bad",
        5,
        False,
    )
    cancelled = rejection_from_event(Cancelled("o1", intent, 6))
    assert isinstance(cancelled, OrderRejection)
    assert (cancelled.reason, cancelled.ts, cancelled.cancelled) == ("cancelled", 6, True)
    expired = rejection_from_event(Expired("o1", intent, 7))
    assert isinstance(expired, OrderRejection)
    assert (expired.reason, expired.ts, expired.cancelled) == ("expired", 7, False)
    assert rejection_from_event(Submitted("o1", intent, 1)) is None
    assert rejection_from_event(Accepted("o1", intent, 1)) is None
    assert rejection_from_event(Fill(_trade(Decimal("4")), Decimal("10"), True)) is None
    assert rejection_from_event(CancelRequested("o1", 1)) is None


def test_event_from_rejection_parity() -> None:
    intent = _intent()
    cancelled = event_from_rejection(
        OrderRejection("o1", intent, "cancelled", 6, cancelled=True)
    )
    assert isinstance(cancelled, Cancelled)
    assert cancelled.ts == 6
    rejected = event_from_rejection(OrderRejection("o1", intent, "bad", 5))
    assert isinstance(rejected, Rejected)
    assert rejected.reason == "bad"
    assert rejected.ts == 5


def test_event_order_id() -> None:
    assert event_order_id(Submitted("o1", _intent(), 1)) == "o1"
    assert event_order_id(Fill(_trade(), Decimal("10"), True)) == "o1"
    with pytest.raises(ValueError):
        event_order_id(Fill(_trade(order_id=""), Decimal("10"), True))


class _EventPort:
    def __init__(self) -> None:
        self._events: list[ExecutionEvent] = []
        self.submits: list[tuple[str, OrderIntent, int]] = []

    def submit(self, order_id: str, intent: OrderIntent, ts: int) -> None:
        self.submits.append((order_id, intent, ts))

    def cancel(self, order_id: str, now: int) -> None:
        pass

    def drain_events(self) -> list[ExecutionEvent]:
        out, self._events = self._events, []
        return out


def test_adapt_port_event_port_passthrough() -> None:
    port = _EventPort()
    adapted = adapt_port(port)
    assert adapted._events is None
    intent = _intent()
    adapted.submit("o1", intent, 1)
    assert port.submits == [("o1", intent, 1)]
    assert adapted.cancel("o1", 1) is True
    port._events.append(Submitted("o1", intent, 1))
    assert adapted.drain_events() == [Submitted("o1", intent, 1)]


class _FillsLegacyPort:
    def __init__(self) -> None:
        self.trades: list[Trade] = []

    def submit(self, order_id: str, intent: OrderIntent, ts: int) -> None:
        pass

    def drain_fills(self) -> list[Trade]:
        out, self.trades = self.trades, []
        return out


def test_adapt_port_legacy_fills_derives_cum_qty_complete() -> None:
    iid = InstrumentId("RELIANCE", "NSE")
    side = OrderSide.BUY
    port = _FillsLegacyPort()
    adapted = adapt_port(port)
    assert isinstance(adapted._events, LegacyPortEvents)
    adapted.submit("o1", OrderIntent(iid, side, Decimal("10")), 1)
    port.trades.append(Trade(iid, side, Decimal("4"), Decimal("100"), order_id="o1"))
    port.trades.append(Trade(iid, side, Decimal("6"), Decimal("101"), order_id="o1"))
    events = adapted.drain_events()
    assert [type(ev) for ev in events] == [Fill, Fill]
    assert events[0].cum_qty == Decimal("4")
    assert events[0].complete is False
    assert events[1].cum_qty == Decimal("10")
    assert events[1].complete is True


class _LegacyCancelPort:
    def __init__(self) -> None:
        self.cancelled: list[str] = []

    def submit(self, order_id: str, intent: OrderIntent, ts: int) -> None:
        pass

    def drain_fills(self) -> list[Trade]:
        return []

    def cancel(self, order_id: str) -> None:
        self.cancelled.append(order_id)


def test_cancel_order_adapts_one_arg_legacy_cancel() -> None:
    port = _LegacyCancelPort()
    with pytest.warns(DeprecationWarning):
        assert cancel_order(port, "o1") is True
    assert port.cancelled == ["o1"]


def test_adapt_port_one_arg_legacy_cancel_warns() -> None:
    port = _LegacyCancelPort()
    with pytest.warns(DeprecationWarning):
        adapted = adapt_port(port)
    assert adapted.cancel("o2", 5) is True
    assert port.cancelled == ["o2"]


def test_base_port_defaults_are_inert() -> None:
    class P(BaseExecutionPort):
        def submit(self, order_id: str, intent: OrderIntent, ts: int) -> None:
            pass

    p = P()
    assert p.cancel("o1", 1) is None
    assert p.drain_events() == []
    assert p.drain_fills() == []
    assert p.drain_rejections() == []


def test_base_port_buffered_shim_splits_without_loss() -> None:
    class P(BaseExecutionPort):
        def __init__(self) -> None:
            self._q: list[ExecutionEvent] = []

        def submit(self, order_id: str, intent: OrderIntent, ts: int) -> None:
            pass

        def drain_events(self) -> list[ExecutionEvent]:
            out, self._q = self._q, []
            return out

    p = P()
    iid = InstrumentId("RELIANCE", "NSE")
    intent = OrderIntent(iid, OrderSide.BUY, Decimal("10"))
    p._q = [
        Submitted("o1", intent, 1),
        Fill(Trade(iid, OrderSide.BUY, Decimal("4"), Decimal("100"), order_id="o1"),
             Decimal("4"), False),
        Rejected("o2", intent, "bad", 2),
        Cancelled("o3", intent, 3),
        Expired("o4", intent, 4),
    ]
    fills = p.drain_fills()
    assert [t.order_id for t in fills] == ["o1"]
    rejections = p.drain_rejections()
    assert [r.order_id for r in rejections] == ["o2", "o3", "o4"]
    assert [r.reason for r in rejections] == ["bad", "cancelled", "expired"]
    assert p.drain_fills() == []
    assert p.drain_rejections() == []


def test_money_from_minor() -> None:
    assert Money.from_minor(253, Currency.INR).amount == Decimal("2.53")
    assert Money.from_minor("10000", Currency.USD).amount == Decimal("100.00")
    assert Money.from_minor(Decimal("1"), Currency.INR).amount == Decimal("0.01")
    assert Money.from_minor(0).amount == Decimal("0.00")
