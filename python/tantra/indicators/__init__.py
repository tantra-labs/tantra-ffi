# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Streaming indicators, grouped by family like TradingView's taxonomy
(moving_average, trend, momentum, volatility, volume, support_resistance, breadth, statistical).

``update`` returns ``None`` until warmed up. Import from the family
(``indicators.moving_average.Ema``) or from here (``indicators.Ema``).
"""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from typing import Any  # mirror accommodation (gap 0006)

from tantra.indicators import _base, bank, moving_average  # noqa: F401  (importing registers the indicators)
from tantra.indicators._base import FAMILIES, Indicator
from tantra.indicators.bank import IndicatorBank
from tantra.indicators.moving_average import Ema, Rma, Sma, Wma, make_ma
from tantra.indicators._legacy import SMA, EMA, RSI


def indicator_family(kind: str) -> str:
    return _base.get(kind).family


def indicator_spec(kind: str) -> dict:
    """JSON-serialisable description of an indicator (params, inputs, outputs, family)."""
    return _base.spec(kind)


def list_indicators(family: str | None = None) -> list[str]:
    """Indicator kinds, optionally only those in ``family``."""
    if family is not None and family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}; choose from {list(FAMILIES)}")
    return sorted(k for k, c in _base._REGISTRY.items() if family is None or c.family == family)


def build_indicator(kind: str, **params: Any) -> Any:  # mirror accommodation (gap 0006)
    """Builds an indicator from a config-style spec, e.g. ``build_indicator("ema", period=20)``.

    Unknown kinds raise ``ValueError``; unknown or invalid parameters raise ``TypeError`` /
    ``ValueError`` from the indicator itself.
    """
    return _base.get(kind)(**params)


# remaining families (trend, momentum, volatility, volume, support_resistance, breadth, statistical) ship in later ex 0006 waves
__all__ = [
    "FAMILIES",
    "Ema",
    "Indicator",
    "IndicatorBank",
    "Rma",
    "Sma",
    "Wma",
    "build_indicator",
    "indicator_family",
    "indicator_spec",
    "list_indicators",
    "make_ma",
    "SMA",
    "EMA",
    "RSI",
]


def __getattr__(name: str) -> Any:  # mirror accommodation (gap 0006)
    """Flat access to every registered indicator class: ``from ...indicators import Alma``."""
    for cls in _base._REGISTRY.values():
        if cls.__name__ == name:
            return cls
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
