# wheel surface (ex 0006): Decimal-canonical kernel-parity portfolio strategy parts
# (mirrors tantra_examples/_kernel/portfolio_strategy/stats public API; returns are Decimal)

"""Small pure statistics shared by weighting and scoring.

Exact ``decimal.Decimal`` arithmetic (no ``statistics`` module): the population stdev of
simple returns is ``mean of squared deviations, then sqrt``.
"""

from __future__ import annotations

from decimal import Decimal
from itertools import pairwise

from tantra.instrument import InstrumentId
from tantra.portfolio_strategy.view import MarketView


def return_stdev(
    view: MarketView, instrument_id: InstrumentId, lookback: int
) -> Decimal | None:
    """Population stdev of simple returns over the last ``lookback`` closes, else ``None``.

    ``lookback`` closes give ``lookback - 1`` returns; at least two returns are needed, so
    ``lookback=2`` is always ``None``. ``None`` also when history is shorter than
    ``lookback``, any close is non-finite, or any return's base close is <= 0.
    """
    closes = view.recent_closes(instrument_id)
    if len(closes) < lookback:
        return None
    window = closes[-lookback:]
    if not all(c.is_finite() for c in window) or any(c <= 0 for c in window[:-1]):
        return None
    returns = [b / a - Decimal(1) for a, b in pairwise(window)]
    if len(returns) < 2:
        return None
    n = len(returns)
    mean = sum(returns, Decimal(0)) / n
    variance = sum(((r - mean) ** 2 for r in returns), Decimal(0)) / n
    return variance.sqrt()
