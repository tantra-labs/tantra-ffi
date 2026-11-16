"""L2 native vs python parity on the coincident tape (plan 0003, D2).

Full-tape parity between the old top-of-book reference and the paper-exchange
engine is NOT asserted: they are different matching models (one matches quotes,
the other the resting order book). The canonical cross-language parity oracle is
the golden paper tape (``python/tests/golden/paper_golden.json``), which P4
re-verifies across all embeddings. Here we assert parity on the *coincident*
tape: a resting limit then a full-size market order crossing the touch.
"""

from __future__ import annotations

from decimal import Decimal

from tantra.backtest.l2_sim import L2Execution
from tantra.execution import Fill
from tantra.instrument import InstrumentId
from tantra.money import Currency, Money
from tantra.order import OrderIntent, OrderSide, OrderType
from tantra.tick import AggressorSide, QuoteTick, TradeTick

RELIANCE = InstrumentId("RELIANCE", "NSE")
TS = 1_700_000_000_000_000_000


def _quote(ts: int = TS):
    return QuoteTick(
        RELIANCE, ts, Decimal(100), Decimal(101), Decimal(100), Decimal(100)
    )


def _trade(ts: int):
    return TradeTick(
        RELIANCE,
        ts,
        Decimal(100),
        Decimal(10),
        AggressorSide.NO_AGGRESSOR,
        "t1",
    )


def _run(backend: str):
    """The coincident tape: LTP print, resting limit, full-size crossing market.

    ``long_only=False``: the market sell is a naked sell (no position held), and
    the native paper engine books naked sells (the golden tape's SELL with no
    position), so both backends agree on the tape.
    """
    port = L2Execution(
        cash=Money(Decimal(1_000_000), Currency.INR), long_only=False, backend=backend
    )
    port.on_quote(_quote())
    port.on_trade(_trade(TS))  # establish the LTP at 100
    port.submit(
        "o1",
        OrderIntent(
            RELIANCE, OrderSide.BUY, Decimal(10), OrderType.LIMIT, price=Decimal(100)
        ),
        TS,
    )
    port.submit(
        "o2",
        OrderIntent(RELIANCE, OrderSide.SELL, Decimal(10), OrderType.MARKET),
        TS,
    )
    port.on_trade(_trade(TS + 2))
    events = port.drain_events()
    fills = [
        (str(e.trade.side), e.trade.price, e.trade.quantity)
        for e in events
        if isinstance(e, Fill)
    ]
    return fills, port.cash


def test_coincident_tape_fill_parity():
    py_fills, py_cash = _run("python")
    native_fills, native_cash = _run("native")
    assert sorted(py_fills) == sorted(native_fills)
    assert len(native_fills) == 2
    assert py_cash == native_cash


def test_native_backend_resolves_and_runs():
    port = L2Execution(cash=Money(Decimal(1_000_000), Currency.INR), backend="native")
    assert port.backend == "native"
    assert port.cash == Money(Decimal(1_000_000), Currency.INR)
