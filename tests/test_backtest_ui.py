import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_backtest_run_returns_run_id():
    response = client.post("/api/backtest/run", json={
        "agent_id": 999,   # non-existent, will be stored
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
        "mode": "basic",
    })
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert isinstance(data["run_id"], str)


def test_backtest_poll_returns_status():
    # Create a run first
    run_resp = client.post("/api/backtest/run", json={
        "agent_id": 999,
        "start_date": "2024-01-01",
        "end_date": "2024-03-31",
        "mode": "basic",
    })
    run_id = run_resp.json()["run_id"]
    # Poll it
    response = client.get(f"/api/backtest/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run_id
    assert data["status"] in ("running", "done", "failed")


def test_backtest_poll_unknown_id_returns_404():
    response = client.get("/api/backtest/nonexistent-id-abc")
    assert response.status_code == 404


def test_backtest_history_returns_list():
    response = client.get("/api/backtest/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_backtest_history_filter_by_agent():
    response = client.get("/api/backtest/history?agent_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
