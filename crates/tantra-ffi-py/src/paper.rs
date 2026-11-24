//! Paper-trading exchange embedding: `PaperExchange`.
//!
//! Wraps the shipped `tantra-exec-paper` engine (root plan 0007, P0) as a
//! `tantra._tantra` pyclass. The engine is a deterministic, exact-decimal
//! order-driven simulator: prices/quantities cross the boundary as
//! `decimal.Decimal` (Zero Floats Policy) and timestamps as RFC3339 UTC strings
//! (an empty string means the deterministic Unix epoch, matching `market.rs`).
//!
//! Engine steps that do real work (`submit_order`, `feed_bar`, `feed_tick`,
//! `advance_to`, `cancel_order`, `amend_order`) release the GIL via
//! `py.detach` (see `runner.rs` for the same pattern); the read views
//! (`fills`, `positions`, `cash`, ...) are cheap and run with the GIL held.

use chrono::{DateTime, Utc};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyModule};

use crate::decimal::{decimal_to_pydecimal, pydecimal_to_decimal};
use crate::error::{conversion_err, parse_utc};
use crate::market::{Bar, Tick};
use crate::orders::{FillReport, OrderRequest};
use crate::types::{InstrumentId, price_from_any, quantity_from_any};

/// Parse an RFC3339 timestamp, treating the empty string as the Unix epoch
/// (the same convention as `market.rs`).
fn parse_ts(iso: &str) -> PyResult<DateTime<Utc>> {
    if iso.is_empty() {
        Ok(DateTime::<Utc>::UNIX_EPOCH)
    } else {
        parse_utc(iso)
    }
}

fn side_code(side: &tantra_core::OrderSide) -> &'static str {
    match side {
        tantra_core::OrderSide::Buy => "BUY",
        tantra_core::OrderSide::Sell => "SELL",
    }
}

fn order_type_code(order_type: &tantra_core::OrderType) -> &'static str {
    match order_type {
        tantra_core::OrderType::Market => "MARKET",
        tantra_core::OrderType::Limit(_) => "LIMIT",
        tantra_core::OrderType::StopLoss(_) => "STOP_LOSS",
        tantra_core::OrderType::StopLimit { .. } => "STOP_LIMIT",
    }
}

fn tif_code(tif: &tantra_core::TimeInForce) -> &'static str {
    match tif {
        tantra_core::TimeInForce::Day => "DAY",
        tantra_core::TimeInForce::Ioc => "IOC",
        tantra_core::TimeInForce::Gtc => "GTC",
    }
}

fn state_code(state: &tantra_exec_paper::OrderState) -> &'static str {
    match state {
        tantra_exec_paper::OrderState::New => "NEW",
        tantra_exec_paper::OrderState::Working => "WORKING",
        tantra_exec_paper::OrderState::PartiallyFilled => "PARTIALLY_FILLED",
        tantra_exec_paper::OrderState::Filled => "FILLED",
        tantra_exec_paper::OrderState::Cancelled => "CANCELLED",
        tantra_exec_paper::OrderState::Rejected => "REJECTED",
        tantra_exec_paper::OrderState::StopTriggered => "STOP_TRIGGERED",
    }
}

fn exchange_error(e: tantra_exec_paper::ExchangeError) -> PyErr {
    conversion_err(format!("paper exchange: {e}"))
}

/// Project a fill event onto a dict: `{kind, broker_order_id, instrument,
/// side, quantity, price, timestamp}` (only the fields a fill carries).
fn fill_event_dict(
    d: &Bound<'_, PyDict>,
    kind: &str,
    fill: &tantra_core::FillReport,
    py: Python<'_>,
) -> PyResult<()> {
    d.set_item("kind", kind)?;
    d.set_item("broker_order_id", &fill.order_id)?;
    d.set_item("instrument", fill.instrument.to_string())?;
    d.set_item("side", side_code(&fill.side))?;
    d.set_item("quantity", decimal_to_pydecimal(py, fill.quantity.value())?)?;
    d.set_item("price", decimal_to_pydecimal(py, fill.price.value())?)?;
    d.set_item("timestamp", fill.timestamp.to_rfc3339())?;
    Ok(())
}

/// The deterministic seeded latency model used for `seed=` sessions (plan 0003
/// D3): `tantra_exec_paper::NetworkLatency` has no `seeded()` constructor, so
/// the seed drives its `SeededRng` through `NetworkLatency::new(mean, std,
/// seed)`.
fn seeded_latency(seed: u64) -> tantra_exec_paper::NetworkLatency {
    tantra_exec_paper::NetworkLatency::new(10, 5, seed)
}

/// The compiled paper-exchange engine: a deterministic, order-driven paper
/// trading simulator (plan 0003, D1).
#[pyclass(module = "tantra._tantra")]
pub struct PaperExchange {
    pub(crate) inner: tantra_exec_paper::PaperExchange,
}

impl PaperExchange {
    /// Lift a core engine into its Python wrapper (public Rust API).
    #[allow(dead_code)]
    pub(crate) fn from_core(inner: tantra_exec_paper::PaperExchange) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PaperExchange {
    #[new]
    #[pyo3(signature = (initial_cash, *, seed=None))]
    fn new(initial_cash: &Bound<'_, PyAny>, seed: Option<u64>) -> PyResult<Self> {
        let cash = pydecimal_to_decimal(initial_cash)?;
        let inner = match seed {
            Some(seed) => {
                tantra_exec_paper::PaperExchange::new(cash).with_latency(seeded_latency(seed))
            }
            None => tantra_exec_paper::PaperExchange::new(cash),
        };
        Ok(Self { inner })
    }

    /// Place an order; returns the broker order id (`PAPER-0001`, ...).
    ///
    /// ``gtd_until`` (RFC3339 UTC) makes the order good-till-date: the engine
    /// sets the order's `expires_ts` and the first `advance_to` at or past that
    /// instant expires it (state `CANCELLED`, `cancelled` event).
    #[pyo3(signature = (order, ts_iso="", gtd_until=None))]
    fn place_order(
        &mut self,
        py: Python<'_>,
        order: &Bound<'_, OrderRequest>,
        ts_iso: &str,
        gtd_until: Option<&str>,
    ) -> PyResult<String> {
        let order_req = order.borrow().inner.clone();
        let now = parse_ts(ts_iso)?;
        let broker_id = match gtd_until {
            Some(gtd) => {
                let gtd = parse_ts(gtd)?;
                py.detach(move || self.inner.submit_order_gtd(order_req, gtd, now))
            }
            None => py.detach(move || self.inner.submit_order(order_req, now)),
        }
        .map_err(exchange_error)?;
        Ok(broker_id)
    }

    /// Cancel a working order by its broker order id.
    fn cancel_order(
        &mut self,
        py: Python<'_>,
        broker_order_id: &str,
        ts_iso: &str,
    ) -> PyResult<()> {
        let now = parse_ts(ts_iso)?;
        py.detach(move || self.inner.cancel_order(broker_order_id, now))
            .map_err(exchange_error)
    }

    /// Amend a working order's limit price and/or quantity (both optional).
    #[pyo3(signature = (broker_order_id, limit_price=None, quantity=None, ts_iso=""))]
    fn amend_order(
        &mut self,
        py: Python<'_>,
        broker_order_id: &str,
        limit_price: Option<&Bound<'_, PyAny>>,
        quantity: Option<&Bound<'_, PyAny>>,
        ts_iso: &str,
    ) -> PyResult<()> {
        let new_price = limit_price.map(price_from_any).transpose()?;
        let new_qty = quantity.map(quantity_from_any).transpose()?;
        let now = parse_ts(ts_iso)?;
        py.detach(move || {
            self.inner
                .amend_order(broker_order_id, new_price, new_qty, now)
        })
        .map_err(exchange_error)
    }

    /// Feed one bar; the engine updates its market prices and re-matches.
    fn feed_bar(&mut self, py: Python<'_>, bar: &Bound<'_, Bar>) -> PyResult<()> {
        let core_bar = bar.borrow().inner.clone();
        py.detach(move || self.inner.feed_bar(&core_bar));
        Ok(())
    }

    /// Feed one tick (quote or LTP); the engine updates its market prices.
    fn feed_tick(&mut self, py: Python<'_>, tick: &Bound<'_, Tick>) -> PyResult<()> {
        let core_tick = tick.borrow().inner.clone();
        py.detach(move || self.inner.feed_tick(&core_tick));
        Ok(())
    }

    /// Advance the engine clock: expires GTD orders and re-matches
    /// latency-ready orders.
    fn advance_to(&mut self, py: Python<'_>, ts_iso: &str) -> PyResult<()> {
        let now = parse_ts(ts_iso)?;
        py.detach(move || self.inner.advance_to(now));
        Ok(())
    }

    /// Set the instrument's last market price (drives resting-limit matching).
    fn set_market_price(
        &mut self,
        instrument: &Bound<'_, InstrumentId>,
        price: &Bound<'_, PyAny>,
    ) -> PyResult<()> {
        let inst = instrument.borrow().inner.clone();
        let p = price_from_any(price)?;
        self.inner.set_market_price(inst, p);
        Ok(())
    }

    /// Every fill so far, in engine order.
    fn fills(&self) -> Vec<FillReport> {
        self.inner
            .fills()
            .iter()
            .map(|f| FillReport::from_core(f.clone()))
            .collect()
    }

    /// The engine's event stream, one dict per event: `{kind, ...}` where kind
    /// is `order_accepted`, `fill`, `partial_fill`, `cancelled`, `rejected` or
    /// `stop_triggered`.
    fn events<'py>(&self, py: Python<'py>) -> PyResult<Vec<Bound<'py, PyDict>>> {
        let mut out = Vec::new();
        for ev in self.inner.events() {
            let d = PyDict::new(py);
            match ev {
                tantra_exec_paper::ExchangeEvent::OrderAccepted {
                    broker_order_id,
                    instrument,
                    side,
                    quantity,
                    timestamp,
                } => {
                    d.set_item("kind", "order_accepted")?;
                    d.set_item("broker_order_id", broker_order_id)?;
                    d.set_item("instrument", instrument.to_string())?;
                    d.set_item("side", side_code(side))?;
                    d.set_item("quantity", decimal_to_pydecimal(py, quantity.value())?)?;
                    d.set_item("timestamp", timestamp.to_rfc3339())?;
                }
                tantra_exec_paper::ExchangeEvent::Fill { fill } => {
                    fill_event_dict(&d, "fill", fill, py)?;
                }
                tantra_exec_paper::ExchangeEvent::PartialFill { fill } => {
                    fill_event_dict(&d, "partial_fill", fill, py)?;
                }
                tantra_exec_paper::ExchangeEvent::Cancelled {
                    broker_order_id,
                    timestamp,
                } => {
                    d.set_item("kind", "cancelled")?;
                    d.set_item("broker_order_id", broker_order_id)?;
                    d.set_item("timestamp", timestamp.to_rfc3339())?;
                }
                tantra_exec_paper::ExchangeEvent::Rejected {
                    broker_order_id,
                    reason,
                    timestamp,
                } => {
                    d.set_item("kind", "rejected")?;
                    d.set_item("broker_order_id", broker_order_id)?;
                    d.set_item("reason", reason)?;
                    d.set_item("timestamp", timestamp.to_rfc3339())?;
                }
                tantra_exec_paper::ExchangeEvent::StopTriggered {
                    broker_order_id,
                    timestamp,
                } => {
                    d.set_item("kind", "stop_triggered")?;
                    d.set_item("broker_order_id", broker_order_id)?;
                    d.set_item("timestamp", timestamp.to_rfc3339())?;
                }
            }
            out.push(d);
        }
        Ok(out)
    }

    /// Net position per instrument (wire `EXCHANGE:SYMBOL` string to Decimal).
    fn positions<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let d = PyDict::new(py);
        for (inst, qty) in self.inner.positions() {
            d.set_item(inst.to_string(), decimal_to_pydecimal(py, *qty)?)?;
        }
        Ok(d)
    }

    /// Booked cash (Decimal).
    fn cash<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        decimal_to_pydecimal(py, self.inner.cash())
    }

    /// Equity = cash + sum(position * last) (Decimal).
    fn equity<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        decimal_to_pydecimal(py, self.inner.equity())
    }

    /// The instrument's best bid/ask (both Optional, absent until quoted).
    #[allow(clippy::type_complexity)]
    fn depth<'py>(
        &self,
        py: Python<'py>,
        instrument: &Bound<'_, InstrumentId>,
    ) -> PyResult<Option<(Option<Bound<'py, PyAny>>, Option<Bound<'py, PyAny>>)>> {
        let inst = instrument.borrow().inner.clone();
        match self.inner.depth(&inst) {
            Some((bid, ask)) => {
                let bid = bid
                    .map(|p| decimal_to_pydecimal(py, p.value()))
                    .transpose()?;
                let ask = ask
                    .map(|p| decimal_to_pydecimal(py, p.value()))
                    .transpose()?;
                Ok(Some((bid, ask)))
            }
            None => Ok(None),
        }
    }

    /// One working order as a dict (empty when unknown): broker_order_id, side,
    /// order_type, tif, original_qty, filled_qty, remaining_qty,
    /// avg_fill_price, state, reject_reason, submitted_ts.
    fn order<'py>(&self, py: Python<'py>, broker_order_id: &str) -> PyResult<Bound<'py, PyDict>> {
        let d = PyDict::new(py);
        if let Some(wo) = self.inner.order(broker_order_id) {
            d.set_item("broker_order_id", &wo.broker_order_id)?;
            d.set_item("side", side_code(&wo.side))?;
            d.set_item("order_type", order_type_code(&wo.order_type))?;
            d.set_item("tif", tif_code(&wo.tif))?;
            d.set_item(
                "original_qty",
                decimal_to_pydecimal(py, wo.original_qty.value())?,
            )?;
            d.set_item(
                "filled_qty",
                decimal_to_pydecimal(py, wo.filled_qty.value())?,
            )?;
            d.set_item(
                "remaining_qty",
                decimal_to_pydecimal(py, wo.remaining_qty.value())?,
            )?;
            d.set_item(
                "avg_fill_price",
                decimal_to_pydecimal(py, wo.avg_fill_price.value())?,
            )?;
            d.set_item("state", state_code(&wo.state))?;
            d.set_item(
                "reject_reason",
                wo.reject_reason.clone().unwrap_or_default(),
            )?;
            d.set_item("submitted_ts", wo.submitted_ts.to_rfc3339())?;
        }
        Ok(d)
    }
}

/// Register the paper-exchange class onto the module.
pub(crate) fn init(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PaperExchange>()?;
    Ok(())
}
