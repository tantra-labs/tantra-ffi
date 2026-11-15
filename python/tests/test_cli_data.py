"""Tests for the ``tantra.cli.data`` stream helpers (ex 0004 closure)."""

from __future__ import annotations

import io
import json

from tantra.cli.data import dumps, parse_symbols, read_symbols, to_stream


def test_parse_symbols_whitespace_and_commas() -> None:
    assert parse_symbols("RELIANCE, TCS  NTPC") == ["RELIANCE", "TCS", "NTPC"]
    assert parse_symbols("reliance tcs") == ["RELIANCE", "TCS"]
    assert parse_symbols("") == []
    assert parse_symbols(None) == []


def test_parse_symbols_json_payloads() -> None:
    assert parse_symbols('{"candidates": [{"symbol": "INFY"}, {"symbol": "TCS"}]}') == [
        "INFY",
        "TCS",
    ]
    assert parse_symbols('["RELIANCE", {"symbol": "HDFCBANK"}]') == [
        "RELIANCE",
        "HDFCBANK",
    ]
    assert parse_symbols('{"symbols": ["SBIN", "ITC"]}') == ["SBIN", "ITC"]
    assert parse_symbols("{not valid json} RELIANCE") == [
        "{NOT",
        "VALID",
        "JSON}",
        "RELIANCE",
    ]


def test_read_symbols_from_stream() -> None:
    assert read_symbols(io.StringIO("HDFCBANK ITC")) == ["HDFCBANK", "ITC"]
    assert read_symbols(io.StringIO("")) == []


def test_to_stream_formats() -> None:
    assert to_stream(["RELIANCE", "TCS"]) == "RELIANCE TCS"
    assert to_stream(["RELIANCE", "TCS"], fmt="plain") == "RELIANCE\nTCS"
    assert json.loads(to_stream(["RELIANCE"], fmt="json")) == {"symbols": ["RELIANCE"]}


def test_roundtrip_through_dumps_and_to_stream() -> None:
    assert parse_symbols(dumps({"symbols": ["RELIANCE", "TCS"]})) == ["RELIANCE", "TCS"]
    assert parse_symbols(to_stream(["RELIANCE", "TCS"])) == ["RELIANCE", "TCS"]
