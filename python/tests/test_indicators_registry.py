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
    Ema,
    IndicatorBank,
    Rma,
    Sma,
    Wma,
    build_indicator,
    indicator_family,
    indicator_spec,
    list_indicators,
    make_ma,
)
from tantra.indicators._base import indicator
from tantra.indicators.moving_average import Hma, Vwma
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
