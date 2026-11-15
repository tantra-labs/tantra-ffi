# wheel surface (ex 0006): backtest simulators (mirrors tantra_examples/_kernel/backtest public API)
# stand-in closure for tantra-examples gap 0006

"""Simulated execution ports for backtests.

:class:`NextOpenExecution` is a deterministic multi-instrument ``ExecutionPort``
(``tantra.execution``) that fills market orders at the next session's open.
Rules:

* **Sessions.** A session is one point on the driving clock, identified by an
  increasing integer (the bars' ``ts`` by default). Open one explicitly with
  :meth:`NextOpenExecution.open_session` or a :class:`SessionOpen` event (all of the
  session's bars at once), or let plain ``Bar`` events open it: the first bar with a new
  ``ts`` opens a session, later bars with that ``ts`` open their own instruments.
* **Timing.** An order submitted during session *k* fills at the open of the
  instrument's first bar in a later session; it never sees the close that produced it.
  If the instrument does not print, the order waits.
* **Order within a session.** For the instruments opened together, sells fill before
  buys; each side in submission order.
* **Impact.** With ``impact=`` a fill never happens at the printed open: the price is
  degraded by :class:`tantra.backtest.impact.MarketImpact` (square-root law, past
  sessions only) and costs are charged on that price.
* **Opening auction.** With ``auction=`` every fill at a printed open pays the adverse
  spread buffer of :class:`tantra.backtest.opening_auction.OpeningAuction`
  (``spread_bps``, stacking with ``impact=``) and an order waits ``delay_bars`` extra
  driving bars after submission before it may fill — the post-open turbulence window of
  Balch pitfall #8.
* **Cash.** Decimal ``Money``, notional ``Money.mul_qty`` like the ledger. A buy debits
  ``notional + cost`` at once; a sell credits ``notional - cost`` at once but the
  proceeds only become *available* ``settlement_days`` sessions later.
* **Funding.** A buy that available cash cannot cover waits up to ``settlement_days``
  sessions for sale proceeds to settle, then is cut to the whole units cash allows; the
  rest is reported as a ``Rejected`` event (``"insufficient_funds"``), after the fill.
* **Long only** (default). A sell is capped at the position held; the rest is rejected
  (``"no_position"``).
* **Order types.** Market orders only; any other type is rejected
  (``"unsupported_order_type"``).
* **Cancel.** ``cancel(order_id, now)`` drops a working order and reports it as a
  ``Cancelled`` event stamped ``now``.
* **Events.** ``drain_events()`` is the one ordered stream (ADR 0019): a ``Fill``
  precedes the ``Rejected`` of its remainder. ``drain_fills()`` /
  ``drain_rejections()`` are the buffered legacy shim over it (removed in 0.3.0).

The settlement cycle and the cost schedule are market rules and are injected:
:func:`make_simulator` normally takes them from ``markets.india``
(``settlement_days_for(exchange, as_of=...)``); that pack is not in the wheel yet
(gap 0004), so an explicit ``settlement_days`` is required for now. A session is
one bar, so the cycle counts bars: that equals trading days only for daily-or-longer
timeframes, and :func:`make_simulator` therefore requires an explicit ``settlement_days``
for intraday timeframes. Pure: no I/O and no wall clock.

**Backend.** The wheel has no compiled simulator in ``_tantra``, so
:class:`NextOpenExecution` always runs the pure-Python reference
(:class:`_PythonSim`); :func:`resolve_backend` always resolves to ``"python"`` and
requesting ``backend="native"`` raises :class:`NotImplementedError`
(mirror: ``tantra-examples/docs/gaps/0006-tantra-wheel-kernel-domain-surface.md``).

Decimal-canonical (rust_decimal parity): quantities, prices, lot sizes and cash are
exact ``decimal.Decimal`` values (``zero_costs`` returns ``Money.zero(INR)``).
"""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

import dataclasses
import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_FLOOR
from typing import Any, Literal

from tantra.backtest.impact import (
    MarketImpact,  # gap 0006: backtest simulator mirror
)
from tantra.backtest.opening_auction import (
    OpeningAuction,  # gap 0006: backtest simulator mirror
)
from tantra.bar import Bar
from tantra.execution import (
    BaseExecutionPort,
    Cancelled,
    ExecutionEvent,
    ExecutionPortLike,
    Fill,
    Rejected,
)
from tantra.instrument import InstrumentId
from tantra.money import Currency, Money
from tantra.order import OrderIntent, OrderSide, OrderType
from tantra.trade import Trade
from tantra.types import to_decimal

__all__ = [
    "BACKEND_ENV",
    "FillCostFn",
    "FillModel",
    "MarketImpact",
    "NextOpenExecution",
    "OpeningAuction",
    "SessionOpen",
    "fill_costs_from_model",
    "group_sessions",
    "is_intraday",
    "make_simulator",
    "resolve_backend",
    "resolve_fill_costs",
    "session_date",
    "zero_costs",
]

FillModel = Literal["bar_close", "next_open", "l2"]

Backend = Literal["python", "native"]
"""The implementation behind a :class:`NextOpenExecution`."""

BackendChoice = Literal["auto", "python", "native"]
"""``backend=`` values: the wheel has no native simulator, so ``auto`` is python."""

BACKEND_ENV = "VYAAPAAR_SIM_BACKEND"
"""Environment variable giving the default :data:`BackendChoice` (``auto`` when unset)."""

FillCostFn = Callable[[OrderSide, Decimal, Decimal], Money]
"""``(side, quantity, price) -> cost`` of one fill, never negative, in the port's currency."""


def zero_costs(side: OrderSide, quantity: Decimal, price: Decimal) -> Money:
    """No transaction costs."""
    return Money.zero(Currency.INR)


@dataclass(frozen=True, slots=True)
class SessionOpen:
    """Opens session ``ts`` with every bar that opens it (one per instrument).

    Feed it to the runner before the session's bars (``group_sessions`` does) so sells
    of every instrument fill before buys of any. The runner dispatches it to no hook.
    """

    ts: int
    bars: tuple[Bar, ...]


@dataclass
class _Working:
    order_id: str
    intent: OrderIntent
    session: int  # index of the session it was submitted in
    first_try: int | None = None  # first session it was eligible and considered


class _PythonSim:
    """The pure-Python next-open simulator: the reference implementation (ADR 0016).

    The wheel has no compiled ``_tantra`` simulator (ex 0006), so this is the only
    implementation behind :class:`NextOpenExecution`.
    """

    def __init__(
        self,
        *,
        cash: Money,
        settlement_days: int = 0,
        costs: FillCostFn = zero_costs,
        long_only: bool = True,
        lot_sizes: Mapping[InstrumentId, Decimal] | None = None,
        impact: MarketImpact | None = None,
        auction: OpeningAuction | None = None,
    ) -> None:
        if settlement_days < 0:
            raise ValueError("settlement_days must be >= 0")
        if cash.amount < 0:
            raise ValueError("cash must be >= 0")
        self.settlement_days = settlement_days
        self.cash = cash
        self.fees = Money.zero(cash.currency)
        self.traded_notional = Money.zero(cash.currency)
        self.positions: dict[InstrumentId, Decimal] = {}
        self._currency = cash.currency
        self._cost_fn = costs
        self._impact = impact
        self._auction = auction
        self._lot_sizes: dict[InstrumentId, Decimal] = {}
        for iid, lot in (lot_sizes or {}).items():
            self.set_lot_size(iid, lot)
        self._long_only = long_only
        self._session = -1
        self._session_ts: int | None = None
        self._from_open = False  # the current session came from a SessionOpen event
        self._opened: set[InstrumentId] = set()
        self._working: list[_Working] = []
        self._receivables: list[tuple[int, Money]] = []  # (available from session, amount)
        self._events: list[ExecutionEvent] = []

    # -- cash ----------------------------------------------------------------------
    @property
    def unsettled(self) -> Money:
        """Sale proceeds booked but not yet available."""
        total = Money.zero(self._currency)
        for due, amount in self._receivables:
            if due > self._session:
                total = total + amount
        return total

    @property
    def available_cash(self) -> Money:
        """Cash that may fund a buy now: booked cash less unsettled sale proceeds."""
        return self.cash - self.unsettled

    @property
    def working_orders(self) -> list[str]:
        """Ids of orders not yet filled, rejected or cancelled, in submission order."""
        return [w.order_id for w in self._working]

    # -- ExecutionPort -------------------------------------------------------------
    def submit(self, order_id: str, intent: OrderIntent, ts: int) -> None:
        if intent.side not in (OrderSide.BUY, OrderSide.SELL):
            raise ValueError(f"order {order_id} has no side: it must be buy or sell")
        if any(w.order_id == order_id for w in self._working):
            raise ValueError(f"order id {order_id} is already working")
        if intent.order_type is not OrderType.MARKET:
            self._reject(order_id, intent, "unsupported_order_type", ts)
            return
        self._working.append(_Working(order_id, intent, self._session))

    def drain_events(self) -> list[ExecutionEvent]:
        out, self._events = self._events, []
        return out

    def cancel(self, order_id: str, now: int) -> None:
        for w in self._working:
            if w.order_id == order_id:
                self._working.remove(w)
                self._events.append(Cancelled(order_id, w.intent, now))
                return

    # -- session driver ------------------------------------------------------------
    def on_event(self, event: Any, ts_init: int) -> None:
        """Observe the runner's event stream (called before the strategy sees it)."""
        if isinstance(event, SessionOpen):
            self.open_session(event.ts, event.bars)
            self._from_open = True
        elif isinstance(event, Bar):
            if self._from_open:
                # The SessionOpen carried this session's bars and its key need not be a
                # timestamp, so a bar never opens or orders sessions here; it only
                # opens an instrument the SessionOpen left out, at the same ts.
                if event.ts == self._session_ts and event.instrument_id not in self._opened:
                    self._fill_at([event])
            elif self._session_ts is None or event.ts > self._session_ts:
                self.open_session(event.ts, [event])
                self._from_open = False
            elif event.ts < self._session_ts:
                raise ValueError(
                    f"non-monotonic bar: ts {event.ts} is before session {self._session_ts}"
                )
            elif event.instrument_id in self._opened:
                raise ValueError(
                    f"duplicate bar for {event.instrument_id} at ts {event.ts} in session "
                    f"{self._session_ts}"
                )
            else:
                self._fill_at([event])

    def open_session(self, ts: int, bars: Sequence[Bar]) -> None:
        """Start session ``ts``: settle due proceeds, then fill eligible orders at the opens."""
        if self._session_ts is not None and ts <= self._session_ts:
            raise ValueError(f"session {ts} does not follow session {self._session_ts}")
        self._session += 1
        self._session_ts = ts
        self._opened = set()
        self._receivables = [(d, a) for d, a in self._receivables if d > self._session]
        self._fill_at(bars)

    # -- internals -----------------------------------------------------------------
    def set_settlement_days(self, settlement_days: int) -> None:
        """Change the settlement cycle before the first session opens."""
        if settlement_days < 0:
            raise ValueError("settlement_days must be >= 0")
        if self._session_ts is not None:
            raise RuntimeError("settlement_days can only change before the first session")
        self.settlement_days = settlement_days

    def set_lot_size(self, instrument_id: InstrumentId, lot_size: Decimal) -> None:
        """Quantity step a funding cut floors to for ``instrument_id`` (default 1)."""
        lot = to_decimal(lot_size)
        if not (lot.is_finite() and lot > 0):
            raise ValueError(f"lot_size must be positive, got {lot_size}")
        self._lot_sizes[instrument_id] = lot

    def _costs(self, side: OrderSide, qty: Decimal, px: Decimal) -> Money:
        cost = self._cost_fn(side, qty, px)
        if cost.amount == 0:
            return Money.zero(self._currency)  # a zero schedule is currency-neutral
        if cost.amount < 0:
            raise ValueError(f"fill cost must not be negative, got {cost}")
        if cost.currency is not self._currency:
            # Checked here, before an order is dequeued, so a failing cost leaves the order
            # working and the state unchanged (a sell used to fail only at the proceeds sum).
            raise ValueError(f"currency mismatch: fill cost {cost}, port {self._currency}")
        return cost

    def _now(self) -> int:
        return self._session_ts or 0

    def _fill_at(self, bars: Sequence[Bar]) -> None:
        opens: dict[InstrumentId, Bar] = {}
        for b in bars:
            if b.instrument_id not in self._opened and _usable_open(b.open):
                opens.setdefault(b.instrument_id, b)
        self._opened.update(opens)
        # The post-open delay holds every order back for ``delay_bars`` extra sessions.
        delay = self._auction.delay_bars if self._auction is not None else 0
        eligible = [
            w
            for w in self._working
            if w.session + delay < self._session and w.intent.instrument_id in opens
        ]
        for w in eligible:
            if w.intent.side is OrderSide.SELL:
                self._fill_sell(w, opens[w.intent.instrument_id])
        for w in eligible:
            if w.intent.side is OrderSide.BUY:
                self._fill_buy(w, opens[w.intent.instrument_id])
        # After the fills: a session's own volume/close only ever informs *later* fills.
        if self._impact is not None:
            for b in bars:
                self._impact.observe(b.instrument_id, volume=b.volume, close=b.close)

    def _exec_price(self, side: OrderSide, bar: Bar, quantity: Decimal) -> Decimal:
        """The fill price: the printed open adverse of the auction buffer and impact, if any."""
        fraction = Decimal(0)
        if self._auction is not None:
            fraction += self._auction.fraction  # the opening auction is crossed whatever the size
        if self._impact is not None:
            fraction += self._impact.fraction(bar.instrument_id, quantity)
        if fraction <= 0:
            return bar.open
        px = bar.open * (Decimal(1) + fraction) if side is OrderSide.BUY else bar.open * (
            Decimal(1) - fraction
        )
        return px if _usable_open(px) else bar.open

    def _fill_sell(self, w: _Working, bar: Bar) -> None:
        want = w.intent.quantity
        qty = want
        if self._long_only:
            held = self.positions.get(w.intent.instrument_id, Decimal(0))
            qty = max(Decimal(0), min(want, held))
            if Decimal(0) < qty < want and want - qty <= _QTY_EPS:
                want = qty  # a hair over the position is float residue: sell it all, no reject
        if qty > 0:  # compute before dequeuing: a failure leaves the order working
            px = self._exec_price(OrderSide.SELL, bar, qty)
            notional = Money.mul_qty(qty, px, self._currency)
            cost = self._costs(OrderSide.SELL, qty, px)
            self._working.remove(w)
            proceeds = notional - cost
            self.cash = self.cash + proceeds
            self._receivables.append((self._session + self.settlement_days, proceeds))
            self._book(w, bar, qty, notional, cost, qty >= want, price=px)
        else:
            self._working.remove(w)
        if qty < want:
            self._reject_part(w, want - qty, "no_position")

    def _fill_buy(self, w: _Working, bar: Bar) -> None:
        if w.first_try is None:
            w.first_try = self._session
        want = w.intent.quantity
        px = self._exec_price(OrderSide.BUY, bar, want)
        available = self.available_cash
        if self._buy_cost(want, px).amount <= available.amount:
            qty = want
        elif self.unsettled.amount > 0 and self._session - w.first_try < self.settlement_days:
            return  # wait for pending sale proceeds to settle
        else:
            qty = self._affordable(
                want, px, available, self._lot_sizes.get(w.intent.instrument_id, Decimal(1))
            )
        if qty > 0:  # compute before dequeuing: a failure leaves the order working
            if qty != want:  # a funding cut shrinks the order, so reprice the impact
                px = self._exec_price(OrderSide.BUY, bar, qty)
            notional = Money.mul_qty(qty, px, self._currency)
            cost = self._costs(OrderSide.BUY, qty, px)
            self._working.remove(w)
            self.cash = self.cash - (notional + cost)
            self._book(w, bar, qty, notional, cost, qty >= want, price=px)
        else:
            self._working.remove(w)
        if qty < want:
            self._reject_part(w, want - qty, "insufficient_funds")

    def _buy_cost(self, qty: Decimal, px: Decimal) -> Money:
        return Money.mul_qty(qty, px, self._currency) + self._costs(OrderSide.BUY, qty, px)

    def _affordable(
        self, want: Decimal, px: Decimal, available: Money, lot: Decimal = Decimal(1)
    ) -> Decimal:
        """Largest whole number of lots (<= ``want``) whose notional plus cost fits ``available``.

        Costs are assumed non-decreasing in quantity, so the answer is found by bisection
        between zero and the cost-free bound instead of stepping down one lot at a time.
        """
        if px <= 0 or available.amount <= 0:
            return Decimal(0)
        hi = min(
            (want / lot + _QTY_EPS).to_integral_value(rounding=ROUND_FLOOR),
            (available.to_major() / px / lot + _QTY_EPS).to_integral_value(
                rounding=ROUND_FLOOR
            ),
        )
        lo = 0
        while lo < hi:  # invariant: lo lots are affordable (0 trivially), hi + 1 are not
            mid = (lo + hi + 1) // 2
            if self._buy_cost(mid * lot, px).amount <= available.amount:
                lo = mid
            else:
                hi = mid - 1
        return lo * lot

    def _book(
        self,
        w: _Working,
        bar: Bar,
        qty: Decimal,
        notional: Money,
        cost: Money,
        complete: bool,
        *,
        price: Decimal,
    ) -> None:
        iid = w.intent.instrument_id
        signed = qty if w.intent.side is OrderSide.BUY else -qty
        held = self.positions.get(iid, Decimal(0)) + signed
        if abs(held) <= _QTY_EPS:
            self.positions.pop(iid, None)
        else:
            self.positions[iid] = held
        self.fees = self.fees + cost
        self.traded_notional = self.traded_notional + notional
        trade = Trade(iid, w.intent.side, qty, price, bar.ts, w.order_id, costs=cost)
        # One fill per order: its cumulative quantity is its own.
        self._events.append(Fill(trade, qty, complete))

    def _reject_part(self, w: _Working, qty: Decimal, reason: str) -> None:
        self._reject(
            w.order_id, dataclasses.replace(w.intent, quantity=qty), reason, self._now()
        )

    def _reject(self, order_id: str, intent: OrderIntent, reason: str, ts: int) -> None:
        self._events.append(Rejected(order_id, intent, reason, ts))


_QTY_EPS = Decimal("1e-9")  # quantities closer than this are equal (fractional-lot residue)


def _usable_open(price: Decimal) -> bool:
    return price.is_finite() and price > 0


# -- backend selection ---------------------------------------------------------------------------
def resolve_backend(requested: BackendChoice | None = None) -> Backend:
    """The backend a :class:`NextOpenExecution` built now would run on.

    ``requested`` (``"auto"``, ``"python"``, ``"native"``) wins over the
    ``VYAAPAAR_SIM_BACKEND`` environment variable, which wins over the default
    ``"auto"``. The wheel has no compiled ``_tantra`` simulator (ex 0006), so every
    usable choice resolves to ``"python"``; a ``"native"`` request raises
    :class:`NotImplementedError`
    (mirror: ``tantra-examples/docs/gaps/0006-tantra-wheel-kernel-domain-surface.md``).
    """
    if requested is None:
        raw = os.environ.get(BACKEND_ENV, "").strip().lower() or "auto"
        origin = f"{BACKEND_ENV}={os.environ.get(BACKEND_ENV)!r}"
    else:
        raw, origin = str(requested).strip().lower(), f"backend={requested!r}"
    if raw not in ("auto", "python", "native"):
        raise ValueError(f"{origin}: backend must be 'auto', 'python' or 'native'")
    if raw == "native":
        raise NotImplementedError(
            f"{origin}: the native Rust simulator is not compiled into the wheel; only the "
            "python backend exists "
            "(tantra-examples/docs/gaps/0006-tantra-wheel-kernel-domain-surface.md)"
        )
    return "python"


class NextOpenExecution(BaseExecutionPort):
    """``ExecutionPort`` filling market orders at the next session's open (see module docs).

    Always runs the pure-Python reference (:class:`_PythonSim`): the wheel has no
    compiled simulator, so :attr:`backend` is ``"python"`` and a ``"native"`` request
    raises :class:`NotImplementedError` (ex 0006).
    """

    def __init__(
        self,
        *,
        cash: Money,
        settlement_days: int = 0,
        costs: FillCostFn = zero_costs,
        long_only: bool = True,
        lot_sizes: Mapping[InstrumentId, Decimal] | None = None,
        backend: BackendChoice | None = None,
        impact: MarketImpact | None = None,
        auction: OpeningAuction | None = None,
    ) -> None:
        if impact is not None and backend == "native":
            raise ValueError(
                "impact= needs the Python backend (the native simulator has no market-impact "
                "model in the wheel): drop backend='native'"
            )
        if auction is not None and backend == "native":
            raise ValueError(
                "auction= needs the Python backend (the native simulator has no opening-auction "
                "model in the wheel): drop backend='native'"
            )
        # ``auto`` with impact/auction resolves to python: both are only implemented there today.
        self._backend: Backend = (
            "python" if (impact is not None or auction is not None) else resolve_backend(backend)
        )
        self._impl: _PythonSim = _PythonSim(
            cash=cash,
            settlement_days=settlement_days,
            costs=costs,
            long_only=long_only,
            lot_sizes=lot_sizes,
            impact=impact,
            auction=auction,
        )

    @property
    def backend(self) -> Backend:
        """``"python"``: the implementation this port runs on (no native sim in the wheel)."""
        return self._backend

    # -- state ---------------------------------------------------------------------------
    @property
    def settlement_days(self) -> int:
        """Sessions after a sale before its proceeds are available."""
        return self._impl.settlement_days

    @property
    def cash(self) -> Money:
        """Booked cash (sale proceeds count at once, see :attr:`available_cash`)."""
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
    def positions(self) -> dict[InstrumentId, Decimal]:
        """Net quantity per instrument; assigning an entry seeds a holding."""
        return self._impl.positions

    @property
    def unsettled(self) -> Money:
        """Sale proceeds booked but not yet available."""
        return self._impl.unsettled

    @property
    def available_cash(self) -> Money:
        """Cash that may fund a buy now: booked cash less unsettled sale proceeds."""
        return self._impl.available_cash

    @property
    def working_orders(self) -> list[str]:
        """Ids of orders not yet filled, rejected or cancelled, in submission order."""
        return self._impl.working_orders

    # -- ExecutionPort -------------------------------------------------------------------
    def submit(self, order_id: str, intent: OrderIntent, ts: int) -> None:
        self._impl.submit(order_id, intent, ts)

    def drain_events(self) -> list[ExecutionEvent]:
        """Return and clear the ordered execution events (a fill precedes its remainder's reject).

        ``drain_fills()`` / ``drain_rejections()`` are the buffered legacy split of this
        stream.
        """
        return self._impl.drain_events()

    def cancel(self, order_id: str, now: int) -> None:
        """Cancel a working order; the ``Cancelled`` event is stamped ``now``."""
        self._impl.cancel(order_id, now)

    # -- session driver ------------------------------------------------------------------
    def on_event(self, event: Any, ts_init: int) -> None:
        """Observe the runner's event stream (called before the strategy sees it)."""
        self._impl.on_event(event, ts_init)

    def open_session(self, ts: int, bars: Sequence[Bar]) -> None:
        """Start session ``ts``: settle due proceeds, then fill eligible orders at the opens."""
        self._impl.open_session(ts, bars)

    def set_settlement_days(self, settlement_days: int) -> None:
        """Change the settlement cycle before the first session opens."""
        self._impl.set_settlement_days(settlement_days)

    def set_lot_size(self, instrument_id: InstrumentId, lot_size: Decimal) -> None:
        """Quantity step a funding cut floors to for ``instrument_id`` (default 1)."""
        self._impl.set_lot_size(instrument_id, lot_size)


def group_sessions(
    bars: Sequence[Bar], key: Callable[[Bar], int] | None = None
) -> list[tuple[Any, int]]:
    """Order ``bars`` into runner events: per session a :class:`SessionOpen`, then its bars.

    ``key`` maps a bar to its session (default: ``bar.ts``); sessions run in key order and
    bars within one by ``(ts, symbol, exchange)``. Each event's ``ts_init`` is the bar's
    ``ts`` (the ``SessionOpen`` takes its first bar's).
    """
    session_of = key or (lambda b: b.ts)
    ordered = sorted(
        bars,
        key=lambda b: (
            session_of(b),
            b.ts,
            b.instrument_id.symbol,
            b.instrument_id.exchange,
        ),
    )
    events: list[tuple[Any, int]] = []
    i = 0
    while i < len(ordered):
        k = session_of(ordered[i])
        j = i
        while j < len(ordered) and session_of(ordered[j]) == k:
            j += 1
        group = tuple(ordered[i:j])
        events.append((SessionOpen(k, group), group[0].ts))
        events.extend((b, b.ts) for b in group)
        i = j
    return events


_FILL_COSTS: dict[str, str] = {
    "none": "zero",
    "zero": "zero",
    "india.equity": "delivery",
    "india.equity.delivery": "delivery",
    "india.equity.intraday": "intraday",
}


def resolve_fill_costs(name: str) -> FillCostFn:
    """Map a cost-pack name to a fill-cost function.

    Only the zero packs exist in the wheel: the India equity cost schedule ships in gap
    0004 (``tantra.markets.india``), so ``india.equity*`` raises :class:`NotImplementedError`
    (mirror: ``tantra-examples/docs/gaps/0004-*``).
    """
    kind = _FILL_COSTS.get(name.strip().lower())
    if kind is None:
        raise ValueError(f"unknown cost pack {name!r}; expected one of {sorted(_FILL_COSTS)}")
    if kind == "zero":
        return zero_costs
    raise NotImplementedError(
        f"cost pack {name!r} needs the India equity cost schedule (gap 0004): "
        "tantra.markets.india is not in the wheel yet; use costs='none' or a custom "
        "FillCostFn"
    )


_INTRADAY = re.compile(
    r"^\s*\d*\s*(s|sec|second|seconds|m|min|mins|minute|minutes|h|hr|hour|hours)\s*$",
    re.IGNORECASE,
)
_IST_OFFSET = timedelta(hours=5, minutes=30)
_EPOCH = datetime(1970, 1, 1)


def is_intraday(timeframe: str) -> bool:
    """True for sub-daily bar sizes ("1m", "5min", "1h", ...); "1d"/"1w" and unknowns are not."""
    return _INTRADAY.match(timeframe) is not None


def session_date(ts_ns: int) -> date:
    """Trading date (IST, the India market clock) of a unix-nanosecond timestamp."""
    return (_EPOCH + timedelta(seconds=ts_ns // 10**9) + _IST_OFFSET).date()


def fill_costs_from_model(model: Any, *, currency: Currency = Currency.INR) -> FillCostFn:
    """Adapt a post-hoc ``CostModel`` (``apply(trade) -> trade``) to a :data:`FillCostFn`.

    The model sees a zero-cost :class:`Trade` for the fill and its returned ``costs`` is the
    fill's cost; the simulator then charges it to cash, so fills, ledger, equity and metrics
    agree. Only ``costs`` is read (a model cannot change price or quantity here). The trade
    carries a placeholder instrument, so a model must not depend on the symbol; use a
    ``FillCostFn`` for that.
    """
    placeholder = InstrumentId("_", "_")

    def cost(side: OrderSide, quantity: Decimal, price: Decimal) -> Money:
        return model.apply(
            Trade(placeholder, side, quantity, price, costs=Money.zero(currency))
        ).costs

    return cost


def make_simulator(
    *,
    fill: FillModel,
    cash: Money,
    costs: str | FillCostFn = "none",
    exchange: str = "NSE",
    settlement_days: int | None = None,
    long_only: bool = True,
    timeframe: str = "1d",
    as_of: date | None = None,
    lot_sizes: Mapping[InstrumentId, Decimal] | None = None,
    impact: MarketImpact | None = None,
    auction: OpeningAuction | None = None,
) -> ExecutionPortLike:
    """Build the simulated port for ``fill``.

    * ``"next_open"``: :class:`NextOpenExecution`; ``settlement_days`` defaults to the
      market pack's cycle for ``exchange`` on ``as_of``. The India market pack
      (``settlement_days_for``) ships in gap 0004, so until then an explicit
      ``settlement_days`` is required (intraday ``timeframe`` values need one anyway
      because the port counts bars, not trading days). ``auction.delay_bars`` (Balch
      pitfall #8) also counts driving bars, so it needs an intraday ``timeframe``.
    * ``"l2"``: the L2 simulator (``tantra.backtest.l2_sim``), matching orders against a
      ``QuoteTick`` / ``TradeTick`` stream — ships in a later ex 0006 wave.
    * ``"bar_close"``: the single-price conformance simulator
      (``BarCloseFills``) — ships in a later ex 0006 wave.
    """
    if fill == "next_open":
        if auction is not None and auction.delay_bars > 0 and not is_intraday(timeframe):
            raise ValueError(
                f"auction.delay_bars={auction.delay_bars} counts driving bars, and timeframe "
                f"{timeframe!r} is not intraday: the post-open delay only means anything "
                "sub-daily (e.g. timeframe='1m' with delay_bars=5..15)"
            )
        if settlement_days is None:
            if is_intraday(timeframe):
                raise ValueError(
                    f"timeframe {timeframe!r} is intraday: the simulator counts one session "
                    "per bar, not per trading day, so pass an explicit settlement_days"
                )
            raise NotImplementedError(
                f"no explicit settlement_days for timeframe {timeframe!r}: the India "
                "settlement cycle (settlement_days_for) ships in gap 0004 "
                "(tantra-examples/docs/gaps/0004-*); pass settlement_days explicitly"
            )
        cost_fn = resolve_fill_costs(costs) if isinstance(costs, str) else costs
        return NextOpenExecution(
            cash=cash,
            settlement_days=settlement_days,
            costs=cost_fn,
            long_only=long_only,
            lot_sizes=lot_sizes,
            impact=impact,
            auction=auction,
        )
    if fill == "l2":
        if impact is not None:
            raise ValueError(
                "impact= requires fill='next_open': the L2 simulator has no impact model"
            )
        if auction is not None:
            raise ValueError(
                "auction= requires fill='next_open': the L2 simulator has no "
                "opening-auction model"
            )
        # l2_sim ships in a later ex 0006 wave.
        raise NotImplementedError(
            "fill='l2' needs tantra.backtest.l2_sim, which ships in a later ex 0006 wave"
        )
    if fill == "bar_close":
        if impact is not None:
            raise ValueError(
                "impact= requires fill='next_open': the bar-close conformance simulator has "
                "no market-impact model"
            )
        if auction is not None:
            raise ValueError(
                "auction= requires fill='next_open': the bar-close conformance simulator has "
                "no opening-auction model"
            )
        # BarCloseFills ships in a later ex 0006 wave.
        raise NotImplementedError(
            "fill='bar_close' needs BarCloseFills, which ships in a later ex 0006 wave"
        )
    raise ValueError(f"unknown fill model {fill!r}; expected 'next_open', 'l2' or 'bar_close'")
