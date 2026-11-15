# wheel surface (ex 0006): backtest simulators (mirrors tantra_examples/_kernel/backtest public API)
# stand-in closure for tantra-examples gap 0006

"""L2 top-of-book execution port (ADR 0030): the Python side of ``honba_sim::L2Sim``.

:class:`L2Execution` is an ``ExecutionPort`` (``tantra.execution``) that matches orders
against a :class:`~tantra.tick.QuoteTick` / :class:`~tantra.tick.TradeTick` stream
at nanosecond event time; there is no wall clock. It is opt-in: the default simulator stays the
L1 :class:`~tantra.backtest.simulated.NextOpenExecution` (ADR 0025). Rules (v1):

* **Market**: fills at the opposite touch (buy at the ask, sell at the bid), up to the touch
  size; a remainder keeps working and fills against later quotes (cancelled under IOC).
* **Marketable limit**: walks the touch only (one level) at the touch price; the remainder
  rests at its limit (cancelled under IOC). Consumed touch size is gone until the next quote.
* **Resting limit**: fills at its limit when a trade prints through it (buy: ``price <= limit``,
  sell: ``price >= limit``), FIFO by submission, sharing the print's size. A new quote that
  crosses a resting limit fills it at the touch.
* **Stop / stop-limit**: armed until a trade crosses the trigger (buy: ``price >= trigger``,
  sell: ``price <= trigger``), then behaves as a market / limit order. **Trailing stops** are
  refused (``"unsupported_order_type"``), as in L1.
* **IOC / FOK**: judged once, against the book at submit (or trigger) time; FOK is
  all-or-nothing against the touch size, else rejected ``"fok_unfillable"``.
* **Day**: expires at the session close (default 23:59:00 UTC time of day) with an ``Expired``
  at the close instant, driven by event time (:meth:`L2Execution.advance_to` or the next event)
  or an explicit :meth:`L2Execution.on_session_close`; ``GTC`` / ``GTD`` never expire.
* **Cancel**: ``cancel(order_id, now)`` emits ``CancelRequested`` and ``Cancelled``, both
  stamped ``now`` (ADR 0019 decision 6, L2 v1).
* **Cash.** Decimal ``Money`` (ADR 0011); a fill moves cash at once (no settlement cycle). A buy
  that cash cannot cover is cut to the whole lots cash allows and the rest rejected
  (``"insufficient_funds"``); with ``long_only`` (default) a sell is capped at the position held
  (``"no_position"``). Costs follow L1.

**Backend.** The wheel has no compiled simulator in ``_tantra``, so
:class:`L2Execution` always runs the pure-Python reference (:class:`_PythonL2`); a
``backend="native"`` request raises :class:`NotImplementedError` (mirror:
``tantra-examples/docs/gaps/0006-tantra-wheel-kernel-domain-surface.md``).

Decimal-canonical (rust_decimal parity): quantities, prices, sizes, lot sizes and cash are
exact ``decimal.Decimal`` values.
"""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

import dataclasses
from collections.abc import Iterator, Mapping, MutableMapping
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import Any, NamedTuple

from tantra.backtest.simulated import (
    Backend,
    BackendChoice,
    FillCostFn,
    resolve_backend,
    zero_costs,
)
from tantra.execution import (
    BaseExecutionPort,
    Cancelled,
    CancelRequested,
    ExecutionEvent,
    Expired,
    Fill,
    Rejected,
)
from tantra.instrument import InstrumentId
from tantra.money import Money
from tantra.order import OrderIntent, OrderSide, OrderType, TimeInForce
from tantra.tick import QuoteTick, TradeTick
from tantra.trade import Trade
from tantra.types import to_decimal

__all__ = ["L2Execution", "TopOfBook"]

_QTY_EPS = Decimal("1e-9")  # quantities closer than this are equal (fractional-lot residue)
_NS_PER_DAY = 86_400_000_000_000
_DEFAULT_CLOSE_NS = 86_340_000_000_000  # 23:59:00 UTC into the day


class TopOfBook(NamedTuple):
    """Best bid / ask with the size left at each, as last quoted and drawn down by fills."""

    bid: Decimal
    ask: Decimal
    bid_size: Decimal
    ask_size: Decimal


@dataclass
class _Working:
    order_id: str
    intent: OrderIntent
    remaining: Decimal
    filled: Decimal = Decimal(0)
    limit: Decimal | None = None
    armed: Decimal | None = None  # stop price while the stop is armed
    expire_at: int | None = None  # Day expiry instant


class _RefPositions(MutableMapping[InstrumentId, Decimal]):
    """The reference's positions with the native semantics: a flat entry is absent."""

    def __init__(self) -> None:
        self._d: dict[InstrumentId, Decimal] = {}

    def __getitem__(self, key: InstrumentId) -> Decimal:
        return self._d[key]

    def __setitem__(self, key: InstrumentId, value: Decimal) -> None:
        value = to_decimal(value)
        if not value.is_finite():
            raise ValueError(f"position must be finite, got {value}")
        if abs(value) <= _QTY_EPS:
            self._d.pop(key, None)
        else:
            self._d[key] = value

    def __delitem__(self, key: InstrumentId) -> None:
        del self._d[key]

    def __iter__(self) -> Iterator[InstrumentId]:
        return iter(self._d)

    def __len__(self) -> int:
        return len(self._d)

    def __repr__(self) -> str:
        return repr(self._d)


def _usable(price: Decimal | None) -> bool:
    return price is not None and price.is_finite() and price > 0


class _PythonL2:
    """The pure-Python L2 simulator: the reference twin of ``honba_sim::L2Sim`` (ADR 0030)."""

    def __init__(
        self,
        *,
        cash: Money,
        costs: FillCostFn,
        long_only: bool,
        lot_sizes: Mapping[InstrumentId, Decimal] | None = None,
    ) -> None:
        if cash.amount < 0:
            raise ValueError("cash must be >= 0")
        self._currency = cash.currency
        self._cash = cash.amount
        self._fees = Decimal(0)
        self._traded = Decimal(0)
        self._cost_fn = costs
        self._long_only = long_only
        self._lot_sizes: dict[InstrumentId, Decimal] = {}
        for iid, lot in (lot_sizes or {}).items():
            self.set_lot_size(iid, lot)
        self.positions: MutableMapping[InstrumentId, Decimal] = _RefPositions()
        self._books: dict[InstrumentId, list[Decimal]] = {}
        self._now = 0
        self._working: list[_Working] = []
        self._events: list[ExecutionEvent] = []

    # -- state ---------------------------------------------------------------------
    @property
    def cash(self) -> Money:
        return Money(self._cash, self._currency)

    @property
    def fees(self) -> Money:
        return Money(self._fees, self._currency)

    @property
    def traded_notional(self) -> Money:
        return Money(self._traded, self._currency)

    @property
    def working_orders(self) -> list[str]:
        return [w.order_id for w in self._working]

    def book(self, instrument_id: InstrumentId) -> TopOfBook | None:
        b = self._books.get(instrument_id)
        return None if b is None else TopOfBook(*b)

    def set_lot_size(self, instrument_id: InstrumentId, lot_size: Decimal) -> None:
        lot = to_decimal(lot_size)
        if not (lot.is_finite() and lot > 0):
            raise ValueError(f"lot_size must be positive, got {lot_size}")
        self._lot_sizes[instrument_id] = lot

    def set_position(self, instrument_id: InstrumentId, quantity: Decimal) -> None:
        """Seed a holding of ``quantity`` for ``instrument_id`` (zero removes it)."""
        self.positions[instrument_id] = quantity

    # -- ExecutionPort ---------------------------------------------------------------
    def submit(self, order_id: str, intent: OrderIntent, ts: int) -> None:
        if intent.side not in (OrderSide.BUY, OrderSide.SELL):
            raise ValueError(f"order {order_id} has no side: it must be buy or sell")
        if any(w.order_id == order_id for w in self._working):
            raise ValueError(f"order id {order_id} is already working")
        ts = max(ts, self._now)
        self._advance(ts)
        qty = intent.quantity
        kind = intent.order_type
        limit: Decimal | None = None
        armed: Decimal | None = None
        if kind is OrderType.MARKET:
            pass
        elif kind is OrderType.LIMIT:
            limit = intent.price
        elif kind is OrderType.STOP_MARKET:
            armed = intent.trigger_price
        elif kind is OrderType.STOP_LIMIT:
            limit, armed = intent.price, intent.trigger_price
        else:
            self._reject(order_id, intent, qty, "unsupported_order_type", ts)
            return
        needs_limit = kind in (OrderType.LIMIT, OrderType.STOP_LIMIT)
        needs_stop = kind in (OrderType.STOP_MARKET, OrderType.STOP_LIMIT)
        if (
            not (qty.is_finite() and qty > 0)
            or (needs_limit and not _usable(limit))
            or (needs_stop and not _usable(armed))
        ):
            self._reject(order_id, intent, qty, "invalid_order", ts)
            return
        expire_at = self._close_after(ts) if intent.time_in_force is TimeInForce.DAY else None
        self._working.append(_Working(order_id, intent, qty, Decimal(0), limit, armed, expire_at))
        if armed is None:
            self._aggress(len(self._working) - 1, ts, True)

    def cancel(self, order_id: str, now: int) -> None:
        for w in self._working:
            if w.order_id == order_id:
                self._working.remove(w)
                # ADR 0019 decision 6, L2 v1: both stamped ``now``.
                self._events.append(CancelRequested(order_id, now))
                self._events.append(Cancelled(order_id, self._rest(w), now))
                return

    def drain_events(self) -> list[ExecutionEvent]:
        out, self._events = self._events, []
        return out

    # -- market events -----------------------------------------------------------------
    def on_event(self, event: Any, ts_init: int) -> None:
        if isinstance(event, QuoteTick):
            self.on_quote(event)
        elif isinstance(event, TradeTick):
            self.on_trade(event)

    def on_quote(self, q: QuoteTick) -> None:
        """Update the book, then match working orders in time priority."""
        self._advance(q.ts)
        self._books[q.instrument_id] = [
            q.bid_price,
            q.ask_price,
            q.bid_size,
            q.ask_size,
        ]
        i = 0
        while i < len(self._working):
            w = self._working[i]
            if (
                w.armed is None
                and w.intent.instrument_id == q.instrument_id
                and self._aggress(i, q.ts, False)
            ):
                continue
            i += 1

    def on_trade(self, t: TradeTick) -> None:
        """Fill resting limits the print trades through (FIFO, sharing its size), then stops."""
        ts, px = t.ts, t.price
        self._advance(ts)
        left = t.size
        i = 0
        while i < len(self._working):
            w = self._working[i]
            through = False
            if (
                w.armed is None
                and w.intent.instrument_id == t.instrument_id
                and w.limit is not None
            ):
                through = px <= w.limit if w.intent.side is OrderSide.BUY else px >= w.limit
            if through and left > _QTY_EPS:
                assert w.limit is not None
                filled, removed = self._execute(i, left, w.limit, ts, True)
                left -= filled
                if removed:
                    continue
            i += 1
        i = 0
        while i < len(self._working):
            w = self._working[i]
            hit = False
            if w.armed is not None and w.intent.instrument_id == t.instrument_id:
                hit = px >= w.armed if w.intent.side is OrderSide.BUY else px <= w.armed
            if hit:
                w.armed = None
                if self._aggress(i, ts, True):
                    continue
            i += 1

    def on_session_close(self, ts: int) -> None:
        """Every working Day order expires, stamped ``ts``."""
        self._now = max(self._now, ts)
        i = 0
        while i < len(self._working):
            if self._working[i].intent.time_in_force is TimeInForce.DAY:
                self._expire(i, ts)
            else:
                i += 1

    def advance_to(self, ts: int) -> None:
        """Move event time to ``ts`` with no market event."""
        self._advance(ts)

    # -- internals -----------------------------------------------------------------------
    def _advance(self, ts: int) -> None:
        i = 0
        while i < len(self._working):
            at = self._working[i].expire_at
            if at is not None and at <= ts:
                self._expire(i, at)
            else:
                i += 1
        self._now = max(self._now, ts)

    def _expire(self, idx: int, ts: int) -> None:
        w = self._working.pop(idx)
        self._events.append(Expired(w.order_id, self._rest(w), ts))

    @staticmethod
    def _close_after(now: int) -> int:
        candidate = now // _NS_PER_DAY * _NS_PER_DAY + _DEFAULT_CLOSE_NS
        return candidate + _NS_PER_DAY if candidate < now else candidate

    @staticmethod
    def _rest(w: _Working) -> OrderIntent:
        """The order's intent carrying its unfilled remainder."""
        if w.intent.quantity == w.remaining:
            return w.intent
        return dataclasses.replace(w.intent, quantity=w.remaining)

    def _reject(
        self, order_id: str, intent: OrderIntent, qty: Decimal, reason: str, ts: int
    ) -> None:
        if intent.quantity != qty:
            intent = dataclasses.replace(intent, quantity=qty)
        self._events.append(Rejected(order_id, intent, reason, ts))

    def _touch(self, iid: InstrumentId, side: OrderSide) -> tuple[Decimal, Decimal] | None:
        b = self._books.get(iid)
        if b is None:
            return None
        px, sz = (b[1], b[3]) if side is OrderSide.BUY else (b[0], b[2])
        return (px, sz) if (px.is_finite() and px > 0 and sz > 0) else None

    def _aggress(self, idx: int, ts: int, first: bool) -> bool:
        """Match order ``idx`` against the touch; True when it left the working set."""
        w = self._working[idx]
        side, tif, remaining = w.intent.side, w.intent.time_in_force, w.remaining
        iid = w.intent.instrument_id
        touch = self._touch(iid, side)
        if touch is not None and w.limit is not None:
            ok = touch[0] <= w.limit if side is OrderSide.BUY else touch[0] >= w.limit
            touch = touch if ok else None
        if first and tif is TimeInForce.FOK and (touch is None or touch[1] + _QTY_EPS < remaining):
            self._working.pop(idx)
            self._reject(w.order_id, w.intent, w.remaining, "fok_unfillable", ts)
            return True
        if touch is not None:
            px, sz = touch
            filled, removed = self._execute(idx, min(sz, remaining), px, ts, False)
            book = self._books.get(iid)
            if book is not None:
                k = 3 if side is OrderSide.BUY else 2
                book[k] = max(book[k] - filled, Decimal(0))
            if removed:
                return True
        if first and tif is TimeInForce.IOC:
            self._working.pop(idx)
            self._events.append(Cancelled(w.order_id, self._rest(w), ts))
            return True
        return False

    def _execute(
        self, idx: int, avail: Decimal, base: Decimal, ts: int, passive: bool
    ) -> tuple[Decimal, bool]:
        """Fill up to ``avail`` of order ``idx`` at ``base``: caps, funding cut, costs."""
        w = self._working[idx]
        side = w.intent.side
        iid = w.intent.instrument_id
        qty = min(avail, w.remaining)
        cut: str | None = None
        if self._long_only and side is OrderSide.SELL:
            capped = max(Decimal(0), min(qty, self.positions.get(iid, Decimal(0))))
            if capped < qty:
                cut = "no_position"
                qty = capped
        px = base
        if w.limit is not None:
            px = min(px, w.limit) if side is OrderSide.BUY else max(px, w.limit)
        if side is OrderSide.BUY and qty > 0 and self._buy_cost(qty, px) > self._cash:
            qty = self._affordable(qty, px, self._cash, self._lot_sizes.get(iid, Decimal(1)))
            cut = "insufficient_funds"
        if qty > 0:
            notional = Money.mul_qty(qty, px, self._currency).amount
            cost = self._costs(side, qty, px)
            delta = -(notional + cost) if side is OrderSide.BUY else notional - cost
            w.remaining -= qty
            w.filled += qty
            self._cash += delta
            self._book_fill(w, px, qty, notional, cost, ts)
        if cut is not None:
            self._working.pop(idx)
            self._reject(w.order_id, w.intent, w.remaining, cut, ts)
            return qty, True
        if w.remaining <= _QTY_EPS:
            self._working.pop(idx)
            return qty, True
        return qty, False

    def _book_fill(
        self, w: _Working, price: Decimal, qty: Decimal, notional: Decimal, cost: Decimal, ts: int
    ) -> None:
        iid = w.intent.instrument_id
        signed = qty if w.intent.side is OrderSide.BUY else -qty
        held = self.positions.get(iid, Decimal(0)) + signed
        self.positions.pop(iid, None)  # the native book re-appends: last updated is last
        if abs(held) > _QTY_EPS:
            self.positions[iid] = held
        self._fees += cost
        self._traded += notional
        trade = Trade(
            iid,
            w.intent.side,
            qty,
            price,
            ts,
            w.order_id,
            costs=Money(cost, self._currency),
        )
        self._events.append(Fill(trade, w.filled, w.remaining <= _QTY_EPS))

    def _costs(self, side: OrderSide, qty: Decimal, px: Decimal) -> Decimal:
        cost = self._cost_fn(side, qty, px)
        if cost.amount == 0:
            return Decimal(0)
        if cost.currency is not self._currency:
            raise ValueError(f"currency mismatch: fill cost {cost}, port {self._currency}")
        if cost.amount < 0:
            raise ValueError(f"fill cost must not be negative, got {cost}")
        return cost.amount

    def _buy_cost(self, qty: Decimal, px: Decimal) -> Decimal:
        return Money.mul_qty(qty, px, self._currency).amount + self._costs(
            OrderSide.BUY, qty, px
        )

    def _affordable(
        self, want: Decimal, px: Decimal, available: Decimal, lot: Decimal = Decimal(1)
    ) -> Decimal:
        """Largest whole number of lots (<= ``want``) whose notional plus cost fits."""
        if px <= 0 or available <= 0:
            return Decimal(0)
        hi = int(
            min(
                (want / lot + _QTY_EPS).to_integral_value(rounding=ROUND_FLOOR),
                (available / px / lot + _QTY_EPS).to_integral_value(rounding=ROUND_FLOOR),
            )
        )
        lo = 0
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._buy_cost(mid * lot, px) <= available:
                lo = mid
            else:
                hi = mid - 1
        return Decimal(lo) * lot


def resolve_l2_backend(requested: BackendChoice | None = None) -> Backend:
    """The backend an :class:`L2Execution` built now would run on (see ``resolve_backend``).

    The wheel has no compiled ``_tantra`` simulator (ex 0006), so every usable choice
    resolves to ``"python"``; a ``"native"`` request raises :class:`NotImplementedError`
    (mirror: ``tantra-examples/docs/gaps/0006-tantra-wheel-kernel-domain-surface.md``).
    """
    return resolve_backend(requested)


class L2Execution(BaseExecutionPort):
    """``ExecutionPort`` matching orders against a quote / trade stream (see module docs).

    Feed it ``QuoteTick`` and ``TradeTick`` events through :meth:`on_event` (other events are
    ignored); submit and cancel as for any port. Always runs the pure-Python reference
    (:class:`_PythonL2`): the wheel has no compiled simulator, so :attr:`backend` is
    ``"python"`` and a ``"native"`` request raises :class:`NotImplementedError` (ex 0006).
    """

    def __init__(
        self,
        *,
        cash: Money,
        costs: FillCostFn = zero_costs,
        long_only: bool = True,
        lot_sizes: Mapping[InstrumentId, Decimal] | None = None,
        backend: BackendChoice | None = None,
    ) -> None:
        self._backend: Backend = resolve_l2_backend(backend)
        self._impl: _PythonL2 = _PythonL2(
            cash=cash, costs=costs, long_only=long_only, lot_sizes=lot_sizes
        )

    @property
    def backend(self) -> Backend:
        """``"python"``: the implementation this port runs on (no native sim in the wheel)."""
        return self._backend

    # -- state ---------------------------------------------------------------------------
    @property
    def cash(self) -> Money:
        """Booked cash (a fill moves it at once)."""
        return self._impl.cash

    @property
    def fees(self) -> Money:
        """Transaction costs paid so far."""
        return self._impl.fees

    @property
    def traded_notional(self) -> Money:
        """Sum of the notional of every fill."""
        return self._impl.traded_notional

    @property
    def positions(self) -> MutableMapping[InstrumentId, Decimal]:
        """Net quantity per instrument; assigning an entry seeds a holding (zero removes it)."""
        return self._impl.positions

    @property
    def working_orders(self) -> list[str]:
        """Ids of orders not yet filled, rejected, cancelled or expired, in submission order."""
        return self._impl.working_orders

    def book(self, instrument_id: InstrumentId) -> TopOfBook | None:
        """The top of book of ``instrument_id`` once quoted, else ``None``."""
        return self._impl.book(instrument_id)

    # -- ExecutionPort -------------------------------------------------------------------
    def submit(self, order_id: str, intent: OrderIntent, ts: int) -> None:
        """Accept an order at event time ``ts`` (a trailing stop is rejected at once)."""
        self._impl.submit(order_id, intent, ts)

    def cancel(self, order_id: str, now: int) -> None:
        """Cancel a working order; ``CancelRequested`` and ``Cancelled`` are stamped ``now``."""
        self._impl.cancel(order_id, now)

    def drain_events(self) -> list[ExecutionEvent]:
        """Return/clear the ordered execution events (a fill precedes its remainder's reject)."""
        return self._impl.drain_events()

    # -- market driver ---------------------------------------------------------------------
    def on_event(self, event: Any, ts_init: int) -> None:
        """Observe the runner's event stream: quotes and trades drive matching."""
        self._impl.on_event(event, ts_init)

    def on_quote(self, quote: QuoteTick) -> None:
        """Update the book and match working orders."""
        self._impl.on_quote(quote)

    def on_trade(self, trade: TradeTick) -> None:
        """Fill resting limits the print trades through and trigger the stops it crosses."""
        self._impl.on_trade(trade)

    def advance_to(self, ts: int) -> None:
        """Move event time to ``ts`` with no market event; due Day orders expire."""
        self._impl.advance_to(ts)

    def on_session_close(self, ts: int) -> None:
        """Explicit session close: every working Day order expires, stamped ``ts``."""
        self._impl.on_session_close(ts)

    def set_lot_size(self, instrument_id: InstrumentId, lot_size: Decimal) -> None:
        """Quantity step a funding cut floors to for ``instrument_id`` (default 1)."""
        self._impl.set_lot_size(instrument_id, lot_size)

    def set_position(self, instrument_id: InstrumentId, quantity: Decimal) -> None:
        """Seed a holding of ``quantity`` for ``instrument_id`` (zero removes it)."""
        self._impl.set_position(instrument_id, quantity)
