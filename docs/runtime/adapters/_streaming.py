# adapters/_streaming.py — shared types for streaming adapters.
#
# Both OpenAICompatAdapter (covers 15 OpenAI-compat providers) and
# AnthropicAdapter (covers the Anthropic Messages API) consume these.
# Future streaming adapters (Cohere v2/chat, Gemini Vertex, custom SSE
# endpoints) should import the same shapes so call_agent can treat them
# interchangeably.
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StreamChunk:
    """One streamed delta from any provider's SSE channel.

    Attributes
    ----------
    delta : str
        Incremental text fragment to feed the TUI bubble. Empty on the
        final chunk (which carries `usage` instead).
    finish_reason : str | None
        Set when the server publishes the reason the stream ended
        ("stop", "length", "tool_use", "end_turn", etc.). Carried on
        the final chunk only.
    usage : dict[str, int] | None
        Server-reported token counts. Always paired with
        `cost_usd_estimate` (USD, float) when present — adapters normalise
        the schema across providers, so the runtime sees one shape.
    raw : dict | None
        The original provider event, kept for debugging and citation
        audit trails (we want a paper trail of what the model actually
        said if a finance memo is later challenged).
    """
    delta: str = ""
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None
    raw: dict[str, Any] | None = field(default=None, repr=False)


# ---------------------------------------------------------- typed errors
@dataclass(frozen=True)
class AuthMissing(Exception):
    """No key for the requested provider in any of: explicit > keychain > env."""
    provider: str

    def __str__(self) -> str:
        return (
            f"No API key for '{self.provider}'. "
            f"Add one in Settings → Providers, or set "
            f"{self.provider.upper()}_API_KEY in your environment."
        )


@dataclass(frozen=True)
class AdapterHTTPError(Exception):
    provider: str
    status: int
    body: str

    def __str__(self) -> str:
        return f"{self.provider} HTTP {self.status}: {self.body[:200]}"


AdapterError = (AuthMissing, AdapterHTTPError)


# ---------------------------------------------------------- helpers
def merge_usage(usage: dict[str, Any] | None, cost: float) -> dict[str, Any] | None:
    """Normalise a provider's usage dict into the runtime's standard shape.

    The runtime only cares about {prompt_tokens, completion_tokens, cost_usd_estimate}.
    Each provider publishes them under different names — this helper exists
    so adapters don't have to keep rewriting the same dict-merge logic.
    """
    if not usage:
        return None
    return {
        "prompt_tokens": int(usage.get("prompt_tokens",
                                      usage.get("input_tokens", 0) or 0)),
        "completion_tokens": int(usage.get("completion_tokens",
                                            usage.get("output_tokens", 0) or 0)),
        "cost_usd_estimate": cost,
    }
