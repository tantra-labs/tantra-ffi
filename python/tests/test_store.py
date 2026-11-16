"""Tests for tantra.coverage interval algebra and tantra.store Parquet bar store (ex 0006)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tantra.bar import Bar
from tantra.coverage import (
    CoverageRecord,
    CoverageStatus,
    DateInterval,
    merge_intervals,
    plan_gaps,
    subtract_intervals,
)
from tantra.instrument import InstrumentId
from tantra.store import (
    ParquetBarStore,
    _utc_midnight_ns,
    _validate_bar,
    find_data_root,
)


# --- helpers ------------------------------------------------------------------


def _bar(iid: InstrumentId, day: date, close: str = "100.5") -> Bar:
    return Bar(iid, _utc_midnight_ns(day), "100", "101", "99", close, "1000")


def _raw_bar(**overrides: object) -> Bar:
    """Build a Bar without Bar.__post_init__ validation (tests _validate_bar)."""
    fields: dict[str, object] = {
        "instrument_id": InstrumentId("RELIANCE"),
        "ts": 1710000000000000000,
        "open": Decimal("100"),
        "high": Decimal("101"),
        "low": Decimal("99"),
        "close": Decimal("100.5"),
        "volume": Decimal("1000"),
    }
    fields.update(overrides)
    bar = object.__new__(Bar)
    for name, value in fields.items():
        object.__setattr__(bar, name, value)
    return bar


# --- coverage algebra ---------------------------------------------------------


def test_empty_interval() -> None:
    assert DateInterval(date(2024, 1, 1), date(2024, 1, 1)).is_empty()
    assert not DateInterval(date(2024, 1, 1), date(2024, 1, 2)).is_empty()


def test_interval_start_after_end_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be after"):
        DateInterval(date(2024, 1, 2), date(2024, 1, 1))


def test_merge_intervals_merges_adjacent_and_overlapping() -> None:
    intervals = [
        DateInterval(date(2024, 1, 1), date(2024, 1, 10)),
        DateInterval(date(2024, 1, 10), date(2024, 1, 20)),  # adjacent
        DateInterval(date(2024, 1, 15), date(2024, 1, 25)),  # overlapping
        DateInterval(date(2024, 2, 1), date(2024, 2, 5)),
    ]
    assert merge_intervals(intervals) == [
        DateInterval(date(2024, 1, 1), date(2024, 1, 25)),
        DateInterval(date(2024, 2, 1), date(2024, 2, 5)),
    ]
    assert merge_intervals([]) == []


def test_subtract_intervals_computes_gaps() -> None:
    required = DateInterval(date(2024, 1, 1), date(2024, 1, 31))
    covered = [
        DateInterval(date(2024, 1, 5), date(2024, 1, 10)),
        DateInterval(date(2024, 1, 20), date(2024, 1, 25)),
    ]
    assert subtract_intervals(required, covered) == [
        DateInterval(date(2024, 1, 1), date(2024, 1, 5)),
        DateInterval(date(2024, 1, 10), date(2024, 1, 20)),
        DateInterval(date(2024, 1, 25), date(2024, 1, 31)),
    ]


def test_plan_gaps_keeps_distant_gaps_separate() -> None:
    required = DateInterval(date(2024, 1, 1), date(2024, 2, 1))
    covered = [DateInterval(date(2024, 1, 10), date(2024, 1, 20))]
    assert plan_gaps(required, covered, max_gap_days=3) == [
        DateInterval(date(2024, 1, 1), date(2024, 1, 10)),
        DateInterval(date(2024, 1, 20), date(2024, 2, 1)),
    ]


def test_plan_gaps_merges_close_gaps() -> None:
    required = DateInterval(date(2024, 1, 1), date(2024, 1, 15))
    covered = [DateInterval(date(2024, 1, 5), date(2024, 1, 7))]
    assert plan_gaps(required, covered, max_gap_days=5) == [
        DateInterval(date(2024, 1, 1), date(2024, 1, 15))
    ]


def test_coverage_record_field_defaults() -> None:
    record = CoverageRecord(
        exchange="NSE",
        symbol="RELIANCE",
        timeframe="1D",
        interval=DateInterval(date(2024, 1, 1), date(2024, 1, 2)),
        status=CoverageStatus.FINAL,
        source="test",
    )
    assert record.row_count == 0
    assert record.checksum is None
    assert record.fetched_at_ns == 0


# --- find_data_root -----------------------------------------------------------


def test_find_data_root_uses_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("TANTRA_DATA_DIR", str(tmp_path))
    assert find_data_root() == tmp_path.resolve()


def test_find_data_root_resolves_tantra_data_sibling(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.delenv("TANTRA_DATA_DIR", raising=False)
    (tmp_path / "tantra-data" / "data").mkdir(parents=True)
    start = tmp_path / "some" / "dir"
    start.mkdir(parents=True)
    assert find_data_root(start) == (tmp_path / "tantra-data" / "data").resolve()


def test_find_data_root_falls_back_to_start_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.delenv("TANTRA_DATA_DIR", raising=False)
    assert find_data_root(tmp_path) == (tmp_path / "data").resolve()


# --- ParquetBarStore round-trip ------------------------------------------------


def test_store_round_trip(tmp_path) -> None:
    store = ParquetBarStore(tmp_path)
    iid = InstrumentId("RELIANCE", "NSE")
    interval = DateInterval(date(2024, 1, 1), date(2024, 1, 3))
    record = CoverageRecord(
        exchange="NSE",
        symbol="RELIANCE",
        timeframe="1D",
        interval=interval,
        status=CoverageStatus.FINAL,
        source="test",
        row_count=2,
        checksum="abc",
        fetched_at_ns=1,
    )
    b1 = _bar(iid, date(2024, 1, 1))
    b2 = _bar(iid, date(2024, 1, 2))
    store.append(record, [b1, b2])

    bars = store.read(iid, "1D", interval)
    assert bars == [b1, b2]
    assert [b.ts for b in bars] == sorted(b.ts for b in bars)
    assert all(isinstance(b.open, Decimal) for b in bars)

    # decimal128(38, 10) canonical schema was written
    fpath = store._file_path(iid, "1D", 2024)
    written = pq.read_table(fpath)
    assert written.column("close").type == pa.decimal128(38, 10)

    cov = store.coverage(iid, "1D")
    assert cov == [record]


def test_store_appending_overlapping_interval_merges_ledger(tmp_path) -> None:
    store = ParquetBarStore(tmp_path)
    iid = InstrumentId("RELIANCE", "NSE")
    store.append(
        CoverageRecord(
            exchange="NSE",
            symbol="RELIANCE",
            timeframe="1D",
            interval=DateInterval(date(2024, 1, 1), date(2024, 1, 3)),
            status=CoverageStatus.FINAL,
            source="test",
            row_count=2,
            checksum=None,
            fetched_at_ns=1,
        ),
        [_bar(iid, date(2024, 1, 1)), _bar(iid, date(2024, 1, 2))],
    )
    store.append(
        CoverageRecord(
            exchange="NSE",
            symbol="RELIANCE",
            timeframe="1D",
            interval=DateInterval(date(2024, 1, 3), date(2024, 1, 5)),
            status=CoverageStatus.FINAL,
            source="test",
            row_count=2,
            checksum=None,
            fetched_at_ns=2,
        ),
        [_bar(iid, date(2024, 1, 3)), _bar(iid, date(2024, 1, 4))],
    )

    bars = store.read(iid, "1D", DateInterval(date(2024, 1, 1), date(2024, 1, 5)))
    assert len(bars) == 4
    assert bars[0].ts == _utc_midnight_ns(date(2024, 1, 1))
    assert bars[3].ts == _utc_midnight_ns(date(2024, 1, 4))

    cov = store.coverage(iid, "1D")
    assert len(cov) == 1
    assert cov[0].interval == DateInterval(date(2024, 1, 1), date(2024, 1, 5))
    assert cov[0].row_count == 4
    assert cov[0].fetched_at_ns == 2


def test_store_decimal_fidelity(tmp_path) -> None:
    store = ParquetBarStore(tmp_path)
    iid = InstrumentId("RELIANCE", "NSE")
    bar = Bar(
        iid,
        _utc_midnight_ns(date(2024, 1, 1)),
        "2450.00",
        "2460.00",
        "2448.00",
        "2450.55",
        "1000",
    )
    store.append(
        CoverageRecord(
            exchange="NSE",
            symbol="RELIANCE",
            timeframe="1D",
            interval=DateInterval(date(2024, 1, 1), date(2024, 1, 2)),
            status=CoverageStatus.FINAL,
            source="test",
            row_count=1,
        ),
        [bar],
    )
    bars = store.read(iid, "1D", DateInterval(date(2024, 1, 1), date(2024, 1, 2)))
    assert len(bars) == 1
    assert bars[0].close == Decimal("2450.55")


def test_store_reads_legacy_float64_parquet_as_decimal(tmp_path) -> None:
    store = ParquetBarStore(tmp_path)
    iid = InstrumentId("RELIANCE", "NSE")
    fpath = store._file_path(iid, "1D", 2024)
    fpath.parent.mkdir(parents=True, exist_ok=True)
    ts = _utc_midnight_ns(date(2024, 1, 1))
    legacy_schema = pa.schema(
        [
            ("ts", pa.int64()),
            ("open", pa.float64()),
            ("high", pa.float64()),
            ("low", pa.float64()),
            ("close", pa.float64()),
            ("volume", pa.float64()),
        ]
    )
    table = pa.Table.from_arrays(
        [
            pa.array([ts], type=pa.int64()),
            pa.array([100.0], type=pa.float64()),
            pa.array([101.0], type=pa.float64()),
            pa.array([99.0], type=pa.float64()),
            pa.array([2450.55], type=pa.float64()),
            pa.array([1000.0], type=pa.float64()),
        ],
        schema=legacy_schema,
    )
    pq.write_table(table, fpath)

    bars = store.read(iid, "1D", DateInterval(date(2024, 1, 1), date(2024, 1, 2)))
    assert len(bars) == 1
    assert bars[0].close == Decimal("2450.55")
    assert bars[0].open == Decimal("100")
    assert bars[0].volume == Decimal("1000")


# --- _validate_bar -------------------------------------------------------------


def test_validate_bar_rejects_low_above_high() -> None:
    with pytest.raises(ValueError, match="high must be >= low"):
        _validate_bar(_raw_bar(low=Decimal("102"), high=Decimal("101")))


def test_validate_bar_rejects_non_finite_close() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        _validate_bar(_raw_bar(close=Decimal("Infinity")))


def test_validate_bar_rejects_negative_volume() -> None:
    with pytest.raises(ValueError, match="volume must be >= 0"):
        _validate_bar(_raw_bar(volume=Decimal("-1")))


def test_validate_bar_accepts_valid_bar() -> None:
    assert _validate_bar(_raw_bar()) is True
