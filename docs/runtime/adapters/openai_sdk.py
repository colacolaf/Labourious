"""
adapters/openai_sdk.py — OpenAI Python SDK adapter (optional).

Wraps the official ``openai`` SDK's chat.completions streaming API.
Installed via ``pip install labourious[openai-sdk]`` or ``[all]``.

Imports SDK eagerly (during __init__) so ``get_adapter()`` can fall
back gracefully.
"""

from __future__ import annotations

import os
from typing import Any, Iterator

from . import Response
from ._streaming import StreamChunk, AuthMissing, AdapterHTTPError


_COSTS: dict[str, tuple[float, float]] = {
    "gpt-4": (30, 60), "gpt-4o": (2.5, 10), "gpt-4o-mini": (0.15, 0.6),
    "gpt-3.5-turbo": (0.5, 1.5), "o1": (15, 60), "o1-mini": (1.1, 4.4),
    "o3": (15, 60), "o3-mini": (1.1, 4.4),
}
_DEFAULT = (2.5, 10)


def _cost(model: str, in_t: int, out_t: int) -> float:
    n = model.lower()
    m = [s for s in _COSTS if n.startswith(s)]
    ir, ora = _COSTS[max(m, key=len)] if m else _DEFAULT
    return (in_t / 1e6) * ir + (out_t / 1e6) * ora


class OpenAISDKAdapter:
    def __init__(self, model: str):
        self.model = model
        import openai  # type: ignore
        self.sdk = openai
        self._client: Any = None

    def _client_or_create(self) -> Any:
        if self._client is not None:
            return self._client
        prefix = self.model.split("/", 1)[0].lower()

        # Resolve base_url + api key
        from .openai_compat import _OPENAI_COMPAT_SPECS
        spec = _OPENAI_COMPAT_SPECS.get(prefix)
        base_url = None
        api_key = ""
        if spec:
            base_url = spec.base_url
            try:
                from frontend.keys_storage import get_key
                api_key = get_key(prefix) or os.environ.get(spec.env_var or "", "")
            except Exception:
                api_key = os.environ.get(spec.env_var or "", "")
        else:
            api_key = os.environ.get(f"{prefix.upper()}_API_KEY", "")
        kw = {"api_key": api_key if api_key else "sk-placeholder"}
        if base_url:
            kw["base_url"] = base_url
        self._client = self.sdk.OpenAI(**kw)
        return self._client

    def call(self, messages, system, options) -> Response:
        c = self._client_or_create()
        _, mid = self.model.split("/", 1) if "/" in self.model else ("openai", self.model)
        msgs = [{"role": "system", "content": system}] if system else []
        msgs.extend(messages)
        try:
            r = c.chat.completions.create(model=mid, messages=msgs,
                                          temperature=options.get("temperature", 0.2))
        except Exception as e:
            _fail(e, self.model)
        choice = r.choices[0] if r.choices else None
        text = getattr(choice.message, "content", "") if choice else ""
        in_t, out_t = r.usage.prompt_tokens if hasattr(r, "usage") else 0, r.usage.completion_tokens if hasattr(r, "usage") else 0
        return Response(text=text, in_tokens=in_t, out_tokens=out_t,
                        cost_usd_estimate=_cost(self.model, in_t, out_t), raw=r)

    def stream(self, messages, system, options) -> Iterator[StreamChunk]:
        c = self._client_or_create()
        _, mid = self.model.split("/", 1) if "/" in self.model else ("openai", self.model)
        msgs = [{"role": "system", "content": system}] if system else []
        msgs.extend(messages)
        try:
            s = c.chat.completions.create(model=mid, messages=msgs,
                                          temperature=options.get("temperature", 0.2),
                                          stream=True, stream_options={"include_usage": True})
            for ch in s:
                if not ch.choices:
                    if hasattr(ch, "usage") and ch.usage:
                        yield StreamChunk(
                            usage={"prompt_tokens": ch.usage.prompt_tokens,
                                   "completion_tokens": ch.usage.completion_tokens,
                                   "cost_usd_estimate": _cost(self.model,
                                                               ch.usage.prompt_tokens,
                                                               ch.usage.completion_tokens)})
                    continue
                d = ch.choices[0].delta
                ctxt = getattr(d, "content", "") or ""
                if ctxt:
                    yield StreamChunk(delta=ctxt)
        except Exception as e:
            _fail(e, self.model)


def _fail(e: Exception, model: str) -> None:
    msg_s = str(e).lower()
    if "auth" in msg_s or "api key" in msg_s or "401" in msg_s:
        raise AuthMissing(provider=model)
    st = getattr(getattr(e, "response", None), "status_code", 500)
    raise AdapterHTTPError(provider=model, status=st, body=str(e)[:300])