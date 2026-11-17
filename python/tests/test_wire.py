"""Tests for the wheel `tantra.wire` pydantic wire-contract models (gap 0006 wire slice)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
import tantra
from pydantic import TypeAdapter, ValidationError
from tantra.instrument import InstrumentId
from tantra.money import Currency, Money
from tantra.order import OrderIntent, OrderSide, OrderType, TimeInForce
from tantra.wire import (
    ENUMS,
    MODELS,
    BarAggregation,
    BarEvent,
    BarSpecification,
    BarType,
    ClassificationFilter,
    Event,
    FilterOp,
    MarketCapBucket,
    Message,
    MetricPeriod,
    MetricRef,
    PriceType,
    QuoteEvent,
    RelativeStat,
    RelativeToIndex,
    ScreenerFilterGroup,
    ScreenerFilterPredicate,
    ScreenerRow,
    ScreenerScanRequest,
    Timeframe,
    UnixNanos,
    loads,
)
from tantra.wire import (
    InstrumentId as WireInstrumentId,
)
from tantra.wire import (
    Order as WireOrder,
)
from tantra.wire import (
    OrderIntent as WireOrderIntent,
)
from tantra.wire.wire import Money as WireMoney


def test_unix_nanos_from_ns_roundtrip() -> None:
    ts = UnixNanos.from_ns(1_700_000_000_123_456_789)
    assert ts.unix_nanos == "1700000000123456789"
    assert ts.to_ns() == 1_700_000_000_123_456_789


@pytest.mark.parametrize("bad", [True, False, -1, 2**64, 1.5, "7"])
def test_unix_nanos_from_ns_rejects_non_u64(bad: Any) -> None:
    with pytest.raises(ValueError):
        UnixNanos.from_ns(bad)


@pytest.mark.parametrize("bad", ["18446744073709551616", "-1", "abc", ""])
def test_unix_nanos_rejects_non_u64_string(bad: str) -> None:
    with pytest.raises(ValueError):
        UnixNanos(iso="1970-01-01T00:00:00.000000000Z", unix_nanos=bad)


def test_instrument_id_roundtrip() -> None:
    dom = InstrumentId("RELIANCE", "NSE")
    wire = WireInstrumentId.from_domain(dom)
    assert (wire.symbol, wire.exchange) == ("RELIANCE", "NSE")
    assert wire.to_domain() == dom


def test_money_from_domain_minor_units() -> None:
    wire = WireMoney.from_domain(Money(Decimal("2450.50"), Currency.INR))
    assert wire.amount == 245050
    assert wire.currency is Currency.INR


def test_money_to_domain_major_units() -> None:
    back = WireMoney.from_domain(Money(Decimal("2450.50"), Currency.INR)).to_domain()
    assert back.amount == Decimal("2450.50")
    assert back.currency is Currency.INR


def test_money_legacy_major_float() -> None:
    wire = WireMoney.model_validate({"amount": 2450.5, "currency": Currency.INR})
    assert wire.amount == 245050


def test_order_intent_roundtrip() -> None:
    dom = OrderIntent.limit_buy(
        InstrumentId("RELIANCE", "NSE"), Decimal(10), Decimal("2450.50")
    )
    wire = WireOrderIntent.from_domain(dom)
    back = wire.to_domain()
    assert back == dom
    assert isinstance(back.quantity, Decimal)
    assert isinstance(back.price, Decimal)


def test_order_intent_limit_requires_price() -> None:
    with pytest.raises(ValidationError):
        WireOrderIntent(
            instrument_id=WireInstrumentId(symbol="RELIANCE", exchange="NSE"),
            side=OrderSide.BUY,
            quantity=10.0,
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
        )


def test_order_intent_trailing_stop_exactly_one_trail() -> None:
    with pytest.raises(ValidationError):
        WireOrderIntent(
            instrument_id=WireInstrumentId(symbol="RELIANCE", exchange="NSE"),
            side=OrderSide.SELL,
            quantity=10.0,
            order_type=OrderType.TRAILING_STOP,
            time_in_force=TimeInForce.DAY,
            trail_amount=1.0,
            trail_percent=0.5,
        )


def test_order_intent_dump_omits_none_trail() -> None:
    wire = WireOrderIntent.from_domain(
        OrderIntent.market_buy(InstrumentId("RELIANCE", "NSE"), Decimal(10))
    )
    data = wire.model_dump()
    assert "trail_amount" not in data
    assert "trail_percent" not in data


def _wire_order(**kwargs: Any) -> WireOrder:
    fields: dict[str, Any] = {
        "order_id": "o1",
        "instrument_id": WireInstrumentId(symbol="RELIANCE", exchange="NSE"),
        "side": "buy",
        "order_type": "market",
        "quantity": 10.0,
        "status": "submitted",
        "time_in_force": "day",
        "ts_event": UnixNanos.from_ns(1),
        "ts_init": UnixNanos.from_ns(1),
    }
    fields.update(kwargs)
    return WireOrder(**fields)


def test_order_cancel_requested_only_when_working() -> None:
    with pytest.raises(ValidationError):
        _wire_order(status="filled", cancel_requested=True)


def test_order_filled_qty_must_not_exceed_quantity() -> None:
    with pytest.raises(ValidationError):
        _wire_order(status="filled", filled_qty=11.0)


def test_order_dump_omits_optional_unset() -> None:
    data = _wire_order().model_dump()
    for key in (
        "filled_qty",
        "avg_fill_price",
        "reject_reason",
        "filled_at",
        "cancel_requested",
    ):
        assert key not in data


def _bar_event() -> BarEvent:
    return BarEvent(
        bar_type=BarType(
            instrument_id=WireInstrumentId(symbol="RELIANCE", exchange="NSE"),
            spec=BarSpecification(
                step=1,
                aggregation=BarAggregation.MINUTE,
                price_type=PriceType.LAST,
            ),
        ),
        open=100.0,
        high=105.0,
        low=99.0,
        close=104.0,
        volume=1000.0,
        ts_event=UnixNanos.from_ns(1),
        ts_init=UnixNanos.from_ns(1),
    )


def test_message_wrap_stamps_schema_version() -> None:
    msg = Message.wrap(_bar_event(), 2)
    assert msg.schema_version == tantra.SCHEMA_VERSION
    assert msg.ts_init.to_ns() == 2


def test_message_rejects_wrong_schema_version() -> None:
    with pytest.raises(ValueError):
        Message(
            schema_version=tantra.SCHEMA_VERSION + 1,
            event=_bar_event(),
            ts_init=UnixNanos.from_ns(2),
        )


def test_event_discriminates_on_type() -> None:
    ev = TypeAdapter(Event).validate_python(
        {
            "type": "quote",
            "instrument_id": {"symbol": "RELIANCE", "exchange": "NSE"},
            "bid_price": 100.0,
            "ask_price": 100.5,
            "bid_size": 10.0,
            "ask_size": 12.0,
            "ts_event": {"iso": "1970-01-01T00:00:00.000000001Z", "unix_nanos": "1"},
            "ts_init": {"iso": "1970-01-01T00:00:00.000000001Z", "unix_nanos": "1"},
        }
    )
    assert isinstance(ev, QuoteEvent)


def test_loads_order_intent() -> None:
    intent = loads(
        "OrderIntent",
        '{"instrument_id": {"symbol": "RELIANCE", "exchange": "NSE"},'
        ' "side": "buy", "quantity": 10.0, "order_type": "market",'
        ' "time_in_force": "day"}',
    )
    assert intent.side == OrderSide.BUY
    assert intent.quantity == 10.0


def test_loads_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        loads("bogus", "{}")


def test_loads_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError):
        loads("UnixNanos", '{"iso": "a", "unix_nanos": "1", "unix_nanos": "2"}')


def test_loads_rejects_nan_literal() -> None:
    with pytest.raises(ValueError):
        loads(
            "OrderIntent",
            '{"instrument_id": {"symbol": "RELIANCE", "exchange": "NSE"},'
            ' "side": "buy", "quantity": NaN, "order_type": "market",'
            ' "time_in_force": "day"}',
        )


def test_screener_scan_request_aliases() -> None:
    req = ScreenerScanRequest(market="NSE", primaryOnly=False, columnSet="summary")
    assert req.primary_only is False
    assert req.column_set == "summary"
    data = req.model_dump(by_alias=True)
    assert data["primaryOnly"] is False
    assert data["columnSet"] == "summary"


def test_screener_row_full_symbol_alias() -> None:
    row = ScreenerRow(
        fullSymbol="NSE:RELIANCE-EQ",
        instrumentId="NSE:RELIANCE-EQ",
        name="Reliance Industries",
        values={},
    )
    assert row.full_symbol == "NSE:RELIANCE-EQ"
    assert row.instrument_id == "NSE:RELIANCE-EQ"
    data = row.model_dump(by_alias=True)
    assert data["fullSymbol"] == "NSE:RELIANCE-EQ"


def test_screener_predicate_between_requires_pair() -> None:
    with pytest.raises(ValidationError):
        ScreenerFilterPredicate(key="PE", op=FilterOp.BETWEEN, value=[10.0])


def test_screener_predicate_crosses_above_accepts_metric_ref() -> None:
    p = ScreenerFilterPredicate(
        key="SMA50", op=FilterOp.CROSSES_ABOVE, value={"key": "SMA200"}
    )
    assert isinstance(p.value, MetricRef)
    assert p.value.key == "SMA200"


def test_models_and_enums_expected_keys() -> None:
    for key in (
        "UnixNanos",
        "InstrumentId",
        "Bar",
        "Order",
        "OrderIntent",
        "Trade",
        "Position",
        "Event",
        "Message",
        "ScreenerFilterPredicate",
    ):
        assert key in MODELS
    for key in (
        "OrderSide",
        "OrderType",
        "OrderStatus",
        "TimeInForce",
        "BarAggregation",
        "PriceType",
        "AggressorSide",
        "PositionSide",
        "Currency",
    ):
        assert key in ENUMS


def test_screener_filter_op_ne_and_legacy_neq_alias() -> None:
    pred = ScreenerFilterPredicate.model_validate({"key": "flag", "op": "neq", "value": 0})
    assert pred.op is FilterOp.NE
    assert pred.model_dump()["op"] == FilterOp.NE


def test_screener_classification_relative_and_nested_group() -> None:
    nested_items: list[ScreenerFilterPredicate | ScreenerFilterGroup | dict[str, Any]] = [
        ScreenerFilterPredicate(
            key="SMA50",
            op=FilterOp.CROSSES_ABOVE,
            value={"key": "SMA200"},
            timeframe=Timeframe.D1,
        ),
        ScreenerFilterPredicate(
            key="pe",
            op=FilterOp.LT,
            value={"key": "pe", "period": "ttm"},
            relative_to="sector",
            relative_stat=RelativeStat.MEDIAN,
        ),
    ]
    nested = ScreenerFilterGroup(operator="OR", items=nested_items)
    root_items: list[ScreenerFilterPredicate | ScreenerFilterGroup | dict[str, Any]] = [
        nested,
        ScreenerFilterPredicate(
            key="return_3m",
            op=FilterOp.GT,
            value=Decimal(0),
            relative_to=RelativeToIndex(index="  nifty500 "),
            relative_stat=RelativeStat.RETURN_DELTA,
        ),
    ]
    root = ScreenerFilterGroup(
        operator="AND",
        items=root_items,
        classification=ClassificationFilter(
            sector="  Financial   Services ",
            industry="Banks",
            cap_bucket=MarketCapBucket.LARGE,
            index="nifty50",
            theme="AI_EXPORT",
        ),
    )
    assert root.classification is not None
    assert root.classification.sector == "Financial Services"
    assert root.classification.cap_bucket is MarketCapBucket.LARGE
    assert root.classification.index == "NIFTY50"
    assert isinstance(root.items[1], ScreenerFilterPredicate)
    assert root.items[1].relative_to == RelativeToIndex(index="NIFTY500")
    assert root.items[1].period is None


def test_screener_metric_period_cadence_aliases() -> None:
    pred = ScreenerFilterPredicate.model_validate(
        {"key": "close", "op": "gt", "value": "100", "period": "d1"}
    )
    assert pred.period is MetricPeriod.DAILY
