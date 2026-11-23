# 0004 — Hand-written stub codegen and no drift gate for generated artifacts

**Status**: open
**Filed**: 2026-11-23 — workspace design review (root plan 0021) · **Kind**: design-flaw · **Severity**: high
**Plan**: [0005](../plans/0005-design-review-2026-11.md)

## What's stubbed or hardcoded

- `crates/tantra-ffi-codegen/src/lib.rs:252-258` — `pyi_stubs()` returns a raw string literal ("This string is a contract... Do not reformat it"). It is not derived from the `#[pyclass]` items, so a new method in `crates/tantra-ffi-py/src/*.rs` silently diverges from `python/tantra/_tantra.pyi`.
- `.github/workflows/ci.yml` runs fmt/clippy/cargo test/maturin develop/pytest only: no `make codegen && git diff --exit-code`, no `mypy --strict`, no regeneration check for `scripts/gen_client_models.py`.
- `Makefile:58-63` — the `codegen` target only echoes file names.
- `python/tantra/client/_models.py:1-5` is generated from a sibling-repo path: `scripts/gen_client_models.py:24` reads `tantra-runtime/.../openapi.v2.json`, so a standalone checkout cannot regenerate it.
- `crates/tantra-ffi-codegen/src/lib.rs:161-250` emits a second OpenAPI document (`/health`, tags orders/positions, ...) from tantra-core definitions, distinct from the runtime's `openapi.v2.json` (`schema/openapi.json` vs the runtime file).

## Why

Stub drift hands wrong types to IDE and mypy users. Drift is already visible: `risk.rs` exposes `suspend_algo`, `reactivate_algo`, `unregister_algo` while the `RiskEngine` stub block at `python/tantra/_tantra.pyi:205-225` is 21 lines. Two competing OpenAPI documents are confusing and violate single-source DTOs (`.agents/rules/interface-first-and-modularity.md`).

## How to close it

1. Generate stubs from PyO3 introspection (`pyo3-introspection` / `experimental-inspect`), or at minimum add a pytest that enumerates `dir(tantra._tantra)` and compares class/method names with `_tantra.pyi`.
2. CI step: `make codegen && git diff --exit-code schema python/tantra/_tantra.pyi`.
3. Add `mypy --strict python/tantra` to CI.
4. Vendor `openapi.v2.json` into `schema/` with a hash check, or make `scripts/gen_client_models.py` take a path argument; add a regeneration diff check for `_models.py`.
5. Retire the generated `schema/openapi.json` in favour of the runtime's document.

**Verification**: new `python/tests/test_stub_matches_native.py`; `make codegen` produces a clean diff; `cargo clippy --all-targets -- -D warnings`, `make check`, `mypy --strict python/tantra`, `pytest -q`.

## Related

- root gap 0022 (one canonical OpenAPI document and generated clients); root gap 0029 (generated-artifact drift).
- [0003](0003-python-risk-never-uses-native-engine.md) (stub block for `RiskEngine` must grow).
- root plan 0023 (CI).
