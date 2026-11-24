# 0011 — Decimal extraction duck-types and accepts floats

**Status**: open
**Filed**: 2026-11-23 — workspace design review (root plan 0021) · **Kind**: design-flaw · **Severity**: medium
**Plan**: [0005](../plans/0005-design-review-2026-11.md)

## What's stubbed or hardcoded

- `crates/tantra-ffi-py/src/decimal.rs:18-30` — `object_decimal_string` duck-types on a `to_str` attribute, else calls `obj.str()`. A Python `float` (for example `0.1`, or `1e-7`, which stringifies as `"1e-07"`) is accepted and stringified; `Decimal::from_str` rejects exponent notation, so some inputs fail confusingly.
- `crates/tantra-ffi-py/src/decimal.rs:36-38` — `Decimal::from_str(&s)` only: no scale or precision cap and no NaN/Infinity handling (`Decimal("NaN")` yields a vague "invalid decimal").
- `python/tantra/types.py` `to_decimal` and several modules re-implement coercion independently (`python/tantra/sizing.py:9`, `python/tantra/options.py:22`).

## Why

The zero-floats policy (`.agents/rules/interface-first-and-modularity.md` section 2.3) should be enforced at the FFI boundary. Instead `Price(0.1)` works only by luck of `str()` repr, and `Decimal("1E+2")` produced by ordinary Python arithmetic fails at runtime.

## How to close it

1. In `pydecimal_to_decimal`, switch to `isinstance` checks: accept `decimal.Decimal`, `str`, `int`, and the native pyclasses; reject `float` and `bool` with `ConversionError` (see [0007](0007-typed-python-exceptions.md)).
2. Format via `format(d, "f")` (or use `Decimal::from_scientific`) so exponent notation is handled; reject NaN/Infinity with a specific message; cap scale.
3. Share one `to_decimal` in Python (`python/tantra/types.py`) and delete the module-local copies.
4. Document the accepted input types in `_tantra.pyi`.

**Verification**: hypothesis tests over `Decimal` strategies including exponents, NaN, Infinity and huge scale, plus explicit float/bool rejection cases, in `python/tests/test_decimal_boundary.py`; proptest in `crates/tantra-ffi-py/tests/decimal_boundary.rs`; `cargo clippy --all-targets -- -D warnings`, `pytest -q`, `mypy --strict python/tantra`.

## Related

- [0007](0007-typed-python-exceptions.md), [0008](0008-arrow-decimal-rescale.md).
- `tantra-core/docs/gaps/README.md#closed-gaps` gap `0003` (value-object invariants at construction).
