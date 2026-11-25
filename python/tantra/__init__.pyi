"""Type stubs for the tantra pure-Python SDK layer.

The compiled surface is re-exported from ``._tantra`` (see ``_tantra.pyi``).
"""

from datetime import datetime, tzinfo
from decimal import Decimal as Decimal
from typing import Any, ClassVar

from . import (
    _tantra as _tantra,
)
from . import (
    adapters as adapters,
)
from . import (
    ai as ai,
)
from . import (
    algo_analytics as algo_analytics,
)
from . import (
    bar as bar,
)
from . import (
    calendar as calendar,
)
from . import (
    data as data,
)
from . import (
    display as display,
)
from . import (
    entities as entities,
)
from . import (
    execution as execution,
)
from . import (
    indicators as indicators,
)
from . import (
    markets as markets,
)
from . import (
    metrics as metrics,
)
from . import (
    money as money,
)
from . import (
    optimizer as optimizer,
)
from . import (
    options as options,
)
from . import (
    order as order,
)
from . import (
    order_state as order_state,
)
from . import (
    portfolio as portfolio,
)
from . import (
    quant as quant,
)
from . import (
    risk as risk,
)
from . import (
    screener as screener,
)
from . import (
    session as session,
)
from . import (
    sizing as sizing,
)
from . import (
    strategy as strategy,
)
from . import (
    tick as tick,
)
from ._tantra import (
    API_VERSION as API_VERSION,
)
from ._tantra import (
    SCHEMA_VERSION as SCHEMA_VERSION,
)
from ._tantra import (
    Bar as Bar,
)
from ._tantra import (
    ConversionError as ConversionError,
)
from ._tantra import (
    Currency as Currency,
)
from ._tantra import (
    Decision as Decision,
)
from ._tantra import (
    DepthLevel as DepthLevel,
)
from ._tantra import (
    Exchange as Exchange,
)
from ._tantra import (
    FillReport as FillReport,
)
from ._tantra import (
    InstrumentId as InstrumentId,
)
from ._tantra import (
    OrderAck as OrderAck,
)
from ._tantra import (
    OrderEvent as OrderEvent,
)
from ._tantra import (
    OrderRequest as OrderRequest,
)
from ._tantra import (
    OrderSide as OrderSide,
)
from ._tantra import (
    OrderStatus as OrderStatus,
)
from ._tantra import (
    Price as Price,
)
from ._tantra import (
    Quantity as Quantity,
)
from ._tantra import (
    RiskEngine as RiskEngine,
)
from ._tantra import (
    RiskRefused as RiskRefused,
)
from ._tantra import (
    StrategyRunner as StrategyRunner,
)
from ._tantra import (
    Tick as Tick,
)
from ._tantra import (
    TimeInForce as TimeInForce,
)
from ._tantra import (
    __version__ as __version__,
)
from ._tantra import (
    bars_to_stream as bars_to_stream,
)
from ._tantra import (
    now_iso as now_iso,
)
from ._tantra import (
    stream_capsule_name as stream_capsule_name,
)
from ._tantra import (
    ticks_to_stream as ticks_to_stream,
)

class Parameter:
    default: Any
    min: Any | None
    max: Any | None
    step: Any | None

    def __init__(
        self, default: Any, min: Any = None, max: Any = None, step: Any = None
    ) -> None: ...
    @classmethod
    def int(cls, default: int, min: int = ..., max: int = ...) -> Parameter: ...
    def as_dict(self) -> dict[str, Any]: ...

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
        limit_price: Decimal | str | None = None,
        tag: str | None = None,
    ) -> OrderAck | None: ...
    def sell(
        self,
        symbol: str,
        quantity: Decimal | str,
        *,
        limit_price: Decimal | str | None = None,
        tag: str | None = None,
    ) -> OrderAck | None: ...

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
def to_decimal(value: Decimal | int | str | Price | Quantity) -> Decimal: ...
def instrument_id(symbol: str) -> InstrumentId: ...

class Sizer: ...

def fixed_quantity(quantity: Decimal | str) -> Decimal: ...
def fractional(
    equity: Decimal | str, risk_pct: Decimal | str, entry_price: Decimal | str
) -> Decimal: ...
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
    def current(
        now: datetime | None = None, tz: tzinfo = ...
    ) -> SessionWindow | None: ...
    @staticmethod
    def is_live(now: datetime | None = None) -> bool: ...

PRE_MARKET: SessionWindow
LIVE: SessionWindow
POST_MARKET: SessionWindow

def current_session(
    now: datetime | None = None, tz: tzinfo = ...
) -> SessionWindow | None: ...
def is_live(now: datetime | None = None) -> bool: ...

class SMA:
    def __init__(self, period: int) -> None: ...
    def add(self, price: Decimal | str) -> Decimal | None: ...
    def value(self) -> Decimal | None: ...
    def crosses_above(self, other: Any) -> bool: ...
    def crosses_below(self, other: Any) -> bool: ...

class EMA:
    def __init__(self, period: int) -> None: ...
    def add(self, price: Decimal | str) -> Decimal | None: ...
    def value(self) -> Decimal | None: ...
    def crosses_above(self, other: Any) -> bool: ...
    def crosses_below(self, other: Any) -> bool: ...

class RSI:
    def __init__(self, period: int = 14) -> None: ...
    def add(self, price: Decimal | str) -> Decimal | None: ...
    def value(self) -> Decimal | None: ...
