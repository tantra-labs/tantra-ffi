# 0002 — Workspace declares unused `tantra-market-*` dependencies

**Status**: open

## What's stubbed or hardcoded

`tantra-ffi/Cargo.toml` `[workspace.dependencies]` declares:

```toml
tantra-market-finance = { path = "../tantra-market/crates/tantra-market-finance" }
tantra-market-feed    = { path = "../tantra-market/crates/tantra-market-feed" }
tantra-market-store   = { path = "../tantra-market/crates/tantra-market-store" }
```

with the comment *"declared per the Tier-4 playbook so the SDK can bridge
market data into Python; consumed by future data-bridge features."* But **no
crate in this workspace depends on them**:

- `crates/tantra-ffi-codegen/Cargo.toml` depends only on `tantra-core`,
  `serde`, `serde_json`, `schemars`.
- `crates/tantra-ffi-py/Cargo.toml` depends only on `tantra-core`,
  `tantra-risk`, `pyo3`, `arrow`, `rust_decimal`, `chrono`, `serde`,
  `serde_json`, `thiserror`, `tracing`, `uuid`.
- `Cargo.lock` contains **zero** `tantra-market` packages, and no
  `tantra_market_*` symbol is referenced anywhere in `crates/` or `python/`.

## Why

The Tier-4 playbook planned a future market-data bridge (feed bars/ticks into
Python). The workspace deps were declared in anticipation; the bridge was never
implemented, so the declarations are dead weight that also make the workspace
reach across to `tantra-market` for no current consumer.

## How to close it

1. Either remove the three `tantra-market-*` entries from
   `[workspace.dependencies]` (atomic, one commit), or
2. implement the data-bridge feature in `tantra-ffi-py` that actually consumes
   one of them (e.g. exposing `tantra-market-store` lakehouse reads through the
   SDK's `data.py`).
3. Verify: `cd tantra-ffi && cargo check --workspace --profile prod` and
   `make test`.

## Verification

`cargo check --workspace --profile prod` passes without the declarations (or
with the new bridge consuming them); `Cargo.lock` is consistent with the
result.
