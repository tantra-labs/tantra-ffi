"""Tests for the Arrow zero-copy data bridge (tantra.data)."""
from decimal import Decimal

import pytest

pyarrow = pytest.importorskip("pyarrow")
import pyarrow as pa

import tantra
from tantra import _tantra


def make_bars():
    iid = _tantra.InstrumentId("NSE", "RELIANCE")
    return [
        _tantra.Bar(
            iid, "2450.75", "2455.00", "2448.00", "2452.00", "1000",
            "2026-11-05T09:30:00+05:30",
        ),
        _tantra.Bar(
            iid, "2452.00", "2460.00", "2450.00", "2458.00", "1200",
            "2026-11-05T09:35:00+05:30",
        ),
    ]


def test_bars_to_stream_capsule_imports_as_arrow():
    capsule = _tantra.bars_to_stream(make_bars())
    assert _tantra.stream_capsule_name() == "arrow_array_stream"
    reader = pa.RecordBatchReader._import_from_c_capsule(capsule)
    table = reader.read_all()
    assert table.num_rows == 2
    assert table.column_names == ["symbol", "open", "high", "low", "close", "volume", "ts"]
    assert table.column("symbol").to_pylist() == ["NSE:RELIANCE", "NSE:RELIANCE"]
    assert table.column("open").to_pylist()[0] == Decimal("2450.75000000")


def test_bars_to_arrow_helper():
    reader = tantra.data.bars_to_arrow(make_bars())
    assert isinstance(reader, pa.RecordBatchReader)
    table = reader.read_all()
    assert table.num_rows == 2
    assert str(table.column("open")[0]) == "2450.75000000"


def test_ticks_to_arrow():
    iid = _tantra.InstrumentId("NSE", "RELIANCE")
    ticks = [
        _tantra.Tick.ltp(
            iid, "2450.75", "100",
            "2026-11-05T09:30:00+05:30", "2026-11-05T09:30:00+05:30",
        )
    ]
    reader = tantra.data.ticks_to_arrow(ticks)
    table = reader.read_all()
    assert table.num_rows == 1
    assert table.column_names == ["instrument", "kind", "price", "volume", "exchange_ts", "receive_ts"]
    assert table.column("kind").to_pylist() == ["ltp"]
