# `tantra-ffi` — Codegen Reference

Documents `crates/tantra-ffi-codegen/src/lib.rs`: deterministic code generator producing
three artifacts from the canonical `tantra_core` wire types.

## Generated Artifacts

| Artifact | Function | Description |
|----------|----------|-------------|
| JSON Schema | `domain_schema()` | Combined JSON Schema document (draft 2020-12) |
| OpenAPI 3.1 | `openapi_document()` | OpenAPI document for REST surface |
| Python stubs | `pyi_stubs()` | `.pyi` type stubs for `tantra._tantra` |

## Determinism

- Pure generators perform **no I/O** — identical inputs always produce identical output.
- The single sanctioned I/O entry point is `write_all()`, driven by the `tantra-codegen` CLI binary (`main.rs`).
- Artifacts are committed and diffable — any wire type change bumps `SCHEMA_VERSION` (mirrors `tantra_core::SCHEMA_VERSION`).

## Wire Types Covered

`OrderRequest`, `OrderAck`, `FillReport`, `OrderEvent`, `CancelRequest`, `ModifyRequest`,
`FeeBreakdown`, `Bar`, `Tick`, and all `tantra_core` wire types.

## Verification

Run with `make codegen` — re-generated artifacts verified in CI.

## Related

- `tantra-core/src/lib.rs` — `SCHEMA_VERSION: u32 = 8`, `API_VERSION: &str = "v1"`.
- `tantra-core/src/types.rs` — `Price`, `Quantity`, `Money` (schema sources).
- `python/tantra/_tantra.pyi` — generated type stubs.
