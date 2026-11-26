# wheel surface (ex 0006): Decimal-canonical kernel-parity strategy context
# (mirrors tantra_examples/_kernel/context public API; quantities are Decimal)

"""The ``StrategyContext`` port: a strategy's only view of the world (ADR 008).

Mirrors the Rust ``honba_strategy::StrategyContext`` trait. A strategy reads the
clock, its positions, cash and instrument metadata, and submits order intents
through the context. It never touches execution, I/O or the wall clock, so the
same strategy runs unchanged in backtest, paper and live.

The wheel surface is Decimal-canonical (zero-floats policy): every quantity is
an exact ``decimal.Decimal``, unlike the float kernel mirror. Cash is
Decimal major-unit ``Money`` (see ``tantra.money``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from decimal import Decimal

from tantra.instrument import Instrument, InstrumentId
from tantra.money import Currency, Money
from tantra.order import OrderIntent, OrderSide, validate_intent
from tantra.trade import Trade
from tantra.types import OrderSide as CompiledOrderSide

_EPSILON = Decimal("1e-9")


def _is_valid(intent: OrderIntent) -> bool:
    try:
        validate_intent(
            intent.side,
            intent.quantity,
            intent.order_type,
            intent.price,
            intent.trigger_price,
        )
    except ValueError:
        return False
    return True


def _is_buy(side: OrderSide | CompiledOrderSide) -> bool:
    """True for a BUY fill side, whether it carries the wheel or the compiled enum.

    The wheel ``Trade`` accepts either ``tantra.order.OrderSide`` (what intents
    carry) or the compiled ``tantra.types.OrderSide`` (its declared annotation);
    both expose ``BUY``/``SELL``, so map by identity or by the compiled ``code``.
    """
    if side is OrderSide.BUY:
        return True
    if side is OrderSide.SELL:
        return False
    return getattr(side, "code", None) == "BUY"


class StrategyContext(ABC):
    """What a strategy may read and do. Implementations are supplied by the runner."""

    @abstractmethod
    def now(self) -> int:
        """``ts_init`` (unix ns) of the event being processed; 0 before the first event."""

    @abstractmethod
    def position(self, instrument_id: InstrumentId) -> Decimal:
        """Net signed quantity held (positive long, negative short), updated from fills."""

    @abstractmethod
    def positions(self) -> dict[InstrumentId, Decimal]:
        """Every non-flat position, ordered by instrument id (symbol, then exchange)."""

    @abstractmethod
    def cash(self) -> Money:
        """Initial cash plus the net cash flow of all fills (buys debit notional plus
        costs, sells credit notional minus costs), as Decimal major-unit ``Money``."""

    @abstractmethod
    def busy(self, instrument_id: InstrumentId) -> bool:
        """True while an intent submitted for ``instrument_id`` is not fully filled or rejected."""

    @abstractmethod
    def instrument(self, instrument_id: InstrumentId) -> Instrument | None:
        """Instrument metadata (lot and tick size), or ``None`` if the run does not know it."""

    @abstractmethod
    def submit(self, intent: OrderIntent) -> None:
        """Queue an intent; the runner turns it into an order after the current hook returns."""

    # -- optional order management (concrete defaults keep older contexts valid) -----
    def cancel(self, intent: OrderIntent) -> None:
        """Ask for ``intent``'s order to be cancelled. Default: not supported, does nothing.

        Idempotent: an intent that was never submitted, or whose order already finished, is
        ignored. One still waiting to be sent is withdrawn. The runner delivers the request
        to the execution port once the current hook returns.
        """

    def intent_of(self, order_id: str | None) -> OrderIntent | None:
        """The intent the runner sent as ``order_id``, or ``None`` (unknown or unsupported)."""
        return None

    def is_open(self, intent: OrderIntent) -> bool:
        """Whether ``intent`` may still fill: waiting to be sent or working, not finished.

        Default for contexts that cannot tell: ``True``.
        """
        return True

    def pending_quantity(self, instrument_id: InstrumentId) -> Decimal:
        """Quantity submitted for ``instrument_id`` and not yet filled or released.

        Default for contexts that cannot tell: unbounded while ``busy``, else zero.
        """
        return Decimal("Infinity") if self.busy(instrument_id) else Decimal(0)


class LedgerContext(StrategyContext):
    """The reference context (mirrors ``honba_strategy::LedgerContext``).

    A deterministic in-memory ledger: the runner sets the clock, applies fills and
    releases rejected intents; the strategy reads it and submits intents, which the
    runner drains. Pure: no I/O and no wall clock, so backtest and live share it.

    Cash is Decimal major-unit ``Money`` (wheel surface). ``cash`` may be ``Money``
    or a major-unit number, converted once here (half away from zero; non-finite
    raises ``ValueError``).
    """

    def __init__(
        self,
        cash: Money | Decimal | int | str = 0,
        instruments: Iterable[Instrument] = (),
        currency: Currency = Currency.INR,
    ) -> None:
        self._now = 0
        self._cash = cash if isinstance(cash, Money) else Money.from_major(cash, currency)
        self._positions: dict[InstrumentId, Decimal] = {}
        self._pending: dict[tuple[InstrumentId, OrderSide], Decimal] = {}
        self._instruments: dict[InstrumentId, Instrument] = {}
        self._outbox: list[OrderIntent] = []
        self._order_intents: dict[str, OrderIntent] = {}
        self._intent_orders: dict[int, str] = {}  # id(intent) -> order id (intents are kept alive)
        self._closed: set[str] = set()
        self._cancel_asked: set[str] = set()
        self._cancels: list[str] = []
        for instrument in instruments:
            self.add_instrument(instrument)

    # -- StrategyContext ------------------------------------------------------
    def now(self) -> int:
        return self._now

    def position(self, instrument_id: InstrumentId) -> Decimal:
        return self._positions.get(instrument_id, Decimal(0))

    def positions(self) -> dict[InstrumentId, Decimal]:
        held = (item for item in self._positions.items() if item[1] != 0)
        return dict(sorted(held, key=lambda item: (item[0].symbol, item[0].exchange)))

    def cash(self) -> Money:
        return self._cash

    @property
    def currency(self) -> Currency:
        """The currency this ledger settles in."""
        return self._cash.currency

    def busy(self, instrument_id: InstrumentId) -> bool:
        return any(q > 0 for (iid, _), q in self._pending.items() if iid == instrument_id)

    def instrument(self, instrument_id: InstrumentId) -> Instrument | None:
        return self._instruments.get(instrument_id)

    def submit(self, intent: OrderIntent) -> None:
        # An invalid intent (only possible if built around ``OrderIntent``'s validation) is
        # still queued so the runner can reject it, but it must not touch the pending
        # ledger (same rule as the Rust ``LedgerContext``).
        if _is_valid(intent):
            key = (intent.instrument_id, intent.side)
            self._pending[key] = self._pending.get(key, Decimal(0)) + intent.quantity
        self._outbox.append(intent)

    def pending_quantity(self, instrument_id: InstrumentId) -> Decimal:
        return sum(
            (q for (iid, _), q in self._pending.items() if iid == instrument_id),
            Decimal(0),
        )

    def is_open(self, intent: OrderIntent) -> bool:
        order_id = self._intent_orders.get(id(intent))
        if order_id is None:
            return any(queued is intent for queued in self._outbox)
        return order_id not in self._closed

    def intent_of(self, order_id: str | None) -> OrderIntent | None:
        return self._order_intents.get(order_id) if order_id is not None else None

    def cancel(self, intent: OrderIntent) -> None:
        for index, queued in enumerate(self._outbox):
            if queued is intent:  # not sent yet: withdraw it
                del self._outbox[index]
                self.release(intent)
                return
        order_id = self._intent_orders.get(id(intent))
        if (
            order_id is not None
            and order_id not in self._closed
            and order_id not in self._cancel_asked
        ):
            self._cancel_asked.add(order_id)
            self._cancels.append(order_id)

    # -- runner side ----------------------------------------------------------
    def note_order(self, order_id: str, intent: OrderIntent) -> None:
        """Record that the runner sent ``intent`` as ``order_id`` (enables ``cancel``)."""
        self._order_intents[order_id] = intent
        self._intent_orders[id(intent)] = order_id

    def note_closed(self, order_id: str) -> None:
        """Record that ``order_id`` finished (filled, rejected, cancelled or expired)."""
        self._closed.add(order_id)

    def drain_cancels(self) -> list[str]:
        """Return and clear the order ids the strategy asked to cancel, in request order."""
        ids, self._cancels = self._cancels, []
        return ids

    def set_now(self, ts: int) -> None:
        """Set the clock to the ``ts_init`` of the event about to be processed."""
        self._now = ts

    def add_instrument(self, instrument: Instrument) -> None:
        self._instruments[instrument.instrument_id] = instrument

    def drain_intents(self) -> list[OrderIntent]:
        """Return and clear submitted intents, in submission order."""
        intents, self._outbox = self._outbox, []
        return intents

    def apply_fill(self, fill: Trade) -> None:
        """Book a fill: position, cash (notional plus costs) and pending quantity.

        The notional is exact Decimal major-unit ``Money`` and costs are ``Money``.
        All-or-nothing, like the Rust ledger: a fill whose notional cannot be
        represented or whose costs are in another currency raises ``ValueError``
        and leaves the ledger untouched.
        """
        buy = _is_buy(fill.side)
        notional = Money.mul_qty(fill.quantity, fill.price, self.currency)
        if buy:
            cash = self._cash - (notional + fill.costs)
            signed = fill.quantity
        else:
            cash = self._cash + (notional - fill.costs)
            signed = -fill.quantity
        self._cash = cash
        self._positions[fill.instrument_id] = self.position(fill.instrument_id) + signed
        self._reduce_pending(fill.instrument_id, OrderSide.BUY if buy else OrderSide.SELL, fill.quantity)

    def release(self, intent: OrderIntent) -> None:
        """An intent was rejected or its order cancelled unfilled: it no longer counts as busy.

        An invalid intent never counted (see ``submit``), so releasing it is a no-op.
        """
        if not _is_valid(intent):
            return
        self._reduce_pending(intent.instrument_id, intent.side, intent.quantity)

    def _reduce_pending(
        self, instrument_id: InstrumentId, side: OrderSide, quantity: Decimal
    ) -> None:
        key = (instrument_id, side)
        left = self._pending.get(key, Decimal(0)) - quantity
        if left > _EPSILON:
            self._pending[key] = left
        else:
            self._pending.pop(key, None)
