"""Tests for the wheel broker-adapter framework (tantra-examples gap 0007 closure).

The promoted ``tantra.adapters`` namespace ships the adapter contract, the registry, the
rate limiter, the order-event reducer and ``FakeAdapter`` (the in-memory reference
implementation). The contract suite itself is the certification; these tests exercise the
wheel surface end to end.
"""

import asyncio
from decimal import Decimal

import pytest
from tantra.adapters.base import Adapter, MarketDataClient
from tantra.adapters.capabilities import AdapterCapabilities, Capability
from tantra.adapters.contract import verify_adapter_contract
from tantra.adapters.errors import AdapterError, AdapterNotFound, CapabilityError
from tantra.adapters.models import OrderReport, Product, RunMode, SessionInfo
from tantra.adapters.order_events import reduce_order_report
from tantra.adapters.rate_limit import InMemoryBucket, RateLimiter, RateLimitExceeded
from tantra.adapters.registry import (
    AdapterRegistry,
    available_adapters,
    default_registry,
    register_adapter,
    resolve_adapter,
)
from tantra.adapters.testing import FakeAdapter
from tantra.execution import Fill, Rejected
from tantra.instrument import InstrumentId
from tantra.order import OrderIntent, OrderSide, OrderStatus


def test_fake_adapter_passes_verify_adapter_contract() -> None:
    asyncio.run(verify_adapter_contract(FakeAdapter()))


class _ExecutionOnly(Adapter):
    """A minimal lifecycle+execution facade with *no* market-data role."""

    name = "exec-only"

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            name=self.name, features=frozenset({Capability.PLACE_ORDER})
        )

    async def connect(self) -> SessionInfo:
        return SessionInfo(user_id="EXEC_ONLY", mode=RunMode.LIVE)

    async def disconnect(self) -> None:
        return None

    def is_connected(self) -> bool:
        return True

    async def session(self) -> SessionInfo:
        return SessionInfo(user_id="EXEC_ONLY", mode=RunMode.LIVE)


def test_registry_roundtrip_through_default_registry() -> None:
    name = "wheeltest-fake"
    default_registry().unregister(name)
    register_adapter(name, FakeAdapter)
    try:
        assert name in available_adapters()
        adapter = resolve_adapter(name)
        assert isinstance(adapter, FakeAdapter)
    finally:
        default_registry().unregister(name)
    assert name not in available_adapters()


def test_adapter_not_found_names_installed_alternatives() -> None:
    name = "wheeltest-fake"
    default_registry().unregister(name)
    register_adapter(name, FakeAdapter)
    try:
        with pytest.raises(AdapterNotFound) as excinfo:
            resolve_adapter("wheeltest-nope")
        assert name in str(excinfo.value)
    finally:
        default_registry().unregister(name)


def test_duplicate_registration_is_a_typed_error() -> None:
    registry = AdapterRegistry()
    registry.register("dup", FakeAdapter)
    with pytest.raises(AdapterError):
        registry.register("dup", FakeAdapter)


def test_create_market_data_requires_the_market_data_role() -> None:
    registry = AdapterRegistry()
    registry.register("exec-only", _ExecutionOnly)
    # A role mismatch is a typed AdapterError (CapabilityError is a subclass), never a raw
    # AttributeError or TypeError.
    with pytest.raises(AdapterError):
        registry.create_market_data("exec-only")
    registry.register("fake", FakeAdapter)
    client = registry.create_market_data("fake")
    assert isinstance(client, MarketDataClient)


def test_refused_capability_surfaces_as_capability_error() -> None:
    async def probe() -> None:
        fake = FakeAdapter()
        await fake.connect()
        try:
            # FakeAdapter declares no DEPTH capability; the refusal is a typed error.
            with pytest.raises(CapabilityError):
                await fake.depth(InstrumentId("RELIANCE", "NSE"))
        finally:
            await fake.disconnect()

    asyncio.run(probe())


def test_rate_limiter_try_acquire_and_refill() -> None:
    store = InMemoryBucket()
    limiter = RateLimiter(capacity=2.0, refill_rate=1.0, key="orders", store=store)
    assert limiter.try_acquire(1.0, now_ns=0) is True
    assert limiter.try_acquire(1.0, now_ns=0) is True
    assert limiter.try_acquire(1.0, now_ns=0) is False
    # One second later one token has refilled.
    assert limiter.try_acquire(1.0, now_ns=1_000_000_000) is True


def test_rate_limiter_acquire_blocks_until_refill() -> None:
    async def consume() -> None:
        limiter = RateLimiter(capacity=1.0, refill_rate=1.0, key="orders")
        assert limiter.try_acquire(1.0, now_ns=0) is True
        assert limiter.try_acquire(1.0, now_ns=0) is False

    asyncio.run(consume())


def test_rate_limiter_empty_no_refill_raises() -> None:
    async def consume() -> None:
        limiter = RateLimiter(capacity=1.0, refill_rate=0.0, key="orders")
        assert limiter.try_acquire(1.0, now_ns=0) is True
        with pytest.raises(RateLimitExceeded):
            await limiter.acquire(1.0)

    asyncio.run(consume())


def _filled_report(order_id: str = "o1") -> OrderReport:
    return OrderReport(
        order_id=order_id,
        instrument_id=InstrumentId("RELIANCE", "NSE"),
        side=OrderSide.BUY,
        quantity=Decimal(10),
        status=OrderStatus.FILLED,
        product=Product.DELIVERY,
        filled_quantity=Decimal(10),
        average_price=Decimal("2450.55"),
        ts_event=2,
    )


def test_reduce_order_report_first_sighting_of_a_fill() -> None:
    reduction = reduce_order_report(None, _filled_report())
    assert reduction.flagged is False
    assert len(reduction.events) == 1
    fill = reduction.events[0]
    assert isinstance(fill, Fill)
    assert fill.complete is True
    assert fill.trade.quantity == Decimal(10)


def test_reduce_order_report_rejection_emits_rejected() -> None:
    rejected = OrderReport(
        order_id="o2",
        instrument_id=InstrumentId("RELIANCE", "NSE"),
        side=OrderSide.SELL,
        quantity=Decimal(10),
        status=OrderStatus.REJECTED,
        product=Product.DELIVERY,
        reject_reason="insufficient funds",
        ts_event=3,
    )
    reduction = reduce_order_report(None, rejected)
    assert reduction.flagged is False
    assert len(reduction.events) == 1
    assert isinstance(reduction.events[0], Rejected)


def test_reduce_order_report_backwards_move_is_flagged() -> None:
    prev = OrderReport(
        order_id="o3",
        instrument_id=InstrumentId("RELIANCE", "NSE"),
        side=OrderSide.BUY,
        quantity=Decimal(10),
        status=OrderStatus.ACCEPTED,
        product=Product.DELIVERY,
        filled_quantity=Decimal(10),
        average_price=Decimal("2450.55"),
        ts_event=4,
    )
    new = OrderReport(
        order_id="o3",
        instrument_id=InstrumentId("RELIANCE", "NSE"),
        side=OrderSide.BUY,
        quantity=Decimal(10),
        status=OrderStatus.ACCEPTED,
        product=Product.DELIVERY,
        filled_quantity=Decimal(5),
        average_price=Decimal("2450.55"),
        ts_event=5,
    )
    reduction = reduce_order_report(prev, new)
    assert reduction.flagged is True
    assert reduction.events == ()


def test_client_order_id_replay_is_idempotent() -> None:
    async def replay() -> None:
        fake = FakeAdapter()
        await fake.connect()
        try:
            intent = OrderIntent.market_buy(
                InstrumentId("RELIANCE", "NSE"), Decimal(10)
            )
            first = await fake.place_order(
                intent, product=Product.DELIVERY, client_order_id="replay-1"
            )
            orders_before = len(await fake.orders())
            trades_before = len(await fake.trades())
            again = await fake.place_order(
                intent, product=Product.DELIVERY, client_order_id="replay-1"
            )
            assert again.order_id == first.order_id
            assert len(await fake.orders()) == orders_before
            assert len(await fake.trades()) == trades_before
        finally:
            await fake.disconnect()

    asyncio.run(replay())
