"""Tests for the ``tantra.display`` wheel surface (ex 0004 closure)."""

from __future__ import annotations

import io
from decimal import Decimal

import pytest
from tantra.display import (
    Column,
    OutputFormat,
    format_cell,
    format_money,
    format_percent,
    format_timestamp_ns,
    grade_style_fn,
    pnl_style_fn,
    render,
    render_kv,
    render_table,
)


def test_format_money_indian_grouping() -> None:
    assert format_money(1234567.5) == "₹12,34,567.50"
    assert format_money(Decimal("1234.5")) == "₹1,234.50"
    assert format_money(50) == "₹50.00"
    assert format_money(-50) == "-₹50.00"
    assert format_money(Decimal(0)) == "₹0.00"
    assert format_money(Decimal("99.99")) == "₹99.99"
    assert format_money("not a number") == "not a number"


def test_format_money_non_inr_currency() -> None:
    assert format_money(1234.5, currency="USD") == "$1,234.50"


def test_format_percent_explicit_sign() -> None:
    assert format_percent(12.5) == "+12.50%"
    assert format_percent(-3.25) == "-3.25%"
    assert format_percent(0) == "+0.00%"
    assert format_percent("n/a") == "n/a"


def test_format_cell() -> None:
    assert format_cell(None) == "-"
    assert format_cell(1.5) == "1.50"
    assert format_cell(2) == "2"
    assert format_cell("x") == "x"


def test_format_timestamp_ns() -> None:
    assert format_timestamp_ns(0) == "?"
    assert format_timestamp_ns(-5) == "?"
    assert format_timestamp_ns(1_700_000_000_000_000_000) == "2023-11-14"


def test_pnl_style_fn() -> None:
    assert pnl_style_fn(5) == "green"
    assert pnl_style_fn(0) == "green"
    assert pnl_style_fn(-1) == "red"
    assert pnl_style_fn(None) is None


def test_grade_style_fn() -> None:
    assert grade_style_fn("A+") == "bold green"
    assert grade_style_fn("A") == "green"
    assert grade_style_fn("b") == "yellow"
    assert grade_style_fn("C") == "dim"
    assert grade_style_fn(None) == "dim"


def test_column_construction() -> None:
    col = Column("sym", header="Symbol", align="right", style="bold cyan")
    assert col.key == "sym"
    assert col.title == "Symbol"
    assert col.align == "right"
    assert col.style == "bold cyan"
    assert Column("sym").title == "sym"


def test_output_format_parse() -> None:
    assert OutputFormat.parse("JSON") is OutputFormat.JSON
    assert OutputFormat.parse(OutputFormat.CSV) is OutputFormat.CSV
    with pytest.raises(ValueError, match="unknown output format"):
        OutputFormat.parse("xml")


def test_render_json() -> None:
    out = io.StringIO()
    rows = [{"sym": "RELIANCE", "score": 1.5}]
    render(rows, ["sym", "score"], OutputFormat.JSON, out=out)
    text = out.getvalue()
    assert '"sym": "RELIANCE"' in text
    assert '"score": 1.5' in text


def test_render_csv() -> None:
    out = io.StringIO()
    rows = [{"sym": "RELIANCE", "score": 1.5}]
    render(rows, ["sym", "score"], OutputFormat.CSV, out=out)
    text = out.getvalue()
    assert text.splitlines() == ["sym,score", "RELIANCE,1.5"]


def test_render_table_plain() -> None:
    out = io.StringIO()
    rows = [{"sym": "RELIANCE", "score": 1.5}, {"sym": "TCS", "score": 2.5}]
    render_table(rows, ["sym", "score"], plain=True, out=out)
    text = out.getvalue()
    assert "RELIANCE" in text
    assert "1.50" in text
    assert "TCS" in text


def test_render_table_rich() -> None:
    out = io.StringIO()
    rows = [{"sym": "RELIANCE", "score": 1.5}]
    render_table(rows, ["sym", "score"], out=out)
    text = out.getvalue()
    assert "RELIANCE" in text
    assert "1.50" in text


def test_render_kv() -> None:
    out = io.StringIO()
    render_kv({"sym": "RELIANCE", "score": 1.5}, title="KV", out=out)
    text = out.getvalue()
    assert "RELIANCE" in text
    assert "1.50" in text
