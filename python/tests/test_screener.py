"""Wheel `tantra.screener` surface (ex 0003 closure): metric catalog + coverage helpers."""

from __future__ import annotations

import datetime as dt

from tantra.screener import Coverage, DateInterval, Metric, MetricCatalog, load_catalog


def test_load_catalog_returns_a_catalog_with_known_metrics() -> None:
    catalog = load_catalog()
    assert isinstance(catalog, MetricCatalog)
    for key in ("close", "open", "high", "low", "volume", "pe_ratio", "sma20"):
        assert key in catalog
        assert catalog.get(key) is not None
        assert catalog[key].name == key


def test_catalog_get_returns_none_for_unknown_metric() -> None:
    catalog = load_catalog()
    assert catalog.get("no_such_metric") is None
    assert "no_such_metric" not in catalog


def test_catalog_all_names_are_unique_and_complete() -> None:
    catalog = load_catalog()
    names = catalog.all_names()
    assert len(names) == len(set(names))
    assert len(names) >= 10
    assert "close" in names
    assert "volume" in names


def test_catalog_by_type_covers_the_known_value_types() -> None:
    catalog = load_catalog()
    # Every catalog metric is value_type "float" today; by_type covers it.
    assert "close" in catalog.by_type("float")
    assert set(catalog.by_type("float")) == set(catalog.all_names())


def test_catalog_metrics_are_frozen_metrics() -> None:
    metric = load_catalog()["close"]
    assert isinstance(metric, Metric)
    assert metric.group == "price"
    assert metric.has_timeframe is True


def test_coverage_add_and_intervals_round_trip_with_date_interval() -> None:
    coverage = Coverage()
    first = DateInterval(dt.date(2025, 1, 1), dt.date(2025, 6, 1))
    second = DateInterval(dt.date(2025, 6, 1), dt.date(2026, 1, 1))
    assert coverage.intervals("RELIANCE") == []
    coverage.add("RELIANCE", first)
    coverage.add("RELIANCE", second)
    assert coverage.intervals("RELIANCE") == [first, second]
    assert coverage.intervals("TCS") == []
