import json
import os
from dataclasses import dataclass, asdict

CONFIG_PATH = "data/llm_config.json"

DEFAULTS = {"provider": "ollama", "model": "mistral", "ollama_url": "http://localhost:11434"}


@dataclass
class LLMConfig:
    provider: str = "ollama"
    model: str = "mistral"
    ollama_url: str = "http://localhost:11434"


def read_config() -> LLMConfig:
    try:
        with open(CONFIG_PATH) as f:
            data = {**DEFAULTS, **json.load(f)}
        return LLMConfig(
            provider=data["provider"],
            model=data["model"],
            ollama_url=data["ollama_url"],
        )
    except Exception:
        return LLMConfig()


def write_config(cfg: LLMConfig) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH) or ".", exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(asdict(cfg), f, indent=2)
