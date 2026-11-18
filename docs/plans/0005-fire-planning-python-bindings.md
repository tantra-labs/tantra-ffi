# 0005 — Python Bindings for FIRE Planning & Cashflow (`tantra.fire` & `tantra.wire.fire`)

**Status**: Proposed (2026-11-18) — Track **T19.4**

Master plan: root [`docs/plans/0013-fire-planning-and-cashflow-platform.md`](../../../docs/plans/0013-fire-planning-and-cashflow-platform.md).
Depends on: [`tantra-ledger` plan 0006](../../../tantra-ledger/docs/plans/0006-fire-bucket-glidepath-and-swr-metrics.md).

---

## 0. Executive Summary & Objective

Expose `tantra_ledger_allocation::fire` cleanly to Python strategies, notebooks, and backtest post-processors through `tantra-ffi-codegen` and `tantra-ffi-py` (`tantra.fire`), guaranteeing byte-for-byte parity with Rust/REST/WASM and strict `decimal.Decimal` inputs/outputs (`tantra-core` remains untouched).

---

## 1. Deliverables

1. **`crates/tantra-ffi-codegen`**:
   - Depend on `tantra-ledger-allocation` (permitted at L4 → L1) and export `FirePlanConfig`, `FireSimulationReport`, `CashflowBucketConfig`, `PostFireCashflowReport`, `SorStressConfig`, `SorStressResult` into generated Python schemas under `python/tantra/wire/fire.py` (or `wire/` module layout).
2. **`crates/tantra-ffi-py` (`src/fire.rs`)**:
   - Depend on `tantra-ledger-allocation`; wrap calculation functions via PyO3, releasing the GIL (`py.detach`) for heavy SoRR Monte Carlo runs (`run_sor_stress`).
   - Accept & return `decimal.Decimal` / typed Python dataclasses — reject native `float` for monetary fields (`TypeError`).
3. **`python/tantra/fire/__init__.py`**:
   - Ergonomic helpers: `simulate_runway(...)`, `calculate_archetypes(...)`, `simulate_cashflow(...)`, `stress_test_sor(...)`, plus `from_backtest_result(result, ...) -> dict` bridging a `BacktestResult`'s CAGR & drawdown directly into a FIRE simulation.
4. **CLI (`python/tantra/cli.py`)**:
   - Optional `tantra-py fire` helper or stub-free module integration.

---

## 2. Tests & Verification

- `python/tests/test_fire.py`: golden vector parity against `tantra-ledger-allocation/tests/golden/fire_golden.json`, `float` rejection type checks, `.pyi` stub verification.
- Gate: `cargo check --workspace --profile prod && maturin develop && ruff check . && mypy --strict && pytest -q`.
