# adapters/openai_compat.py — Any OpenAI-compatible API.
#
# Works for: OpenAI itself, OpenRouter (including free routes), Together AI,
# Anyscale, Fireworks, and any local OpenAI-compatible server (LM Studio, llama.cpp server, etc.).
#
# Configure via env: OPENAI_COMPAT_BASE_URL, OPENAI_COMPAT_API_KEY, OPENAI_COMPAT_DEFAULT_MODEL.
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from dataclasses import dataclass

from . import Response


@dataclass
class OpenAICompatAdapter:
    model: str  # e.g. "openrouter/meta-llama/llama-3.3-70b:free", "openai/gpt-4o"
    base_url: str = "https://api.openai.com/v1"

    def __post_init__(self):
        # The "openai/" prefix is special: real OpenAI. Everyone else, also accept a
        # "provider/" prefix that overrides base_url.
        if "/" in self.model:
            prefix, after = self.model.split("/", 1)
            if prefix == "openai":
                self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
                self.api_key = os.environ.get("OPENAI_API_KEY")
            elif prefix == "openrouter":
                self.base_url = "https://openrouter.ai/api/v1"
                self.api_key = os.environ.get("OPENROUTER_API_KEY")
            elif prefix == "together":
                self.base_url = "https://api.together.xyz/v1"
                self.api_key = os.environ.get("TOGETHER_API_KEY")
            elif prefix == "llamacpp":
                self.base_url = os.environ.get("LLAMACPP_BASE_URL", "http://localhost:8080/v1")
                self.api_key = "no-key"
            else:
                # Unknown provider prefix; assume OpenAI-compat with env-configured base
                self.base_url = os.environ.get(f"{prefix.upper()}_BASE_URL", self.base_url)
                self.api_key = os.environ.get(f"{prefix.upper()}_API_KEY")
        if not getattr(self, "api_key", None) or self.api_key == "no-key":
            if not getattr(self, "api_key", None):
                # Anthropic prefix was wrong; final fallback
                self.api_key = os.environ.get("OPENAI_COMPAT_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError(f"API key not configured for model: {self.model}")

    def call(self, messages: list[dict], system: str, options: dict | None = None) -> Response:
        options = options or {}
        # OpenAI's chat completions: combine system into the user/assistant msgs.
        full_messages = [{"role": "system", "content": system}] + list(messages)
        body = {
            "model": self.model,
            "messages": full_messages,
            "temperature": options.get("temperature", 0.2),
            "max_tokens": options.get("max_tokens", 4096),
        }
        req = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"OpenAI-compat {self.base_url} {e.code}: {e.read().decode('utf-8', errors='replace')}"
            ) from e
        text = (payload.get("choices", [{}])[0].get("message", {}) or {}).get("content", "").strip()
        usage = payload.get("usage", {}) or {}
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        # Cost: track as $0 by default for free-tier; allow env override
        cost_per_1k_in = float(os.environ.get("OPENAI_COMPAT_COST_PER_1K_IN", 0))
        cost_per_1k_out = float(os.environ.get("OPENAI_COMPAT_COST_PER_1K_OUT", 0))
        cost = (in_tok / 1000.0) * cost_per_1k_in + (out_tok / 1000.0) * cost_per_1k_out
        return Response(text=text, in_tokens=in_tok, out_tokens=out_tok,
                        cache_hit_tokens=0, cost_usd_estimate=cost, raw=payload)
