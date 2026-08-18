# adapters/openai_compat.py — Any OpenAI-compatible API.
#
# Covers (13 providers; mirrors `frontend/providers.py`):
#   Tier 1: lmstudio, vllm, custom          (local-first, no- or user-key)
#   Tier 2: openrouter, mistral, hf-router, cerebras
#   Tier 3: openai, xai
#   Tier 4: perplexity, fireworks, together, deepseek
#
# Anthropic / Gemini / Groq / Ollama / Cohere have their own adapters
# (they don't speak /v1/chat/completions, or have non-trivial edge cases).
#
# Auth precedence (highest first):
#   1. OS keychain via `frontend.keys_storage.get_key(provider_name)`
#      — anything the user added through the Settings modal.
#   2. Environment variable per provider (`OPENAI_API_KEY`, `XAI_API_KEY` …)
#   3. `OPENAI_COMPAT_API_KEY` legacy fallback (single key for any provider)
#
# Models:
#   "<provider>/<model-id>"   — provider prefix is what we route on.
#   "<model-id>" alone         — assumed to be `openai/<model-id>`.
#
# Two entry points:
#   - `.call(...)` → single Response (text + usage + cost) — for batch
#     agents that don't need incremental progress.
#   - `.stream(...)` → generator of StreamChunk — for agents that should
#     surface tokens to the TUI incrementally. Same HTTP shape; just
#     `stream: true` in the request body and SSE decoding on the way back.
from __future__ import annotations

import json
import os
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Iterator

try:
    import httpx  # type: ignore
except ImportError:  # pragma: no cover — runtime requires httpx; tests inject a stub
    httpx = None  # type: ignore

from . import Response


# ---------------------------------------------------------- registry
#
# {(prefix, base_url, auth, env_var, default_model, streaming)}
# Mirrored from docs/frontend/providers.py — keep in sync.
# (We don't import from the frontend to avoid a runtime → frontend
# dependency. A pilot verifies the two stay aligned.)
@dataclass(frozen=True)
class _Spec:
    name: str              # provider id (lowercase, matches the prefix)
    base_url: str          # https://...
    env_var: str | None    # env var one would set without Labourious
    streaming: bool = True


_OPENAI_COMPAT_SPECS: dict[str, _Spec] = {
    # tier 1 — local
    "lm_studio":   _Spec("lm_studio",   "http://localhost:1234/v1",                None,                      streaming=False),
    "vllm":        _Spec("vllm",        "http://localhost:8000/v1",                None,                      streaming=True),
    "custom_openai": _Spec("custom_openai", "http://localhost:9999/v1",            "CUSTOM_API_KEY",          streaming=True),
    "omniroute":   _Spec("omniroute",   "http://localhost:8317/v1",                None,                      streaming=False),  # CLI; default to no-stream
    # tier 2 — free cloud
    "openrouter":  _Spec("openrouter",  "https://openrouter.ai/api/v1",            "OPENROUTER_API_KEY",      streaming=True),
    "mistral":     _Spec("mistral",     "https://api.mistral.ai/v1",               "MISTRAL_API_KEY",         streaming=True),
    "huggingface": _Spec("huggingface", "https://router.huggingface.co/v1",        "HF_TOKEN",                streaming=True),
    "cerebras":    _Spec("cerebras",    "https://api.cerebras.ai/v1",              "CEREBRAS_API_KEY",        streaming=True),
    "google_ai_studio": _Spec("google_ai_studio", "https://generativelanguage.googleapis.com/v1beta/openai",
                                                                "GOOGLE_API_KEY",            streaming=True),
    # tier 3 — paid
    "openai":      _Spec("openai",      "https://api.openai.com/v1",               "OPENAI_API_KEY",          streaming=True),
    "grok":        _Spec("grok",        "https://api.x.ai/v1",                     "XAI_API_KEY",             streaming=True),
    # tier 4 — specialty
    "perplexity":  _Spec("perplexity",  "https://api.perplexity.ai",               "PPLX_API_KEY",            streaming=True),
    "fireworks":   _Spec("fireworks",   "https://api.fireworks.ai/inference/v1",   "FIREWORKS_API_KEY",       streaming=True),
    "together":    _Spec("together",    "https://api.together.xyz/v1",             "TOGETHER_API_KEY",        streaming=True),
    "deepseek":    _Spec("deepseek",    "https://api.deepseek.com/v1",             "DEEPSEEK_API_KEY",        streaming=True),
}


@dataclass(frozen=True)
class ProviderNotSupported(Exception):
    """Raised when a model prefix isn't in the OpenAI-compat registry."""

    prefix: str
    suggestion: str

    def __str__(self) -> str:
        return (
            f"Provider '{self.prefix}' is not OpenAI-compat. "
            f"{self.suggestion}"
        )


@dataclass(frozen=True)
class AuthMissing(Exception):
    provider: str

    def __str__(self) -> str:
        return (
            f"No API key for '{self.provider}'. "
            f"Add one in Settings → Providers, or set "
            f"{self.provider.upper()}_API_KEY in your environment."
        )


@dataclass(frozen=True)
class AdapterHTTPError(Exception):
    provider: str
    status: int
    body: str

    def __str__(self) -> str:
        return f"{self.provider} HTTP {self.status}: {self.body[:200]}"


# ---------------------------------------------------------- keychain helpers
def _resolve_key(provider_name: str, env_var: str | None) -> str | None:
    """Auth precedence: keys_storage → env → legacy OPENAI_COMPAT_API_KEY."""
    try:
        from frontend.keys_storage import get_key  # type: ignore
        k = get_key(provider_name)
        if k:
            return k
    except Exception:
        # Runtime may be running without the frontend (CLI on a headless box).
        pass
    if env_var:
        k = os.environ.get(env_var)
        if k:
            return k
    return os.environ.get("OPENAI_COMPAT_API_KEY")


# ---------------------------------------------------------- request body
def _build_body(messages: list[dict], system: str, options: dict, *, stream: bool) -> dict[str, Any]:
    full_messages = [{"role": "system", "content": system}] + list(messages)
    body: dict[str, Any] = {
        "model": "",                              # patched in caller
        "messages": full_messages,
        "temperature": options.get("temperature", 0.2),
        "max_tokens": options.get("max_tokens", 4096),
    }
    if stream:
        body["stream"] = True
    return body


# ---------------------------------------------------------- usage + cost
def _parse_usage(payload: dict[str, Any]) -> tuple[int, int]:
    u = payload.get("usage", {}) or {}
    return int(u.get("prompt_tokens", 0) or 0), int(u.get("completion_tokens", 0) or 0)


def _parse_text_non_stream(payload: dict[str, Any]) -> str:
    try:
        return (payload["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError):
        return ""


_COST_OVERRIDE_IN = "OPENAI_COMPAT_COST_PER_1K_IN"
_COST_OVERRIDE_OUT = "OPENAI_COMPAT_COST_PER_1K_OUT"


def _cost(in_tok: int, out_tok: int) -> float:
    cin = float(os.environ.get(_COST_OVERRIDE_IN, 0) or 0)
    cout = float(os.environ.get(_COST_OVERRIDE_OUT, 0) or 0)
    return (in_tok / 1000.0) * cin + (out_tok / 1000.0) * cout


# ---------------------------------------------------------- StreamChunk
@dataclass
class StreamChunk:
    delta: str = ""
    finish_reason: str | None = None
    usage: dict[str, int] | None = None       # set only on the final chunk
    raw: dict[str, Any] | None = field(default=None, repr=False)


# ---------------------------------------------------------- SSE helpers
def _iter_sse_events(response: httpx.Response) -> Iterator[dict[str, Any]]:
    """Yield decoded JSON objects from a `text/event-stream` response.

    Lines look like:
        data: {"choices":[{"delta":{"content":"hi"}}]}
        data: {"choices":[{"delta":{},"finish_reason":"stop"}]}
        data: [DONE]
        \\n
    Empty lines are event separators. We treat the raw assistant text as
    the only thing we care about — usage (if any) comes in a trailing
    chunk that lacks a `choices` array.
    """
    for line in response.iter_lines():
        if not line:
            continue
        # Event-stream framing is "data: <...>" (and optional "event:" / "id:" /
        # "retry:" — we ignore those for /v1/chat/completions usage).
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            if payload == "[DONE]":
                return
            try:
                yield json.loads(payload)
            except json.JSONDecodeError:
                # Malformed frame — skip; the next frame will carry the tokens.
                continue


# ---------------------------------------------------------- adapter
@dataclass
class OpenAICompatAdapter:
    model: str              # "openai/gpt-4o" / "groq/llama-3.3" / "gpt-4o" etc.
    base_url: str | None = None       # override (used by tests)
    api_key: str | None = None        # override (used by tests)
    transport: Any = None             # httpx.MockTransport in tests

    def __post_init__(self):
        if httpx is None:
            raise RuntimeError(
                "httpx is required for OpenAICompatAdapter. "
                "Install with: pip install httpx httpx_sse"
            )
        self.provider, self._model_only = self._split_prefix(self.model)
        self.spec = _OPENAI_COMPAT_SPECS.get(self.provider)
        if self.spec is None:
            raise ProviderNotSupported(
                prefix=self.provider,
                suggestion=(
                    "Use Anthropic, Ollama, or Groq adapters for those providers. "
                    "OpenAI-compat supports: " + ", ".join(sorted(_OPENAI_COMPAT_SPECS))
                ),
            )
        self.base_url = self.base_url or self.spec.base_url
        # Auth resolution: explicit override → keychain → env → legacy fallback.
        if self.api_key is None:
            self.api_key = _resolve_key(self.spec.name, self.spec.env_var)
        if not self.api_key:
            raise AuthMissing(provider=self.spec.name)

    # --------------------------------------------------------------- call
    def call(self, messages: list[dict], system: str, options: dict | None = None) -> Response:
        options = options or {}
        body = _build_body(messages, system, options, stream=False)
        body["model"] = self._model_only
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        try:
            with httpx.Client(timeout=120, transport=self.transport) as client:
                r = client.post(f"{self.base_url}/chat/completions", json=body, headers=headers)
        except httpx.RequestError as exc:
            raise AdapterHTTPError(provider=self.spec.name, status=0,
                                   body=f"connection error: {exc}") from exc
        if r.status_code >= 400:
            raise AdapterHTTPError(provider=self.spec.name, status=r.status_code, body=r.text)
        try:
            payload = r.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{self.spec.name}: malformed JSON response: {exc}") from exc
        text = _parse_text_non_stream(payload)
        in_tok, out_tok = _parse_usage(payload)
        return Response(
            text=text,
            in_tokens=in_tok,
            out_tokens=out_tok,
            cache_hit_tokens=0,
            cost_usd_estimate=_cost(in_tok, out_tok),
            raw=payload,
        )

    # --------------------------------------------------------------- stream
    def stream(self, messages: list[dict], system: str, options: dict | None = None) -> Iterator[StreamChunk]:
        """Yield text deltas, terminating with one final chunk whose `usage` is set."""
        options = options or {}
        body = _build_body(messages, system, options, stream=True)
        body["model"] = self._model_only
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
        }
        try:
            with httpx.Client(timeout=120, transport=self.transport) as client:
                with client.stream("POST",
                                   f"{self.base_url}/chat/completions",
                                   json=body, headers=headers) as r:
                    if r.status_code >= 400:
                        raise AdapterHTTPError(provider=self.spec.name,
                                               status=r.status_code,
                                               body=r.read().decode("utf-8", "replace"))
                    text = ""
                    last_usage: tuple[int, int] = (0, 0)
                    last_finish: str | None = None
                    for event in _iter_sse_events(r):
                        # Each event is one `data:` frame — usually a single
                        # choice with a `delta.content` slice.
                        try:
                            chunks = event.get("choices", [])
                        except AttributeError:
                            chunks = []
                        if chunks:
                            delta = (chunks[0].get("delta") or {}).get("content") or ""
                            finish = chunks[0].get("finish_reason")
                            if delta:
                                text += delta
                                yield StreamChunk(delta=delta, finish_reason=finish)
                            elif finish:
                                last_finish = finish
                        # Some OpenRouter / DeepSeek responses append a
                        # trailing frame with no `choices` but only `usage`.
                        if "usage" in event and event["usage"]:
                            last_usage = (
                                int(event["usage"].get("prompt_tokens", 0) or 0),
                                int(event["usage"].get("completion_tokens", 0) or 0),
                            )
                    # EOT: yield one final chunk carrying finish + usage.
                    in_tok, out_tok = last_usage
                    yield StreamChunk(
                        delta="",
                        finish_reason=last_finish or "stop",
                        usage={"prompt_tokens": in_tok,
                               "completion_tokens": out_tok,
                               "cost_usd_estimate": _cost(in_tok, out_tok)},
                    )
        except httpx.RequestError as exc:
            raise AdapterHTTPError(provider=self.spec.name, status=0,
                                   body=f"connection error: {exc}") from exc

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _split_prefix(model: str) -> tuple[str, str]:
        if "/" in model:
            prefix, rest = model.split("/", 1)
            return prefix.lower(), rest
        # No prefix → default to "openai/".
        return "openai", model

    def route_summary(self) -> dict[str, Any]:
        """Useful for diagnostics + the runtime's debug log."""
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "model_id": self._model_only,
            "streaming_supported": self.spec.streaming if self.spec else False,
        }


# ---------------------------------------------------------- AdapterError export
# (the dispatcher wants a single symbol to look for; we expose our three.)
AdapterError = (ProviderNotSupported, AuthMissing, AdapterHTTPError)
