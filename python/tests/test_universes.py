"""Tests for the wheel universe lists (``tantra.markets.india.universes``)."""

from __future__ import annotations

import datetime as dt

import pytest
from tantra.markets.india.universes import (
    ALPHA30_ENGINE,
    ALPHA30_SEED,
    NIFTY_50_SYMBOLS,
    NIFTY_200_ALPHA_30_SYMBOLS,
    Constituent,
    UniverseHistory,
    UniverseUnavailable,
    alpha30_instruments,
    alpha30_symbols,
    banknifty_members,
    resolve_universe,
    save_universe_history,
)


def test_resolve_nifty50() -> None:
    assert [i.symbol for i in resolve_universe("nifty50")] == list(NIFTY_50_SYMBOLS)


def test_resolve_alpha30_engine_and_aliases() -> None:
    assert [i.symbol for i in resolve_universe("nifty200_alpha_30")] == list(
        ALPHA30_ENGINE
    )
    assert [i.symbol for i in resolve_universe("alpha30")] == list(ALPHA30_ENGINE)


def test_alpha30_symbols_variants() -> None:
    assert ALPHA30_ENGINE == tuple(NIFTY_200_ALPHA_30_SYMBOLS)
    assert alpha30_symbols() == ALPHA30_ENGINE
    assert alpha30_symbols("seed") == ALPHA30_SEED
    assert set(ALPHA30_SEED) != set(ALPHA30_ENGINE)
    assert [i.symbol for i in alpha30_instruments("seed")] == list(ALPHA30_SEED)
    with pytest.raises(ValueError, match="unknown alpha30 list"):
        alpha30_symbols("bogus")


def test_unknown_universe_raises() -> None:
    # Unknown names are rejected with ValueError; the catalog-less universe
    # (banknifty) surfaces as UniverseUnavailable.
    with pytest.raises(ValueError, match="unknown universe"):
        resolve_universe("no-such-universe")


def test_banknifty_unavailable_without_catalog(tmp_path) -> None:
    with pytest.raises(UniverseUnavailable):
        banknifty_members(data_dir=tmp_path)


def test_banknifty_reads_saved_catalog_history(tmp_path) -> None:
    history = UniverseHistory(
        "banknifty",
        (
            Constituent("AAA", dt.date(2020, 1, 1)),
            Constituent("BBB", dt.date(2020, 1, 1)),
        ),
    )
    save_universe_history(history, data_dir=tmp_path)
    members = banknifty_members(data_dir=tmp_path)
    assert [m.symbol for m in members] == ["AAA", "BBB"]


def test_constituent_active_interval() -> None:
    c = Constituent("AAA", dt.date(2020, 1, 1), dt.date(2020, 2, 1))
    assert c.active_on(dt.date(2020, 1, 15)) is True
    assert c.active_on(dt.date(2020, 2, 1)) is False
