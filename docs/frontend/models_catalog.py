"""models_catalog.py — live model discovery from local/OpenAI-compatible providers.

Why this exists
===============
Every model list used to be hardcoded (``llama3.3:70b``, ``qwen2.5:72b`` …)
in the wizard, the provider panel, and the settings presets — so the UI
advertised models the user may never have pulled, and never showed the
ones they had. This module asks the server what it actually serves:

    Ollama                 GET {base}/api/tags           (no auth)
    OpenAI-compatible      GET {base}/models             (Bearer, optional)
    Anthropic              GET {base}/v1/models          (x-api-key)
    Google                 GET {base}/v1beta/models      (?key=)

Design constraints (match the TUI's event-loop realities):
    * Sync stdlib-only HTTP (urllib) — the frontend calls this through
      ``asyncio.to_thread``, the same way provider probes work. No new
      dependency, no httpx version pin issues.
    * Short hard timeouts (2.5 s connect/read) — a dead local server
      must degrade instantly, not hang the Settings screen.
    * 30 s TTL cache keyed on (provider, base_url) so opening the
      panel twice doesn't re-hit the network; a ``force=True`` bypass
      exists for the connect form's explicit refresh.
    * Every failure mode returns the curated fallback list from
      ``frontend.providers`` — the UI is never left with nothing.

Public surface:
    fetch_models(provider, base_url=None, api_key=None, force=False)
        -> tuple[str, ...]
    fetch_models_result(...) -> ModelDiscovery (status + detail included)
    clear_models_cache()
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from frontend.providers import by_name

# Hard ceilings — a local server that is *starting up* (model load) can
# take a second to answer; anything longer is treated as down.
_CONNECT_TIMEOUT_S = 2.5
_READ_TIMEOUT_S = 4.0
_TTL_S = 30.0

# Curated fallbacks stay available for offline/broken endpoints.
_FALLBACKS: dict[str, tuple[str, ...]] = {}


def _fallback_for(provider: str) -> tuple[str, ...]:
    entry = by_name(provider)
    return tuple(entry.models) if entry else ()


# --------------------------------------------------------------- cache
_CACHE: dict[tuple[str, str], tuple[float, tuple[str, ...]]] = {}


def clear_models_cache() -> None:
    """Forget all cached discovery results (used by tests + refresh)."""
    _CACHE.clear()


# --------------------------------------------------------------- result
@dataclass
class ModelDiscovery:
    """Outcome of one discovery attempt — status is always safe to show."""

    provider: str
    base_url: str
    status: str                      # "ok" | "unreachable" | "auth" | "error"
    models: tuple[str, ...] = ()     # live models when status == "ok"
    fallback: tuple[str, ...] = ()   # curated list for UI display on failure
    detail: str = ""                 # human-readable error/summary
    latency_ms: int | None = None
    source: str = "static"           # "live" | "static"

    @property
    def display_models(self) -> tuple[str, ...]:
        """Models the UI should offer: live when available, else curated."""
        return self.models if self.status == "ok" and self.models else self.fallback


# --------------------------------------------------------------- http
def _http_get_json(url: str, *, headers: dict[str, str] | None = None,
                   timeout_s: float = _READ_TIMEOUT_S) -> tuple[Any, int]:
    """GET a URL, parse JSON. Returns (payload, status_code).
    Raises urllib.error.URLError / HTTPError / TimeoutError on failure."""
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    started = time.monotonic()
    with urllib.request.urlopen(
        req,
        timeout=timeout_s,
    ) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        latency = int((time.monotonic() - started) * 1000)
    return payload, latency


def _normalize_base(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return ""
    # OpenAI-compatible bases usually end in /v1 — /models appends cleanly.
    # Ollama bases are bare host:port — /api/tags appends cleanly.
    return base


def _extract_openai_models(payload: Any) -> list[str]:
    """/models payload: {"data": [{"id": "llama3.2:3b"}, …]} (OpenAI shape)."""
    data = payload.get("data") if isinstance(payload, dict) else payload
    models: list[str] = []
    if isinstance(data, list):
        for row in data:
            if isinstance(row, str):
                models.append(row)
            elif isinstance(row, dict):
                mid = row.get("id") or row.get("name") or row.get("model")
                if isinstance(mid, str) and mid:
                    models.append(mid)
    return sorted(dict.fromkeys(models))


def _extract_ollama_models(payload: Any) -> list[str]:
    """/api/tags payload: {"models": [{"name": "llama3.2:3b", …}, …]}.

    `name` is the pullable tag ("llama3.2:3b"); `model` duplicates it.
    Sort with smallest-first preference (param-size heuristics) so the
    recommended default surfaces at the top of pickers.
    """
    models: list[str] = []
    rows = payload.get("models") if isinstance(payload, dict) else None
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                mid = row.get("name") or row.get("model")
                if isinstance(mid, str) and mid:
                    models.append(mid)
    return _sort_ollama(models)


def _param_billions(name: str) -> float:
    """Best-effort parameter count from a tag like `llama3.2:3b` or
    `qwen2.5:14b-instruct` — used only for display ordering."""
    import re

    m = re.search(r":([0-9]+(?:\.[0-9]+)?)\s*b\b", name.lower())
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return 999.0
    return 999.0


def _sort_ollama(models: list[str]) -> list[str]:
    return sorted(dict.fromkeys(models), key=lambda m: (_param_billions(m), m))


# --------------------------------------------------------------- per-shape probes
def _probe_ollama(base: str) -> tuple[str, tuple[str, ...], str]:
    """Returns (status, models, detail)."""
    payload, _ = _http_get_json(f"{base}/api/tags", timeout_s=_READ_TIMEOUT_S)
    models = _extract_ollama_models(payload)
    if not models:
        return "error", (), "ollama is up but has no models pulled — run: ollama pull llama3.2:3b"
    return "ok", tuple(models), f"{len(models)} models installed"


def _probe_openai_compat(base: str, api_key: str | None) -> tuple[str, tuple[str, ...], str]:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload, _ = _http_get_json(f"{base}/models", headers=headers, timeout_s=_READ_TIMEOUT_S)
    models = _extract_openai_models(payload)
    if not models:
        return "error", (), "endpoint responded but listed no models"
    return "ok", tuple(models), f"{len(models)} models listed"


def _probe_anthropic(api_key: str | None) -> tuple[str, tuple[str, ...], str]:
    if not api_key:
        return "auth", (), "an API key is required to list models"
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    payload, _ = _http_get_json(
        "https://api.anthropic.com/v1/models", headers=headers, timeout_s=_READ_TIMEOUT_S)
    models = _extract_openai_models(payload)  # same {"data":[{id:…}]} shape
    if not models:
        return "error", (), "endpoint responded but listed no models"
    return "ok", tuple(models), f"{len(models)} models listed"


def _probe_google(api_key: str | None) -> tuple[str, tuple[str, ...], str]:
    if not api_key:
        return "auth", (), "an API key is required to list models"
    url = ("https://generativelanguage.googleapis.com/v1beta/models"
           + (f"?key={api_key}" if api_key else ""))
    payload, _ = _http_get_json(url, timeout_s=_READ_TIMEOUT_S)
    rows = payload.get("models") if isinstance(payload, dict) else None
    models: list[str] = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                name = row.get("name")  # "models/gemini-2.0-flash"
                if isinstance(name, str) and name.startswith("models/"):
                    models.append(name.split("/", 1)[1])
    models = sorted(dict.fromkeys(models))
    if not models:
        return "error", (), "endpoint responded but listed no models"
    return "ok", tuple(models), f"{len(models)} models listed"


def _shape_for(provider: str, entry) -> str:
    if entry is not None and getattr(entry, "shape", None):
        return entry.shape
    return "openai"


# --------------------------------------------------------------- public API
def fetch_models_result(
    provider: str,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    force: bool = False,
) -> ModelDiscovery:
    """Ask the provider's endpoint what models it actually serves.

    Never raises — every failure returns a ModelDiscovery with status
    set and the curated fallback list attached, so callers can always
    populate a picker.
    """
    provider = (provider or "").strip().lower()
    entry = by_name(provider)
    resolved_base = _normalize_base(
        base_url or (entry.base_url if entry else "") or "")
    cache_key = (provider, resolved_base or "default")

    if not force:
        cached = _CACHE.get(cache_key)
        if cached and (time.monotonic() - cached[0]) < _TTL_S:
            return cached[1]

    fallback = _fallback_for(provider)

    def _finish(status: str, models: tuple[str, ...], detail: str,
                latency: int | None, source: str) -> ModelDiscovery:
        result = ModelDiscovery(
            provider=provider, base_url=resolved_base, status=status,
            models=models, fallback=fallback, detail=detail,
            latency_ms=latency, source=source,
        )
        _CACHE[cache_key] = (time.monotonic(), result)
        return result

    if not resolved_base and _shape_for(provider, entry) not in ("anthropic", "google"):
        return _finish("error", (), "no endpoint configured to query", None, "static")

    try:
        shape = _shape_for(provider, entry)
        if shape == "ollama":
            status, models, detail = _probe_ollama(resolved_base)
        elif shape == "anthropic":
            status, models, detail = _probe_anthropic(api_key)
        elif shape == "google":
            status, models, detail = _probe_google(api_key)
        else:
            # openai / hf / custom all speak the OpenAI-compatible shape.
            status, models, detail = _probe_openai_compat(resolved_base, api_key)
        return _finish(
            status, models, detail, None,
            "live" if status == "ok" else "static",
        )
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return _finish("auth", (), f"HTTP {e.code} — key rejected or missing", None, "static")
        return _finish("error", (), f"HTTP {e.code} from {resolved_base}", None, "static")
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        return _finish(
            "unreachable", (),
            f"{provider} not reachable at {resolved_base} ({reason}) — is the server running?",
            None, "static",
        )
    except TimeoutError:
        return _finish("unreachable", (), f"{provider} timed out at {resolved_base}", None, "static")
    except (json.JSONDecodeError, ValueError) as e:
        return _finish("error", (), f"malformed response from {resolved_base}: {e}", None, "static")
    except Exception as e:  # noqa: BLE001 — last-resort guard for UI safety
        return _finish("error", (), f"{type(e).__name__}: {e}", None, "static")


def fetch_models(
    provider: str,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    force: bool = False,
) -> tuple[str, ...]:
    """Convenience wrapper — just the models the UI should display."""
    return fetch_models_result(
        provider, base_url=base_url, api_key=api_key, force=force,
    ).display_models


def cached_models(provider: str, base_url: str | None = None) -> ModelDiscovery | None:
    """Return a FRESH CACHED discovery result without touching the network.

    For render-path code (panels painted on every keystroke) that must
    never block: shows live models when a worker has already fetched
    them, None otherwise. The connect forms use fetch_models_result in
    a worker thread instead.
    """
    provider = (provider or "").strip().lower()
    entry = by_name(provider)
    resolved_base = _normalize_base(
        base_url or (entry.base_url if entry else "") or "")
    cached = _CACHE.get((provider, resolved_base or "default"))
    if cached and (time.monotonic() - cached[0]) < _TTL_S:
        return cached[1]
    return None


__all__ = [
    "ModelDiscovery",
    "cached_models",
    "clear_models_cache",
    "fetch_models",
    "fetch_models_result",
]
