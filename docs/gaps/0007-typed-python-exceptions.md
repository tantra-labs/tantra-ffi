# 0007 — Stringly-typed risk refusals and a flat exception hierarchy

**Status**: open
**Filed**: 2026-11-23 — workspace design review (root plan 0021) · **Kind**: design-flaw · **Severity**: medium
**Plan**: [0005](../plans/0005-design-review-2026-11.md)

## What's stubbed or hardcoded

- `crates/tantra-ffi-py/src/error.rs:16-18` — `RiskRefused::new_err(format!("rule={}: {}", ...))`: the rule is embedded in the message; there is no `.rule` / `.code` attribute.
- `crates/tantra-ffi-py/src/lib.rs:36-37` — `RiskRefused` and `ConversionError` derive `PyException` directly (not `ValueError` or a shared base); only two exception types cover the whole boundary.
- `python/tantra/risk.py:185` defines a second, unrelated `RiskRefused` dataclass, and `python/tantra/types.py:30` re-exports the native one under the same name. Docs mention a third name, `RiskRefusalError` (`python/tantra/risk.py:15,117`), that does not exist.

## Why

Callers must regex the message to branch on rules such as `sebi_otr_breach`; `except ValueError` misses `ConversionError`; three same-named concepts cause wrong imports. This violates the typed-error contract in `.agents/rules/interface-first-and-modularity.md` section 1.3 at the Python boundary.

## How to close it

1. Define `TantraError` as the base exception; `RiskRefused(TantraError)` carrying `rule`, `code`, `context` attributes (set through `PyErr` args / `setattr`); `ConversionError(TantraError, ValueError)`.
2. Use the runtime `ErrorCode` literal set (`python/tantra/client/_models.py:13`) as the stable code list.
3. Rename the audit dataclass at `python/tantra/risk.py:185` to `RiskRefusalRecord`; fix the `RiskRefusalError` doc references.
4. Update `_tantra.pyi` stubs (see [0004](0004-stub-and-codegen-drift-gate.md)).

**Verification**: pytest contract tests asserting `.rule` / `.code` values for each refusal path and that `ConversionError` is a `ValueError`; `cargo clippy --all-targets -- -D warnings`, `maturin develop`, `pytest -q`, `mypy --strict python/tantra`.

## Related

- [0003](0003-python-risk-never-uses-native-engine.md) (refusals flow through this type once native risk is bound).
- [0011](0011-decimal-extraction-strictness.md) (conversion errors raised from the decimal boundary).
