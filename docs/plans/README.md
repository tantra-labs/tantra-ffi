# Plans Index — `tantra-ffi`

Per workspace rule `.agents/rules/gap-tracking.md`:
- Gaps are individual features (`docs/gaps/XXXX-*.md`).
- Plans are collections of gaps (`docs/plans/XXXX-*.md`).
- When implemented, plan documents are cleaned up from `docs/plans/` and recorded in this index.

## Active Plans

| # | Title | Target Scope | Status |
|---|-------|--------------|--------|
| [0004](0004-trade-planner-bindings.md) | Trade Planner Python Bindings (`tantra.trade_plan`) | `tantra-ffi` | Proposed — root plan `docs/plans/0008` |
| [0005](0005-design-review-2026-11.md) | tantra-ffi design review (2026-11): native-first bindings, parity vectors, typed errors & wheel release matrix | `tantra-ffi` | Proposed (2026-11-23) — root plan `docs/plans/0021` |

## Implemented Plans

| # | Title | Target Scope | Implemented In |
|---|-------|--------------|----------------|
| 0001 | Python-First Quant Engine Bridge Policy | `tantra-ffi` | Adopted standing policy in commit `c7bc420` |
| 0002 | Tantra Wheel Domain-Harness Surfaces — `tantra.portfolio`, `tantra.risk`, `tantra.options`, `tantra.metrics`, `tantra.calendar` (T13 Thrust A) | `python/tantra/` + `tantra-examples` consumers | 2026-11-16: wheel surfaces + tests in `9b354d5`/`3d5a1ac`/`f210c8a` (ffi); consumers retargeted + `_kernel` domain modules deleted in `25cb5df`/`1acabfb` (examples) |
| 0003 | Python SDK Paper Exchange Embedding — native `tantra.paper.PaperExchange` PyO3 binding over `tantra-exec-paper`, `l2_sim` native backend (removes `NotImplementedError`), deterministic seeded `PaperSession` for examples | `crates/tantra-ffi-py`, `python/tantra/paper/`, `python/tantra/backtest/l2_sim.py` | 2026-11-16: T14.10 wheel embedding (D1–D3 + P1–P4 tests, golden tape) + T14.11 examples/strategies consumers — see the root plan 0007 implemented row in `docs/plans/README.md` for deviations |
