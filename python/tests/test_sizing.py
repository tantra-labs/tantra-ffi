"""Tests for the wheel freeze-slicer (tantra-examples gap 0005 closure)."""

from decimal import Decimal

import pytest

from tantra.sizing import (
    OPTION_FREEZE_LIMIT_DEFAULT,
    Sizer,
    freeze_limit_qty,
    slice_order,
    verify_slices,
)


def test_slice_order_whole_and_remainder() -> None:
    assert slice_order(5000, 1800) == [1800, 1800, 1400]
    assert slice_order(3600, 1800) == [1800, 1800]
    assert slice_order(1800, 1800) == [1800]
    assert slice_order(100, 1800) == [100]
    # a total below the limit yields a single remainder slice
    assert slice_order(1500, 1800) == [1500]


def test_slice_order_errors() -> None:
    with pytest.raises(ValueError):
        slice_order(0, 1800)
    with pytest.raises(ValueError):
        slice_order(-10, 1800)
    with pytest.raises(ValueError):
        slice_order(100, 0)
    with pytest.raises(ValueError):
        slice_order(100, -1)


def test_verify_slices() -> None:
    verify_slices([1800, 1800, 1400], 1800)
    verify_slices([], 1800)
    with pytest.raises(ValueError, match="slice 2"):
        verify_slices([1800, 1800, 1801], 1800)


def test_freeze_limit_qty() -> None:
    assert OPTION_FREEZE_LIMIT_DEFAULT == 1800
    assert freeze_limit_qty() == 1800
    assert freeze_limit_qty("NIFTY", "NSE") == 1800


def test_sizer_staticmethods() -> None:
    assert Sizer.slice_order(5000, 1800) == [1800, 1800, 1400]
    Sizer.verify_slices([1800, 1800, 1400], 1800)
    assert Sizer.freeze_limit_qty() == 1800


def test_sizer_decimal_slicing_stays_exact() -> None:
    # Zero-floats invariant: slicing operates on exact integers/Decimals only.
    slices = slice_order(int(Decimal("3650")), 1800)
    assert slices == [1800, 1800, 50]
    assert all(isinstance(s, int) for s in slices)
