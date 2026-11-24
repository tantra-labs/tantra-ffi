# 0004 — Trade Planner Python Bindings (`tantra.trade_plan`)

**Status**: Proposed

## 0. Executive Summary & Objective

Expose `TradePlanSpec`, `TradePlanner`, `TradeManager`, `TradePlan`/`TradeAction`,
`ChartPattern`, and canonical presets from [`tantra-core` plan 0005](../../../tantra-core/docs/plans/README.md#implemented-plans)
to Python as `tantra.trade_plan`, so the SDK and notebooks run the exact same planner,
presets, and bar-by-bar state machine as Rust backtest and live execution.
Roadmap: [root plan 0008](../../../docs/plans/0008-trade-signal-generator.md).

## 1. Context & Gaps Covered

- Bridge policy: plan 0001 (Python-First Quant Engine Bridge) — Rust owns the math and canonical preset TOML catalog.
- Two Python strategy surfaces exist today:
  - `python/tantra/declarative.py`: `Entry(quantity, stop_loss?, take_profit?)` and `DeclarativeStrategy(oco=True)` (sim-only OCO) in `tantra-ffi`
  - `tantra_strategies.sdk.strategy.Strategy` + `StopProtection` in `tantra-strategies`
- `python/tantra/order.py`: `OrderType.TRAILING_STOP` (`trail_amount`/`trail_percent`) is Python-only, with no Rust counterpart.
- Upstream: `tantra-core/docs/plans/README.md#implemented-plans`, `tantra-market/docs/plans/0002-chart-pattern-analyzer.md` (`ChartPattern`); consumer: `tantra-strategies/docs/plans/0003-trade-plan-sdk.md`.

## 2. Component Specifications & Phases

- **P1 Planner & Presets**: PyO3 classes `TradePlanSpec` (`from_preset(name, **overrides)`, `from_toml`, `from_json`, `list_presets()` reading the **single canonical preset catalog embedded in `tantra-core`**), `PlannerInputs` (incl. `tick_size` and optional `ChartPattern` / `LevelMap`), `ChartPattern`, `TradePlan`, and `PlanError` mapped to typed Python exceptions. `TradePlanner.plan(spec, inputs, budget)`.
- **P2 Manager**: stateful `TradeManager` wrapper exposing `on_entry_fill(fill_price, fill_qty, ts)`, `on_bar(bar, snapshot) -> list[TradeAction]`, and `on_session_close(timeframe, bar, snapshot) -> list[TradeAction]`; state serializable (`to_json`/`from_json`) for restart/checkpoint parity.
- **P3 Batch + Pattern Scan + Parity**: `plan_many(...)` releases the GIL (`py.detach`); Arrow C-Stream `PyCapsule` for bar batches where bulk. Expose read-only `analyze_chart_patterns(bars, timeframe, params)` binding over `tantra-market-signals::PatternAnalyzer` (if exposed in L4 `tantra-ffi`, gated cleanly so `tantra.trade_plan` itself stays L0-backed).
- **P4 Reconcile Python Strategy Surfaces**: `declarative.py` (`Entry`/`oco`) and `TRAILING_STOP` become thin adapters over `TradePlanSpec`/`StopRule`/`TrailRule`/`TargetLadder` and `TradeManager` (no separate Python OCO simulator or third strategy hierarchy); keep deprecated aliases for one release.
- Decimal round-trip: values cross as `decimal.Decimal` (string/integer based), never `float`; reject floats at the boundary.

## 3. Test Plan (TDD)

`tests/` only (pytest):
- `test_trade_plan_parity.py` consumes the core golden vectors (preset → plan JSON, fill + bars + session close → actions) and asserts byte-equal `Decimal` strings;
- `ChartPattern` round-trip & `FormingArmed` vs `BreakoutConfirmed` plan parity tests;
- `Decimal` round-trip + float-rejection tests; `mypy --strict` stubs; `py.detach` smoke under threads; legacy `declarative.py` behaviour regression tests before P4.
Gates: `cargo check --workspace --profile prod`, `maturin develop`, `pytest -q`.

## 4. Dependencies & Tier Notes

L4: `tantra.trade_plan` depends on `tantra-core` only; optional `tantra.patterns` submodule may wrap L2 `tantra-market-signals` cleanly per L4 DAG rules. Blocks `tantra-strategies` plan 0003.

## 5. Open Questions

- Ship schema stubs (`.pyi`) generated from `schemars` or hand-written? (Prefer `schemars`-driven check in CI so Python `.pyi` cannot drift from Rust `TradePlanSpec`/`ChartPattern`.)
