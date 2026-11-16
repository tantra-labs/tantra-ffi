"""Tests for the wheel `tantra.calendar` (T13 IST trading calendar surface)."""

import datetime as dt

from tantra.calendar import IST, NseCalendar, SessionWindow, ist_midnight_ns


def test_ist_midnight_ns() -> None:
    date = dt.date(2026, 11, 15)
    expected = (
        int(dt.datetime.combine(date, dt.time.min, tzinfo=IST).timestamp())
        * 1_000_000_000
    )
    assert ist_midnight_ns(date) == expected


def test_saturday_not_trading_day() -> None:
    cal = NseCalendar()
    assert not cal.is_trading_day(dt.date(2026, 11, 14))  # Saturday


def test_monday_holiday_not_trading_day() -> None:
    holiday = dt.date(2026, 11, 9)  # Monday
    cal = NseCalendar(holidays=[holiday])
    assert cal.is_holiday(holiday)
    assert not cal.is_trading_day(holiday)


def test_plain_monday_is_trading_day() -> None:
    cal = NseCalendar()
    assert cal.is_trading_day(dt.date(2026, 11, 9))  # Monday


def test_next_trading_day_skips_weekend() -> None:
    cal = NseCalendar()
    # Friday 2026-11-13 -> Monday 2026-11-16 (skips Sat/Sun)
    assert cal.next_trading_day(dt.date(2026, 11, 13)) == dt.date(2026, 11, 16)


def test_next_trading_day_skips_holiday() -> None:
    cal = NseCalendar(holidays=[dt.date(2026, 11, 16)])  # Monday
    assert cal.next_trading_day(dt.date(2026, 11, 13)) == dt.date(2026, 11, 17)


def test_prev_trading_day_skips_weekend() -> None:
    cal = NseCalendar()
    # Monday 2026-11-16 -> Friday 2026-11-13 (skips Sat/Sun)
    assert cal.prev_trading_day(dt.date(2026, 11, 16)) == dt.date(2026, 11, 13)


def test_trading_days_between() -> None:
    cal = NseCalendar()
    start = dt.date(2026, 11, 9)  # Monday
    end = dt.date(2026, 11, 13)  # Friday
    assert cal.trading_days_between(start, end) == [
        dt.date(2026, 11, 9),
        dt.date(2026, 11, 10),
        dt.date(2026, 11, 11),
        dt.date(2026, 11, 12),
        dt.date(2026, 11, 13),
    ]


def test_trading_days_between_excludes_holiday() -> None:
    cal = NseCalendar(holidays=[dt.date(2026, 11, 11)])
    days = cal.trading_days_between(dt.date(2026, 11, 9), dt.date(2026, 11, 13))
    assert len(days) == 4
    assert dt.date(2026, 11, 11) not in days


def test_trading_days_between_reversed_start_end() -> None:
    cal = NseCalendar()
    assert cal.trading_days_between(dt.date(2026, 11, 13), dt.date(2026, 11, 9)) == []


def test_sessions_before_chronological() -> None:
    cal = NseCalendar()
    # asof Saturday 2026-11-14 -> last 3 sessions: Fri 13, Thu 12, Wed 11
    assert cal.sessions_before(dt.date(2026, 11, 14), 3) == [
        dt.date(2026, 11, 11),
        dt.date(2026, 11, 12),
        dt.date(2026, 11, 13),
    ]


def test_sessions_before_includes_asof_when_trading_day() -> None:
    cal = NseCalendar()
    assert cal.sessions_before(dt.date(2026, 11, 13), 2) == [
        dt.date(2026, 11, 12),
        dt.date(2026, 11, 13),
    ]


def test_sessions_before_non_positive_count() -> None:
    cal = NseCalendar()
    assert cal.sessions_before(dt.date(2026, 11, 13), 0) == []


def test_session_window_default_contains() -> None:
    win = SessionWindow()
    assert win.contains(dt.time(9, 15))
    assert not win.contains(dt.time(15, 30))
    assert win.contains(dt.time(12, 0))
