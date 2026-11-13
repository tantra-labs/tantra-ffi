# Gaps Index — `tantra-ffi`

Per workspace rule `.agents/rules/gap-tracking.md`:
- **Gaps** (`docs/gaps/XXXX-*.md`) are individual missing features, endpoints, or stubs.
- **Plans** (`docs/plans/XXXX-*.md`) are collections of gaps or multi-phase architectural features.
- When a gap is implemented and verified, remove the document from this
  directory and record it in the README "Closed" table below.

## Open Gaps

| # | Title | Scope | Status |
|---|-------|-------|--------|
| [0001](0001-cli-stub-subcommands.md) | `tantra` CLI `backtest` is a stub; `serve`/`stub` subcommands are placeholders | `python/tantra/cli.py` | Stub |

## Closed Gaps

| # | Title | Closed In |
|---|-------|-----------|
| 0002 | Unused `tantra-market-{finance,feed,store}` workspace deps (declared, nothing consumes them) | Removed 2026-11-13 (root plan 0003 Phase 4 / task T0.5) |

## Related

- [`docs/design/architecture.md`](../design/architecture.md) — crate topology and module map.
