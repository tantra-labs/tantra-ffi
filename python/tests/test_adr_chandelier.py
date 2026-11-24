"""Tests for AdrPct and ChandelierExit in the tantra.indicators registry."""

from __future__ import annotations

from decimal import Decimal

import pytest
from tantra.indicators import (
    AdrPct,
    ChandelierExit,
    ChandelierExitValue,
    build_indicator,
    indicator_family,
    indicator_spec,
    list_indicators,
)


def test_adr_pct_registered_in_volatility_catalog() -> None:
    assert "adr_pct" in set(list_indicators("volatility"))
    assert indicator_family("adr_pct") == "volatility"
    spec = indicator_spec("adr_pct")
    assert spec["inputs"] == ["high", "low"]
    assert spec["outputs"] == ["value"]
    ind = build_indicator("adr_pct", period=20)
    assert isinstance(ind, AdrPct)
    assert ind.warmup == 20


def test_adr_pct_mean_of_ratios_golden() -> None:
    adr = AdrPct(2)
    assert adr.update(Decimal(200), Decimal(100)) is None
    assert adr.update(Decimal(15), Decimal(10)) == Decimal(75)
    adr.reset()
    assert adr.update(Decimal(104), Decimal(100)) is None


def test_adr_pct_non_positive_low_returns_none_without_mutation() -> None:
    adr = AdrPct(2)
    assert adr.update(Decimal(105), Decimal(100)) is None
    assert adr.update(Decimal(105), Decimal(0)) is None
    assert adr.update(Decimal(105), Decimal(-1)) is None
    assert adr.update(Decimal(115), Decimal(100)) == Decimal(10)


def test_chandelier_exit_registered_in_volatility_catalog() -> None:
    assert "chandelier_exit" in set(list_indicators("volatility"))
    assert indicator_family("chandelier_exit") == "volatility"
    spec = indicator_spec("chandelier_exit")
    assert spec["inputs"] == ["high", "low", "close"]
    assert spec["outputs"] == ["long_stop", "short_stop"]
    ind = build_indicator("chandelier_exit", period=22, mult=Decimal(3))
    assert isinstance(ind, ChandelierExit)
    assert ind.warmup == 22


def test_chandelier_exit_golden_matches_rust() -> None:
    ce = ChandelierExit(2, Decimal(3))
    assert ce.update(Decimal(10), Decimal(8), Decimal(9)) is None
    v2 = ce.update(Decimal(12), Decimal(9), Decimal(11))
    assert v2 == ChandelierExitValue(Decimal("4.5"), Decimal("15.5"))
    v3 = ce.update(Decimal(11), Decimal(10), Decimal("10.5"))
    assert v3 == ChandelierExitValue(Decimal("6.75"), Decimal("14.25"))
    ce.reset()
    assert ce.update(Decimal(10), Decimal(8), Decimal(9)) is None


def test_chandelier_exit_rejects_negative_multiplier() -> None:
    with pytest.raises(ValueError, match="mult"):
        ChandelierExit(14, Decimal(-1))
