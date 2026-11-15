# wheel surface (ex 0006): backtest simulators (mirrors tantra_examples/_kernel/backtest public API)
# stand-in closure for tantra-examples gap 0006

"""Square-root market impact: the printed open is not the price you get.

Balch pitfall #4 ("Ignoring Market Impact"): assuming frictionless, size-blind
fills at the last print turns strategies that only work with infinite liquidity
into apparent winners. The model here is the standard square-root law:

    impact_fraction = kappa * sigma_daily * sqrt(quantity / ADV)

``sigma_daily`` is the sample standard deviation of close-to-close returns over
the rolling ``window``, ``ADV`` the mean volume over the same window, and the
result is a *fraction* of the fill price — a buy pays it, a sell receives less
of it. ``kappa`` is the security's impact coefficient (higher for anything
thin or jumpy); 0 disables impact without changing the simulator.

History only ever comes from sessions the simulator has already seen
(:meth:`MarketImpact.observe` is called after a session's fills), so a fill
never prices itself off its own bar. Pure: no I/O, no wall clock.

Decimal-canonical (rust_decimal parity): every quantity, volume, close and
return is an exact ``decimal.Decimal``.
"""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import pairwise

from tantra.instrument import InstrumentId
from tantra.types import to_decimal

__all__ = ["MarketImpact"]


@dataclass
class MarketImpact:
    """Rolling square-root impact model, tracked per instrument.

    Args:
        kappa: Impact coefficient (>= 0). ``0`` means no impact anywhere.
        window: Sessions of volume/close history to keep (>= 2, so a daily
            volatility exists).
    """

    kappa: Decimal = Decimal(1)
    window: int = 20
    _volumes: dict[InstrumentId, deque[Decimal]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _closes: dict[InstrumentId, deque[Decimal]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        self.kappa = to_decimal(self.kappa)
        if not (self.kappa.is_finite() and self.kappa >= 0):
            raise ValueError(f"kappa must be a finite number >= 0, got {self.kappa}")
        if self.window < 2:
            raise ValueError(f"window must be >= 2 so a daily sigma exists, got {self.window}")

    def observe(self, instrument_id: InstrumentId, *, volume: Decimal, close: Decimal) -> None:
        """Record one finished session's volume and close for ``instrument_id``.

        Called after the session's fills, so the oldest usable history for a
        fill at session *k+1* ends at session *k*.
        """
        volume = to_decimal(volume)
        close = to_decimal(close)
        volumes = self._volumes.get(instrument_id)
        closes = self._closes.get(instrument_id)
        if volumes is None:
            volumes = deque(maxlen=self.window)
            self._volumes[instrument_id] = volumes
        if closes is None:
            closes = deque(maxlen=self.window)
            self._closes[instrument_id] = closes
        volumes.append(volume)
        closes.append(close)

    def adv(self, instrument_id: InstrumentId) -> Decimal:
        """Average daily volume over the window (0 when nothing is observed)."""
        volumes = self._volumes.get(instrument_id)
        if not volumes:
            return Decimal(0)
        return sum(volumes, Decimal(0)) / len(volumes)

    def sigma(self, instrument_id: InstrumentId) -> Decimal:
        """Sample standard deviation of close-to-close returns (0 when undefined)."""
        closes = self._closes.get(instrument_id)
        if closes is None or len(closes) < 2:
            return Decimal(0)
        returns = [
            to_decimal(after) / to_decimal(before) - Decimal(1)
            for before, after in pairwise(closes)
            if before > 0
        ]
        if len(returns) < 2:
            return Decimal(0)
        mean = sum(returns, Decimal(0)) / len(returns)
        variance = sum((x - mean) ** 2 for x in returns) / (len(returns) - 1)
        return variance.sqrt()

    def fraction(self, instrument_id: InstrumentId, quantity: Decimal) -> Decimal:
        """``kappa * sigma_daily * sqrt(quantity / ADV)`` — 0 without usable history."""
        quantity = to_decimal(quantity)
        if quantity <= 0:
            return Decimal(0)
        adv = self.adv(instrument_id)
        if adv <= 0:
            return Decimal(0)
        sigma = self.sigma(instrument_id)
        if sigma <= 0:
            return Decimal(0)
        return self.kappa * sigma * (quantity / adv).sqrt()
