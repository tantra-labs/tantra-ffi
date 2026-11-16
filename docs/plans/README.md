# Plans Index — `tantra-ffi`

Per workspace rule `.agents/rules/gap-tracking.md`:
- Gaps are individual features (`docs/gaps/XXXX-*.md`).
- Plans are collections of gaps (`docs/plans/XXXX-*.md`).
- When implemented, plan documents are cleaned up from `docs/plans/` and recorded in this index.

## Active Plans

| # | Title | Target Scope | Status |
|---|-------|--------------|--------|
| [0002](0002-tantra-wheel-domain-harness-surface.md) | Tantra Wheel Domain-Harness Surfaces — lift the examples' domain/math modules into the wheel: `tantra.portfolio`, `tantra.risk`, `tantra.options`, `tantra.metrics`, `tantra.calendar` (Thrust A of root plan 0006, T13) | `python/tantra/` (wheel) + consumers retargeted in `tantra-examples` | **Implemented 2026-11-16** — T13.1–T13.5 (see Implemented table) |
| [0003](0003-python-sdk-paper-exchange-embedding.md) | Python SDK Paper Exchange Embedding — native `tantra.paper.PaperExchange` PyO3 binding over `tantra-exec-paper`, `l2_sim` native backend (removes `NotImplementedError`), deterministic seeded `PaperSession` for examples | `crates/tantra-ffi-py`, `python/tantra/paper.py`, `python/tantra/backtest/l2_sim.py` | Proposed — T14 (P2); master plan root `docs/plans/0007` |

## Implemented Plans

| # | Title | Target Scope | Implemented In |
|---|-------|--------------|----------------|
| 0001 | Python-First Quant Engine Bridge Policy | `tantra-ffi` | Adopted standing policy in commit `c7bc420` |
| [0002](0002-tantra-wheel-domain-harness-surface.md) | Tantra Wheel Domain-Harness Surfaces — `tantra.portfolio`, `tantra.risk`, `tantra.options`, `tantra.metrics`, `tantra.calendar` (T13 Thrust A) | `python/tantra/` + `tantra-examples` consumers | 2026-11-16: wheel surfaces + tests in `9b354d5`/`3d5a1ac`/`f210c8a` (ffi); consumers retargeted + `_kernel` domain modules deleted in `25cb5df`/`1acabfb` (examples) |
