"""Good-till-date (GTD) orders through the paper facade (plan 0003 follow-on).

The engine (``tantra-exec-paper``) already ships ``submit_order_gtd``; this test
pins the wheel facade: ``PaperSession.place_order(..., gtd_until=)`` sets the
order's expiry and ``advance_to`` at/past that instant expires it (state
``CANCELLED`` plus a ``cancelled`` event). The same order without GTD keeps
working past the same instant. Prices/quantities stay exact ``decimal.Decimal``
(Zero Floats Policy).
"""

from __future__ import annotations

from decimal import Decimal

from tantra.instrument import InstrumentId
from tantra.paper import PaperSession

RELIANCE = InstrumentId("RELIANCE", "NSE")

_TS0 = "2023-11-14T22:13:20Z"
_GDT_INSTANT = "2023-11-14T22:13:30Z"
_BEFORE_GDT = "2023-11-14T22:13:29Z"
_AFTER_GDT = "2023-11-14T22:13:31Z"


def _working_buy_limit(session: PaperSession, gtd_until: str | None) -> str:
    # Market at 105 > the 100 limit: the buy rests (no fill), so expiry is
    # observable without the market interfering.
    session.set_market_price(RELIANCE, Decimal(105))
    return session.place_order(
        RELIANCE,
        "BUY",
        Decimal(100),
        order_type="LIMIT",
        limit_price=Decimal(100),
        tif="DAY",
        ts_iso=_TS0,
        gtd_until=gtd_until,
    )


def test_gtd_order_cancels_when_expired():
    session = PaperSession(cash=Decimal(1_000_000))
    broker_id = _working_buy_limit(session, gtd_until=_GDT_INSTANT)

    order = session.order(broker_id)
    assert order["state"] == "WORKING"
    assert order["original_qty"] == Decimal(100)
    assert order["filled_qty"] == Decimal(0)

    # Just before the GTD instant the order still works.
    session.advance_to(_BEFORE_GDT)
    assert session.order(broker_id)["state"] == "WORKING"

    # At/past the GTD instant the engine expires the order.
    session.advance_to(_AFTER_GDT)
    order = session.order(broker_id)
    assert order["state"] == "CANCELLED"
    assert order["remaining_qty"] == Decimal(100)
    kinds = [ev["kind"] for ev in session.events()]
    assert "cancelled" in kinds


def test_order_without_gtd_stays_working_past_the_same_instant():
    session = PaperSession(cash=Decimal(1_000_000))
    broker_id = _working_buy_limit(session, gtd_until=None)

    session.advance_to(_AFTER_GDT)
    order = session.order(broker_id)
    assert order["state"] == "WORKING"
    assert order["filled_qty"] == Decimal(0)
    assert "cancelled" not in [ev["kind"] for ev in session.events()]
