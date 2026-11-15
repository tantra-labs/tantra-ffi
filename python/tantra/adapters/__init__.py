"""Broker adapters: the contract, the canonical value types, the registry and the test double.

Import from here, never from the modules directly::

    from tantra.adapters import Adapter, ExecutionAdapter, MarketDataAdapter, resolve_adapter

The contract is three declarations in :mod:`tantra.adapters.base` (a lifecycle facade plus a
market-data role and an execution role), the values an adapter may return live in
:mod:`tantra.adapters.models`, and :mod:`tantra.adapters.capabilities` says up front what an
adapter can do. :mod:`tantra.adapters.contract` is the suite every adapter must pass, and
:mod:`tantra.adapters.testing.FakeAdapter` is the in-memory reference implementation.

The shared runtime pieces live here too: :mod:`tantra.adapters.session` owns token expiry and
refresh, :mod:`tantra.adapters.rate_limit` a token-bucket limiter that holds across workers,
and :mod:`tantra.adapters.secrets` an encrypted at-rest secret store (E1-S5).

Broker implementations live in the separate ``tantra-adapters`` repository, installed as
packages that advertise themselves through the ``tantra.adapters`` entry-point group.
"""
# wheel surface (ex 0007 closure)

from tantra.adapters.base import (
    Adapter,
    ExecutionAdapter,
    ExecutionClient,
    FullAdapterClient,
    MarketDataAdapter,
    MarketDataClient,
)
from tantra.adapters.boundary import (
    BoundaryViolation,
    find_boundary_violations,
    format_violations,
)
from tantra.adapters.capabilities import (
    AdapterCapabilities,
    Capability,
    capability_for_method,
)
from tantra.adapters.errors import (
    AdapterError,
    AdapterFatalError,
    AdapterNotFound,
    CapabilityError,
    SessionError,
    SessionExpired,
)
from tantra.adapters.models import (
    DepthLevel,
    Funds,
    Holding,
    MarginReport,
    MarketDepth,
    OrderReport,
    Product,
    RunMode,
    SessionInfo,
    StreamCallback,
    StreamEvent,
    StreamMode,
    Subscription,
)
from tantra.adapters.order_events import ReportReduction, reduce_order_report
from tantra.adapters.rate_limit import (
    BucketState,
    FileBackedBucket,
    InMemoryBucket,
    RateLimiter,
    RateLimiterRegistry,
    RateLimitExceeded,
    SharedBucketStore,
)
from tantra.adapters.registry import (
    ENTRY_POINT_GROUP,
    AdapterFactory,
    AdapterRegistry,
    available_adapters,
    default_registry,
    register_adapter,
    resolve_adapter,
    resolve_execution_adapter,
    resolve_full_adapter,
    resolve_market_data_adapter,
)
from tantra.adapters.secrets import FileSecretStore, SecretStore
from tantra.adapters.session import (
    DEFAULT_REFRESH_MARGIN_NS,
    Clock,
    SessionProvider,
    Token,
    TokenSession,
)

__all__ = [
    "DEFAULT_REFRESH_MARGIN_NS",
    "ENTRY_POINT_GROUP",
    "Adapter",
    "AdapterCapabilities",
    "AdapterError",
    "AdapterFactory",
    "AdapterFatalError",
    "AdapterNotFound",
    "AdapterRegistry",
    "BoundaryViolation",
    "BucketState",
    "Capability",
    "CapabilityError",
    "Clock",
    "DepthLevel",
    "ExecutionAdapter",
    "ExecutionClient",
    "FileBackedBucket",
    "FileSecretStore",
    "FullAdapterClient",
    "Funds",
    "Holding",
    "InMemoryBucket",
    "MarginReport",
    "MarketDataAdapter",
    "MarketDataClient",
    "MarketDepth",
    "OrderReport",
    "Product",
    "RateLimitExceeded",
    "RateLimiter",
    "RateLimiterRegistry",
    "ReportReduction",
    "RunMode",
    "SecretStore",
    "SessionError",
    "SessionExpired",
    "SessionInfo",
    "SessionProvider",
    "SharedBucketStore",
    "StreamCallback",
    "StreamEvent",
    "StreamMode",
    "Subscription",
    "Token",
    "TokenSession",
    "available_adapters",
    "capability_for_method",
    "default_registry",
    "find_boundary_violations",
    "format_violations",
    "reduce_order_report",
    "register_adapter",
    "resolve_adapter",
    "resolve_execution_adapter",
    "resolve_full_adapter",
    "resolve_market_data_adapter",
]
