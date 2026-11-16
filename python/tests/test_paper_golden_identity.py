"""P4 cross-embedding golden vector identity (root plan 0007, T14.14).

The canonical paper-exchange golden tape lives in this repo at
``python/tests/golden/paper_golden.json`` (the Python wheel embedding). The
same JSON file must be byte-identical in the other two embeddings that replay
it: ``tantra-ui-api-wasm`` (WASM) and ``tantra-exec-paper`` (the paper engine,
which also owns ``tests/golden_parity_tests.rs``). One vector, four
embeddings (backtest E9 / paper / Python wheel / WASM).
"""

from __future__ import annotations

from pathlib import Path

TESTS = Path(__file__).parent
GOLDEN = TESTS / "golden" / "paper_golden.json"

# Sibling embedding copies of the canonical vector (byte-identical by
# contract; workspace root is three levels above `python/tests/`).
_SIBLING_COPIES = {
    "wasm": TESTS
    / "../../../tantra-ui/crates/tantra-ui-api-wasm/tests/golden/paper_golden.json",
    "exec": TESTS
    / "../../../tantra-exec/crates/tantra-exec-paper/tests/golden/paper_golden.json",
}


def test_paper_golden_vector_is_byte_identical_across_embeddings() -> None:
    canonical = GOLDEN.read_bytes()
    assert canonical, "canonical golden vector must not be empty"
    for embedding, path in _SIBLING_COPIES.items():
        assert path.is_file(), f"{embedding} golden vector missing: {path}"
        assert path.read_bytes() == canonical, (
            f"{embedding} golden vector diverged from the canonical file"
        )
