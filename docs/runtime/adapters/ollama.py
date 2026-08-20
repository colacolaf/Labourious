# adapters/ollama.py — Ollama (local LLM) adapter. No auth, defaults to localhost:11434.
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Iterator

from . import Response
from ._streaming import StreamChunk


@dataclass
class OllamaAdapter:
    model: str  # "ollama/llama3.3:70b" → underlying "llama3.3:70b"
    base_url: str = "http://localhost:11434"
    request_timeout_s: int = 240

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
            with urllib.request.urlopen(req, timeout=self.request_timeout_s) as r:
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

    # --------------------------------------------------------------- stream
    def stream(self, messages: list[dict], system: str,
               options: dict | None = None) -> Iterator[StreamChunk]:
        """Yield `StreamChunk`s from Ollama's `/api/chat` SSE-like channel.

        Ollama streams as **newline-delimited JSON** when `stream: true`.
        Each line is a JSON object with:
          ``{ "model": "...", "created_at": "...", "message": {"role":"assistant","content":"delta"}, "done": false }``
        Followed by a final line with ``"done": true`` plus
        ``prompt_eval_count`` + ``eval_count`` (when supported by the
        model). We yield ``StreamChunk(delta=…)`` on each non-final line
        and a final ``StreamChunk`` with ``finish_reason="stop"`` and
        ``usage={"prompt_tokens":..., "completion_tokens":...,
        "cost_usd_estimate": 0.0}`` so the runtime sees the same shape
        across providers.
        """
        options = options or {}
        full_messages = [{"role": "system", "content": system}] + list(messages)
        body = {
            "model": self.model,
            "messages": full_messages,
            "stream": True,
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
            resp = urllib.request.urlopen(req, timeout=self.request_timeout_s)
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"Ollama {e.code}: "
                f"{e.read().decode('utf-8', errors='replace')}"
            ) from e
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Ollama not reachable at {self.base_url}: {e}"
            ) from e

        in_tok_total = 0
        out_tok_total = 0
        try:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                done = payload.get("done", False)
                msg = payload.get("message") or {}
                delta_text = msg.get("content") or ""
                # Emit delta once per chunk that has text; the final
                # line MAY have both `done: true` and a non-empty
                # `content` (Ollama collapses the last delta + done
                # into one line for some models — we honour that).
                if delta_text:
                    yield StreamChunk(delta=delta_text, raw=payload)
                if done:
                    # Final line. Ollama publishes token counts here for
                    # compatible models. Older versions omit these.
                    in_tok_total = int(payload.get(
                        "prompt_eval_count", 0) or 0)
                    out_tok_total = int(payload.get(
                        "eval_count", 0) or 0)
                    break
        finally:
            try:
                resp.close()
            except Exception:
                pass

        yield StreamChunk(
            delta="",
            finish_reason="stop",
            usage={
                "prompt_tokens": in_tok_total,
                "completion_tokens": out_tok_total,
                "cost_usd_estimate": 0.0,   # local LLM = free
            },
            raw={"final": True, "model": self.model,
                 "in_tokens": in_tok_total,
                 "out_tokens": out_tok_total},
        )
