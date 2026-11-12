# `tantra-ffi` — PyO3 Value Objects Reference

Documents `crates/tantra-ffi-py/src/types.rs`: canonical value-object pyclasses exposing
`tantra_core` types to Python as exact-decimal value objects.

## PyClasses

| PyClass | Rust Type | Purpose |
|---------|-----------|---------|
| `Price` | `tantra_core::Price` | Exact decimal price (non-negative, validated) |
| `Quantity` | `tantra_core::Quantity` | Exact decimal quantity (non-negative) |
| `Currency` | `tantra_core::Currency` | ISO 4217 currency (INR/USD/EUR/GBP) |
| `Exchange` | `tantra_core::Exchange` | Indian market venue (NSE/BSE/NFO/MCX/CDS) |
| `InstrumentId` | `tantra_core::InstrumentId` | Canonical `EXCHANGE:SYMBOL` identifier |
| `OrderSide` | `tantra_core::OrderSide` | `BUY` / `SELL` |
| `TimeInForce` | `tantra_core::TimeInForce` | `DAY` / `IOC` / `GTC` |
| `OrderStatus` | `tantra_core::OrderStatus` | Order lifecycle status |

## Conversion Pattern

Every `Price`/`Quantity` crosses the FFI boundary as an exact `decimal.Decimal`
via `crate::decimal` helpers:
- `pydecimal_to_decimal(obj)` — Python `Decimal` → `rust_decimal::Decimal` (via exact string)
- `decimal_to_pydecimal(py, d)` — `rust_decimal::Decimal` → Python `Decimal`

No `f32`/`f64` crosses the FFI boundary — Python `decimal.Decimal` ↔ Rust `Decimal`
round-trips through exact string forms.

## Custom Exceptions

| Exception | Purpose |
|-----------|---------|
| `RiskRefused` | Pre-trade risk gate refused an order |
| `ConversionError` | FFI boundary conversion failure |

## Module Registration

`init_module(m)` registers all classes, exceptions, and submodules onto the
`tantra._tantra` PyO3 module (ABI3, py310+).

## Related

- `crates/tantra-ffi-py/src/decimal.rs` — Decimal conversion helpers.
- `crates/tantra-ffi-py/src/market.rs` — `Bar`, `Tick` pyclasses.
- `crates/tantra-ffi-py/src/orders.rs` — `OrderRequest`, `OrderAck` pyclasses.
- `crates/tantra-ffi-py/src/decision.rs` — `Decision` pyclass.
- `crates/tantra-ffi-py/src/risk.rs` — `RiskEngine` pyclass.
- `crates/tantra-ffi-py/src/runner.rs` — `StrategyRunner` pyclass.
