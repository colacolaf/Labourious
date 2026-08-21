"""
providers.py — the canonical catalog of supported LLM providers.

21 entries, organized by tier:
  Tier 1 — Local (no API key required; runs on the user's machine)
  Tier 2 — Free cloud (rate-limited, no $ required)
  Tier 3 — Paid cloud (gold standard, billed per token)
  Tier 4 — Custom (specialty aggregators and OpenAI-compatible fallbacks)

The catalog drives:
  - The default provider list in the Settings → Providers panel (L3 layout)
  - The model dropdown inside each provider's expanded pane
  - The connection-test logic (auth + base URL probe)
  - The preview catalog on first launch (welcome screen)

Connection shape column pre-computes whether we hit the OpenAI-compatible
endpoint or the native SDK. 12 of 21 are OpenAI-shaped — connector layer
can reuse one client. The other 9 need bespoke adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Tier = Literal["local", "free", "paid", "custom"]
AuthKind = Literal["none", "bearer", "header", "oauth", "pat"]


@dataclass(frozen=True)
class ProviderEntry:
    """One row in the catalog. Immutable by design."""
    name: str                          # the key used in config.json
    display: str                       # human label shown in the panel
    tier: Tier
    auth: AuthKind
    base_url: str | None               # None when the provider is a CLI tool (OmniRoute)
    env_var: str | None                # env var name holding the API key
    default_model: str                 # initial model
    models: tuple[str, ...]            # curated list shown in the model dropdown
    shape: Literal["openai", "anthropic", "google", "ollama", "hf", "custom"]
    description: str                   # one-line tooltip / description
    recommended: bool = False          # shown in welcome state


# ----------------------------------------------------------- tier 1 · local
_LOCAL = (
    ProviderEntry(
        name="ollama",
        display="Ollama",
        tier="local",
        auth="none",
        base_url="http://localhost:11434",
        env_var=None,
        default_model="llama3.3:70b",
        models=("llama3.3:70b", "qwen2.5:72b", "deepseek-r1:70b",
                "mistral-large", "gemma3:27b", "phi4:14b"),
        shape="ollama",
        description="Local models via Ollama — zero config, runs offline",
        recommended=True,
    ),
    ProviderEntry(
        name="lm_studio",
        display="LM Studio",
        tier="local",
        auth="none",
        base_url="http://localhost:1234/v1",
        env_var=None,
        default_model="local-model",
        models=("local-model",),
        shape="openai",
        description="Local models via LM Studio — desktop GUI runner",
        recommended=False,
    ),
    ProviderEntry(
        name="omniroute",
        display="OmniRoute",
        tier="local",
        auth="none",
        # OmniRoute is a local OpenAI-compatible gateway (npm i -g omniroute).
        # Default port per upstream docs: 20128 (NOT 8317 — that was an old
        # version we tracked before re-reading the npm page in 2026-08).
        base_url="http://localhost:20128/v1",
        env_var=None,
        # Default model: `auto` is OmniRoute's "you pick the best free
        # combo" mode. The prefix variants below tune the routing strategy
        # (latency vs cost vs offline quota etc.). All OpenAI-compatible.
        default_model="auto",
        models=(
            "auto",
            "auto/coding",
            "auto/fast",
            "auto/cheap",
            "auto/offline",
            "auto/smart",
        ),
        shape="openai",
        description=(
            "Local OpenAI-compat gateway — `npm i -g omniroute` unlocks "
            "~1.5B free tokens/month across 43 provider pools / 516 models, "
            "auto-routing + zero config"
        ),
        recommended=True,
    ),
    ProviderEntry(
        name="vllm",
        display="vLLM / llama.cpp",
        tier="local",
        auth="none",
        base_url="http://localhost:8000/v1",
        env_var=None,
        default_model="local-model",
        models=("local-model",),
        shape="openai",
        description="Self-hosted OpenAI-compatible server (vLLM, llama.cpp server, TGI)",
        recommended=False,
    ),
    ProviderEntry(
        name="custom_openai",
        display="Custom OpenAI-compat",
        tier="local",
        auth="bearer",
        base_url=None,
        env_var="CUSTOM_API_KEY",
        default_model="user/default",
        models=(),
        shape="openai",
        description="Any OpenAI-compatible endpoint — paste a base URL + key",
        recommended=False,
    ),
)


# ----------------------------------------------------------- tier 2 · free
_FREE = (
    ProviderEntry(
        name="openrouter",
        display="OpenRouter",
        tier="free",
        auth="bearer",
        base_url="https://openrouter.ai/api/v1",
        env_var="OPENROUTER_API_KEY",
        default_model="meta-llama/llama-3.3-70b-instruct:free",
        models=(
            "meta-llama/llama-3.3-70b-instruct:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "qwen/qwen-2.5-72b-instruct:free",
            "deepseek/deepseek-r1:free",
        ),
        shape="openai",
        description="One key, 500+ models — free tier rotates daily. Best breadth.",
        recommended=True,
    ),
    ProviderEntry(
        name="groq",
        display="Groq",
        tier="free",
        auth="bearer",
        base_url="https://api.groq.com/openai/v1",
        env_var="GROQ_API_KEY",
        default_model="llama-3.3-70b-versatile",
        models=(
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "deepseek-r1-distill-llama-70b",
            "whisper-large-v3",
        ),
        shape="openai",
        description="Blazing-fast free inference — 30 RPM, 6K TPM, 14.4K RPD",
        recommended=True,
    ),
    ProviderEntry(
        name="google_ai_studio",
        display="Google AI Studio",
        tier="free",
        auth="bearer",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        env_var="GOOGLE_API_KEY",
        default_model="gemini-2.0-flash",
        models=("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"),
        shape="google",
        description="Free Gemini Flash tier — 1M-token context for SEC filings",
        recommended=False,
    ),
    ProviderEntry(
        name="mistral",
        display="Mistral",
        tier="free",
        auth="bearer",
        base_url="https://api.mistral.ai/v1",
        env_var="MISTRAL_API_KEY",
        default_model="mistral-small-latest",
        models=("mistral-small-latest", "open-mistral-7b",
                "mistral-large-latest"),
        shape="openai",
        description="Mistral La Plateforme free tier — small open models",
        recommended=False,
    ),
    ProviderEntry(
        name="huggingface",
        display="Hugging Face",
        tier="free",
        auth="bearer",
        base_url="https://router.huggingface.co/v1",
        env_var="HF_TOKEN",
        default_model="meta-llama/Llama-3.3-70B-Instruct",
        models=(
            "meta-llama/Llama-3.3-70B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "Qwen/Qwen2.5-72B-Instruct",
            "deepseek-ai/DeepSeek-R1",
        ),
        shape="openai",
        description="Serverless inference for thousands of OSS models — rate-limited",
        recommended=False,
    ),
    ProviderEntry(
        name="cerebras",
        display="Cerebras",
        tier="free",
        auth="bearer",
        base_url="https://api.cerebras.ai/v1",
        env_var="CEREBRAS_API_KEY",
        default_model="llama-3.3-70b",
        models=("llama-3.3-70b", "llama-3.1-8b", "qwen-3-32b"),
        shape="openai",
        description="1M tokens/day free — wafer-scale fast inference",
        recommended=False,
    ),
    ProviderEntry(
        name="cohere",
        display="Cohere",
        tier="free",
        auth="bearer",
        base_url="https://api.cohere.com/v2",
        env_var="COHERE_API_KEY",
        default_model="command-r-plus",
        models=("command-r-plus", "command-r"),
        shape="cohere",  # bespoke adapter
        description="Cohere Command-R+ — free trial tier for RAG workloads",
        recommended=False,
    ),
)


# ----------------------------------------------------------- tier 3 · paid
_PAID = (
    ProviderEntry(
        name="anthropic",
        display="Anthropic Claude",
        tier="paid",
        auth="bearer",
        base_url="https://api.anthropic.com",
        env_var="ANTHROPIC_API_KEY",
        default_model="claude-sonnet-4-5",
        models=("claude-sonnet-4-5", "claude-opus-4", "claude-haiku-4"),
        shape="anthropic",
        description="Claude family — best analytical writing & tool use",
        recommended=False,
    ),
    ProviderEntry(
        name="openai",
        display="OpenAI",
        tier="paid",
        auth="bearer",
        base_url="https://api.openai.com/v1",
        env_var="OPENAI_API_KEY",
        default_model="gpt-4.1",
        models=("gpt-4.1", "gpt-4o", "o3", "o4-mini", "gpt-4.1-mini"),
        shape="openai",
        description="OpenAI — strong tool-calling & coding workloads",
        recommended=False,
    ),
    ProviderEntry(
        name="gemini_vertex",
        display="Google Gemini (Vertex)",
        tier="paid",
        auth="oauth",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        env_var="GOOGLE_API_KEY",
        default_model="gemini-2.5-pro",
        models=("gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-pro"),
        shape="google",
        description="Vertex / AI Studio paid — 2M ctx, multimodal PDFs",
        recommended=False,
    ),
    ProviderEntry(
        name="grok",
        display="xAI Grok",
        tier="paid",
        auth="bearer",
        base_url="https://api.x.ai/v1",
        env_var="XAI_API_KEY",
        default_model="grok-4",
        models=("grok-4", "grok-3", "grok-4-fast"),
        shape="openai",
        description="Grok — real-time X/Twitter data, strong for sentiment agents",
        recommended=False,
    ),
)


# ----------------------------------------------------------- tier 4 · custom
_CUSTOM = (
    ProviderEntry(
        name="perplexity",
        display="Perplexity",
        tier="custom",
        auth="bearer",
        base_url="https://api.perplexity.ai",
        env_var="PPLX_API_KEY",
        default_model="sonar-pro",
        models=("sonar-pro", "sonar", "sonar-reasoning-pro"),
        shape="openai",
        description="Live web-cited research — could replace web-research agent",
        recommended=False,
    ),
    ProviderEntry(
        name="fireworks",
        display="Fireworks AI",
        tier="custom",
        auth="bearer",
        base_url="https://api.fireworks.ai/inference/v1",
        env_var="FIREWORKS_API_KEY",
        default_model="accounts/fireworks/models/llama-v3p3-70b-instruct",
        models=("accounts/fireworks/models/llama-v3p3-70b-instruct",
                "accounts/fireworks/models/deepseek-r1"),
        shape="openai",
        description="OSS models at scale — fast, cheaper than Groq for batch",
        recommended=False,
    ),
    ProviderEntry(
        name="together",
        display="Together AI",
        tier="custom",
        auth="bearer",
        base_url="https://api.together.xyz/v1",
        env_var="TOGETHER_API_KEY",
        default_model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        models=("meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "deepseek-ai/DeepSeek-R1"),
        shape="openai",
        description="OSS models — free trial credits, Groq backup",
        recommended=False,
    ),
    ProviderEntry(
        name="deepseek",
        display="DeepSeek (direct)",
        tier="custom",
        auth="bearer",
        base_url="https://api.deepseek.com/v1",
        env_var="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
        models=("deepseek-chat", "deepseek-reasoner"),
        shape="openai",
        description="Cheapest frontier reasoning — V3 + R1 direct from DeepSeek",
        recommended=False,
    ),
)


# ----------------------------------------------------------- canonical catalog
ALL_PROVIDERS: tuple[ProviderEntry, ...] = (
    *_LOCAL, *_FREE, *_PAID, *_CUSTOM
)


# ----------------------------------------------------------- lookups
TIER_ORDER: tuple[Tier, ...] = ("local", "free", "paid", "custom")
TIER_LABEL: dict[Tier, str] = {
    "local": "Local", "free": "Free cloud", "paid": "Paid", "custom": "Custom",
}


def by_name(name: str) -> ProviderEntry | None:
    for p in ALL_PROVIDERS:
        if p.name == name:
            return p
    return None


def by_tier(tier: Tier) -> tuple[ProviderEntry, ...]:
    return tuple(p for p in ALL_PROVIDERS if p.tier == tier)


def tier_counts() -> dict[Tier, int]:
    out: dict[Tier, int] = {t: 0 for t in TIER_ORDER}
    for p in ALL_PROVIDERS:
        out[p.tier] += 1
    return out


def total_count() -> int:
    return len(ALL_PROVIDERS)


def recommended() -> tuple[ProviderEntry, ...]:
    """Used by the welcome / empty-state screen."""
    return tuple(p for p in ALL_PROVIDERS if p.recommended)


# ----------------------------------------------------------- status helpers
@dataclass(frozen=True)
class ProviderStatus:
    """Runtime status for the panel's row dot."""
    state: Literal["ready", "auth-missing", "auth-present", "not-running",
                   "not-installed", "config-not-set", "key-loaded"]
    detail: str


def status_for(entry: ProviderEntry) -> ProviderStatus:
    """Compute the row state. Cheap; pure-function of (entry, keyring).

    The real keyring probe is in keys_storage.status_for(); this is the
    catalog-aware helper it delegates to.
    """
    # Imported lazily to avoid circular import at module load.
    from frontend.keys_storage import get_key, key_present, probe_endpoint
    if entry.tier == "local":
        if entry.base_url and probe_endpoint(entry.base_url):
            return ProviderStatus(state="ready",
                                  detail=f"● connected · {entry.default_model}")
        return ProviderStatus(state="not-running",
                              detail="— not running")
    if entry.tier == "free" or entry.tier == "paid" or entry.tier == "custom":
        if key_present(entry.name):
            return ProviderStatus(state="key-loaded",
                                  detail="● ready · key in keychain")
        return ProviderStatus(state="auth-missing",
                              detail="— no API key")
    return ProviderStatus(state="config-not-set", detail="— config not set")
