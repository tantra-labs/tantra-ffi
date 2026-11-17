"""L2 native vs python parity on the coincident + golden tapes (plan 0003, D2).

Full-tape parity between the old top-of-book reference and the paper-exchange
engine is NOT asserted: they are different matching models (one matches quotes,
the other the resting order book). The canonical cross-language parity oracle is
the golden paper tape (``python/tests/golden/paper_golden.json``), which P4
re-verifies across all embeddings. Here we assert parity on the two tapes where
the models coincide:

* the *coincident* tape: a resting limit then a full-size market order crossing
  the touch, and
* the *golden* tape: the T14.14 golden economics expressed as a touch-size-full
  crossing, reproduced by the native backend (plan 0003 follow-on).
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


def _golden_quote_start(ts: int = TS):
    # Bid 101 (size 100) / ask 102: neither buy is marketable (ask above both
    # limits) while the sell market's first leg crosses the 101 bid.
    return QuoteTick(
        RELIANCE, ts, Decimal(101), Decimal(102), Decimal(100), Decimal(100)
    )


def _golden_quote_cross(ts: int):
    # Bid 100 (size 50) / ask 101 (size 100): the sell remainder crosses the 100
    # bid and the resting 101 buy becomes marketable at the 101 ask.
    return QuoteTick(
        RELIANCE, ts, Decimal(100), Decimal(101), Decimal(50), Decimal(100)
    )


def _golden_print(ts: int, price: Decimal, size: Decimal):
    return TradeTick(
        RELIANCE,
        ts,
        price,
        size,
        AggressorSide.NO_AGGRESSOR,
        f"g{ts}",
    )


def _golden_run(backend: str):
    """The T14.14 golden paper tape as a tick tape BOTH backends reproduce.

    Golden economics (``paper_golden.json``): market 100, BUY 100@101,
    BUY 100@100, SELL MARKET 150 -> 4 fills (sell 100@101, buy 100@101, sell
    50@100, buy 50@100), sell avg ``100.6667``, net position 0, cash back to
    1_000_000.

    Tape mechanics (a touch-size-full crossing so the top-of-book reference and
    the paper order book coincide):

    * the LTP print that establishes the market prints at 102, above the resting
      101 buy -- a print at 100 would be marketable liquidity the paper engine
      price-improves the buy against, consuming 10@100 and breaking the crossing;
    * the golden's 100@100 buy is expressed as its 50@100 consumed leg, because a
      print *at* the 100 limit would double-count the paper engine's partial fill
      of that order;
    * the sell market 150 crosses exactly the resting depth (100@101 + 50@100),
      so neither backend is left with a remainder.
    """
    port = L2Execution(
        cash=Money(Decimal(1_000_000), Currency.INR), long_only=False, backend=backend
    )
    port.on_quote(_golden_quote_start(TS))
    port.on_trade(_golden_print(TS + 1, Decimal(102), Decimal(10)))
    port.submit(
        "o1",
        OrderIntent(
            RELIANCE, OrderSide.BUY, Decimal(100), OrderType.LIMIT, price=Decimal(101)
        ),
        TS + 2,
    )
    port.submit(
        "o2",
        OrderIntent(
            RELIANCE, OrderSide.BUY, Decimal(50), OrderType.LIMIT, price=Decimal(100)
        ),
        TS + 3,
    )
    port.submit(
        "o3",
        OrderIntent(RELIANCE, OrderSide.SELL, Decimal(150), OrderType.MARKET),
        TS + 4,
    )
    # The crossing: the sell remainder takes the 100 bid, the 101 buy takes the
    # 101 ask, and the 100 buy fills on the print at its limit.
    port.on_quote(_golden_quote_cross(TS + 5))
    port.on_trade(_golden_print(TS + 6, Decimal(100), Decimal(50)))
    events = port.drain_events()
    fills = [
        (str(e.trade.side).rsplit(".", 1)[-1], e.trade.price, e.trade.quantity)
        for e in events
        if isinstance(e, Fill)
    ]
    return fills, port.cash, port.positions


GOLDEN_FILLS = [
    ("BUY", Decimal(100), Decimal(50)),
    ("BUY", Decimal(101), Decimal(100)),
    ("SELL", Decimal(100), Decimal(50)),
    ("SELL", Decimal(101), Decimal(100)),
]


def test_golden_tape_parity_through_native_backend():
    py_fills, py_cash, py_positions = _golden_run("python")
    native_fills, native_cash, native_positions = _golden_run("native")

    # Both matching models reproduce the golden tape (reference == native).
    assert sorted(py_fills) == sorted(native_fills)
    assert py_cash == native_cash

    # The native backend reproduces the golden fill prices/quantities and the
    # golden cash()/net result (cash back to 1_000_000, net position 0).
    assert sorted(native_fills) == GOLDEN_FILLS
    assert native_cash == Money(Decimal(1_000_000), Currency.INR)
    assert sum(py_positions.values()) == Decimal(0)
    assert sum(native_positions.values()) == Decimal(0)

    # Golden sell economics: qty 150, notional 15_100, avg 100.6667.
    sell_fills = [(p, q) for side, p, q in native_fills if side == "SELL"]
    sell_notional = sum(p * q for p, q in sell_fills)
    sell_qty = sum(q for _, q in sell_fills)
    assert sell_qty == Decimal(150)
    assert sell_notional == Decimal(15100)
    assert (sell_notional / sell_qty).quantize(Decimal("0.0001")) == Decimal("100.6667")
