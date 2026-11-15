"""Tests for tantra.quant and tantra.optimizer (ex 0001 wheel surface)."""
from decimal import Decimal

import pytest

from tantra.optimizer import (
    ParetoPoint,
    extract_pareto_frontier,
    plot_pareto,
    sharpe_sortino_dd,
)
from tantra.quant import (
    covariance_matrix,
    mean,
    ols,
    returns,
    solve_linear_system,
    std_dev,
)


def test_returns_golden():
    prices = [Decimal("100"), Decimal("110"), Decimal("99")]
    assert returns(prices) == [Decimal("0.1"), Decimal("-0.1")]


def test_returns_requires_two():
    with pytest.raises(ValueError):
        returns([Decimal("100")])


def test_mean_std_dev():
    values = [Decimal("2"), Decimal("4"), Decimal("4"), Decimal("4"), Decimal("5"), Decimal("5"), Decimal("7"), Decimal("9")]
    assert mean(values) == Decimal("5")
    assert std_dev(values) == Decimal("2")


def test_covariance_matrix_and_solver():
    # Two assets, perfectly anti-correlated observations.
    panel = [[Decimal("1"), Decimal("5")], [Decimal("2"), Decimal("4")], [Decimal("3"), Decimal("3")]]
    cov = covariance_matrix(panel)
    assert len(cov) == 2
    assert all(len(row) == 2 for row in cov)
    # x = 1, y = 2 solves [[1,0],[0,1]] x = [1, 2]
    solution = solve_linear_system([[Decimal("1"), Decimal("0")], [Decimal("0"), Decimal("1")]], [Decimal("1"), Decimal("2")])
    assert solution == [Decimal("1"), Decimal("2")]


def test_solve_linear_system_singular_raises():
    with pytest.raises(ArithmeticError):
        solve_linear_system([[Decimal("1"), Decimal("1")], [Decimal("1"), Decimal("1")]], [Decimal("1"), Decimal("2")])


def test_ols_golden():
    # y = 2x + 1 (design with constant column)
    design = [[Decimal("1"), Decimal("0")], [Decimal("1"), Decimal("1")], [Decimal("1"), Decimal("2")]]
    y = [Decimal("1"), Decimal("3"), Decimal("5")]
    beta = ols(design, y)
    assert len(beta) == 2
    assert beta[0] == Decimal("1")
    assert beta[1] == Decimal("2")


def test_extract_pareto_frontier():
    results = [
        {"status": "ok", "return_pct": 10.0, "max_dd_pct": 5.0, "sharpe": 1.2, "fast": 5, "slow": 10},
        {"status": "ok", "return_pct": 12.0, "max_dd_pct": 8.0, "sharpe": 1.4, "fast": 10, "slow": 20},
        {"status": "ok", "return_pct": 8.0, "max_dd_pct": 4.0, "sharpe": 1.0, "fast": 3, "slow": 8},
        {"status": "error", "return_pct": 50.0, "max_dd_pct": 1.0},
    ]
    frontier = extract_pareto_frontier(results)
    assert all(isinstance(p, ParetoPoint) for p in frontier)
    # error rows are excluded; frontier rises with drawdown
    assert frontier[0].return_pct == 8.0
    assert frontier[-1].return_pct == 12.0


def test_plot_pareto_returns_string():
    p = ParetoPoint(fast=5, slow=10, return_pct=10.0, max_dd_pct=5.0, sharpe=1.2)
    plot = plot_pareto([p])
    assert "Pareto Frontier" in plot
    assert "* = Pareto optimal" in plot


def test_sharpe_sortino_dd_weights():
    score = sharpe_sortino_dd(1.0, 1.0, 1.0, 5.0)
    assert score == pytest.approx(0.5 + 0.3 + 0.15 + (1.0 / 6.0) * 0.05)
