# HANDOFF — `tantra-ffi` (Tier 4, Soul)

## Latest Batch
- **T14 P2 paper-exchange wheel embedding SHIPPED (2026-11-16)**: plan 0003 → **Implemented**
  (T14.10 + T14.11). Native `tantra._tantra.PaperExchange` pyclass
  (`crates/tantra-ffi-py/src/paper.rs`, wired into `lib.rs` + workspace dep
  `tantra-exec-paper`): `place_order`→`PAPER-0001…`, `cancel_order`, `amend_order`,
  `feed_bar`/`feed_tick`, `advance_to`, `set_market_price`, `fills`, `events`, `positions`,
  `cash`/`equity`, `depth`, `order`; `seed=` runs the engine's seeded latency
  (`NetworkLatency::new(10, 5, seed)` — no `seeded()` ctor, recorded deviation). Engine steps
  release the GIL via `py.detach` (pyo3 0.30; `allow_threads` removed). Wheel `tantra/paper/`
  (`PaperSession` facade + `run(strategy, bars)` + `wire.fills_wire`); `l2_sim.py` native
  backend `_NativeL2` (backend="native" resolves, no NotImplementedError; coincident-tape
  parity only — different matching models, see plan deviations). Golden tape re-embedded at
  `python/tests/golden/paper_golden.json`. **Wheel suite 505 passed**; Rust gate green;
  changed paths ruff-clean (venv ruff 0.17.4; FURB157 fires on untouched files — pre-existing).
  T14.11 examples/strategies consumers (see `tantra-examples`/`tantra-strategies` HANDOFFs).
- **T13 Thrust A wheel lift SHIPPED (2026-11-15/16)** — plan 0002 phases A1–A5 (T13.1–T13.5)
  wheel surfaces landed in `python/tantra/` with wheel tests (`python/tests` **480 passed**,
  exit 0; ruff clean on all new files; eager imports + `__all__` wired into
  `python/tantra/__init__.py`):
  - `tantra.portfolio` (`Account`/`Portfolio`, verbatim from `_kernel/portfolio.py`) + `test_portfolio.py`
  - `tantra.risk` (pure-Python `check_state`/`check_order`/`limits_from_config` + audit records +
    `_native_attr` probe, verbatim from `_kernel/risk.py`) + `test_risk_surface.py`
  - `tantra.calendar` (`IST`/`ist_midnight_ns`/`SessionWindow`/`MarketCalendar`/`NseCalendar`) + `test_calendar.py`
  - `tantra.options` (`OptionKind`/`OptionStyle`/`OptionContract`/`OptionChain` + `Greeks`/
    `bs_price`/`bs_greeks`/`implied_volatility`, option.py + greeks.py merged into one module) + `test_options.py`
  - `tantra.metrics` (`extract_metrics_from_bars` + screener predicate evaluation; the Sma/Rsi
    wrappers retargeted to the wheel `tantra.indicators` `_legacy` API) + `test_metrics.py`
  The `tantra-examples` side (delete `_kernel/` domain modules + retarget consumers) **landed
  2026-11-16** (examples `25cb5df` Thrust A + `1acabfb` Thrust B harness rename + `3c2e5ae`
  docs; root plan 0006 **Implemented**). **Plan 0002 moved to Implemented** (see index).
- **Wheel suite fully green (2026-11-15)**: all 3 pre-existing stale-wheel failures fixed
  (`python/tests` **464 passed**, exit 0).
  - `test_risk.py` ×2 (`test_price_band_enforced`, `test_reduce_only_refuses_buy_allows_sell`):
    the venv's installed `_tantra.abi3.so` was stale (pre-`side` `check_order_fast`). Fixed by
    rebuilding: `.venv/bin/maturin develop --release` (abi3, no libpython link issue under
    maturin). Signature now `check_order_fast(self, /, algo_id, instrument, side, quantity,
    limit_price=None, ts_iso=None)`.
  - `test_indicators_registry.py::test_registry_total_matches_kernel`: cross-checked the wheel
    registry against the deleted `tantra_examples._kernel.indicators._base` mirror. Rewritten as a
    wheel self-consistency gate (74 unique kinds, all 8 `FAMILIES`, per-family counts pinned:
    12/9/17/12/11/3/5/5) — the wheel IS the promoted kernel, so a mirror compare is obsolete.
- **T13 IMPLEMENTED (2026-11-16)**: root plan 0006 (dismantle the `_kernel` shared harness)
  complete — Thrust A wheel surfaces (this repo, plan 0002, T13.1–T13.5) + Thrust B harness
  rename in `tantra-examples` (plan 0003, T13.6) + gate (T13.7). See the top entry and
  `tantra-examples/.agents/HANDOFF.md`.
- **ex 0008 closure (2026-11-15)**: wheel `tantra.backtest.session` (`Tantra.backtest`:
  next-open fills, NSE delivery costs, T+1 settlement) shipped; `simulated.resolve_fill_costs`
  + `make_simulator` now wired to `tantra.markets.india`; `algo_analytics` default runner
  uses the session. `2d9214e`.
- ex 0003 closure: wheel `tantra.screener` surface shipped — `python/tantra/screener/`
  (`catalog.py` `Metric`/`MetricCatalog`/`load_catalog`, `coverage.py`
  `Coverage` + `DateInterval`, `__init__.py` re-export with `__all__`); wired into
  `tantra/__init__.py` eager pure-Python imports + `__all__`. 6 new tests
  (`test_screener.py`). `import tantra, tantra.screener` ok; wheel suite fully green
  (464 passed — the former 3 stale-wheel failures fixed 2026-11-15; see the top entry). New files
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
- **P3 / P4 of the paper-exchange track (T14)**: `tantra-ui` plan 0008 (WASM paper studio
  consuming `tantra.paper`) and P4 cross-repo parity + docs (re-verify the golden tape
  `python/tests/golden/paper_golden.json` across every embedding, close out root plan 0007).
- Housekeeping: run `make all` (fmt → clippy → `cargo test --workspace` → codegen →
  wheel → pytest) before tagging the T14 milestone; the venv's ruff (0.17.4) FURB157 hits on
  untouched files are pre-existing and out of scope.

## Operating Invariants
- **Toolchain**: rustc/cargo 1.95, edition 2024; `rust-version = 1.85` minimum in the workspace.
- **Zero floats**: `decimal.Decimal` / `rust_decimal::Decimal` only across every FFI boundary; no `f32`/`f64` in financial paths.
- **Tests only in `tests/`**: no in-file `#[test]`/`#[cfg(test)]` in `src/` (CI `grep` guard fails the build on matches).
- **PYO3_PYTHON required** to build or test the py crate (set in `.cargo/config.toml`; override via environment).
- **Do not modify** `crates/**` Rust sources, `python/tantra/*.py`, `python/tests/*`, `pyproject.toml`, `.cargo/config.toml` (owned by sibling agent sessions).
- `docs/migration-guide.md` decimated: sub-crate mapping moved to `docs/design/code-migration-map.md`; verification commands folded into the same map; original `migration-guide.md` removed. `docs/roadmap/` removed (dismantled into `docs/{design,gaps,plans}`).
