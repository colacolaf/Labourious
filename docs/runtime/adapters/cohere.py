# adapters/cohere.py — Cohere v2 Chat API adapter.
#
# Spec: https://docs.cohere.com/reference/chat (v2)
# Endpoint:  POST https://api.cohere.com/v2/chat
# Auth:      Authorization: Bearer <COHERE_API_KEY> (or GOOGLE_API_KEY backwards-compat)
# Stream framing: identical to Anthropic — each event has BOTH an `event:`
#                and a `data:` line, separated by a blank line.
#
# Event types we care about:
#   message-start    → record the response id (debugging only)
#   content-start    → confirm the text type
#   content-delta    → emit StreamChunk(delta=delta.message.content.text)
#   content-end      → close out the text block
#   message-end      → captures finish_reason + usage (billed_units.input_tokens,
#                       billed_units.output_tokens)
#   stream-end       → terminator
#
# Cost model — current Cohere Command family (per million tokens):
#   command-r-plus:    $2.50 in / $10.00 out
#   command-r:         $0.50 in / $1.50 out
#   command-light:     $0.30 in / $0.60 out
#   c4ai-command-r-plus / aya-* : same as their non-equivalent
#   unknown            → defaults to command-r-plus rates
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Iterator

try:
    import httpx  # type: ignore
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

from . import Response
from ._streaming import StreamChunk, AuthMissing, AdapterHTTPError


# ---------------------------------------------------------- cost table
_COSTS_PER_MILLION: dict[str, tuple[float, float]] = {
    "command-r-plus":   (2.50, 10.00),
    "command-r":        (0.50,  1.50),
    "command":          (0.30,  0.60),     # command-light (or older)
    "command-light":    (0.30,  0.60),
    "command-nightly":  (0.30,  0.60),
    "c4ai-command-r-plus": (2.50, 10.00),
    "aya-expanse":      (0.30,  0.60),
}
_DEFAULT_COST: tuple[float, float] = (2.50, 10.00)  # command-r-plus


def _cost_for(model: str, in_tok: int, out_tok: int) -> float:
    """Longest-prefix match against `_COSTS_PER_MILLION`."""
    needle = model.lower()
    candidates = [slug for slug in _COSTS_PER_MILLION if needle.startswith(slug)]
    if candidates:
        in_rate, out_rate = _COSTS_PER_MILLION[max(candidates, key=len)]
    else:
        in_rate, out_rate = _DEFAULT_COST
    return (in_tok / 1_000_000.0) * in_rate + (out_tok / 1_000_000.0) * out_rate


# ---------------------------------------------------------- auth
def _resolve_key(provider_name: str = "cohere") -> str | None:
    """Auth precedence: keychain → env (with two vars to support aliases)."""
    try:
        from frontend.keys_storage import get_key  # type: ignore
        k = get_key(provider_name)
        if k:
            return k
    except Exception:
        pass
    for env in ("COHERE_API_KEY", "CO_API_KEY"):
        v = os.environ.get(env)
        if v:
            return v
    return None


# ---------------------------------------------------------- request body
def _build_messages(system: str, messages: list[dict]) -> list[dict]:
    """Cohere v2 keeps the system message as the first item with role=system."""
    out = [{"role": "system", "content": system}] if system else []
    out.extend(list(messages))
    return out


def _build_body(messages: list[dict], system: str, options: dict, *, stream: bool) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": "",
        "messages": _build_messages(system, messages),
        "max_tokens": options.get("max_tokens", 4096),
        "temperature": options.get("temperature", 0.2),
    }
    if stream:
        body["stream"] = True
    return body


# ---------------------------------------------------------- adapter
@dataclass
class CohereAdapter:
    model: str                      # "cohere/command-r-plus" or "command-r-plus"
    base_url: str = "https://api.cohere.com/v2"
    api_key: str | None = None      # explicit (tests) → keychain → env
    transport: Any = None           # httpx.MockTransport in tests

    def __post_init__(self):
        if httpx is None:
            raise RuntimeError(
                "httpx is required for CohereAdapter. "
                "Install with: pip install httpx httpx_sse"
            )
        # Strip "<provider>/" prefix.
        if "/" in self.model:
            self.model = self.model.split("/", 1)[1]
        if self.api_key is None:
            self.api_key = _resolve_key("cohere")
        if not self.api_key:
            raise AuthMissing(provider="cohere")

    # --------------------------------------------------------------- call
    def call(self, messages: list[dict], system: str, options: dict | None = None) -> Response:
        options = options or {}
        body = _build_body(messages, system, options, stream=False)
        body["model"] = self.model
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",   # explicit for non-stream
        }
        try:
            with httpx.Client(timeout=120, transport=self.transport) as client:
                r = client.post(f"{self.base_url}/chat", json=body, headers=headers)
        except httpx.RequestError as exc:
            raise AdapterHTTPError(provider="cohere", status=0,
                                   body=f"connection error: {exc}") from exc
        if r.status_code >= 400:
            raise AdapterHTTPError(provider="cohere", status=r.status_code, body=r.text)
        try:
            payload = r.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"cohere: malformed JSON response: {exc}") from exc

        # Non-stream response: message.content[].text — concatenate text blocks.
        msg = payload.get("message") or {}
        text = "\n".join(
            p.get("text", "") for p in msg.get("content", []) if p.get("type") == "text"
        ).strip()
        usage = (payload.get("usage") or {}).get("billed_units") or {}
        in_tok = int(usage.get("input_tokens", 0) or 0)
        out_tok = int(usage.get("output_tokens", 0) or 0)
        cost = _cost_for(self.model, in_tok, out_tok)
        return Response(
            text=text, in_tokens=in_tok, out_tokens=out_tok,
            cache_hit_tokens=0, cost_usd_estimate=cost, raw=payload,
        )

    # --------------------------------------------------------------- stream
    def stream(self, messages: list[dict], system: str, options: dict | None = None) -> Iterator[StreamChunk]:
        """Yield text deltas from Cohere's `/v2/chat` SSE channel.

        Cohere's framing is identical to Anthropic: each event has BOTH
        an `event:` line and a `data:` line, separated by blanks. The
        text fragment lives in `data: {"delta": {"message": {"content":
        {"text": "..."}}}}` inside `content-delta` events.
        """
        options = options or {}
        body = _build_body(messages, system, options, stream=True)
        body["model"] = self.model
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
        }
        in_tok_total = 0
        out_tok_total = 0
        stop_reason: str | None = None
        try:
            with httpx.Client(timeout=120, transport=self.transport) as client:
                with client.stream("POST",
                                   f"{self.base_url}/chat",
                                   json=body, headers=headers) as r:
                    if r.status_code >= 400:
                        raise AdapterHTTPError(
                            provider="cohere", status=r.status_code,
                            body=r.read().decode("utf-8", "replace"),
                        )
                    event_type: str | None = None
                    event_data: list[str] = []
                    for raw_line in r.iter_lines():
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
                            if ev_type == "content-delta":
                                # Path: delta.message.content.text
                                try:
                                    text_piece = (
                                        payload["delta"]["message"]["content"]["text"]
                                    )
                                    if text_piece:
                                        yield StreamChunk(delta=text_piece,
                                                           raw=payload)
                                except (KeyError, TypeError):
                                    pass
                            elif ev_type == "message-end":
                                blk = payload.get("delta") or {}
                                if blk.get("finish_reason"):
                                    stop_reason = blk["finish_reason"]
                                usage = blk.get("usage") or {}
                                billed = usage.get("billed_units") or {}
                                if billed:
                                    in_tok_total = int(billed.get("input_tokens",
                                                                    in_tok_total) or 0)
                                    out_tok_total = int(billed.get("output_tokens",
                                                                     out_tok_total) or 0)
                            # Other events: message-start / content-start /
                            # content-end / stream-end carry no extra text or
                            # final usage we don't already have.
                            continue
                        if raw_line.startswith("event:"):
                            event_type = raw_line[len("event:"):].strip()
                        elif raw_line.startswith("data:"):
                            event_data.append(raw_line[len("data:"):].lstrip())
                    cost = _cost_for(self.model, in_tok_total, out_tok_total)
                    yield StreamChunk(
                        delta="",
                        finish_reason=stop_reason or "COMPLETE",
                        usage={
                            "prompt_tokens": in_tok_total,
                            "completion_tokens": out_tok_total,
                            "cost_usd_estimate": cost,
                        },
                    )
        except httpx.RequestError as exc:
            raise AdapterHTTPError(provider="cohere", status=0,
                                   body=f"connection error: {exc}") from exc

    # --------------------------------------------------------------- helpers
    def route_summary(self) -> dict[str, Any]:
        return {
            "provider": "cohere",
            "base_url": self.base_url,
            "model_id": self.model,
            "streaming_supported": True,
        }


__all__ = ["CohereAdapter", "_cost_for"]
