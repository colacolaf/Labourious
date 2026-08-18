# adapters/anthropic.py — Anthropic Messages API adapter.
#
# Spec: https://docs.anthropic.com/claude/reference/messages-streaming
#
# Two entry points:
#   - .call(...)  → single Response (text + usage + cost). Drop-in replacement
#                   for the previous urllib-based sync adapter.
#   - .stream(...) → generator of StreamChunk so the TUI can render tokens
#                     incrementally. SSE event types:
#                       message_start → content_block_start →
#                       [content_block_delta]* → content_block_stop →
#                       message_delta (carries stop_reason + usage) → message_stop
#
# Auth precedence:
#   1. explicit `api_key` arg (used by tests)
#   2. OS keychain via `frontend.keys_storage.get_key("anthropic")`
#   3. ANTHROPIC_API_KEY env var (legacy)
#
# Cost model: per-model rate table (USD per 1M tokens). Fails closed to
# the Sonnet 4.5 rate if a model isn't recognised — better to under-bill
# than silently bill $0 for a future model we haven't catalogued.
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Iterator

try:
    import httpx  # type: ignore
except ImportError:  # pragma: no cover — runtime requires httpx
    httpx = None  # type: ignore

from . import Response
from ._streaming import StreamChunk, AuthMissing, AdapterHTTPError, merge_usage


# ---------------------------------------------------------- cost table
# (USD per 1M tokens; in/out). Falls back to Sonnet 4.5 for unknown.
_COSTS_PER_MILLION: dict[str, tuple[float, float]] = {
    # current Claude 4.x family
    "claude-opus-4":       (15.00, 75.00),
    "claude-sonnet-4":     (3.00, 15.00),
    "claude-haiku-4":      (1.00,  5.00),
    # legacy 3.x family
    "claude-3-5-sonnet":   (3.00, 15.00),
    "claude-3-5-haiku":    (0.80,  4.00),
    "claude-3-opus":       (15.00, 75.00),
    "claude-3-sonnet":     (3.00, 15.00),
    "claude-3-haiku":      (0.25,  1.25),
}
_DEFAULT_COST: tuple[float, float] = (3.00, 15.00)        # Sonnet 4.5


def _cost_for(model: str, in_tok: int, out_tok: int) -> float:
    needle = model.lower()
    # Longest-prefix match so "claude-3-5-sonnet-20241022" picks the
    # 3-5-sonnet row ahead of the bare 3-sonnet row.
    matches = [rate for slug, rate in _COSTS_PER_MILLION.items() if needle.startswith(slug)]
    in_rate, out_rate = max(matches, key=lambda r: -len(str(r))) if matches else _DEFAULT_COST
    # Re-pick by actual slug length for clarity:
    if matches:
        longest_slug = max(
            (slug for slug in _COSTS_PER_MILLION if needle.startswith(slug)),
            key=len,
        )
        in_rate, out_rate = _COSTS_PER_MILLION[longest_slug]
    return (in_tok / 1_000_000.0) * in_rate + (out_tok / 1_000_000.0) * out_rate


# ---------------------------------------------------------- auth
def _resolve_key() -> str | None:
    """Auth precedence: keychain → env."""
    try:
        from frontend.keys_storage import get_key  # type: ignore
        k = get_key("anthropic")
        if k:
            return k
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


# ---------------------------------------------------------- request body
def _build_body(messages: list[dict], system: str, options: dict, *, stream: bool) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": "",                                  # patched in caller
        "max_tokens": options.get("max_tokens", 4096),
        "temperature": options.get("temperature", 0.2),
        "system": system,
        "messages": list(messages),
    }
    if stream:
        body["stream"] = True
    return body


def _usage_to_response(usage: dict[str, int], model: str) -> tuple[int, int, float, int]:
    in_tok = int(usage.get("input_tokens", 0) or 0)
    out_tok = int(usage.get("output_tokens", 0) or 0)
    cache = int(usage.get("cache_read_input_tokens", 0) or 0)
    return in_tok, out_tok, _cost_for(model, in_tok, out_tok), cache


# ---------------------------------------------------------- adapter
@dataclass
class AnthropicAdapter:
    model: str                      # "anthropic/claude-sonnet-4-5" or "claude-3-5-sonnet"
    base_url: str = "https://api.anthropic.com/v1"
    api_key: str | None = None      # override (tests); else resolved via _resolve_key()
    transport: Any = None           # httpx.MockTransport in tests

    def __post_init__(self):
        if httpx is None:
            raise RuntimeError(
                "httpx is required for AnthropicAdapter. "
                "Install with: pip install httpx httpx_sse"
            )
        # Strip the "<provider>/" prefix if present.
        if "/" in self.model:
            self.model = self.model.split("/", 1)[1]
        if self.api_key is None:
            self.api_key = _resolve_key()
        if not self.api_key:
            raise AuthMissing(provider="anthropic")

    # --------------------------------------------------------------- call
    def call(self, messages: list[dict], system: str, options: dict | None = None) -> Response:
        options = options or {}
        body = _build_body(messages, system, options, stream=False)
        body["model"] = self.model
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        try:
            with httpx.Client(timeout=120, transport=self.transport) as client:
                r = client.post(f"{self.base_url}/messages", json=body, headers=headers)
        except httpx.RequestError as exc:
            raise AdapterHTTPError(provider="anthropic", status=0,
                                   body=f"connection error: {exc}") from exc
        if r.status_code >= 400:
            raise AdapterHTTPError(provider="anthropic", status=r.status_code, body=r.text)
        try:
            payload = r.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"anthropic: malformed JSON response: {exc}") from exc

        # Anthropic returns content blocks; first text blocks concatenated.
        text = "\n".join(
            b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text"
        ).strip()
        usage = payload.get("usage", {}) or {}
        in_tok, out_tok, cost, cache = _usage_to_response(usage, self.model)
        return Response(
            text=text, in_tokens=in_tok, out_tokens=out_tok,
            cache_hit_tokens=cache, cost_usd_estimate=cost, raw=payload,
        )

    # --------------------------------------------------------------- stream
    def stream(self, messages: list[dict], system: str, options: dict | None = None) -> Iterator[StreamChunk]:
        """Yield text deltas from Anthropic's `/v1/messages` SSE channel.

        Anthropic's framing differs from OpenAI's data-only SSE. Each
        event has BOTH an `event:` line (the type) AND a `data:` line
        (the JSON payload). SSE rules: events are separated by blank
        lines, the `event:` line is followed by `data:`.

        Event types we care about:
          message_start       → record initial usage (input_tokens)
          content_block_start → no payload useful to us; just confirm type=text
          content_block_delta → emit StreamChunk(delta=delta.text) on every text_delta
          content_block_stop  → close out the current text block
          message_delta       → carries stop_reason + final usage.output_tokens
          message_stop        → terminator
        """
        options = options or {}
        body = _build_body(messages, system, options, stream=True)
        body["model"] = self.model
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Accept": "text/event-stream",
        }
        in_tok_total = 0
        out_tok_total = 0
        stop_reason: str | None = None
        try:
            with httpx.Client(timeout=120, transport=self.transport) as client:
                with client.stream("POST",
                                   f"{self.base_url}/messages",
                                   json=body, headers=headers) as r:
                    if r.status_code >= 400:
                        raise AdapterHTTPError(
                            provider="anthropic", status=r.status_code,
                            body=r.read().decode("utf-8", "replace"),
                        )
                    cache_read = 0
                    event_type: str | None = None
                    event_data: list[str] = []
                    for raw_line in r.iter_lines():
                        # Anthropic frames a single event as:
                        #   event: <type>
                        #   data: <json>
                        #   <blank line>
                        if raw_line == "":
                            if event_type is None or not event_data:
                                event_type = None
                                event_data = []
                                continue
                            payload_str = "\n".join(event_data)
                            try:
                                payload = json.loads(payload_str)
                            except json.JSONDecodeError:
                                payload = None
                            ev_type = event_type
                            event_type = None
                            event_data = []
                            if payload is None:
                                continue
                            if ev_type == "content_block_delta":
                                try:
                                    blk = payload.get("delta", {})
                                    if blk.get("type") == "text_delta":
                                        text_delta = blk.get("text", "")
                                        if text_delta:
                                            yield StreamChunk(delta=text_delta,
                                                               raw=payload)
                                except AttributeError:
                                    pass
                            elif ev_type == "message_delta":
                                blk = payload.get("delta") or {}
                                if blk.get("stop_reason"):
                                    stop_reason = blk["stop_reason"]
                                usage = payload.get("usage") or {}
                                if usage:
                                    out_tok_total = int(usage.get("output_tokens",
                                                                   out_tok_total) or 0)
                            elif ev_type == "message_start":
                                m = payload.get("message") or {}
                                usage = m.get("usage") or {}
                                if usage:
                                    in_tok_total = int(usage.get("input_tokens", 0) or 0)
                                    out_tok_total = int(usage.get("output_tokens", 1) or 1)
                                    cache_read = int(usage.get("cache_read_input_tokens", 0) or 0)
                            else:
                                # message_stop / content_block_start / content_block_stop
                                # carry no extra text or final usage we already have.
                                pass
                            continue
                        if raw_line.startswith("event:"):
                            event_type = raw_line[len("event:"):].strip()
                        elif raw_line.startswith("data:"):
                            event_data.append(raw_line[len("data:"):].lstrip())
                        # else: ignore (id:/retry: framing is not used by Anthropic Messages)
                    # End-of-stream: emit the final chunk carrying usage.
                    cost = _cost_for(self.model, in_tok_total, out_tok_total)
                    yield StreamChunk(
                        delta="",
                        finish_reason=stop_reason or "end_turn",
                        usage={
                            "prompt_tokens": in_tok_total,
                            "completion_tokens": out_tok_total,
                            "cache_read_input_tokens": cache_read,
                            "cost_usd_estimate": cost,
                        },
                    )
        except httpx.RequestError as exc:
            raise AdapterHTTPError(provider="anthropic", status=0,
                                   body=f"connection error: {exc}") from exc

    # --------------------------------------------------------------- helpers
    def route_summary(self) -> dict[str, Any]:
        return {
            "provider": "anthropic",
            "base_url": self.base_url,
            "model_id": self.model,
            "streaming_supported": True,
        }


# Keep merge_usage importable from this module too for symmetry.
__all__ = ["AnthropicAdapter", "StreamChunk", "merge_usage"]
