"""Tests for the Decimal-canonical kernel strategy base layer (ex 0006).

Covers ``tantra.base`` (Parameter, Strategy, StockSharp primitives),
``tantra.context`` (StrategyContext / LedgerContext) and the ``whole_shares``
sizing helper. All financial quantities are asserted as exact ``Decimal``.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tantra.base import (
    ArbitrageStrategy,
    Parameter,
    QuotingStrategy,
    RebalancingStrategy,
    SlicingStrategy,
    Strategy,
)
from tantra.context import LedgerContext, StrategyContext
from tantra.instrument import Instrument, InstrumentId, InstrumentKind
from tantra.money import Currency, Money
from tantra.order import OrderIntent, OrderSide
from tantra.sizing import Sizer, whole_shares
from tantra.trade import Trade

IID = InstrumentId("RELIANCE", "NSE")
IID2 = InstrumentId("TCS", "NSE")


# ===========================================================================
# Parameter
# ===========================================================================


class _ParamStrat(Strategy):
    name = "param_test"
    fast = Parameter(default=20, min=5, max=50, step=5, description="Fast SMA")


def test_parameter_descriptor_default_read() -> None:
    strat = _ParamStrat()
    assert strat.fast == 20
    assert _ParamStrat.fast is _ParamStrat._declared_parameters["fast"]
    assert _ParamStrat.fast.name == "fast"
    assert _ParamStrat.fast.description == "Fast SMA"


def test_parameter_range_string_parsing() -> None:
    p = Parameter(default=20, range="5:50:5")
    assert p.min == 5
    assert p.max == 50
    assert p.step == 5
    assert p.range_str == "5:50:5"


def test_parameter_range_string_float_parts() -> None:
    p = Parameter(default=0.5, range="0.1:1.0:0.1")
    assert p.min == 0.1
    assert p.max == 1.0
    assert p.step == 0.1


def test_parameter_range_tuple() -> None:
    p = Parameter(default=20, range=(5, 50, 5))
    assert p.min == 5
    assert p.max == 50
    assert p.step == 5
    assert p.range_str == "5:50:5"


def test_parameter_min_max_value_error() -> None:
    with pytest.raises(ValueError):
        Parameter(default=20, min=50, max=5)


def test_parameter_step_zero_value_error() -> None:
    with pytest.raises(ValueError):
        Parameter(default=20, min=5, max=50, step=0)


def test_parameter_default_out_of_bounds_value_error() -> None:
    with pytest.raises(ValueError):
        Parameter(default=60, min=5, max=50)


def test_parameter_discrete_values() -> None:
    p = Parameter(default=10, range="10:20:5")
    assert p.discrete_values() == [10, 15, 20]
    p_float = Parameter(default=0.5, range="0.1:1.0:0.1")
    vals = p_float.discrete_values()
    assert len(vals) == 10
    assert vals[-1] == 1.0
    p_values = Parameter(default=3, values=[1, 2, 3])
    assert p_values.discrete_values() == [1, 2, 3]
    p_plain = Parameter(default=7)
    assert p_plain.discrete_values() == [7]


# ===========================================================================
# Strategy
# ===========================================================================


class NoNameStrategy(Strategy):
    pass


class TradingStrategy(Strategy):
    name = "trading"
    fast = Parameter(default=10, min=5, max=50, step=5)


def test_strategy_requires_name() -> None:
    with pytest.raises(TypeError):
        NoNameStrategy()


def test_strategy_constructs_with_ledger_context() -> None:
    strat = TradingStrategy()
    assert isinstance(strat.ctx, LedgerContext)
    assert strat.ctx.cash().amount == Decimal(0)
    assert strat.hyperparameters()["fast"].default == 10


def test_strategy_hooks_default_noop() -> None:
    strat = TradingStrategy()
    assert strat.on_start() is None
    assert strat.setup() is None
    assert strat.on_stop() is None
    assert strat.on_fill(Trade(IID, OrderSide.BUY, "1", "100")) is None
    assert strat.busy(IID) is False
    assert strat.position(IID) == Decimal(0)


def test_strategy_buy_sell_submit_intents() -> None:
    strat = TradingStrategy()
    strat.buy(IID, "10")
    strat.sell(IID2, "5")
    intents = strat.drain_intents()
    assert len(intents) == 2
    assert intents[0].side is OrderSide.BUY
    assert intents[0].quantity == Decimal("10")
    assert isinstance(intents[0].quantity, Decimal)
    assert intents[1].side is OrderSide.SELL
    assert intents[1].quantity == Decimal("5")
    assert strat.ctx.pending_quantity(IID) == Decimal("10")
    assert strat.ctx.pending_quantity(IID2) == Decimal("5")


def test_strategy_legacy_handle_fill_roundtrip() -> None:
    strat = TradingStrategy()
    strat.buy(IID, "10")
    strat.drain_intents()
    strat.handle_fill(Trade(IID, OrderSide.BUY, Decimal("10"), Decimal("2500.5")))
    assert strat.position(IID) == Decimal("10")
    assert strat.ctx.cash().to_major() == Decimal(0) - Decimal("25005.0")
    assert strat.ctx.pending_quantity(IID) == Decimal(0)
    assert strat.busy(IID) is False


def test_strategy_legacy_handle_rejected_roundtrip() -> None:
    strat = TradingStrategy()
    strat.buy(IID, "10")
    intents = strat.drain_intents()
    assert strat.busy(IID) is True
    strat.handle_rejected(intents[0])
    assert strat.busy(IID) is False
    assert strat.ctx.pending_quantity(IID) == Decimal(0)
    assert strat.position(IID) == Decimal(0)


def test_strategy_log_event_does_not_raise() -> None:
    strat = TradingStrategy()
    strat.log_event("EVENT_TEST", "hello", key="value")
    strat.log_event("EVENT_BUY", symbol=IID.symbol, qty=Decimal("10"))


# ===========================================================================
# LedgerContext
# ===========================================================================


def test_ledger_submit_and_drain() -> None:
    ctx = LedgerContext(cash="100000")
    intent = OrderIntent.market_buy(IID, "10")
    ctx.submit(intent)
    assert ctx.pending_quantity(IID) == Decimal("10")
    assert ctx.busy(IID) is True
    intents = ctx.drain_intents()
    assert intents == [intent]
    assert ctx.pending_quantity(IID) == Decimal("10")


def test_ledger_apply_fill_buy() -> None:
    ctx = LedgerContext(cash="100000")
    ctx.submit(OrderIntent.market_buy(IID, "10"))
    ctx.drain_intents()
    ctx.apply_fill(Trade(IID, OrderSide.BUY, Decimal("10"), Decimal("2500.5")))
    assert ctx.position(IID) == Decimal("10")
    assert ctx.cash().to_major() == Decimal("100000") - Decimal("25005.0")
    assert ctx.pending_quantity(IID) == Decimal(0)
    assert ctx.busy(IID) is False
    assert isinstance(ctx.cash(), Money)


def test_ledger_apply_fill_sell() -> None:
    ctx = LedgerContext(cash="100000")
    ctx.submit(OrderIntent.market_sell(IID, "5"))
    ctx.drain_intents()
    ctx.apply_fill(Trade(IID, OrderSide.SELL, Decimal("5"), Decimal("2500.5")))
    assert ctx.position(IID) == Decimal("-5")
    assert ctx.cash().to_major() == Decimal("100000") + Decimal("12502.5")
    assert ctx.pending_quantity(IID) == Decimal(0)


def test_ledger_apply_fill_with_costs() -> None:
    ctx = LedgerContext(cash="100000")
    ctx.submit(OrderIntent.market_buy(IID, "10"))
    ctx.drain_intents()
    costs = Money.from_major("20", Currency.INR)
    ctx.apply_fill(Trade(IID, OrderSide.BUY, Decimal("10"), Decimal("2500.5"), costs=costs))
    assert ctx.position(IID) == Decimal("10")
    assert ctx.cash().to_major() == Decimal("100000") - Decimal("25025.0")


def test_ledger_positions_ordered() -> None:
    ctx = LedgerContext(cash="100000")
    ctx.apply_fill(Trade(IID2, OrderSide.BUY, Decimal("5"), Decimal("100")))
    ctx.apply_fill(Trade(IID, OrderSide.BUY, Decimal("3"), Decimal("100")))
    assert list(ctx.positions().keys()) == [IID, IID2]
    assert ctx.positions()[IID2] == Decimal("5")


def test_ledger_release_frees_busy() -> None:
    ctx = LedgerContext()
    intent = OrderIntent.market_buy(IID, "10")
    ctx.submit(intent)
    assert ctx.busy(IID) is True
    ctx.drain_intents()
    ctx.release(intent)
    assert ctx.busy(IID) is False
    assert ctx.pending_quantity(IID) == Decimal(0)


def test_ledger_cancel_withdraws_unsent_intent() -> None:
    ctx = LedgerContext()
    intent = OrderIntent.market_buy(IID, "10")
    ctx.submit(intent)
    ctx.cancel(intent)
    assert ctx.drain_intents() == []
    assert ctx.busy(IID) is False
    assert ctx.pending_quantity(IID) == Decimal(0)


def test_ledger_note_order_closed_intent_of_is_open() -> None:
    ctx = LedgerContext()
    intent = OrderIntent.market_buy(IID, "10")
    ctx.submit(intent)
    ctx.drain_intents()
    ctx.note_order("o1", intent)
    assert ctx.intent_of("o1") is intent
    assert ctx.is_open(intent) is True
    ctx.note_closed("o1")
    assert ctx.is_open(intent) is False
    assert ctx.intent_of("o1") is intent


def test_ledger_set_now_and_instruments() -> None:
    ctx = LedgerContext()
    ctx.set_now(42)
    assert ctx.now() == 42
    inst = Instrument(IID, InstrumentKind.EQUITY, "1", "0.05")
    ctx.add_instrument(inst)
    assert ctx.instrument(IID) is inst
    assert ctx.instrument(IID2) is None
    assert ctx.currency is Currency.INR


# ===========================================================================
# StrategyContext bare stub defaults
# ===========================================================================


class _StubCtx(StrategyContext):
    def __init__(self, busy_state: bool) -> None:
        self._busy_state = busy_state

    def now(self) -> int:
        return 0

    def position(self, instrument_id: InstrumentId) -> Decimal:
        return Decimal(0)

    def positions(self) -> dict[InstrumentId, Decimal]:
        return {}

    def cash(self) -> Money:
        return Money.zero(Currency.INR)

    def busy(self, instrument_id: InstrumentId) -> bool:
        return self._busy_state

    def instrument(self, instrument_id: InstrumentId) -> Instrument | None:
        return None

    def submit(self, intent: OrderIntent) -> None:
        pass


def test_pending_quantity_default_infinity_while_busy() -> None:
    stub_busy = _StubCtx(busy_state=True)
    assert stub_busy.pending_quantity(IID) == Decimal("Infinity")
    stub_idle = _StubCtx(busy_state=False)
    assert stub_idle.pending_quantity(IID) == Decimal(0)
    assert stub_idle.is_open(OrderIntent.market_buy(IID, "1")) is True
    assert stub_idle.intent_of("nope") is None
    stub_idle.cancel(OrderIntent.market_buy(IID, "1"))  # default no-op, must not raise
    assert stub_idle.cash() == Money.zero(Currency.INR)


# ===========================================================================
# whole_shares
# ===========================================================================


def test_whole_shares() -> None:
    result = whole_shares("10000", "0.98", "2500.5")
    assert result == 3
    assert isinstance(result, int)


def test_whole_shares_invalid_allocation() -> None:
    with pytest.raises(ValueError):
        whole_shares("10000", "1.1", "2500.5")
    with pytest.raises(ValueError):
        whole_shares("10000", "0", "2500.5")
    with pytest.raises(ValueError):
        whole_shares("10000", "-0.5", "2500.5")


def test_whole_shares_invalid_price() -> None:
    with pytest.raises(ValueError):
        whole_shares("10000", "0.5", "0")
    with pytest.raises(ValueError):
        whole_shares("10000", "0.5", "-1")


def test_whole_shares_sizer_namespace() -> None:
    assert Sizer.whole_shares("10000", "0.98", "2500.5") == 3


# ===========================================================================
# StockSharp primitives (Decimal)
# ===========================================================================


def test_quoting_strategy_need_requote_and_update_quote() -> None:
    qs = QuotingStrategy(quoting_side="BUY", quoting_quantity="10", price_tolerance="0.05")
    assert qs.remaining_quantity == Decimal("10")
    assert qs.need_requote("2450.5", "10") is True
    intent = qs.update_quote(IID, "2450.5", "10")
    assert intent is not None
    assert intent.side is OrderSide.BUY
    assert intent.quantity == Decimal("10")
    assert intent.price == Decimal("2450.5")
    assert isinstance(intent.quantity, Decimal)
    assert isinstance(intent.price, Decimal)
    assert qs.quoted_price == Decimal("2450.5")
    # within tolerance: no requote, same active intent returned
    assert qs.need_requote("2450.52", "10") is False
    assert qs.update_quote(IID, "2450.52", "10") is intent
    # tolerance breach triggers a requote
    assert qs.need_requote("2450.6", "10") is True
    # drained intents carry the Decimal limit intent
    drained = qs.drain_intents()
    assert drained and drained[0].order_type.name == "LIMIT"


def test_quoting_strategy_sell_side() -> None:
    qs = QuotingStrategy(quoting_side="SELL", quoting_quantity="10", price_tolerance="0.05")
    intent = qs.update_quote(IID, "2500", "10")
    assert intent is not None
    assert intent.side is OrderSide.SELL
    assert intent.price == Decimal("2500")


def test_slicing_strategy_slices_decimal() -> None:
    ss = SlicingStrategy(total_quantity="100", slice_size="30", side="BUY")
    assert ss.remaining_to_dispatch == Decimal("100")
    assert ss.next_slice_quantity() == Decimal("30")
    s1 = ss.execute_slice(IID, price="2450.5")
    assert s1 is not None
    assert s1.quantity == Decimal("30")
    assert s1.price == Decimal("2450.5")
    assert isinstance(s1.quantity, Decimal)
    assert ss.remaining_to_dispatch == Decimal("70")
    ss.execute_slice(IID, price="2450.5")
    s3 = ss.execute_slice(IID, price="2450.5")
    assert s3 is not None
    assert s3.quantity == Decimal("30")
    assert ss.remaining_to_dispatch == Decimal("10")
    s4 = ss.execute_slice(IID, price="2450.5")
    assert s4 is not None
    assert s4.quantity == Decimal("10")
    assert ss.remaining_to_dispatch == Decimal("0")
    assert ss.is_complete is True
    assert ss.execute_slice(IID, price="2450.5") is None


def test_slicing_strategy_market_slice_sell() -> None:
    ss = SlicingStrategy(total_quantity="10", slice_size="10", side="SELL")
    intent = ss.execute_slice(IID)
    assert intent is not None
    assert intent.side is OrderSide.SELL
    assert intent.order_type.name == "MARKET"
    assert intent.quantity == Decimal("10")


def test_slicing_strategy_invalid_slice_size() -> None:
    with pytest.raises(ValueError):
        SlicingStrategy(total_quantity="10", slice_size="0")


def test_rebalancing_strategy_compute_rebalance_deltas() -> None:
    rs = RebalancingStrategy(target_weights={"RELIANCE": "0.5", "TCS": "0.5"})
    deltas = rs.compute_rebalance_deltas(
        "100000",
        {"RELIANCE": "10", "TCS": "10"},
        {"RELIANCE": "2500.5", "TCS": "3500.5"},
    )
    assert isinstance(deltas, dict)
    assert set(deltas.keys()) == {"RELIANCE", "TCS"}
    for value in deltas.values():
        assert isinstance(value, Decimal)
    assert deltas["RELIANCE"] == Decimal("9")
    assert deltas["TCS"] == Decimal("4")


def test_rebalancing_strategy_rebalance_submits() -> None:
    rs = RebalancingStrategy(target_weights={"RELIANCE": "0.5", "TCS": "0.5"})
    instruments = {"RELIANCE": IID, "TCS": IID2}
    executed = rs.rebalance(
        instruments,
        "100000",
        {"RELIANCE": "10", "TCS": "10"},
        {"RELIANCE": "2500.5", "TCS": "3500.5"},
    )
    assert len(executed) == 2
    assert executed == [("RELIANCE", Decimal("9")), ("TCS", Decimal("4"))]
    intents = rs.drain_intents()
    assert [i.side for i in intents] == [OrderSide.BUY, OrderSide.BUY]
    assert intents[0].quantity == Decimal("9")
    assert intents[1].quantity == Decimal("4")


def test_arbitrage_strategy_compute_spread_decimal() -> None:
    ar = ArbitrageStrategy(entry_spread="5", exit_spread="0.5")
    spread = ar.compute_spread("2500.5", "2500.0")
    assert isinstance(spread, Decimal)
    assert spread == Decimal("0.5")
    assert ar.last_spread == Decimal("0.5")
    # spread inside the entry band: no orders, stays flat
    assert ar.evaluate_legs(IID, "2500.5", IID2, "2500.0") == 0
    assert ar.drain_intents() == []


def test_arbitrage_strategy_evaluate_legs_entry() -> None:
    ar = ArbitrageStrategy(entry_spread="5", exit_spread="0.5")
    pos = ar.evaluate_legs(IID, "2505.0", IID2, "2500.0")
    assert pos == -1
    intents = ar.drain_intents()
    assert len(intents) == 2
    assert intents[0].side is OrderSide.SELL
    assert intents[0].quantity == Decimal("1")
    assert isinstance(intents[0].quantity, Decimal)
    assert intents[1].side is OrderSide.BUY
    assert intents[1].quantity == Decimal("1.0")
