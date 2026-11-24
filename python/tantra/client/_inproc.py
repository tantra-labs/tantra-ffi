"""In-process transport: the wheel embeds the runtime's ``/api/v2`` router."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

from ._http import ClientError, HttpTransport, _default

__all__ = ["InprocTransport"]


def _opt(p: str | os.PathLike[str] | None) -> str | None:
    return None if p is None else os.fspath(p)


class InprocTransport:
    def __init__(
        self,
        data_dir: str | os.PathLike[str],
        *,
        token: str | None = None,
        journals_dir: str | os.PathLike[str] | None = None,
        profiles_dir: str | os.PathLike[str] | None = None,
        portfolios_dir: str | os.PathLike[str] | None = None,
        tokens_file: str | os.PathLike[str] | None = None,
    ) -> None:
        try:
            from tantra._tantra import InprocRuntime
        except ImportError:
            raise ClientError(
                0,
                "inproc_unavailable",
                "this tantra build has no in-process runtime",
            ) from None
        self._token = token
        try:
            self._rt: Any = InprocRuntime(
                os.fspath(data_dir),
                journals_dir=_opt(journals_dir),
                profiles_dir=_opt(profiles_dir),
                portfolios_dir=_opt(portfolios_dir),
                tokens_file=_opt(tokens_file),
            )
        except RuntimeError as e:
            raise ClientError(0, "inproc_start_failed", str(e)) from None

    def __repr__(self) -> str:
        tok = "[REDACTED]" if self._token else None
        return f"InprocTransport(token={tok!r})"

    def close(self) -> None:
        self._rt.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, str | None] | None = None,
        body: Mapping[str, Any] | None = None,
    ) -> Any:
        url = "/api/v2" + path
        if query:
            qs = urlencode({k: v for k, v in query.items() if v is not None})
            if qs:
                url += "?" + qs
        headers = [("accept", "application/json")]
        data: bytes | None = None
        if self._token:
            headers.append(("authorization", f"Bearer {self._token}"))
        if body is not None:
            headers.append(("content-type", "application/json"))
            data = json.dumps(body, default=_default).encode("utf-8")
        try:
            status, raw = self._rt.request(method, url, headers, data)
        except RuntimeError as e:
            raise ClientError(0, "inproc_error", str(e)) from None
        return HttpTransport._unwrap(status, bytes(raw))
