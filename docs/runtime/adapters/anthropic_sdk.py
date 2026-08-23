"""
adapters/anthropic_sdk.py — Anthropic Python SDK adapter (optional).

Wraps the official ``anthropic`` SDK's streaming messages API.
Installed via ``pip install labourious[anthropic-sdk]`` or ``[all]``.

Imports the SDK eagerly (during __init__) so ``get_adapter()`` can
fall back gracefully when it's not installed.
"""

from __future__ import annotations

import os
from typing import Any, Iterator

from . import Response
from ._streaming import StreamChunk, AuthMissing, AdapterHTTPError


_COSTS_PER_MILLION: dict[str, tuple[float, float]] = {
    "claude-opus-4": (15.00, 75.00), "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-4": (1.00, 5.00), "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00), "claude-3-opus": (15.00, 75.00),
    "claude-3-sonnet": (3.00, 15.00), "claude-3-haiku": (0.25, 1.25),
}
_DEFAULT = (3.00, 15.00)


def _cost(model: str, in_t: int, out_t: int) -> float:
    n = model.lower()
    m = [s for s in _COSTS_PER_MILLION if n.startswith(s)]
    ir, ora = _COSTS_PER_MILLION[max(m, key=len)] if m else _DEFAULT
    return (in_t / 1e6) * ir + (out_t / 1e6) * ora


class AnthropicSDKAdapter:
    def __init__(self, model: str):
        self.model = model
        import anthropic  # type: ignore
        self.sdk = anthropic
        self._client: Any = None

    def _client_or_create(self) -> Any:
        if self._client is not None:
            return self._client
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            try:
                from frontend.keys_storage import get_key
                key = get_key("anthropic")
            except Exception:
                pass
        if not key:
            raise AuthMissing(provider="anthropic")
        model_id = self.model.split("/", 1)[1] if "/" in self.model else self.model
        self._client = self.sdk.Anthropic(api_key=key)
        return self._client

    def call(self, messages, system, options) -> Response:
        c = self._client_or_create()
        model_id = self.model.split("/", 1)[1] if "/" in self.model else self.model
        kw = {"model": model_id, "max_tokens": 4096, "messages": messages,
              "temperature": options.get("temperature", 0.2)}
        if system:
            kw["system"] = system
        try:
            msg = c.messages.create(**kw)
        except Exception as e:
            if "auth" in str(e).lower() or "401" in str(e):
                raise AuthMissing(provider="anthropic")
            status = getattr(getattr(e, "response", None), "status_code", 500)
            raise AdapterHTTPError(provider="anthropic", status=status, body=str(e)[:300])

        t = ""
        for b in msg.content:
            if getattr(b, "type", "") == "text":
                t += getattr(b, "text", "")
        return Response(text=t,
                        in_tokens=getattr(msg.usage, "input_tokens", 0) if hasattr(msg, "usage") else 0,
                        out_tokens=getattr(msg.usage, "output_tokens", 0) if hasattr(msg, "usage") else 0,
                        cost_usd_estimate=_cost(self.model,
                                                getattr(msg.usage, "input_tokens", 0) if hasattr(msg, "usage") else 0,
                                                getattr(msg.usage, "output_tokens", 0) if hasattr(msg, "usage") else 0),
                        raw=msg)

    def stream(self, messages, system, options) -> Iterator[StreamChunk]:
        c = self._client_or_create()
        model_id = self.model.split("/", 1)[1] if "/" in self.model else self.model
        kw = {"model": model_id, "max_tokens": 4096, "messages": messages,
              "temperature": options.get("temperature", 0.2)}
        if system:
            kw["system"] = system
        try:
            with c.messages.stream(**kw) as s:
                in_t = out_t = 0
                for ev in s:
                    if ev.type == "content_block_delta":
                        d = getattr(ev.delta, "text", "")
                        if d:
                            yield StreamChunk(delta=d)
                    elif ev.type == "message_delta":
                        u = getattr(ev, "usage", None)
                        if u:
                            in_t = getattr(u, "input_tokens", 0)
                            out_t = getattr(u, "output_tokens", 0)
                    elif ev.type == "message_stop":
                        yield StreamChunk(finish_reason="end_turn",
                                          usage={"prompt_tokens": in_t, "completion_tokens": out_t,
                                                 "cost_usd_estimate": _cost(self.model, in_t, out_t)})
        except Exception as e:
            msg_s = str(e).lower()
            if "auth" in msg_s or "401" in msg_s:
                raise AuthMissing(provider="anthropic")
            status = getattr(getattr(e, "response", None), "status_code", 500)
            raise AdapterHTTPError(provider="anthropic", status=status, body=str(e)[:300])