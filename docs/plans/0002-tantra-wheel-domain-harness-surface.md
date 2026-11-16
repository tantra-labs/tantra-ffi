# 0002 — Tantra Wheel Domain-Harness Surfaces (Thrust A of root plan 0006)

**Status**: Active — Thrust A wheel lift shipped 2026-11-15 (A1–A5); the `tantra-examples`
consumer retarget is deferred (another agent is fixing the 73 pre-existing float-rooted failures
there; retarget + `_kernel/` deletion land after).
**Track**: T13 (rows T13.1–T13.5) · **Root master plan**: `docs/plans/0006-dismantle-kernel-harness.md`
**Owning repo**: `tantra-ffi` (wheel `python/tantra/`) → consumers retargeted in `tantra-examples`

## Symptom

Six domain/math modules still live in the `tantra_examples` learning path under
`tantra_examples/_kernel/` (`portfolio`, `risk`, `greeks`, `option`, `evaluator`,
`calendar`), duplicated from the bounded-context domain they belong to. The `tantra` wheel is
the canonical Decimal-canonical Python SDK surface (AGENTS §6.1) and the standing rule is
Consolidation Over Duplication (§4.1): shared domain/math logic belongs in the wheel, and the
examples consume it from there. Keeping it in `tantra_examples/_kernel/` also keeps the
misleading "kernel internals" name alive (root plan 0006).

## What stands in (to promote)

| Wheel surface | Source (in `tantra-examples`) | Public API | Consumers to retarget |
| :--- | :--- | :--- | :--- |
| `tantra.portfolio` | `_kernel/portfolio.py` (65 L) | `Account`, `Portfolio` | `_kernel/__init__.py` facade re-export (only consumer found — re-verify; delete if still unused) |
| `tantra.risk` | `_kernel/risk.py` (189 L) | `check_state`, `check_order`, `limits_from_config`, `RiskRefusal`, `RiskRefused`, `OrderRejected` (+ `_native_attr` probe) | `_kernel/runner.py` |
| `tantra.options` | `_kernel/greeks.py` (198 L) + `_kernel/option.py` (78 L) | `bs_greeks`, `bs_price`, `OptionKind`, `OptionStyle`, `OptionChain`, `OptionContract` | options examples 01–08, `tantra_examples/options/*`, `_kernel/greeks.py` (intra) |
| `tantra.metrics` | `_kernel/evaluator.py` (268 L) | `extract_metrics_from_bars` (+ exported helpers) | `screening/nl_support.py` |
| `tantra.calendar` | `_kernel/calendar.py` (101 L) | `ist_midnight_ns` (+ IST helpers) | `_kernel/ports.py` (moves with the harness) |

## How to close (per surface, one wave each)

1. **Promote** the module verbatim into `python/tantra/<surface>/` — public API and `__all__`
   byte-identical; rewrite only intra-package imports and the `# mirror:`/gap-citation
   comments to `# wheel surface (T13)`. The modules are already Decimal-canonical against
   the wheel (ex 0006 retarget); preserve that exactly. No I/O, no wall clock (domain
   purity, AGENTS §2.3).
2. **Test** — wheel tests in `python/tests/` (never inline): for `portfolio` the
   credit/debit/insufficient-funds and currency-mismatch invariants; for `risk` the
   `check_state` halt/reduce-only matrix, `limits_from_config` parsing and unknown-key
   refusal, and the `_native_attr` probe raising `RuntimeError` for the absent compiled
   classes; for `options` the Black-Scholes price/greeks against a known fixture and the
   option-chain model invariants; for `metrics` `extract_metrics_from_bars` on a small bars
   fixture; for `calendar` the IST-midnight arithmetic.
3. **Delete** the `_kernel/` source module and retarget its consumers (the retarget list in
   the table) to the wheel surface.
4. **Verify** — wheel suite green (only the 3 pre-existing failures: `test_risk.py` ×2,
   `test_indicators_registry.py::test_registry_total_matches_kernel`), `ruff check .` +
   `ruff format --check .` clean, `python -c "import tantra.<surface>"` works; the
   `tantra-examples` `tests/unit` baseline (841 passed / 73 failed / 3 errors / 50 skipped)
   gets **no new failures**.
5. **Docs** — update the plan index (this doc → Implemented on completion), the root master
   plan 0006 table, and the ffi HANDOFF; cite the closure in the `tantra-examples`
   consumers' commit messages.

## Phases

| Phase | Surface | Track row | Blocked on |
| :--- | :--- | :--- | :--- |
| A1 | `tantra.portfolio` | T13.1 | — |
| A2 | `tantra.risk` | T13.2 | — |
| A3 | `tantra.options` (greeks + option) | T13.3 | — |
| A4 | `tantra.metrics` | T13.4 | — |
| A5 | `tantra.calendar` | T13.5 | — |

Phases are independent (no cross-surface imports); they run one at a time because they share
the `_kernel/` package and the `_kernel/__init__.py` facade in `tantra-examples`.

## Non-goals

- No Rust/PyO3 changes (the compiled risk/trading-state classes remain a separate,
  already-documented surface — the pure-Python checks keep the `_native_attr` probe).
- The examples-harness modules (`runner`, `testing`, `service`, `ports`, `log`, `loader`,
  `manifest`, `config`) are NOT promoted here — they move to `tantra_examples/harness/`
  under Thrust B (`tantra-examples/docs/plans/0003-*.md`).
