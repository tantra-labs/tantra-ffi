# HANDOFF — `tantra-ffi` (Tier 4, Soul)

## Latest Batch
- ex 0003 closure: wheel `tantra.screener` surface shipped — `python/tantra/screener/`
  (`catalog.py` `Metric`/`MetricCatalog`/`load_catalog`, `coverage.py`
  `Coverage` + `DateInterval`, `__init__.py` re-export with `__all__`); wired into
  `tantra/__init__.py` eager pure-Python imports + `__all__`. 6 new tests
  (`test_screener.py`). `import tantra, tantra.screener` ok; wheel suite green except the
  3 known pre-existing failures (test_risk ×2, test_indicators_registry). New files
  ruff check + format clean (default 88-width; mirror `catalog.py` reformatted).
- ex 0006 `indicators` mirror COMPLETE (wave 2d): Decimal-canonical
  **support_resistance** (pivot_points, fibonacci_retracement, williams_fractals),
  **breadth** (advance_decline_line, mcclellan_oscillator, put_call_ratio, trin,
  updown_volume_ratio) and **statistical** (beta, correlation, covariance,
  hurst_exponent, zscore, `_pair`) families in `python/tantra/indicators/`. All 8
  kernel families are now mirrored; `indicators/__init__.py` imports the three new
  families and adds a `Zscore` case-compat alias (the class is `ZScore`). 14 new
  registry tests; 74 registered indicators = kernel `_REGISTRY` total (asserted
  against the kernel).
- ex 0006 `indicators` mirror wave 2c: volatility + volume families in
  `python/tantra/indicators/`, `_rolling.py` `RollingMoments`/`RollingPairMoments`;
  superseded the `_atr.py` stand-in (15 registry tests).
- Wheel `tantra.execution` (ex 0006 slice): Decimal-canonical `ExecutionPort`
  surface — frozen `OrderRejection` + the 7 `ExecutionEvent` dataclasses,
  `order_event`/`events_from_native` (Decimal qty/price/cum_qty,
  `Money.from_minor` costs), `rejection_from_event`/`event_from_rejection`,
  runtime-checkable `ExecutionPort`/`LegacyExecutionPort`/
  `RejectingExecutionPort`, `adapt_port`/`AdaptedPort`/`LegacyPortEvents`,
  `BaseExecutionPort` buffered legacy drains, deprecated
  `drain_port_rejections`/`cancel_order`. Added `Money.from_minor` to
  `money.py`. 21 new tests (`test_execution.py`).
- Wheel `tantra.bar` + `tantra.tick` (ex 0006 slice): Decimal-canonical
  `Bar` (OHLCV/volume Decimal, prices >= 0, high >= low) and
  `AggressorSide`/`QuoteTick`/`TradeTick` (exact `mid_price`), mirroring the
  `_kernel` mirror public API. 16 new tests (`test_bar.py` + `test_tick.py`).
- Wheel `tantra.order` + `tantra.order_state` (ex 0006 slice):
  `OrderSide`/`OrderType`/`TimeInForce`/`OrderStatus`/`validate_intent`/
  `OrderIntent` (Decimal quantity/price/trail fields, trailing-stop factories)
  and the `OrderEvent`/`OrderState` lifecycle FSM (exact Decimal `QTY_EPS`,
  mirror-parity `can_transition` table: illegal transitions raise
  `IllegalStatusTransition`, terminal no-ops return False). 18 new tests
  (`test_order.py` + `test_order_state.py`).
- ex 0006 slices wired into the `tantra` top-level package (`bar`/`tick`/
  `order`/`order_state`/`execution` modules + `__all__`); compiled top-level
  `Bar`/`OrderSide`/`OrderStatus` untouched (same documented split as
  `money.Currency`).
- Pytest green except the 2 pre-existing stale-wheel `test_risk.py` failures
  (`check_order_fast` signature) — out of scope, no wheel rebuild. 218 wheel
  tests collected (216 green) after the indicators wave 2d (+14 registry tests);
  the indicators slice of gap 0006 is complete.
- Prior batch: Decimal-canonical domain core (`money`/`position`/`trade`/
  `instrument`/`entities`) + freeze-slicer + algo_analytics/quant/optimizer
  (gaps 0005/0001/0006 root slice).
- Prior batch: CLI `backtest` subcommand (T9.1) via `tantra.strategy.run`.

## Status
Tier 4 (tantra-ffi) implementation complete:
- Rust gate green: `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test --workspace`.
- Zero `#[cfg(test)]` in `src/` — all tests live in `tests/` (enforced in `.github/workflows/ci.yml`).
- Wheel builds via `maturin develop` into `.venv` (editable install of `tantra._tantra`).
- `pytest` suite under `python/tests/` green.

Build/CI/docs plumbing written and verified: `Makefile` (kept Rust targets + new `bootstrap-python`/`codegen`/`py-build`/`py-test`/`py`/`all`), `.github/workflows/ci.yml` (rust + python jobs), `README.md`, `.agents/HANDOFF.md`.

Docs: `docs/roadmap/` dismantled into `docs/{design,gaps,plans}` (2026-11-12).
Roadmap milestones are DONE; their status now lives in `docs/design/code-migration-map.md`
and the per-module design docs. Gaps index added at `docs/gaps/` (CLI stub subcommands
`0001`, unused `tantra-market-*` workspace deps `0002`).

2026-11-13: `RiskEngine.check_order_fast` gained a required `side: OrderSide` (tantra-risk
plan 0002 — side-aware reduce-only). Mirrored in the pyclass, codegen stub, `_tantra.pyi`,
`docs/design/code-risk.md`, and `python/tests/test_risk.py` (new reduce-only test). Rust
`cargo check --workspace` green; the Python suite needs a `maturin develop` rebuild before
`pytest` (see "Immediate Next Step").

## Decisions & Discoveries
- **pyo3 0.30 API**: `Python::attach`/`detach` replace the removed `with_gil`/`allow_threads` surface; `#[pyclass]` items are private by default and must be made public explicitly; extension modules use `abi3-py310`.
- **pyo3 0.22 is incompatible with rustc 1.95** — the workspace pins `pyo3 = "0.30"` (see workspace `Cargo.toml`).
- **arrow 53**: zero-copy export uses `FFI_ArrowArrayStream` + the Python `PyCapsule` protocol; verified by consuming the capsule with `pyarrow` (`bars_to_stream` / `ticks_to_stream`).
- **PYO3_PYTHON**: required to build/test the py crate. Repo-local `.cargo/config.toml` pins a full conda-forge CPython 3.12 (default `/usr/bin/python3` lacks dev headers). CI overrides it to the `actions/setup-python` interpreter via `GITHUB_ENV`.
- **Venv at `.venv`** (Python 3.12 + maturin + pytest + pyarrow), wheel installed editable.

## Immediate Next Step
- Continue the ex 0006 Decimal-canonical kernel-mirror cascade (gap 0006):
  remaining `indicators`-adjacent slices `portfolio_strategy`/`wire`/`store`/
  `backtest` sims. Map:
  `tantra-examples/docs/design/gap-cascade-kernel-mirror.md`.
- Verify with `make all` (fmt → clippy → `cargo test --workspace` → codegen →
  wheel → pytest) before tagging the milestone.

## Operating Invariants
- **Toolchain**: rustc/cargo 1.95, edition 2024; `rust-version = 1.85` minimum in the workspace.
- **Zero floats**: `decimal.Decimal` / `rust_decimal::Decimal` only across every FFI boundary; no `f32`/`f64` in financial paths.
- **Tests only in `tests/`**: no in-file `#[test]`/`#[cfg(test)]` in `src/` (CI `grep` guard fails the build on matches).
- **PYO3_PYTHON required** to build or test the py crate (set in `.cargo/config.toml`; override via environment).
- **Do not modify** `crates/**` Rust sources, `python/tantra/*.py`, `python/tests/*`, `pyproject.toml`, `.cargo/config.toml` (owned by sibling agent sessions).
- `docs/migration-guide.md` decimated: sub-crate mapping moved to `docs/design/code-migration-map.md`; verification commands folded into the same map; original `migration-guide.md` removed. `docs/roadmap/` removed (dismantled into `docs/{design,gaps,plans}`).
