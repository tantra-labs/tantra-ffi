"""Tests for the wheel `tantra.algo_analytics` package (gap 0001 closure)."""

import math
from dataclasses import dataclass
from datetime import date
from statistics import NormalDist

import pytest

from tantra.algo_analytics import deflated_sharpe, plan_folds, walk_forward
from tantra.algo_analytics.monte_carlo import (
    StartDateConfig,
    offsets_to_ranges,
    summarise_start_dates,
)


def test_plan_folds_expanding_geometry() -> None:
    start = date(2020, 1, 1)
    end = date(2021, 7, 1)
    folds = plan_folds(
        start, end, train_months=6, test_months=2, n_folds=3, window="expanding"
    )
    assert len(folds) == 3
    # fold 0: train [2020-01-01, 2020-07-01), test [2020-07-01, 2020-09-01)
    assert folds[0].train_start == date(2020, 1, 1)
    assert folds[0].train_end == date(2020, 7, 1)
    assert folds[0].test_start == date(2020, 7, 1)
    assert folds[0].test_end == date(2020, 9, 1)
    # expanding: the training window only grows, anchored at start
    assert folds[1].train_start == date(2020, 1, 1)
    assert folds[1].train_end == date(2020, 9, 1)
    assert folds[1].test_end == date(2020, 11, 1)
    assert folds[2].train_end == date(2020, 11, 1)
    assert folds[2].test_end == date(2021, 1, 1)
    # contiguous, non-overlapping test windows: train_end == next test_start
    assert folds[0].test_end == folds[1].test_start
    assert folds[1].test_end == folds[2].test_start


def test_plan_folds_rolling_geometry() -> None:
    start = date(2020, 1, 1)
    end = date(2021, 7, 1)
    folds = plan_folds(
        start, end, train_months=6, test_months=2, n_folds=3, window="rolling"
    )
    assert len(folds) == 3
    # rolling: the training window slides forward by test_months per fold
    assert folds[0].train_start == date(2020, 1, 1)
    assert folds[1].train_start == date(2020, 3, 1)
    assert folds[2].train_start == date(2020, 5, 1)
    assert folds[0].train_end == date(2020, 7, 1)
    assert folds[1].train_end == date(2020, 9, 1)


def test_plan_folds_rejects_short_range() -> None:
    with pytest.raises(ValueError):
        plan_folds(date(2020, 1, 1), date(2020, 6, 1), train_months=6, test_months=2, n_folds=3)


def test_deflated_sharpe_known_input() -> None:
    observed_sr = 0.2
    n_trials = 1000
    t = 252
    # Hand-computed expected value from the Bailey & Lopez de Prado (2014)
    # reference formulas, built independently with math + NormalDist.
    v_sr = (1.0 + observed_sr**2 / 2.0) / (t - 1)
    log_n = math.log(n_trials)
    mu_max_z = math.sqrt(2.0 * log_n) - (math.log(log_n) + math.log(4.0 * math.pi)) / (
        2.0 * math.sqrt(2.0 * log_n)
    )
    mu_max = mu_max_z * math.sqrt(v_sr)
    sigma_max = math.sqrt(v_sr * (1.0 - 2.0 / math.pi))
    expected = NormalDist().cdf((observed_sr - mu_max) / sigma_max)

    actual = deflated_sharpe(observed_sr, n_trials, t=t)
    assert actual == pytest.approx(expected)
    assert 0.0 < actual < 1.0


def test_deflated_sharpe_errors() -> None:
    with pytest.raises(ValueError):
        deflated_sharpe(float("nan"), 10)
    with pytest.raises(ValueError):
        deflated_sharpe(0.5, -1)
    with pytest.raises(ValueError):
        deflated_sharpe(0.5, 10, t=1)


def test_monte_carlo_machinery_is_deterministic() -> None:
    start = date(2020, 1, 1)
    end = date(2021, 1, 1)
    ranges = offsets_to_ranges(start, end, (0, 5, 10))
    assert len(ranges) == 3
    assert ranges[0] == (start, end)
    assert ranges[1] == (date(2020, 1, 6), date(2021, 1, 6))

    gates = StartDateConfig(symbol="NIFTY50", start=start, end=end, offsets=(0, 5, 10))
    first = summarise_start_dates(
        final_equities=[100000.0, 101000.0, 99000.0],
        max_drawdown_pcts=[8.0, 9.0, 7.0],
        gates=gates,
    )
    second = summarise_start_dates(
        final_equities=[100000.0, 101000.0, 99000.0],
        max_drawdown_pcts=[8.0, 9.0, 7.0],
        gates=gates,
    )
    assert first == second  # deterministic: same inputs, same verdict
    assert len(first.final_equities) == 3
    assert len(first.offsets) == 3
    assert isinstance(first.passed, bool)


@dataclass
class FakeResult:
    """BacktestResult-shaped stand-in for the injected runner."""

    metrics: dict
    equity_curve: list[tuple[str, float]]


def _fake_result() -> FakeResult:
    return FakeResult(
        metrics={
            "total_return_pct": 12.5,
            "max_drawdown_pct": 8.0,
            "final_equity": 112500.0,
            "n_fills": 10,
            "n_trades": 5,
        },
        equity_curve=[
            ("2024-01-01", 100000.0),
            ("2024-01-02", 100500.0),
            ("2024-01-03", 101000.0),
            ("2024-01-04", 101500.0),
            ("2024-01-05", 102000.0),
        ],
    )


def _stub_runner(strategy, *, symbol, exchange, start, end, data=None, **backtest_kwargs) -> FakeResult:
    return _fake_result()


def test_walk_forward_with_stub_runner() -> None:
    result = walk_forward(
        None,
        start=date(2020, 1, 1),
        end=date(2024, 1, 1),
        symbol="NIFTY50",
        train_months=12,
        test_months=3,
        n_folds=3,
        runner=_stub_runner,
    )
    assert len(result.folds) == 3
    assert isinstance(result.passed, bool)
    # every fold's stats were read off the stub result (same FakeResult per fold)
    assert all(fold.in_sample.final_equity == 112500.0 for fold in result.folds)
    assert all(fold.out_of_sample.n_fills == 10 for fold in result.folds)


def test_walk_forward_without_runner_raises() -> None:
    with pytest.raises(RuntimeError, match="session orchestrator"):
        walk_forward(
            None,
            start=date(2020, 1, 1),
            end=date(2024, 1, 1),
            symbol="NIFTY50",
            train_months=12,
            test_months=3,
            n_folds=3,
        )


def test_train_test_split_with_stub_runner() -> None:
    from tantra.algo_analytics import train_test_split

    in_sample, out_of_sample = train_test_split(
        None,
        start=date(2020, 1, 1),
        end=date(2020, 6, 1),
        train_end=date(2020, 3, 1),
        symbol="NIFTY50",
        runner=_stub_runner,
    )
    assert in_sample.final_equity == 112500.0
    assert out_of_sample.final_equity == 112500.0
