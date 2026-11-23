# Gaps Index — `tantra-ffi`

Per workspace rule `.agents/rules/gap-tracking.md`:
- **Gaps** (`docs/gaps/XXXX-*.md`) are individual missing features, endpoints, or stubs.
- **Plans** (`docs/plans/XXXX-*.md`) are collections of gaps or multi-phase architectural features.
- When a gap is implemented and verified, remove the document from this
  directory and record it in the README "Closed" table below.

## Open Gaps

| # | Title | Scope | Status |
|---|-------|-------|--------|
| [0003](0003-python-risk-never-uses-native-engine.md) | `tantra.risk` never reaches the compiled RiskEngine | high design-flaw | open — [plan 0005](../plans/0005-design-review-2026-11.md) |
| [0004](0004-stub-and-codegen-drift-gate.md) | Hand-written stub codegen and no drift gate for generated artifacts | high design-flaw | open — [plan 0005](../plans/0005-design-review-2026-11.md) |
| [0005](0005-wheel-release-matrix.md) | Linux-only abi3 wheel, no release pipeline, no version sync | high deployment | open — [plan 0005](../plans/0005-design-review-2026-11.md) |
| [0006](0006-python-fallback-parity-vectors.md) | Pure-Python copies of Rust domain logic without parity vectors | high duplication | open — [plan 0005](../plans/0005-design-review-2026-11.md) |
| [0007](0007-typed-python-exceptions.md) | Stringly-typed risk refusals and flat exception hierarchy | medium design-flaw | open — [plan 0005](../plans/0005-design-review-2026-11.md) |
| [0008](0008-arrow-decimal-rescale.md) | Arrow decimal export truncates silently; micros-only timestamps | medium design-flaw | open — [plan 0005](../plans/0005-design-review-2026-11.md) |
| [0009](0009-strategy-runner-placeholder.md) | `StrategyRunner` GIL-free batch is a placeholder checksum | medium design-flaw | open — [plan 0005](../plans/0005-design-review-2026-11.md) |
| [0010](0010-pyclass-borrow-under-detach.md) | `#[pyclass]` borrow and re-entrancy under `py.detach` | medium design-flaw | open — [plan 0005](../plans/0005-design-review-2026-11.md) |
| [0011](0011-decimal-extraction-strictness.md) | Decimal extraction duck-types and accepts floats | medium design-flaw | open — [plan 0005](../plans/0005-design-review-2026-11.md) |

## Closed Gaps

| # | Title | Closed In |
|---|-------|-----------|
| 0001 | `tantra` CLI `backtest` is a stub; `serve`/`stub` subcommands are placeholders | Implemented 2026-11-14 (task T9.1): real `backtest` via `tantra.strategy.run`; `serve`/`stub` removed per gap-tracking §4 |
| 0002 | Unused `tantra-market-{finance,feed,store}` workspace deps (declared, nothing consumes them) | Removed 2026-11-13 (root plan 0003 Phase 4 / task T0.5) |

## Related

- [`docs/design/architecture.md`](../design/architecture.md) — crate topology and module map.
