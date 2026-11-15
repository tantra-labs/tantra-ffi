"""Tests for the wheel session orchestrator `tantra.backtest.session` (ex 0008 closure)."""

from decimal import Decimal

from tantra.backtest.session import BacktestResult, Tantra
from tantra.backtest.simulated import group_sessions, make_simulator, resolve_fill_costs
from tantra.bar import Bar
from tantra.execution import Fill
from tantra.instrument import InstrumentId
from tantra.money import Currency, Money
from tantra.order import OrderIntent, OrderSide
from tantra.strategy import Strategy


def _bars(symbol: str = "TEST", exchange: str = "NSE", n: int = 5, base: int = 100) -> list[Bar]:
    """A rising 5-bar daily series (one bar per session, ts one day apart)."""
    ts = 1_600_000_000_000_000_000
    bars = []
    for i in range(n):
        o = Decimal(base + i)
        bars.append(
            Bar(
                InstrumentId(symbol, exchange),
                ts + i * 86_400_000_000_000,
                o,
                o + Decimal(2),
                o - Decimal(1),
                o + Decimal(1),
                Decimal(1000),
            )
        )
    return bars


class BuySellNextOpen(Strategy):
    """Buys on the first bar, sells two bars later: both fill at the next open."""

    name = "buy_sell_next_open"

    def __init__(self, symbol: str) -> None:
        super().__init__()
        self._symbol = symbol
        self._bar = 0

    def on_bar(self, bar: Bar) -> None:
        if self._bar == 0:
            self.buy(self._symbol, 10)
        elif self._bar == 2:
            self.sell(self._symbol, 10)
        self._bar += 1


def test_tantra_backtest_drives_next_open_fills() -> None:
    bars = _bars()
    result = Tantra.backtest(
        BuySellNextOpen("TEST"),
        symbol="TEST",
        exchange="NSE",
        start="2020-10-01",
        end="2020-10-08",
        bars=bars,
    ).run()
    assert isinstance(result, BacktestResult)
    assert result.strategy_name == "buy_sell_next_open"
    assert len(result.equity_curve) > 0
    assert result.metrics["final_equity"] > 0
    # the bar-0 buy and the bar-2 sell both fill at a later open
    assert result.metrics["n_fills"] >= 2
    assert result.metrics["n_trades"] >= 2
    assert all(isinstance(v, float) for v in result.metrics.values())


def test_next_open_fill_cannot_fill_at_signal_bars_open() -> None:
    bars = _bars()
    port = make_simulator(
        fill="next_open",
        cash=Money(1_000_000, Currency.INR),
        costs="none",
        exchange="NSE",
        settlement_days=0,
        timeframe="1d",
    )
    events = group_sessions(bars)
    port.on_event(*events[0])  # SessionOpen(ts0)
    port.on_event(*events[1])  # bar 0
    # submitted during bar 0's session: must not fill at bar 0's open
    port.submit("o1", OrderIntent(bars[0].instrument_id, OrderSide.BUY, Decimal(10)), events[1][1])
    assert port.working_orders == ["o1"]
    # session 1 opens with bar 1: the buy fills at bar 1's open
    port.on_event(*events[2])  # SessionOpen(ts1)
    fills = [ev for ev in port.drain_events() if isinstance(ev, Fill)]
    assert len(fills) == 1
    assert fills[0].trade.price == bars[1].open


def _drive_one_buy(port, bars: list[Bar]) -> None:
    events = group_sessions(bars)
    port.on_event(*events[0])  # SessionOpen(ts0)
    port.on_event(*events[1])  # bar 0
    port.submit("o1", OrderIntent(bars[0].instrument_id, OrderSide.BUY, Decimal(10)), events[1][1])
    port.on_event(*events[2])  # session 1 opens: the buy fills at bar 1's open


def test_india_delivery_costs_charge_fees_versus_none() -> None:
    bars = _bars()
    zero = make_simulator(
        fill="next_open",
        cash=Money(1_000_000, Currency.INR),
        costs="none",
        exchange="NSE",
        settlement_days=0,
        timeframe="1d",
    )
    delivery = make_simulator(
        fill="next_open",
        cash=Money(1_000_000, Currency.INR),
        costs="india.equity.delivery",
        exchange="NSE",
        settlement_days=0,
        timeframe="1d",
    )
    _drive_one_buy(zero, bars)
    _drive_one_buy(delivery, bars)
    assert zero.fees.amount == 0
    assert delivery.fees.amount > 0


def test_resolve_fill_costs_india_delivery_returns_nonzero_money() -> None:
    fn = resolve_fill_costs("india.equity.delivery")
    cost = fn(OrderSide.BUY, Decimal(10), Decimal(100))
    assert isinstance(cost, Money)
    assert cost.amount > 0


def test_make_simulator_resolves_india_settlement_when_omitted() -> None:
    port = make_simulator(
        fill="next_open",
        cash=Money(1_000_000, Currency.INR),
        costs="none",
        exchange="NSE",
        settlement_days=None,
        timeframe="1d",
    )
    assert port.settlement_days >= 1
