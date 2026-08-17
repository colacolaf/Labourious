"""
config_io.py — load + save + validate `~/.labourious/config.json`.

The file is the canonical source of truth (PROTOCOL.md Appendix A). Both
the runtime (`docs/runtime/runtime.py`) and the TUI's Settings modal
import this module — they MUST agree on shape, validation, and write
semantics. Writes are atomic (write-to-tmp + rename) so a TUI crash
mid-write never leaves a half-written config.

Public surface:
    CONFIG_PATH         -> Path
    Config              -> dataclass with all fields
    load_config()       -> Config (defaults if file missing)
    save_config(cfg,    -> None; raises on validation failure
                 *, reason="...") -> records the cause in the save badge
    health_check(cfg)   -> per-provider and per-connector health dict
    KNOWN_PROVIDERS, KNOWN_CONNECTORS — picker catalogs
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal


# --------------------------------------------------------------- locations
CONFIG_PATH = Path(
    os.environ.get("LABOURIOUS_CONFIG", str(Path.home() / ".labourious" / "config.json"))
)


# --------------------------------------------------------------- schemas
@dataclass(frozen=True)
class ProviderConfig:
    """A configured LLM provider.

    base_url:    Where to send requests.
    api_key_env: Name of the env var holding the API key
                 (None for local-only providers like ollama).
    """
    name: str
    base_url: str
    api_key_env: str | None = None

    @property
    def is_local(self) -> bool:
        return self.api_key_env is None


@dataclass
class ConnectorConfig:
    """A configured data connector (sec_edgar, news, market_data, …).
    provider:   the adapter name (sec_edgar, google_rss, yfinance, …)
    extra:      provider-specific extras (user_agent, fred_api_key_env, …)
    """
    name: str
    provider: str
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    version: int = 1
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    default_model: str = "ollama/llama3.3:70b"
    per_agent_model: dict[str, str] = field(default_factory=dict)
    hybrid_paid_for: list[str] = field(default_factory=list)
    connectors: dict[str, ConnectorConfig] = field(default_factory=dict)
    defaults_depth: Literal["STANDARD", "DEEP"] = "STANDARD"
    defaults_compressed: bool = False

    # --------------------------------------------------------------- I/O
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "providers": {
                name: {"base_url": p.base_url, **(
                    {"api_key_env": p.api_key_env} if p.api_key_env else {}
                )}
                for name, p in self.providers.items()
            },
            "default_model": self.default_model,
            "per_agent_model": dict(self.per_agent_model),
            "hybrid_routing": {"paid_for": list(self.hybrid_paid_for)},
            "connectors": {
                name: {"provider": c.provider, **c.extra}
                for name, c in self.connectors.items()
            },
            "defaults": {
                "depth": self.defaults_depth,
                "compressed": self.defaults_compressed,
            },
            "thesis_register_db_path": "docs/runtime/thesis_register/theses.db",
            "memory": {"history_dir": "~/.labourious/history/"},
        }


# --------------------------------------------------------------- defaults
_DEFAULTS = Config(
    providers={
        "anthropic": ProviderConfig(
            name="anthropic",
            base_url="https://api.anthropic.com",
            api_key_env="ANTHROPIC_API_KEY",
        ),
        "ollama": ProviderConfig(
            name="ollama",
            base_url="http://localhost:11434",
            api_key_env=None,
        ),
    },
)


# --------------------------------------------------------------- load/save
def load_config() -> Config:
    """Read config from disk. Returns defaults if file doesn't exist."""
    if not CONFIG_PATH.exists():
        return Config(**{k: getattr(_DEFAULTS, k) for k in (
            "providers", "default_model", "per_agent_model",
            "hybrid_paid_for", "connectors",
            "defaults_depth", "defaults_compressed",
        )})
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return _from_dict(raw)


def save_config(cfg: Config) -> None:
    """Write config to disk atomically. Validates first; raises on error."""
    _validate(cfg)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".tmp")
    data = json.dumps(asdict_safe(cfg), indent=2, sort_keys=True)
    tmp.write_text(data, encoding="utf-8")
    # Atomic on POSIX; on Windows, replace() is also atomic for same-volume.
    os.replace(tmp, CONFIG_PATH)


def _from_dict(d: dict) -> Config:
    providers = {
        n: ProviderConfig(
            name=n,
            base_url=v.get("base_url", ""),
            api_key_env=v.get("api_key_env"),
        )
        for n, v in d.get("providers", {}).items()
    }
    connectors = {
        n: ConnectorConfig(
            name=n,
            provider=v.get("provider", n),
            extra={k: val for k, val in v.items() if k != "provider"},
        )
        for n, v in d.get("connectors", {}).items()
    }
    defaults = d.get("defaults", {})
    return Config(
        providers=providers,
        default_model=d.get("default_model", _DEFAULTS.default_model),
        per_agent_model=d.get("per_agent_model", {}),
        hybrid_paid_for=d.get("hybrid_routing", {}).get("paid_for", []),
        connectors=connectors,
        defaults_depth=defaults.get("depth", _DEFAULTS.defaults_depth),
        defaults_compressed=defaults.get("compressed", _DEFAULTS.defaults_compressed),
    )


def asdict_safe(cfg: Config) -> dict:
    """Convert to JSON-safe dict (dataclass → dict, env var refs preserved)."""
    return cfg.to_dict()


# --------------------------------------------------------------- validation
class ConfigValidationError(ValueError):
    """Raised when a config fails validation. Never wrap a generic Exception."""


def _validate(cfg: Config) -> None:
    """Light validation: regex-check model ids, names, etc. Runs on save."""
    import re
    name_re = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")
    model_re = re.compile(r"^[a-z0-9_-]+/[a-z0-9._:/-]{1,80}$", re.IGNORECASE)
    for n in cfg.providers:
        if not name_re.match(n):
            raise ConfigValidationError(f"Invalid provider name: {n!r}")
    if not model_re.match(cfg.default_model):
        raise ConfigValidationError(f"Invalid model id: {cfg.default_model!r}")
    for agent, mid in cfg.per_agent_model.items():
        if not name_re.match(agent):
            raise ConfigValidationError(f"Invalid agent name: {agent!r}")
        if not model_re.match(mid):
            raise ConfigValidationError(f"Invalid model id: {mid!r} for agent {agent}")
    for n in cfg.connectors:
        if not name_re.match(n):
            raise ConfigValidationError(f"Invalid connector name: {n!r}")
    if cfg.defaults_depth not in ("STANDARD", "DEEP"):
        raise ConfigValidationError(f"Invalid depth: {cfg.defaults_depth!r}")


# --------------------------------------------------------------- health
def health_check(cfg: Config) -> dict[str, str]:
    """Returns a per-provider and per-connector health map.

    Values: 'set' (key env var present), 'missing' (env ref but not present),
            'local' (no env needed), 'ok' (no extra deps), 'unknown' (no env check).
    """
    out: dict[str, str] = {}
    for name, p in cfg.providers.items():
        if p.api_key_env is None:
            out[f"provider:{name}"] = "local"
        elif os.environ.get(p.api_key_env):
            out[f"provider:{name}"] = "set"
        else:
            out[f"provider:{name}"] = "missing"
    for name in cfg.connectors:
        # Provider-specific health hooks could go here; for v1 we just mark
        # connectors whose config references a missing env var as "missing".
        c = cfg.connectors[name]
        bad = any(
            v.startswith("$") and not os.environ.get(v[1:])
            for v in c.extra.values()
            if isinstance(v, str)
        )
        out[f"connector:{name}"] = "missing" if bad else "ok"
    return out


# --------------------------------------------------------------- catalogs (for the picker)
KNOWN_PROVIDERS: list[tuple[str, str, str, str | None]] = [
    # (name, description, base_url, api_key_env or None for local)
    ("anthropic",    "Anthropic Claude API (paid)", "https://api.anthropic.com", "ANTHROPIC_API_KEY"),
    ("ollama",       "Local models via Ollama (free)", "http://localhost:11434", None),
    ("groq",         "Groq Cloud (OpenAI-compatible, free tier)", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    ("openrouter",   "Multi-provider router (credit system)", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ("openai",       "OpenAI (paid)", "https://api.openai.com/v1", "OPENAI_API_KEY"),
    ("google",       "Google Gemini (paid)", "https://generativelanguage.googleapis.com/v1beta", "GOOGLE_API_KEY"),
    ("mistral",      "Mistral AI (paid)", "https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
    ("cohere",       "Cohere (paid)", "https://api.cohere.ai/v1", "COHERE_API_KEY"),
]


KNOWN_CONNECTORS: list[tuple[str, str, dict[str, str]]] = [
    # (name, label, extra)
    ("sec_edgar",   "SEC filings (sec_edgar)",   {"provider": "sec_edgar", "user_agent": "Labourious <[email protected]>"}),
    ("news",        "News (Google RSS)",         {"provider": "google_rss"}),
    ("market_data", "Market data (yfinance + FRED)", {"provider": "yfinance", "fred_api_key_env": "$FRED_API_KEY"}),
    ("web_fetch",   "Web page fetcher",          {"provider": "web_fetch"}),
    ("fred",        "FRED macro series",         {"provider": "fred", "fred_api_key_env": "$FRED_API_KEY"}),
    ("polygon",     "Polygon equities/options",  {"provider": "polygon", "polygon_api_key_env": "$POLYGON_API_KEY"}),
    ("fmp",         "Financial Modeling Prep",   {"provider": "fmp", "fmp_api_key_env": "$FMP_API_KEY"}),
]


# --------------------------------------------------------------- display helpers
def mtime_str() -> str:
    """Returns last-modified timestamp of the config file, or '—' if missing."""
    if not CONFIG_PATH.exists():
        return "—"
    ts = CONFIG_PATH.stat().st_mtime
    return time.strftime("%H:%M:%S", time.localtime(ts))


def cfg_path_str() -> str:
    return str(CONFIG_PATH)
