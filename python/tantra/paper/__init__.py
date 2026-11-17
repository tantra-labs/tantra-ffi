"""Paper-trading exchange embedding: the native ``PaperExchange`` plus a session facade.

The compiled paper-exchange engine (``tantra-exec-paper``, plan 0003, D1) is
exposed through ``tantra._tantra.PaperExchange``. :class:`PaperSession` adds a
deterministic facade: a ``seed=`` session runs the engine's seeded latency model
(the identical seed reproduces the identical tape), and :meth:`PaperSession.run`
drives a :class:`~tantra.strategy.Strategy` over bars the way
:class:`tantra.backtest.session.Session` does (buffered ``OrderRequest``s flushed
onto the exchange after each callback).

This subpackage is lazily imported (like ``tantra.backtest``), so it is never
loaded by ``import tantra`` alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import tantra.indicators as _indicators
from tantra._tantra import (
    Bar as _CompiledBar,
)
from tantra._tantra import (
    InstrumentId as _CompiledInstrumentId,
)
from tantra._tantra import (
    OrderRequest as _CompiledOrderRequest,
)
from tantra._tantra import (
    OrderSide as _CompiledOrderSide,
)
from tantra._tantra import (
    PaperExchange,
)
from tantra.types import to_decimal

__all__ = ["PaperExchange", "PaperResult", "PaperSession"]

# The seeded latency profile (plan 0003, D3): mean 10us / std 5us so the RNG is
# exercised, but fills still land on the very next advance. The profile is part
# of the determinism contract -- two sessions with the same seed reproduce the
# same tape byte for byte.
_LATENCY_MEAN_US = 10
_LATENCY_STD_US = 5


def _ts_iso(ts_ns: int) -> str:
    """Unix-nanosecond timestamp as an RFC3339 UTC string."""
    return (
        datetime.fromtimestamp(ts_ns / 1_000_000_000, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _compiled_instrument(inst: Any) -> _CompiledInstrumentId:
    """Accept a wire string, a wheel ``InstrumentId``, or a compiled one."""
    if isinstance(inst, str):
        return _CompiledInstrumentId.from_str(inst)
    to_compiled = getattr(inst, "to_compiled", None)
    if callable(to_compiled):
        return to_compiled()
    return inst


@dataclass
class PaperResult:
    """What :meth:`PaperSession.run` returns: a small paper-run summary."""

    strategy_name: str
    fills: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)


class _RunnerShim:
    """Non-None stand-in for the compiled ``StrategyRunner``.

    ``Strategy._require_runner`` only checks ``_runner is not None`` and
    ``_algo_id is not None``; ``PaperSession.run`` drives the orders itself, so
    the shim is never called (orders are buffered while ``_in_callback`` is
    True and flushed by the session).
    """


class PaperSession:
    """A deterministic paper-trading session over the native exchange engine."""

    def __init__(
        self,
        cash: Decimal = Decimal(1_000_000),
        seed: int | None = None,
    ) -> None:
        self._exchange = PaperExchange(to_decimal(cash), seed=seed)

    @property
    def exchange(self) -> PaperExchange:
        """The underlying native :class:`PaperExchange`."""
        return self._exchange

    # -- engine passthrough ----------------------------------------------------
    def set_market_price(self, instrument: Any, price: Any) -> None:
        """Set ``instrument``'s last market price (drives resting-limit matching)."""
        self._exchange.set_market_price(
            _compiled_instrument(instrument), to_decimal(price)
        )

    def place_order(
        self,
        instrument: Any,
        side: str,
        quantity: Any,
        order_type: str = "MARKET",
        limit_price: Any = None,
        trigger_price: Any = None,
        tif: str = "DAY",
        ts_iso: str = "",
        gtd_until: str | None = None,
    ) -> str:
        """Place an order; returns the broker order id (``PAPER-0001``, ...).

        ``gtd_until`` (RFC3339 UTC) makes the order good-till-date: the engine
        sets the order's expiry and the first ``advance_to`` at or past that
        instant expires it (state ``CANCELLED``).
        """
        request = _CompiledOrderRequest(
            _compiled_instrument(instrument),
            _CompiledOrderSide(side.upper()),
            order_type.upper(),
            to_decimal(quantity),
            "paper",
            limit_price=None if limit_price is None else to_decimal(limit_price),
            trigger_price=None if trigger_price is None else to_decimal(trigger_price),
            tif=tif.upper(),
        )
        return self._exchange.place_order(request, ts_iso, gtd_until)

    def cancel_order(self, broker_order_id: str, ts_iso: str = "") -> None:
        """Cancel a working order by its broker order id."""
        self._exchange.cancel_order(broker_order_id, ts_iso)

    def amend_order(
        self,
        broker_order_id: str,
        limit_price: Any = None,
        quantity: Any = None,
        ts_iso: str = "",
    ) -> None:
        """Amend a working order's limit price and/or quantity (both optional)."""
        self._exchange.amend_order(
            broker_order_id,
            None if limit_price is None else to_decimal(limit_price),
            None if quantity is None else to_decimal(quantity),
            ts_iso,
        )

    def feed_bar(self, bar: Any) -> None:
        """Feed a compiled ``_tantra.Bar`` (the engine updates prices and re-matches)."""
        self._exchange.feed_bar(bar)

    def feed_tick(self, tick: Any) -> None:
        """Feed a compiled ``_tantra.Tick`` (quote or LTP)."""
        self._exchange.feed_tick(tick)

    def advance_to(self, ts_iso: str = "") -> None:
        """Advance the engine clock (expires GTD orders, matches latency-ready ones)."""
        self._exchange.advance_to(ts_iso)

    def fills(self) -> list:
        """Every :class:`~tantra._tantra.FillReport` so far, in engine order."""
        return self._exchange.fills()

    def events(self) -> list:
        """The engine's event stream, one dict per event."""
        return self._exchange.events()

    def positions(self) -> dict:
        """Net position per instrument (wire ``EXCHANGE:SYMBOL`` -> Decimal)."""
        return self._exchange.positions()

    def cash(self) -> Decimal:
        """Booked cash."""
        return self._exchange.cash()

    def equity(self) -> Decimal:
        """Equity = cash + sum(position * last)."""
        return self._exchange.equity()

    def depth(self, instrument: Any) -> tuple | None:
        """Best bid/ask of ``instrument`` (``(bid, ask)``, each possibly None)."""
        return self._exchange.depth(_compiled_instrument(instrument))

    def order(self, broker_order_id: str) -> dict:
        """One working order as a dict (empty when unknown)."""
        return self._exchange.order(broker_order_id)

    # -- strategy driving -------------------------------------------------------
    def run(self, strategy: Any, bars: list) -> PaperResult:
        """Drive ``strategy`` over ``bars`` onto the exchange (mirrors ``Session.run``).

        ``on_start`` and each ``on_bar`` run with the strategy's ``_in_callback``
        True so ``self.buy`` / ``self.sell`` buffer their compiled
        ``OrderRequest``s; the session flushes each buffer onto the exchange
        immediately after the callback. Equity is marked after every bar.
        """
        strategy._algo_id = "paper"
        strategy._pending_orders = []
        strategy._orders_filled = 0
        strategy._refusals = 0
        strategy._events = 0
        strategy._runner = _RunnerShim()
        strategy.indicators = _indicators

        def flush(ts_iso: str) -> None:
            pending, strategy._pending_orders = strategy._pending_orders, []
            for order in pending:
                self._exchange.place_order(order, ts_iso)

        strategy._in_callback = True
        try:
            strategy.on_start()
        finally:
            strategy._in_callback = False
        flush(_ts_iso(bars[0].ts) if bars else "")

        equity_curve: list = []
        for bar in bars:
            self._feed_wheel_bar(bar)
            strategy._in_callback = True
            try:
                strategy.on_bar(bar)
            finally:
                strategy._in_callback = False
            flush(_ts_iso(bar.ts))
            equity_curve.append(self._exchange.equity())

        return PaperResult(
            strategy_name=getattr(strategy, "name", type(strategy).__name__),
            fills=self._exchange.fills(),
            equity_curve=equity_curve,
        )

    def _feed_wheel_bar(self, bar: Any) -> None:
        """Lift a wheel ``tantra.bar.Bar`` into a compiled bar and feed it."""
        compiled = _CompiledBar(
            _compiled_instrument(bar.instrument_id),
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            bar.volume,
            _ts_iso(bar.ts),
        )
        self._exchange.feed_bar(compiled)
