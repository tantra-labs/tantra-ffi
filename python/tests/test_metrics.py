"""Tests for the Decimal-canonical wheel `tantra.metrics` (T13 wheel port)."""

from decimal import Decimal

from tantra.bar import Bar
from tantra.instrument import InstrumentId
from tantra.metrics import Rsi, Sma, extract_metrics_from_bars


def _bars(n: int = 60) -> list[Bar]:
    """Simple monotonically rising OHLCV series with closes 100, 101, 102, ..."""
    bars = []
    for i in range(n):
        close = Decimal(100 + i)
        bars.append(
            Bar(
                instrument_id=InstrumentId("RELIANCE", "NSE"),
                ts=i,
                open=close - Decimal(1),
                high=close + Decimal(1),
                low=close - Decimal(2),
                close=close,
                volume=Decimal(1000),
            )
        )
    return bars


def test_extract_metrics_last_bar_values() -> None:
    bars = _bars()
    out = extract_metrics_from_bars(["close", "high", "low", "open", "volume"], bars)
    assert out["close"] == bars[-1].close
    assert out["high"] == bars[-1].high
    assert out["low"] == bars[-1].low
    assert out["open"] == bars[-1].open
    assert out["volume"] == bars[-1].volume
    assert isinstance(out["close"], Decimal)


def test_extract_metrics_sma5() -> None:
    bars = _bars()
    out = extract_metrics_from_bars(["sma5"], bars)
    expected = sum((b.close for b in bars[-5:]), Decimal(0)) / Decimal(5)
    assert out["sma5"] == expected
    assert isinstance(out["sma5"], Decimal)


def test_extract_metrics_rsi_in_unit_range() -> None:
    bars = _bars()  # 60 bars warms RSI(14)
    out = extract_metrics_from_bars(["rsi"], bars)
    val = out["rsi"]
    assert val is not None
    assert Decimal(0) <= val <= Decimal(100)


def test_extract_metrics_unknown_key_is_none() -> None:
    bars = _bars()
    assert extract_metrics_from_bars(["unknown"], bars) == {"unknown": None}


def test_sma_wrapper_warms_from_first_value() -> None:
    s = Sma(3)
    assert s.ready is False
    assert s.value is None
    # The wheel `_legacy.SMA` returns a running average from the first value, so
    # the wrapper is warm immediately (unlike the old kernel adapter that waited
    # for `period` values); assert the actual wheel behavior.
    first = s.update(Decimal(1))
    assert first == Decimal(1) / Decimal(3)
    assert s.update(Decimal(2)) == Decimal(1)  # (1+2)/3
    assert s.update(Decimal(3)) == Decimal(2)  # (1+2+3)/3
    assert s.ready is True
    assert s.value == Decimal(2)


def test_rsi_wrapper_warms_after_period() -> None:
    r = Rsi(14)
    out = [r.update(Decimal(100 + i)) for i in range(15)]
    assert out[0] is None
    assert out[13] is None
    # Strictly rising series -> RSI 100 once 14 deltas have accumulated.
    assert out[14] == Decimal(100)
    assert r.ready is True
    assert r.value == Decimal(100)
