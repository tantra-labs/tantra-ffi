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
