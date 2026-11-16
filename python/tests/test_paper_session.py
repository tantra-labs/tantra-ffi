"""``PaperSession`` facade (plan 0003, D2/D3): seeded determinism and strategy driving."""

from __future__ import annotations

from decimal import Decimal

from tantra.bar import Bar
from tantra.instrument import InstrumentId
from tantra.paper import PaperResult, PaperSession
from tantra.strategy import Strategy

RELIANCE = InstrumentId("RELIANCE", "NSE")


def _bars():
    return [
        Bar(
            RELIANCE,
            1_700_000_000_000_000_000,
            Decimal(100),
            Decimal(100),
            Decimal(95),
            Decimal(95),
            Decimal(1000),
        ),
        Bar(
            RELIANCE,
            1_700_000_001_000_000_000,
            Decimal(95),
            Decimal(95),
            Decimal(95),
            Decimal(95),
            Decimal(1000),
        ),
    ]


def _run(seed: int | None):
    session = PaperSession(cash=Decimal(1_000_000), seed=seed)
    session.set_market_price(RELIANCE, Decimal(100))
    session.place_order(
        RELIANCE, "BUY", Decimal(10), order_type="LIMIT", limit_price=Decimal(100)
    )
    session.place_order(RELIANCE, "SELL", Decimal(10), order_type="MARKET")
    session.advance_to("2023-11-14T22:14:00Z")
    return session


def test_seeded_session_is_deterministic():
    s1, s2 = _run(42), _run(42)
    fills1 = [(str(f.side), f.price, f.quantity) for f in s1.fills()]
    fills2 = [(str(f.side), f.price, f.quantity) for f in s2.fills()]
    assert fills1 == fills2
    assert len(fills1) >= 2  # the resting limit and the market order both fill
    assert s1.equity() == s2.equity()
    assert s1.cash() == s2.cash()
    assert s1.events() == s2.events()


class BuyOnBar(Strategy):
    def on_start(self):
        self.buy("NSE:RELIANCE", Decimal(10), limit_price=Decimal(100))


def test_run_drives_strategy_and_returns_fills():
    session = PaperSession(cash=Decimal(1_000_000))
    session.set_market_price(RELIANCE, Decimal(100))
    result = session.run(BuyOnBar(), _bars())
    assert isinstance(result, PaperResult)
    assert result.strategy_name == "BuyOnBar"
    assert len(result.fills) >= 1
    # The resting buy limit fills at the first bar's crossing close (95).
    assert result.fills[0].price == Decimal(95)
    assert result.fills[0].quantity == Decimal(10)
    assert result.equity_curve  # one entry per bar
