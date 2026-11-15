# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Money flow index."""
# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._rolling import RollingSum
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator(
    "money_flow_index",
    "volume",
    inputs=("high", "low", "close", "volume"),
    warmup=lambda s: s.period + 1,
)
class MoneyFlowIndex(Indicator):
    """Money flow index (TradingView): raw flow = hlc3*volume, split into positive/negative by the
    hlc3 change; 100 - 100/(1+pos/neg) over ``period`` bars. Needs a previous bar, so the first value
    appears after ``period + 1`` bars. Convention: no flow at all -> 50; only positive flow -> 100."""

    def __init__(self, period: int = 14) -> None:
        self.period = _check(period)
        self._prev: Decimal | None = None
        self._pos = RollingSum(period)
        self._neg = RollingSum(period)

    def update(self, high: Decimal, low: Decimal, close: Decimal, volume: Decimal) -> Decimal | None:
        high, low, close, volume = (
            to_decimal(high),
            to_decimal(low),
            to_decimal(close),
            to_decimal(volume),
        )
        tp = (high + low + close) / 3
        prev, self._prev = self._prev, tp
        if prev is None:
            return None
        raw = tp * volume
        pos = self._pos.update(raw if tp > prev else Decimal("0"))
        neg = self._neg.update(raw if tp < prev else Decimal("0"))
        if pos is None or neg is None:
            return None
        if neg == 0:
            return Decimal("50") if pos == 0 else Decimal("100")
        return Decimal("100") - Decimal("100") / (Decimal("1") + pos / neg)
