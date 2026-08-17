# adapters/ollama.py — Ollama (local LLM) adapter. No auth, defaults to localhost:11434.
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from dataclasses import dataclass

from . import Response


@dataclass
class OllamaAdapter:
    model: str  # "ollama/llama3.3:70b" → underlying "llama3.3:70b"
    base_url: str = "http://localhost:11434"

    def __post_init__(self):
        if "/" in self.model:
            self.model = self.model.split("/", 1)[1]
        self.base_url = os.environ.get("OLLAMA_BASE_URL", self.base_url)

    def call(self, messages: list[dict], system: str, options: dict | None = None) -> Response:
        options = options or {}
        # Ollama chat endpoint: role='system' is part of the same messages list with role 'system'.
        # Many Ollama models understand it.
        full_messages = [{"role": "system", "content": system}] + list(messages)
        body = {
            "model": self.model,
            "messages": full_messages,
            "stream": False,
            "options": {
                "temperature": options.get("temperature", 0.2),
                "num_predict": options.get("max_tokens", 4096),
            },
        }
        req = urllib.request.Request(
            url=f"{self.base_url}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Ollama {e.code}: {e.read().decode('utf-8', errors='replace')}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama not reachable at {self.base_url}: {e}") from e
        text = (payload.get("message", {}) or {}).get("content", "")
        # Ollama's token counts are often `prompt_eval_count` and `eval_count`.
        in_tok = payload.get("prompt_eval_count", 0)
        out_tok = payload.get("eval_count", 0)
        # Local = free
        cost = 0.0
        return Response(text=text.strip(), in_tokens=in_tok, out_tokens=out_tok,
                        cache_hit_tokens=0, cost_usd_estimate=cost, raw=payload)
