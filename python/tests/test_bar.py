import dataclasses

import pytest
from decimal import Decimal

from tantra.bar import Bar
from tantra.instrument import InstrumentId


def test_positional_construction_coerces_to_decimal() -> None:
    bar = Bar(
        InstrumentId("RELIANCE"),
        1710000000000000000,
        "100",
        "101",
        "99",
        "100.5",
        "1000",
    )
    assert bar.open == Decimal("100")
    assert bar.high == Decimal("101")
    assert bar.low == Decimal("99")
    assert bar.close == Decimal("100.5")
    assert bar.volume == Decimal("1000")
    assert isinstance(bar.open, Decimal)


def test_ts_stays_int_and_instrument_id_is_canonical() -> None:
    bar = Bar(
        InstrumentId("RELIANCE"),
        1710000000000000000,
        "100",
        "101",
        "99",
        "100.5",
        "1000",
    )
    assert bar.ts == 1710000000000000000
    assert isinstance(bar.ts, int)
    assert str(bar.instrument_id) == "RELIANCE.NSE"


def test_negative_price_rejected() -> None:
    with pytest.raises(ValueError):
        Bar(
            InstrumentId("RELIANCE"),
            1710000000000000000,
            "-1",
            "101",
            "99",
            "100.5",
            "1000",
        )


def test_negative_volume_rejected() -> None:
    with pytest.raises(ValueError):
        Bar(
            InstrumentId("RELIANCE"),
            1710000000000000000,
            "100",
            "101",
            "99",
            "100.5",
            "-1000",
        )


def test_high_below_low_rejected() -> None:
    with pytest.raises(ValueError):
        Bar(
            InstrumentId("RELIANCE"),
            1710000000000000000,
            "100",
            "98",
            "99",
            "100.5",
            "1000",
        )


def test_frozen_bar_rejects_mutation() -> None:
    bar = Bar(
        InstrumentId("RELIANCE"),
        1710000000000000000,
        "100",
        "101",
        "99",
        "100.5",
        "1000",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        bar.close = Decimal("101")


def test_value_equality_between_equivalent_bars() -> None:
    left = Bar(
        InstrumentId("RELIANCE"),
        1710000000000000000,
        "100",
        "101",
        "99",
        "100.5",
        "1000",
    )
    right = Bar(
        InstrumentId("RELIANCE"),
        1710000000000000000,
        Decimal("100"),
        Decimal("101"),
        Decimal("99"),
        Decimal("100.5"),
        Decimal("1000"),
    )
    assert left == right
    assert hash(left) == hash(right)
