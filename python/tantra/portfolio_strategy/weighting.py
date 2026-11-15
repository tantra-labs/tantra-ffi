# wheel surface (ex 0006): Decimal-canonical kernel-parity portfolio strategy parts
# (mirrors tantra_examples/_kernel/portfolio_strategy/weighting public API; weights are Decimal)

"""Weighting port: how to split capital across the selected names."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Protocol, runtime_checkable

from tantra.instrument import InstrumentId
from tantra.portfolio_strategy.stats import return_stdev
from tantra.portfolio_strategy.view import MarketView


@runtime_checkable
class WeightingScheme(Protocol):
    """Long-only target weights for ``selected`` (non-negative, sum <= 1, keys within
    ``selected``). The strategy applies ``allocation`` on top."""

    def weights(
        self, selected: Sequence[InstrumentId], view: MarketView
    ) -> Mapping[InstrumentId, Decimal]: ...


class EqualWeight:
    """1/N across distinct selected names; an empty selection gives no weights."""

    def weights(
        self, selected: Sequence[InstrumentId], view: MarketView
    ) -> Mapping[InstrumentId, Decimal]:
        names = list(dict.fromkeys(selected))
        return {iid: Decimal(1) / len(names) for iid in names}


class InverseVolatility:
    """Weight proportional to 1/sigma, sigma = population stdev of simple returns over the
    last ``lookback`` closes (``lookback >= 2``; ``2`` yields one return, so always invalid).

    Instruments with insufficient history or zero/NaN/invalid vol get the mean of the valid
    inverse-vols (a neutral weight). If no instrument has a valid vol the result is equal
    weight. Weights sum to 1 (empty selection gives no weights); duplicates are dropped.
    """

    def __init__(self, lookback: int = 20) -> None:
        if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback < 2:
            raise ValueError(f"lookback must be an int >= 2, got {lookback!r}")
        self.lookback = lookback

    def weights(
        self, selected: Sequence[InstrumentId], view: MarketView
    ) -> Mapping[InstrumentId, Decimal]:
        names = list(dict.fromkeys(selected))
        inverse: dict[InstrumentId, Decimal] = {}
        for iid in names:
            vol = return_stdev(view, iid, self.lookback)
            if vol is not None and vol > 0 and vol.is_finite():
                inverse[iid] = Decimal(1) / vol
        if not inverse:
            return {iid: Decimal(1) / len(names) for iid in names}
        neutral = sum(inverse.values(), Decimal(0)) / len(inverse)
        raw = {iid: inverse.get(iid, neutral) for iid in names}
        total = sum(raw.values(), Decimal(0))
        return {iid: w / total for iid, w in raw.items()}
