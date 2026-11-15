# wheel surface (ex 0006): Decimal-canonical kernel-parity portfolio strategy parts
# (mirrors tantra_examples/_kernel/portfolio_strategy/universe public API)

"""Universe port and implementations: which instruments are eligible."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Protocol, runtime_checkable

from tantra.instrument import InstrumentId


@runtime_checkable
class Universe(Protocol):
    """Eligible instruments. ``members`` must be deterministic and free of duplicates.

    ``as_of`` is the bar's UTC date (``None`` when unknown); implementations without
    point-in-time knowledge ignore it.
    """

    def members(self, as_of: date | None = None) -> Sequence[InstrumentId]: ...


class StaticUniverse:
    """A fixed list (duplicates dropped, first-seen order kept).

    Mutable on purpose so tests and scenarios can change membership mid-run via
    ``set_members``; the strategy re-reads it at every rebalance.
    """

    def __init__(self, instruments: Iterable[InstrumentId]) -> None:
        self._members: tuple[InstrumentId, ...] = ()
        self.set_members(instruments)

    def set_members(self, instruments: Iterable[InstrumentId]) -> None:
        """Replace the membership."""
        self._members = tuple(dict.fromkeys(instruments))

    def members(self, as_of: date | None = None) -> Sequence[InstrumentId]:
        return self._members


class NamedUniverse:
    """A universe known to the engine (``tantra_examples.universe_lists``), e.g. ``"nifty50"``.

    By default ``as_of`` is ignored and the engine's current list is returned. With
    ``point_in_time=True`` the engine's historical snapshot for ``as_of`` is used; the
    engine then raises ``ValueError`` if no history is registered (it never projects
    today's constituents into the past). An unknown name raises ``ValueError``; there is
    no seed fallback here.
    """

    def __init__(self, name: str, exchange: str = "NSE", *, point_in_time: bool = False) -> None:
        self.name = name
        self.exchange = exchange
        self.point_in_time = point_in_time

    def members(self, as_of: date | None = None) -> Sequence[InstrumentId]:
        # stand-in: tantra-examples/docs/gaps/0004-tantra-wheel-display-universes-client.md
        try:
            from tantra_examples.universe_lists import resolve_universe
        except ImportError:
            raise NotImplementedError(
                "NamedUniverse needs tantra_examples.universe_lists: tantra-examples gap 0004 "
                "(display/universes wheel surface) does not ship a wheel client yet; install "
                "tantra-examples or use StaticUniverse"
            ) from None
        when = as_of if self.point_in_time else None
        return tuple(resolve_universe(self.name, self.exchange, as_of=when))
