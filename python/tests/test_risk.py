"""Tests for the compiled SEBI pre-trade risk gate (tantra.RiskEngine)."""
import pytest

from tantra import _tantra

TS = "2026-11-05T09:30:00+05:30"
SYMBOL = "NSE:RELIANCE"


def make_order(algo_id="algo-1"):
    iid = _tantra.InstrumentId.from_str(SYMBOL)
    return _tantra.OrderRequest(
        iid, _tantra.OrderSide("BUY"), "LIMIT", "10", algo_id,
        limit_price="2450.00",
    )


def test_register_then_check_passes():
    engine = _tantra.RiskEngine()
    engine.register_algo("algo-1")
    assert engine.is_algo_registered("algo-1")
    engine.check_order(make_order(), TS)  # must not raise


def test_unregistered_algo_refused():
    engine = _tantra.RiskEngine()
    with pytest.raises(_tantra.RiskRefused):
        engine.check_order(make_order(), TS)


def test_global_halt_blocks_orders():
    engine = _tantra.RiskEngine()
    engine.register_algo("algo-1")
    engine.halt_global("test halt", TS)
    assert engine.is_halted()
    assert engine.global_state() == "HALTED"
    with pytest.raises(_tantra.RiskRefused):
        engine.check_order(make_order(), TS)
    engine.resume_global()
    assert not engine.is_halted()
    engine.check_order(make_order(), TS)


def test_price_band_enforced():
    engine = _tantra.RiskEngine()
    engine.register_algo("algo-1")
    iid = _tantra.InstrumentId.from_str(SYMBOL)
    engine.set_price_band(iid, "2400", "2500", "2450")
    engine.check_order_fast("algo-1", iid, _tantra.OrderSide("BUY"), "10", "2450.00", TS)
    with pytest.raises(_tantra.RiskRefused):
        engine.check_order_fast(
            "algo-1", iid, _tantra.OrderSide("BUY"), "10", "2550.00", TS
        )


def test_reduce_only_refuses_buy_allows_sell():
    engine = _tantra.RiskEngine()
    engine.register_algo("algo-1")
    iid = _tantra.InstrumentId.from_str(SYMBOL)
    engine.set_reduce_only()
    assert engine.global_state() == "REDUCE_ONLY"
    with pytest.raises(_tantra.RiskRefused):
        engine.check_order_fast(
            "algo-1", iid, _tantra.OrderSide("BUY"), "10", None, TS
        )
    engine.check_order_fast(
        "algo-1", iid, _tantra.OrderSide("SELL"), "10", None, TS
    )
    engine.resume_global()
    engine.check_order_fast(
        "algo-1", iid, _tantra.OrderSide("BUY"), "10", None, TS
    )


def test_check_decision_hold_passes():
    engine = _tantra.RiskEngine()
    engine.register_algo("algo-1")
    engine.check_decision('{"action":"hold","reason":"x"}', TS)


def test_total_refusals_counted():
    engine = _tantra.RiskEngine()
    for _ in range(3):
        with pytest.raises(_tantra.RiskRefused):
            engine.check_order(make_order(), TS)
    assert engine.total_refusals() == 3
