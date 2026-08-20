"""
rates.py — unified per-model rate table + cost estimator.

Single source of truth for the footer hint's "≈ $0.30 · 5 agents" line
and any other place we need to predict the cost of an LLM call before
running it.

Three things live here:

  1. ``_PROVIDER_RATES`` — USD per 1M tokens (in, out) keyed by
     provider prefix. Local + free-tier models get (0.0, 0.0).
     Unknown models fall through to ``_UNKNOWN_DEFAULT`` so we never
     silently bill $0 for a model we haven't catalogued.

  2. ``_AGENT_TOKEN_ESTIMATES`` — median (in_tokens, out_tokens) per
     agent × depth. Calibrated from real smoke runs (see
     ``docs/runtime/.runs/20260819*/cost.json`` — ranges are 0.7-1.4×
     the median across the 11 runs we have). Used for the flow-level
     estimate, not for actual billing (the adapter's own
     ``_cost_for()`` is the source of truth post-hoc).

  3. ``estimate_run_cost()`` — public API. Takes a flow + model +
     paid_for + depth and returns ``(usd, agent_count, is_free)``.
     The footer formatter consumes this.

Why a unified module instead of reusing each adapter's private
``_cost_for()``?
  - The adapters already export ``Response.cost_usd_estimate`` once a
    call completes; we don't want to duplicate that billing logic.
  - But the *footer* runs BEFORE any adapter call, so we need a
    pre-call estimator that doesn't depend on httpx / keyring / etc.
  - Per-agent token budgets are a runtime concept, not an adapter
    concept — they belong here, not in anthropic.py / openai_compat.py.

Falls back to ``_UNKNOWN_DEFAULT = (5.00, 15.00)`` (Opus-class) for
unknown models so the footer is conservative rather than silently
free. Users who see "$X" can override to a known-cheaper model.
"""

from __future__ import annotations

from typing import Iterable


# --------------------------------------------------------------------------- #
#  Rate tables — USD per 1M tokens (in, out).
# --------------------------------------------------------------------------- #
# Format: provider -> model_slug -> (in_per_mtok, out_per_mtok).
# Local / free-tier models use (0.0, 0.0). Keys are lowercase.
#
# Updates: if you add a model the footer must show correctly, append
# it here. The pilot (cost_footer_smoke.py) flags known-model slugs as
# required, so adding a new model is a one-line change.
_PROVIDER_RATES: dict[str, dict[str, tuple[float, float]]] = {
    "anthropic": {
        # current Claude 4.x family
        "claude-opus-4":        (15.00, 75.00),
        "claude-sonnet-4":      (3.00, 15.00),
        "claude-haiku-4":       (1.00,  5.00),
        # legacy 3.x family
        "claude-3-5-sonnet":    (3.00, 15.00),
        "claude-3-5-haiku":     (0.80,  4.00),
        "claude-3-opus":        (15.00, 75.00),
        "claude-3-sonnet":      (3.00, 15.00),
        "claude-3-haiku":       (0.25,  1.25),
    },
    "openai": {
        "gpt-4o":               (2.50, 10.00),
        "gpt-4o-mini":          (0.15,  0.60),
        "gpt-4-turbo":          (10.00, 30.00),
        "gpt-4":                (30.00, 60.00),
        "gpt-3.5-turbo":        (0.50,  1.50),
        "o1-preview":           (15.00, 60.00),
        "o1-mini":              (3.00, 12.00),
    },
    "groq": {
        # Groq's *free* developer tier is rate-limited but $0 — these
        # are the public-slug free models. (Paid tier inherits the
        # underlying model's pricing, but we don't ship that table
        # because v1 users are free-tier-first.)
        "llama-3.3-70b-versatile": (0.0, 0.0),
        "llama-3.1-8b-instant":    (0.0, 0.0),
        "mixtral-8x7b-32768":      (0.0, 0.0),
        "gemma2-9b-it":            (0.0, 0.0),
    },
    "gemini": {
        "gemini-2.5-pro":          (1.25,  10.00),
        "gemini-2.5-flash":        (0.075,  0.30),
        "gemini-2.5-flash-lite":   (0.018,  0.075),
        "gemini-2.0-flash-lite":   (0.025,  0.10),
        "gemini-1.5-pro":          (1.25,   5.00),
        "gemini-1.5-flash":        (0.075,  0.30),
        "gemini-1.5-flash-8b":     (0.0375, 0.15),
    },
    "cohere": {
        "command-r-plus":       (2.50, 10.00),
        "c4ai-command-r-plus":  (2.50, 10.00),
    },
    "ollama": {
        # Local — everything is free. We list a few common slugs so
        # `is_free(model)` can short-circuit without scanning the dict.
        "llama3.3":             (0.0, 0.0),
        "llama3.2":             (0.0, 0.0),
        "llama3.1":             (0.0, 0.0),
        "qwen2.5":              (0.0, 0.0),
        "qwen2.5-coder":        (0.0, 0.0),
        "deepseek-r1":          (0.0, 0.0),
        "mistral":              (0.0, 0.0),
        "phi3":                 (0.0, 0.0),
        "gemma2":               (0.0, 0.0),
    },
    # openai_compat covers openrouter / together / any /v1/chat/completions
    # host. We don't ship their full catalogs because rates vary by
    # upstream provider — they fall through to _UNKNOWN_DEFAULT and the
    # footer prints "? · N agents" until the user picks a known model.
}


# Conservative fall-back for unknown paid models. Anchored on Opus
# pricing so a user who picks an un-catalogued model sees an upper-
# bound cost instead of "$0.00". Updated only when market shifts.
_UNKNOWN_DEFAULT: tuple[float, float] = (5.00, 15.00)


def _split_provider_model(model_str: str) -> tuple[str, str]:
    """``"anthropic/claude-sonnet-4-5"`` → ``("anthropic", "claude-sonnet-4-5")``.

    Falls back to ``("<unknown>", model_str)`` if no slash is present.
    """
    if "/" in model_str:
        provider, _, model = model_str.partition("/")
        return provider.strip().lower(), model.strip().lower()
    return "<unknown>", model_str.strip().lower()


def rates_for_model(model_str: str) -> tuple[float, float]:
    """Return ``(in_usd_per_mtok, out_usd_per_mtok)`` for ``model_str``.

    Lookup order:
      1. Exact ``provider/model`` slug match
      2. Longest-prefix match on the model slug within the provider's table
         (handles "claude-3-5-sonnet-20241022" → "claude-3-5-sonnet")
      3. ``_UNKNOWN_DEFAULT`` (Opus-class conservative bound)

    Free-tier providers (ollama, groq-with-(0,0)) return (0, 0).
    """
    provider, model = _split_provider_model(model_str)
    ptable = _PROVIDER_RATES.get(provider)
    if ptable is None:
        return _UNKNOWN_DEFAULT
    # Exact match
    if model in ptable:
        return ptable[model]
    # Longest-prefix match — important for dated slugs like
    # ``claude-3-5-sonnet-20241022``.
    matches = [slug for slug in ptable if model.startswith(slug)]
    if matches:
        longest = max(matches, key=len)
        return ptable[longest]
    return _UNKNOWN_DEFAULT


def is_free_model(model_str: str) -> bool:
    """True when the model is provably free (ollama + groq free tier)."""
    in_rate, _ = rates_for_model(model_str)
    return in_rate == 0.0


# --------------------------------------------------------------------------- #
#  Per-agent token estimates (median from real runs).
# --------------------------------------------------------------------------- #
# Calibrated against docs/runtime/.runs/20260819*/cost.json — the median
# for a STANDARD-depth f1 run is ~5 agents, each ~3.5k in / 1.5k out.
# These numbers ARE an estimate, not a bill. The actual run lands within
# 0.7-1.4× the median across the 11 f1 runs we have on disk.
_AGENT_TOKEN_ESTIMATES: dict[str, dict[str, tuple[int, int]]] = {
    "STANDARD": {
        # The five f1 agents are calibrated from real smoke runs.
        "orchestrator":         (1000,  200),
        "senior-analyst":       (3500, 1500),
        "forensic-accounting":  (4000, 2000),
        "devils-advocate":      (3500, 1500),
        "final-report":         (4500, 2500),
        # f2..f9 agents — estimates calibrated by analogy:
        # most specialists do similar work to senior-analyst / forensic-accounting.
        "comparator":           (3500, 1500),  # f2 — peer comp + thesis compare
        "earnings-preview":     (3500, 1500),  # f3
        "earnings-review":      (4000, 2000),  # f4 — print analysis
        "sector-analyst":       (4000, 2000),  # f5 — sector-pack + comps
        "thematic-screen":      (3500, 1500),  # f6
        "risk-event":           (3500, 1500),  # f7
        "stress-concentration": (3500, 1500),  # f7
        "black-swan":           (3000, 1200),  # f7
        "macro-overlay":        (4000, 2000),  # f8
        "model-build":          (4500, 2500),  # f9 — DCF/comp build (heavy)
    },
    "SCAN": {
        "orchestrator":         ( 800,  150),
        "senior-analyst":       (2500, 1000),
        "forensic-accounting":  (3000, 1500),
        "devils-advocate":      (2500, 1000),
        "final-report":         (3500, 2000),
        "comparator":           (2500, 1000),
        "earnings-preview":     (2500, 1000),
        "earnings-review":      (3000, 1500),
        "sector-analyst":       (3000, 1500),
        "thematic-screen":      (2500, 1000),
        "risk-event":           (2500, 1000),
        "stress-concentration": (2500, 1000),
        "black-swan":           (2200,  900),
        "macro-overlay":        (3000, 1500),
        "model-build":          (3500, 2000),
    },
    "DEEP": {
        "orchestrator":         (1200,  250),
        "senior-analyst":       (4500, 2000),
        "forensic-accounting":  (5500, 2500),
        "devils-advocate":      (4500, 2000),
        "final-report":         (6000, 3500),
        "comparator":           (4500, 2000),
        "earnings-preview":     (4500, 2000),
        "earnings-review":      (5500, 2500),
        "sector-analyst":       (5500, 2500),
        "thematic-screen":      (4500, 2000),
        "risk-event":           (4500, 2000),
        "stress-concentration": (4500, 2000),
        "black-swan":           (4000, 1800),
        "macro-overlay":        (5500, 2500),
        "model-build":          (6000, 3500),
    },
}

# Flow → agents invoked (in order). Used to size the estimate.
# f10 has N senior-analyst calls (one per watchlist ticker) + 1
# final-report. We model the canonical case (N=5) — estimates are
# scaled per call_agent invocation, so the footer cost is approximately
# right for watchlists of 3-10 names.
_FLOW_AGENTS: dict[str, tuple[str, ...]] = {
    "f1": (
        "orchestrator", "senior-analyst",
        "forensic-accounting", "devils-advocate",
        "final-report",
    ),
    "f2": (
        "orchestrator", "senior-analyst",
        "comparator", "final-report",
    ),
    "f3": (
        "orchestrator", "earnings-preview",
        "forensic-accounting", "devils-advocate",
        "final-report",
    ),
    "f4": (
        "orchestrator", "earnings-review",
        "forensic-accounting", "devils-advocate",
        "final-report",
    ),
    "f5": (
        "orchestrator", "sector-analyst",
        "senior-analyst", "forensic-accounting", "devils-advocate",
        "final-report",
    ),
    "f6": (
        "orchestrator", "thematic-screen",
        "senior-analyst", "devils-advocate",
        "final-report",
    ),
    "f7": (
        "orchestrator", "risk-event",
        "stress-concentration", "black-swan",
        "final-report",
    ),
    "f8": (
        "orchestrator", "macro-overlay",
        "senior-analyst", "final-report",
    ),
    "f9": (
        "orchestrator", "model-build",
        "forensic-accounting", "devils-advocate",
        "final-report",
    ),
    # f10 — N senior-analyst (one per watchlist ticker, model as 5
    # canonical) + 1 final-report.
    "f10": (
        "orchestrator",
        "senior-analyst", "senior-analyst", "senior-analyst",
        "senior-analyst", "senior-analyst",
        "final-report",
    ),
}


# --------------------------------------------------------------------------- #
#  Public API
# --------------------------------------------------------------------------- #
def estimate_run_cost(
    flow_id: str,
    model: str,
    paid_for: Iterable[str] | None = None,
    depth: str = "STANDARD",
    per_agent_model: dict[str, str] | None = None,
) -> tuple[float, int, bool]:
    """Estimate the USD cost of running ``flow_id`` once.

    Args:
        flow_id: ``f1`` ... ``f9`` (see ``_FLOW_AGENTS``).
        model: default model string (``"anthropic/claude-sonnet-4-5"``).
        paid_for: list of agent_ids routed to the paid model. Empty /
            None means everything runs on the default model.
        depth: ``SCAN`` | ``STANDARD`` | ``DEEP``.
        per_agent_model: optional explicit per-agent model overrides
            (wins over paid_for). Same shape as the runtime accepts.

    Returns:
        ``(usd, agent_count, is_free)``
        - ``usd``: estimated dollar cost (rounded to nearest $0.01 by
          the caller; this fn returns the raw float).
        - ``agent_count``: number of agent calls in this flow.
        - ``is_free``: True when every agent runs on a free model
          (ollama + groq free tier). Use this to swap the footer label
          from "≈ $0.30" → "free".

    Note: this is an *estimate*. Post-hoc, the adapter's
    ``Response.cost_usd_estimate`` is the source of truth.
    """
    agents = _FLOW_AGENTS.get(flow_id)
    if agents is None:
        # Unknown flow → fall back to STANDARD 5-agent budget.
        agents = ("orchestrator", "senior-analyst",
                  "forensic-accounting", "devils-advocate", "final-report")
    depth_table = _AGENT_TOKEN_ESTIMATES.get(depth)
    if depth_table is None:
        depth_table = _AGENT_TOKEN_ESTIMATES["STANDARD"]
    paid_for_set = set(paid_for or ())
    per_agent = per_agent_model or {}
    # Hybrid convention (mirrors docs/runtime/runtime.py:604-611):
    #   paid_for=["final-report"]       → final-report → Sonnet (paid)
    #   paid_for=["senior-analyst"]     → senior-analyst → Sonnet (paid)
    #   paid_for=["senior-analyst", "final-report"] → both → Sonnet
    #   everything else → default model (free, by user convention)
    # Per-agent override wins over both.
    hybrid_paid_model = "anthropic/claude-sonnet-4-5"
    total_usd = 0.0
    all_free = True
    for agent_id in agents:
        if agent_id in per_agent:
            agent_model = per_agent[agent_id]
        elif agent_id in paid_for_set:
            agent_model = hybrid_paid_model
        else:
            agent_model = model
        in_rate, out_rate = rates_for_model(agent_model)
        in_tok, out_tok = depth_table.get(agent_id, (3000, 1500))
        cost = (in_tok / 1_000_000.0) * in_rate + (out_tok / 1_000_000.0) * out_rate
        total_usd += cost
        if in_rate > 0.0 or out_rate > 0.0:
            all_free = False
    return (total_usd, len(agents), all_free)


# --------------------------------------------------------------------------- #
#  Footer formatter — single source of truth for the visible string.
# --------------------------------------------------------------------------- #
def format_cost_for_footer(
    flow_id: str,
    model: str,
    paid_for: Iterable[str] | None = None,
    depth: str = "STANDARD",
    per_agent_model: dict[str, str] | None = None,
) -> str:
    """Return the footer cost segment for ``"≈ $0.30 / run · 5 agents"``.

    Three output shapes:
      - free:      ``"free · 5 agents"``
      - paid:      ``"≈ $0.30 · 5 agents"``  (rounded to 2 dp; < $0.01 → "$0.00")
      - unknown:   ``"? · 5 agents"``        (model unrecognised AND not free)
    """
    usd, agent_count, is_free = estimate_run_cost(
        flow_id, model, paid_for=paid_for, depth=depth,
        per_agent_model=per_agent_model,
    )
    if is_free:
        return f"free · {agent_count} agents"
    # Detect "unknown" — we used the conservative fall-back. We can't
    # 100% tell (the unknown rate is also the Opus rate, which IS known),
    # but a conservative heuristic: if the model string isn't in any
    # provider table, fall back. The footer should say "?" so the user
    # knows the number is a guess.
    provider, model_slug = _split_provider_model(model)
    ptable = _PROVIDER_RATES.get(provider, {})
    is_known = (
        model_slug in ptable
        or any(model_slug.startswith(s) for s in ptable)
    )
    if not is_known and provider != "ollama":
        return f"? · {agent_count} agents"
    return f"≈ ${usd:.2f} · {agent_count} agents"