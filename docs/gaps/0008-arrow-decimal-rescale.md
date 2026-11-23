# 0008 — Arrow decimal export truncates silently; timestamps are microseconds only

**Status**: open
**Filed**: 2026-11-23 — workspace design review (root plan 0021) · **Kind**: design-flaw · **Severity**: medium
**Plan**: [0005](../plans/0005-design-review-2026-11.md)

## What's stubbed or hardcoded

- `crates/tantra-ffi-py/src/arrow_bridge.rs:38-45` — `scaled.rescale(8); scaled.mantissa()`. `rust_decimal::Decimal::rescale` truncates sub-1e-8 digits and, when the value would overflow 96 bits, stops early at a smaller scale, so the mantissa is wrong for `Decimal128(38, 8)`. The result is not checked.
- `crates/tantra-ffi-py/src/arrow_bridge.rs:122,181,225` — `timestamp_micros()`, while the Python side uses nanoseconds (`python/tantra/backtest/l2_sim.py:545-556`; `python/tantra/store.py:244` `ts // 1_000_000_000`): ns to micros precision is lost in the Arrow export.
- `python/tantra/store.py` writes `decimal128(38,10)` (see its schema comment) whereas the FFI Arrow bridge and the workspace rule say `Decimal128(38, 8)`: two precisions for the same lakehouse column family.

## Why

A quantity with nine or more fractional digits is truncated without any error, violating the zero-silent-loss intent of the zero-floats policy. Two scales make joins or concatenation of bridge output with the Parquet store fail or require casts; micros timestamps cannot round-trip ns tick data.

## How to close it

1. Replace `rescale` with `checked_mul(10^8)` / `round_dp_with_strategy` and return `ConversionError` when scale 8 would lose information (strictness configurable).
2. Align `python/tantra/store.py` with the lakehouse constant owned by tantra-data / tantra-core (see root gap 0018); pin one scale workspace-wide.
3. Expose a nanosecond column (`Timestamp(Nanosecond)`) in all three export paths.
4. Add property tests for Decimal to Arrow to Decimal round trips including boundary magnitudes.

**Verification**: proptest in `crates/tantra-ffi-py/tests/arrow_decimal_roundtrip.rs`; hypothesis in `python/tests/test_arrow_roundtrip.py`; `cargo clippy --all-targets -- -D warnings`, `make check`, `pytest -q`, `make prod`.

## Related

- root gap 0018 (lakehouse manifest/ref contract and byte-compat fixtures); `tantra-core/docs/gaps/0010-decimal-wire-scale-pinning.md` (decimal wire scale pinning).
- [0011](0011-decimal-extraction-strictness.md).
