# 0003 — `tantra.risk` never reaches the compiled RiskEngine

**Status**: open
**Filed**: 2026-11-23 — workspace design review (root plan 0021) · **Kind**: design-flaw · **Severity**: high
**Plan**: [0005](../plans/0005-design-review-2026-11.md)

## What's stubbed or hardcoded

- `python/tantra/risk.py:72-84` — `_native_attr(name)` returns only `SCHEMA_VERSION` / `API_VERSION` and raises `RuntimeError("the tantra wheel ships no compiled risk engine")` for every other name. Every caller therefore falls back to the pure-Python risk path.
- `python/tantra/risk.py:56-63` — `_NATIVE` lists `RiskEngine`, `RiskLimits`, `RiskStage`, `TradingState`, `Command`, `RiskDecision`; `python/tantra/risk.py:106-123` — `limits_from_config` / `check_order` call into it, so the public `tantra.risk.check_order` is unconditionally broken on the native route.
- `crates/tantra-ffi-py/src/risk.rs:26-31,185-187` — the wheel does register a `RiskEngine` pyclass (`register_algo`, `suspend_algo`, ...) and `python/tantra/_tantra.pyi:205` declares it. `RiskLimits`, `TradingState`, `RiskStage` and `Command` are not bound.
- The docstring ("wheel ships no compiled risk engine") contradicts the shipped binding.

## Why

Callers that probe for the native engine fall back to the pure-Python reduce-only / epsilon rules, so backtests and live Python runs use a different gate than the SEBI-grade `tantra-risk` engine. Research/live parity is untestable and the pre-trade gate is not single or shared (root gap 0013). A stale error message also hides that the engine exists.

## How to close it

1. Bind `RiskLimits`, `TradingState`, `RiskStage`, `Command` and `RiskDecision` in `crates/tantra-ffi-py/src/risk.rs`; extend `crates/tantra-ffi-codegen/src/lib.rs` stubs and `python/tantra/_tantra.pyi`.
2. Make `python/tantra/risk.py` re-export the native types and delete `_native_attr`, the module `__getattr__` proxies (`RiskEngine: Any`) and the `_POSITION_EPS` fallback.
3. Pre-trade refusal must surface through the typed exception from [0007](0007-typed-python-exceptions.md).
4. Add a parity test: a table of orders to `(approved, rule code)` generated from `tantra-risk` as golden JSON and executed through the Python facade (see [0006](0006-python-fallback-parity-vectors.md)).

**Verification**: `python/tests/test_risk_native_parity.py` with golden JSON in `python/tests/golden/`; `cargo clippy --all-targets -- -D warnings`, `make check`, `maturin develop`, `pytest -q python/tests`, `mypy --strict python/tantra`, `make prod`.

## Related

- root gap 0013 (pre-trade risk gate not single, shared or fail-closed).
- [0006](0006-python-fallback-parity-vectors.md), [0007](0007-typed-python-exceptions.md), [0004](0004-stub-and-codegen-drift-gate.md).
- Extends root plan 0019 duplicate-model list (risk.py).
