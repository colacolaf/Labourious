"""runtime/providers.py — probe each LLM provider for live health.

This is the **↻ test** button's backend in Settings → Providers. It talks
to the same adapter the production flows use, calls the model with a
minimal "hi" payload, and reports:

- ``status`` — one of:
    - ``OK``            → model responded, completed normally
    - ``FAIL``          → provider reachable but model returned an error
    - ``AUTH_MISSING``  → no API key for this provider
    - ``TIMEOUT``       → provider didn't respond within budget
    - ``UNREACHABLE``   → couldn't connect at all
- ``latency_ms`` — round-trip wallclock (None on failure paths)
- ``error_message`` — short string for the UI (None on OK)
- ``model_name`` — the exact model string probed
- ``provider_name`` — bare provider (anthropic, openai, ollama, etc.)
- ``in_tokens``, ``out_tokens`` — final usage counts (None on OK paths
  that don't return them, e.g. Cohere non-stream)

Three probe styles:

- **chat probe** — preferred. Issues `adapter.call(messages=[…],
  system="…")`. Returns the full real LLM round-trip, including
  permission/auth, model availability, and round-trip latency.
- **endpoint probe** — `probe_endpoint(base_url, timeout=…)` for
  adapter classes that declare a `base_url`. Just TCP/HTTP up check;
  much faster but doesn't verify the model/deployment exists.
- **no-op probe** — every registered entry returns a sane status
  even when no API call is possible (skipped when `run_io=False`).

The pilot `runtime/smokes/providers_probe_smoke.py` covers all three.
"""
from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Any, Iterable

from .adapters import get_adapter
from .adapters._streaming import AuthMissing, AdapterHTTPError
from ..frontend.keys_storage import probe_endpoint, get_key, key_present


# ---------------------------------------------------------------------------
# Status sentinels
# ---------------------------------------------------------------------------

STATUS_OK = "OK"
STATUS_FAIL = "FAIL"
STATUS_AUTH_MISSING = "AUTH_MISSING"
STATUS_TIMEOUT = "TIMEOUT"
STATUS_UNREACHABLE = "UNREACHABLE"


# ---------------------------------------------------------------------------
# Default per-provider timeouts
# ---------------------------------------------------------------------------
# Probes should be quick (UI launches them on click), so the defaults
# are tighter than what production flows use. Local Ollama typically
# responds in <1s once warm; cloud LLMs in 2-6s. 8s is the sweet spot
# for "is it alive?" — longer means "is the model doing something
# useful" which is a different question.

DEFAULT_TIMEOUT_S = 8.0
SOCKET_TIMEOUT_S = 0.4

# The probe prompt: 1 user turn with a 1-token answer expected. The
# actual content is irrelevant — we just want a live round-trip. We
# guard tokens via `max_tokens=4` so a chatty model doesn't add 30s of
# read time to the probe.
_PROBE_MESSAGES = [
    {"role": "user", "content": "Reply with the single word 'ok'."}
]
_PROBE_SYSTEM = (
    "Reply with the single word 'ok'. Do not add commentary."
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ProbeResult:
    """Result of one provider probe.

    Attributes
    ----------
    provider_name : str
        Bare provider (``"ollama"``, ``"anthropic"``, ``"cohere"``,
        ...). Empty if `model_name` couldn't be parsed.
    model_name : str
        The exact model string probed (e.g. ``"anthropic/claude-sonnet-4-5"``).
    status : str
        One of STATUS_*.
    latency_ms : int | None
        Round-trip wallclock in milliseconds. None on every failed
        path (timeout, unreachable, fail, auth_missing) except where
        we have something meaningful to report.
    error_message : str | None
        Short string for the UI. None on OK.
    in_tokens, out_tokens : int | None
        Final usage counts on OK; None elsewhere.
    note : str | None
        Free-form extra context ("rate-limit retry", "weak response",
        "key from keychain", etc.).
    """

    provider_name: str
    model_name: str
    status: str
    latency_ms: int | None
    error_message: str | None = None
    in_tokens: int | None = None
    out_tokens: int | None = None
    note: str | None = None

    def is_ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "error_message": self.error_message,
            "in_tokens": self.in_tokens,
            "out_tokens": self.out_tokens,
            "note": self.note,
        }


# ---------------------------------------------------------------------------
# Provider-name extraction
# ---------------------------------------------------------------------------

def _split_model(model_name: str) -> tuple[str, str]:
    """`"ollama/llama3.2:3b" → ("ollama", "llama3.2:3b")`.

    Returns `(provider, model_name_with_provider)` for compat with
    adapters that expect the same string back.
    """
    if "/" not in model_name:
        return ("", model_name)
    provider, _, _ = model_name.partition("/")
    return provider.lower(), model_name


# ---------------------------------------------------------------------------
# Per-provider key present?
# ---------------------------------------------------------------------------

def _provider_has_key(provider: str) -> bool | None:
    """True if a key is present for `provider` via keychain or env.

    Returns None when the provider doesn't need authentication (e.g.
    local Ollama). Returns False when no key was found.
    """
    # Local providers don't need keys.
    if provider in ("ollama",):
        return None
    if provider == "":
        return None
    # Try the storage layer first.
    try:
        if key_present(provider):
            return True
    except Exception:
        pass
    # Fallback to env equivalents the adapter itself uses.
    env_equiv = {
        "anthropic":     "ANTHROPIC_API_KEY",
        "openai":        "OPENAI_API_KEY",
        "groq":          "GROQ_API_KEY",
        "cohere":        "COHERE_API_KEY",
        "gemini":        "GEMINI_API_KEY",
        "google_ai_studio": "GEMINI_API_KEY",
        "openrouter":    "OPENROUTER_API_KEY",
    }
    import os
    env = env_equiv.get(provider)
    if env and os.environ.get(env):
        return True
    return False


# ---------------------------------------------------------------------------
# The core probe function
# ---------------------------------------------------------------------------

def probe_provider(
    model_name: str,
    *,
    run_io: bool = True,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ProbeResult:
    """Probe a model with a minimal "hi" round-trip.

    ``run_io=False`` skips the actual chat call — useful for the
    per-row endpoint probe (faster) when the UI just wants up-vs-down.

    Returns a :class:`ProbeResult` (always populated; never raises).
    """
    provider, _ = _split_model(model_name)

    # Key check FIRST (before adapter construction). Adapters raise
    # AuthMissing on construction when there's no key, so checking
    # in advance lets us classify the error cleanly as AUTH_MISSING
    # rather than as a generic construction FAIL.
    has_key = _provider_has_key(provider)
    if has_key is False:
        return ProbeResult(
            provider_name=provider, model_name=model_name,
            status=STATUS_AUTH_MISSING, latency_ms=None,
            error_message=(
                f"no API key configured for '{provider}'. "
                "Add one in Settings → Providers → Secrets, or set "
                f"{provider.upper()}_API_KEY in your environment."
            ),
            note="key check failed before adapter construction",
        )

    # If we can't resolve to an adapter at all, that's a structured FAIL
    # — but only if there *was* a key, otherwise we'd have hit the
    # earlier AUTH_MISSING check.
    try:
        adapter = get_adapter(model_name)
    except AuthMissing as e:
        return ProbeResult(
            provider_name=provider, model_name=model_name,
            status=STATUS_AUTH_MISSING, latency_ms=None,
            error_message=str(e),
            note="AuthMissing raised by adapter at construction",
        )
    except Exception as e:
        return ProbeResult(
            provider_name=provider, model_name=model_name,
            status=STATUS_FAIL, latency_ms=None,
            error_message=f"adapter construction failed: {type(e).__name__}: {e}",
        )

    # Endpoint up check (cheap, non-LLM). Done before the chat probe
    # so manifest the user not-a-network-problem as UNREACHABLE rather
    # than TIMEOUT (which is what a hung chat call would look like).
    base_url = getattr(adapter, "base_url", None)
    if base_url and not probe_endpoint(base_url, timeout=SOCKET_TIMEOUT_S):
        return ProbeResult(
            provider_name=provider, model_name=model_name,
            status=STATUS_UNREACHABLE, latency_ms=None,
            error_message=(
                f"endpoint {base_url} unreachable within "
                f"{SOCKET_TIMEOUT_S}s (network / firewall / DNS fail?)"
            ),
            note="endpoint probe failed before chat call",
        )

    # Skip actual call when caller wants cheap (panel heartbeat).
    if not run_io:
        return ProbeResult(
            provider_name=provider, model_name=model_name,
            status=STATUS_OK, latency_ms=0,
            note="endpoint reachable (chat call skipped — run_io=False)",
        )

    # Bound the chat call by `timeout_s`. Adapters that take their own
    # timeout kwarg (OpenAI-compat, Cohere) get `timeout=timeout_s`;
    # those without one (Ollama) we still bound via signal-style wall
    # timing below.
    started = time.monotonic()
    try:
        adapter._bound_timeout = timeout_s  # noqa: SLF001 - read by adapter
        kwargs: dict[str, Any] = {"max_tokens": 4, "temperature": 0.0}
        # Read adapter's own `timeout` argument if it knows about it.
        try:
            import inspect as _i
            sig = _i.signature(adapter.call)
            if "timeout" in sig.parameters:
                kwargs["timeout"] = timeout_s
        except Exception:
            pass
        response = adapter.call(messages=_PROBE_MESSAGES,
                                system=_PROBE_SYSTEM, options=kwargs)
    except AuthMissing as e:
        return ProbeResult(
            provider_name=provider, model_name=model_name,
            status=STATUS_AUTH_MISSING, latency_ms=None,
            error_message=str(e),
            note="AuthMissing raised during chat call",
        )
    except AdapterHTTPError as e:
        return ProbeResult(
            provider_name=provider, model_name=model_name,
            status=STATUS_FAIL, latency_ms=int((time.monotonic() - started) * 1000),
            error_message=str(e),
        )
    except (socket.timeout, TimeoutError) as e:
        return ProbeResult(
            provider_name=provider, model_name=model_name,
            status=STATUS_TIMEOUT, latency_ms=int((time.monotonic() - started) * 1000),
            error_message=f"timed out after {timeout_s}s",
        )
    except (ConnectionError, OSError) as e:
        return ProbeResult(
            provider_name=provider, model_name=model_name,
            status=STATUS_UNREACHABLE, latency_ms=None,
            error_message=f"connection error: {e}",
        )
    except Exception as e:
        return ProbeResult(
            provider_name=provider, model_name=model_name,
            status=STATUS_FAIL,
            latency_ms=int((time.monotonic() - started) * 1000),
            error_message=f"{type(e).__name__}: {e}",
        )

    elapsed_ms = int((time.monotonic() - started) * 1000)
    text = getattr(response, "text", "") or ""
    if elapsed_ms > timeout_s * 1000:
        # Adapter didn't honour timeout, but we exceeded the budget.
        return ProbeResult(
            provider_name=provider, model_name=model_name,
            status=STATUS_TIMEOUT, latency_ms=elapsed_ms,
            error_message=f"slow response: {elapsed_ms}ms > {int(timeout_s*1000)}ms",
            in_tokens=getattr(response, "in_tokens", None),
            out_tokens=getattr(response, "out_tokens", None),
        )
    return ProbeResult(
        provider_name=provider, model_name=model_name,
        status=STATUS_OK, latency_ms=elapsed_ms,
        in_tokens=getattr(response, "in_tokens", None),
        out_tokens=getattr(response, "out_tokens", None),
        note=("response text: " + text[:30]) if text else "OK (no body content)",
    )


# ---------------------------------------------------------------------------
# Batch convenience
# ---------------------------------------------------------------------------

def probe_many(
    model_names: Iterable[str],
    *,
    run_io: bool = True,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> list[ProbeResult]:
    """Probe a list of providers sequentially.

    Sequential (not parallel) is the right default for the Settings ↻
    test rail — parallel probes hammer the same endpoint in CI/dev
    machines and just trip rate-limits. The UI calls this once per
    rail row; the orchestrator's reachability ping uses this too.
    """
    return [
        probe_provider(m, run_io=run_io, timeout_s=timeout_s)
        for m in model_names
    ]


__all__ = [
    "ProbeResult",
    "probe_provider",
    "probe_many",
    "STATUS_OK", "STATUS_FAIL", "STATUS_AUTH_MISSING",
    "STATUS_TIMEOUT", "STATUS_UNREACHABLE",
    "DEFAULT_TIMEOUT_S",
]
