"""Tests for the ``tantra.cli`` command-line interface."""

import json

import pytest
from tantra import _tantra
from tantra.cli import main
from tantra.strategy import Strategy


class CountingStrategy(Strategy):
    """Strategy that buys one lot on every bar."""

    def on_bar(self, bar) -> None:
        self.buy("NSE:RELIANCE", quantity="10", limit_price=str(bar.close))


def _bars_fixture() -> list:
    return [
        {
            "instrument": "NSE:RELIANCE",
            "ts": "2026-11-05T09:30:00+05:30",
            "open": "2450.75",
            "high": "2455.00",
            "low": "2448.00",
            "close": "2452.00",
            "volume": "1000",
        },
        {
            "instrument": "NSE:RELIANCE",
            "ts": "2026-11-05T09:31:00+05:30",
            "open": "2452.00",
            "high": "2460.00",
            "low": "2451.00",
            "close": "2458.50",
            "volume": "1200",
        },
        {
            "instrument": "NSE:RELIANCE",
            "ts": "2026-11-05T09:32:00+05:30",
            "open": "2458.50",
            "high": "2465.00",
            "low": "2456.00",
            "close": "2462.75",
            "volume": "1100",
        },
    ]


def _write_bars(tmp_path) -> object:
    path = tmp_path / "bars.json"
    path.write_text(json.dumps(_bars_fixture()), encoding="utf-8")
    return path


def test_version_subcommand(capsys) -> None:
    assert main(["version"]) == 0
    out = capsys.readouterr().out
    assert "tantra" in out
    assert _tantra.__version__ in out


def test_backtest_runs_real_backtest(tmp_path, capsys) -> None:
    path = _write_bars(tmp_path)
    assert main(["backtest", "--bars-json", str(path)]) == 0
    out = capsys.readouterr().out
    assert "Backtest" in out
    assert "bars=3" in out


def test_backtest_with_strategy_flag(tmp_path, capsys) -> None:
    path = _write_bars(tmp_path)
    rc = main(
        [
            "backtest",
            "--bars-json",
            str(path),
            "--strategy",
            "test_cli:CountingStrategy",
            "--algo-id",
            "cli-test",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "orders_filled=3" in out
    assert "algo=cli-test" in out


def test_backtest_missing_file_returns_2(capsys) -> None:
    assert main(["backtest", "--bars-json", "/no/such/file.json"]) == 2
    err = capsys.readouterr().err
    assert "/no/such/file.json" in err


def test_backtest_invalid_json_returns_2(tmp_path, capsys) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    assert main(["backtest", "--bars-json", str(path)]) == 2


def test_backtest_bad_strategy_returns_2(tmp_path, capsys) -> None:
    path = _write_bars(tmp_path)
    rc = main(["backtest", "--bars-json", str(path), "--strategy", "no.such.module:Whatever"])
    assert rc == 2


def test_serve_and_stub_removed() -> None:
    with pytest.raises(SystemExit):
        main(["serve"])
    with pytest.raises(SystemExit):
        main(["stub"])
