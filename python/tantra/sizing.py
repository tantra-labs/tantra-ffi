"""Exact-decimal position sizing helpers.

All arithmetic is ``decimal.Decimal`` (no floats) and quantities are rounded
down so a sizing calculation never risks over-allocating capital.
"""
# stand-in closure for tantra-examples gap 0005
from decimal import Decimal, ROUND_DOWN

from tantra.types import to_decimal


def fixed_quantity(quantity) -> Decimal:
    """Return ``quantity`` as an exact ``Decimal``."""
    return to_decimal(quantity)


def fractional(equity, risk_pct, entry_price) -> Decimal:
    """Quantity for risking ``risk_pct`` of ``equity`` at ``entry_price``.

    ``qty = (equity * risk_pct) / entry_price`` rounded down to 2 decimals.
    """
    equity = to_decimal(equity)
    risk_pct = to_decimal(risk_pct)
    entry_price = to_decimal(entry_price)
    if equity <= 0 or risk_pct <= 0 or entry_price <= 0:
        raise ValueError("equity, risk_pct, and entry_price must all be positive")
    qty = (equity * risk_pct) / entry_price
    return qty.quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def risk_budget(equity, max_risk_pct, entry_price, stop_price) -> Decimal:
    """Maximum quantity given a per-trade risk budget.

    ``qty = floor(equity * max_risk_pct / |entry_price - stop_price|)``.
    """
    equity = to_decimal(equity)
    max_risk_pct = to_decimal(max_risk_pct)
    entry_price = to_decimal(entry_price)
    stop_price = to_decimal(stop_price)
    risk_per_unit = abs(entry_price - stop_price)
    if equity <= 0 or max_risk_pct <= 0 or entry_price <= 0 or stop_price <= 0:
        raise ValueError("equity, max_risk_pct, entry_price, and stop_price must all be positive")
    if risk_per_unit == 0:
        raise ValueError("entry_price must differ from stop_price")
    qty = (equity * max_risk_pct) / risk_per_unit
    return qty.to_integral_value(rounding=ROUND_DOWN)


OPTION_FREEZE_LIMIT_DEFAULT = 1800
"""SEBI single-order freeze quantity for NIFTY options.

Set by SEBI and revised by circular; read from the instrument master when a
client surface ships (cite: ffi kernel-surface gap; never hard-coded in a
strategy).
"""


def freeze_limit_qty(symbol: str = "NIFTY", exchange: str = "NSE") -> int:
    """The SEBI single-order freeze quantity for ``symbol`` (options, default 1800).

    The wheel ships no instrument-master client yet; the master-read path is the
    future ``tantra.client.get_instrument`` surface. Until then this returns the
    pinned default constant.
    """
    return OPTION_FREEZE_LIMIT_DEFAULT


def slice_order(total_quantity: int, freeze_limit_qty: int) -> list[int]:
    """Split ``total_quantity`` into whole slices of exactly the freeze limit,
    then one remainder slice (if any).

    Raises ``ValueError`` when either argument is not positive.
    """
    if total_quantity <= 0:
        raise ValueError(f"total_quantity must be > 0, got {total_quantity}")
    if freeze_limit_qty <= 0:
        raise ValueError(f"freeze_limit_qty must be > 0, got {freeze_limit_qty}")
    whole, remainder = divmod(total_quantity, freeze_limit_qty)
    slices = [freeze_limit_qty] * whole
    if remainder:
        slices.append(remainder)
    return slices


def verify_slices(slices: list[int], freeze_limit_qty: int) -> None:
    """Raise ``ValueError`` naming the offending slice index when any slice
    exceeds the freeze limit.
    """
    if freeze_limit_qty <= 0:
        raise ValueError(f"freeze_limit_qty must be > 0, got {freeze_limit_qty}")
    for index, quantity in enumerate(slices):
        if quantity > freeze_limit_qty:
            raise ValueError(
                f"slice {index} exceeds freeze limit {freeze_limit_qty}: {quantity}"
            )


class Sizer:
    """Namespace exposing the sizing helpers as static methods."""

    fixed_quantity = staticmethod(fixed_quantity)
    fractional = staticmethod(fractional)
    risk_budget = staticmethod(risk_budget)
    slice_order = staticmethod(slice_order)
    verify_slices = staticmethod(verify_slices)
    freeze_limit_qty = staticmethod(freeze_limit_qty)
