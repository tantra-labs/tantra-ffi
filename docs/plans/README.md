# Plans Index — `tantra-ffi`

Per workspace rule `.agents/rules/gap-tracking.md`:
- Gaps are individual features (`docs/gaps/XXXX-*.md`).
- Plans are collections of gaps (`docs/plans/XXXX-*.md`).
- When implemented, plan documents are cleaned up from `docs/plans/` and recorded in this index.

## Active Plans

| # | Title | Target Scope | Status |
|---|-------|--------------|--------|
| [0002](0002-tantra-wheel-domain-harness-surface.md) | Tantra Wheel Domain-Harness Surfaces — lift the examples' domain/math modules into the wheel: `tantra.portfolio`, `tantra.risk`, `tantra.options`, `tantra.metrics`, `tantra.calendar` (Thrust A of root plan 0006, T13) | `python/tantra/` (wheel) + consumers retargeted in `tantra-examples` | Proposed — phases A1–A5, rows T13.1–T13.5 |

## Implemented Plans

| # | Title | Target Scope | Implemented In |
|---|-------|--------------|----------------|
| 0001 | Python-First Quant Engine Bridge Policy | `tantra-ffi` | Adopted standing policy in commit `c7bc420` |
