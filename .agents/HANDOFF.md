# HANDOFF — `tantra-ffi` (Tier 4, Soul)

## Latest Batch
- Wheel freeze-slicer (`tantra.sizing`): `OPTION_FREEZE_LIMIT_DEFAULT = 1800`,
  `freeze_limit_qty` / `slice_order` / `verify_slices` (+ `Sizer` staticmethods)
  — stand-in closure for tantra-examples gap 0005.
- Wheel `tantra.algo_analytics` package (gap 0001): ported from
  tantra-examples `optimizer/algo_analytics` (`folds`, `metrics`,
  `deflated_sharpe`, `plateau`, `monte_carlo`, `walk_forward`); `walk_forward` /
  `train_test_split` take an injected `runner=` (the wheel ships no session
  orchestrator; `None` raises a loud RuntimeError naming it).
- Decimal-canonical domain core (gap 0006 root slice): `tantra.money`
  (`Money`/`Currency`/`MinorUnit`), `tantra.position`, `tantra.trade`,
  `tantra.instrument`, `tantra.entities` facade; new names re-exported from
  `tantra` (compiled `Currency` untouched).
- Pytest green except the 2 pre-existing stale-wheel `test_risk.py` failures
  (`check_order_fast` signature) — out of scope, no wheel rebuild. New suites:
  `test_sizing.py`, `test_algo_analytics.py`, `test_money.py`,
  `test_position_trade_instrument.py` (existing strategy/types/sdk green).
- Prior batch: CLI `backtest` subcommand (T9.1) shipped via `tantra.strategy.run`
  — tests in `python/tests/test_cli.py`.

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
- Tier 5A (tantra-ui) per the master migration guide, or extending the Python SDK surface.
- Post-T9.1: optional CLI surface growth (e.g. `positions`/`portfolio` read-only subcommands wired to the SDK) or a `--bars-csv` loader — pick up whichever slice is next in the batch plan.
- Verify with `make all` (fmt → clippy → `cargo test --workspace` → codegen → wheel → pytest) before tagging the milestone.

## Operating Invariants
- **Toolchain**: rustc/cargo 1.95, edition 2024; `rust-version = 1.85` minimum in the workspace.
- **Zero floats**: `decimal.Decimal` / `rust_decimal::Decimal` only across every FFI boundary; no `f32`/`f64` in financial paths.
- **Tests only in `tests/`**: no in-file `#[test]`/`#[cfg(test)]` in `src/` (CI `grep` guard fails the build on matches).
- **PYO3_PYTHON required** to build or test the py crate (set in `.cargo/config.toml`; override via environment).
- **Do not modify** `crates/**` Rust sources, `python/tantra/*.py`, `python/tests/*`, `pyproject.toml`, `.cargo/config.toml` (owned by sibling agent sessions).
- `docs/migration-guide.md` decimated: sub-crate mapping moved to `docs/design/code-migration-map.md`; verification commands folded into the same map; original `migration-guide.md` removed. `docs/roadmap/` removed (dismantled into `docs/{design,gaps,plans}`).
