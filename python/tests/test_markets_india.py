"""Tests for the wheel India market-pack surfaces (``tantra.markets.india``)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from tantra.markets.india import (
    INDIA_EXCHANGES,
    INSTRUMENT_KINDS,
    CostBreakdown,
    Segment,
    nse_equity_delivery_breakdown,
    nse_equity_delivery_cost,
    nse_equity_intraday_cost,
    nse_equity_settlement_days,
    settlement_days_for,
    to_iso_date,
)
from tantra.order import OrderSide


def test_delivery_buy_components_exact() -> None:
    breakdown = nse_equity_delivery_breakdown(OrderSide.BUY, Decimal(10), Decimal(100))
    assert breakdown == CostBreakdown(
        Decimal("0.3000"),
        Decimal("0.0000"),
        Decimal("0.0297"),
        Decimal("0.0010"),
        Decimal("0.0010"),
        Decimal("0.1500"),
        Decimal("0.0597"),
    )
    assert breakdown.total == Decimal("0.5414")
    assert nse_equity_delivery_cost(
        OrderSide.BUY, Decimal(10), Decimal(100)
    ) == Decimal("0.5414")


def test_delivery_sell_cost_exact() -> None:
    # STT (0.10% on sell = 1.0) replaces stamp duty (buy-only).
    assert nse_equity_delivery_cost(
        OrderSide.SELL, Decimal(10), Decimal(100)
    ) == Decimal("1.3914")


def test_intraday_buy_cost_exact() -> None:
    # Intraday stamp 0.003% = 0.03; STT only on sell.
    assert nse_equity_intraday_cost(
        OrderSide.BUY, Decimal(10), Decimal(100)
    ) == Decimal("0.4214")


def test_zero_notional_is_free() -> None:
    assert nse_equity_delivery_cost(OrderSide.BUY, Decimal(0), Decimal(100)) == Decimal(
        0
    )
    assert nse_equity_delivery_cost(OrderSide.SELL, Decimal(10), Decimal(0)) == Decimal(
        0
    )


def test_segment_dispatch() -> None:
    assert nse_equity_delivery_cost(
        OrderSide.BUY, Decimal(10), Decimal(100)
    ) == Decimal("0.5414")
    assert nse_equity_intraday_cost(
        OrderSide.BUY, Decimal(10), Decimal(100)
    ) == Decimal("0.4214")


def test_settlement_days_before_and_after_cutover() -> None:
    assert settlement_days_for("NSE", kind="equity", as_of="2023-01-26") == 2
    assert settlement_days_for("NSE", kind="equity", as_of="2023-01-27") == 1
    assert settlement_days_for("bse", as_of=dt.date(2022, 12, 1)) == 2
    assert nse_equity_settlement_days(dt.date(2023, 1, 27)) == 1
    assert nse_equity_settlement_days(dt.datetime(2023, 1, 27, 10, 30)) == 1


def test_settlement_days_today_and_foreign() -> None:
    assert nse_equity_settlement_days() == 1  # today's cycle is T+1
    assert settlement_days_for("NSE") == 1
    assert settlement_days_for("NYSE") == 1


def test_settlement_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unknown instrument kind"):
        settlement_days_for("NSE", kind="crypto")


def test_to_iso_date() -> None:
    assert to_iso_date("2023-01-27") == "2023-01-27"
    assert to_iso_date(dt.date(2023, 1, 27)) == "2023-01-27"
    assert to_iso_date(dt.datetime(2023, 1, 27, 9, 15)) == "2023-01-27"


def test_constants() -> None:
    assert INDIA_EXCHANGES == frozenset({"NSE", "BSE"})
    assert "equity" in INSTRUMENT_KINDS
    assert "option" in INSTRUMENT_KINDS
    assert list(Segment) == [
        Segment.EQUITY_DELIVERY,
        Segment.EQUITY_INTRADAY,
        Segment.FNO_FUTURES,
        Segment.FNO_OPTIONS,
    ]
