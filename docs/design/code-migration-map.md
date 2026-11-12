# `tantra-ffi` — Historical Migration Map (honba-tamashii → tantra-ffi)

> **Tier**: Tier 4 (Depends on `tantra-core`, `tantra-risk`, `tantra-market`, `tantra-runtime`)
> **Source**: `honba-workspace/honba-tamashii`
> **Target**: `tantra-ffi`
> **Status**: Migration complete (all milestones done).

## Sub-Crate & Directory Mapping

| Source (`honba-tamashii/`) | Target (`tantra-ffi/`) | Action |
| :--- | :--- | :--- |
| `Cargo.toml` | `Cargo.toml` | Update workspace dependencies (`tantra-core`, `tantra-risk`, `tantra-market-finance`, `tantra-market-feed`, `tantra-market-store`). |
| `pyproject.toml` | `pyproject.toml` | Rename package `honba` → `tantra`, module-name `tantra._tantra`. |
| `crates/honba-tamashii-codegen` | `crates/tantra-ffi-codegen` | Replace `honba` → `tantra` across codegen templates and tests. |
| `crates/honba-tamashii-py` | `crates/tantra-ffi-py` | Rename `#[pymodule] fn _honba` → `fn _tantra`; update imports to `tantra_*`. |
| `python/honba/` | `python/tantra/` | Rename package directory and replace `honba` / `_honba` imports with `tantra` / `_tantra`. |
| `_honba.pyi`, `__init__.pyi` | `_tantra.pyi`, `__init__.pyi` | Update stub files. |

## Verification Commands

```bash
# Run from the repository root
grep -rn "#\[cfg(test)\]" crates/*/src/ && exit 1 || true
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --workspace
```

## Migration Milestone Status

| Milestone | Status |
|-----------|--------|
| `tantra-ffi-codegen` ported (JSON Schema + OpenAPI + `.pyi` stubs) | Complete |
| `tantra-ffi-py` ported (PyO3 ABI3 extension `tantra._tantra`) | Complete |
| `python/tantra/` SDK ported (`Strategy`, `Parameter`, `indicators`, `sizing`, `session`, `data`, `cli`) | Complete |
| `pyproject.toml` (maturin ABI3 build config) | Complete |
| Decimal round-tripping verified | Complete |
| GIL release (`py.detach`/`py.allow_threads`) verified | Complete |
| Arrow PyCapsule zero-copy export verified | Complete |
| `cargo test --workspace` | Passing |
| `pytest` under `python/tests/` | Passing |
| Zero inline `#[cfg(test)]` in `src/` | Complete |
| `cargo fmt --check` | Clean |
| `cargo clippy --all-targets -- -D warnings` | Clean |
