# adapters/anthropic.py — Anthropic Messages API adapter.
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any

from . import Response


@dataclass
class AnthropicAdapter:
    model: str
    base_url: str = "https://api.anthropic.com/v1"
    api_key: str | None = None  # read from env if not set

    def __post_init__(self):
        # Strip provider prefix; "anthropic/claude-sonnet-4-5" → "claude-sonnet-4-5"
        if "/" in self.model:
            self.model = self.model.split("/", 1)[1]
        self.api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

    def call(self, messages: list[dict], system: str, options: dict | None = None) -> Response:
        options = options or {}
        body = {
            "model": self.model,
            "max_tokens": options.get("max_tokens", 4096),
            "temperature": options.get("temperature", 0.2),
            "system": system,
            "messages": messages,
        }
        req = urllib.request.Request(
            url=f"{self.base_url}/messages",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Anthropic {e.code}: {e.read().decode('utf-8', errors='replace')}") from e

        # Anthropic returns content blocks; first text block is the answer.
        text_blocks = [b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text"]
        text = "\n".join(text_blocks).strip()
        usage = payload.get("usage", {})
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        cache = usage.get("cache_read_input_tokens", 0)
        # Cost estimate (Sonnet 4.5 prices subject to change; rough ballpark)
        cost = 0.000003 * in_tok + 0.000015 * out_tok
        return Response(text=text, in_tokens=in_tok, out_tokens=out_tok,
                        cache_hit_tokens=cache, cost_usd_estimate=cost, raw=payload)
