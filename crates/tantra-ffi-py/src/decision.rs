//! Closed AI `Decision` grammar pyclass: `Decision`.
//!
//! An AI model is an untrusted signal generator: decisions are parsed against
//! the closed serde grammar (`deny_unknown_fields`, snake_case `action` tag)
//! and validated before they may reach the risk gate.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};

use crate::error::conversion_err;

fn side_code(side: tantra_core::OrderSide) -> &'static str {
    match side {
        tantra_core::OrderSide::Buy => "BUY",
        tantra_core::OrderSide::Sell => "SELL",
    }
}

/// A strictly-validated AI decision.
#[pyclass(module = "tantra._tantra")]
#[derive(Clone)]
pub struct Decision {
    pub(crate) inner: tantra_core::Decision,
}

impl Decision {
    /// Lift a core `Decision` into its Python wrapper (public Rust API; the
    /// Python SDK primarily enters through [`Decision::from_json`]).
    #[allow(dead_code)]
    pub(crate) fn from_core(inner: tantra_core::Decision) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl Decision {
    /// Parse a JSON decision string against the closed serde grammar.
    ///
    /// Raises `ConversionError` on invalid JSON, unknown fields
    /// (`deny_unknown_fields`), or validation failures (bad `algo_id`, zero
    /// quantity, empty symbol).
    #[staticmethod]
    fn from_json(s: &str) -> PyResult<Decision> {
        let inner = tantra_core::Decision::from_json_str(s).map_err(conversion_err)?;
        Ok(Decision { inner })
    }

    #[getter]
    fn action(&self) -> &'static str {
        match &self.inner {
            tantra_core::Decision::PlaceOrder { .. } => "place_order",
            tantra_core::Decision::ModifyOrder { .. } => "modify_order",
            tantra_core::Decision::CancelOrder { .. } => "cancel_order",
            tantra_core::Decision::CancelAll { .. } => "cancel_all",
            tantra_core::Decision::Hold { .. } => "hold",
        }
    }

    /// String-valued dict with the keys available on this variant
    /// (`action`, `symbol`, `side`, `qty`, `price_limit`, `algo_id`, ...).
    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let dict = PyDict::new(py);
        match &self.inner {
            tantra_core::Decision::PlaceOrder {
                symbol,
                side,
                qty,
                price_limit,
                algo_id,
                rationale,
            } => {
                dict.set_item("action", "place_order")?;
                dict.set_item("symbol", symbol)?;
                dict.set_item("side", side_code(*side))?;
                dict.set_item("qty", qty.0.to_string())?;
                if let Some(price) = price_limit {
                    dict.set_item("price_limit", price.0.to_string())?;
                }
                dict.set_item("algo_id", algo_id)?;
                if let Some(reason) = rationale {
                    dict.set_item("rationale", reason)?;
                }
            }
            tantra_core::Decision::ModifyOrder {
                instrument,
                new_qty,
                new_price,
                algo_id,
                rationale,
            } => {
                dict.set_item("action", "modify_order")?;
                dict.set_item("instrument", instrument.to_string())?;
                if let Some(qty) = new_qty {
                    dict.set_item("new_qty", qty.0.to_string())?;
                }
                if let Some(price) = new_price {
                    dict.set_item("new_price", price.0.to_string())?;
                }
                dict.set_item("algo_id", algo_id)?;
                if let Some(reason) = rationale {
                    dict.set_item("rationale", reason)?;
                }
            }
            tantra_core::Decision::CancelOrder {
                instrument,
                algo_id,
                rationale,
            } => {
                dict.set_item("action", "cancel_order")?;
                dict.set_item("instrument", instrument.to_string())?;
                if let Some(id) = algo_id {
                    dict.set_item("algo_id", id)?;
                }
                if let Some(reason) = rationale {
                    dict.set_item("rationale", reason)?;
                }
            }
            tantra_core::Decision::CancelAll { algo_id, reason } => {
                dict.set_item("action", "cancel_all")?;
                if let Some(id) = algo_id {
                    dict.set_item("algo_id", id)?;
                }
                if let Some(reason) = reason {
                    dict.set_item("reason", reason)?;
                }
            }
            tantra_core::Decision::Hold { reason } => {
                dict.set_item("action", "hold")?;
                if let Some(reason) = reason {
                    dict.set_item("reason", reason)?;
                }
            }
        }
        Ok(dict.into_any())
    }
}

/// Register decision classes onto the module.
pub(crate) fn init(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Decision>()?;
    Ok(())
}
