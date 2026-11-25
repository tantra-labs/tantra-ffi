# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

# mirror: kernel-verbatim port (gap 0006)
from __future__ import annotations

from collections import deque
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.momentum.rsi import Rsi
from tantra.types import to_decimal


@indicator(
    "connors_rsi",
    "momentum",
    warmup=lambda s: max(s.rsi_length + 1, s.streak_length + 2, s.rank_length + 2),
)
class ConnorsRsi(Indicator):
    """Connors RSI (TradingView): mean of RSI(close, rsi_length), RSI(up/down streak, streak_length) and PercentRank(ROC(1), rank_length).

    Streak = consecutive closes up (+n) or down (-n), 0 on an unchanged close. PercentRank is
    100 * (count of the previous ``rank_length`` 1-bar ROC values <= current) / rank_length.
    """

    def __init__(
        self, rsi_length: int = 3, streak_length: int = 2, rank_length: int = 100
    ) -> None:
        self.rsi_length = _check(rsi_length)
        self.streak_length = _check(streak_length)
        self.rank_length = _check(rank_length)
        self._rsi, self._srsi = Rsi(rsi_length), Rsi(streak_length)
        self._prev: Decimal | None = None
        self._streak = 0
        self._rocs: deque[Decimal] = deque(maxlen=rank_length)

    def update(self, close: Decimal) -> Decimal | None:
        close = to_decimal(close)
        r = self._rsi.update(close)
        prev, self._prev = self._prev, close
        if prev is None:
            return None
        if close > prev:
            self._streak = self._streak + 1 if self._streak > 0 else 1
        elif close < prev:
            self._streak = self._streak - 1 if self._streak < 0 else -1
        else:
            self._streak = 0
        sr = self._srsi.update(to_decimal(self._streak))
        roc = Decimal(100) * (close - prev) / prev if prev != 0 else Decimal(0)
        rank = None
        if len(self._rocs) == self.rank_length:
            rank = (
                Decimal(100) * sum(1 for v in self._rocs if v <= roc) / self.rank_length
            )
        self._rocs.append(roc)
        if r is None or sr is None or rank is None:
            return None
        return (r + sr + rank) / 3
