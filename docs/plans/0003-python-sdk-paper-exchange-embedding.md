# 0003 — Python SDK Paper Exchange Embedding (`tantra.paper`)

**Status**: Implemented (2026-11-16, T14.10 wheel embedding + T14.11 cross-repo examples).
**Track**: T14 (P2) · **Phase**: 5 (Python wheel / SDK surface)
**Owning repo**: `tantra-ffi` · **Master plan**: root `docs/plans/0007-*.md`

## Why

The wheel already ships an execution SDK (`tantra.backtest.session`, `tantra.backtest.simulated`,
`tantra.backtest.l2_sim`) — but the L2 port is a **pure-Python reference with no native
backend**: `l2_sim.py` explicitly documents `backend="native"` → `NotImplementedError` (the
compiled engine is absent from `_tantra`). Meanwhile the Rust `tantra-exec-paper` engine (see
`tantra-exec/docs/plans/0003`) is the canonical matching engine. The Python SDK should
**embed the same engine** so that a Python strategy/example session produces byte-identical
fills to the Rust backtest, paper server, and WASM UI — the research-live parity invariant
(AGENTS §4.3.3) extended to the Python plane.

This is consistent with the standing FFI policy (`tantra-ffi/docs/plans/0001`): user-facing
strategy authoring lives in Python; high-frequency/engine math lives in Rust; the boundary is
PyO3 + Arrow zero-copy with smart GIL management.

## What shipped (T14.10 + T14.11)

- **D1 — native `PaperExchange` pyclass** (`crates/tantra-ffi-py/src/paper.rs`), registered
  via `paper::init` in `crates/tantra-ffi-py/src/lib.rs` and the `tantra-exec-paper` workspace
  dep in `Cargo.toml` + `crates/tantra-ffi-py/Cargo.toml`:
  - `PaperExchange(initial_cash, *, seed=None)`; `place_order(order, ts_iso) -> str`
    (returns `PAPER-0001`…), `cancel_order`, `amend_order(broker_order_id, limit_price,
    quantity, ts_iso)`, `feed_bar`, `feed_tick`, `advance_to`, `set_market_price`,
    `fills() -> list[FillReport]`, `events() -> list[dict]`, `positions() -> dict`,
    `cash()`/`equity()` → Decimal, `depth() -> (bid, ask)`, `order(id) -> dict`.
  - Engine steps run under `py.detach` (pyo3 0.30's GIL-release API, the `runner.rs`
    pattern); timestamps cross as RFC3339 UTC strings (empty = Unix epoch); every
    price/quantity is `decimal.Decimal` (Zero Floats Policy).
  - Seeded mode (D3): `seed=` builds `PaperExchange::new(cash).with_latency(NetworkLatency::new(10, 5, seed))`
    — deterministic; the same seed reproduces the same tape.
- **D2 — wheel module `tantra/paper/`**:
  - `PaperSession(cash, seed)` facade: `place_order`/`cancel_order`/`amend_order`/`feed_bar`/
    `feed_tick`/`advance_to`/`set_market_price`/`fills`/`events`/`positions`/`cash`/`equity`/
    `depth`/`order` + `run(strategy, bars)` (mirrors `tantra.backtest.session.Session`: sets
    `_in_callback = True` for `on_start`/`on_bar`, flushes the buffered compiled
    `OrderRequest`s onto the exchange, marks equity per bar, returns `PaperResult`).
  - `wire.py::fills_wire(session)` — REST `FillReport` wire shape (fill_id, order_id,
    client_order_id, instrument, side, price, quantity, algo_id, timestamp, fee).
  - `l2_sim.py` upgrade: `resolve_l2_backend("native")` → `"native"` (no
    `NotImplementedError`); `L2Execution(backend="native")` runs the new `_NativeL2` adapter
    (OrderIntent → native `OrderRequest` with `algo_id="paper"`, QuoteTick/TradeTick →
    native `Tick`, native `FillReport`s → `Fill` events on `drain_events()`, mirrors
    `cash`/`positions`/`working_orders`/`book`). `backend="python"` keeps `_PythonL2`.
    The ex-0006 `# stand-in` reference was removed from l2_sim's backend section (closed).
  - `PaperExchange` re-exported from the top-level `tantra/__init__.py`; `tantra.paper`
    stays lazily imported (like `tantra.backtest`). `make codegen` adds the `PaperExchange`
    block to `_tantra.pyi`.
- **Tests (TDD, `python/tests/`)**: `test_paper_native.py` (limit-buy fill on bar cross +
  the golden tape: exactly 4 fills, `100.6667` avg, cash back to `1_000_000`, 7 events),
  `test_paper_session.py` (seeded run twice → identical `fills()`/`equity()`; `run(strategy,
  bars)` returns fills), `test_l2_native_parity.py` (coincident-tape parity python vs
  native), `test_gil.py` (two threads drive engine steps without deadlock), `test_paper_wire.py`
  (wire shape). Golden oracle at `python/tests/golden/paper_golden.json` (P4 cross-repo
  reuse). **Full wheel suite: 505 passed.**
- **T14.11 (cross-repo)**: `tantra-examples/production/paper_trading.py` deterministic
  seeded `PaperSession` example + `tests/unit/test_paper_trading_example.py` (two runs
  identical); `tantra-strategies/tests/test_paper_session_strategy.py` (a `Strategy`
  subclass drives a `PaperSession`, deterministic).

## Recorded deviations

1. **Seeded latency constructor**: `tantra_exec_paper::NetworkLatency` has no `seeded()`
   constructor (only `new(mean_us, std_dev_us, seed)`); seeded mode uses
   `NetworkLatency::new(10, 5, seed)` (mean 10µs / std 5µs, deterministic via `SeededRng`).
2. **pyo3 0.30**: `Python::allow_threads` is removed; engine steps release the GIL via
   `py.detach(|| ...)` (the `runner.rs` pattern).
3. **Engine matching semantics (verified against the shipped engine)**: resting limits the
   market trades through fill at the *crossing* market price (price improvement), with the
   bar's synthetic depth print participation-capped (half the bar volume); `positions()`
   keeps flat (zero) entries; a market order with no contra liquidity raises
   `NoMarketPrice`; naked sells are allowed (no `long_only` gate).
4. **l2_sim native-vs-reference parity scope**: full-tape parity between the old top-of-book
   reference and the paper-exchange engine is NOT asserted (different matching models —
   quotes vs resting book). Parity is asserted on the coincident tape and the golden tape
   (follow-on 2, closed 2026-11-16); the canonical cross-language parity oracle is the
   golden tape (`paper_golden.json`), re-verified by P4. The native backend refuses `costs=`
   (engine prices with zero costs) and derives positions from fills (seeding unsupported).
5. **Facade GTD**: closed 2026-11-16 (follow-on 1) — `place_order(gtd_until=)` exposes
   `submit_order_gtd`; see "Follow-ons closed".
6. **Environment ruff drift**: the shared venv's `ruff 0.17.4` enables FURB157
   (verbose-`Decimal` constructor), which fires on the repo's long-standing
   `Decimal("100")` style in untouched files (421 pre-existing hits). Changed paths are
   ruff-clean under 0.17.4 (`Decimal(100)` numeric form in new code); the pre-existing
   hits are out of scope.

## Follow-ons closed (2026-11-16)

1. **GTD facade exposure** (`930a6bf`): `PaperExchange.place_order` gained keyword-only
   `gtd_until: str | None = None` — when set, the pyclass calls `submit_order_gtd` (the
   order's `expires_ts`; the first `advance_to` at/past the instant expires it →
   `CANCELLED` + `cancelled` event); `PaperSession.place_order` passes it through; the
   `_tantra.pyi` stub and codegen template updated (`make codegen`). Tests:
   `python/tests/test_paper_gtd.py`. Deviation 5 closed.
2. **l2_sim native golden parity** (`7dc2419`): `python/tests/test_l2_native_parity.py`
   asserts the T14.14 golden economics through the native backend — the
   `paper_golden.json` tape (BUY 100@101, BUY 50@100, SELL MARKET 150 → 4 fills,
   sell avg `100.6667`, cash back to `1_000_000`, net 0) as a touch-size-full crossing
   both the top-of-book reference and the paper engine reproduce identically.
   `l2_sim.py` records the permanent scope: the native backend runs the paper-exchange
   engine; reference-vs-native parity is asserted on the coincident + golden tapes only;
   it is NOT a byte-identical port of the top-of-book reference; the canonical
   cross-language parity oracle is `paper_golden.json` (T14.14). Deviation 4 updated.

## Verification (green at time of writing)

```bash
cd tantra-ffi
cargo check --workspace --profile prod
cargo test --workspace --profile prod          # with LIBRARY_PATH for -lpython3.12
cargo clippy --workspace --all-targets --profile prod -- -D warnings
cargo fmt --check
make codegen   # regenerates python/tantra/_tantra.pyi
../.venv/bin/maturin develop
../.venv/bin/python -m pytest python/tests -q  # 505 passed
../.venv/bin/ruff check python/tantra/paper python/tantra/backtest/l2_sim.py python/tests (changed paths)
```

## Cross-repo dependencies

- **Requires** `tantra-exec/docs/plans/0003` (the `tantra-exec-paper` engine) — SHIPPED (P0).
- Uses `tantra-runtime/docs/plans/0005` golden vectors (T14.14) as the parity oracle —
  the golden tape from `paper_parity_tests.rs` is re-embedded at
  `python/tests/golden/paper_golden.json`.
- `tantra-examples` consumes `tantra.paper` for its paper-trading examples (T14.11, shipped);
  next step: P3 `tantra-ui` plan 0008 (WASM paper studio) / P4 parity + docs.
