"""REST client for the Tantra runtime's ``/api/v2`` contract (stdlib only).

Money is never a ``float``: JSON numbers are parsed to ``Decimal`` and Decimals are sent
as strings. Only canonical (non-redirected) paths are called.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from types import TracebackType
from typing import Any
from urllib.parse import quote

from ._config import RuntimeConfigError, RuntimeEndpoint, load_runtime_endpoint
from ._http import ClientError, HttpTransport
from ._models import (
    ExpiryHedgeRequest,
    ExpiryHedgeResponse,
    StrategyLoopRequest,
    StrategyLoopResponse,
    StrategySweepRequest,
    StrategySweepResponse,
)

__all__ = [
    "BacktestResult",
    "Client",
    "ClientError",
    "RuntimeConfigError",
    "RuntimeEndpoint",
    "load_runtime_endpoint",
]

_TERMINAL = {"completed", "succeeded", "failed", "cancelled", "interrupted"}
_MONEY_FIELDS = ("initial_capital", "commission_per_fill", "slippage_bps")


@dataclass(frozen=True)
class BacktestResult:
    """A backtest run manifest; ``status`` is ``None`` when the manifest has no status key."""

    run_id: str
    status: str | None
    manifest: Mapping[str, Any] = field(default_factory=dict)


def _seg(value: str) -> str:
    return quote(str(value), safe="")


def _money(name: str, value: object) -> str:
    if isinstance(value, (bool, float)):
        raise TypeError(
            f"{name} must be Decimal, int or str, not {type(value).__name__}"
        )
    if isinstance(value, Decimal | int | str):
        return str(value)
    raise TypeError(f"{name} must be Decimal, int or str, not {type(value).__name__}")


class Client:
    """Synchronous client for ``/api/v2``. Build with :meth:`http` or :meth:`from_config`."""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    def __repr__(self) -> str:
        return f"Client({self._t!r})"

    # -- constructors ------------------------------------------------------------------
    @classmethod
    def http(
        cls, base_url: str, *, token: str | None = None, timeout: float = 30.0
    ) -> Client:
        return cls(HttpTransport(base_url, token, timeout))

    @classmethod
    def from_config(
        cls, path: str | os.PathLike[str] | None = None, *, timeout: float = 30.0
    ) -> Client:
        try:
            ep = load_runtime_endpoint(path)
        except RuntimeConfigError as exc:
            raise ClientError(0, "config_error", str(exc)) from exc
        if not ep.url:
            raise ClientError(0, "not_configured", "no runtime.url in tantra.jsonc")
        return cls.http(ep.url, token=ep.token, timeout=timeout)

    @classmethod
    def inproc(cls, *args: Any, **kwargs: Any) -> Client:
        raise NotImplementedError(
            "in-process transport is not available in the wheel yet; "
            "use Client.http(...) against `tantra serve`"
        )

    # -- lifecycle ---------------------------------------------------------------------
    def close(self) -> None:
        """No persistent connection is held; kept for API symmetry."""

    def __enter__(self) -> Client:  # noqa: PYI034 (Self needs 3.11)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # -- read routes -------------------------------------------------------------------
    def health(self) -> Any:
        return self._t.request("GET", "/health")

    def bars(
        self, id: str, tf: str = "1d", from_: str | None = None, to: str | None = None
    ) -> Any:
        return self._t.request(
            "GET", f"/bars/{_seg(id)}", query={"tf": tf, "from": from_, "to": to}
        )

    def screener_scans(
        self,
        filters: Any,
        universe: Any,
        tf: str | None = None,
        as_of: str | None = None,
    ) -> Any:
        def enc(v: Any) -> str:
            return v if isinstance(v, str) else json.dumps(v, default=str)

        return self._t.request(
            "GET",
            "/screener/scans",
            query={
                "filters": enc(filters),
                "universe": enc(universe),
                "tf": tf,
                "as_of": as_of,
            },
        )

    def strategy_loop_evaluate(self, req: StrategyLoopRequest) -> StrategyLoopResponse:
        out: StrategyLoopResponse = self._t.request(
            "POST", "/studies/strategy-loop/evaluate", body=req
        )
        return out

    def strategy_loop_sweep(self, req: StrategySweepRequest) -> StrategySweepResponse:
        out: StrategySweepResponse = self._t.request(
            "POST", "/studies/strategy-loop/sweep", body=req
        )
        return out

    def recommend_hedge(self, req: ExpiryHedgeRequest) -> ExpiryHedgeResponse:
        out: ExpiryHedgeResponse = self._t.request(
            "POST", "/studies/strategy-loop/recommend-hedge", body=req
        )
        return out

    # -- backtests ---------------------------------------------------------------------
    def run_backtest(
        self,
        *,
        timeout: float = 60.0,
        poll_interval: float = 0.5,
        **fields: Any,
    ) -> BacktestResult:
        """Start a backtest and poll until it reaches a terminal state."""
        body: dict[str, Any] = dict(fields)
        for name in _MONEY_FIELDS:
            if name in body:
                body[name] = _money(name, body[name])
        manifest = self._t.request("POST", "/backtests", body=body)
        run_id = str(manifest["run_id"])
        deadline = time.monotonic() + timeout
        while True:
            status = _status(manifest)
            if status is None or status in _TERMINAL:
                return BacktestResult(run_id, status, manifest)
            if time.monotonic() >= deadline:
                raise ClientError(
                    0, "timeout", f"backtest {run_id} still {status} after {timeout}s"
                )
            time.sleep(poll_interval)
            manifest = self.backtest(run_id)

    def backtest(self, run_id: str) -> Any:
        return self._t.request("GET", f"/backtests/{_seg(run_id)}")

    def backtest_journal(self, run_id: str) -> Any:
        return self._t.request("GET", f"/backtests/{_seg(run_id)}/journal")


def _status(manifest: Any) -> str | None:
    if not isinstance(manifest, Mapping):
        return None
    for key in ("status", "state"):
        v = manifest.get(key)
        if isinstance(v, str):
            return v.lower()
    return None
