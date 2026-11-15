# wheel surface (ex 0006): backtest simulators (mirrors tantra_examples/_kernel/testing public API)
# stand-in closure for tantra-examples gap 0006

"""Single-price ``"bar_close"`` execution: every order fills in full at the latest bar close.

:class:`BarCloseFills` is the simulated execution port of the conformance suite (mirrors
``honba_sim::BarFillEngine``): an order fills at the close of the latest
:class:`~tantra.bar.Bar` (``fill_ts = max(order ts, previous fill ts + 1)``). An order
submitted before any bar raises instead of filling at 0.0 (a known gap of the Rust engine,
ADR 006). Trailing stops rest and trigger off later bars' peaks/troughs.

Costs (ADR 008) default to none. With ``flat_cost`` (``0..=MAX_FLAT_COST``) and ``cost_bps``
(``0..=MAX_COST_BPS``) every fill carries ``Trade.costs`` = the flat leg plus
``(quantity * price) * cost_bps / 10_000``, **each leg rounded to minor units once before
summation** (ADR 0011), as ``Money`` in ``currency`` and not signed by side. Invalid values
raise :class:`FillCostsError`; a cost that cannot be represented raises ``ValueError``
instead of charging zero.

Decimal-canonical (rust_decimal parity): every price, quantity and cost is an exact
``decimal.Decimal`` (minor-unit rounding is ``ROUND_HALF_UP``, mirroring the Rust nearest
minor unit, half away from zero).
"""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from tantra.bar import Bar
from tantra.money import Currency, Money
from tantra.order import OrderIntent, OrderSide, OrderType
from tantra.trade import Trade
from tantra.types import to_decimal

__all__ = ["BarCloseFills"]

MAX_FLAT_COST = Decimal("1e9")
"""Largest accepted flat cost per fill (mirrors ``honba_sim::MAX_FLAT_COST``)."""

MAX_COST_BPS = Decimal("10_000")
"""Largest accepted proportional cost in bps of the fill notional (100%)."""


class FillCostsError(ValueError):
    """Invalid ``BarCloseFills`` cost parameter (not finite, negative or above its cap)."""


def _checked(name: str, value: Decimal, cap: Decimal) -> Decimal:
    d = to_decimal(value)
    if not (d.is_finite() and Decimal(0) <= d <= cap):
        raise FillCostsError(f"{name} must be finite and within 0..={cap}, got {value}")
    return d


class BarCloseFills:
    """Simulated execution: every order fills in full at the latest bar close.

    Fill time is ``max(order ts, previous fill ts + 1)``. This is the
    ``"bar_close"`` fill model of the conformance fixture and mirrors Rust's
    ``BarFillEngine``, except that an order before any bar raises instead of
    filling at 0.0 (a known gap of the Rust engine, ADR 006).

    Costs (ADR 008) default to none. With ``flat_cost`` (``0..=MAX_FLAT_COST``)
    and ``cost_bps`` (``0..=MAX_COST_BPS``) every fill carries ``Trade.costs`` =
    the flat leg plus ``(quantity * price) * cost_bps / 10_000``, **each leg rounded
    to minor units once before summation** (ADR 0011), as ``Money`` in ``currency``
    and not signed by side. Invalid values raise ``FillCostsError``; a cost that
    cannot be represented raises ``ValueError`` instead of charging zero.
    """

    def __init__(
        self,
        flat_cost: Decimal = Decimal(0),
        cost_bps: Decimal = Decimal(0),
        currency: Currency = Currency.INR,
    ) -> None:
        self._flat_cost = _checked("flat_cost", flat_cost, MAX_FLAT_COST)
        self._cost_bps = _checked("cost_bps", cost_bps, MAX_COST_BPS)
        self._currency = currency
        self._last_price: Decimal | None = None
        self._next_ts = 0
        self._fills: list[Trade] = []
        self._resting_trailing: list[tuple[str, OrderIntent, Decimal, Decimal]] = []

    def on_event(self, event: Any, ts_init: int) -> None:
        if isinstance(event, Bar):
            self._last_price = event.close
            remaining = []
            for order_id, intent, peak, trough in self._resting_trailing:
                if intent.instrument_id != event.instrument_id:
                    remaining.append((order_id, intent, peak, trough))
                    continue
                if intent.side is OrderSide.SELL:
                    peak = max(peak, event.high)
                    trigger = (
                        peak - intent.trail_amount
                        if intent.trail_amount is not None
                        else peak * (Decimal(1) - (intent.trail_percent or Decimal(0)) / Decimal(100))
                    )
                    if event.low <= trigger:
                        px = min(event.open, trigger) if event.open <= trigger else trigger
                        self._fill_order(order_id, intent, px, event.ts)
                    else:
                        remaining.append((order_id, intent, peak, trough))
                else:
                    trough = min(trough, event.low)
                    trigger = (
                        trough + intent.trail_amount
                        if intent.trail_amount is not None
                        else trough * (Decimal(1) + (intent.trail_percent or Decimal(0)) / Decimal(100))
                    )
                    if event.high >= trigger:
                        px = max(event.open, trigger) if event.open >= trigger else trigger
                        self._fill_order(order_id, intent, px, event.ts)
                    else:
                        remaining.append((order_id, intent, peak, trough))
            self._resting_trailing = remaining

    def submit(self, order_id: str, intent: OrderIntent, ts: int) -> None:
        if self._last_price is None:
            raise RuntimeError(f"order {order_id} submitted before any bar: no price to fill at")
        if intent.order_type is OrderType.TRAILING_STOP:
            self._resting_trailing.append((order_id, intent, self._last_price, self._last_price))
            return
        self._fill_order(order_id, intent, self._last_price, ts)

    def _fill_order(self, order_id: str, intent: OrderIntent, price: Decimal, ts: int) -> None:
        costs = self._costs(intent.quantity, price)
        fill_ts = max(self._next_ts, ts)
        self._next_ts = fill_ts + 1
        self._fills.append(
            Trade(
                intent.instrument_id,
                intent.side,
                intent.quantity,
                price,
                fill_ts,
                order_id,
                costs=costs,
            )
        )

    def _costs(self, quantity: Decimal, price: Decimal) -> Money:
        # Per leg, then sum (ADR 0011): the same rounding as Rust's FillCosts.
        quantum = Decimal(1) / Decimal(self._currency.minor_per_major)
        flat = self._flat_cost.quantize(quantum, rounding=ROUND_HALF_UP)
        bps = (quantity * price * self._cost_bps / Decimal(10_000)).quantize(
            quantum, rounding=ROUND_HALF_UP
        )
        return Money(flat + bps, self._currency)

    def drain_fills(self) -> list[Trade]:
        fills, self._fills = self._fills, []
        return fills
