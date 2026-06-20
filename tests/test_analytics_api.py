import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_portfolio_endpoint_returns_200():
    response = client.get("/api/analytics/portfolio")
    assert response.status_code == 200
    data = response.json()
    assert "total_pnl" in data
    assert "sharpe_ratio" in data
    assert "max_drawdown" in data
    assert "win_rate" in data
    assert "return_30d_pct" in data


def test_equity_curve_default_days():
    response = client.get("/api/analytics/equity-curve")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_equity_curve_custom_days():
    response = client.get("/api/analytics/equity-curve?days=7")
    assert response.status_code == 200


def test_leaderboard_returns_list():
    response = client.get("/api/analytics/leaderboard")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_leaderboard_sort_by_sharpe():
    response = client.get("/api/analytics/leaderboard?sort_by=sharpe")
    assert response.status_code == 200


def test_correlation_returns_dict():
    response = client.get("/api/analytics/correlation")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_attribution_today():
    response = client.get("/api/analytics/attribution")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert "contributions" in data


def test_attribution_specific_date():
    response = client.get("/api/analytics/attribution?date=2026-06-19")
    assert response.status_code == 200
