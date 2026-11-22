"""Tests for ``tantra.client`` against a real local HTTP server (no mocks)."""

from __future__ import annotations

import importlib.util
import json
import threading
from collections.abc import Callable, Iterator
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from tantra.client import Client, ClientError, RuntimeEndpoint, load_runtime_endpoint

Reply = tuple[int, bytes]
Responder = Callable[[str, str, dict[str, str], bytes], Reply]


class _Server:
    def __init__(self) -> None:
        self.responder: Responder = lambda *_: (200, b"{}")
        self.requests: list[tuple[str, str, dict[str, str], bytes]] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def _serve(self) -> None:
                n = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(n) if n else b""
                hdrs = {k.lower(): v for k, v in self.headers.items()}
                outer.requests.append((self.command, self.path, hdrs, body))
                status, payload = outer.responder(self.command, self.path, hdrs, body)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_GET = do_POST = _serve

            def log_message(self, *a: Any) -> None:
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def _env(data: Any) -> bytes:
    return json.dumps(
        {"api_version": "v2", "schema_version": "1", "data": data}
    ).encode()


@pytest.fixture
def server() -> Iterator[_Server]:
    s = _Server()
    yield s
    s.close()


def test_success_returns_data_with_exact_decimal(server: _Server) -> None:
    server.responder = lambda *_: (
        200,
        b'{"api_version":"v2","schema_version":"1","data":{"a":2500.05,"b":"2500.05"}}',
    )
    data = Client.http(server.url).health()
    assert data["a"] == Decimal("2500.05")
    assert isinstance(data["a"], Decimal)
    assert Decimal(data["b"]) == Decimal("2500.05")
    assert server.requests[0][1] == "/api/v2/health"


def test_error_envelope_raises(server: _Server) -> None:
    body = json.dumps(
        {
            "api_version": "v2",
            "schema_version": "1",
            "data": None,
            "error": {
                "code": "forbidden",
                "message": "no scope",
                "retryable": False,
                "context": {"reason": "missing_scope"},
            },
        }
    ).encode()
    server.responder = lambda *_: (403, body)
    with pytest.raises(ClientError) as ei:
        Client.http(server.url).health()
    assert (ei.value.status, ei.value.code, ei.value.reason) == (
        403,
        "forbidden",
        "missing_scope",
    )
    assert ei.value.message == "no scope"


def test_redirect_is_not_followed(server: _Server) -> None:
    server.responder = lambda *_: (308, b"")
    with pytest.raises(ClientError) as ei:
        Client.http(server.url).health()
    assert ei.value.code == "redirect" and ei.value.status == 308
    assert len(server.requests) == 1


def test_unreachable() -> None:
    with pytest.raises(ClientError) as ei:
        Client.http("http://127.0.0.1:1", timeout=2.0).health()
    assert (ei.value.status, ei.value.code) == (0, "unreachable")


def test_bearer_header_only_when_token_set(server: _Server) -> None:
    server.responder = lambda *_: (200, _env({}))
    Client.http(server.url, token="s3cret").health()
    Client.http(server.url).health()
    assert server.requests[0][2]["authorization"] == "Bearer s3cret"
    assert "authorization" not in server.requests[1][2]
    assert server.requests[0][2]["accept"] == "application/json"


def test_path_segment_is_encoded(server: _Server) -> None:
    server.responder = lambda *_: (200, _env([]))
    Client.http(server.url).bars("A/B C.NSE", tf="1d")
    assert server.requests[0][1].startswith("/api/v2/bars/A%2FB%20C.NSE?")


def test_run_backtest_polls_to_terminal(server: _Server) -> None:
    states = iter(["running", "running", "Completed"])

    def respond(method: str, path: str, hdrs: dict[str, str], body: bytes) -> Reply:
        if method == "POST":
            return 200, _env({"run_id": "r1", "status": "queued"})
        return 200, _env({"run_id": "r1", "status": next(states), "sharpe": 1.25})

    server.responder = respond
    res = Client.http(server.url).run_backtest(
        strategy="s", initial_capital=Decimal("1000000.50"), poll_interval=0.01
    )
    assert res.run_id == "r1" and res.status == "completed"
    assert res.manifest["sharpe"] == Decimal("1.25")
    sent = json.loads(server.requests[0][3])
    assert sent["initial_capital"] == "1000000.50"
    assert server.requests[0][2]["content-type"] == "application/json"


def test_run_backtest_rejects_float(server: _Server) -> None:
    with pytest.raises(TypeError):
        Client.http(server.url).run_backtest(initial_capital=1.5)
    assert server.requests == []


def test_run_backtest_no_status_is_terminal(server: _Server) -> None:
    server.responder = lambda *_: (200, _env({"run_id": "r2"}))
    res = Client.http(server.url).run_backtest()
    assert res.status is None and len(server.requests) == 1


def test_from_config_file_env_comments_trailing_commas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    monkeypatch.setenv("TANTRA_TEST_URL", "http://example.test:9")
    (tmp_path / "tok.txt").write_text("  file-token \n")
    cfg = tmp_path / "tantra.jsonc"
    cfg.write_text(
        """{
  // a comment
  "other": "http://not/ignored", /* block */
  "runtime": {
    "url": "{env:TANTRA_TEST_URL}",
    "token": "{file:tok.txt}", // trailing comma next
  },
}
"""
    )
    ep = load_runtime_endpoint(cfg)
    assert ep.url == "http://example.test:9" and ep.token == "file-token"
    c = Client.from_config(cfg)
    assert "example.test" in repr(c) and "file-token" not in repr(c)


def test_from_config_walks_up_and_project_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    (home / ".config" / "tantra").mkdir(parents=True)
    (home / ".config" / "tantra" / "tantra.jsonc").write_text(
        '{"runtime": {"url": "http://global", "token": "gtok"}}'
    )
    proj = tmp_path / "proj"
    (proj / "sub").mkdir(parents=True)
    (proj / "tantra.jsonc").write_text('{"runtime": {"url": "http://project"}}')
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(proj / "sub")
    ep = load_runtime_endpoint()
    assert (ep.url, ep.token) == ("http://project", "gtok")


def test_from_config_not_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = tmp_path / "tantra.jsonc"
    cfg.write_text("{}")
    with pytest.raises(ClientError) as ei:
        Client.from_config(cfg)
    assert ei.value.code == "not_configured"


def test_token_redacted_in_repr(server: _Server) -> None:
    assert "s3cret" not in repr(RuntimeEndpoint("http://x", "s3cret"))
    assert "s3cret" not in repr(Client.http(server.url, token="s3cret"))


def test_inproc_not_available() -> None:
    with pytest.raises(NotImplementedError):
        Client.inproc("data")


def test_models_check_is_current() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "gen_client_models.py"
    schema = (
        script.parents[2]
        / "tantra-runtime/crates/tantra-runtime-api-rest/schema/openapi.v2.json"
    )
    if not schema.is_file():
        pytest.skip("openapi.v2.json artifact absent")
    spec = importlib.util.spec_from_file_location("gen_client_models", script)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--check"]) == 0


def test_from_config_unresolvable_reference_is_an_error(tmp_path, monkeypatch):
    """A broken {env:}/{file:} reference raises, never a silently dropped token."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("TANTRA_TEST_UNSET_TOKEN", raising=False)
    (tmp_path / "tantra.jsonc").write_text(
        '{"runtime": {"url": "http://127.0.0.1:1", "token": "{env:TANTRA_TEST_UNSET_TOKEN}"}}'
    )
    with pytest.raises(ClientError) as info:
        Client.from_config()
    assert info.value.code == "config_error"
