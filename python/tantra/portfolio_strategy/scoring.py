# wheel surface (ex 0006): Decimal-canonical kernel-parity portfolio strategy parts
# (mirrors tantra_examples/_kernel/portfolio_strategy/scoring public API; scores are Decimal)

"""Ready-made scores for ``TopN``: ``score(instrument_id, view) -> Decimal | None``.

Higher is better. ``None`` means "cannot score yet" (insufficient or invalid history) and
makes ``TopN`` drop the instrument. Each score carries a ``lookback`` attribute (closes
required) so factories can size the history buffer.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from tantra.instrument import InstrumentId
from tantra.portfolio_strategy.stats import return_stdev
from tantra.portfolio_strategy.view import MarketView

Score = Callable[[InstrumentId, MarketView], "Decimal | None"]


def _check(lookback: int) -> None:
    if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback < 2:
        raise ValueError(f"lookback must be an int >= 2, got {lookback!r}")


@dataclass(frozen=True, slots=True)
class _Momentum:
    lookback: int

    def __call__(self, instrument_id: InstrumentId, view: MarketView) -> Decimal | None:
        closes = view.recent_closes(instrument_id)
        if len(closes) < self.lookback:
            return None
        first, last = closes[-self.lookback], closes[-1]
        if not (first.is_finite() and last.is_finite()) or first <= 0:
            return None
        return last / first - Decimal(1)


@dataclass(frozen=True, slots=True)
class _LowVol:
    lookback: int

    def __call__(self, instrument_id: InstrumentId, view: MarketView) -> Decimal | None:
        vol = return_stdev(view, instrument_id, self.lookback)
        return None if vol is None else -vol


@dataclass(frozen=True, slots=True)
class _MeanReversion:
    lookback: int

    def __call__(self, instrument_id: InstrumentId, view: MarketView) -> Decimal | None:
        closes = view.recent_closes(instrument_id)
        if len(closes) < self.lookback:
            return None
        window = closes[-self.lookback :]
        if not all(c.is_finite() for c in window):
            return None
        n = len(window)
        mean = sum(window, Decimal(0)) / n
        # Population stdev in exact Decimal (no `statistics` module).
        variance = sum(((c - mean) ** 2 for c in window), Decimal(0)) / n
        stdev = variance.sqrt()
        if stdev == 0:
            return Decimal(0)
        # Lower z-score (more oversold) ranks higher
        z = (window[-1] - mean) / stdev
        return -z


def momentum(lookback: int) -> Score:
    """Total return from the first to the last of the last ``lookback`` closes.

    ``None`` if fewer than ``lookback`` closes or the first close is <= 0. ``lookback >= 2``.
    """
    _check(lookback)
    return _Momentum(lookback)


def low_volatility(lookback: int) -> Score:
    """Negative population stdev of simple returns over ``lookback`` closes (calmer ranks higher).

    ``None`` with insufficient or invalid history (see ``stats.return_stdev``).
    ``lookback >= 2`` (``2`` never scores: it yields a single return).
    """
    _check(lookback)
    return _LowVol(lookback)


def mean_reversion(lookback: int) -> Score:
    """Negative rolling price z-score over ``lookback`` closes (most oversold ranks highest).

    ``None`` with insufficient history. ``lookback >= 2``.
    """
    _check(lookback)
    return _MeanReversion(lookback)
