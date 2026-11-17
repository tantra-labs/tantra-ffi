# wheel surface (ex 0006): wire contract models (mirrors tantra_examples/_kernel/wire public API)
# stand-in closure for tantra-examples gap 0006

"""Screener and metric definition models for Tantra (ADR 006 / Pillar P2 / Core Plan 0004)."""

from __future__ import annotations

import math
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import (
    BeforeValidator,
    Field,
    SerializerFunctionWrapHandler,
    Strict,
    model_serializer,
    model_validator,
)

from tantra.wire.base import Str, _canonical, _Command


class ValueType(Enum):
    NUMBER = "NUMBER"
    STRING = "STRING"
    ENUM = "ENUM"
    BOOL = "BOOL"
    DATE = "DATE"
    MONEY = "MONEY"


class UnitType(Enum):
    PCT = "PCT"
    PRICE = "PRICE"
    RATIO = "RATIO"
    SHARES = "SHARES"
    CURRENCY = "CURRENCY"


class MetricPeriod(Enum):
    SNAPSHOT = "SNAPSHOT"
    TTM = "TTM"
    FY = "FY"
    FQ = "FQ"
    H1 = "H1"
    CURRENT = "CURRENT"
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


_METRIC_PERIOD_ALIASES: dict[str, str] = {
    "snapshot": "SNAPSHOT",
    "ttm": "TTM",
    "fy": "FY",
    "fq": "FQ",
    "h1": "H1",
    "halfyear": "H1",
    "current": "CURRENT",
    "intraday": "intraday",
    "daily": "daily",
    "d1": "daily",
    "1d": "daily",
    "weekly": "weekly",
    "w1": "weekly",
    "1w": "weekly",
    "monthly": "monthly",
    "1m": "monthly",
    "1mo": "monthly",
}


def _metric_period_wire() -> BeforeValidator:
    values = {m.value for m in MetricPeriod}

    def check(value: Any) -> Any:
        if isinstance(value, str):
            if value in values:
                return value
            mapped = _METRIC_PERIOD_ALIASES.get(value.lower())
            if mapped is not None:
                return mapped
            raise ValueError(f"{value!r} is not a valid MetricPeriod")
        return value

    return BeforeValidator(check)


class Timeframe(Enum):
    M1 = "1"
    M5 = "5"
    M15 = "15"
    M30 = "30"
    H1 = "60"
    H2 = "120"
    H4 = "240"
    D1 = "1D"
    W1 = "1W"
    MONTH1 = "1M"


class FilterOp(Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"
    LIKE = "like"
    HAS = "has"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"


def _filter_op_wire() -> BeforeValidator:
    """Accept canonical FilterOp values plus legacy ``"neq"`` alias for ``"ne"``."""
    values = {m.value for m in FilterOp}

    def check(value: Any) -> Any:
        if isinstance(value, str):
            if value == "neq":
                return FilterOp.NE.value
            if value not in values:
                raise ValueError(f"{value!r} is not a valid FilterOp")
        return value

    return BeforeValidator(check)


class MarketCapBucket(Enum):
    """Jurisdiction-neutral market capitalization bucket (mirrors Rust MarketCapBucket)."""

    LARGE = "large"
    MID = "mid"
    SMALL = "small"
    MICRO = "micro"


class RelativeStat(Enum):
    """Cross-sectional or relative return statistic computed over a RelativeTo scope."""

    MEDIAN = "median"
    MEAN = "mean"
    RETURN_DELTA = "return_delta"


MAX_CLASSIFICATION_LEN = 80
MAX_INDEX_ID_LEN = 40


def _validate_label(kind: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{kind} must be a string")
    if any((ch != "\t" and ord(ch) < 32) or ord(ch) == 127 for ch in value):
        raise ValueError(f"{kind} cannot contain control characters")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{kind} cannot be empty")
    if len(normalized) > MAX_CLASSIFICATION_LEN:
        raise ValueError(f"{kind} exceeds maximum length of {MAX_CLASSIFICATION_LEN} characters")
    return normalized


def _validate_sector(value: Any) -> str:
    return _validate_label("sector", value)


def _validate_industry(value: Any) -> str:
    return _validate_label("industry", value)


def _validate_index_id(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("index_id must be a string")
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("index_id cannot be empty")
    if len(trimmed) > MAX_INDEX_ID_LEN:
        raise ValueError(f"index_id exceeds maximum length of {MAX_INDEX_ID_LEN} characters")
    if not all(ch.isascii() and (ch.isalnum() or ch in "_-") for ch in trimmed):
        raise ValueError(
            f"invalid index_id {trimmed!r}: expected ASCII alphanumeric, '_' or '-'"
        )
    return trimmed.upper()


Sector = Annotated[str, BeforeValidator(_validate_sector)]
Industry = Annotated[str, BeforeValidator(_validate_industry)]
IndexId = Annotated[str, BeforeValidator(_validate_index_id)]

WireValueType = Annotated[ValueType, _canonical(ValueType)]
WireUnitType = Annotated[UnitType, _canonical(UnitType)]
WireMetricPeriod = Annotated[MetricPeriod, _metric_period_wire()]
WireTimeframe = Annotated[Timeframe, _canonical(Timeframe)]
WireFilterOp = Annotated[FilterOp, _filter_op_wire()]
WireMarketCapBucket = Annotated[MarketCapBucket, _canonical(MarketCapBucket)]
WireRelativeStat = Annotated[RelativeStat, _canonical(RelativeStat)]


class RelativeToIndex(_Command):
    """Benchmark index target for relative comparison (`{"index": "NIFTY500"}`)."""

    index: IndexId


RelativeTo = Literal["sector", "industry"] | RelativeToIndex


class ClassificationFilter(_Command):
    """Classification constraints optionally attached to a ScreenerFilterGroup."""

    sector: Sector | None = None
    industry: Industry | None = None
    cap_bucket: WireMarketCapBucket | None = None
    index: IndexId | None = None
    theme: Str | None = None


class MetricKeySpec(_Command):
    """Specification of a metric with optional period and timeframe dimensions."""

    key: Str
    period: WireMetricPeriod | None = None
    timeframe: WireTimeframe | None = None


def _omit_absent_dimensions(data: Any) -> Any:
    """Drop absent optional fields when unset, as Rust's ``skip_serializing_if`` does."""
    if isinstance(data, dict):
        for name in ("period", "timeframe", "relative_to", "relative_stat"):
            if name in data and data[name] is None:
                del data[name]
    return data


class MetricRef(_Command):
    """A metric used as the right-hand operand of a predicate.

    Makes metric-to-metric comparisons expressible on the wire, e.g.
    ``SMA50 crosses_above {"key": "SMA200"}``. ``key`` is the wire key, never a UI id.
    """

    key: Str
    period: WireMetricPeriod | None = None
    timeframe: WireTimeframe | None = None

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> Any:
        return _omit_absent_dimensions(handler(self))


class MetricDefinition(_Command):
    """Catalog definition of a metric.

    ``key`` is the wire key sent to the backend. ``ui_id`` (``uiId``) is the frontend
    column id and must never be emitted on the wire. ``aliases`` are natural-language
    phrases the NL layer (``tantra.screener.MetricCatalog.resolve``) maps to ``key``.
    """

    key: Str
    ui_id: Str | None = Field(default=None, alias="uiId")
    label: Str
    group: Str
    value_type: WireValueType = Field(alias="valueType")
    unit: WireUnitType | None = None
    description: Str | None = None
    has_period: Annotated[bool, Strict()] = Field(default=False, alias="hasPeriod")
    has_timeframe: Annotated[bool, Strict()] = Field(default=False, alias="hasTimeframe")
    default_period: Str | None = Field(default=None, alias="defaultPeriod")
    default_timeframe: Str | None = Field(default=None, alias="defaultTimeframe")
    filterable: Annotated[bool, Strict()] = True
    sortable: Annotated[bool, Strict()] = True
    source: Str | None = None
    aliases: list[Str] = Field(default_factory=list)


_ORDERING_OPS = frozenset({FilterOp.GT, FilterOp.GTE, FilterOp.LT, FilterOp.LTE})
_CROSSING_OPS = frozenset({FilterOp.CROSSES_ABOVE, FilterOp.CROSSES_BELOW})
_SET_OPS = frozenset({FilterOp.IN, FilterOp.NOT_IN})


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, Decimal):
        return value.is_finite()
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def _metric_ref(value: Any, op: FilterOp) -> MetricRef:
    if isinstance(value, MetricRef):
        return value
    if isinstance(value, dict):
        return MetricRef.model_validate(value)
    raise ValueError(f"{op.value}: value must be a finite number or a MetricRef object")


def _check_value(op: FilterOp, value: Any) -> Any:
    """Enforce the per-operator value contract (mirrors Rust ``check_predicate_value``).

    - ``crosses_above`` / ``crosses_below``: a finite number or a ``MetricRef``.
    - ``gt`` / ``gte`` / ``lt`` / ``lte``: a finite number, a string, or a ``MetricRef``.
    - ``between``: a list of exactly two finite numbers.
    - ``in`` / ``not_in``: a list.
    - other operators: unconstrained.
    """
    if op in _CROSSING_OPS:
        return value if _is_finite_number(value) else _metric_ref(value, op)
    if op in _ORDERING_OPS:
        if _is_finite_number(value) or isinstance(value, str):
            return value
        return _metric_ref(value, op)
    if op is FilterOp.BETWEEN:
        if not (isinstance(value, list) and len(value) == 2 and all(map(_is_finite_number, value))):
            raise ValueError("between: value must be a list of two finite numbers")
        return value
    if op in _SET_OPS:
        if not isinstance(value, list):
            raise ValueError(f"{op.value}: value must be a list")
        return value
    return value


PredicateValue = (
    Decimal
    | Annotated[int, Strict()]
    | Annotated[float, Strict()]
    | Str
    | Annotated[bool, Strict()]
    | None
    | MetricRef
    | list[Any]
    | dict[str, Any]
)
"""Typed predicate operand matching the supported scalar, Decimal, MetricRef, array, or object values."""


class ScreenerFilterPredicate(_Command):
    """Filter predicate for screening instruments.

    ``value`` must fit ``op``: ``crosses_above`` / ``crosses_below`` take a finite number
    or a ``MetricRef``; ``gt`` / ``gte`` / ``lt`` / ``lte`` a finite number, a string or a
    ``MetricRef``; ``between`` a list of two finite numbers; ``in`` / ``not_in`` a list;
    other operators any value. A ``MetricRef`` operand is parsed into a ``MetricRef``.
    """

    key: Str
    op: WireFilterOp
    value: PredicateValue
    period: WireMetricPeriod | None = None
    timeframe: WireTimeframe | None = None
    relative_to: RelativeTo | None = None
    relative_stat: WireRelativeStat | None = None

    @model_validator(mode="after")
    def _value_matches_op(self) -> ScreenerFilterPredicate:
        checked = _check_value(self.op, self.value)
        if checked is not self.value:
            # Frozen model: replace the raw dict with the parsed MetricRef.
            object.__setattr__(self, "value", checked)
        return self

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> Any:
        return _omit_absent_dimensions(handler(self))


class ScreenerFilterGroup(_Command):
    """Recursive boolean group of filter predicates and nested groups, with optional classification."""

    operator: Literal["AND", "OR"] = "AND"
    items: list[ScreenerFilterPredicate | ScreenerFilterGroup | dict[str, Any]] = Field(
        default_factory=list
    )
    classification: ClassificationFilter | None = None

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> Any:
        data = handler(self)
        if isinstance(data, dict) and data.get("classification") is None:
            data.pop("classification", None)
        return data


class ScreenerSortSpec(_Command):
    """Sorting specification for screener results."""

    key: Str
    dir: Literal["asc", "desc"] = "desc"
    period: WireMetricPeriod | None = None
    timeframe: WireTimeframe | None = None


class ScreenerScanRequest(_Command):
    """Request payload for POST /api/v1/screener/scan."""

    market: Str
    types: list[Str] = Field(default_factory=lambda: ["EQUITY"])
    primary_only: Annotated[bool, Strict()] = Field(default=True, alias="primaryOnly")
    column_set: Str | None = Field(default=None, alias="columnSet")
    columns: list[MetricKeySpec] = Field(default_factory=list)
    filters: ScreenerFilterGroup | None = None
    sort: ScreenerSortSpec | None = None
    range: tuple[int, int] = (0, 50)


class ScreenerRow(_Command):
    """A row of screened instrument results."""

    full_symbol: Str = Field(alias="fullSymbol")
    instrument_id: Str = Field(alias="instrumentId")
    name: Str
    values: dict[str, Any]


class ScreenerScanResponse(_Command):
    """Response payload for POST /api/v1/screener/scan."""

    total: Annotated[int, Strict()]
    range: tuple[int, int]
    columns: list[Str]
    rows: list[ScreenerRow]
