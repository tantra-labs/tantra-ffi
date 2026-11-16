"""Fill wire projection (plan 0003, D2): serde-identical REST ``FillReport`` shape."""

from __future__ import annotations

from decimal import Decimal

from tantra.paper import PaperSession
from tantra.paper.wire import fills_wire

WIRE_FIELDS = {
    "fill_id",
    "order_id",
    "client_order_id",
    "instrument",
    "side",
    "price",
    "quantity",
    "algo_id",
    "timestamp",
    "fee",
}


def _session_with_fills() -> PaperSession:
    session = PaperSession(cash=Decimal(1_000_000))
    session.set_market_price("NSE:RELIANCE", Decimal(100))
    session.place_order(
        "NSE:RELIANCE", "BUY", Decimal(10), order_type="LIMIT", limit_price=Decimal(100)
    )
    session.place_order("NSE:RELIANCE", "SELL", Decimal(10), order_type="MARKET")
    session.advance_to("2023-11-14T22:13:30Z")
    return session


def test_fills_wire_matches_rest_shape():
    wire = fills_wire(_session_with_fills())
    assert len(wire) >= 1
    assert set(wire[0]) == WIRE_FIELDS
    for entry in wire:
        assert entry["side"] in ("BUY", "SELL")
        assert entry["instrument"] == "NSE:RELIANCE"
        assert isinstance(entry["price"], str)
        assert isinstance(entry["quantity"], str)
        assert entry["fee"] == "0"
        assert entry["algo_id"] == "paper"
