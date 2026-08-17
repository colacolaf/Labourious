# adapters/groq.py — Groq Inference API. Speculative decoding; very fast. Free tier available.
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from dataclasses import dataclass

from . import Response


@dataclass
class GroqAdapter:
    model: str  # "groq/llama-3.3-70b-versatile" → "llama-3.3-70b-versatile"
    base_url: str = "https://api.groq.com/openai/v1"

    def __post_init__(self):
        if "/" in self.model:
            self.model = self.model.split("/", 1)[1]
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY not set")

    def call(self, messages: list[dict], system: str, options: dict | None = None) -> Response:
        options = options or {}
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
            raise RuntimeError(f"Groq {e.code}: {e.read().decode('utf-8', errors='replace')}") from e

        text = (payload.get("choices", [{}])[0].get("message", {}) or {}).get("content", "").strip()
        usage = payload.get("usage", {}) or {}
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        # Groq free tier: $0 cost in our model.
        cost = 0.0
        return Response(text=text, in_tokens=in_tok, out_tokens=out_tok,
                        cache_hit_tokens=0, cost_usd_estimate=cost, raw=payload)
