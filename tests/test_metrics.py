import math
import pytest
from backend.analytics.metrics import (
    compute_sharpe,
    compute_max_drawdown,
    compute_correlation_matrix,
    compute_attribution,
)


def test_compute_sharpe_positive():
    returns = [0.01, 0.02, -0.005, 0.015, 0.008] * 10  # 50 data points
    result = compute_sharpe(returns)
    assert isinstance(result, float)
    assert result > 0


def test_compute_sharpe_zero_std():
    # All same return → std=0 → sharpe=0.0
    returns = [0.01] * 30
    assert compute_sharpe(returns) == 0.0


def test_compute_sharpe_empty():
    assert compute_sharpe([]) == 0.0


def test_compute_max_drawdown_basic():
    # Equity goes 100 → 150 → 90 — drawdown = (90-150)/150 = -0.4
    equity = [100.0, 120.0, 150.0, 130.0, 90.0]
    dd = compute_max_drawdown(equity)
    assert dd < 0
    assert abs(dd - (-0.4)) < 0.001


def test_compute_max_drawdown_no_drawdown():
    equity = [100.0, 110.0, 120.0, 130.0]
    assert compute_max_drawdown(equity) == 0.0


def test_compute_max_drawdown_empty():
    assert compute_max_drawdown([]) == 0.0


def test_compute_correlation_matrix_identical():
    # Same series → correlation = 1.0
    data = {"A": [1.0, 2.0, 3.0, 4.0], "B": [1.0, 2.0, 3.0, 4.0]}
    result = compute_correlation_matrix(data)
    assert abs(result["A"]["B"] - 1.0) < 0.001
    assert abs(result["B"]["A"] - 1.0) < 0.001


def test_compute_correlation_matrix_uncorrelated():
    import random
    random.seed(42)
    data = {
        "A": [1.0, -1.0, 1.0, -1.0, 1.0, -1.0],
        "B": [1.0,  1.0, 1.0,  1.0, 1.0,  1.0],
    }
    result = compute_correlation_matrix(data)
    assert abs(result["A"]["B"]) < 0.1


def test_compute_correlation_matrix_single_agent():
    data = {"A": [0.01, 0.02, -0.01]}
    result = compute_correlation_matrix(data)
    assert result == {}  # no pairs


def test_compute_attribution_sums_to_100():
    trades = [
        {"agent_id": 1, "pnl": 420.0,  "closed_at": "2026-06-19T15:00:00"},
        {"agent_id": 2, "pnl": 210.0,  "closed_at": "2026-06-19T14:00:00"},
        {"agent_id": 3, "pnl": -85.0,  "closed_at": "2026-06-19T12:00:00"},
    ]
    result = compute_attribution(trades, "2026-06-19")
    # sum of abs pct contributions = 100
    total = sum(abs(v) for v in result.values())
    assert abs(total - 100.0) < 0.01


def test_compute_attribution_empty():
    assert compute_attribution([], "2026-06-19") == {}


def test_compute_attribution_filters_by_date():
    trades = [
        {"agent_id": 1, "pnl": 100.0, "closed_at": "2026-06-19T15:00:00"},
        {"agent_id": 2, "pnl": 200.0, "closed_at": "2026-06-18T15:00:00"},  # different day
    ]
    result = compute_attribution(trades, "2026-06-19")
    assert "1" in result
    assert "2" not in result
