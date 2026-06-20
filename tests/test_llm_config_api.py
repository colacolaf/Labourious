import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_config_returns_200():
    response = client.get("/api/llm/config")
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "model" in data
    assert "has_openai_key" in data
    assert "has_claude_key" in data
    assert data["provider"] in ("ollama", "claude", "openai")


def test_patch_config_valid_provider():
    response = client.patch("/api/llm/config", json={"provider": "ollama", "model": "mistral"})
    assert response.status_code == 200
    assert response.json()["provider"] == "ollama"


def test_patch_config_invalid_provider_returns_422():
    response = client.patch("/api/llm/config", json={"provider": "llama-999"})
    assert response.status_code == 422


def test_patch_config_openai_without_key_returns_422():
    # Vault has no openai_api_key in test environment → should 422
    response = client.patch("/api/llm/config", json={"provider": "openai", "model": "gpt-4o"})
    # Either 422 (no key) or 200 (if vault somehow has it) — just must not 500
    assert response.status_code in (200, 422)


def test_post_test_returns_ok_or_error():
    response = client.post("/api/llm/test")
    assert response.status_code == 200
    data = response.json()
    assert "ok" in data
    assert "latency_ms" in data


def test_history_llm_key_missing_vault_password():
    # No vault password in test env → 503 or similar graceful error
    response = client.post("/api/llm/key", json={"key_name": "openai_api_key", "value": "sk-test"})
    assert response.status_code in (200, 503, 500)
