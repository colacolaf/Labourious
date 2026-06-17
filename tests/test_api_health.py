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
