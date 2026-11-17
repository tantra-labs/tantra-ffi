"""Type stubs for the tantra pure-Python SDK layer.

The compiled surface is re-exported from ``._tantra`` (see ``_tantra.pyi``).
"""
from datetime import datetime, tzinfo
from decimal import Decimal
from typing import Any, ClassVar, Optional

from ._tantra import (
    API_VERSION as API_VERSION,
    SCHEMA_VERSION as SCHEMA_VERSION,
    Bar as Bar,
    ConversionError as ConversionError,
    Currency as Currency,
    Decision as Decision,
    DepthLevel as DepthLevel,
    Exchange as Exchange,
    FillReport as FillReport,
    InstrumentId as InstrumentId,
    OrderAck as OrderAck,
    OrderRequest as OrderRequest,
    OrderSide as OrderSide,
    OrderStatus as OrderStatus,
    Price as Price,
    Quantity as Quantity,
    RiskEngine as RiskEngine,
    RiskRefused as RiskRefused,
    StrategyRunner as StrategyRunner,
    Tick as Tick,
    TimeInForce as TimeInForce,
    __version__ as __version__,
    bars_to_stream as bars_to_stream,
    now_iso as now_iso,
    stream_capsule_name as stream_capsule_name,
    ticks_to_stream as ticks_to_stream,
)


class Parameter:
    default: Any
    min: Optional[Any]
    max: Optional[Any]
    step: Optional[Any]

    def __init__(self, default: Any, min: Any = None, max: Any = None, step: Any = None) -> None: ...
    @classmethod
    def int(cls, default: int, min: int = ..., max: int = ...) -> Parameter: ...
    def as_dict(self) -> dict: ...


class Strategy:
    logger: Any
    indicators: Any

    def __init__(self) -> None: ...
    def on_start(self) -> None: ...
    def on_bar(self, bar: Bar) -> None: ...
    def on_tick(self, tick: Tick) -> None: ...
    def on_order_event(self, event: Any) -> None: ...
    def buy(
        self,
        symbol: str,
        quantity: Decimal | str,
        *,
        limit_price: Optional[Decimal | str] = None,
        tag: Optional[str] = None,
    ) -> Optional[OrderAck]: ...
    def sell(
        self,
        symbol: str,
        quantity: Decimal | str,
        *,
        limit_price: Optional[Decimal | str] = None,
        tag: Optional[str] = None,
    ) -> Optional[OrderAck]: ...


class BacktestResult:
    bars_processed: int
    orders_filled: int
    events: int
    refusals: int
    algo_id: str

    def __init__(
        self,
        bars_processed: int,
        orders_filled: int,
        events: int,
        refusals: int,
        algo_id: str,
    ) -> None: ...
    def summary(self) -> str: ...


def run(
    strategy: Strategy,
    bars: list[Bar],
    *,
    algo_id: str = "default-algo",
    on_start: bool = True,
) -> BacktestResult: ...


def to_decimal(value: Decimal | str | Price | Quantity) -> Decimal: ...
def instrument_id(symbol: str) -> InstrumentId: ...


class Sizer: ...
def fixed_quantity(quantity: Decimal | str) -> Decimal: ...
def fractional(equity: Decimal | str, risk_pct: Decimal | str, entry_price: Decimal | str) -> Decimal: ...
def risk_budget(
    equity: Decimal | str,
    max_risk_pct: Decimal | str,
    entry_price: Decimal | str,
    stop_price: Decimal | str,
) -> Decimal: ...


class SessionWindow:
    name: str
    open_time: str
    close_time: str

    def __init__(self, name: str, open_time: str, close_time: str) -> None: ...


class Session:
    PRE_MARKET: ClassVar[SessionWindow]
    LIVE: ClassVar[SessionWindow]
    POST_MARKET: ClassVar[SessionWindow]

    @staticmethod
    def current(now: Optional[datetime] = None, tz: tzinfo = ...) -> Optional[SessionWindow]: ...
    @staticmethod
    def is_live(now: Optional[datetime] = None) -> bool: ...


PRE_MARKET: SessionWindow
LIVE: SessionWindow
POST_MARKET: SessionWindow
def current_session(now: Optional[datetime] = None, tz: tzinfo = ...) -> Optional[SessionWindow]: ...
def is_live(now: Optional[datetime] = None) -> bool: ...


class SMA:
    def __init__(self, period: int) -> None: ...
    def add(self, price: Decimal | str) -> Optional[Decimal]: ...
    def value(self) -> Optional[Decimal]: ...
    def crosses_above(self, other: Any) -> bool: ...
    def crosses_below(self, other: Any) -> bool: ...


class EMA:
    def __init__(self, period: int) -> None: ...
    def add(self, price: Decimal | str) -> Optional[Decimal]: ...
    def value(self) -> Optional[Decimal]: ...
    def crosses_above(self, other: Any) -> bool: ...
    def crosses_below(self, other: Any) -> bool: ...


class RSI:
    def __init__(self, period: int = 14) -> None: ...
    def add(self, price: Decimal | str) -> Optional[Decimal]: ...
    def value(self) -> Optional[Decimal]: ...
