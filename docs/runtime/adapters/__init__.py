# adapters/__init__.py — pick the right model adapter by model name.
from __future__ import annotations
import re
from typing import Any
from dataclasses import dataclass


@dataclass
class Response:
    text: str
    in_tokens: int = 0
    out_tokens: int = 0
    cache_hit_tokens: int = 0
    cost_usd_estimate: float = 0.0
    raw: Any = None


def get_adapter(model_name: str):
    """
    Decide which adapter to use based on the model_name prefix:
      - 'anthropic/...'      → Anthropic adapter (Messages API + SSE)
      - 'ollama/...'         → Ollama adapter (local)
      - 'groq/...'           → Groq adapter (its own speed-tuned SDK path)
      - 'cohere/...'         → Cohere v2/chat adapter (command-r family)
      - 'google_ai_studio/', 'gemini_vertex/'
                              → Gemini adapter (:generateContent SSE)
      - anything else        → OpenAI-compat adapter (covers 14 providers)
    """
    prefix = model_name.split("/", 1)[0].lower()
    if prefix == "anthropic":
        from .anthropic import AnthropicAdapter
        return AnthropicAdapter(model=model_name)
    if prefix == "ollama":
        from .ollama import OllamaAdapter
        return OllamaAdapter(model=model_name)
    if prefix == "groq":
        from .groq import GroqAdapter
        return GroqAdapter(model=model_name)
    if prefix == "cohere":
        from .cohere import CohereAdapter
        return CohereAdapter(model=model_name)
    if prefix in ("google_ai_studio", "gemini_vertex"):
        from .gemini import GeminiAdapter
        return GeminiAdapter(model=model_name)
    from .openai_compat import OpenAICompatAdapter
    return OpenAICompatAdapter(model=model_name)
