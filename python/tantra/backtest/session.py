# wheel surface (ex 0008): session orchestrator (replaces the tantra_examples/_kernel/session stub shape)
# closure for tantra-examples gap 0008

"""The wheel session orchestrator: ``Tantra.backtest``.

Mirrors the public shape of the deleted ``tantra_examples/_kernel/session.py``
stub: a ``Tantra.backtest(...) -> Session -> .run()`` orchestrator that drives a
:class:`tantra.strategy.Strategy` over bars through the Decimal-canonical
next-open simulator (:mod:`tantra.backtest.simulated`) with Indian equity costs
and settlement wired from ``tantra.markets.india`` (gaps 0004 + 0006 are
closed).

Design (the next-open rule):

* Bars come from ``bars=`` or ``data.bars(instrument_id, ...)`` where
  ``instrument_id = InstrumentId(symbol, exchange)``.
* ``make_simulator`` builds the port: ``next_open`` fills every market order at
  the **next** session's open, so a buy placed on bar *k* can never fill at bar
  *k*'s open. Costs and settlement resolve from the India pack unless given
  explicitly.
* ``on_start`` and ``on_bar`` run with ``_in_callback = True`` so the strategy's
  ``self.buy`` / ``self.sell`` buffer their orders (compiled ``OrderRequest``
  objects); the session flushes each buffer into :class:`OrderIntent` and
  ``port.submit`` immediately after the callback.
* Equity is marked after each session: ``cash + Σ position × last_close``
  (Decimal), deduped per ``ts``.

Zero-floats: all internal arithmetic is exact ``decimal.Decimal`` (the
simulator's ``Money`` / ``OrderIntent`` / ``Bar`` world); ``float`` appears only
at the metrics / equity-curve boundary the ``algo_analytics`` readers expect.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from tantra import indicators
from tantra.backtest.simulated import FillCostFn, group_sessions, make_simulator
from tantra.bar import Bar
from tantra.execution import ExecutionPortLike, Fill
from tantra.instrument import InstrumentId
from tantra.money import Currency, Money
from tantra.order import OrderIntent, OrderSide, OrderType
from tantra.strategy import Strategy
from tantra.types import to_decimal

__all__ = ["BacktestResult", "CostModel", "DataProvider", "Session", "Tantra"]


class DataProvider(Protocol):
    """Where ``Tantra.backtest`` gets its bars when ``bars=`` is not given."""

    def bars(self, instrument_id: Any, *, timeframe: str, start: Any, end: Any) -> Any: ...
    def instrument(self, instrument_id: Any) -> Any: ...


class CostModel(Protocol):
    """Post-hoc per-trade cost model (adaptable to the port via ``fill_costs_from_model``)."""

    def apply(self, trade: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """What ``Session.run()`` returns: the summary the algo-analytics readers consume."""

    strategy_name: str
    metrics: dict[str, float]
    equity_curve: list[tuple[Any, float]]


class _RunnerShim:
    """Non-None stand-in for the compiled ``StrategyRunner``.

    ``Strategy._require_runner`` only checks ``_runner is not None`` and
    ``_algo_id is not None``; the session drives orders itself, so the shim is
    never called (orders are buffered while ``_in_callback`` is True and flushed
    by the session).
    """


class Session:
    """One ``Tantra.backtest`` run; :meth:`run` drives the strategy and returns a result."""

    def __init__(
        self,
        *,
        strategy: Strategy | type[Strategy],
        symbol: str,
        exchange: str,
        start: Any,
        end: Any,
        data: DataProvider | None,
        timeframe: str,
        cash: Any,
        costs: str | FillCostFn,
        fill: str,
        settlement_days: int | None,
        algo_id: str,
        bars: Any,
        simulator_kwargs: dict[str, Any],
    ) -> None:
        self._strategy = strategy
        self._symbol = symbol
        self._exchange = exchange
        self._start = start
        self._end = end
        self._data = data
        self._timeframe = timeframe
        self._cash = cash
        self._costs = costs
        self._fill = fill
        self._settlement_days = settlement_days
        self._algo_id = algo_id
        self._bars = bars
        self._simulator_kwargs = simulator_kwargs

    def run(self) -> BacktestResult:
        strategy = self._strategy
        if isinstance(strategy, type):
            strategy = strategy()

        bars = self._resolve_bars()
        initial_cash = Money(self._cash or 1_000_000, Currency.INR)
        port = make_simulator(
            fill=self._fill,
            cash=initial_cash,
            costs=self._costs,
            exchange=self._exchange,
            settlement_days=self._settlement_days,
            timeframe=self._timeframe,
            **self._simulator_kwargs,
        )
        self._attach(strategy)

        last_close: dict[InstrumentId, Decimal] = {}
        equity_by_ts: dict[int, Decimal] = {}
        order_n = 0

        def flush(ts: int) -> None:
            """Submit every order the last callback buffered (fills at the next open)."""
            nonlocal order_n
            pending, strategy._pending_orders = strategy._pending_orders, []
            for order in pending:
                order_n += 1
                port.submit(f"order-{order_n}", _intent_of(order), ts)

        strategy._in_callback = True
        try:
            strategy.on_start()
        finally:
            strategy._in_callback = False

        for event, ts in group_sessions(bars):
            flush(ts)  # on_start orders land before the first session opens
            port.on_event(event, ts)
            if isinstance(event, Bar):
                last_close[event.instrument_id] = event.close
                strategy._in_callback = True
                try:
                    strategy.on_bar(event)
                finally:
                    strategy._in_callback = False
                flush(ts)
            equity_by_ts[ts] = _equity(port, last_close)

        n_fills = sum(1 for ev in port.drain_events() if isinstance(ev, Fill))
        if not equity_by_ts:
            equity_by_ts[0] = initial_cash.amount
        order = sorted(equity_by_ts)
        equity_curve = [(ts, float(equity_by_ts[ts])) for ts in order]
        final = equity_by_ts[order[-1]]
        metrics = {
            "total_return_pct": float(
                (final / initial_cash.amount - Decimal(1)) * Decimal(100)
            ),
            "max_drawdown_pct": float(
                _max_drawdown_pct([equity_by_ts[ts] for ts in order])
            ),
            "final_equity": float(final),
            "n_fills": float(n_fills),
            "n_trades": float(n_fills),
        }
        return BacktestResult(
            strategy_name=getattr(strategy, "name", type(strategy).__name__),
            metrics=metrics,
            equity_curve=equity_curve,
        )

    # -- internals -----------------------------------------------------------------
    def _resolve_bars(self) -> list[Bar]:
        if self._bars is not None:
            return self._bars
        if self._data is None:
            raise RuntimeError(
                "Tantra.backtest needs data= (DataProvider) or bars=; neither was "
                f"supplied for {self._symbol} on {self._exchange} between "
                f"{self._start} and {self._end}"
            )
        return self._data.bars(
            InstrumentId(self._symbol, self._exchange),
            timeframe=self._timeframe,
            start=self._start,
            end=self._end,
        )

    def _attach(self, strategy: Strategy) -> None:
        strategy._algo_id = self._algo_id
        strategy._pending_orders = []
        strategy._orders_filled = 0
        strategy._refusals = 0
        strategy._events = 0
        strategy._runner = _RunnerShim()
        strategy.indicators = indicators


class Tantra:
    """Backtest session entry point (ex 0008 closure; the old ``_kernel/session.Tantra`` stub)."""

    @classmethod
    def backtest(
        cls,
        strategy: Strategy | type[Strategy],
        *,
        symbol: str,
        exchange: str = "NSE",
        start: Any,
        end: Any,
        data: DataProvider | None = None,
        timeframe: str = "1d",
        cash: Any = None,
        costs: str | FillCostFn = "india.equity.delivery",
        fill: str = "next_open",
        settlement_days: int | None = None,
        algo_id: str = "default-algo",
        **kwargs: Any,
    ) -> Session:
        """Prepare one backtest; call ``.run()`` to drive it.

        ``bars=`` (in ``kwargs``) runs the strategy over explicit bars;
        otherwise ``data.bars(InstrumentId(symbol, exchange), ...)`` feeds it and
        ``data`` is required. Remaining ``kwargs`` go to
        :func:`tantra.backtest.simulated.make_simulator` (``long_only``,
        ``as_of``, ``lot_sizes``, ``impact``, ``auction``).
        """
        bars = kwargs.pop("bars", None)
        return Session(
            strategy=strategy,
            symbol=symbol,
            exchange=exchange,
            start=start,
            end=end,
            data=data,
            timeframe=timeframe,
            cash=cash,
            costs=costs,
            fill=fill,
            settlement_days=settlement_days,
            algo_id=algo_id,
            bars=bars,
            simulator_kwargs=kwargs,
        )


def _intent_of(order: Any) -> OrderIntent:
    """Adapt one buffered compiled ``OrderRequest`` to a wheel :class:`OrderIntent`.

    ``_build_order`` (``tantra.strategy``) emits MARKET unless a limit price was
    given; a LIMIT order passes its price through and the simulator rejects it as
    ``unsupported_order_type`` (market orders only, next-open fills).
    """
    iid = InstrumentId(order.instrument.symbol, order.instrument.exchange)
    side = OrderSide.BUY if str(order.side).upper() == "BUY" else OrderSide.SELL
    if order.order_type == "LIMIT" or order.limit_price is not None:
        return OrderIntent(
            iid,
            side,
            to_decimal(order.quantity),
            OrderType.LIMIT,
            to_decimal(order.limit_price),
        )
    return OrderIntent(iid, side, to_decimal(order.quantity), OrderType.MARKET)


def _equity(port: ExecutionPortLike, last_close: dict[InstrumentId, Decimal]) -> Decimal:
    total = port.cash.amount
    for iid, qty in port.positions.items():
        close = last_close.get(iid)
        if close is not None:
            total = total + qty * close
    return total


def _max_drawdown_pct(curve: list[Decimal]) -> Decimal:
    """Largest peak-to-trough percentage drop over the (Decimal) equity curve."""
    peak = curve[0]
    mdd = Decimal(0)
    for eq in curve[1:]:
        if eq > peak:
            peak = eq
        elif peak > 0:
            drop = (peak - eq) / peak * 100
            mdd = max(mdd, drop)
    return mdd
