import pytest


def test_health_check_status(client):
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_check_fields(client):
    data = client.get("/api/health").json()
    assert "status" in data
    assert "version" in data
    assert "timestamp" in data


def test_health_check_ok(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "health" in data


def test_db_health_endpoint(client):
    response = client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health_full_returns_all_subsystems(client):
    resp = client.get("/api/health/full")
    assert resp.status_code == 200
    data = resp.json()
    assert "backend" in data
    assert "db" in data
    assert "vault" in data
    assert "llm" in data
