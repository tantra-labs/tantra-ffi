# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Ichimoku cloud (trend family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.types import to_decimal


@indicator(
    "ichimoku",
    "trend",
    inputs=("high", "low"),
    outputs=("span_a", "span_b"),
    warmup=lambda s: max(s._n) + s._spans.maxlen - 1,
)
class Ichimoku(Indicator):
    """Ichimoku cloud as plotted on the current bar: spans computed ``displacement - 1``
    bars earlier (the standard convention, matching Jesse). ``update`` returns
    ``(span_a, span_b)`` or ``None`` until warm."""

    def __init__(
        self,
        tenkan: int = 9,
        kijun: int = 26,
        senkou_b: int = 52,
        displacement: int = 26,
    ) -> None:
        self._n = (_check(tenkan), _check(kijun), _check(senkou_b))
        self._h: deque[Decimal] = deque(maxlen=max(self._n))
        self._l: deque[Decimal] = deque(maxlen=max(self._n))
        self._spans: deque[tuple[Decimal, Decimal]] = deque(maxlen=_check(displacement))

    def _mid(self, n: int) -> Decimal:
        return (max(list(self._h)[-n:]) + min(list(self._l)[-n:])) / 2

    def update(self, high: Decimal, low: Decimal) -> tuple[Decimal, Decimal] | None:
        high, low = to_decimal(high), to_decimal(low)
        self._h.append(high)
        self._l.append(low)
        if self._h.maxlen is None or len(self._h) < self._h.maxlen:
            return None
        tenkan, kijun, senkou_b = (self._mid(n) for n in self._n)
        self._spans.append(((tenkan + kijun) / 2, senkou_b))
        return self._spans[0] if len(self._spans) == self._spans.maxlen else None
