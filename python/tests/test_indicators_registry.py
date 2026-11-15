# wheel surface (ex 0006): Decimal-canonical indicators registry tests
# stand-in closure for tantra-examples gap 0006

"""Tests for the Decimal-canonical indicator registry core and moving_average family."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tantra import EMA, RSI, SMA
from tantra.bar import Bar
from tantra.indicators import (
    FAMILIES,
    Adx,
    Aroon,
    Cci,
    Ema,
    Ichimoku,
    IndicatorBank,
    Kdj,
    Macd,
    MacdValue,
    Rma,
    Roc,
    Rsi,
    Sma,
    Stochastic,
    Supertrend,
    Wma,
    build_indicator,
    indicator_family,
    indicator_spec,
    list_indicators,
    make_ma,
)
from tantra.indicators._base import indicator
from tantra.indicators.moving_average import Hma, Vwma
from tantra.indicators.trend.adx import AdxValue
from tantra.indicators.trend.aroon import AroonValue
from tantra.indicators.trend.supertrend import SupertrendValue
from tantra.indicators.momentum.stochastic import StochasticValue
from tantra.instrument import InstrumentId

_ALL_FAMILIES = {
    "moving_average",
    "trend",
    "momentum",
    "volatility",
    "volume",
    "support_resistance",
    "breadth",
    "statistical",
}


def _bar(close: str, ts: int = 1) -> Bar:
    """Minimal wheel ``Bar`` with the given close and volume 10."""
    c = Decimal(close)
    high = max(c, Decimal("10"))
    low = min(c, Decimal("10"))
    return Bar(
        InstrumentId("RELIANCE"),
        ts,
        open="10",
        high=str(high),
        low=str(low),
        close=close,
        volume="10",
    )


# --- registry mechanics --------------------------------------------------


def test_families_include_all_eight() -> None:
    assert set(FAMILIES) == _ALL_FAMILIES


def test_build_indicator_returns_ema() -> None:
    ind = build_indicator("ema", period=20)
    assert isinstance(ind, Ema)
    assert ind.period == 20


def test_build_indicator_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        build_indicator("bogus")


def test_list_indicators_sorted_and_includes_ema() -> None:
    kinds = list_indicators()
    assert kinds == sorted(kinds)
    assert "ema" in kinds
    assert "sma" in kinds


def test_list_indicators_moving_average_subset() -> None:
    ma = set(list_indicators("moving_average"))
    assert ma <= set(list_indicators())
    assert "ema" in ma


def test_list_indicators_unknown_family_raises() -> None:
    with pytest.raises(ValueError):
        list_indicators("bogus")


def test_indicator_family_ema() -> None:
    assert indicator_family("ema") == "moving_average"


def test_indicator_spec_sma_shape() -> None:
    spec = indicator_spec("sma")
    assert spec["kind"] == "sma"
    assert spec["family"] == "moving_average"
    assert spec["inputs"] == ["close"]
    assert spec["outputs"] == ["value"]
    assert spec["params"]
    assert {"name", "default", "type"} <= set(spec["params"][0])
    assert isinstance(spec["summary"], str)
    assert indicator_spec("ema")["summary"]  # Ema has a docstring -> non-empty summary


def test_duplicate_kind_registration_raises() -> None:
    with pytest.raises(ValueError):
        @indicator("ema", "moving_average")
        class _Duplicate:  # type: ignore[no-redef]
            ...


# --- warmup semantics ----------------------------------------------------


def test_sma_warmup_returns_none_then_decimal() -> None:
    s = Sma(3)
    assert s.update("10") is None
    assert s.update("20") is None
    assert s.update("30") == Decimal("20")
    assert isinstance(s.update("40"), Decimal)


# --- numeric sanity (Decimal, exact) -------------------------------------


def test_sma_exact_mean() -> None:
    s = Sma(3)
    s.update("10")
    s.update("20")
    assert s.update("30") == Decimal("20")


def test_ema_seed_first() -> None:
    e = Ema(3, seed="first")
    assert e.update("10") == Decimal("10")
    assert e.update("20") == Decimal("15")  # 20*0.5 + 10*0.5
    assert e.update("30") == Decimal("22.5")


def test_ema_seed_sma_warms_after_period() -> None:
    e = Ema(3)  # seed="sma" (TA-Lib default)
    assert e.update("10") is None
    assert e.update("20") is None
    assert e.update("30") == Decimal("20")


def test_wma_weights_newest_heaviest() -> None:
    w = Wma(3)
    assert w.update("10") is None
    assert w.update("20") is None
    assert w.update("30") == Decimal(140) / Decimal(6)  # (1*10 + 2*20 + 3*30) / 6


def test_rma_seeds_as_sma() -> None:
    r = Rma(3)
    assert r.update("10") is None
    assert r.update("20") is None
    assert r.update("30") == Decimal("20")  # SMA seed over 10,20,30
    assert r.update("40") == Decimal(80) / Decimal(3)  # (20*2 + 40) / 3


def test_make_ma_kinds() -> None:
    assert isinstance(make_ma("sma", 5), Sma)
    assert isinstance(make_ma("ema", 5), Ema)
    assert isinstance(make_ma("rma", 5), Rma)
    assert isinstance(make_ma("wma", 5), Wma)
    with pytest.raises(ValueError):
        make_ma("bogus", 5)


# --- update_bar with wheel Bar ------------------------------------------


def test_sma_update_bar() -> None:
    s = Sma(3)
    assert s.update_bar(_bar("10", 1)) is None
    assert s.update_bar(_bar("20", 2)) is None
    assert s.update_bar(_bar("30", 3)) == Decimal("20")


def test_ema_update_bar() -> None:
    e = Ema(3)
    assert e.update_bar(_bar("10", 1)) is None
    assert e.update_bar(_bar("20", 2)) is None
    assert e.update_bar(_bar("30", 3)) == Decimal("20")


def test_vwma_update_bar() -> None:
    v = Vwma(2)
    assert v.update_bar(_bar("10", 1)) is None
    assert v.update_bar(_bar("20", 2)) == Decimal("15")  # (10*10 + 20*10) / 20


# --- flat access ---------------------------------------------------------


def test_flat_access_resolves_registered_classes() -> None:
    import tantra.indicators as indicators_module

    assert indicators_module.Sma is Sma  # explicit export
    assert indicators_module.Hma is Hma  # resolved via module __getattr__
    assert indicators_module.Vwma is Vwma  # resolved via module __getattr__
    with pytest.raises(AttributeError):
        indicators_module.NoSuchIndicator  # type: ignore[attr-defined]


# --- IndicatorBank -------------------------------------------------------


def test_indicator_bank_computes() -> None:
    bank = IndicatorBank({"fast": {"kind": "ema", "period": 3}})
    assert bank.names == ["fast"]
    assert not bank.ready
    assert bank.update(_bar("10", 1)) == {"fast": None}
    assert bank.update(_bar("20", 2)) == {"fast": None}
    assert not bank.ready
    assert bank.update(_bar("30", 3)) == {"fast": Decimal("20")}
    assert bank.ready
    assert bank["fast"] == Decimal("20")


def test_indicator_bank_missing_kind_raises() -> None:
    with pytest.raises(ValueError):
        IndicatorBank({"x": {"period": 3}})


def test_indicator_bank_reset() -> None:
    bank = IndicatorBank({"s": {"kind": "sma", "period": 2}})
    bank.update(_bar("10", 1))
    bank.update(_bar("20", 2))
    assert bank.ready
    bank.reset()
    assert not bank.ready
    assert bank.update(_bar("30", 3)) == {"s": None}


# --- legacy aliases preserved --------------------------------------------


def test_legacy_aliases_preserved() -> None:
    import tantra

    assert tantra.indicators.SMA is SMA
    assert tantra.indicators.EMA is EMA
    assert tantra.indicators.RSI is RSI
    sma = SMA(3)
    assert sma.value() is None
    first = sma.add("10")
    assert isinstance(first, Decimal)  # Decimal, mean over the full period
    assert first == Decimal("10") / Decimal("3")
    sma.add("20")
    sma.add("30")
    assert sma.value() == Decimal("20")
    assert sma.add("40") == Decimal("30")
    ema = EMA(3)
    assert ema.add("10") == Decimal("10")
    assert ema.add("20") == Decimal("15")
    rsi = RSI(3)
    rsi.add("10")
    rsi.add("20")
    rsi.add("30")
    assert rsi.add("40") == Decimal("100")  # gains only -> RSI 100


def test_tantra_indicators_import_line() -> None:
    from tantra.indicators import EMA, RSI, SMA  # noqa: F401  (import line must keep working)

    assert callable(SMA)
    assert callable(EMA)
    assert callable(RSI)


# --- trend family (ex 0006) ---------------------------------------------


def test_list_indicators_trend_and_momentum_subset() -> None:
    all_kinds = set(list_indicators())
    for family in ("trend", "momentum"):
        kinds = set(list_indicators(family))
        assert kinds
        assert kinds <= all_kinds
    assert {"adx", "chande_kroll_stop", "ichimoku", "macd", "supertrend", "vortex"} <= set(
        list_indicators("trend")
    )
    assert {"cci", "kdj", "roc", "rsi", "stochastic", "williams_r"} <= set(
        list_indicators("momentum")
    )


def test_build_indicator_macd() -> None:
    m = build_indicator("macd", fast=12, slow=26, signal=9)
    assert isinstance(m, Macd)
    assert m.warmup == 26 + 9 - 1  # slow EMA seed + signal EMA seed - 1
    with pytest.raises(ValueError):
        build_indicator("macd", fast=30, slow=10)  # fast must be < slow


def test_indicator_family_rsi_is_momentum() -> None:
    assert indicator_family("rsi") == "momentum"
    assert indicator_family("macd") == "trend"


def test_flat_access_trend_momentum() -> None:
    import tantra.indicators as indicators_module

    assert indicators_module.Adx is Adx
    assert indicators_module.Kdj is Kdj
    assert indicators_module.Rsi is Rsi
    assert indicators_module.Ichimoku is Ichimoku
    assert indicators_module.Macd is Macd
    assert indicators_module.MacdValue is MacdValue


# --- trend/momentum numeric sanity (Decimal, exact) ---------------------


def test_rsi_none_until_warm_then_decimal() -> None:
    r = Rsi(3)
    assert r.warmup == 4  # period + 1
    assert r.update("10") is None
    assert r.update("20") is None
    assert r.update("30") is None
    v = r.update("40")
    assert isinstance(v, Decimal)
    assert v == Decimal("100")  # gains only
    assert r.value == Decimal("100")


def test_rsi_mixed_series_exact() -> None:
    r = Rsi(2)
    assert r.update("10") is None
    assert r.update("20") is None
    assert r.update("30") == Decimal("100")
    v = r.update("10")
    assert isinstance(v, Decimal)
    assert v == Decimal("100") - Decimal("100") / Decimal("1.5")  # avg_gain 5, avg_loss 10


def test_macd_consumes_ema_cross_family() -> None:
    m = Macd(2, 3, 2)  # Ema(fast), Ema(slow), Ema(signal) all from moving_average
    assert m.update("10") is None
    assert m.update("20") is None
    assert m.update("30") is None
    v = m.update("40")
    assert isinstance(v, MacdValue)
    assert isinstance(v.macd, Decimal)
    assert isinstance(v.signal, Decimal)
    assert isinstance(v.histogram, Decimal)
    assert v.macd == Decimal("5")
    assert v.signal == Decimal("5")
    assert v.histogram == Decimal("0")


def test_adx_none_until_warmed_then_adxvalue() -> None:
    a = Adx(3, 2)
    assert a.warmup == 5  # di_length + adx_smoothing
    # TR stays 4 and +DM stays 2, so the RMA seed and Wilder steps stay exact.
    assert a.update("10", "6", "9") is None
    assert a.update("12", "8", "11") is None
    assert a.update("14", "10", "13") is None
    assert a.update("16", "12", "15") is None
    v = a.update("18", "14", "17")
    assert isinstance(v, AdxValue)
    assert isinstance(v.adx, Decimal)
    assert isinstance(v.plus_di, Decimal)
    assert isinstance(v.minus_di, Decimal)
    assert v.adx == Decimal("100")
    assert v.plus_di == Decimal("50")  # 100 * RMA(+DM) / RMA(TR) = 100 * 2 / 4
    assert v.minus_di == Decimal("0")


def test_aroon_warm_then_value() -> None:
    a = Aroon(3)
    assert a.update("10", "5") is None
    assert a.update("20", "6") is None
    assert a.update("30", "7") is None
    v = a.update("40", "8")
    assert isinstance(v, AroonValue)
    assert v.up == Decimal("100")
    assert v.down == Decimal("0")
    assert v.oscillator == Decimal("100")


def test_stochastic_warm_then_value() -> None:
    s = Stochastic(3, 1, 2)
    assert s.update("10", "8", "9") is None
    assert s.update("20", "9", "15") is None
    v = s.update("30", "10", "25")
    assert v is None  # %D still warming
    v = s.update("40", "11", "35")
    assert isinstance(v, StochasticValue)
    assert isinstance(v.k, Decimal)
    assert v.k == Decimal("2600") / Decimal("31")
    assert v.d == (Decimal("850") / Decimal("11") + Decimal("2600") / Decimal("31")) / 2


def test_kdj_tuple_output() -> None:
    k = Kdj(3, 1, 1)
    assert k.update("10", "8", "9") is None
    assert k.update("20", "9", "15") is None
    kk, dd, jj = k.update("30", "10", "25")
    assert isinstance(kk, Decimal)
    assert kk == dd == Decimal("850") / Decimal("11")
    assert jj == 3 * kk - 2 * dd  # J = 3K - 2D (rounds at context precision)


def test_cci_warm_then_decimal() -> None:
    c = Cci(2)
    assert c.update("10", "10", "10") is None
    v = c.update("20", "20", "20")
    assert isinstance(v, Decimal)
    assert v == Decimal("5") / Decimal("0.075")


def test_roc_warm_then_decimal() -> None:
    r = Roc(2)
    assert r.update("10") is None
    assert r.update("20") is None
    v = r.update("30")
    assert isinstance(v, Decimal)
    assert v == Decimal("200")


def test_supertrend_uses_wilder_atr_standin() -> None:
    st = Supertrend(3, Decimal("2"))
    assert st.update("12", "10", "11") is None
    assert st.update("14", "11", "13") is None
    v = st.update("16", "12", "15")
    assert isinstance(v, SupertrendValue)
    assert isinstance(v.value, Decimal)
    assert isinstance(v.direction, Decimal)
    assert v.value == Decimal("20")  # upper band: hl2 14 + 2 * ATR 3
    assert v.direction == Decimal("-1")  # starts in a downtrend (TradingView convention)

