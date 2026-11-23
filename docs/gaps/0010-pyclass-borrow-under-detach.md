# 0010 — `#[pyclass]` borrow and re-entrancy under `py.detach`

**Status**: open
**Filed**: 2026-11-23 — workspace design review (root plan 0021) · **Kind**: design-flaw · **Severity**: medium
**Plan**: [0005](../plans/0005-design-review-2026-11.md)

## What's stubbed or hardcoded

- `crates/tantra-ffi-py/src/paper.rs:102-105,134-150,164,181-206` — mutating methods run engine work inside `py.detach(move || self.inner...)` with `&mut self`. PyO3's runtime borrow flag stays held while the GIL is released, so a second thread (or a re-entrant callback) calling any method raises `RuntimeError: Already borrowed` instead of blocking.
- `crates/tantra-ffi-py/src/risk.rs:26-28` — `#[derive(Clone)] pub struct RiskEngine` pyclass without `frozen` or an interior lock; no `gil_used` declaration (`crates/tantra-ffi-py/src/lib.rs:67`); no `#[pyclass(frozen)]` plus `Mutex` for free-threaded builds.
- `python/tests/test_gil.py` checks that the GIL is released but not concurrent access.

## Why

Multi-threaded Python (executors, free-threaded 3.13t) gets spurious `Already borrowed` errors in production. A kill-switch call from a watchdog thread can fail exactly when it is needed, which defeats the purpose of the risk engine's halt controls.

## How to close it

1. Make `RiskEngine` and `PaperExchange` `frozen` with an inner `parking_lot::Mutex`, or explicitly mark them `unsendable` and document single-thread use.
2. Add `#[pymodule(gil_used = false)]` once the above is true (gate for the free-threaded wheel in [0005](0005-wheel-release-matrix.md)).
3. Ensure the halt/kill-switch path never needs a long-held lock: engine work under `detach` must be chunked or the lock released between steps.
4. Add a threaded pytest: trip the kill switch from a second thread during a long `advance_to`.

**Verification**: `python/tests/test_concurrent_access.py`; `cargo clippy --all-targets -- -D warnings`, `make check`, `maturin develop`, `pytest -q`; repeat on a free-threaded interpreter once available.

## Related

- [0005](0005-wheel-release-matrix.md) (free-threaded wheel), [0009](0009-strategy-runner-placeholder.md).
- [0003](0003-python-risk-never-uses-native-engine.md) (binding more of `RiskEngine` must follow the new locking model).
