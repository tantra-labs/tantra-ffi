# wheel surface (ex 0006): Decimal-canonical tests for tantra.declarative +
# tantra.portfolio_strategy (mirrors the kernel _kernel/portfolio_strategy test surface)

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from tantra.bar import Bar
from tantra.context import LedgerContext
from tantra.declarative import DeclarativeStrategy, Entry, TargetWeightStrategy
from tantra.instrument import InstrumentId
from tantra.order import OrderSide, OrderType
from tantra.portfolio_strategy import (
    AnyOf,
    DriftBand,
    EqualWeight,
    EveryNDays,
    InverseVolatility,
    MonthlyFirstSession,
    PortfolioStrategy,
    PriceHistory,
    StaticUniverse,
    TopN,
    build_portfolio_strategy,
)
from tantra.portfolio_strategy.schedule import ScheduleState
from tantra.portfolio_strategy.stats import return_stdev
from tantra.trade import Trade

NS_PER_DAY = 86_400 * 10**9

IID_A = InstrumentId("RELIANCE", "NSE")
IID_B = InstrumentId("TCS", "NSE")


def bar(iid: InstrumentId, day: int, close: str) -> Bar:
    """A same-price OHLCV bar for ``day`` (days since epoch) at ``close``."""
    price = Decimal(close)
    return Bar(iid, day * NS_PER_DAY, price, price, price, price, Decimal(0))


# -- TargetWeightStrategy --------------------------------------------------------


def test_target_weight_initial_rebalance_buys_whole_shares() -> None:
    class Tw(TargetWeightStrategy):
        name = "tw_buy"

        def universe(self):
            return (IID_A, IID_B)

    s = Tw()
    s.bind(LedgerContext(cash=Decimal("100000")))
    s.on_bar(bar(IID_A, 0, "2000"))
    s.on_bar(bar(IID_B, 0, "1000"))
    intents = s.drain_intents()
    assert [i.instrument_id for i in intents] == [IID_A, IID_B]
    assert [i.quantity for i in intents] == [Decimal(24), Decimal(49)]
    assert all(i.side is OrderSide.BUY for i in intents)
    assert all(isinstance(i.quantity, Decimal) for i in intents)


def test_target_weight_rebalance_trims() -> None:
    class Tw(TargetWeightStrategy):
        name = "tw_trim"
        rebalance_days = 1

        def universe(self):
            return (IID_A, IID_B)

    s = Tw()
    s.bind(LedgerContext(cash=Decimal("100000")))
    s.on_bar(bar(IID_A, 0, "2000"))
    s.on_bar(bar(IID_B, 0, "1000"))
    intents = s.drain_intents()
    assert [i.quantity for i in intents] == [Decimal(24), Decimal(49)]

    # Fill both entries, then the market moves up: RELIANCE must be trimmed while
    # TCS (still at its last close of 1000) keeps its target quantity of 49.
    for index, (intent, price) in enumerate(
        zip(intents, (Decimal("2000"), Decimal("1000")))
    ):
        s.handle_fill(
            Trade(intent.instrument_id, intent.side, intent.quantity, price, order_id=f"f{index}")
        )
    s.on_bar(bar(IID_A, 1, "2083"))
    out = s.drain_intents()
    assert len(out) == 1
    assert out[0].instrument_id == IID_A
    assert out[0].side is OrderSide.SELL
    assert out[0].quantity == Decimal(1)


# -- DeclarativeStrategy OCO -----------------------------------------------------


def test_declarative_oco_protects_and_cancels_sibling() -> None:
    class Oco(DeclarativeStrategy):
        name = "oco"

        def should_long(self, bar: Bar) -> bool:
            return True

        def go_long(self, bar: Bar) -> Entry:
            return Entry("5", stop_loss="2400", take_profit="2600")

    s = Oco()
    s.bind(LedgerContext(cash=Decimal("100000")))
    s.on_bar(bar(IID_A, 0, "2500"))
    intents = s.drain_intents()
    assert len(intents) == 1
    assert intents[0].side is OrderSide.BUY
    assert intents[0].quantity == Decimal(5)

    # Entry fill places the protective stop-market sell + limit sell.
    s.handle_fill(Trade(IID_A, OrderSide.BUY, Decimal(5), Decimal("2500"), order_id="entry"))
    group = s._oco_groups[IID_A][0]
    assert len(group.legs) == 2
    stop, target = group.legs
    assert stop.intent.order_type is OrderType.STOP_MARKET
    assert stop.intent.side is OrderSide.SELL
    assert stop.intent.trigger_price == Decimal("2400")
    assert target.intent.order_type is OrderType.LIMIT
    assert target.intent.side is OrderSide.SELL
    assert target.intent.price == Decimal("2600")
    protectives = s.drain_intents()
    assert [p.intent for p in group.legs] == protectives

    # A full fill of one leg cancels the sibling.
    ctx = s._ledger()
    ctx.note_order("stop1", stop.intent)
    ctx.note_order("tgt1", target.intent)
    s.handle_fill(Trade(IID_A, OrderSide.SELL, Decimal(5), Decimal("2400"), order_id="stop1"))
    assert stop.filled == Decimal(5)
    assert ctx.drain_cancels() == ["tgt1"]
    assert IID_A not in s._oco_groups
    assert s.position(IID_A) == Decimal(0)


def test_declarative_validate_levels_rejects_bad_stop() -> None:
    class Bad(DeclarativeStrategy):
        name = "bad_oco"

        def should_long(self, bar: Bar) -> bool:
            return True

        def go_long(self, bar: Bar) -> Entry:
            return Entry("5", stop_loss="2500", take_profit="2600")

    s = Bad()
    s.bind(LedgerContext())
    with pytest.raises(ValueError, match="stop_loss"):
        s.on_bar(bar(IID_A, 0, "2500"))


def test_entry_validates_finite_positive() -> None:
    with pytest.raises(ValueError):
        Entry(Decimal(0))
    with pytest.raises(ValueError):
        Entry("5", stop_loss="nan")


# -- PortfolioStrategy ------------------------------------------------------------


def test_portfolio_strategy_initial_rebalance_and_history_len() -> None:
    s = PortfolioStrategy(
        StaticUniverse([IID_A, IID_B]),
        EqualWeight(),
        EveryNDays(15),
    )
    assert s.history_len == 64
    s.bind(LedgerContext(cash=Decimal("100000")))
    s.on_bar(bar(IID_A, 0, "2000"))
    s.on_bar(bar(IID_B, 0, "1000"))
    intents = s.drain_intents()
    assert [i.instrument_id for i in intents] == [IID_A, IID_B]
    assert [i.quantity for i in intents] == [Decimal(24), Decimal(49)]
    assert all(i.side is OrderSide.BUY for i in intents)

    s2 = PortfolioStrategy(
        StaticUniverse([IID_A, IID_B]),
        EqualWeight(),
        EveryNDays(15),
        history_len=10,
    )
    assert s2.history_len == 10


def test_portfolio_strategy_allocation_bounds() -> None:
    with pytest.raises(ValueError, match="allocation"):
        PortfolioStrategy(
            StaticUniverse([IID_A]), EqualWeight(), EveryNDays(15), allocation=Decimal("1.5")
        )
    with pytest.raises(ValueError, match="allocation"):
        PortfolioStrategy(
            StaticUniverse([IID_A]), EqualWeight(), EveryNDays(15), allocation=Decimal(0)
        )
    with pytest.raises(ValueError, match="allocation"):
        PortfolioStrategy(
            StaticUniverse([IID_A]), EqualWeight(), EveryNDays(15), allocation=Decimal("NaN")
        )


# -- build_portfolio_strategy grammar --------------------------------------------


def test_build_portfolio_strategy_grammar() -> None:
    s = build_portfolio_strategy(
        {
            "universe": {"static": ["RELIANCE", "TCS"]},
            "weighting": "equal",
            "schedule": "every:15d",
        }
    )
    assert isinstance(s, PortfolioStrategy)
    assert isinstance(s.universe_source, StaticUniverse)
    assert isinstance(s.weighting, EqualWeight)
    assert isinstance(s.schedule, EveryNDays)
    assert s.schedule.n == 15

    # list-form universe and +-joined schedules
    s2 = build_portfolio_strategy(
        {"universe": ["RELIANCE", "TCS"], "schedule": "monthly:first_session+drift:0.05"}
    )
    assert isinstance(s2.universe_source, StaticUniverse)
    assert isinstance(s2.schedule, AnyOf)
    assert any(isinstance(x, MonthlyFirstSession) for x in s2.schedule.schedules)
    assert any(isinstance(x, DriftBand) for x in s2.schedule.schedules)
    assert s2.schedule.needs_drift is True

    s3 = build_portfolio_strategy({"universe": ["RELIANCE", "TCS"]})
    assert isinstance(s3.universe_source, StaticUniverse)
    assert isinstance(s3.weighting, EqualWeight)
    assert isinstance(s3.schedule, EveryNDays)
    assert s3.schedule.n == 15


def test_build_portfolio_strategy_invalid_grammar() -> None:
    with pytest.raises(ValueError):
        build_portfolio_strategy({})
    with pytest.raises(ValueError):
        build_portfolio_strategy({"universe": "nifty50", "schedule": "every"})
    with pytest.raises(ValueError):
        build_portfolio_strategy({"universe": []})
    with pytest.raises(ValueError):
        build_portfolio_strategy({"universe": ["RELIANCE"], "bogus": 1})
    with pytest.raises(ValueError):
        build_portfolio_strategy({"universe": ["RELIANCE"], "schedule": "drift:0"})
    with pytest.raises(ValueError):
        build_portfolio_strategy({"universe": ["RELIANCE"], "allocation": 1.5})


# -- schedules -------------------------------------------------------------------


def test_schedule_due_logic() -> None:
    every = EveryNDays(5)
    day = date(2024, 1, 2)
    assert every.due(ScheduleState(day, False, 0, True)) is True
    assert every.due(ScheduleState(day, False, 1, False)) is True
    assert every.due(ScheduleState(day, False, 0, False)) is False
    assert every.due(ScheduleState(day, True, 4, False)) is False
    assert every.due(ScheduleState(day, True, 5, False)) is True
    with pytest.raises(ValueError):
        EveryNDays(0)

    band = DriftBand(Decimal("0.05"))
    assert band.due(ScheduleState(day, True, 1, False, drift=Decimal("0.06"))) is True
    assert band.due(ScheduleState(day, True, 1, False, drift=Decimal("0.04"))) is False
    assert band.due(ScheduleState(day, True, 0, False, drift=Decimal("0.06"))) is False
    assert band.due(ScheduleState(day, True, 1, False, drift=None)) is False
    with pytest.raises(ValueError):
        DriftBand(Decimal(0))

    monthly = MonthlyFirstSession()
    assert (
        monthly.due(
            ScheduleState(date(2024, 2, 1), True, 1, False, previous_bar_day=date(2024, 1, 31))
        )
        is True
    )
    assert (
        monthly.due(
            ScheduleState(date(2024, 1, 3), True, 1, False, previous_bar_day=date(2024, 1, 2))
        )
        is False
    )
    assert monthly.due(ScheduleState(day, False, 0, True)) is True

    anyof = AnyOf(EveryNDays(10), DriftBand(Decimal("0.05")))
    assert anyof.needs_drift is True
    assert anyof.due(ScheduleState(day, True, 4, False, drift=Decimal("0.06"))) is True
    assert anyof.due(ScheduleState(day, True, 10, False, drift=None)) is True
    assert anyof.due(ScheduleState(day, True, 4, False, drift=None)) is False
    with pytest.raises(ValueError):
        AnyOf()


# -- selection / weighting / stats -----------------------------------------------


def test_topn_selection() -> None:
    ph = PriceHistory()
    ph.record(IID_A, Decimal(100))
    ph.record(IID_B, Decimal(200))
    view = ph.view({IID_A: Decimal(100), IID_B: Decimal(200)})

    top = TopN(1, lambda iid, v: v.price(iid))
    assert top.select([IID_A, IID_B], view) == [IID_B]

    bottom = TopN(1, lambda iid, v: v.price(iid), descending=False)
    assert bottom.select([IID_A, IID_B], view) == [IID_A]

    picky = TopN(2, lambda iid, v: v.price(iid) if iid is IID_A else None)
    assert picky.select([IID_A, IID_B], view) == [IID_A]

    with pytest.raises(ValueError):
        TopN(0, lambda iid, v: None)


def test_inverse_volatility_weights() -> None:
    ph = PriceHistory()
    for p in (100, 101, 100, 101, 100, 101, 100, 101, 100, 101):
        ph.record(IID_A, Decimal(p))
    for p in (100, 110, 90, 110, 90, 110, 90, 110, 90, 110):
        ph.record(IID_B, Decimal(p))
    view = ph.view({IID_A: Decimal(101), IID_B: Decimal(110)})

    w = InverseVolatility(10).weights([IID_A, IID_B], view)
    assert isinstance(w[IID_A], Decimal)
    total = sum(w.values(), Decimal(0))
    assert abs(total - Decimal(1)) < Decimal("1e-9")
    assert w[IID_A] > w[IID_B]

    # Equal fallback when no instrument has usable history.
    w2 = InverseVolatility(10).weights([IID_A, IID_B], PriceHistory().view({}))
    assert w2[IID_A] == Decimal("0.5")
    assert w2[IID_B] == Decimal("0.5")


def test_return_stdev() -> None:
    ph = PriceHistory()
    for p in (100, 110, 121):
        ph.record(IID_A, Decimal(p))
    view = ph.view({IID_A: Decimal(121)})
    assert return_stdev(view, IID_A, 3) == Decimal(0)
    assert return_stdev(view, IID_A, 10) is None  # history shorter than lookback
    assert return_stdev(view, IID_A, 2) is None  # single return

    ph2 = PriceHistory()
    ph2.record(IID_A, Decimal(100))
    v2 = ph2.view({IID_A: Decimal(100)})
    assert return_stdev(v2, IID_A, 2) is None

    ph3 = PriceHistory()
    for p in (100, 110, 100):
        ph3.record(IID_A, Decimal(p))
    v3 = ph3.view({IID_A: Decimal(100)})
    s = return_stdev(v3, IID_A, 3)
    assert isinstance(s, Decimal)
    assert s > 0
