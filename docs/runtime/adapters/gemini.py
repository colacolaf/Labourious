# adapters/gemini.py — Google Gemini (AI Studio + Vertex) adapter.
#
# Covers both `google_ai_studio/*` and `gemini_vertex/*` prefixes (they share
# the same underlying API surface — Vertex differs only in auth, and AI
# Studio's "OpenAI-compat" path is optional, not the canonical way to talk
# to Gemini).
#
# Spec:   https://ai.google.dev/api/generate-content
# Stream: https://ai.google.dev/api/generate-content#stream
# Endpoint:  POST  {base}/v1beta/models/{model}:generateContent
#           POST  {base}/v1beta/models/{model}:streamGenerateContent
# Auth:   ?key={API_KEY} query parameter (Google AI Studio path — simplest).
#         For Vertex, swap base_url and pass api_key=None; the deployment
#         sets OAuth-bearer headers, which we leave as a future TODO since
#         AI Studio's API-key approach covers >95% of free-tier users.
#
# Stream framing: each chunk is `data: {...JSON...}\n\n` (no `event:` line —
# unlike Anthropic/Cohere). The JSON has `candidates[].content.parts[].text`
# for the delta, and `usageMetadata.{prompt,candidates}TokenCount` for
# billing.
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
# (USD per 1M tokens, in/out).  Prefixes chosen so `gemini-2.5-pro-preview-05-06`
# still hits the gemini-2.5-pro row.  Unknown models default to 2.5-pro.
_COSTS_PER_MILLION: dict[str, tuple[float, float]] = {
    # Gemini 2.5 (latest)
    "gemini-2.5-pro":       (1.25, 10.00),
    "gemini-2.5-flash":     (0.075, 0.30),
    "gemini-2.5-flash-lite":(0.018, 0.075),
    # Gemini 2.0
    "gemini-2.0-pro":       (1.25, 5.00),
    "gemini-2.0-flash":     (0.10, 0.40),
    "gemini-2.0-flash-lite":(0.025, 0.10),
    # Gemini 1.5
    "gemini-1.5-pro":       (1.25, 5.00),
    "gemini-1.5-flash":     (0.075, 0.30),
    "gemini-1.5-flash-8b":  (0.0375, 0.15),
    # Gemini 1.0
    "gemini-1.0-pro":       (0.50, 1.50),
    "gemini-nano":          (0.10, 0.40),
}
_DEFAULT_COST: tuple[float, float] = (1.25, 10.00)   # gemini-2.5-pro


def _cost_for(model: str, in_tok: int, out_tok: int) -> float:
    needle = model.lower()
    candidates = [slug for slug in _COSTS_PER_MILLION if needle.startswith(slug)]
    if candidates:
        in_rate, out_rate = _COSTS_PER_MILLION[max(candidates, key=len)]
    else:
        in_rate, out_rate = _DEFAULT_COST
    return (in_tok / 1_000_000.0) * in_rate + (out_tok / 1_000_000.0) * out_rate


# ---------------------------------------------------------- auth
def _resolve_key(provider_name: str) -> str | None:
    """Auth precedence: keychain → GOOGLE_API_KEY env."""
    try:
        from frontend.keys_storage import get_key  # type: ignore
        k = get_key(provider_name)
        if k:
            return k
    except Exception:
        pass
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")


# ---------------------------------------------------------- role mapping
_ROLE_OPENAI_TO_GEMINI = {"user": "user", "assistant": "model", "system": None}
_ROLE_GEMINI_TO_OPENAI = {"user": "user", "model": "assistant"}


def _messages_to_contents(messages: list[dict], system: str | None) -> tuple[list[dict], list[str]]:
    """Translate OpenAI-style messages to Gemini contents.

    Returns:
      contents : list of {"role": "user"|"model", "parts": [...]}
      warnings : any dropped roles (Gemini has no system role — system goes
                 in `systemInstruction` separately)
    """
    contents: list[dict] = []
    warnings: list[str] = []
    for m in messages:
        role = (m.get("role") or "user").lower()
        content = m.get("content") or ""
        gem_role = _ROLE_OPENAI_TO_GEMINI.get(role)
        if gem_role is None:
            # Treat a stray "system" message as additional system prompt.
            warnings.append(f"role={role!r} routed to systemInstruction")
            continue
        contents.append({"role": gem_role, "parts": [{"text": content}]})
    return contents, warnings


def _system_instruction(system: str | None) -> dict | None:
    if not system:
        return None
    return {"parts": [{"text": system}]}


# ---------------------------------------------------------- request body
def _build_body(messages: list[dict], system: str, options: dict, *, stream: bool) -> dict[str, Any]:
    contents, _ = _messages_to_contents(messages, system)
    body: dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": options.get("temperature", 0.2),
            "maxOutputTokens": options.get("max_tokens", 4096),
        },
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    # `stream` is a query parameter, not a body field on streamGenerateContent.
    return body


# ---------------------------------------------------------- SSE helpers
def _iter_gemini_chunks(response: httpx.Response) -> Iterator[dict[str, Any]]:
    """Yield each chunk JSON from Gemini's `:streamGenerateContent` body.

    Each chunk is a JSON object (not an event wrapper). They're streamed as
    `data: {...}\n\n` — no `event:` line, no `[DONE]` marker. Streaks of
    blank lines separate successive chunks; we skip them.

    Note: Gemini's response wraps the *whole thing* in `[...]` for non-stream;
    for stream, each line is exactly one chunk's JSON.
    """
    for raw_line in response.iter_lines():
        if not raw_line:
            continue
        if raw_line.startswith("data:"):
            payload = raw_line[len("data:"):].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                yield json.loads(payload)
            except json.JSONDecodeError:
                continue
        elif raw_line.startswith("{"):
            # Some implementations bypass SSE framing and stream JSON lines
            # directly. Handle that case too.
            try:
                yield json.loads(raw_line)
            except json.JSONDecodeError:
                continue


# ---------------------------------------------------------- text extraction
def _extract_text(payload: dict[str, Any]) -> str:
    """Concatenate text parts from a chunk's candidates."""
    out: list[str] = []
    for c in payload.get("candidates", []) or []:
        content = c.get("content") or {}
        for part in content.get("parts", []) or []:
            t = part.get("text")
            if t:
                out.append(t)
    return "".join(out)


def _extract_usage(payload: dict[str, Any]) -> tuple[int, int]:
    usage = payload.get("usageMetadata") or {}
    in_tok = int(usage.get("promptTokenCount", 0) or 0)
    out_tok = int(usage.get("candidatesTokenCount", 0) or 0)
    return in_tok, out_tok


# ---------------------------------------------------------- adapter
@dataclass
class GeminiAdapter:
    model: str                      # "google_ai_studio/gemini-2.0-flash" or "gemini_vertex/gemini-2.5-pro" or just "gemini-2.0-flash"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    api_key: str | None = None      # explicit (tests) → keychain → env
    transport: Any = None           # httpx.MockTransport in tests
    provider_name: str | None = None   # "google_ai_studio" or "gemini_vertex" (defaults to prefix)

    def __post_init__(self):
        if httpx is None:
            raise RuntimeError(
                "httpx is required for GeminiAdapter. "
                "Install with: pip install httpx httpx_sse"
            )
        # Strip "<provider>/" prefix; remember which provider so keychain
        # lookup goes to the right service name.
        if "/" in self.model:
            prefix, self.model = self.model.split("/", 1)
            self.provider_name = self.provider_name or prefix
        else:
            self.provider_name = self.provider_name or "google_ai_studio"
        if "/" not in self.model:
            # No prefix — default to google_ai_studio
            self.provider_name = self.provider_name or "google_ai_studio"

        if self.api_key is None:
            self.api_key = _resolve_key(self.provider_name)
        if not self.api_key:
            raise AuthMissing(provider=self.provider_name)

    # --------------------------------------------------------------- call
    def call(self, messages: list[dict], system: str, options: dict | None = None) -> Response:
        options = options or {}
        body = _build_body(messages, system, options, stream=False)
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        try:
            with httpx.Client(timeout=120, transport=self.transport) as client:
                r = client.post(url, json=body)
        except httpx.RequestError as exc:
            raise AdapterHTTPError(provider=self.provider_name, status=0,
                                   body=f"connection error: {exc}") from exc
        if r.status_code >= 400:
            raise AdapterHTTPError(provider=self.provider_name,
                                   status=r.status_code, body=r.text)
        try:
            payload = r.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{self.provider_name}: malformed JSON response: {exc}") from exc
        text = _extract_text(payload).strip()
        in_tok, out_tok = _extract_usage(payload)
        cost = _cost_for(self.model, in_tok, out_tok)
        return Response(
            text=text, in_tokens=in_tok, out_tokens=out_tok,
            cache_hit_tokens=0, cost_usd_estimate=cost, raw=payload,
        )

    # --------------------------------------------------------------- stream
    def stream(self, messages: list[dict], system: str, options: dict | None = None) -> Iterator[StreamChunk]:
        """Yield text deltas from Gemini's `:streamGenerateContent` SSE channel.

        Gemini's framing is data-only (no `event:` line). Each chunk's
        `usageMetadata` carries the running token counts; costs them per
        chunk so the final emitted figure is up-to-date.
        """
        options = options or {}
        body = _build_body(messages, system, options, stream=True)
        url = f"{self.base_url}/models/{self.model}:streamGenerateContent?key={self.api_key}"
        in_tok_total = 0
        out_tok_total = 0
        last_text_emitted: str = ""
        finish_reason: str | None = None
        try:
            with httpx.Client(timeout=120, transport=self.transport) as client:
                with client.stream("POST", url, json=body) as r:
                    if r.status_code >= 400:
                        raise AdapterHTTPError(
                            provider=self.provider_name,
                            status=r.status_code,
                            body=r.read().decode("utf-8", "replace"),
                        )
                    for payload in _iter_gemini_chunks(r):
                        # Extract the delta text — Gemini emits the *whole
                        # accumulated* text in each fragment, so we dedupe
                        # by comparing to last_text_emitted and slicing off
                        # the prefix.
                        text_now = _extract_text(payload)
                        if text_now and text_now != last_text_emitted:
                            delta = text_now[len(last_text_emitted):]
                            last_text_emitted = text_now
                            if delta:
                                yield StreamChunk(delta=delta, raw=payload)
                        # Track running usage from usageMetadata.
                        u = payload.get("usageMetadata") or {}
                        if u:
                            in_tok_total = int(u.get("promptTokenCount",
                                                      in_tok_total) or in_tok_total)
                            out_tok_total = int(u.get("candidatesTokenCount",
                                                       out_tok_total) or out_tok_total)
                        # Capture finish_reason from the last candidate.
                        for c in payload.get("candidates", []) or []:
                            fr = c.get("finishReason")
                            if fr and fr != "STOP":
                                finish_reason = fr
                            elif fr == "STOP":
                                finish_reason = fr
                    cost = _cost_for(self.model, in_tok_total, out_tok_total)
                    yield StreamChunk(
                        delta="",
                        finish_reason=finish_reason or "STOP",
                        usage={
                            "prompt_tokens": in_tok_total,
                            "completion_tokens": out_tok_total,
                            "cost_usd_estimate": cost,
                        },
                    )
        except httpx.RequestError as exc:
            raise AdapterHTTPError(provider=self.provider_name, status=0,
                                   body=f"connection error: {exc}") from exc

    # --------------------------------------------------------------- helpers
    def route_summary(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "base_url": self.base_url,
            "model_id": self.model,
            "streaming_supported": True,
        }


__all__ = ["GeminiAdapter", "_cost_for"]
