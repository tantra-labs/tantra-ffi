"""Tantra Python SDK (Tier 4 FFI).

Re-exports the compiled ``tantra._tantra`` extension surface plus the
pure-Python high-level API (``Strategy``, ``run``, indicators, sizing, session
windows, and Arrow bridge helpers).
"""
from decimal import Decimal

from tantra import _tantra
from tantra._tantra import (
    SCHEMA_VERSION,
    API_VERSION,
    __version__,
    RiskRefused,
    ConversionError,
    Price,
    Quantity,
    Currency,
    Exchange,
    InstrumentId,
    OrderSide,
    TimeInForce,
    OrderStatus,
    DepthLevel,
    Bar,
    Tick,
    OrderRequest,
    OrderAck,
    FillReport,
    OrderEvent,
    Decision,
    RiskEngine,
    StrategyRunner,
    now_iso,
    bars_to_stream,
    ticks_to_stream,
    stream_capsule_name,
)

# Pure-Python API (submodules importable as `tantra.strategy`, ...).
# `cli` is deliberately not imported eagerly so `python -m tantra.cli`
# executes the module cleanly; it stays importable as `import tantra.cli`.
from tantra import strategy, indicators, sizing, session, data
from tantra import algo_analytics, entities, money, optimizer, quant, screener
from tantra import adapters, bar, order, order_state, tick
from tantra import execution
from tantra.strategy import Strategy, Parameter, BacktestResult, run
from tantra.sizing import Sizer, fixed_quantity, fractional, risk_budget
from tantra.optimizer import ParetoPoint, extract_pareto_frontier, plot_pareto, sharpe_sortino_dd
from tantra.quant import (
    covariance_matrix,
    mean,
    ols,
    returns,
    solve_linear_system,
    std_dev,
)
from tantra.entities import (
    Instrument,
    InstrumentKind,
    MinorUnit,
    Money,
    OptionType,
    Position,
    PositionSide,
    Trade,
)
from tantra.session import (
    Session,
    SessionWindow,
    PRE_MARKET,
    LIVE,
    POST_MARKET,
    current_session,
    is_live,
)
from tantra.types import instrument_id, to_decimal
from tantra.indicators import SMA, EMA, RSI

__all__ = [
    "SCHEMA_VERSION", "API_VERSION", "__version__",
    "RiskRefused", "ConversionError",
    "Price", "Quantity", "Currency", "Exchange", "InstrumentId",
    "OrderSide", "TimeInForce", "OrderStatus",
    "DepthLevel", "Bar", "Tick",
    "OrderRequest", "OrderAck", "FillReport", "OrderEvent",
    "Decision", "RiskEngine", "StrategyRunner",
    "now_iso", "bars_to_stream", "ticks_to_stream", "stream_capsule_name",
    "Decimal",
    "Strategy", "Parameter", "BacktestResult", "run",
    "Sizer", "fixed_quantity", "fractional", "risk_budget",
    "Session", "SessionWindow", "PRE_MARKET", "LIVE", "POST_MARKET",
    "current_session", "is_live",
    "instrument_id", "to_decimal",
    "SMA", "EMA", "RSI",
    "Instrument", "InstrumentKind", "MinorUnit", "Money",
    "OptionType", "Position", "PositionSide", "Trade",
    "ParetoPoint", "extract_pareto_frontier", "plot_pareto", "sharpe_sortino_dd",
    "covariance_matrix", "mean", "ols", "returns", "solve_linear_system", "std_dev",
    "adapters", "algo_analytics", "bar", "cli", "data", "entities", "execution", "indicators", "money",
    "optimizer", "order", "order_state", "quant", "screener", "session", "sizing", "strategy", "tick",
]
