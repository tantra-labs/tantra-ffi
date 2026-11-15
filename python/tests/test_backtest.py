# wheel surface (ex 0006): Decimal-canonical backtest tests
# stand-in closure for tantra-examples gap 0006

"""Tests for the Decimal-canonical backtest simulator wheel surface (ex 0006, wave 1)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from tantra.backtest import (
    MarketImpact,
    NextOpenExecution,
    OpeningAuction,
    SessionOpen,
    group_sessions,
    make_simulator,
    resolve_fill_costs,
    zero_costs,
)
from tantra.backtest.simulated import is_intraday, session_date
from tantra.bar import Bar
from tantra.execution import Cancelled, Fill, Rejected
from tantra.instrument import InstrumentId
from tantra.money import Currency, Money
from tantra.order import OrderIntent, OrderSide, OrderType


def _iid(symbol: str = "RELIANCE") -> InstrumentId:
    return InstrumentId(symbol, "NSE")


def _bar(ts: int, price: str, instrument: InstrumentId | None = None) -> Bar:
    iid = instrument or _iid()
    return Bar(iid, ts, price, price, price, price, "1000")


# -- MarketImpact ----------------------------------------------------------------------------


def test_market_impact_adv_sigma_fraction_are_decimal() -> None:
    mi = MarketImpact()
    iid = _iid()
    for vol, close in [("100", "100"), ("300", "110")]:
        mi.observe(iid, volume=Decimal(vol), close=Decimal(close))
    adv = mi.adv(iid)
    sigma = mi.sigma(iid)
    assert isinstance(adv, Decimal)
    assert isinstance(sigma, Decimal)
    assert adv == Decimal("400") / Decimal(2)
    assert mi.fraction(iid, Decimal("50")) == Decimal(0)  # one return only -> no sigma yet


def test_market_impact_fraction_is_zero_without_history() -> None:
    mi = MarketImpact()
    iid = _iid()
    assert mi.adv(iid) == Decimal(0)
    assert mi.sigma(iid) == Decimal(0)
    assert mi.fraction(iid, Decimal("100")) == Decimal(0)
    assert mi.fraction(iid, Decimal("-5")) == Decimal(0)
    mi.observe(iid, volume=Decimal("0"), close=Decimal("100"))
    assert mi.fraction(iid, Decimal("100")) == Decimal(0)  # zero ADV -> no impact


def test_market_impact_fraction_scales_with_kappa() -> None:
    mi = MarketImpact(kappa=Decimal(2))
    iid = _iid()
    # Three closes give two returns (0.2 and 0.0): sample stdev = sqrt(0.02).
    for vol, close in [("1000", "100"), ("1000", "120"), ("1000", "120")]:
        mi.observe(iid, volume=Decimal(vol), close=Decimal(close))
    sigma = mi.sigma(iid)
    assert sigma == (Decimal("0.02")).sqrt()
    assert mi.adv(iid) == Decimal("1000")
    assert mi.fraction(iid, Decimal("250")) == (
        Decimal(2) * sigma * (Decimal("250") / Decimal("1000")).sqrt()
    )
    assert mi.fraction(iid, Decimal("250")) > 0


def test_market_impact_validation() -> None:
    with pytest.raises(ValueError):
        MarketImpact(kappa=Decimal("-1"))
    with pytest.raises(ValueError):
        MarketImpact(window=1)


# -- OpeningAuction --------------------------------------------------------------------------


def test_opening_auction_fraction_and_enabled() -> None:
    a = OpeningAuction(spread_bps=Decimal(5))
    assert a.fraction == Decimal("0.0005")
    assert isinstance(a.fraction, Decimal)
    assert a.enabled is True
    off = OpeningAuction()
    assert off.fraction == Decimal(0)
    assert off.enabled is False
    assert OpeningAuction(delay_bars=3).enabled is True


def test_opening_auction_validation() -> None:
    with pytest.raises(ValueError):
        OpeningAuction(spread_bps=Decimal(10000))
    with pytest.raises(ValueError):
        OpeningAuction(spread_bps=Decimal(-1))
    with pytest.raises(ValueError):
        OpeningAuction(delay_bars=-1)
    with pytest.raises(ValueError):
        OpeningAuction(delay_bars=Decimal(1))


# -- NextOpenExecution -----------------------------------------------------------------------


def test_next_open_buy_fills_at_next_open() -> None:
    iid = _iid()
    sim = NextOpenExecution(cash=Money("100000"))
    sim.open_session(1_000, [_bar(1_000, "95")])
    sim.submit("o1", OrderIntent(iid, OrderSide.BUY, Decimal("10")), ts=1_000)
    assert sim.working_orders == ["o1"]
    sim.open_session(2_000, [_bar(2_000, "100")])
    events = sim.drain_events()
    assert len(events) == 1
    fill = events[0]
    assert isinstance(fill, Fill)
    assert isinstance(fill.trade.quantity, Decimal)
    assert isinstance(fill.trade.price, Decimal)
    assert fill.trade.quantity == Decimal("10")
    assert fill.trade.price == Decimal("100")
    assert fill.cum_qty == Decimal("10")
    assert fill.complete is True
    assert sim.positions[iid] == Decimal("10")
    assert sim.cash.amount == Decimal("99000")
    assert sim.drain_events() == []


def test_next_open_sells_fill_before_buys() -> None:
    iid = _iid()
    sim = NextOpenExecution(cash=Money("100000"))
    sim.submit("o1", OrderIntent(iid, OrderSide.BUY, Decimal("10")), 1_000)
    sim.open_session(2_000, [_bar(2_000, "100")])
    sim.drain_events()
    sim.submit("o2", OrderIntent(iid, OrderSide.SELL, Decimal("5")), 2_000)
    sim.submit("o3", OrderIntent(iid, OrderSide.BUY, Decimal("5")), 2_000)
    sim.open_session(3_000, [_bar(3_000, "110")])
    events = sim.drain_events()
    assert [type(ev).__name__ for ev in events] == ["Fill", "Fill"]
    assert events[0].trade.order_id == "o2"  # the sell fills before the buy
    assert events[1].trade.order_id == "o3"
    assert sim.positions[iid] == Decimal("10")


def test_next_open_sell_beyond_holding_is_capped() -> None:
    iid = _iid()
    sim = NextOpenExecution(cash=Money("100000"))
    sim.submit("o1", OrderIntent(iid, OrderSide.BUY, Decimal("10")), 1_000)
    sim.open_session(2_000, [_bar(2_000, "100")])
    sim.drain_events()
    sim.submit("o2", OrderIntent(iid, OrderSide.SELL, Decimal("15")), 2_000)
    sim.open_session(3_000, [_bar(3_000, "110")])
    events = sim.drain_events()
    assert len(events) == 2
    fill, rejected = events
    assert isinstance(fill, Fill)
    assert fill.trade.side is OrderSide.SELL
    assert fill.trade.quantity == Decimal("10")
    assert fill.trade.price == Decimal("110")
    assert isinstance(rejected, Rejected)
    assert rejected.order_id == "o2"
    assert rejected.reason == "no_position"
    assert rejected.intent.quantity == Decimal("5")
    assert iid not in sim.positions
    assert sim.cash.amount == Decimal("100100")  # 100000 - 10*100 + 10*110


def test_next_open_rejects_unsupported_order_type() -> None:
    iid = _iid()
    sim = NextOpenExecution(cash=Money("100000"))
    sim.submit(
        "o1",
        OrderIntent(iid, OrderSide.BUY, Decimal("10"), OrderType.LIMIT, Decimal("100")),
        1_000,
    )
    events = sim.drain_events()
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, Rejected)
    assert ev.reason == "unsupported_order_type"
    assert ev.intent.order_type is OrderType.LIMIT
    assert sim.working_orders == []


def test_next_open_cancel_emits_cancelled_stamped_now() -> None:
    iid = _iid()
    sim = NextOpenExecution(cash=Money("100000"))
    sim.submit("o1", OrderIntent(iid, OrderSide.BUY, Decimal("10")), 1_000)
    sim.cancel("o1", now=7_777)
    events = sim.drain_events()
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, Cancelled)
    assert ev.order_id == "o1"
    assert ev.ts == 7_777
    assert sim.working_orders == []


def test_next_open_buy_cut_to_whole_lots() -> None:
    iid = _iid()
    sim = NextOpenExecution(cash=Money("1000"))
    sim.set_lot_size(iid, Decimal(25))
    sim.submit("o1", OrderIntent(iid, OrderSide.BUY, Decimal("100")), 1_000)
    sim.open_session(2_000, [_bar(2_000, "30")])
    events = sim.drain_events()
    assert len(events) == 2
    fill, rejected = events
    assert isinstance(fill, Fill)
    assert fill.trade.quantity == Decimal("25")
    assert fill.trade.price == Decimal("30")
    assert fill.complete is False
    assert isinstance(rejected, Rejected)
    assert rejected.reason == "insufficient_funds"
    assert rejected.intent.quantity == Decimal("75")
    assert sim.positions[iid] == Decimal("25")
    assert sim.cash.amount == Decimal("250")


# -- group_sessions --------------------------------------------------------------------------


def test_group_sessions_groups_bars_by_ts() -> None:
    a = _iid("A")
    b = _iid("B")
    bars = [
        _bar(2_000, "100", a),
        _bar(1_000, "100", b),
        _bar(1_000, "100", a),
    ]
    events = group_sessions(bars)
    assert [type(ev).__name__ for ev, _ in events] == [
        "SessionOpen",
        "Bar",
        "Bar",
        "SessionOpen",
        "Bar",
    ]
    so, ts_init = events[0]
    assert ts_init == 1_000
    assert isinstance(so, SessionOpen)
    assert so.ts == 1_000
    assert tuple(bar.instrument_id.symbol for bar in so.bars) == ("A", "B")
    assert (events[1][0].instrument_id, events[1][1]) == (a, 1_000)
    assert (events[2][0].instrument_id, events[2][1]) == (b, 1_000)
    assert isinstance(events[3][0], SessionOpen)
    assert events[3][1] == 2_000
    assert isinstance(events[4][0], Bar)


# -- resolve_fill_costs ----------------------------------------------------------------------


def test_resolve_fill_costs_maps_zero_packs() -> None:
    assert resolve_fill_costs("none") is zero_costs
    assert resolve_fill_costs("zero") is zero_costs


def test_resolve_fill_costs_india_packs_not_in_wheel() -> None:
    with pytest.raises(NotImplementedError):
        resolve_fill_costs("india.equity")
    with pytest.raises(NotImplementedError):
        resolve_fill_costs("india.equity.delivery")
    with pytest.raises(NotImplementedError):
        resolve_fill_costs("india.equity.intraday")


def test_resolve_fill_costs_unknown_pack_raises() -> None:
    with pytest.raises(ValueError):
        resolve_fill_costs("bogus")


# -- make_simulator --------------------------------------------------------------------------


def test_make_simulator_next_open() -> None:
    sim = make_simulator(fill="next_open", cash=Money("100000"), settlement_days=1)
    assert isinstance(sim, NextOpenExecution)
    assert sim.backend == "python"


def test_make_simulator_without_settlement_days_raises() -> None:
    with pytest.raises(NotImplementedError):
        make_simulator(fill="next_open", cash=Money("100000"), timeframe="1d")
    with pytest.raises(ValueError):
        make_simulator(fill="next_open", cash=Money("100000"), timeframe="1m")


def test_make_simulator_later_waves_raise_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        make_simulator(fill="l2", cash=Money("100000"))
    with pytest.raises(NotImplementedError):
        make_simulator(fill="bar_close", cash=Money("100000"))
    with pytest.raises(ValueError):
        make_simulator(fill="l2", cash=Money("100000"), impact=MarketImpact())
    with pytest.raises(ValueError):
        make_simulator(
            fill="bar_close", cash=Money("100000"), auction=OpeningAuction()
        )


def test_make_simulator_unknown_fill_raises() -> None:
    with pytest.raises(ValueError):
        make_simulator(fill="bogus", cash=Money("100000"))


# -- helpers ---------------------------------------------------------------------------------


def test_is_intraday() -> None:
    assert is_intraday("1m") is True
    assert is_intraday("5min") is True
    assert is_intraday("1h") is True
    assert is_intraday("1d") is False
    assert is_intraday("1w") is False
    assert is_intraday("weekly") is False


def test_session_date_ist_clock() -> None:
    assert session_date(0) == date(1970, 1, 1)
    assert session_date(86_400 * 10**9) == date(1970, 1, 2)
    assert session_date(5 * 3600 * 10**9 + 30 * 60 * 10**9) == date(1970, 1, 1)
