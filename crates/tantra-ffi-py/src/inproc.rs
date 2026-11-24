//! In-process runtime pyclass: `InprocRuntime` (`tantra.client.Client.inproc`).
//!
//! This module is the FFI composition root: it owns a Tokio runtime plus the
//! runtime's axum router and dispatches `/api/v2` requests without a socket.
//! Owning a runtime and calling `block_on` from a Python thread is the
//! boundary itself, not library/dispatch code (`.agents/rules/
//! scalability-and-concurrency.md` section 2.3 bans it only inside the latter).
//! The GIL is released around every blocking call (`py.detach`).

use axum::Router;
use axum::body::Body;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyModule;
use tantra_runtime_api_rest::{AppState, ServeConfig, prepare_server};
use tower::util::ServiceExt;

/// Upper bound on a buffered response body.
const MAX_BODY: usize = 64 * 1024 * 1024;

fn rt_err(e: impl std::fmt::Display) -> PyErr {
    PyRuntimeError::new_err(e.to_string())
}

/// The runtime's `/api/v2` router, served in-process.
#[pyclass(module = "tantra._tantra", name = "InprocRuntime")]
pub struct InprocRuntime {
    rt: tokio::runtime::Runtime,
    router: Router,
    state: Option<AppState>,
}

#[pymethods]
impl InprocRuntime {
    #[new]
    #[pyo3(signature = (data_dir, *, journals_dir=None, profiles_dir=None, portfolios_dir=None, tokens_file=None))]
    fn new(
        py: Python<'_>,
        data_dir: String,
        journals_dir: Option<String>,
        profiles_dir: Option<String>,
        portfolios_dir: Option<String>,
        tokens_file: Option<String>,
    ) -> PyResult<Self> {
        let mut cfg = ServeConfig::new(data_dir);
        if let Some(d) = journals_dir {
            cfg.runs.journals_dir = d.into();
        }
        if let Some(d) = profiles_dir {
            cfg.runs.profiles_dir = d.into();
        }
        if let Some(d) = portfolios_dir {
            cfg.runs.portfolios_dir = d.into();
        }
        if let Some(t) = tokens_file {
            cfg.auth.tokens_file = Some(t.into());
        }
        let rt = tokio::runtime::Builder::new_multi_thread()
            .worker_threads(2)
            .enable_all()
            .build()
            .map_err(rt_err)?;
        let prepared = py
            .detach(|| rt.block_on(prepare_server(&cfg)))
            .map_err(|e| PyRuntimeError::new_err(format!("{e:#}")))?;
        let (router, state) = prepared.into_router();
        Ok(Self {
            rt,
            router,
            state: Some(state),
        })
    }

    /// Dispatch one request; returns `(status, body_bytes)`.
    fn request(
        &self,
        py: Python<'_>,
        method: &str,
        path: &str,
        headers: Vec<(String, String)>,
        body: Option<Vec<u8>>,
    ) -> PyResult<(u16, Vec<u8>)> {
        if !path.starts_with("/api/v2/") {
            return Err(PyValueError::new_err("path must start with /api/v2/"));
        }
        if self.state.is_none() {
            return Err(PyRuntimeError::new_err("in-process runtime is closed"));
        }
        let mut builder = http::Request::builder().method(method).uri(path);
        for (k, v) in headers {
            builder = builder.header(k, v);
        }
        let req = builder
            .body(Body::from(body.unwrap_or_default()))
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let router = self.router.clone();
        py.detach(|| {
            self.rt.block_on(async move {
                let resp = router.oneshot(req).await.map_err(rt_err)?;
                let status = resp.status().as_u16();
                let bytes = axum::body::to_bytes(resp.into_body(), MAX_BODY)
                    .await
                    .map_err(rt_err)?;
                Ok((status, bytes.to_vec()))
            })
        })
    }

    /// Drain run workers; idempotent.
    fn close(&mut self, py: Python<'_>) {
        if let Some(state) = self.state.take() {
            py.detach(move || {
                let _ = state.shutdown_runs();
            });
        }
    }
}

pub fn init(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<InprocRuntime>()?;
    Ok(())
}
