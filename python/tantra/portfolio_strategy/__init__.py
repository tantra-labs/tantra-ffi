# wheel surface (ex 0006): Decimal-canonical kernel-parity portfolio strategy package
# (mirrors tantra_examples/_kernel/portfolio_strategy public API)

"""Composable portfolio construction: universe, selection, weighting, schedule.

``PortfolioStrategy(universe, weighting, schedule, selector)`` wires the parts into a
``TargetWeightStrategy``. Each part is a small ``Protocol`` with simple implementations.
"""
# mirror: kernel-verbatim port (gap 0006)

from tantra.portfolio_strategy.factory import build_portfolio_strategy
from tantra.portfolio_strategy.schedule import (
    AnyOf,
    DriftBand,
    EveryNDays,
    MonthlyFirstSession,
    RebalanceSchedule,
    ScheduleState,
)
from tantra.portfolio_strategy.scoring import (
    low_volatility,
    mean_reversion,
    momentum,
)
from tantra.portfolio_strategy.selection import SelectAll, Selector, TopN
from tantra.portfolio_strategy.strategy import PortfolioStrategy
from tantra.portfolio_strategy.universe import (
    NamedUniverse,
    StaticUniverse,
    Universe,
)
from tantra.portfolio_strategy.view import MarketView, PriceHistory
from tantra.portfolio_strategy.weighting import (
    EqualWeight,
    InverseVolatility,
    WeightingScheme,
)

__all__ = [
    "AnyOf",
    "DriftBand",
    "EqualWeight",
    "EveryNDays",
    "InverseVolatility",
    "MarketView",
    "MonthlyFirstSession",
    "NamedUniverse",
    "PortfolioStrategy",
    "PriceHistory",
    "RebalanceSchedule",
    "ScheduleState",
    "SelectAll",
    "Selector",
    "StaticUniverse",
    "TopN",
    "Universe",
    "WeightingScheme",
    "build_portfolio_strategy",
    "low_volatility",
    "mean_reversion",
    "momentum",
]
