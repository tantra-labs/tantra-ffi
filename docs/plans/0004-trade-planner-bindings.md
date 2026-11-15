# 0004 — Trade Planner Python Bindings (`tantra.trade_plan`)

**Status**: Proposed

## 0. Executive Summary & Objective

Expose `TradePlanSpec`, `TradePlanner`, `TradeManager` and `TradePlan`/`TradeAction` from
`tantra-core` plan 0005 to Python as `tantra.trade_plan`, so the SDK and notebooks run the same planner as backtest/live. Roadmap: [root plan 0008](../../../docs/plans/0008-trade-signal-generator.md).

## 1. Context & Gaps Covered

- Bridge policy: plan 0001 (Python-First Quant Engine Bridge) — Rust owns the math.
- `python/tantra/declarative.py`: `Entry(quantity, stop_loss?, take_profit?)` and `DeclarativeStrategy(oco=True)` (sim-only OCO) overlap the new types.
- `python/tantra/order.py`: `OrderType.TRAILING_STOP` (`trail_amount`/`trail_percent`) is Python-only, with no Rust counterpart.
- Upstream: `tantra-core/docs/plans/0005-trade-planner-and-manager.md`; consumer: `tantra-strategies/docs/plans/0003-trade-plan-sdk.md`.

## 2. Component Specifications & Phases

- **P1 Planner**: PyO3 classes `TradePlanSpec` (from dict/TOML/JSON, preset lookup, kwargs overrides), `PlannerInputs`, `TradePlan`, `PlanError` mapped to typed Python exceptions. `TradePlanner.plan(spec, inputs, budget)`.
- **P2 Manager**: stateful `TradeManager` wrapper with `on_bar(bar, snapshot) -> list[TradeAction]`; state serializable for restart.
- **P3 Batch + parity**: `plan_many(...)` releases the GIL (`py.detach`); Arrow C-Stream `PyCapsule` for bar batches where bulk.
- **P4 Reconcile**: `Entry`/`oco` and `TRAILING_STOP` become thin adapters over core `StopRule`/`TrailRule`/`TargetLadder`; keep deprecated aliases for one release.
- Decimal round-trip: values cross as `decimal.Decimal` (string/integer based), never `float`; reject floats at the boundary.

## 3. Test Plan (TDD)

`tests/` only (pytest): `test_trade_plan_parity.py` consumes the core golden vectors (spec -> plan JSON, bars -> actions) and asserts byte-equal Decimal strings;
Decimal round-trip + float-rejection tests; `mypy --strict` stubs; `py.detach` smoke under threads; legacy `declarative.py` behaviour regression tests before P4.
Gates: `cargo check --workspace --profile prod`, `maturin develop`, `pytest -q`.

## 4. Dependencies & Tier Notes

L4: depends on `tantra-core` only for these types (no market/runtime edges). Blocks the strategies plan 0003.

## 5. Open Questions

- Ship schema stubs (`.pyi`) generated from `schemars` or hand-written?
