# wheel surface (ex 0006): backtest simulators (mirrors tantra_examples/_kernel/backtest public API)
# stand-in closure for tantra-examples gap 0006

"""Backtest building blocks: simulated execution ports (``tantra.backtest.simulated``).

The backtest-sims slice of ``tantra-examples`` gap 0006: the next-open simulator and its
``impact`` / ``opening_auction`` knobs, the L2 top-of-book simulator
(``tantra.backtest.l2_sim``) and the single-price conformance simulator
(``tantra.backtest.bar_close_fills``).
"""

from __future__ import annotations

from tantra.backtest.bar_close_fills import (
    BarCloseFills,  # gap 0006: backtest simulator mirror
)
from tantra.backtest.impact import (
    MarketImpact,  # gap 0006: backtest simulator mirror
)
from tantra.backtest.l2_sim import (  # gap 0006: backtest simulator mirror
    L2Execution,
    TopOfBook,
)
from tantra.backtest.opening_auction import (
    OpeningAuction,  # gap 0006: backtest simulator mirror
)
from tantra.backtest.simulated import (
    BACKEND_ENV,
    Backend,
    FillCostFn,
    FillModel,
    NextOpenExecution,
    SessionOpen,
    fill_costs_from_model,
    group_sessions,
    is_intraday,
    make_simulator,
    resolve_backend,
    resolve_fill_costs,
    session_date,
    zero_costs,
)

__all__ = [
    "BACKEND_ENV",
    "Backend",
    "BarCloseFills",
    "FillCostFn",
    "FillModel",
    "L2Execution",
    "MarketImpact",
    "NextOpenExecution",
    "OpeningAuction",
    "SessionOpen",
    "TopOfBook",
    "fill_costs_from_model",
    "group_sessions",
    "is_intraday",
    "make_simulator",
    "resolve_backend",
    "resolve_fill_costs",
    "session_date",
    "zero_costs",
]
