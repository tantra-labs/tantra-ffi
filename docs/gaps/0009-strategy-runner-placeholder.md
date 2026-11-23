# 0009 — `StrategyRunner` "GIL-free batch" is a placeholder checksum

**Status**: open
**Filed**: 2026-11-23 — workspace design review (root plan 0021) · **Kind**: design-flaw · **Severity**: medium
**Plan**: [0005](../plans/0005-design-review-2026-11.md)

## What's stubbed or hardcoded

- `crates/tantra-ffi-py/src/runner.rs:171-176,192-205` — `py.detach` only counts positive closes/prices (`checksum`); there is no indicator, risk or OMS work. The real per-bar work is Python `on_bar` calls that re-acquire the GIL.
- `crates/tantra-ffi-py/src/runner.rs:178-184` — `self.strategy.bind(py).getattr("on_bar").is_ok()` on every bar, which also swallows genuine `AttributeError`s raised inside a property.
- `crates/tantra-ffi-py/src/runner.rs:17-24,224-226` — `now_or_utc` / `now_iso` use `Utc::now()`: acceptable at the boundary, but Python strategies then get a wall-clock default, defeating deterministic replay unless callers always pass `ts_iso`.
- `.agents/rules/scalability-and-concurrency.md` section 4 requires `PythonStrategyActor`-style isolation with `CancellationToken` deadlines; the runner has none, so a stuck `on_bar` blocks the caller forever.

## Why

The advertised "GIL-safe runner" gives no parallel speed-up and no strategy deadline, and its `i64` checksum return value is meaningless API surface. The stand-in is uncited workaround code in the sense of `.agents/rules/gap-tracking.md`; this document is its record.

## How to close it

1. Resolve the `on_bar` / `on_tick` callbacks once at construction and fail fast on a missing attribute.
2. Make `run_bars` return a typed result (processed count, per-bar errors) instead of the checksum.
3. Take an explicit clock (timestamp argument or injected clock object); keep `Utc::now()` out of the default replay path.
4. Implement cancellation: a deadline check between callbacks plus `py.check_signals()` so `KeyboardInterrupt` works; test with a hanging strategy.
5. Either perform real batch work in the detached section (indicator/risk via native engines) or drop the detach and document the runner honestly.

**Verification**: `python/tests/test_runner_deadline.py` (hanging strategy, missing-callback, deterministic replay), `cargo clippy --all-targets -- -D warnings`, `maturin develop`, `pytest -q`.

## Related

- root gap 0012 (synthetic or placeholder results presented as real).
- [0010](0010-pyclass-borrow-under-detach.md).
