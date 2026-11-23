# 0005 — Linux-only abi3 wheel, no release pipeline, no version sync

**Status**: open
**Filed**: 2026-11-23 — workspace design review (root plan 0021) · **Kind**: deployment · **Severity**: high
**Plan**: [0005](../plans/0005-design-review-2026-11.md)

## What's stubbed or hardcoded

- `pyproject.toml:12-16` — classifier only `Operating System :: POSIX :: Linux`; `.github/workflows/ci.yml` builds on ubuntu-latest with `maturin develop` only: no `maturin build --release`, manylinux, macOS, Windows, sdist or PyPI trusted-publish job.
- `Cargo.toml:43` — pyo3 `abi3-py310`: the stable ABI is incompatible with free-threaded 3.13t/3.14t builds, and `#[pymodule]` at `crates/tantra-ffi-py/src/lib.rs:67` has no `gil_used = false`. `auto-initialize` is enabled as a workspace dependency feature (`Cargo.toml:43`) and should be test-only.
- `pyproject.toml:7` `version = "0.1.0"` and `Cargo.toml:11` `version = "0.1.0"` are duplicated by hand; `[tool.maturin] features = ["pyo3/extension-module"]` at `pyproject.toml:29`.
- `.cargo/config.toml` hardcodes `PYO3_PYTHON = "/usr/bin/python3"` (its comment says a conda path); CI overrides it by env.
- Path deps `../tantra-core`, `../tantra-risk`, `../tantra-exec/...` (`Cargo.toml:17-19`): an sdist or PyPI build outside the workspace cannot resolve them.
- `pyproject.toml:21-24` declares `pyarrow` and `pydantic` optional, but `python/tantra/store.py:22-23` imports pyarrow unconditionally, `python/tantra/wire/*` uses pydantic, and `python/tantra/__init__.py` imports `tantra.session`, `strategy`, ... eagerly.

## Why

`pip install tantra` cannot work for macOS/Windows users or from an sdist, there is no way to ship a tagged release, and free-threaded Python users get a GIL-reenabling warning or an import failure. The AGENTS.md portability statement (linux x86_64 + aarch64 wheels) is not backed by any pipeline.

## How to close it

1. Add `.github/workflows/release.yml`: maturin-action / cibuildwheel matrix for manylinux2014 x86_64 + aarch64, macOS universal2, Windows; sdist with vendored sibling crates or published crates; PyPI trusted publishing on tags.
2. Single version source: `dynamic = ["version"]` read from Cargo.
3. Remove `auto-initialize` from non-test builds; drop the hardcoded `PYO3_PYTHON`.
4. Decide abi3 vs per-version wheels for 3.14t; add `gil_used = false` only after [0010](0010-pyclass-borrow-under-detach.md).
5. Smoke test `python -c "import tantra; assert tantra.__version__ == ..."` on 3.10-3.14; make pyarrow/pydantic imports lazy or required.

**Verification**: release workflow dry-run on a branch; `maturin build --profile prod` locally; `cargo check --workspace --profile prod`, `pytest -q`.

## Related

- root plan 0023 (build, CI, release engineering); root gap 0025 (non-reproducible builds); root gap 0026 (licensing/attribution of the published wheel).
- [0010](0010-pyclass-borrow-under-detach.md).
