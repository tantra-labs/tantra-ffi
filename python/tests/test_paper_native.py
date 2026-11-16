"""Native ``PaperExchange`` wheel surface (plan 0003, D1): the golden parity tape.

The golden oracle (``tantra-runtime`` E9, ``paper_parity_tests.rs``) is
re-verified here against the wheel embedding and also stored machine-readable in
``python/tests/golden/paper_golden.json`` (P4 cross-repo reuse).

Every price/quantity field is asserted to be an exact ``decimal.Decimal`` (the
Zero Floats Policy across the FFI boundary).
"""

from __future__ import annotations

import datetime
import json
from decimal import Decimal
from pathlib import Path

import pytest
from tantra._tantra import Bar, InstrumentId, OrderRequest, OrderSide, PaperExchange

GOLDEN = Path(__file__).parent / "golden" / "paper_golden.json"


def _ts(epoch: int) -> str:
    dt = datetime.datetime.fromtimestamp(epoch, tz=datetime.timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _limit_buy(instrument, qty, price):
    return OrderRequest(
        instrument,
        OrderSide("BUY"),
        "LIMIT",
        Decimal(qty),
        "paper",
        limit_price=Decimal(price),
    )


def _market_sell(instrument, qty):
    return OrderRequest(instrument, OrderSide("SELL"), "MARKET", Decimal(qty), "paper")


def test_limit_buy_fills_when_bar_crosses():
    ex = PaperExchange(Decimal(100000))
    inst = InstrumentId("NSE", "RELIANCE")
    ex.set_market_price(inst, Decimal(100))
    oid = ex.place_order(_limit_buy(inst, 10, 100), _ts(1_700_000_000))
    assert oid.startswith("PAPER-")
    # The bar seeds a synthetic depth print at its close, participation-capped
    # (half the bar volume), so volume 100 clears the 10-qty order fully.
    ex.feed_bar(
        Bar(
            inst,
            Decimal(100),
            Decimal(100),
            Decimal(95),
            Decimal(95),
            Decimal(100),
            _ts(1_700_000_001),
        )
    )
    fills = ex.fills()
    assert len(fills) == 1
    fill = fills[0]
    # The engine fills a resting limit the market trades through at the
    # *crossing* price (price improvement for the buyer), not the limit.
    assert fill.price == Decimal(95)
    assert fill.quantity == Decimal(10)
    assert str(fill.side) == "BUY"
    assert isinstance(fill.price, Decimal)
    assert isinstance(fill.quantity, Decimal)
    assert ex.order(oid)["state"] == "FILLED"


def test_golden_tape_matches_engine_oracle():
    tape = json.loads(GOLDEN.read_text())
    ex = PaperExchange(Decimal(tape["initial_cash"]))
    inst = InstrumentId("NSE", "RELIANCE")
    assert inst.to_str() == tape["instrument"]
    assert tape["ts0"] == _ts(1_700_000_000)
    ex.set_market_price(inst, Decimal(tape["market_price"]))

    o1 = ex.place_order(_limit_buy(inst, 100, 101), tape["ts0"])
    o2 = ex.place_order(_limit_buy(inst, 100, 100), tape["ts0"])
    o3 = ex.place_order(_market_sell(inst, 150), tape["ts0"])
    ex.advance_to("2023-11-14T22:13:21Z")

    fills = ex.fills()
    assert len(fills) == 4
    got = {(str(f.side), f.price, f.quantity) for f in fills}
    expected = {
        ("SELL", Decimal(101), Decimal(100)),
        ("BUY", Decimal(101), Decimal(100)),
        ("SELL", Decimal(100), Decimal(50)),
        ("BUY", Decimal(100), Decimal(50)),
    }
    assert got == expected
    for f in fills:
        assert isinstance(f.price, Decimal)
        assert isinstance(f.quantity, Decimal)

    assert ex.order(o1)["state"] == "FILLED"
    assert ex.order(o2)["state"] == "PARTIALLY_FILLED"
    o3_state = ex.order(o3)
    assert o3_state["state"] == "FILLED"
    assert o3_state["filled_qty"] == Decimal(150)
    assert o3_state["avg_fill_price"] == Decimal("100.6667")

    assert ex.cash() == Decimal(tape["expected"]["net_cash"])
    assert ex.equity() == Decimal(tape["expected"]["net_cash"])
    # Net position is zero; the engine keeps the flat entry in its map.
    assert ex.positions() == {tape["instrument"]: Decimal(0)}
    assert len(ex.events()) == tape["expected"]["event_count"]


def test_market_order_without_contra_liquidity_is_rejected():
    ex = PaperExchange(Decimal(100000))
    inst = InstrumentId("NSE", "RELIANCE")
    ex.set_market_price(inst, Decimal(100))
    with pytest.raises(Exception, match="market price"):
        ex.place_order(_market_sell(inst, 10), _ts(1_700_000_000))
