"""Fill wire projection for the paper exchange (plan 0003, D2).

``fills_wire`` maps a session's :class:`~tantra._tantra.FillReport` list to the
REST ``FillReport`` wire shape -- the core ``FillReport`` fields: ``fill_id``,
``order_id``, ``client_order_id``, ``instrument``, ``side``, ``price``,
``quantity``, ``algo_id``, ``timestamp``, ``fee``. The paper engine prices with
zero costs by default, so ``fee`` is always ``"0"``; prices and quantities are
exact decimal strings (rust_decimal parity).
"""

from __future__ import annotations

__all__ = ["fills_wire"]


def fills_wire(session) -> list[dict]:
    """The session's fills as REST ``FillReport`` wire dicts (serde-identical keys)."""
    return [_fill_wire(fill) for fill in session.fills()]


def _fill_wire(fill) -> dict:
    return {
        "fill_id": fill.fill_id,
        "order_id": fill.order_id,
        "client_order_id": fill.client_order_id,
        "instrument": fill.instrument.to_str(),
        "side": str(fill.side),
        "price": str(fill.price),
        "quantity": str(fill.quantity),
        "algo_id": fill.algo_id,
        "timestamp": fill.timestamp,
        "fee": "0",
    }
