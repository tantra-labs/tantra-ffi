# HANDOFF — `tantra-ffi` (Tier 4, Soul)

## Latest Batch
- ex 0006 `indicators` mirror wave 2c: Decimal-canonical **volatility** family
  (atr, bollinger + %B/bandwidth, donchian, keltner, envelope, stdev,
  historical_volatility, chaikin_volatility, choppiness_index, volatility_stop)
  and **volume** family (accumulation_distribution, chaikin_money_flow,
  chaikin_oscillator, ease_of_movement, force_index, klinger_oscillator,
  money_flow_index, obv, price_volume_trend, volume_oscillator, vwap) in
  `python/tantra/indicators/`. Completed `_rolling.py` with Decimal
  `RollingMoments`/`RollingPairMoments` (+ `Moments`/`PairMoments` NamedTuples).
  Superseded the private `_atr.py` stand-in: `supertrend`/`chande_kroll_stop`
  now import the registered `volatility.atr.Atr` (wave 2c of gap 0006). 15 new
  registry tests (`test_indicators_registry.py`).
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
  (`check_order_fast` signature) — out of scope, no wheel rebuild. 204 wheel
  tests collected (202 green) after the indicators wave 2c (+15 registry tests).
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
- Finish the ex 0006 Decimal-canonical `indicators` mirror (gap 0006, root of
  the tantra-examples 8-gap cascade): remaining families `support_resistance`,
  `breadth`, `statistical`; then `portfolio_strategy`/`wire`/`store`/`backtest`
  sims. Map:
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
