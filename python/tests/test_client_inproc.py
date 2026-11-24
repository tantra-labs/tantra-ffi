from __future__ import annotations

import pytest

_native = pytest.importorskip("tantra._tantra")
if not hasattr(_native, "InprocRuntime"):
    pytest.skip("extension lacks InprocRuntime", allow_module_level=True)

from tantra.client import Client, ClientError


def _client(tmp_path):
    return Client.inproc(
        tmp_path,
        journals_dir=tmp_path / "journals",
        profiles_dir=tmp_path / "profiles",
        portfolios_dir=tmp_path / "portfolios",
    )


def test_health(tmp_path):
    with _client(tmp_path) as c:
        assert c.health() is not None


def test_unknown_route_is_not_found(tmp_path):
    with _client(tmp_path) as c, pytest.raises(ClientError) as ei:
        c._t.request("GET", "/no-such-route")
    assert ei.value.status == 404
    assert ei.value.code == "not_found"


def test_close_twice(tmp_path):
    c = _client(tmp_path)
    c.close()
    c.close()


_DROP_WITHOUT_CLOSE = """
import gc, sys
from pathlib import Path
from tantra.client import Client

root = Path(sys.argv[1])
c = Client.inproc(
    root,
    journals_dir=root / "journals",
    profiles_dir=root / "profiles",
    portfolios_dir=root / "portfolios",
)
assert c.health() is not None
del c  # dropped under the GIL without close()
gc.collect()
print("dropped")
"""


def test_drop_without_close_does_not_hang(tmp_path):
    # Regression: dropping InprocRuntime without close() blocked on worker threads
    # under the GIL. A subprocess + timeout turns a deadlock into a test failure.
    import subprocess
    import sys

    out = subprocess.run(
        [sys.executable, "-c", _DROP_WITHOUT_CLOSE, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.returncode == 0, out.stderr
    assert "dropped" in out.stdout
