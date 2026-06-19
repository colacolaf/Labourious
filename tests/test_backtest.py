"""Tests for backtest CLI (Task 18)."""
import pytest
import numpy as np
import pandas as pd


def make_ohlcv(n=60):
    """Synthetic OHLCV DataFrame."""
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = np.cumsum(np.random.randn(n)) + 100
    return pd.DataFrame(
        {
            "Open": close * 0.99,
            "High": close * 1.01,
            "Low": close * 0.98,
            "Close": close,
            "Volume": np.random.randint(100000, 1000000, n),
        },
        index=dates,
    )


def test_compute_metrics_basic():
    from backend.scripts.backtest import compute_metrics

    trades = [
        {"pnl": 100, "side": "BUY"},
        {"pnl": -50, "side": "SELL"},
        {"pnl": 200, "side": "BUY"},
    ]
    metrics = compute_metrics(trades, initial_balance=10000)
    assert "total_return" in metrics
    assert "win_rate" in metrics
    assert "sharpe_ratio" in metrics
    assert "max_drawdown" in metrics
    assert metrics["win_rate"] == pytest.approx(2 / 3, rel=0.01)


def test_run_basic_backtest_synthetic():
    from backend.scripts.backtest import run_basic_backtest

    df = make_ohlcv(60)
    agent_config = {
        "symbol": "AAPL",
        "context": "BUY if RSI < 30. SELL if RSI > 70.",
        "initial_balance": 10000,
    }
    result = run_basic_backtest(df, agent_config)
    assert "trades" in result
    assert "metrics" in result
    assert isinstance(result["trades"], list)


def test_walk_forward_produces_windows():
    from backend.scripts.backtest import run_walk_forward

    # 200 rows → window_size=50, test portion=12 rows (>10 threshold) → all 4 windows kept
    df = make_ohlcv(200)
    agent_config = {
        "symbol": "AAPL",
        "context": "BUY if price < MA20.",
        "initial_balance": 10000,
    }
    result = run_walk_forward(df, agent_config, windows=4)
    assert "windows" in result
    assert len(result["windows"]) == 4
    assert "efficiency" in result
