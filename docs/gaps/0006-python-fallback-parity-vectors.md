# 0006 — Pure-Python copies of Rust domain logic without parity vectors

**Status**: open
**Filed**: 2026-11-23 — workspace design review (root plan 0021) · **Kind**: duplication · **Severity**: high
**Plan**: [0005](../plans/0005-design-review-2026-11.md)

## What's stubbed or hardcoded

The wheel ships second implementations of Rust domain logic (full table in plan 0005 §1):

- `python/tantra/risk.py` (`tantra-risk`), `python/tantra/sizing.py` (`tantra-risk/src/sizing_gate.rs`), `python/tantra/position.py` / `portfolio.py` / `order_state.py` (`tantra-ledger-portfolio`, ledger OMS), `python/tantra/options.py` (Black-Scholes, `tantra-market-pricing`), `python/tantra/quant.py` (`tantra-ledger-allocation`, `tantra-agent-forecast`, `tantra-agent-panel`), `python/tantra/metrics.py`, `calendar.py`, `session.py`, `python/tantra/indicators/` (`tantra-market-indicators`).
- Several modules self-label as a "stand-in closure for tantra-examples gap 0006/0001" (`python/tantra/position.py:2`, `python/tantra/quant.py:2`, `python/tantra/store.py:2`, `python/tantra/risk.py:21`), but no upstream gap doc existed in this repo; this document is that record.
- `python/tantra/quant.py:4-12` states "Rust crates remain the canonical engines; this is the wheel learning-path surface": a deliberate second implementation with no cross-check.
- Golden vectors exist only for paper: `python/tests/golden/paper_golden.json`, `python/tests/test_paper_golden_identity.py`, `python/tests/test_l2_native_parity.py`. No parity tests exist for position, risk, sizing, options, quant, indicators or metrics.

## Why

Numerical, tax-lot or risk-rule divergence between the SDK (research) and the Rust engines (live) is invisible. Research/live parity, a stated NautilusTrader-derived principle (AGENTS.md section 7), cannot be tested. Floats in the Python copies also risk breaking the zero-floats policy.

## How to close it

Per module choose one of:
1. Bind the Rust engine through PyO3 and keep the Python class as a thin facade (position/portfolio, risk, sizing, options pricing, quant allocation, indicators), or
2. Generate golden vectors from the owning Rust crate into `python/tests/golden/*.json` and assert the Python fallback against them with `hypothesis`.

Order: risk ([0003](0003-python-risk-never-uses-native-engine.md)), position/portfolio, sizing, options, indicators, metrics, quant. Add a CI job that regenerates the vectors from the Rust crates and fails on diff.

**Verification**: `pytest -q python/tests/test_*_parity.py`; vectors produced by `cargo test -p <crate> --test golden_export --profile prod`; `ruff check .`, `mypy --strict python/tantra`.

## Related

- root gaps 0013 (risk gate), 0014 (unified enums/position model), 0015 (pricing/quant single source), 0016 (indicator parity suite).
- Extends root plan 0019 P4.5 (models): adds quant.py, metrics.py, indicators, store.py and the missing-parity-tests angle.
- [0003](0003-python-risk-never-uses-native-engine.md).
