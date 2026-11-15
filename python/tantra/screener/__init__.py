"""Wheel screener surface (ex 0003 closure): metric catalog + coverage helpers.

The ``tantra.screener`` submodule ships the screener metric catalog and coverage
helpers the AI research loop consumes — pure Python, no compiled surface needed.
"""

from tantra.screener.catalog import Metric, MetricCatalog, load_catalog
from tantra.screener.coverage import Coverage, DateInterval

__all__ = ["Coverage", "DateInterval", "Metric", "MetricCatalog", "load_catalog"]
