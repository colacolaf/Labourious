"""Tests for Task 16 routers: brokers, trades, dashboard, settings."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_brokers_available():
    r = client.get("/api/brokers/available")
    assert r.status_code == 200
    assert "brokers" in r.json()
    assert "alpaca" in r.json()["brokers"]


def test_brokers_list_empty():
    r = client.get("/api/brokers")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_brokers_connect_unknown():
    r = client.post("/api/brokers/connect", json={
        "broker_name": "unknown_broker", "api_key": "k", "secret": "s"
    })
    assert r.status_code == 400


def test_trades_list():
    r = client.get("/api/trades")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_trades_export_csv():
    r = client.get("/api/trades/export")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]


def test_dashboard_summary():
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total_pnl" in data
    assert "agent_count" in data


def test_dashboard_performance():
    r = client.get("/api/dashboard/performance")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_dashboard_allocation():
    r = client.get("/api/dashboard/allocation")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_dashboard_equity_curve():
    r = client.get("/api/dashboard/equity-curve")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_dashboard_risk():
    r = client.get("/api/dashboard/risk")
    assert r.status_code == 200
    assert "agents_at_risk" in r.json()


def test_settings_get():
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert "llm" in data
    assert "allocation" in data


def test_settings_update_llm():
    r = client.post("/api/settings/llm", json={"use_local_llm": False, "ollama_model": "llama2"})
    assert r.status_code == 200
    assert r.json()["llm"]["use_local_llm"] is False


def test_settings_update_allocation():
    r = client.post("/api/settings/allocation", json={
        "max_portfolio_drawdown": 0.20,
        "default_position_size": 0.03,
        "max_agents": 10,
    })
    assert r.status_code == 200
    assert r.json()["allocation"]["max_agents"] == 10
