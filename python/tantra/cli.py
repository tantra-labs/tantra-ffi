"""Command-line interface for the Tantra Python SDK.

Subcommands:
  version   print SDK + schema versions
  backtest  run a backtest from a bars JSON file (via tantra.strategy.run)
"""
import argparse
import importlib
import json
import sys
from typing import Any, List, Optional, Sequence, Type

from tantra import _tantra
from tantra.strategy import Strategy, run as strategy_run


class _SmaCrossStrategy(Strategy):
    """Default CLI strategy: fast/slow SMA cross per symbol (lazy init).

    Fast SMA period 3, slow SMA period 8. On a fast cross above the slow while
    flat the strategy buys one lot; on a cross below while long it sells.
    """

    def __init__(self) -> None:
        super().__init__()
        self._fast: dict[str, Any] = {}
        self._slow: dict[str, Any] = {}
        self._long: set[str] = set()

    def on_bar(self, bar: _tantra.Bar) -> None:
        symbol = str(bar.instrument)
        fast = self._fast.get(symbol)
        if fast is None:
            fast = self.indicators.SMA(3)
            self._fast[symbol] = fast
        slow = self._slow.get(symbol)
        if slow is None:
            slow = self.indicators.SMA(8)
            self._slow[symbol] = slow
        fast.add(bar.close)
        slow.add(bar.close)
        if fast.crosses_above(slow) and symbol not in self._long:
            self._long.add(symbol)
            self.buy(symbol, quantity="10", limit_price=str(bar.close), tag="sma-cross")
        elif fast.crosses_below(slow) and symbol in self._long:
            self._long.discard(symbol)
            self.sell(symbol, quantity="10", limit_price=str(bar.close), tag="sma-cross")


def _instrument_id(symbol: str) -> _tantra.InstrumentId:
    """Build a canonical InstrumentId from a broker-style symbol string."""
    if ":" in symbol:
        return _tantra.InstrumentId.from_str(symbol)
    return _tantra.InstrumentId("NSE", symbol)


_BAR_KEYS = ("instrument", "ts", "open", "high", "low", "close", "volume")


def _parse_bars(data: Any) -> List[_tantra.Bar]:
    """Validate and convert a parsed JSON bars payload into _tantra.Bar objects."""
    if not isinstance(data, list):
        raise ValueError("bars JSON must be a list of bar objects")
    bars: List[_tantra.Bar] = []
    for index, raw in enumerate(data):
        if not isinstance(raw, dict):
            raise ValueError(f"bar #{index}: expected a JSON object")
        missing = [key for key in _BAR_KEYS if key not in raw]
        if missing:
            raise ValueError(f"bar #{index}: missing key(s) {missing}")
        instrument = raw["instrument"]
        ts = raw["ts"]
        if not isinstance(instrument, str) or not instrument:
            raise ValueError(f"bar #{index}: 'instrument' must be a non-empty string")
        if not isinstance(ts, str) or not ts:
            raise ValueError(f"bar #{index}: 'ts' must be a non-empty string")
        bars.append(
            _tantra.Bar(
                _instrument_id(instrument),
                str(raw["open"]),
                str(raw["high"]),
                str(raw["low"]),
                str(raw["close"]),
                str(raw["volume"]),
                ts,
            )
        )
    return bars


def _load_strategy(value: Optional[str]) -> Type[Strategy]:
    """Resolve MODULE:CLASS into a Strategy subclass (or the built-in default)."""
    if value is None:
        return _SmaCrossStrategy
    if ":" not in value:
        raise ValueError(f"--strategy must be MODULE:CLASS, got {value!r}")
    module_name, _, class_name = value.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ValueError(f"could not import module {module_name!r}: {exc}") from exc
    try:
        cls = getattr(module, class_name)
    except AttributeError as exc:
        raise ValueError(f"module {module_name!r} has no attribute {class_name!r}") from exc
    if not (isinstance(cls, type) and issubclass(cls, Strategy)):
        raise ValueError(f"{value!r} does not name a tantra.Strategy subclass")
    return cls


def _cmd_version(args: argparse.Namespace) -> int:
    print(
        f"tantra {_tantra.__version__} "
        f"(API {_tantra.API_VERSION}, schema {_tantra.SCHEMA_VERSION})"
    )
    return 0


def _cmd_backtest(args: argparse.Namespace) -> int:
    try:
        with open(args.bars_json, encoding="utf-8") as fh:
            data = json.load(fh)
        bars = _parse_bars(data)
    except (OSError, ValueError) as exc:
        print(f"backtest: could not load {args.bars_json}: {exc}", file=sys.stderr)
        return 2
    try:
        strategy_cls = _load_strategy(args.strategy)
    except ValueError as exc:
        print(f"backtest: {exc}", file=sys.stderr)
        return 2
    result = strategy_run(strategy_cls(), bars, algo_id=args.algo_id)
    print(result.summary())
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="tantra", description="Tantra Python SDK CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_version = sub.add_parser("version", help="print the SDK version and schema version")
    p_version.set_defaults(func=_cmd_version)

    p_backtest = sub.add_parser(
        "backtest", help="run a backtest from a bars JSON file (via tantra.strategy.run)"
    )
    p_backtest.add_argument(
        "--bars-json", required=True, metavar="PATH", help="path to a JSON bars file"
    )
    p_backtest.add_argument(
        "--strategy",
        metavar="MODULE:CLASS",
        help="dotted module path and Strategy subclass to run (default: built-in SMA cross)",
    )
    p_backtest.add_argument(
        "--algo-id", default="cli-backtest", metavar="ID", help="algo identifier for the run"
    )
    p_backtest.set_defaults(func=_cmd_backtest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
