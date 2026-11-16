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
    Atr,
    Bollinger,
    BollingerValue,
    Cci,
    Donchian,
    DonchianValue,
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
    Vwap,
    Wma,
    build_indicator,
    indicator_family,
    indicator_spec,
    list_indicators,
    make_ma,
)
from tantra.indicators._base import indicator
from tantra.indicators._rolling import RollingMoments, RollingPairMoments
from tantra.indicators.moving_average import Hma, Vwma
from tantra.indicators.breadth import (
    AdvanceDeclineLine,
    McClellanOscillator,
    PutCallRatio,
    Trin,
    UpDownVolumeRatio,
)
from tantra.indicators.statistical import (
    Beta,
    Correlation,
    Covariance,
    HurstExponent,
    ZScore,
)
from tantra.indicators.support_resistance import (
    FibonacciRetracement,
    FibonacciRetracementValue,
    PivotPoints,
    PivotPointsValue,
    WilliamsFractals,
    WilliamsFractalsValue,
)
from tantra.indicators.trend.adx import AdxValue
from tantra.indicators.trend.aroon import AroonValue
from tantra.indicators.trend.supertrend import SupertrendValue
from tantra.indicators.momentum.stochastic import StochasticValue
from tantra.indicators.volume.chaikin_money_flow import ChaikinMoneyFlow
from tantra.indicators.volume.money_flow_index import MoneyFlowIndex
from tantra.indicators.volume.obv import Obv
from tantra.indicators.volume.vwap import VwapValue
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


# --- volatility/volume families (ex 0006) ---------------------------------


def test_list_indicators_volatility_and_volume_subset() -> None:
    all_kinds = set(list_indicators())
    for family in ("volatility", "volume"):
        kinds = set(list_indicators(family))
        assert kinds
        assert kinds <= all_kinds
    assert {
        "atr",
        "bollinger",
        "bollinger_bandwidth",
        "bollinger_percent_b",
        "chaikin_volatility",
        "choppiness_index",
        "donchian",
        "envelope",
        "historical_volatility",
        "keltner",
        "standard_deviation",
        "volatility_stop",
    } <= set(list_indicators("volatility"))
    assert {
        "accumulation_distribution",
        "chaikin_money_flow",
        "chaikin_oscillator",
        "ease_of_movement",
        "force_index",
        "klinger_oscillator",
        "money_flow_index",
        "obv",
        "price_volume_trend",
        "volume_oscillator",
        "vwap",
    } <= set(list_indicators("volume"))


def test_build_indicator_atr() -> None:
    a = build_indicator("atr", period=14)
    assert isinstance(a, Atr)
    assert a.period == 14


def test_indicator_family_volatility_volume() -> None:
    assert indicator_family("atr") == "volatility"
    assert indicator_family("bollinger") == "volatility"
    assert indicator_family("vwap") == "volume"
    assert indicator_family("obv") == "volume"


def test_flat_access_volatility_volume() -> None:
    import tantra.indicators as indicators_module

    assert indicators_module.Atr is Atr
    assert indicators_module.Bollinger is Bollinger
    assert indicators_module.BollingerValue is BollingerValue
    assert indicators_module.Donchian is Donchian
    assert indicators_module.DonchianValue is DonchianValue
    assert indicators_module.Vwap is Vwap


# --- volatility/volume numeric sanity (Decimal, exact) --------------------


def test_atr_warm_then_decimal() -> None:
    a = Atr(3)
    assert a.warmup == 4  # period + 1 (the first TR needs a previous close)
    assert a.update("10", "8", "9") is None
    assert a.update("12", "9", "11") is None
    assert a.update("14", "11", "13") is None
    v = a.update("16", "13", "15")
    assert isinstance(v, Decimal)
    assert v == Decimal("3")  # TRs 3, 3, 3 seeded as 9 / 3


def test_atr_include_first_bar() -> None:
    a = Atr(2, include_first_bar=True)
    assert a.update("10", "8", "9") is None  # TR = high - low = 2
    v = a.update("12", "9", "11")  # TR = 3; seed (2 + 3) / 2
    assert isinstance(v, Decimal)
    assert v == Decimal("2.5")


def test_bollinger_returns_bollinger_value_decimal() -> None:
    b = Bollinger(3, Decimal("2"))
    assert b.update("10") is None
    assert b.update("20") is None
    v = b.update("30")
    assert isinstance(v, BollingerValue)
    assert isinstance(v.upper, Decimal)
    assert isinstance(v.middle, Decimal)
    assert isinstance(v.lower, Decimal)
    assert v.middle == Decimal("20")
    sd = (Decimal("200") / Decimal("3")).sqrt()  # population std of 10, 20, 30
    assert v.upper == Decimal("20") + 2 * sd
    assert v.lower == Decimal("20") - 2 * sd


def test_donchian_returns_donchian_value_decimal() -> None:
    d = Donchian(3)
    assert d.update("10", "5") is None
    assert d.update("20", "6") is None
    v = d.update("30", "7")
    assert isinstance(v, DonchianValue)
    assert isinstance(v.upper, Decimal)
    assert v.upper == Decimal("30")
    assert v.lower == Decimal("5")
    v2 = d.update("25", "8")  # slides: window is 20, 30, 25 / 6, 7, 8
    assert v2.upper == Decimal("30")
    assert v2.lower == Decimal("6")


def test_vwap_accumulates_and_zero_volume() -> None:
    v = Vwap()
    assert v.warmup is None  # session-anchored: data-dependent warm-up
    first = v.update("10", "8", "9", "100", 100)
    assert isinstance(first, VwapValue)
    assert isinstance(first.vwap, Decimal)
    assert first.vwap == Decimal("9")  # single bar: hlc3 = (10 + 8 + 9) / 3
    assert first.upper == first.lower == first.vwap  # zero deviation single-bar session
    second = v.update("14", "12", "13", "100", 100)
    assert second.vwap == Decimal("11")  # pv = 900 + 1300 = 2200 over volume 200
    assert second.upper == Decimal("13")  # sd = sqrt(125 - 121) = 2
    assert second.lower == Decimal("9")
    # zero volume on a fresh IST session day: vwap is the latest hlc3, bands zero
    z = v.update("10", "8", "9", "0", 100 + 86_400_000_000_000)
    assert z.vwap == Decimal("9")
    assert z.upper == z.lower == z.vwap


def test_obv_simple_accumulation() -> None:
    o = Obv()
    assert o.update("10", "100") == Decimal("0")  # first bar: no change
    assert o.update("12", "100") == Decimal("100")
    assert o.update("10", "50") == Decimal("50")
    assert o.update("10", "25") == Decimal("50")  # unchanged close: no flow


def test_money_flow_index_rolling_sum_decimal() -> None:
    m = MoneyFlowIndex(2)
    assert m.update("10", "8", "9", "100") is None  # no previous hlc3
    assert m.update("12", "10", "11", "100") is None  # window warming
    v = m.update("14", "12", "13", "100")
    assert isinstance(v, Decimal)
    assert v == Decimal("100")  # only positive flow -> 100


def test_chaikin_money_flow_rolling_sum_decimal() -> None:
    c = ChaikinMoneyFlow(2)
    assert c.update("10", "8", "9", "100") is None
    v = c.update("12", "8", "11", "100")
    assert isinstance(v, Decimal)
    assert v == Decimal("50") / Decimal("200")  # clv volumes 0 + 50 over window volume 200
    v2 = c.update("14", "8", "13", "100")  # window slides: clv volumes 50 + 400/6
    assert v2 == (Decimal("50") + Decimal("400") / Decimal("6")) / Decimal("200")


# --- volatility/volume supersession (ex 0006) -----------------------------


def test_supertrend_uses_registered_volatility_atr() -> None:
    st = Supertrend(3, Decimal("2"))
    assert isinstance(st._atr, Atr)  # consumes the registered volatility.atr.Atr
    assert st.update("12", "10", "11") is None
    assert st.update("14", "11", "13") is None
    v = st.update("16", "12", "15")
    assert isinstance(v, SupertrendValue)
    assert v.value == Decimal("20")  # upper band: hl2 14 + 2 * ATR 3
    assert v.direction == Decimal("-1")


def test_atr_import_and_registry_same_class() -> None:
    from tantra.indicators.volatility import Atr as VolatilityAtr

    assert VolatilityAtr is Atr
    assert isinstance(build_indicator("atr"), Atr)  # registry builds the same class


def test_atr_standin_removed() -> None:
    with pytest.raises(ModuleNotFoundError):
        import tantra.indicators._atr  # noqa: F401


# --- support_resistance / breadth / statistical families (ex 0006, final wave) ----


def test_list_indicators_final_three_families() -> None:
    all_kinds = set(list_indicators())
    for family in ("support_resistance", "breadth", "statistical"):
        kinds = set(list_indicators(family))
        assert kinds
        assert kinds <= all_kinds
    assert {
        "fibonacci_retracement",
        "pivot_points",
        "williams_fractals",
    } <= set(list_indicators("support_resistance"))
    assert {
        "advance_decline_line",
        "mcclellan_oscillator",
        "put_call_ratio",
        "trin",
        "updown_volume_ratio",
    } <= set(list_indicators("breadth"))
    assert {"beta", "correlation", "covariance", "hurst_exponent", "zscore"} <= set(
        list_indicators("statistical")
    )


def test_registry_total_matches_kernel() -> None:
    """The wheel registry IS the kernel: 74 canonical kinds, all 8 families, no orphans.

    The examples ``_kernel/indicators`` float mirror was promoted into this wheel
    (ex 0006) and deleted; the wheel registry is now the single source of truth, so
    the cross-check is an internal self-consistency gate instead of a mirror compare.
    """
    kinds = list_indicators()
    assert len(kinds) == 74
    assert len(set(kinds)) == 74  # every kind registered exactly once
    assert set(FAMILIES) == _ALL_FAMILIES

    by_family = {family: [] for family in FAMILIES}
    for kind in kinds:
        family = indicator_family(kind)
        assert family in FAMILIES, f"{kind} has no known family"
        by_family[family].append(kind)

    # Per-family counts are a pinned invariant of the canonical catalog.
    assert {family: len(kinds) for family, kinds in by_family.items()} == {
        "moving_average": 12,
        "trend": 9,
        "momentum": 17,
        "volatility": 12,
        "volume": 11,
        "support_resistance": 3,
        "breadth": 5,
        "statistical": 5,
    }


def test_flat_access_case_compat_zscore() -> None:
    from tantra.indicators import Zscore

    assert Zscore is ZScore


def test_williams_fractals_warm_then_value() -> None:
    f = WilliamsFractals()
    assert f.warmup == 5
    assert f.update("10", "8") is None
    assert f.update("11", "9") is None
    assert f.update("12", "7") is None
    assert f.update("9", "10") is None
    v = f.update("8", "11")  # window 10,11,12,9,8 / 8,9,7,10,11
    assert isinstance(v, WilliamsFractalsValue)
    assert isinstance(v.up, Decimal) and isinstance(v.down, Decimal)
    assert v.up == Decimal("1")  # high[2] = 12 is the strict window high
    assert v.down == Decimal("1")  # low[2] = 7 is the strict window low
    v2 = f.update("13", "6")  # window slides: 11,12,9,8,13 / 9,7,10,11,6
    assert v2.up == Decimal("0")
    assert v2.down == Decimal("0")


def test_pivot_points_session_anchor() -> None:
    p = PivotPoints()
    assert p.warmup is None
    assert p.update("20", "10", "15", 100) is None  # day 1, first bar
    assert p.update("22", "12", "21", 200) is None  # day 1 still accumulating
    day2 = 100 + 86_400_000_000_000
    v = p.update("25", "14", "24", day2)  # day 2: levels from day 1 H/L/C
    assert isinstance(v, PivotPointsValue)
    pp = (Decimal("22") + Decimal("10") + Decimal("21")) / 3
    rng = Decimal("22") - Decimal("10")
    assert v.pp == pp
    assert v.r1 == 2 * pp - Decimal("10")
    assert v.s1 == 2 * pp - Decimal("22")
    assert v.r2 == pp + rng
    assert v.s2 == pp - rng
    assert v.r3 == Decimal("22") + 2 * (pp - Decimal("10"))
    assert v.s3 == Decimal("10") - 2 * (Decimal("22") - pp)
    # levels stay fixed for the rest of the session (same object)
    assert p.update("26", "13", "25", day2) is v
    with pytest.raises(ValueError):
        PivotPoints(mode="bogus")


def test_fibonacci_retracement_levels() -> None:
    f = FibonacciRetracement(3)
    assert f.warmup == 3
    assert f.update("10", "4") is None
    assert f.update("20", "6") is None
    v = f.update("15", "5")
    assert isinstance(v, FibonacciRetracementValue)
    assert isinstance(v.l0, Decimal)
    hi, lo, rng = Decimal("20"), Decimal("4"), Decimal("16")
    assert v.l0 == hi
    assert v.l1000 == lo
    assert v.l236 == hi - rng * Decimal("0.236")
    assert v.l500 == hi - rng * Decimal("0.5")


def test_advance_decline_line_accumulates() -> None:
    a = AdvanceDeclineLine()
    assert a.update("10", "6") == Decimal("4")
    assert a.update("12", "14") == Decimal("2")
    assert a.update("3", "1") == Decimal("4")


def test_mcclellan_oscillator_returns_decimal() -> None:
    m = McClellanOscillator(3, 9)  # alphas 2/4 = 0.5 and 2/10 = 0.2 (both exact)
    assert m.update("10", "8") == Decimal("0")  # net 2 seeds both EMAs at 2
    v = m.update("20", "16")  # net 4
    assert isinstance(v, Decimal)
    assert v == Decimal("0.6")  # (4*0.5 + 2*0.5) - (4*0.2 + 2*0.8)
    with pytest.raises(ValueError):
        McClellanOscillator(5, 5)


def test_put_call_ratio_and_breadth_ratios() -> None:
    p = PutCallRatio(1)
    assert p.update("2", "4") == Decimal("0.5")
    assert p.update("3", "3") == Decimal("1")
    assert p.update("5", "0") == Decimal("1")  # neutral when call volume <= 0
    t = Trin()
    assert t.update("100", "50", "200", "100") == Decimal("1")
    assert t.update("100", "25", "200", "100") == Decimal("2")
    assert t.update("100", "0", "200", "100") == Decimal("1")
    u = UpDownVolumeRatio()
    assert u.update("300", "100") == Decimal("3")
    assert u.update("300", "0") == Decimal("1")


def test_zscore_returns_decimal() -> None:
    z = ZScore(3)
    assert z.warmup == 3
    assert z.update("10") is None
    assert z.update("20") is None
    v = z.update("30")
    assert isinstance(v, Decimal)
    sd = (Decimal("200") / Decimal("3")).sqrt()  # population stdev of 10, 20, 30
    assert v == Decimal("10") / sd
    z2 = ZScore(2)
    assert z2.update("5") is None
    assert z2.update("5") == Decimal("0")  # zero stdev -> 0


def test_correlation_exact_and_nan() -> None:
    c = Correlation(4)
    assert c.warmup == 4
    assert c.update("1", "2") is None
    assert c.update("2", "1") is None
    assert c.update("3", "4") is None
    v = c.update("4", "3")  # window [1,2],[2,1],[3,4],[4,3]
    assert isinstance(v, Decimal)
    assert v == Decimal("0.6")  # Pearson r = 3/4 / sqrt(25/16) = 0.6
    c2 = Correlation(4)
    c2.update("1", "2")
    c2.update("2", "4")
    c2.update("3", "6")
    assert c2.update("4", "8") == Decimal("1")  # perfectly correlated
    # zero variance -> 0.0 (kernel formula)
    c3 = Correlation(3)
    c3.update("5", "1")
    c3.update("5", "2")
    assert c3.update("5", "3") == Decimal("0")
    # non-finite value in the window -> Decimal NaN
    c4 = Correlation(3)
    c4.update("1", "2")
    c4.update("2", "4")
    v4 = c4.update(Decimal("NaN"), "8")
    assert isinstance(v4, Decimal)
    assert v4.is_nan()


def test_beta_and_covariance_exact() -> None:
    b = Beta(2)
    assert b.warmup == 3
    assert b.update("1", "1") is None
    assert b.update("5", "3") is None
    v = b.update("11", "6")
    assert isinstance(v, Decimal)
    assert v == Decimal("2.8")  # cov/var over the return pairs [(4,2),(6/5,1)]
    b2 = Beta(2)
    b2.update("2", "1")
    b2.update("4", "2")
    assert b2.update("8", "4") == Decimal("0")  # zero benchmark variance -> 0
    c = Covariance(2)
    assert c.warmup == 3
    assert c.update("1", "1") is None
    assert c.update("2", "4") is None
    vc = c.update("5", "10")
    assert isinstance(vc, Decimal)
    assert vc == Decimal("-0.375")  # ddof=1 sample covariance of [(1,3),(1.5,1.5)]


def test_hurst_exponent_warm_then_decimal() -> None:
    h = HurstExponent(8)
    assert h.warmup == 8
    for i in range(1, 8):
        assert h.update(str(i)) is None
    v = h.update("8")
    assert isinstance(v, Decimal)
    assert v == Decimal("0.5")  # linear ramp: zero stdev -> random-walk 0.5
    h2 = HurstExponent(8)
    for close in ("1", "2", "4", "8", "16", "32", "64"):
        h2.update(close)
    v2 = h2.update("128")  # exponential ramp: positive stdev and range
    assert isinstance(v2, Decimal)
    assert Decimal("0") <= v2 <= Decimal("1")


def test_cross_family_rolling_consumers() -> None:
    z = ZScore(3)
    assert isinstance(z._m, RollingMoments)  # consumes RollingMoments
    z.update("10")
    z.update("20")
    assert isinstance(z.update("30"), Decimal)
    c = Correlation(3)
    assert isinstance(c._rp, RollingPairMoments)  # consumes RollingPairMoments
    c.update("1", "2")
    c.update("2", "4")
    vc = c.update("3", "6")
    assert isinstance(vc, Decimal)
    assert vc == Decimal("1")
    b = Beta(2)
    assert isinstance(b._rp, RollingPairMoments)
    assert b.update("1", "1") is None
    assert b.update("2", "4") is None  # one return pair only: still warming
    assert isinstance(b.update("4", "8"), Decimal)

