"""Stdlib HTTP transport for the ``/api/v2`` envelope."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

__all__ = ["ClientError", "HttpTransport"]


class ClientError(Exception):
    """A failed runtime call. Network failures use ``status=0, code="unreachable"``."""

    def __init__(
        self,
        status: int,
        code: str | None,
        message: str,
        reason: str | None = None,
    ) -> None:
        super().__init__(
            f"[{status} {code}] {message}" + (f" ({reason})" if reason else "")
        )
        self.status = status
        self.code = code
        self.message = message
        self.reason = reason


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def _default(o: object) -> str:
    if isinstance(o, Decimal):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o).__name__}")


def _loads(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"), parse_float=Decimal)


class HttpTransport:
    def __init__(self, base_url: str, token: str | None, timeout: float) -> None:
        self._base = base_url.rstrip("/") + "/api/v2"
        self._token = token
        self._timeout = timeout
        self._opener = urllib.request.build_opener(_NoRedirect)

    def __repr__(self) -> str:
        tok = "[REDACTED]" if self._token else None
        return f"HttpTransport(base={self._base!r}, token={tok!r})"

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, str | None] | None = None,
        body: Mapping[str, Any] | None = None,
    ) -> Any:
        url = self._base + path
        if query:
            qs = urlencode({k: v for k, v in query.items() if v is not None})
            if qs:
                url += "?" + qs
        headers = {"Accept": "application/json"}
        data: bytes | None = None
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, default=_default).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=self._timeout) as resp:
                status, raw = resp.status, resp.read()
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read()
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            raise ClientError(
                0, "unreachable", f"cannot reach {self._base}: {e}"
            ) from None
        return self._unwrap(status, raw)

    @staticmethod
    def _unwrap(status: int, raw: bytes) -> Any:
        if 300 <= status < 400:
            raise ClientError(
                status,
                "redirect",
                "server redirected the request; update the client path",
            )
        try:
            env = _loads(raw) if raw else None
        except ValueError:
            env = None
        err = env.get("error") if isinstance(env, dict) else None
        if isinstance(err, dict):
            ctx = err.get("context")
            reason = ctx.get("reason") if isinstance(ctx, dict) else None
            raise ClientError(
                status,
                str(err["code"]) if err.get("code") is not None else None,
                str(err.get("message", "")),
                str(reason) if reason is not None else None,
            )
        if status >= 400 or not isinstance(env, dict):
            raise ClientError(status, None, "unexpected response from runtime")
        return env.get("data")
