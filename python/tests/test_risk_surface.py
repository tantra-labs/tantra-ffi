"""Tests for the pure-Python `tantra.risk` surface (T13 wheel port).

The compiled engine is covered by `test_risk.py`; this file exercises the
promoted pure-Python pre-trade checks and the lazy-native fallback.
"""

from decimal import Decimal

import pytest
import tantra
import tantra.risk
from tantra.risk import (
    OrderRejected,
    RiskRefusal,
    RiskRefused,
    _native_attr,
    check_order,
    check_state,
    limits_from_config,
)


class _Side:
    def __init__(self, value: str) -> None:
        self.value = value


def test_native_attr_schema_version() -> None:
    assert _native_attr("SCHEMA_VERSION") == tantra.SCHEMA_VERSION


def test_native_attr_compiled_engine_raises() -> None:
    with pytest.raises(RuntimeError):
        _native_attr("RiskEngine")


def test_lazy_native_import_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError):
        from tantra.risk import RiskLimits  # noqa: F401


def test_refusal_dataclasses_constructible() -> None:
    refusal = RiskRefusal("code", "rule", {"k": "v"})
    assert refusal.code == "code"
    assert refusal.rule == "rule"
    assert refusal.context == {"k": "v"}
    refused = RiskRefused("order-1", 123, "code", "rule", {})
    assert refused.order_id == "order-1"
    assert refused.ts == 123
    rejected = OrderRejected("order-1", 123, "ErrorCode::RiskRefused")
    assert rejected.reason == "ErrorCode::RiskRefused"


def test_check_state_halted_refuses_everything() -> None:
    refusal = check_state(_Side("BUY"), Decimal(1), Decimal(1), "halted")
    assert refusal is not None
    assert refusal.code == "risk_trading_halted"
    assert check_state(_Side("SELL"), Decimal(1), Decimal(1), "halted") is not None


def test_check_state_active_approves() -> None:
    assert check_state(_Side("BUY"), Decimal(2), Decimal(1), "active") is None
    assert check_state(_Side("SELL"), Decimal(2), Decimal(1), "active") is None


def test_check_state_reducing_refuses_opening_buy() -> None:
    # long +1, BUY 2 -> after +3 outside [0, +1] -> refused
    refusal = check_state(_Side("BUY"), Decimal(2), Decimal(1), "reducing")
    assert refusal is not None
    assert refusal.code == "risk_reduce_only_violation"


def test_check_state_reducing_refuses_overselling() -> None:
    # long +1, SELL 2 -> after -1 outside [0, +1] -> refused
    assert check_state(_Side("SELL"), Decimal(2), Decimal(1), "reducing") is not None


def test_check_state_reducing_approves_closing_sell() -> None:
    # long +1, SELL 1 -> after 0 in [0, +1] -> approved
    assert check_state(_Side("SELL"), Decimal(1), Decimal(1), "reducing") is None


def test_check_state_reducing_approves_zero_quantity_buy() -> None:
    # long +1, BUY 0 -> after +1 in [0, +1] -> approved
    assert check_state(_Side("BUY"), Decimal(0), Decimal(1), "reducing") is None


def test_check_state_reducing_refuses_flat_position() -> None:
    # flat +0 refuses everything while reducing
    assert check_state(_Side("BUY"), Decimal(1), Decimal(0), "reducing") is not None
    assert check_state(_Side("SELL"), Decimal(1), Decimal(0), "reducing") is not None


class _StubLimits:
    """Stand-in for the absent compiled RiskLimits, monkeypatched into _native_attr."""

    known = frozenset({"max_notional", "order_rate"})

    def __init__(self, table: dict) -> None:
        self.table = table

    @classmethod
    def from_dict(cls, table: dict) -> "_StubLimits":
        for key in table:
            if key not in cls.known:
                raise ValueError(f"unknown risk key: {key}")
        return cls(table)


def test_limits_from_config_passes_through_known_keys(monkeypatch) -> None:
    monkeypatch.setattr(tantra.risk, "_native_attr", lambda name: _StubLimits)
    limits = limits_from_config({"risk": {"max_notional": "5000"}})
    assert limits.table == {"max_notional": "5000"}


def test_limits_from_config_refuses_unknown_keys(monkeypatch) -> None:
    monkeypatch.setattr(tantra.risk, "_native_attr", lambda name: _StubLimits)
    with pytest.raises(ValueError):
        limits_from_config({"risk": {"unknown_key": 1}})


def test_limits_from_config_absent_table_is_empty(monkeypatch) -> None:
    monkeypatch.setattr(tantra.risk, "_native_attr", lambda name: _StubLimits)
    limits = limits_from_config({})
    assert limits.table == {}


def test_limits_from_config_without_stub_raises() -> None:
    with pytest.raises(RuntimeError):
        limits_from_config({"risk": {"max_notional": "5000"}})


def test_check_order_raises_no_compiled_engine() -> None:
    with pytest.raises(RuntimeError) as excinfo:
        check_order(object())
    assert "no compiled" in str(excinfo.value)
