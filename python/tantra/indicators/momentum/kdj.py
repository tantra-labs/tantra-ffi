# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Stochastic KDJ (momentum family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average.averages import make_ma
from tantra.types import to_decimal


@indicator(
    "kdj",
    "momentum",
    inputs=("high", "low", "close"),
    outputs=("k", "d", "j"),
    warmup=lambda s: s._h.maxlen + s._k.period + s._d.period - 2,
)
class Kdj(Indicator):
    """Stochastic KDJ: RSV over ``fastk`` bars, K = MA(RSV), D = MA(K), J = 3K - 2D.

    ``slowk_ma`` / ``slowd_ma`` choose the smoothing (see :func:`make_ma`; default SMA).
    RSV is 0 on a flat window (talib convention). ``update`` returns ``(k, d, j)``
    or ``None`` until warm.
    """

    def __init__(
        self,
        fastk: int = 9,
        slowk: int = 3,
        slowd: int = 3,
        slowk_ma: str = "sma",
        slowd_ma: str = "sma",
    ) -> None:
        self._h: deque[Decimal] = deque(maxlen=_check(fastk))
        self._l: deque[Decimal] = deque(maxlen=fastk)
        self._k = make_ma(slowk_ma, _check(slowk))
        self._d = make_ma(slowd_ma, _check(slowd))

    def update(
        self, high: Decimal, low: Decimal, close: Decimal
    ) -> tuple[Decimal, Decimal, Decimal] | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        self._h.append(high)
        self._l.append(low)
        if self._h.maxlen is None or len(self._h) < self._h.maxlen:
            return None
        hh, ll = max(self._h), min(self._l)
        k = self._k.update(
            (close - ll) / (hh - ll) * Decimal(100) if hh != ll else Decimal(0)
        )
        d = self._d.update(k) if k is not None else None
        if k is None or d is None:
            return None
        return k, d, 3 * k - 2 * d
