//! Facade of the `tantra-ffi` bounded context (Soul).
//!
//! Re-exports the member crates under their short names so consumers import the
//! whole Python-FFI bridge from a single crate (facade-crate convention, root
//! plan 0003 Phase 4 / gap 0007).

pub use tantra_ffi_codegen as codegen;
pub use tantra_ffi_py as py;
