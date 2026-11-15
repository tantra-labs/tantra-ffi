# wheel surface (ex 0006): backtest simulators (mirrors tantra_examples/_kernel/backtest public API)
# stand-in closure for tantra-examples gap 0006

"""Backtest building blocks: simulated execution ports (``tantra.backtest.simulated``).

Wave 1 of the backtest-sims slice of ``tantra-examples`` gap 0006: the next-open
simulator and its ``impact`` / ``opening_auction`` knobs. The ``L2Execution`` /
``TopOfBook`` / ``BarCloseFills`` entries ship in a later wave.
"""

from __future__ import annotations

from tantra.backtest.impact import (
    MarketImpact,  # gap 0006: backtest simulator mirror
)
from tantra.backtest.opening_auction import (
    OpeningAuction,  # gap 0006: backtest simulator mirror
)
from tantra.backtest.simulated import (
    FillCostFn,
    FillModel,
    NextOpenExecution,
    SessionOpen,
    group_sessions,
    make_simulator,
    resolve_fill_costs,
    zero_costs,
)

# l2_sim + BarCloseFills ship in a later ex 0006 wave.

__all__ = [
    "FillCostFn",
    "FillModel",
    "MarketImpact",
    "NextOpenExecution",
    "OpeningAuction",
    "SessionOpen",
    "group_sessions",
    "make_simulator",
    "resolve_fill_costs",
    "zero_costs",
]
