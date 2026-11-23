# 0005 — tantra-ffi design review (2026-11): native-first bindings, parity vectors, typed errors & wheel release matrix

**Status**: Proposed (2026-11-23)
**Scope**: `tantra-ffi` · **Umbrella**: root `docs/plans/0021-workspace-design-review-2026-11.md`

## 0. Executive Summary & Objective

The `tantra` wheel binds only a thin slice of the Rust engines (value objects, paper exchange, Arrow bridge, a partial `RiskEngine`) and re-implements much of the rest in pure Python with no parity vectors. The Python risk facade never reaches the compiled engine, stubs are a hand-written string with no CI drift gate, errors are stringly typed, and the wheel has no release pipeline beyond Linux `maturin develop`.

This plan makes the wheel native-first: bind the Rust engines (or prove the Python fallbacks against Rust-generated golden vectors), type the boundary (exceptions, decimals, Arrow scale), gate generated artifacts in CI, and add a multi-platform release matrix.

Non-goals: the cross-repo model unification (Product/Position enums, root gap 0014) and the broader audit items in root `docs/plans/0019-codebase-audit-refactoring-unification-and-wiring.md` (P4.5 models) are owned there; this plan only supplies the FFI-side binding and parity work.

## 1. Context & Gaps Covered

| Gap | Title | Kind | Severity |
|---|---|---|---|
| [0003](../gaps/0003-python-risk-never-uses-native-engine.md) | `tantra.risk` never reaches the compiled RiskEngine | design-flaw | high |
| [0004](../gaps/0004-stub-and-codegen-drift-gate.md) | Hand-written stub codegen and no drift gate | design-flaw | high |
| [0005](../gaps/0005-wheel-release-matrix.md) | Linux-only abi3 wheel, no release pipeline | deployment | high |
| [0006](../gaps/0006-python-fallback-parity-vectors.md) | Pure-Python copies of Rust logic without parity vectors | duplication | high |
| [0007](../gaps/0007-typed-python-exceptions.md) | Stringly-typed refusals, flat exception hierarchy | design-flaw | medium |
| [0008](../gaps/0008-arrow-decimal-rescale.md) | Arrow decimal export truncates; micros-only timestamps | design-flaw | medium |
| [0009](../gaps/0009-strategy-runner-placeholder.md) | `StrategyRunner` placeholder checksum, no deadline | design-flaw | medium |
| [0010](../gaps/0010-pyclass-borrow-under-detach.md) | `#[pyclass]` borrow/re-entrancy under `py.detach` | design-flaw | medium |
| [0011](../gaps/0011-decimal-extraction-strictness.md) | Decimal extraction duck-types and accepts floats | design-flaw | medium |

Binding map (Python module, backed by Rust `_tantra`, and the Rust code it duplicates):

| Python module | Backed by Rust `_tantra`? | Duplicates |
|---|---|---|
| `python/tantra/money.py`, `types.py`, `bar.py`, `tick.py`, `instrument.py` | partial (`money.py:1` `_tantra` ref; `types.py` re-exports pyclasses `Price`/`Quantity`/...) plus pure `Decimal` dataclasses | tantra-core value objects (two parallel Price/Quantity/Bar/Tick families: `_tantra.Bar` vs `tantra.bar.Bar`) |
| `python/tantra/risk.py` | No (`_native_attr` always raises) although `_tantra.RiskEngine` exists | `tantra-risk` |
| `python/tantra/sizing.py` | No | `tantra-risk/src/sizing_gate.rs` |
| `python/tantra/position.py`, `portfolio.py`, `order_state.py` | No | `tantra-ledger-portfolio`, `tantra-ledger` oms |
| `python/tantra/options.py` | No (Black-Scholes) | `tantra-market-pricing`, tantra-core options |
| `python/tantra/quant.py` | No | `tantra-ledger-allocation`, `tantra-agent-forecast`, `tantra-agent-panel`, tantra-core quant |
| `python/tantra/metrics.py`, `calendar.py`, `session.py` | No | tantra-core calendar / ledger performance / screener DSL |
| `python/tantra/wire/{wire,screener}.py` | No (hand-written pydantic) | tantra-core wire DTOs (`schema/domain_schema.json`) |
| `python/tantra/client/_models.py` | No, generated from runtime `openapi.v2.json` | TS client, Rust runtime-client |
| `python/tantra/backtest/l2_sim.py`, `simulated.py` | native PaperExchange optional | `tantra-exec-paper` matching engine |
| `python/tantra/store.py`, `coverage.py` | No (pyarrow) | `tantra-market-store` / `tantra-data` lakehouse |
| `python/tantra/paper/` | Yes (PaperExchange) | none |
| `python/tantra/indicators/` | No (`_rolling.py`, `_base.py`) | `tantra-market-indicators` |

Plan-only items (no standalone gap doc):
- **R1 — Two parallel Bar/Tick/Instrument families** — native pyclasses `crates/tantra-ffi-py/src/market.rs:71,163` vs `python/tantra/bar.py`, `tick.py`, `instrument.py`, `wire/wire.py`, `adapters/models.py`; ts units differ (ns int vs RFC3339).
- **R2 — Environment/cwd-dependent discovery and legacy env names** — `python/tantra/backtest/simulated.py:121` `VYAAPAAR_SIM_BACKEND` (read at `simulated.py:474`, `l2_sim.py:796`); stale "no compiled simulator" text at `simulated.py:460-492`; cwd-walking data root and JSON coverage ledger at `python/tantra/store.py:90-110,147`; mutable module registries (`markets/india/universes.py:197`, `indicators/_base.py:33`).
- **R3 — Wheel carries ~32k LOC of non-binding code** — `python/tantra/adapters/` (contract.py, testing.py, models.py, rate_limit.py, base.py, secrets.py, session.py), `client/_models.py` (1613 generated lines), `store.py`/`coverage.py`; eager `python/tantra/__init__.py:13-107` imports; `risk.py:36-60` dynamic `__getattr__` defeats mypy.
- **R4 — Naive datetimes and ad-hoc time converters** — `python/tantra/session.py:30-36` treats naive datetimes as IST; three separate ns/ISO converters (`l2_sim.py:545-556`, `paper/__init__.py:53`, `display.py:98`); `crates/tantra-ffi-py/src/paper.rs:134-150` `ts_iso=""` sentinel; `error.rs:23-27` `parse_utc` accepts RFC3339 strings only.

## 2. Component Specifications & Phases

### Phase A — Quick, low-risk fixes
1. [0007](../gaps/0007-typed-python-exceptions.md) — `TantraError` base, `RiskRefused.rule/.code`, rename audit dataclass.
2. [0011](../gaps/0011-decimal-extraction-strictness.md) — reject float/bool, handle exponent notation; share one Python `to_decimal`.
3. [0008](../gaps/0008-arrow-decimal-rescale.md) — checked rescale, ns timestamp column, align store scale.
4. R2 — rename `VYAAPAAR_SIM_BACKEND` to `TANTRA_SIM_BACKEND` (old name accepted with a deprecation warning), drop cwd discovery outside CLI paths.
5. R4 — add `tantra.time` (`to_utc`, `ts_ns_to_dt`, `dt_to_ns`) rejecting naive datetimes without explicit `assume_tz=`; replace the `""` sentinel with `Option<&str>`.

**Gate**: `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `make check`, `ruff check .`, `ruff format --check .`, `mypy --strict python/tantra`, `pytest -q python/tests`.

### Phase B — Structural refactors / de-duplication
1. [0003](../gaps/0003-python-risk-never-uses-native-engine.md) — bind `RiskLimits`/`TradingState`/`RiskStage`/`Command`/`RiskDecision`; delete `_native_attr` fallback.
2. [0004](../gaps/0004-stub-and-codegen-drift-gate.md) — stub introspection or enumeration test, `git diff --exit-code` codegen step, vendored OpenAPI.
3. [0006](../gaps/0006-python-fallback-parity-vectors.md) — per module: bind or add Rust-generated golden vectors (order: risk, position/portfolio, sizing, options, indicators, metrics, quant).
4. [0010](../gaps/0010-pyclass-borrow-under-detach.md) — `frozen` pyclasses with interior locks; threaded kill-switch test.
5. [0009](../gaps/0009-strategy-runner-placeholder.md) — typed `run_bars` result, explicit clock, deadline/cancellation.
6. R1 — pick native pyclasses as the storage type; make Python dataclasses thin aliases/subclasses; add conversion tests (follows root 0019 P4.5).
7. R3 — lazy `__getattr__` imports for heavy submodules; propose moving `adapters/` and `store.py`/`coverage.py` to their L6 repos (plans owned there); check with `python -X importtime`.

**Gate**: Phase A gate plus `maturin develop`, targeted `cargo test -p tantra-ffi-py --test <bin> --profile prod`, `make prod`.

### Phase C — Deployment readiness
1. [0005](../gaps/0005-wheel-release-matrix.md) — `release.yml` matrix (manylinux x86_64/aarch64, macOS universal2, Windows), sdist with resolvable crates, single version source, import smoke tests on 3.10-3.14, drop `auto-initialize` from non-test builds.
2. Free-threaded decision (abi3 vs per-version wheels, `gil_used = false`) after Phase B item 4.

**Gate**: release workflow dry run on a branch; `cargo check --workspace --profile prod`; `pytest -q` on each matrix interpreter.

## 3. Relationship to Other Plans

- Root plan 0019 P4.5 (model unification) is not duplicated; R1 and gap 0006 supply the FFI-side binding and parity work.
- Root gaps fed by this plan: 0013 (single risk gate), 0014 (enums/position model), 0015 (pricing/quant single source), 0016 (indicator parity), 0020 (time semantics), 0022 (one OpenAPI document), 0029 (generated-artifact drift).
- Root plan 0023 (build/CI/release) owns shared workflow conventions that gap 0005 consumes; root plan 0022 has no direct dependency here.
- Provider repos for bind-vs-vector choices: `tantra-risk`, `tantra-ledger`, `tantra-market`, `tantra-core`; adapter/store relocation (R3) is owned by `tantra-adapters` and `tantra-data` plans.

## 4. Exit Criteria

1. `tantra.risk.check_order` runs through the compiled engine with no Python fallback, proven by golden parity vectors.
2. Every Python module in the binding map is either a thin facade over a native binding or has a passing Rust-generated golden-vector test.
3. CI fails on stub/schema/client drift and runs `mypy --strict python/tantra`.
4. Exceptions expose `.rule`/`.code`; floats are rejected at the decimal boundary; Arrow export never truncates silently.
5. Tagged releases publish wheels for Linux, macOS and Windows with a single version source.
6. A threaded test trips the kill switch from a second thread without `Already borrowed`.
