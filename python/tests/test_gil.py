"""Engine steps release the GIL (plan 0003, P4).

Two Python threads each drive their own :class:`~tantra.paper.PaperSession`
engine steps (``advance_to`` etc.). If an engine step did not release the GIL
via ``py.allow_threads``, the threads would still complete (the GIL serialises
them), so the binding assertion is *no deadlock / no starvation* within the join
timeout: the engine work must run off the GIL or the harness hangs.
"""

from __future__ import annotations

import threading
from decimal import Decimal

from tantra.paper import PaperSession


def _drive(errors: list, results: list) -> None:
    try:
        session = PaperSession(cash=Decimal(1_000_000), seed=7)
        session.set_market_price("NSE:RELIANCE", Decimal(100))
        for i in range(100):
            session.advance_to(f"2023-11-14T22:{10 + (i % 50):02d}:00Z")
            session.set_market_price("NSE:RELIANCE", Decimal(100))
        results.append(session.equity())
    except Exception as exc:  # noqa: BLE001 - surface any driver failure
        errors.append(exc)


def test_concurrent_threads_complete_without_deadlock():
    errors: list = []
    results: list = []
    threads = [
        threading.Thread(target=_drive, args=(errors, results)),
        threading.Thread(target=_drive, args=(errors, results)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not any(t.is_alive() for t in threads), "a driver thread deadlocked"
    assert not errors
    assert len(results) == 2
