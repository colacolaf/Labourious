import pytest
import os
import json
import tempfile
from backend.analytics.cost_estimator import estimate_monthly_cost
from backend.llm.config import LLMConfig, read_config, write_config


# --- cost_estimator ---

def test_ollama_is_free():
    assert estimate_monthly_cost("ollama", "mistral", 300) == 0.0


def test_zero_frequency_is_free():
    assert estimate_monthly_cost("claude", "claude-sonnet-4-6", 0) == 0.0


def test_claude_estimate_positive():
    cost = estimate_monthly_cost("claude", "claude-sonnet-4-6", 300)
    assert cost > 0.0


def test_openai_estimate_positive():
    cost = estimate_monthly_cost("openai", "gpt-4o", 300)
    assert cost > 0.0


def test_openai_costs_more_than_claude():
    claude_cost = estimate_monthly_cost("claude", "claude-sonnet-4-6", 300)
    openai_cost = estimate_monthly_cost("openai", "gpt-4o", 300)
    assert openai_cost > claude_cost


def test_unknown_model_returns_zero():
    assert estimate_monthly_cost("openai", "gpt-99-unknown", 300) == 0.0


def test_unknown_provider_returns_zero():
    assert estimate_monthly_cost("unknown_llm", "some-model", 300) == 0.0


# --- config ---

def test_read_config_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.llm.config.CONFIG_PATH", str(tmp_path / "nonexistent.json"))
    cfg = read_config()
    assert cfg.provider == "ollama"
    assert cfg.model == "mistral"


def test_write_then_read_config(tmp_path, monkeypatch):
    path = str(tmp_path / "llm_config.json")
    monkeypatch.setattr("backend.llm.config.CONFIG_PATH", path)
    cfg = LLMConfig(provider="openai", model="gpt-4o", ollama_url="http://localhost:11434")
    write_config(cfg)
    loaded = read_config()
    assert loaded.provider == "openai"
    assert loaded.model == "gpt-4o"


def test_read_config_corrupt_file_returns_defaults(tmp_path, monkeypatch):
    path = str(tmp_path / "llm_config.json")
    with open(path, "w") as f:
        f.write("NOT JSON {{{{")
    monkeypatch.setattr("backend.llm.config.CONFIG_PATH", path)
    cfg = read_config()
    assert cfg.provider == "ollama"
