#!/usr/bin/env python3
"""
runtime.py — The Analyst's Bench CLI skeleton.

Usage:
    python docs/runtime/runtime.py --flow f1 --ticker NVDA --model ollama/llama3.3:70b [--paid-for final-report]
    python docs/runtime/runtime.py --flow f2 --tickers AAPL,MSFT,GOOG --model groq/llama-3.3-70b-versatile
    python docs/runtime/runtime.py --flow f6 --thesis "AI infra plays" --model ollama/qwen2.5:72b
    python docs/runtime/runtime.py --dry-run --flow f1 --ticker NVDA --model ollama/llama3.3:70b

Phase: skeleton. The shape of a working runtime; many stubs still resolve to "raise NotImplementedError".
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterator

log = logging.getLogger("labourious.runtime")

# Project root (this file lives at docs/runtime/runtime.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = PROJECT_ROOT / "docs" / "prompts"
FLOWS_DIR = PROJECT_ROOT / "docs" / "flows"
RUNS_DIR = PROJECT_ROOT / "docs" / "runtime" / ".runs"
COST_LOG = PROJECT_ROOT / "docs" / "runtime" / ".runs" / "cost.json"

# Import local modules. Prefer relative (so the agents/events classes
# resolve as `runtime.events.AgentChunk` rather than as a duplicate
# `events.AgentChunk` from a sys.path-loaded copy of the same file —
# that duplicate was the source of an isinstance-mismatch bug). Fall
# back to absolute when the script is run directly as
# `python3 docs/runtime/runtime.py ...` (no parent package).
try:
    from .adapters import get_adapter  # type: ignore
    from .thesis_register.register import ThesisRegister  # type: ignore
    from .events import (  # type: ignore  # noqa: E402  -- the event schema lives in events.py
        FlowStarted, FlowFinished, FlowFailed,
        AgentStarted, AgentChunk, AgentFinished, AgentFailed,
        ThesisPriorRead, ThesisWritten,
        CostDelta,
    )
except (ImportError, ValueError):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from adapters import get_adapter  # type: ignore
    from thesis_register.register import ThesisRegister  # type: ignore
    from events import (  # type: ignore
        FlowStarted, FlowFinished, FlowFailed,
        AgentStarted, AgentChunk, AgentFinished, AgentFailed,
        ThesisPriorRead, ThesisWritten,
        CostDelta,
    )


# --------------------------------------------------------------------------- #
# Load prompt
# --------------------------------------------------------------------------- #
def load_prompt(agent_id: str) -> str:
    """
    Resolve an agent_id to its system-prompt.md, reading the content verbatim.
    The 5 agents in the v2 roster and their canonical paths:
      - orchestrator        → docs/prompts/orchestrator/system-prompt.md
      - senior-analyst      → docs/prompts/leads/senior-analyst/system-prompt.md
      - forensic-accounting → docs/prompts/specialists/forensic-accounting/system-prompt.md
      - devils-advocate     → docs/prompts/specialists/devils-advocate/system-prompt.md
      - final-report        → docs/prompts/cross-cutting/final-report/system-prompt.md
    """
    candidates = {
        "orchestrator": PROMPTS_DIR / "orchestrator" / "system-prompt.md",
        "senior-analyst": PROMPTS_DIR / "leads" / "senior-analyst" / "system-prompt.md",
        "forensic-accounting": PROMPTS_DIR / "specialists" / "forensic-accounting" / "system-prompt.md",
        "devils-advocate": PROMPTS_DIR / "specialists" / "devils-advocate" / "system-prompt.md",
        "model-builder": PROMPTS_DIR / "leads" / "model-builder" / "system-prompt.md",
        "final-report": PROMPTS_DIR / "cross-cutting" / "final-report" / "system-prompt.md",
    }
    path = candidates.get(agent_id)
    if path is None or not path.exists():
        raise FileNotFoundError(f"Unknown agent_id: {agent_id}. Known: {list(candidates)}")
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Validate JSON envelope (V2-PROMPT-STANDARD)
# --------------------------------------------------------------------------- #
def validate_envelope(envelope: dict[str, Any], agent_id: str) -> tuple[bool, list[str]]:
    failures = []
    # Per-agent minimum required fields
    required = {
        "orchestrator": ["agent_id", "answer", "key_takeaways", "options", "evidence",
                         "activity", "confidence", "verification", "next_steps", "compressed"],
        "senior-analyst": ["agent_id", "depth", "compressed", "conclusion", "confidence",
                           "thesis", "bottom_line", "findings", "gaps", "verification",
                           "citations", "next_steps"],
        "forensic-accounting": ["agent_id", "depth", "compressed", "conclusion",
                                "confidence", "verdict", "findings", "gaps", "verification",
                                "citations", "next_steps"],
        "devils-advocate": ["agent_id", "depth", "compressed", "conclusion", "confidence",
                            "steelmanned_bull", "bear_case", "fragile_assumption",
                            "what_an_attacker_would_say", "findings", "gaps", "verification",
                            "citations", "next_steps"],
        "model-builder": ["agent_id", "ticker", "depth", "compressed", "as_of", "model",
                         "result_summary", "conclusion", "confidence",
                         "citations", "gaps", "verification"],
        "final-report": ["agent_id", "flow_id", "depth", "compressed", "memo", "confidence",
                         "gaps", "verification"],
    }
    if envelope.get("agent_id") != agent_id:
        failures.append(f"agent_id mismatch: expected {agent_id}, got {envelope.get('agent_id')}")
    for field in required.get(agent_id, []):
        if field not in envelope:
            failures.append(f"missing field: {field}")
    return (len(failures) == 0), failures


def _summarize_prior_thesis(prior: dict | list | None) -> str:
    """Render the prior thesis row as a one-line, schema-free string.

    We deliberately avoid passing the row dict itself into agent briefs:
    small local models treat any nested object as a schema to mirror,
    producing envelopes that look like a thesis row rather than the
    envelope the system prompt asks for.
    """
    if not prior:
        return "no_prior"
    if isinstance(prior, list):
        row = prior[0] if prior else None
    else:
        row = prior
    if not row or not isinstance(row, dict):
        return "no_prior"
    bl = row.get("bottom_line", {}) or {}
    if isinstance(bl, str):
        try:
            bl = json.loads(bl)
        except (json.JSONDecodeError, TypeError):
            bl = {"action": bl}
    direction = bl.get("action") or bl.get("direction") or "UNKNOWN"
    conv = bl.get("conviction") or row.get("conviction") or "?"
    txt = (row.get("thesis_text") or "")[:80]
    score = row.get("score") or "?"
    return f"v{row.get('version', '?')}={direction}/c{conv} score={score} '{txt}'"


def _extract_json_envelope(text: str) -> dict | None:
    """Defensive parser for a non-strict LLM response.

    Tries in order:
      1. Strip ```json ... ``` and ``` ... ``` code fences and parse the inside.
      2. Locate the first '{' and the matching closing '}' (respecting string
         literals and escape sequences) and parse that slice.
      3. Locate the first '[' and treat the result as a dict only if the slice
         itself is a dict (skip — we want objects only).

    Returns the parsed dict, or None if nothing usable was found. Never raises.
    """
    s = text.strip()
    # 1) fenced code block
    if s.startswith("```"):
        # find the matching closing fence
        end = s.rfind("```")
        if end > 3:
            inner = s[3:end].lstrip()
            # strip optional "json" language tag
            if inner.startswith("json"):
                inner = inner[4:].lstrip()
            elif inner.startswith("JSON"):
                inner = inner[4:].lstrip()
            try:
                obj = json.loads(inner)
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                pass

    # 2) outermost brace match (respect strings)
    depth = 0
    start = -1
    in_str = False
    escape = False
    for i, ch in enumerate(s):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    slice_ = s[start:i + 1]
                    try:
                        obj = json.loads(slice_)
                        return obj if isinstance(obj, dict) else None
                    except json.JSONDecodeError:
                        # keep scanning in case there's a larger object later
                        start = -1
                        continue
    return None


# --------------------------------------------------------------------------- #
# Example envelope (for shape-with-content priming)
# --------------------------------------------------------------------------- #
# Small (<=8B) local LLMs over-fit to "fill the keys" instead of "fill the
# content" of a JSON envelope. Empirically observed in smoke-1 with
# llama3.2:3b: every required field present, every substantive string/list
# empty. Fix: append a CONCRETE filled example at the END of the brief,
# before the JSON-only directive. The example gives the model a shape to
# copy WITH content, not just a skeleton to fill with empties.
#
# Critically: the example uses a FICTIONAL ticker ("ACME") so the model
# cannot accidentally echo or substitute it for the user's input. The
# directive explicitly tells the model to fill YOUR answer, not the example.
_EXAMPLE_TICKER = "ACME"


_EXAMPLE_ENVELOPES: dict[str, str] = {
    "orchestrator": json.dumps({
        "agent_id": "orchestrator",
        "flow_id": "f1",
        "answer": f"{_EXAMPLE_TICKER}: HOLD conviction 4/5; multiple > base, with a tight flip trigger.",
        "bottom_line": "HOLD · 4/5 · flip trigger: <= $720 OR dividend suspension.",
        "key_takeaways": [
            "Momentum-cohort correlation ~0.9 in shocks; diversification is thin.",
            "Hyperscaler tier-1 concentration is the single biggest FCF-durability risk.",
            "Bear case steelmanned: multiple expansion drove ~80% of the trailing 12-mo return.",
        ],
        "options": [
            "A: Trim 25% to fund an underweight in a cash-returning mid-cap.",
            "B: Hold core; pair-trade against sector-weakest peer.",
            "C: Maintain full position; size to your tolerance for multiple compression.",
        ],
        "evidence": [
            {"from": "senior-analyst", "claim": "Multiple is 5σ above 10y mean.", "citation": "10-K FY2026 + 10y monthly closes"},
            {"from": "forensic-accounting", "claim": "SBC drag structural.", "citation": "FY2026 10-K share-based comp note"},
        ],
        "disagreements": [
            {"issue": "Whether China export-control overhang resolves in FY25 or FY27", "parties": ["mgmt", "policy"],
             "resolution": "Bear-case risk; flip trigger on policy lapse."},
        ],
        "activity": [
            {"agent": "senior-analyst", "status": "CALLED", "note": "wave 2"},
            {"agent": "forensic-accounting", "status": "CALLED", "note": "wave 3"},
            {"agent": "devils-advocate", "status": "CALLED", "note": "wave 3"},
            {"agent": "final-report", "status": "CALLED", "note": "wave 4"},
        ],
        "confidence": "MODERATE_HIGH",
        "verification": {
            "asset_checks": [{"ticker": _EXAMPLE_TICKER, "status": "CLEAN", "note": "CIK resolved."}],
            "connector_status": [{"tool": "sec_edgar", "status": "SUCCESS", "note": "10-K retrieved"}],
            "error_flags": [],
        },
        "next_steps": ["Confirm Q4 inventory turnover; flag if gross-margin guide slips."],
        "compressed": False,
    }, indent=2),

    "senior-analyst": json.dumps({
        "agent_id": "senior-analyst",
        "depth": "STANDARD",
        "compressed": False,
        "conclusion": f"{_EXAMPLE_TICKER}: HOLD, conviction 4/5; premium to base + tight flip trigger.",
        "question_framed": f"Is {_EXAMPLE_TICKER}'s multiple commensurate with AI-capex tailwind durability?",
        "thesis": {
            "one_sentence": f"{_EXAMPLE_TICKER}'s AI franchise commands a multi-year moat but has priced in 2-3y of accelerating FCF.",
            "fragile_assumption": "Hyperscaler capex stays flat-to-up through FY27.",
            "bull_case": f"{_EXAMPLE_TICKER}'s accelerator moat is intact; FY27 capex is cash-funded; hierarchy-1 hyperscaler commitments hold.",
            "primary_source_priorities": ["10-K FY2026", "Q3 2026 10-Q", "latest transcript"],
        },
        "bear_case_from_devils_advocate": "SBC drag structural at ~12% of revenue; multiple expansion drove 80% of trailing return; China overhang unlapsed.",
        "what_an_attacker_would_say": "Multiple is 5σ above 10y mean; every prior episode ended 35-50% below.",
        "bottom_line": {"direction": "HOLD", "conviction": 4, "flip_trigger": "<= $720 OR dividend suspension OR policy lapse"},
        "next_three_questions": [
            "Is GM guidance supply- or demand-driven?",
            "Hyperscaler pull-through quarterly?",
            "H100/H200 inventory clearing?",
        ],
        "findings": [
            {"id": "f1", "source_agent": "self", "claim": "Multiple 5σ above 10y mean.", "evidence": "Monthly closes 10y.", "source": "10-K FY2026", "url": None, "as_of": "2026-08-12"},
            {"id": "f2", "source_agent": "forensic-accounting", "claim": "SBC 12% of revenue.", "evidence": "FY2024-26 SBC vs revenue.", "source": "10-K Note 14", "url": None, "as_of": "2026-08-12"},
        ],
        "tensions": [{"issue": "Inventory normalization timing", "parties": ["mgmt", "auditor"], "resolution": "Q4 print resolves."}],
        "gaps": ["Hyperscaler pull-through not retrievable.", "Inventory step-down assumed, not disclosed."],
        "verification": {
            "asset_checks": [{"ticker": _EXAMPLE_TICKER, "status": "CLEAN", "note": "ID ok"}],
            "connector_status": [{"tool": "sec_edgar", "status": "SUCCESS", "note": "10-K + 10-Q"}, {"tool": "news_8k", "status": "SUCCESS", "note": "3 8-K"}],
            "error_flags": [],
        },
        "citations": [
            {"ref": "f1", "type": "PRIMARY", "name": f"10-K FY2026 ({_EXAMPLE_TICKER})", "date": "2026-08-12", "url": f"https://www.sec.gov/.../{_EXAMPLE_TICKER}-10k"},
            {"ref": "f2", "type": "PRIMARY", "name": "10-K Note 14 SBC", "date": "2026-08-12", "url": f"https://www.sec.gov/.../{_EXAMPLE_TICKER}-10k#sbc"},
        ],
        "activity": [
            {"agent": "forensic-accounting", "status": "CALLED", "note": "wave 3"},
            {"agent": "devils-advocate", "status": "CALLED", "note": "wave 3"},
        ],
        "next_steps": ["Watch Q4 print.", "Re-run if multiple compresses 1σ."],
        "confidence": "MODERATE_HIGH",
    }, indent=2),

    "forensic-accounting": json.dumps({
        "agent_id": "forensic-accounting",
        "depth": "STANDARD",
        "compressed": False,
        "conclusion": f"{_EXAMPLE_TICKER} FLAGGED (medium): SBC drag structural; FY27 guide rests on unverified inventory step-down.",
        "confidence": "MIXED",
        "verdict": "FLAGGED",
        "findings": [
            {"id": "f1", "source_agent": "self", "claim": "SBC 12.1% of revenue, structural.", "evidence": "FY24 SBC $X bn vs revenue; peer median 5.4%.", "source": "10-K Note 14", "url": None, "as_of": "2026-08-12"},
            {"id": "f2", "source_agent": "self", "claim": "Working capital flat FY27; 5y pattern shows +5-7% build.", "evidence": "5y rolling NWC-to-revenue.", "source": "10-K MD&A", "url": None, "as_of": "2026-08-12"},
            {"id": "f3", "source_agent": "self", "claim": "Inventory normalization unverified; auditor scope covered year-end only.", "evidence": "Note 3 spans 3 pages.", "source": "FY2026 10-K", "url": None, "as_of": "2026-08-16"},
        ],
        "gaps": ["Quarterly inventory disclosed only in 10-Qs.", "SBC FY26+ policy not captured."],
        "verification": {
            "asset_checks": [{"ticker": _EXAMPLE_TICKER, "status": "CLEAN", "note": "ID ok"}],
            "connector_status": [{"tool": "sec_edgar", "status": "SUCCESS", "note": "10-K + auditor report"}],
            "error_flags": [],
        },
        "citations": [
            {"ref": "f1", "type": "PRIMARY", "name": f"10-K Note 14 ({_EXAMPLE_TICKER})", "date": "2026-08-12", "url": f"https://www.sec.gov/.../{_EXAMPLE_TICKER}-10k#sbc"},
            {"ref": "f2", "type": "PRIMARY", "name": f"10-K MD&A ({_EXAMPLE_TICKER})", "date": "2026-08-12", "url": f"https://www.sec.gov/.../{_EXAMPLE_TICKER}-10k#mda"},
        ],
        "next_steps": ["Pull Q4 liquidity.", "Compare SBC policy to MSFT/GOOGL peers."],
    }, indent=2),

    "devils-advocate": json.dumps({
        "agent_id": "devils-advocate",
        "depth": "STANDARD",
        "compressed": False,
        "conclusion": f"Steelmanned bull holds at franchise level; bear case wins on multiple basis — {_EXAMPLE_TICKER}'s premium is not earned by current FCF durability.",
        "confidence": "MODERATE_HIGH",
        "steelmanned_bull": f"{_EXAMPLE_TICKER}'s AI accelerator franchise is structurally defensible; competitive silicon narrowed the gap but didn't erase it; hyperscaler capex is the durable demand backstop.",
        "bear_case": f"{_EXAMPLE_TICKER} trades 32x forward vs 10y mean 19x; 78% of trailing 12-mo return is multiple expansion; SBC 12% of revenue is real cash drag; China overhang unlapsed.",
        "fragile_assumption": "Hyperscaler AI capex stays flat-to-up through FY27 — dip 15-20% collapses the premium in 1Q.",
        "what_an_attacker_would_say": f"Multiple 5σ above 10y mean; every prior episode ended -35-50% before fundamentals stabilized; {_EXAMPLE_TICKER} is crowded long-and-thin.",
        "base_rates": [
            {"claim": "Late-cycle growth names mean-revert 62% within 4Q post-recession onset.", "evidence": "n=14 analog set 1995-2024", "source": "regime analog set", "as_of": "2026-08-16"},
        ],
        "findings": [
            {"id": "f1", "source_agent": "self", "claim": "78% of trailing 12-mo return is multiple expansion.", "evidence": "Decomposition: 22% earnings, 78% PE.", "source": f"monthly closes + consensus EPS ({_EXAMPLE_TICKER})", "url": None, "as_of": "2026-08-16"},
            {"id": "f2", "source_agent": "self", "claim": "H200 lead times narrowing; inventory channel build.", "evidence": "3 trade-press reports.", "source": "trade press 2026-Q3", "url": None, "as_of": "2026-08-16"},
        ],
        "tensions": [{"issue": "Bull case lacks AI capex durability citation.", "parties": ["bull case", "missing citation"], "resolution": "Re-brief with hyperscaler Q3 capex data."}],
        "gaps": ["Hyperscaler GenAI ROI undisclosed.", "Channel inventory is trade-press grade."],
        "verification": {
            "asset_checks": [{"ticker": _EXAMPLE_TICKER, "status": "CLEAN", "note": "ID ok"}],
            "connector_status": [{"tool": "transcripts", "status": "SUCCESS", "note": "Q3 transcript"}],
            "error_flags": [],
        },
        "citations": [
            {"ref": "f1", "type": "SECONDARY", "name": "Trade-press digest 2026-Q3", "date": "2026-08-12", "url": None},
        ],
        "next_steps": ["Layer in 5y/10y curve regime signal from macro lead."],
    }, indent=2),

    "final-report": json.dumps({
        "agent_id": "final-report",
        "flow_id": "f1",
        "depth": "STANDARD",
        "compressed": False,
        "memo": {
            "bottom_line": {
                "direction": "HOLD",
                "conviction": 4,
                "flip_trigger": "<= $720 OR dividend suspension OR policy lapse",
                "one_liner": f"{_EXAMPLE_TICKER}: HOLD; multiple is the position, not the earnings.",
            },
            "bull_case": f"{_EXAMPLE_TICKER}'s AI moat is intact; FY27 capex is cash-funded; hyperscaler commitments hold; GM compression is supply-driven.",
            "bear_case": "78% of trailing return is multiple expansion; GenAI ROI unverified; SBC 12% real cash drag; China overhang unlapsed.",
            "what_an_attacker_would_say": f"Multiple 5σ above 10y mean; every prior episode ended -35-50% before fundamentals stabilized.",
            "next_three_questions": [
                "Is Q4 print showing inventory normalization?",
                "Hyperscaler pull-through quarterly?",
                "H100/H200 inventory clearing?",
            ],
            "citations_used": [
                {"ref": "f1", "type": "PRIMARY", "name": f"10-K FY2026 ({_EXAMPLE_TICKER})", "date": "2026-08-12", "url": f"https://www.sec.gov/.../{_EXAMPLE_TICKER}-10k"},
                {"ref": "f2", "type": "PRIMARY", "name": "Q3 2026 transcript", "date": "2026-08-16", "url": f"https://www.sec.gov/.../{_EXAMPLE_TICKER}-8k"},
            ],
        },
        "confidence": "MODERATE_HIGH",
        "gaps": ["Quarterly hyperscaler pull-through not retrieved.", "Inventory step-down disclosed only in 10-Qs."],
        "verification": {
            "asset_checks": [{"ticker": _EXAMPLE_TICKER, "status": "CLEAN", "note": "CIK ok"}],
            "connector_status": [{"tool": "sec_edgar", "status": "SUCCESS", "note": "10-K + transcript"}],
            "error_flags": [],
        },
    }, indent=2),

    "model-builder": json.dumps({
        "agent_id": "model-builder",
        "ticker": _EXAMPLE_TICKER,
        "depth": "STANDARD",
        "compressed": False,
        "as_of": "2026-08-16",
        "model": {
            "wacc": {
                "cost_of_equity": 0.1112,
                "after_tax_cost_of_debt": 0.0294,
                "wacc": 0.1079,
                "rationale": "CAPM with Damodaran implied US ERP",
            },
            "forecast": {"fcf_series": [115.5, 121.3, 127.4, 132.5, 137.8]},
            "terminal": {"perpetual_growth": 0.03, "primary_method": "gordon"},
            "sensitivity_grid_basis_points": 100,
            "sensitivity_dimensions": ["wacc", "terminal_g"],
        },
        "result_summary": {
            "dcf_intrinsic_per_share_base": 96.77,
            "dcf_intrinsic_per_share_bear": 71.20,
            "comps_implied_per_share_ev_ebitda": 215.06,
            "model_midpoint_per_share": 155.91,
            "triangulation_vs_market": "Market $195 vs DCF base $96.77 (50% premium); vs comps $215 in line.",
        },
        "conclusion": "DEFENSIBLE — DCF base respects GDP cap; bear respects sector medians.",
        "confidence": "MODERATE_HIGH",
        "citations": [
            {"name": f"10-K FY2026 CF ({_EXAMPLE_TICKER})", "type": "PRIMARY", "url": f"https://www.sec.gov/.../{_EXAMPLE_TICKER}-10k", "date": "2026-08-12"},
            {"name": "Damodaran US ERP 2026", "type": "SECONDARY", "url": "https://pages.stern.nyu.edu/~adamodar/", "date": "2026-01-15"},
        ],
        "gaps": ["10-K did not disclose segment FCF.", "Bear peers filter excluded EM-domiciled."],
        "verification": {
            "warnings": ["perpetual growth at GDP cap"],
            "checks_passed": ["WACC within 3-20% band", "share_count > 0", "FCF series positive 5Y", "sensitivity grid 5x5"],
            "asset_checks": [{"ticker": _EXAMPLE_TICKER, "status": "CLEAN", "note": "ID ok"}],
            "connector_status": [{"tool": "sec_edgar", "status": "SUCCESS", "note": "10-K CF stmt"}],
            "error_flags": [],
        },
    }, indent=2),
}


def _example_envelope_for(agent_id: str) -> str | None:
    """Return a compact, schema-complete, content-filled example envelope
    for `agent_id`. Used to prime small LLMs to fill *content*, not just
    *keys*. Returns None for unknown agents.
    """
    return _EXAMPLE_ENVELOPES.get(agent_id)


def _wrap_example_with_directive(agent_id: str) -> str:
    """Wrap an example envelope with anti-echo framing so the model copies
    the *shape* but writes *its own content* for the user's input.

    The block:
    1. Names the placeholder ticker (ACME) so the model knows the example
       is illustrative, not the user's ticker.
    2. Tells the model explicitly to substitute its own conclusions.
    3. Marks the boundary between the example and the final HARD-RULE
       directive so the JSON-only instruction still applies.
    """
    example = _example_envelope_for(agent_id)
    if not example:
        return ""
    return (
        "\n\n---\n\n"
        "BELOW IS AN EXAMPLE OF A WELL-FORMED RESPONSE for this kind of task.\n"
        "It uses the placeholder ticker 'ACME' — your answer must use the\n"
        "user's actual ticker and provide YOUR OWN analysis, not the example's content.\n"
        "Copy the SHAPE and COMPLETENESS; replace facts with yours.\n\n"
        f"```json\n{example}\n```\n"
    )


# --------------------------------------------------------------------------- #
# Call an agent
# --------------------------------------------------------------------------- #
def call_agent(
    agent_id: str,
    user_brief: str,
    model_name: str,
    paid_for: list[str] | None = None,
    emit_event: "Callable[[Any], None] | None" = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
    system_prompt_override: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Calls an agent by loading its prompt, calling the model, parsing the JSON envelope.
    Returns (envelope, cost_record).

    If `emit_event` is provided, emits AgentStarted and AgentFinished around the call.
    AgentFailed is emitted (and re-raised) on unrecoverable errors so the TUI can
    surface partial progress.

    If `stream_chunks` is True AND the adapter exposes a `.stream()` method
    (i.e., OpenAICompatAdapter for openrouter / openai / grok / cerebras /
    mistral / deepseek / etc), the connector's per-token deltas are emitted as
    individual AgentChunk events so the TUI can stream text into the bubble
    incrementally. The full text is still accumulated for envelope parsing, so
    downstream callers see the same return shape.

    Model-routing precedence (highest first):
      1. `per_agent_model[agent_id]` — explicit override from the user
         (Settings > per-agent section, or `/model <id>=<model>` syntax).
      2. `paid_for` hybrid rule — final-report → Sonnet, senior-analyst → Sonnet.
      3. `model_name` — the chat's default model.

    If `system_prompt_override` is provided, it replaces the default
    ``load_prompt(agent_id)`` for this call. Used by f5 (sector deep
    dive) to inject a sector-pack into the senior-analyst prompt at
    runtime — the pluggable policy: sectors are knowledge packs, not
    agents. Callers that pre-format the prompt (e.g. via
    ``packs.format_senior_analyst_with_pack``) pass the formatted
    string here.
    """
    if system_prompt_override is not None:
        system_prompt = system_prompt_override
    else:
        system_prompt = load_prompt(agent_id)

    # [runtime-4] Resume replay short-circuit: if the agent_id has a cached
    # envelope from a prior run that crashed and the user is resuming,
    # skip the model call and return the cached envelope. Cost is 0.0
    # because no tokens burned (and we want cumulative_cost unchanged).
    # We still emit AgentStarted + AgentFinished so the TUI / smoke sees
    # a "this agent ran" signal — the same shape as a real call would.
    if _RESUME_PARTIAL_ENVELOPES and agent_id in _RESUME_PARTIAL_ENVELOPES:
        cached = _RESUME_PARTIAL_ENVELOPES[agent_id]
        if emit_event is not None:
            try:
                effective_model = (
                    per_agent_model.get(agent_id, model_name)
                    if per_agent_model else model_name
                )
            except Exception:
                effective_model = model_name
            emit_event(AgentStarted(agent_id=agent_id,
                                    model=effective_model,
                                    depth="REPLAY",
                                    compressed=False))
            from dataclasses import is_dataclass
            if is_dataclass(cached) and not isinstance(cached, dict):
                cached_as_dict = {f.name: getattr(cached, f.name)
                                    for f in fields(cached)}
            else:
                cached_as_dict = cached
            try:
                emit_event(AgentFinished(agent_id=agent_id,
                                         envelope=cached_as_dict,
                                         wallclock_s=0.0,
                                         in_tokens=0, out_tokens=0,
                                         cost_usd_estimate=0.0))
            except TypeError:
                # Older AgentFinished signature without in_tokens/out_tokens
                try:
                    emit_event(AgentFinished(agent_id=agent_id,
                                             envelope=cached_as_dict,
                                             wallclock_s=0.0,
                                             in_tokens=0, out_tokens=0,
                                             cost_usd_estimate=0.0))
                except TypeError:
                    emit_event(AgentFinished(agent_id=agent_id,
                                             envelope=cached_as_dict,
                                             cost_usd_estimate=0.0))
        return (
            _RESUME_PARTIAL_ENVELOPES.pop(agent_id),
            {"cost_usd_estimate": 0.0},
        )

    # Append (in this order):
    # 1. Example envelope — a CONCRETE filled example for this agent with a
    #    fictional `ACME` ticker. Small (<=8B) models over-fit to "fill the
    #    keys" with empty strings; the example gives them a shape to copy
    #    WITH content. The example is wrapped with anti-echo framing.
    # 2. JSON-only directive — the hard rule that says "respond with one
    #    JSON object, no prose, no fences". Critical because the example
    #    above is itself a JSON block in a fence; the rule below
    #    *removes* the fence for the response and forbids echoing.
    example_block = _wrap_example_with_directive(agent_id)
    json_only_directive = (
        "\n\n---\n\nRESPONSE FORMAT (HARD RULE): Reply with ONE JSON object and nothing else. "
        "No prose, no markdown fences, no commentary before or after. The very first "
        "character of your reply must be `{` and the very last must be `}`. If a field "
        "is unknown, omit it rather than write null.\n\n"
        "DO NOT mirror the example above verbatim. The example uses the placeholder ticker "
        "'ACME' — your answer must use the user's actual ticker and YOUR OWN analysis. "
        "Copy the example's SHAPE and COMPLETENESS, then replace every fact with yours. "
        "Your reply shape is defined by your system prompt, NOT by nested JSON data in "
        "this brief (messages, prior-thesis rows, citation lists, connector excerpts). "
        "Strip nested-object fields down to only the keys required by your schema.")
    if user_brief:
        user_brief = user_brief + example_block + json_only_directive
    else:
        user_brief = (example_block + json_only_directive).lstrip()
    effective_model = model_name
    if per_agent_model and agent_id in per_agent_model:
        effective_model = per_agent_model[agent_id]
    elif paid_for and agent_id in paid_for:
        # Hybrid: senior-analyst -> free; final-report -> Sonnet by convention
        if agent_id == "final-report":
            effective_model = "anthropic/claude-sonnet-4-5"
        elif agent_id == "senior-analyst":
            if "anthropic" not in model_name:
                effective_model = "anthropic/claude-sonnet-4-5"
    if emit_event is not None:
        emit_event(AgentStarted(agent_id=agent_id, model=effective_model,
                                depth="STANDARD", compressed=False))
    try:
        adapter = get_adapter(effective_model)
        t0 = time.monotonic()
        text = ""
        in_tok = 0
        out_tok = 0
        cost_usd = 0.0
        if stream_chunks and hasattr(adapter, "stream"):
            # Streaming path — emit one AgentChunk per delta.
            for chunk in adapter.stream(
                messages=[{"role": "user", "content": user_brief}],
                system=system_prompt,
                options={"temperature": 0.2},
            ):
                if chunk.delta is not None:
                    # Always accumulate the delta into the envelope source —
                    # even if no emitter is hooked (e.g. a CLI pilot).
                    if chunk.delta:
                        text += chunk.delta
                    if emit_event is not None:
                        emit_event(AgentChunk(agent_id=agent_id, delta=chunk.delta))
                if chunk.usage:
                    in_tok = chunk.usage.get("prompt_tokens", 0)
                    out_tok = chunk.usage.get("completion_tokens", 0)
                    cost_usd = chunk.usage.get("cost_usd_estimate", 0.0)
        else:
            # Standard (single-shot) path — emit one AgentChunk with the full body.
            response = adapter.call(
                messages=[{"role": "user", "content": user_brief}],
                system=system_prompt,
                options={"temperature": 0.2},
            )
            text = response.text
            in_tok = response.in_tokens
            out_tok = response.out_tokens
            cost_usd = response.cost_usd_estimate
            if emit_event is not None:
                emit_event(AgentChunk(agent_id=agent_id, delta=response.text))
        wallclock = time.monotonic() - t0
        # Parse envelope. We try strict JSON first, then fall back to a
        # resilient extractor that strips code fences, leading prose,
        # and trailing commentary before locating the outermost {...}.
        envelope = None
        parse_err: Exception | None = None
        try:
            envelope = json.loads(text)
        except json.JSONDecodeError as exc:
            parse_err = exc
            envelope = _extract_json_envelope(text)
        if not isinstance(envelope, dict):
            raise RuntimeError(
                f"{agent_id} returned non-JSON: {parse_err or 'no JSON object found'}\n"
                f"Raw (first 600 chars): {text[:600]}"
            )
        # Fill in trivially-derivable defaults so small models (which often
        # omit depth/compressed/agent_id echoes) still validate. We never
        # touch substantive fields like thesis / bottom_line / findings.
        if not envelope.get("agent_id"):
            envelope["agent_id"] = agent_id
        if "depth" not in envelope or not envelope["depth"]:
            envelope["depth"] = "STANDARD"
        if "compressed" not in envelope:
            envelope["compressed"] = False
        if "confidence" not in envelope or not envelope["confidence"]:
            envelope["confidence"] = "MIXED"  # safe default; honored by validate_envelope
        ok, failures = validate_envelope(envelope, agent_id)
        if not ok:
            raise RuntimeError(f"{agent_id} envelope failed validation: {failures}")
        cost = {
            "agent_id": agent_id,
            "model": effective_model,
            "in_tokens": in_tok,
            "out_tokens": out_tok,
            "cache_hit_tokens": 0,
            "cost_usd_estimate": cost_usd,
            "wallclock_s": round(wallclock, 2),
            "as_of": dt.datetime.utcnow().isoformat() + "Z",
        }
        if emit_event is not None:
            emit_event(AgentFinished(agent_id=agent_id, envelope=envelope,
                                     wallclock_s=cost["wallclock_s"],
                                     in_tokens=in_tok,
                                     out_tokens=out_tok,
                                     cost_usd_estimate=cost_usd))
        return envelope, cost
    except Exception as exc:
        if emit_event is not None:
            emit_event(AgentFailed(agent_id=agent_id, error=str(exc)))
        raise


# --------------------------------------------------------------------------- #
# Tool-feeding: execute ``tool_directives`` from agent envelopes, plus
# pre-flight bulk pulls for every analysis run.
# --------------------------------------------------------------------------- #
# This is ``[tool-feeding]`` from docs/TODO.md, marked ✅ DONE in this
# commit. Two layers of automation:
#
#   1. ``_tool_preflight(ticker)``: before senior-analyst runs, the runtime
#      always pulls a small basket of primary sources via real connectors
#      so any 3B-8B model has data to fill its envelope with. The preflight
#      covers the connectors the LLM most commonly cites (sec_edgar for
#      CIK + recent filings, news_8k for 8-K headlines). It is silent and
#      fails soft: if a connector is unhealthy (e.g. the network is SSL-
#      intercepting in a school environment), the result is a FAILED
#      ToolResult and the LLM still proceeds with whatever did succeed.
#
#   2. ``_execute_tool_directives(directives, requested_by_agent)``: when
#      an agent emits ``tool_directives`` in its envelope (the explicit
#      ``[TOOL: ...]`` protocol from the senior-analyst prompt), the runtime
#      iterates and dispatches each via ``call_tool``. Results are added
#      to the running ``tool_results`` list and stitched into the next
#      agent's brief.
#
# Result blocks delivered to downstream agents:
#   {
#     "tool": "sec_edgar", "status": "SUCCESS", "as_of": "...", "source": "...",
#     "note": "10-K + 10-Q retrieved",
#     "data_summary": "5 filings indexed",          # <=100 char preview
#     "data": [...],                                # full ToolResult.data
#   }
#
# When connectors fail (Securly, rate-limit, 404), the LLM sees a clearly
# labelled FAILED entry instead of silent silence — so it can write the
# failure into ``gaps`` rather than hallucinate.
_MAX_PREFLIGHT_TOOL_RESULTS = 8   # brief stays clean; truncate if more
_PREFLIGHT_TIMEOUT_S = 15         # per-call; never block the flow > 15s


def _summarize_tool_result(tr: Any, max_data_chars: int = 2000) -> dict[str, Any]:
    """Compress a ToolResult into an LLM-friendly summary.

    Includes the full ``data`` field but truncated to ``max_data_chars`` so a
    long news list or filing-list does not blow the brief. The note + status
    are surfaced verbatim so the model can write them into ``gaps``.
    """
    if hasattr(tr, "to_dict"):
        d = tr.to_dict()
    elif hasattr(tr, "__dict__"):
        d = {k: v for k, v in tr.__dict__.items() if not k.startswith("_")}
    else:
        return {"status": "UNKNOWN", "data": str(tr)[:max_data_chars]}
    data = d.get("data")
    if isinstance(data, (list, dict)):
        try:
            data_str = json.dumps(data, default=str)
        except (TypeError, ValueError):
            data_str = str(data)
    else:
        data_str = str(data) if data is not None else ""
    if len(data_str) > max_data_chars:
        data_str = data_str[:max_data_chars] + "…[truncated]"
    try:
        data_obj = json.loads(data_str) if data_str.startswith(("[", "{")) else data_str
    except json.JSONDecodeError:
        data_obj = data_str
    return {
        "tool": d.get("source", "?"),
        "status": d.get("status", "UNKNOWN"),
        "as_of": d.get("as_of", ""),
        "source": d.get("source", "?"),
        "note": d.get("note", ""),
        "data": data_obj,
    }


def _tool_preflight(
    ticker: str,
    emit_event: "Callable[[Any], None] | None" = None,
) -> list[dict[str, Any]]:
    """Pre-flight: always pull a small basket of primary sources.

    The runtime owns this so the LLM never has to emit a directive to get
    core data — note this in TODO.md as the *single biggest UX win* since
    prompts go from "would be nice" to "actually happens." Connectors
    are real HTTP and free-keyless; failures are soft-FAILED in the
    brief's ``tool_results``.
    """
    # Lazy-load call_tool to avoid circular import at module load.
    if "runtime" not in sys.modules:
        _RUNTIME_PKG_PARENT = str(Path(__file__).resolve().parent.parent)
        if _RUNTIME_PKG_PARENT not in sys.path:
            sys.path.insert(0, _RUNTIME_PKG_PARENT)
        import importlib.util as _ilu
        _pkg_init = Path(__file__).resolve().parent / "__init__.py"
        if _pkg_init.exists():
            _spec = _ilu.spec_from_file_location("runtime", _pkg_init)
            _pkg = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_pkg)
            sys.modules["runtime"] = _pkg
    from runtime.call_tool import call_tool as _call_tool

    directives = [
        ("market_data", {"ticker": ticker, "period": "3mo", "interval": "1d"},
         "Recent OHLCV (yfinance) — keyless and the most reliable primary data source even through MITM proxies"),
        ("sec_edgar", {"ticker": ticker},
         "CIK + recent filings for the user's ticker — primary-source backbone for any thesis"),
        ("news_8k",   {"ticker": ticker, "since_days": 30, "limit": 5},
         "Recent 8-K filings (material events) for the user's ticker"),
        ("transcripts", {"ticker": ticker, "since_quarters": 4, "limit": 3},
         "Recent earnings-call transcripts for the user's ticker"),
    ]
    out: list[dict[str, Any]] = []
    for tool_id, args, reason in directives:
        try:
            tr = _call_tool(
                tool_id=tool_id,
                requested_by_agent="preflight",
                emit_event=emit_event,
                args=args,
            )
        except Exception as exc:
            out.append({"tool": tool_id, "status": "FAILED",
                        "as_of": "", "source": tool_id,
                        "note": f"preflight raised: {type(exc).__name__}: {exc}",
                        "data": None})
            continue
        s = _summarize_tool_result(tr)
        s["reason"] = reason
        out.append(s)
    return out[:_MAX_PREFLIGHT_TOOL_RESULTS]


def _execute_tool_directives(
    directives: list[Any],
    requested_by_agent: str,
    emit_event: "Callable[[Any], None] | None" = None,
) -> list[dict[str, Any]]:
    """Run any ``tool_directives`` an agent emitted. Each directive is a
    dict ``{tool: <id>, args: {...}, reason: str}`` (reason optional).
    Returns a list of tool-result summaries, ready to stitch into the next
    agent's brief.
    """
    if not directives:
        return []
    # Lazy-load call_tool (same trick as in _tool_preflight).
    if "runtime" not in sys.modules:
        _RUNTIME_PKG_PARENT = str(Path(__file__).resolve().parent.parent)
        if _RUNTIME_PKG_PARENT not in sys.path:
            sys.path.insert(0, _RUNTIME_PKG_PARENT)
        import importlib.util as _ilu
        _pkg_init = Path(__file__).resolve().parent / "__init__.py"
        if _pkg_init.exists():
            _spec = _ilu.spec_from_file_location("runtime", _pkg_init)
            _pkg = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_pkg)
            sys.modules["runtime"] = _pkg
    from runtime.call_tool import call_tool as _call_tool

    out: list[dict[str, Any]] = []
    # Cap how many extra pulls one envelope can trigger; falls back to
    # whatever fits in the budget. A flaky agent that emits 50 directives
    # would otherwise blow the model timeout.
    bounded = list(directives)[:_MAX_PREFLIGHT_TOOL_RESULTS]
    for d in bounded:
        if not isinstance(d, dict):
            continue
        tool_id = d.get("tool") or d.get("tool_id")
        args = d.get("args") or {}
        reason = d.get("reason", "")
        if not tool_id:
            continue
        try:
            tr = _call_tool(
                tool_id=str(tool_id),
                requested_by_agent=requested_by_agent,
                emit_event=emit_event,
                args=args if isinstance(args, dict) else {},
            )
        except Exception as exc:
            out.append({"tool": str(tool_id), "status": "FAILED",
                        "as_of": "", "source": str(tool_id),
                        "note": f"directive raised: {type(exc).__name__}: {exc}",
                        "data": None})
            continue
        s = _summarize_tool_result(tr)
        s["reason"] = reason
        out.append(s)
    return out


def _format_tool_results_for_brief(tool_results: list[dict[str, Any]]) -> str:
    """Render tool_results as a single stringified block to inject into an
    agent's user_brief. Truncates data fields so the brief stays compact.
    """
    if not tool_results:
        return ""
    lines = ["tool_results:"]
    for i, r in enumerate(tool_results, start=1):
        head = f"  [{i}] {r.get('tool','?')} status={r.get('status','?')} as_of={r.get('as_of','?')}"
        if r.get("reason"):
            head += f"   reason: {r['reason']}"
        lines.append(head)
        if r.get("note"):
            lines.append(f"      note: {r['note']}")
        data = r.get("data")
        if data:
            try:
                data_str = json.dumps(data, default=str)
            except (TypeError, ValueError):
                data_str = str(data)
            if len(data_str) > 800:
                data_str = data_str[:800] + "…[truncated]"
            for ln in data_str.splitlines():
                lines.append(f"      {ln}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Per-flow orchestrators
# --------------------------------------------------------------------------- #
def execute_flow_f1(
    ticker: str,
    model: str,
    paid_for: list[str] | None,
    emit_event: "Callable[[Any], None] | None" = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
) -> dict[str, Any]:
    """
    Flagship f1 — analyze ticker. Returns the final envelope (final-report JSON)
    and a list of per-agent cost records. Sequences:
    orchestrator → senior-analyst → forensic-accounting → devils-advocate → final-report.

    Args:
        emit_event: optional callable invoked with typed Event dataclasses around
            each agent call. main() passes None (flat output to stdout);
            run_flow_stream() passes a hook that re-yields events to the TUI.
        per_agent_model: optional dict mapping agent_id → model string. Wins
            over `paid_for` and the default `model` for any agent listed.
        stream_chunks: when True, each call_agent emits one AgentChunk per
            streamed text delta (instead of one AgentChunk with the full body).
            Backed by the adapter's `.stream()` method when available;
            AnthropicAdapter, OpenAICompatAdapter, CohereAdapter and
            GeminiAdapter all stream natively. Default False preserves the
            pre-streaming CLI contract.
    """
    register = ThesisRegister()
    prior_thesis = register.read_thesis(ticker, since_days=14)

    # Wave 1: orchestrator. We deliberately omit `relevant_history` here
    # because small models (<=8B) tend to mirror the nested thesis-row shape
    # in their response envelope. The senior-analyst carries the prior
    # thesis forward, where its output schema is self-consistent.
    orch_brief = json.dumps({
        "flow_id": "f1",
        "user_query": f"Analyze {ticker}",
        "ticker": ticker,
        "has_prior_thesis": bool(prior_thesis),
        "depth": "STANDARD",
        "compressed": False,
    })
    orch_env, orch_cost = call_agent("orchestrator", orch_brief, model,
                                     stream_chunks=stream_chunks,
                                     paid_for=paid_for, emit_event=emit_event,
                                     per_agent_model=per_agent_model)

    # Tool-feeding pre-flight: pull core primary-source data ONCE per run
    # so every downstream agent (senior, forensic, devils-advocate, final)
    # has the same facts to work from. The runtime owns this so 3B-8B
    # models don't have to emit the explicit ``tool_directives`` protocol
    # to get data; they always see it in their brief. Failures are soft —
    # we keep going with whatever succeeded.
    log.info("[f1] tool pre-flight for %s", ticker)
    preflight = _tool_preflight(ticker=ticker, emit_event=emit_event)
    tool_results: list[dict[str, Any]] = list(preflight)
    preflight_block = _format_tool_results_for_brief(tool_results)

    # Wave 2: senior-analyst. We collapse prior_thesis into a count/string
    # summary rather than passing the full row, because small models
    # (<=8B) tend to mirror nested JSON examples in their response envelope.
    # Concretely: 3B model returned the prior-thesis schema as its OUTPUT
    # when the input contained a prior-thesis-shaped field.
    sr_brief = json.dumps({
        "from": "orchestrator",
        "situation": f"User wants analysis of {ticker}",
        "task": f"Build thesis skeleton on {ticker}. Use the attached `tool_results` (raw primary sources) for every concrete claim — do NOT invent numbers, names, or dates.",
        "ticker": ticker,
        "prior_thesis_summary": _summarize_prior_thesis(prior_thesis),
        "depth": "STANDARD",
        "compressed": False,
        # Tool-feeding: the pre-flight results are appended verbatim. Agents
        # read them and produce ``tool_directives`` only when they need
        # ADDITIONAL connectors that the pre-flight didn't cover.
        "tool_results_provided": [
            {k: v for k, v in r.items() if k != "data"} | {"data_truncated": True}
            for r in tool_results
        ],
        "_tool_results_full": preflight_block,
        # Optional protocol: agent may return extra tool_directives in its
        # envelope and we will execute them post-hoc.
        "_response_protocol": (
            "If you need ADDITIONAL primary sources beyond what's already in "
            "``tool_results_provided``, emit a ``tool_directives`` list in your "
            "envelope with the shape ``[{\"tool\": \"<id>\", \"args\": {...}, "
            "\"reason\": \"...\"}, ...]``. Each will be executed via call_tool "
            "and added to the next agent's brief. Do NOT include unrelated "
            "tools — cap at ~3 directives per envelope."
        ),
    })
    sr_env, sr_cost = call_agent("senior-analyst", sr_brief, model,
                                 paid_for=paid_for, emit_event=emit_event,
                                 per_agent_model=per_agent_model,
                                 stream_chunks=stream_chunks)

    # Tool-feeding post-agent: if senior-analyst emitted any ``tool_directives``,
    # dispatch each via call_tool and append the results to ``tool_results``.
    # This is the agent-initiated extension of the pre-flight; senior analyst
    # can pull news or transcript that pre-flight didn't cover.
    sr_directives = sr_env.get("tool_directives") or []
    if isinstance(sr_directives, list) and sr_directives:
        log.info("[f1] senior-analyst emitted %d tool_directive(s)", len(sr_directives))
        extra = _execute_tool_directives(
            directives=sr_directives,
            requested_by_agent="senior-analyst",
            emit_event=emit_event,
        )
        tool_results.extend(extra)
        log.info("[f1] tool_results now has %d total entries", len(tool_results))

    # Wave 3 (parallel): forensic-accounting + devils-advocate.
    # Per `docs/flows/f1-analyze-ticker.md` the recipe calls this
    # "wave 2 (parallel): forensic + devils-advocate (parallel)". The
    # two agents are independent (devil does not consume forensic's
    # output in the upstream flow); they both feed the final-report
    # wave. Parallelism saves ~5-10s on a typical STAN4/8B speak.
    # ThreadPoolExecutor is fine here because call_agent is synchronous
    # (LLM HTTP requests are blocking); using async/await would require
    # restructuring the runtime. We pin max_workers=2 to mirror the
    # recipe's claim of "two agents one wave".
    # The tool_results block carries real-data excerpts from pre-flight + any
    # senior-analyst tool_directives. Each downstream agent reads the
    # block to inform concrete claims; agents write real numbers into their
    # envelopes, not placeholder prose.
    tool_results_block = _format_tool_results_for_brief(tool_results)
    sr_thesis = sr_env.get("thesis", {}) or {}
    fa_brief = json.dumps({
        "from": "senior-analyst",
        "task": (
            f"Earnings-quality review on {ticker}. Use the attached "
            f"``_tool_results_full`` block — pull every concrete number, "
            f"footnote, and citation from there, not from your memory."
        ),
        "ticker": ticker,
        "depth": "STANDARD",
        "compressed": False,
        "_tool_results_provided": [
            {k: v for k, v in r.items() if k != "data"} for r in tool_results
        ],
        "_tool_results_full": tool_results_block,
    })
    da_brief = json.dumps({
        "from": "senior-analyst",
        "task": (
            f"Counter-case on {ticker} thesis. Cross-check the senior "
            f"thesis against ``_tool_results_full`` — what does the "
            f"primary-source evidence actually say vs what's claimed?"
        ),
        "ticker": ticker,
        "thesis": sr_thesis,
        "depth": "STANDARD",
        "compressed": False,
        "_tool_results_provided": [
            {k: v for k, v in r.items() if k != "data"} for r in tool_results
        ],
        "_tool_results_full": tool_results_block,
    })
    fa_cost: dict[str, Any] = {}
    da_cost: dict[str, Any] = {}
    with cf.ThreadPoolExecutor(max_workers=2, thread_name_prefix="f1-wave3") as ex:
        fa_fut = ex.submit(
            call_agent, "forensic-accounting", fa_brief, model,
            paid_for=paid_for, emit_event=emit_event,
            per_agent_model=per_agent_model, stream_chunks=stream_chunks,
        )
        da_fut = ex.submit(
            call_agent, "devils-advocate", da_brief, model,
            paid_for=paid_for, emit_event=emit_event,
            per_agent_model=per_agent_model, stream_chunks=stream_chunks,
        )
        # Both results must materialize before wave 4. We collect them in
        # deterministic order — forensic first, devil second — for the
        # event log so the TUI sees a stable bubble order.
        try:
            fa_env, fa_cost = fa_fut.result()
        except Exception as exc:
            # Even if forensic fails, try to surface the devil's output
            # so the TUI shows partial work.
            try:
                da_env, da_cost = da_fut.result()
            except Exception:
                da_env, da_cost = {}, {"agent_id": "devils-advocate", "error": str(exc)}
            raise RuntimeError(
                f"forensic-accounting failed in wave 3: {type(exc).__name__}: {exc}"
            ) from exc
        try:
            da_env, da_cost = da_fut.result()
        except Exception as exc:
            da_env, da_cost = {}, {"agent_id": "devils-advocate", "error": str(exc)}

    # Wave 4: final-report
    fr_brief = json.dumps({
        "from": "senior-analyst",
        "flow_id": "f1",
        "thesis_synthesis": sr_env,
        "forensic_output": fa_env,
        "bear_case": da_env,
        "depth": "STANDARD",
        "compressed": False,
        # Tool-feeding: final-report writes the memo's citations_used list.
        # We hand it the primary-source excerpts so the in_text references
        # in ``memo.bull_case`` / ``memo.bear_case`` trace back to real
        # filings, not invented URLs. ``citations_block`` is a compact
        # ``[tool/as_of/note]`` summary used by the agent to populate
        # ``memo.citations_used``.
        "citations_block": [
            f"#{i+1}: tool={r.get('tool','?')} status={r.get('status','?')} "
            f"as_of={r.get('as_of','?')} note={(r.get('note','') or '')[:120]}"
            for i, r in enumerate(tool_results)
            if r.get("status") == "SUCCESS"
        ],
        "_tool_results_full": tool_results_block,
    })
    final_env, final_cost = call_agent("final-report", fr_brief, model,
                                       paid_for=paid_for, emit_event=emit_event,
                                       per_agent_model=per_agent_model,
                                       stream_chunks=stream_chunks)

    # Persist to thesis register. Cite REAL URLs from tool_results when the
    # LLM didn't carry its own forward; SEC URLs and any fetched 8-K links are
    # preferred citations over made-up references.
    real_urls: list[str] = []
    for r in tool_results:
        data = r.get("data")
        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict):
                    u = row.get("url") or row.get("link") or row.get("filing_url")
                    if isinstance(u, str):
                        real_urls.append(u)
    evidence_urls = (
        [c.get("url") for c in sr_env.get("citations", []) if c.get("url")]
        + real_urls
    )
    # Dedupe + cap
    seen = set(); deduped = []
    for u in evidence_urls:
        if u and u not in seen:
            seen.add(u); deduped.append(u)
    evidence_urls = deduped[:8]
    thesis_row = register.write_thesis(
        ticker=ticker,
        thesis_text=sr_env.get("thesis", {}).get("one_sentence", ""),
        conviction=sr_env.get("bottom_line", {}).get("conviction", 0),
        bottom_line=sr_env.get("bottom_line", {}),
        evidence_urls=evidence_urls,
        flow_id="f1",
    )

    # Emit the thesis-write event AFTER the final-report agent so the TUI sees
    # agents → final result → register update in the natural order.
    if emit_event is not None:
        bl = sr_env.get("bottom_line", {})
        citations = [c.get("url") for c in sr_env.get("citations", []) if c.get("url")]
        emit_event(ThesisWritten(
            ticker=ticker,
            thesis_id=thesis_row["thesis_id"],
            version=thesis_row["version"],
            thesis_text=sr_env.get("thesis", {}).get("one_sentence", ""),
            conviction=bl.get("conviction", 0) if isinstance(bl, dict) else 0,
            bottom_line=bl if isinstance(bl, dict) else {},
            evidence_urls=citations,
        ))

    return {
        "final_envelope": final_env,
        "costs": [orch_cost, sr_cost, fa_cost, da_cost, final_cost],
        "envelopes": {
            "orchestrator": orch_env,
            "senior-analyst": sr_env,
            "forensic-accounting": fa_env,
            "devils-advocate": da_env,
            "final-report": final_env,
        },
        "prior_thesis": prior_thesis,
        "thesis_row": thesis_row,
    }


# --------------------------------------------------------------------------- #
# Flow f3 — Earnings Preview (pre-mortem)
# --------------------------------------------------------------------------- #
def execute_flow_f3(
    ticker: str,
    earnings_date: str,
    model: str,
    paid_for: list[str] | None,
    emit_event: "Callable[[Any], None] | None" = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
    flow_context: dict[str, Any] | None = None,
    thesis_id: str | None = None,
    skip_devil: bool = False,
    depth: str = "SCAN",
) -> dict[str, Any]:
    """Pre-mortem on an upcoming earnings print.

    Wave plan (light, deliberately not parallel — pre-mortems work better
    when one voice owns the narrative):

      pre-wave (sequential):
        ➤ load prior thesis from register → RELEVANT HISTORY
      wave 1 (sequential):
        ➤ senior-analyst at DEPTH=SCAN — frame "what to watch"
            with prior thesis context
      wave 2 (sequential OR small parallel):
        ➤ forensic-accounting SCAN — 3 key metrics (rev growth,
            gross margin, FCF gen by default; user can override)
      wave 2b (optional): devils-advocate SCAN — bear-case plausibility
       (only if user wants the cheap "what an attacker would say" beat)
      wave 3 (sequential):
        ➤ final-report — assemble the pre-mortem memo; record a
          catalyst in the thesis_register so f4 can resolve it after
          the print

    Returns the same shape as execute_flow_f1 plus a `catalyst_id`
    field on the result so the TUI can show "watchpoint #7 created."
    """
    flow_context = flow_context or {}
    register = ThesisRegister()
    prior_thesis = register.read_thesis(ticker, since_days=14)

    # Wave 1
    sa_brief = json.dumps({
        "from": "orchestrator",
        "flow_id": "f3",
        "task": (
            f"Frame what to watch on {ticker}'s upcoming earnings "
            f"on {earnings_date}"
        ),
        "ticker": ticker,
        "earnings_date": earnings_date,
        "thesis_id": thesis_id,
        "relevant_history": prior_thesis,
        "depth": depth,
        "compressed": True,
        "flow_context": flow_context,
    })
    sa_env, sa_cost = call_agent(
        "senior-analyst", sa_brief, model,
        paid_for=paid_for, emit_event=emit_event,
        per_agent_model=per_agent_model, stream_chunks=stream_chunks,
    )

    # Wave 2 (sequential forensic — the dependencies between metrics
    # make parallelism artificial here)
    fa_brief = json.dumps({
        "from": "senior-analyst",
        "flow_id": "f3",
        "task": (
            f"Identify 3 measurable metrics for {ticker}'s print and "
            f"what 'good' vs 'bad' look like for each."
        ),
        "ticker": ticker,
        "earnings_date": earnings_date,
        "depth": "SCAN",
        "compressed": True,
    })
    fa_env, fa_cost = call_agent(
        "forensic-accounting", fa_brief, model,
        paid_for=paid_for, emit_event=emit_event,
        per_agent_model=per_agent_model, stream_chunks=stream_chunks,
    )

    da_env = None
    da_cost = None
    if not skip_devil:
        da_brief = json.dumps({
            "from": "senior-analyst",
            "flow_id": "f3",
            "task": (
                f"Bear-case plausibility check for {ticker}'s print — "
                f"what would collapse the prior thesis if it materializes?"
            ),
            "ticker": ticker,
            "earnings_date": earnings_date,
            "thesis": sa_env.get("thesis", {}),
            "depth": "SCAN",
            "compressed": True,
        })
        da_env, da_cost = call_agent(
            "devils-advocate", da_brief, model,
            paid_for=paid_for, emit_event=emit_event,
            per_agent_model=per_agent_model, stream_chunks=stream_chunks,
        )

    # Wave 3 — final-report
    fr_brief = json.dumps({
        "from": "senior-analyst",
        "flow_id": "f3",
        "earnings_date": earnings_date,
        "thesis_synthesis": sa_env,
        "forensic_output": fa_env,
        "bear_case": da_env,
        "skip_devil": skip_devil,
        "depth": depth,
        "compressed": False,
    })
    fr_env, fr_cost = call_agent(
        "final-report", fr_brief, model,
        paid_for=paid_for, emit_event=emit_event,
        per_agent_model=per_agent_model, stream_chunks=stream_chunks,
    )

    # Persist watchpoints as a catalyst row so f4 can resolve later.
    catalyst_id = None
    try:
        watchpoints = (fr_env.get("memo", {}).get("what_to_watch")
                        if isinstance(fr_env.get("memo"), dict) else None)
        watch_str = json.dumps(watchpoints) if watchpoints else f"earnings print {earnings_date}"
        catalyst_id = register.add_catalyst(
            ticker=ticker,
            event=f"earnings_print:{earnings_date}",
            expected_date=earnings_date,
            what_to_watch=watch_str,
        )
    except Exception as exc:
        # Don't fail the flow — log and move on.
        log.warning("f3: failed to register catalyst: %s", exc)

    return {
        "final_envelope": fr_env,
        "catalyst_id": catalyst_id,
        "earnings_date": earnings_date,
        "costs": [sa_cost, fa_cost, da_cost, fr_cost] if da_cost else
                  [sa_cost, fa_cost, fr_cost],
        "envelopes": {
            "senior-analyst": sa_env,
            "forensic-accounting": fa_env,
            "devils-advocate": da_env,
            "final-report": fr_env,
        },
        "prior_thesis": prior_thesis,
    }


# --------------------------------------------------------------------------- #
# Flow f4 — Earnings Review (post-mortem + diff vs prior thesis)
# --------------------------------------------------------------------------- #
def execute_flow_f4(
    ticker: str,
    earnings_date: str,
    model: str,
    paid_for: list[str] | None,
    emit_event: "Callable[[Any], None] | None" = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
    flow_context: dict[str, Any] | None = None,
    thesis_id: str | None = None,
    depth: str = "STANDARD",
) -> dict[str, Any]:
    """Post-print review. The differentiator is the **diff memo** —
    what the prior thesis said vs what we say now.

    Wave plan (heaviest single flow in v1):
      pre-wave (sequential):
        ➤ load prior thesis from register (>=14d window default)
        ➤ resolve any open catalysts at-or-before earnings_date
      wave 1 (sequential):
        ➤ senior-analyst at DEPTH=STANDARD — analyze the print, diff
            against prior
      wave 2 (sequential):
        ➤ forensic-accounting STANDARD — compare print to last quarter
            + check the 3 watchpoints from any prior f3
      wave 2b (sequential):
        ➤ devils-advocate STANDARD — did the bear case worsen?
      wave 3 (sequential):
        ➤ final-report — diff memo and the bottom_line update
      post-wave (sequential):
        ➤ write a new theses row + add_update row so the register
            reflects "we said X, now we say Y, here's why"

    Returns the same shape as f1 + a `thesis_row` field with the new
    `{thesis_id, version}` so the chat strip can flash it.
    """
    flow_context = flow_context or {}
    register = ThesisRegister()
    prior_thesis = register.read_thesis(ticker, since_days=14)

    # Resolve any open catalysts at or before this print date.
    resolved_catalysts: list[dict[str, Any]] = []
    open_catalysts: list[dict[str, Any]] = []
    try:
        cur = register._conn.cursor()
        rows = cur.execute(
            "SELECT id, event, what_to_watch, expected_date FROM catalysts "
            "WHERE ticker=? AND resolved_date IS NULL ORDER BY id",
            (ticker.upper(),),
        ).fetchall()
        for r in rows:
            if r["expected_date"] and r["expected_date"] <= earnings_date:
                # Resolve as 'pending_diff' — f4 will finalize this with
                # the diff output later.
                resolved_catalysts.append(dict(r))
            else:
                open_catalysts.append(dict(r))
    except Exception as exc:
        log.warning("f4: catalyst fetch failed: %s", exc)

    # Wave 1
    sa_brief = json.dumps({
        "from": "orchestrator",
        "flow_id": "f4",
        "task": (
            f"Analyze {ticker}'s earnings print on {earnings_date} and "
            f"diff the implications against the prior thesis."
        ),
        "ticker": ticker,
        "earnings_date": earnings_date,
        "thesis_id": thesis_id,
        "prior_thesis": prior_thesis,
        "open_catalysts": open_catalysts,
        "depth": depth,
        "compressed": False,
    })
    sa_env, sa_cost = call_agent(
        "senior-analyst", sa_brief, model,
        paid_for=paid_for, emit_event=emit_event,
        per_agent_model=per_agent_model, stream_chunks=stream_chunks,
    )

    # Wave 2 — forensic (sequential, after senior-analyst completed)
    fa_brief = json.dumps({
        "from": "senior-analyst",
        "flow_id": "f4",
        "task": (
            f"Compare {ticker}'s print to the prior quarter and to the "
            f"f3 watchpoints. Did the 3 metrics move as expected?"
        ),
        "ticker": ticker,
        "earnings_date": earnings_date,
        "depth": "STANDARD",
        "compressed": False,
    })
    fa_env, fa_cost = call_agent(
        "forensic-accounting", fa_brief, model,
        paid_for=paid_for, emit_event=emit_event,
        per_agent_model=per_agent_model, stream_chunks=stream_chunks,
    )

    # Wave 2b — devils-advocate
    da_brief = json.dumps({
        "from": "senior-analyst",
        "flow_id": "f4",
        "task": (
            f"Did the bear case for {ticker} materially improve or worsen "
            f"after the print on {earnings_date}? What is the new "
            f"fragile assumption?"
        ),
        "ticker": ticker,
        "earnings_date": earnings_date,
        "thesis": sa_env.get("thesis", {}),
        "depth": "STANDARD",
        "compressed": False,
    })
    da_env, da_cost = call_agent(
        "devils-advocate", da_brief, model,
        paid_for=paid_for, emit_event=emit_event,
        per_agent_model=per_agent_model, stream_chunks=stream_chunks,
    )

    # Wave 3 — final-report
    fr_brief = json.dumps({
        "from": "senior-analyst",
        "flow_id": "f4",
        "earnings_date": earnings_date,
        "thesis_synthesis": sa_env,
        "forensic_output": fa_env,
        "bear_case": da_env,
        "prior_thesis": prior_thesis,
        "depth": depth if depth in ("STANDARD", "DEEP") else "STANDARD",
        "compressed": False,
    })
    fr_env, fr_cost = call_agent(
        "final-report", fr_brief, model,
        paid_for=paid_for, emit_event=emit_event,
        per_agent_model=per_agent_model, stream_chunks=stream_chunks,
    )

    # Post-wave — persist the new thesis row + an update row.
    thesis_row = None
    diff_envelope = (fr_env.get("memo", {}).get("diff")
                      if isinstance(fr_env.get("memo"), dict) else None)
    new_thesis_text = sa_env.get("thesis", {}).get("one_sentence", "")
    bl = sa_env.get("bottom_line", {})
    try:
        thesis_row = register.write_thesis(
            ticker=ticker,
            thesis_text=new_thesis_text,
            conviction=int(bl.get("conviction", 0) or 3),
            bottom_line=bl if isinstance(bl, dict) else {},
            evidence_urls=[c.get("url") for c in sa_env.get("citations", [])
                              if c.get("url")],
            flow_id="f4",
        )
    except Exception as exc:
        log.warning("f4: write_thesis failed: %s", exc)
        thesis_row = None

    update_id = None
    if prior_thesis and thesis_row:
        try:
            update_id = register.add_update(
                ticker=ticker,
                what_changed=json.dumps(
                    diff_envelope or {
                        "thesis_diff": "see memo.diff",
                        "earnings_date": earnings_date,
                    }
                ),
                new_thesis_text=new_thesis_text,
                deltas=diff_envelope,
                reason=f"earnings print on {earnings_date}",
            )
        except Exception as exc:
            log.warning("f4: add_update failed: %s", exc)

    # Resolve the open catalysts (we treat all at-or-before now as
    # resolved; users can override via the memo).
    for c in resolved_catalysts:
        try:
            register.resolve_catalyst(
                c["id"], earnings_date,
                outcome=(diff_envelope or {}).get("prior_conviction_change", "")
                        or f"resolved_by_f4_{earnings_date}",
            )
        except Exception as exc:
            log.warning("f4: resolve_catalyst failed for %s: %s", c["id"], exc)

    return {
        "final_envelope": fr_env,
        "diff_envelope": diff_envelope,
        "thesis_row": thesis_row,
        "update_id": update_id,
        "earnings_date": earnings_date,
        "costs": [sa_cost, fa_cost, da_cost, fr_cost],
        "envelopes": {
            "senior-analyst": sa_env,
            "forensic-accounting": fa_env,
            "devils-advocate": da_env,
            "final-report": fr_env,
        },
        "prior_thesis": prior_thesis,
        "resolved_catalyst_ids": [c["id"] for c in resolved_catalysts],
    }


# --------------------------------------------------------------------------- #
# Flow f5 — Sector Deep-Dive (compare 5-15 names within a sector)
# --------------------------------------------------------------------------- #
def execute_flow_f5(
    sector: str,
    universe: list[str],
    model: str,
    paid_for: list[str] | None,
    emit_event: "Callable[[Any], None] | None" = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
    flow_context: dict[str, Any] | None = None,
    rubric: str | list[str] | dict[str, float] | None = None,
    depth: str = "SCAN",
) -> dict[str, Any]:
    """Sector landscape — f2 scaled out. 5-15 tickers, sector context,
    comparator at the end. Same machinery, wider window.

    Wave plan:
      pre-wave (sequential):
        ➤ orchestrator (or CLI --rubric) sets the comparison rubric.
          Default: balanced 6D since "(sector name) winners" is harder
          to encode than "(ticker) winners" — the agent prompts tell
          the user to be specific about the lens.
      wave 1 (parallel fan-out via ThreadPoolExecutor):
        ➤ for each ticker in universe:
              senior-analyst SCAN — "1-line thesis + sector-position"
              devils-advocate SCAN — "1-line bear + sector-position"
              (both share agent_id="<topic>-{ticker}" so the TUI
              bubble remains distinct)
      wave 2 (sequential):
        ➤ comparator (quant_comparator tool) — weighted rank + sensitivity
      wave 3 (sequential):
        ➤ final-report — cross-name memo + sector landscape summary
          + capital-flow commentary + ranked picks
    """
    flow_context = flow_context or {}
    universe = [t.strip().upper() for t in universe if t.strip()]
    if len(universe) < 5:
        raise ValueError(
            f"f5 requires at least 5 tickers in `universe`; got {len(universe)}. "
            f"For fewer, use f2 (compare 2-5)."
        )
    if len(universe) > 15:
        raise ValueError(
            f"f5 caps the universe at 15 names; got {len(universe)}. "
            f"For wider searches, use f6 (thematic screen)."
        )

    # ----------------------------------------------------------------
    # Pluggable sector-pack (pluggable policy: sectors are knowledge
    # packs, not agents.). The senior-analyst prompt accepts a pack
    # body appended under its `{sector_pack}` placeholder; no new
    # agent is created. The pack is identified two ways:
    #
    #   1. explicit slug in `flow_context["sector_pack_slug"]`
    #   2. auto-match against the universe tickers (highest overlap)
    #
    # If both fail (no overlap, no slug), the senior-analyst runs as
    # a generalist and the placeholder carries a stub.
    # ----------------------------------------------------------------
    from runtime.packs import (
        auto_match_pack, format_senior_analyst_with_pack, load_pack,
    )
    explicit_slug = ((flow_context or {}).get("sector_pack_slug") or "").strip()
    explicit_pack = load_pack(explicit_slug) if explicit_slug else None
    auto_match = auto_match_pack(universe)
    chosen_pack = explicit_pack or (auto_match.pack if auto_match else None)
    if chosen_pack is None:
        log.warning(
            "f5: no sector pack matched universe=%s sector_context=%s; "
            "running as generalist.",
            universe, explicit_slug or None,
        )
    base_sa_prompt = load_prompt("senior-analyst")
    sector_pa_prompt = format_senior_analyst_with_pack(base_sa_prompt, chosen_pack)
    if chosen_pack is not None:
        log.info(
            "f5: sector pack loaded slug=%s matched=%s overlap=%.2f",
            chosen_pack.meta.slug,
            auto_match.matched_tickers if auto_match else "(explicit)",
            auto_match.overlap_pct if auto_match else 1.0,
        )

    # Wave 1 — parallel fan-out
    per_ticker_buffers: dict[str, list[Any]] = {t: [] for t in universe}
    per_ticker_results: dict[str, dict[str, Any]] = {}

    def _run_pair(tiker: str) -> dict[str, Any]:
        sa_id = f"senior-analyst-{tiker}"
        da_id = f"devils-advocate-{tiker}"
        local_buf: list[Any] = []

        def _le(ev: Any) -> None:
            local_buf.append(ev)
            if emit_event is not None:
                emit_event(ev)

        sa_brief = json.dumps({
            "from": "orchestrator",
            "flow_id": "f5",
            "task": (f"1-sentence thesis + sector-position claim for "
                     f"{tiker} within {sector}"),
            "ticker": tiker, "sector": sector,
            "depth": "SCAN", "compressed": True,
            "flow_context": flow_context,
        })
        da_brief = json.dumps({
            "from": "senior-analyst",
            "flow_id": "f5",
            "task": (f"1-sentence bear + sector-position claim for "
                     f"{tiker} within {sector}"),
            "ticker": tiker, "sector": sector,
            "depth": "SCAN", "compressed": True,
        })
        sa_env, sa_cost = call_agent(
            "senior-analyst", sa_brief, model,
            paid_for=paid_for, emit_event=_le,
            per_agent_model=per_agent_model, stream_chunks=stream_chunks,
        ) if not _run_pair.__name__ == "__main__" else ({}, {})
        try:
            sa_env, sa_cost = call_agent(
                "senior-analyst", sa_brief, model,
                paid_for=paid_for, emit_event=_le,
                per_agent_model=per_agent_model, stream_chunks=stream_chunks,
                system_prompt_override=sector_pa_prompt,
            )
        except Exception as exc:
            sa_env = {"agent_id": sa_id, "ticker": tiker, "depth": "SCAN",
                      "compressed": True, "conclusion": f"failed: {exc}",
                      "thesis": {"one_sentence": "unreachable"},
                      "bottom_line": {"direction": "ABSTAIN", "conviction": 0,
                                      "flip_trigger": "n/a"},
                      "findings": [], "gaps": [str(exc)],
                      "citations": [], "verification": {"warnings": [str(exc)]}}
            sa_cost = {"cost_usd_estimate": 0.0}
        try:
            da_env, da_cost = call_agent(
                "devils-advocate", da_brief, model,
                paid_for=paid_for, emit_event=_le,
                per_agent_model=per_agent_model, stream_chunks=stream_chunks,
            )
        except Exception as exc:
            da_env = {"agent_id": da_id, "ticker": tiker, "depth": "SCAN",
                      "compressed": True, "conclusion": f"failed: {exc}",
                      "bottom_line": {"direction": "ABSTAIN"},
                      "bear_case": "unreachable", "fragile_assumption": "",
                      "what_an_attacker_would_say": "",
                      "findings": [], "gaps": [str(exc)],
                      "citations": [], "verification": {"warnings": [str(exc)]}}
            da_cost = {"cost_usd_estimate": 0.0}
        sa_env = {**sa_env, "agent_id": sa_id}
        da_env = {**da_env, "agent_id": da_id}
        per_ticker_buffers[tiker] = local_buf
        return {"ticker": tiker, "sa_env": sa_env, "da_env": da_env,
                "sa_cost": sa_cost, "da_cost": da_cost}

    max_workers = min(len(universe), 8)
    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(_run_pair, t): t for t in universe
        }
        for fut in cf.as_completed(future_to_ticker):
            ticker = future_to_ticker[fut]
            try:
                per_ticker_results[ticker] = fut.result()
            except Exception as exc:
                per_ticker_results[ticker] = {
                    "ticker": ticker, "sa_env": {}, "da_env": {},
                    "sa_cost": {"cost_usd_estimate": 0.0},
                    "da_cost": {"cost_usd_estimate": 0.0},
                }

    # Wave 2 — comparator (deterministic Python)
    comparator_input = {"rubric": rubric, "tickers": []}
    for t in universe:
        sa = per_ticker_results[t]["sa_env"]
        bl = sa.get("bottom_line", {})
        comparator_input["tickers"].append({
            "ticker": t,
            "direction": bl.get("direction", "ABSTAIN"),
            "conviction": int(bl.get("conviction", 0) or 3),
            "dimensions": sa.get("dimensions", {}),
            "quant": sa.get("quant", {}),
            "citations": sa.get("citations", []),
            "thesis_one_sentence": sa.get("thesis", {}).get("one_sentence", ""),
        })

    from .call_tool import call_tool as _runtime_call_tool  # avoid cycle

    comparator_output = {"error": None, "tickers_present": len(universe)}
    try:
        ct = _runtime_call_tool(
            "quant_comparator",
            requested_by_agent="comparator",
            emit_event=emit_event,
            args=comparator_input,
        )
        and_data = ct.data or {"error": ct.note}
        comparator_output = (ct.data or {"error": ct.note})
    except Exception as exc:
        log.warning("f5: comparator failed: %s", exc)
        comparator_output = {"error": str(exc), "tickers_present": len(universe)}

    # Wave 3 — final-report
    fr_brief = json.dumps({
        "from": "comparator",
        "flow_id": "f5",
        "task": f"Sector landscape memo on {sector}",
        "sector": sector,
        "universe": universe,
        "rubric": rubric,
        "per_ticker_envelopes": {
            t: {"senior-analyst": per_ticker_results[t]["sa_env"],
                "devils-advocate": per_ticker_results[t]["da_env"]}
            for t in universe
        },
        "comparator_output": comparator_output,
        "depth": depth,
        "compressed": False,
    })
    fr_env, fr_cost = call_agent(
        "final-report", fr_brief, model,
        paid_for=paid_for, emit_event=emit_event,
        per_agent_model=per_agent_model, stream_chunks=stream_chunks,
    )

    return {
        "final_envelope": fr_env,
        "comparator_output": comparator_output,
        "sector": sector,
        "universe": universe,
        "costs": [per_ticker_results[t]["sa_cost"]
                   for t in universe]
                  + [per_ticker_results[t]["da_cost"] for t in universe]
                  + [fr_cost],
        "envelopes": {
            "per_ticker": {t: per_ticker_results[t] for t in universe},
            "final-report": fr_env,
        },
    }


# --------------------------------------------------------------------------- #
# Flow f6 — Thematic Screen (thesis → shortlist of STRONG_FIT names)
# --------------------------------------------------------------------------- #
def execute_flow_f6(
    thesis: str,
    seed_universe: list[str],
    model: str,
    paid_for: list[str] | None,
    emit_event: "Callable[[Any], None] | None" = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
    flow_context: dict[str, Any] | None = None,
    max_universe: int = 30,
    shortlist_size: int = 10,
    depth_screen: str = "SCAN",
    depth_shortlist: str = "STANDARD",
) -> dict[str, Any]:
    """Two-pass thematic screen. Cheap SCAN on a candidate universe,
    prune, STANDARD on survivors, comparator, final-report.
    The two-pass design is the cost optimization.

    Wave plan:
      pre-wave (sequential):
        ➤ orchestrator takes the user's thesis verbatim and the
          seed_universe (capped at max_universe)
      wave 1 (parallel fan-out):
        ➤ for each candidate in seed_universe (cap max_universe):
              senior-analyst at DEPTH=SCAN — verdict
                STRONG_FIT | WEAK_FIT | NO_FIT
              devils-advocate at DEPTH=SCAN — single bear flag
              (only STRONG_FIT and WEAK_FIT proceed; NO_FIT don't
               get the second agent)
      wave 2 (parallel fan-out over survivors):
        ➤ for each top-K survivor:
              senior-analyst at DEPTH=STANDARD — 1-line thesis + fit-revised
              forensic-accounting at DEPTH=STANDARD — headline financials
              devils-advocate at DEPTH=STANDARD — one bear flag
      wave 3 (sequential):
        ➤ comparator — ranks survivors by fit-rationale on the
          derived 6D vector
        ➤ final-report — ranked list with fit-rationale + cross-name memo
    """
    flow_context = flow_context or {}
    seed_universe = [t.strip().upper() for t in seed_universe if t.strip()]
    if not seed_universe:
        raise ValueError("f6 requires non-empty `seed_universe`")
    if len(seed_universe) > max_universe:
        raise ValueError(
            f"f6 caps seed_universe at {max_universe}; got {len(seed_universe)}."
        )

    # Pass 1: cheap SCAN over seed_universe
    wave1_buffers: dict[str, list[Any]] = {t: [] for t in seed_universe}
    wave1_results: dict[str, dict[str, Any]] = {}

    def _scan_one(tiker: str) -> dict[str, Any]:
        sa_id = f"senior-analyst-{tiker}-screen"
        buf: list[Any] = []

        def _le(ev: Any) -> None:
            buf.append(ev)
            if emit_event is not None:
                emit_event(ev)

        brief = json.dumps({
            "from": "orchestrator",
            "flow_id": "f6",
            "task": (f"Verdict on whether {tiker} fits the thesis: "
                     f"{thesis}"),
            "ticker": tiker, "thesis": thesis,
            "depth": depth_screen, "compressed": True,
            "flow_context": flow_context,
        })
        try:
            env, cost = call_agent(
                "senior-analyst", brief, model,
                paid_for=paid_for, emit_event=_le,
                per_agent_model=per_agent_model, stream_chunks=stream_chunks,
            )
        except Exception as exc:
            env = {"agent_id": sa_id, "ticker": tiker, "depth": depth_screen,
                   "compressed": True, "conclusion": f"failed: {exc}",
                   "thesis": {"one_sentence": "unreachable"},
                   "bottom_line": {"direction": "ABSTAIN", "conviction": 0,
                                   "flip_trigger": "n/a"},
                   "findings": [], "gaps": [str(exc)],
                   "citations": [], "verification": {"warnings": [str(exc)]}}
            cost = {"cost_usd_estimate": 0.0}
        env = {**env, "agent_id": sa_id}
        # Read verdict from bottom_line OR a top-level `verdict` field.
        verdict = env.get("verdict") or env.get("bottom_line", {}).get(
            "direction", "ABSTAIN")
        return {"ticker": tiker, "sa_env": env, "sa_cost": cost,
                "verdict": verdict}

    max_workers = min(len(seed_universe), 8)
    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(_scan_one, t): t for t in seed_universe
        }
        for fut in cf.as_completed(future_to_ticker):
            ticker = future_to_ticker[fut]
            try:
                wave1_results[ticker] = fut.result()
            except Exception as exc:
                wave1_results[ticker] = {"ticker": ticker, "sa_env": {},
                                          "sa_cost": {"cost_usd_estimate": 0.0},
                                          "verdict": "NO_FIT"}

    # Rank by verdict_score: STRONG_FIT > WEAK_FIT > NO_FIT (tiebreak: conviction)
    verdict_score = {"STRONG_FIT": 3, "BUY": 3, "WEAK_FIT": 2, "HOLD": 2,
                       "NO_FIT": 1, "SELL": 1, "ABSTAIN": 0}
    ranked = sorted(
        wave1_results.values(),
        key=lambda r: (verdict_score.get(str(r["verdict"]).upper(), 0),
                       int((r["sa_env"].get("bottom_line", {}) or {}).get("conviction", 0))),
        reverse=True,
    )
    shortlist = [r["ticker"] for r in ranked[:shortlist_size]]

    # Pass 2: STANDARD over shortlist
    scan_buf_per_ticker: dict[str, list[Any]] = {t: [] for t in shortlist}
    wave2_results: dict[str, dict[str, Any]] = {}

    def _standard_one(tiker: str) -> dict[str, Any]:
        buf: list[Any] = []

        def _le(ev: Any) -> None:
            buf.append(ev)
            if emit_event is not None:
                emit_event(ev)

        short_env: dict = {}
        da_env: dict = {}
        try:
            sa_brief = json.dumps({
                "from": "senior-analyst",
                "flow_id": "f6",
                "task": (f"Full shortlist analysis: {tiker} re: thesis "
                         f"{thesis}"),
                "ticker": tiker, "thesis": thesis,
                "depth": depth_shortlist, "compressed": False,
                "flow_context": flow_context,
            })
            short_env, _c1 = call_agent(
                "senior-analyst", sa_brief, model, paid_for=paid_for,
                emit_event=_le, per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
            )
        except Exception as exc:
            short_env = {"agent_id": f"senior-analyst-{tiker}",
                         "conclusion": f"failed: {exc}"}
        try:
            fa_brief = json.dumps({
                "from": "senior-analyst",
                "flow_id": "f6",
                "task": f"Headline financials on {tiker}",
                "ticker": tiker,
                "depth": depth_shortlist, "compressed": False,
            })
            fa_env, _c2 = call_agent(
                "forensic-accounting", fa_brief, model, paid_for=paid_for,
                emit_event=_le, per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
            )
        except Exception as exc:
            fa_env = {"agent_id": "forensic-accounting",
                      "conclusion": f"failed: {exc}"}
        try:
            da_brief = json.dumps({
                "from": "senior-analyst",
                "flow_id": "f6",
                "task": f"One bear flag for {tiker} re: thesis {thesis}",
                "ticker": tiker, "thesis": thesis,
                "depth": depth_shortlist, "compressed": False,
            })
            da_env, _c3 = call_agent(
                "devils-advocate", da_brief, model, paid_for=paid_for,
                emit_event=_le, per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
            )
        except Exception as exc:
            da_env = {"agent_id": "devils-advocate",
                      "conclusion": f"failed: {exc}"}
        short_env = {**short_env, "agent_id": f"senior-analyst-{tiker}"}
        fa_env = {**fa_env, "agent_id": f"forensic-accounting-{tiker}"}
        da_env = {**da_env, "agent_id": f"devils-advocate-{tiker}"}
        return {"ticker": tiker, "sa_env": short_env, "fa_env": fa_env,
                "da_env": da_env}

    if shortlist:
        max_workers2 = min(len(shortlist), 5)
        with cf.ThreadPoolExecutor(max_workers=max_workers2) as executor:
            future_to_ticker = {
                executor.submit(_standard_one, t): t for t in shortlist
            }
            for fut in cf.as_completed(future_to_ticker):
                ticker = future_to_ticker[fut]
                try:
                    wave2_results[ticker] = fut.result()
                except Exception as exc:
                    wave2_results[ticker] = {"ticker": ticker, "sa_env": {},
                                              "fa_env": {}, "da_env": {}}

    # Wave 3 — comparator + final-report on the shortlist
    comparator_input = {"rubric": None, "tickers": []}
    for t in shortlist:
        sa = wave2_results[t]["sa_env"]
        bl = sa.get("bottom_line", {})
        comparator_input["tickers"].append({
            "ticker": t,
            "direction": bl.get("direction", "ABSTAIN"),
            "conviction": int(bl.get("conviction", 0) or 3),
            "dimensions": sa.get("dimensions", {}),
            "quant": sa.get("quant", {}),
            "citations": sa.get("citations", []),
        })

    comparator_output: dict = {"error": None, "tickers_present": len(shortlist)}
    try:
        from .call_tool import call_tool as _runtime_call_tool
        ct = _runtime_call_tool(
            "quant_comparator", requested_by_agent="comparator",
            emit_event=emit_event, args=comparator_input)
        comparator_output = (ct.data or {"error": ct.note})
    except Exception as exc:
        log.warning("f6: comparator failed: %s", exc)

    fr_brief = json.dumps({
        "from": "comparator", "flow_id": "f6",
        "thesis": thesis, "shortlist": shortlist,
        "wave1_results": {t: wave1_results[t] for t in seed_universe},
        "wave2_results": {t: wave2_results[t] for t in shortlist},
        "comparator_output": comparator_output,
        "depth": depth_shortlist, "compressed": False,
    })
    fr_env, fr_cost = call_agent(
        "final-report", fr_brief, model, paid_for=paid_for,
        emit_event=emit_event, per_agent_model=per_agent_model,
        stream_chunks=stream_chunks,
    )

    return {
        "final_envelope": fr_env,
        "comparator_output": comparator_output,
        "thesis": thesis,
        "seed_universe": seed_universe,
        "shortlist": shortlist,
        "costs": [v["sa_cost"] for v in wave1_results.values()]
                  + [fr_cost],
        "envelopes": {
            "wave1_results": wave1_results,
            "wave2_results": wave2_results,
            "final-report": fr_env,
        },
    }


# --------------------------------------------------------------------------- #
# Flow f7 — Risk Event (same-day action)
# --------------------------------------------------------------------------- #
def execute_flow_f7(
    event: str,
    exposed_tickers: list[str],
    model: str,
    paid_for: list[str] | None,
    emit_event: "Callable[[Any], None] | None" = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
    flow_context: dict[str, Any] | None = None,
    event_horizon: str = "1-4 weeks",
    depth: str = "SCAN",
) -> dict[str, Any]:
    """Same-day news/event reaction. Speed-priority. SCAN depth through
    all agents to keep wallclock low.

    Wave plan:
      wave 1 (sequential):
        ➤ senior-analyst SCAN — frame the event (systemic vs idiosyncratic,
            reversible vs durable, magnitude class)
      wave 2 (parallel):
        ➤ forensic-accounting SCAN per exposed ticker — "does the
            event change the financials?"
        ➤ devils-advocate SCAN — "market over- vs under-reacting?"
      wave 3 (sequential):
        ➤ final-report — exposure map + duration + action options

    Optionally calls `quant_dcf` (cheap, optional) to compute implied
    price moves if the event is a macro shock with quant inputs.
    """
    flow_context = flow_context or {}
    exposed_tickers = [t.strip().upper() for t in exposed_tickers if t.strip()]
    if not exposed_tickers:
        raise ValueError("f7 requires non-empty `exposed_tickers`")

    # Wave 1 — event framing
    sa_brief = json.dumps({
        "from": "orchestrator",
        "flow_id": "f7",
        "task": (f"Frame the event: {event}; classify it as systemic or "
                 f"idiosyncratic; reversible or durable; magnitude class "
                 f"(LOW/MED/HIGH); typical horizon."),
        "event": event, "exposed_tickers": exposed_tickers,
        "event_horizon": event_horizon,
        "depth": "SCAN", "compressed": True,
        "flow_context": flow_context,
    })
    sa_env, sa_cost = call_agent(
        "senior-analyst", sa_brief, model, paid_for=paid_for,
        emit_event=emit_event, per_agent_model=per_agent_model,
        stream_chunks=stream_chunks,
    )

    # Wave 2 — parallel per-ticker forensic + devils-advocate counter
    wave2_buffers: dict[str, list[Any]] = {t: [] for t in exposed_tickers}
    wave2_results: dict[str, dict[str, Any]] = {}

    def _per_ticker(tiker: str) -> dict[str, Any]:
        buf: list[Any] = []

        def _le(ev: Any) -> None:
            buf.append(ev)
            if emit_event is not None:
                emit_event(ev)

        try:
            fa_brief = json.dumps({
                "from": "senior-analyst", "flow_id": "f7",
                "task": (f"Does event '{event}' materially change the "
                         f"financials of {tiker}? 1-line answer."),
                "ticker": tiker, "event": event,
                "event_horizon": event_horizon,
                "depth": "SCAN", "compressed": True,
            })
            fa_env, fa_cost = call_agent(
                "forensic-accounting", fa_brief, model, paid_for=paid_for,
                emit_event=_le, per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
            )
        except Exception as exc:
            fa_env = {"agent_id": "forensic-accounting",
                      "conclusion": f"failed: {exc}"}
            fa_cost = {"cost_usd_estimate": 0.0}
        try:
            da_brief = json.dumps({
                "from": "senior-analyst", "flow_id": "f7",
                "task": (f"Is the market over- or under-reacting event "
                         f"'{event}' on {tiker}? 1-line answer."),
                "ticker": tiker, "event": event,
                "event_horizon": event_horizon,
                "depth": "SCAN", "compressed": True,
            })
            da_env, da_cost = call_agent(
                "devils-advocate", da_brief, model, paid_for=paid_for,
                emit_event=_le, per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
            )
        except Exception as exc:
            da_env = {"agent_id": "devils-advocate",
                      "conclusion": f"failed: {exc}"}
            da_cost = {"cost_usd_estimate": 0.0}
        fa_env = {**fa_env, "agent_id": f"forensic-accounting-{tiker}"}
        da_env = {**da_env, "agent_id": f"devils-advocate-{tiker}"}
        return {"ticker": tiker, "fa_env": fa_env, "da_env": da_env,
                "fa_cost": fa_cost, "da_cost": da_cost}

    max_workers = min(len(exposed_tickers), 5)
    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(_per_ticker, t): t for t in exposed_tickers
        }
        for fut in cf.as_completed(future_to_ticker):
            ticker = future_to_ticker[fut]
            try:
                wave2_results[ticker] = fut.result()
            except Exception as exc:
                wave2_results[ticker] = {"ticker": ticker, "fa_env": {},
                                           "da_env": {},
                                           "fa_cost": {"cost_usd_estimate": 0.0},
                                           "da_cost": {"cost_usd_estimate": 0.0}}

    # Wave 3 — final-report
    fr_brief = json.dumps({
        "from": "senior-analyst", "flow_id": "f7",
        "task": f"Risk event memo on: {event}",
        "event": event, "exposed_tickers": exposed_tickers,
        "event_horizon": event_horizon,
        "event_framing": sa_env,
        "wave2_results": {t: wave2_results[t] for t in exposed_tickers},
        "depth": depth, "compressed": True,
    })
    fr_env, fr_cost = call_agent(
        "final-report", fr_brief, model, paid_for=paid_for,
        emit_event=emit_event, per_agent_model=per_agent_model,
        stream_chunks=stream_chunks,
    )

    return {
        "final_envelope": fr_env,
        "event": event,
        "exposed_tickers": exposed_tickers,
        "event_framing": sa_env,
        "costs": [sa_cost] +
                  [wave2_results[t]["fa_cost"] for t in exposed_tickers] +
                  [wave2_results[t]["da_cost"] for t in exposed_tickers] +
                  [fr_cost],
        "envelopes": {
            "senior-analyst": sa_env,
            "wave2_results": wave2_results,
            "final-report": fr_env,
        },
    }


# --------------------------------------------------------------------------- #
# Flow f8 — Macro Overlay (existing portfolio + new macro event)
# --------------------------------------------------------------------------- #
def execute_flow_f8(
    macro_shock: str,
    thesis_ids: list[int],
    model: str,
    paid_for: list[str] | None,
    emit_event: "Callable[[Any], None] | None" = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
    flow_context: dict[str, Any] | None = None,
    horizon: str = "6m",
    depth: str = "STANDARD",
) -> dict[str, Any]:
    """For each thesis in the register, ask: does this macro change the
    thesis? Output is per-thesis vulnerability + portfolio-level memo.

    Wave plan:
      pre-wave (sequential):
        ➤ load each thesis by id from register; build per-thesis
          fragility vector
      wave 1 (parallel):
        ➤ per thesis: senior-analyst STANDARD — reassess under macro
        ➤ per thesis: devils-advocate STANDARD — does the thesis break?
      wave 2 (sequential):
        ➤ aggregator — portfolio-level weights shift
        ➤ final-report — per-thesis + portfolio memo
    """
    flow_context = flow_context or {}
    if not thesis_ids:
        raise ValueError("f8 requires a non-empty `thesis_ids` list")
    register = ThesisRegister()
    theses: dict[int, dict[str, Any]] = {}
    for tid in thesis_ids:
        try:
            row = register._conn.execute(
                "SELECT * FROM theses WHERE id=?", (tid,)
            ).fetchone()
            if row is not None:
                theses[tid] = dict(row)
        except Exception as exc:
            log.warning("f8: thesis %s fetch failed: %s", tid, exc)

    if not theses:
        log.warning("f8: no theses resolved")

    # Wave 1 — per-thesis parallel senior + devil under macro
    buffers: dict[int, list[Any]] = {tid: [] for tid in theses}
    results: dict[int, dict[str, Any]] = {}

    def _per_thesis(tid: int) -> dict[str, Any]:
        thesis_row = theses[tid]
        buf: list[Any] = []

        def _le(ev: Any) -> None:
            buf.append(ev)
            if emit_event is not None:
                emit_event(ev)

        try:
            sa_brief = json.dumps({
                "from": "orchestrator", "flow_id": "f8",
                "task": (f"Reassess thesis #{tid} ({thesis_row['ticker']}) "
                         f"under macro shock: {macro_shock}"),
                "ticker": thesis_row["ticker"],
                "thesis_id": tid,
                "macro_shock": macro_shock, "horizon": horizon,
                "prior_thesis": thesis_row,
                "depth": "STANDARD", "compressed": False,
            })
            sa_env, sa_cost = call_agent(
                "senior-analyst", sa_brief, model, paid_for=paid_for,
                emit_event=_le, per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
            )
        except Exception as exc:
            sa_env = {"agent_id": "senior-analyst",
                      "conclusion": f"failed: {exc}"}
            sa_cost = {"cost_usd_estimate": 0.0}
        try:
            da_brief = json.dumps({
                "from": "senior-analyst", "flow_id": "f8",
                "task": (f"Does the macro shock: {macro_shock} break "
                         f"thesis #{tid} ({thesis_row['ticker']})?"),
                "ticker": thesis_row["ticker"],
                "macro_shock": macro_shock, "horizon": horizon,
                "depth": "STANDARD", "compressed": False,
            })
            da_env, da_cost = call_agent(
                "devils-advocate", da_brief, model, paid_for=paid_for,
                emit_event=_le, per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
            )
        except Exception as exc:
            da_env = {"agent_id": "devils-advocate",
                      "conclusion": f"failed: {exc}"}
            da_cost = {"cost_usd_estimate": 0.0}
        sa_env = {**sa_env, "agent_id": f"senior-analyst-{tid}"}
        da_env = {**da_env, "agent_id": f"devils-advocate-{tid}"}
        return {"thesis_id": tid, "sa_env": sa_env, "da_env": da_env,
                "sa_cost": sa_cost, "da_cost": da_cost}

    if theses:
        max_workers = min(len(theses), 5)
        with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_tid = {
                executor.submit(_per_thesis, tid): tid for tid in theses
            }
            for fut in cf.as_completed(future_to_tid):
                tid = future_to_tid[fut]
                try:
                    results[tid] = fut.result()
                except Exception as exc:
                    results[tid] = {"thesis_id": tid, "sa_env": {},
                                     "da_env": {},
                                     "sa_cost": {"cost_usd_estimate": 0.0},
                                     "da_cost": {"cost_usd_estimate": 0.0}}

    # Wave 2 — final-report
    fr_brief = json.dumps({
        "from": "senior-analyst", "flow_id": "f8",
        "task": f"Macro overlay on portfolio of {len(theses)} theses: {macro_shock}",
        "macro_shock": macro_shock, "horizon": horizon,
        "thesis_ids": thesis_ids,
        "prior_theses": theses,
        "per_thesis_results": results,
        "depth": depth, "compressed": False,
    })
    fr_env, fr_cost = call_agent(
        "final-report", fr_brief, model, paid_for=paid_for,
        emit_event=emit_event, per_agent_model=per_agent_model,
        stream_chunks=stream_chunks,
    )

    return {
        "final_envelope": fr_env,
        "macro_shock": macro_shock,
        "thesis_ids": thesis_ids,
        "horizon": horizon,
        "costs": [results[t]["sa_cost"] for t in theses] +
                  [results[t]["da_cost"] for t in theses] +
                  [fr_cost],
        "envelopes": {
            "prior_theses": theses,
            "per_thesis_results": results,
            "final-report": fr_env,
        },
    }


# --------------------------------------------------------------------------- #
# Flow f9 — Model Build (DCF + comps)
# --------------------------------------------------------------------------- #
def execute_flow_f9(
    ticker: str,
    model: str,
    paid_for: list[str] | None,
    emit_event: "Callable[[Any], None] | None" = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
    flow_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """DCF + comps model build. The math runs deterministically in
    `runtime.tools.dcf` and `runtime.tools.comps`; the agent layer's job
    is to populate the inputs (WACC, FCF projections, comps set) with
    cited, defensible numbers and emit the model envelope.

    Wave plan (zero parallelism — single analyst in the loop is intentional):
      wave 1: senior-analyst   → frames the thesis so the model is thesis-aware
      wave 2: model-builder    → parametric envelope (this is what gets quoted)
      wave 3: devils-advocate  → attacks the inputs (β, growth, comps set)
      wave 4: final-report     → memo with model summary

    Note: parallelism is intentionally NOT used here — DCF is a
    serial-sensitivity exercise where the comps come AFTER the DCF is
    built to triangulate. Concurrent waves would produce inconsistent
    per-share values.
    """
    flow_context = flow_context or {}

    # Wave 1: senior-analyst (thesis frame)
    sa_brief = json.dumps({
        "from": "orchestrator",
        "flow_id": "f9",
        "task": f"Frame thesis for DCF + comps model on {ticker}",
        "ticker": ticker,
        "depth": "STANDARD",
        "compressed": False,
        "flow_context": flow_context,
    })
    sa_env, sa_cost = call_agent("senior-analyst", sa_brief, model,
                                  paid_for=paid_for, emit_event=emit_event,
                                  per_agent_model=per_agent_model,
                                  stream_chunks=stream_chunks)

    # Wave 2: model-builder — envelope
    mb_brief = json.dumps({
        "from": "senior-analyst",
        "flow_id": "f9",
        "task": f"Build DCF + comps model on {ticker}",
        "ticker": ticker,
        "thesis_synthesis": sa_env,
        "depth": "STANDARD",
        "compressed": False,
        "as_of": dt.datetime.utcnow().isoformat() + "Z",
    })
    mb_env, mb_cost = call_agent("model-builder", mb_brief, model,
                                  paid_for=paid_for, emit_event=emit_event,
                                  per_agent_model=per_agent_model,
                                  stream_chunks=stream_chunks)

    # Wave 3: devils-advocate — attacks the model inputs
    da_brief = json.dumps({
        "from": "model-builder",
        "flow_id": "f9",
        "task": f"Attack the DCF + comps model on {ticker}",
        "ticker": ticker,
        "thesis": sa_env.get("thesis", {}),
        "model_envelope": mb_env,
        "depth": "STANDARD",
        "compressed": False,
    })
    da_env, da_cost = call_agent("devils-advocate", da_brief, model,
                                  paid_for=paid_for, emit_event=emit_event,
                                  per_agent_model=per_agent_model,
                                  stream_chunks=stream_chunks)

    # Wave 4: final-report — memo with the model summary
    fr_brief = json.dumps({
        "from": "model-builder",
        "flow_id": "f9",
        "thesis_synthesis": sa_env,
        "model_envelope": mb_env,
        "bear_case": da_env,
        "depth": "STANDARD",
        "compressed": False,
    })
    fr_env, fr_cost = call_agent("final-report", fr_brief, model,
                                  paid_for=paid_for, emit_event=emit_event,
                                  per_agent_model=per_agent_model,
                                  stream_chunks=stream_chunks)

    return {
        "final_envelope": fr_env,
        "model_envelope": mb_env,
        "costs": [sa_cost, mb_cost, da_cost, fr_cost],
        "envelopes": {
            "senior-analyst": sa_env,
            "model-builder": mb_env,
            "devils-advocate": da_env,
            "final-report": fr_env,
        },
    }


# --------------------------------------------------------------------------- #
# Flow f10 — Daily Briefing (watchlist re-check)
# --------------------------------------------------------------------------- #
def execute_flow_f10(
    watchlist: list[str],
    model: str,
    paid_for: list[str] | None,
    emit_event: "Callable[[Any], None] | None" = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
    flow_context: dict[str, Any] | None = None,
    since_days: int = 1,
    depth: str = "SCAN",
) -> dict[str, Any]:
    """Daily watchlist briefing — f1 batched at scale.

    For every ticker in `watchlist`, compares today's read against the
    prior thesis stored in `thesis_register` and tags the result as one
    of three states:

      REITERATE — no material change; the prior thesis still holds.
      UPDATE    — something meaningful shifted, but the directional
                  view is intact. The user should re-read the memo
                  today; nothing's broken.
      FLIP      — material change; the prior thesis is now wrong.
                  Auto-writes an `updates` row to thesis_register so
                  f4 (earnings review) and future f10 runs see it.

    The flow is intentionally cheap: SCAN depth per ticker, a single
    final-report to combine the per-ticker paragraphs. A 5-name
    watchlist costs ≈ $0.06 on Haiku, free on Ollama.

    Wave plan:
      pre-wave (sequential, IO-bound):
        ➤ for each ticker in watchlist:
              thesis_register.read_thesis(ticker, since_days=since_days * 7)
              tag as "with_prior" or "no_prior" based on result
        ➤ fetch open catalysts from thesis_register.list_open_catalysts
      wave 1 (parallel fan-out via ThreadPoolExecutor):
        ➤ for each ticker with a prior thesis:
              senior-analyst (DEPTH=SCAN) — "what changed since <last_update>?"
              brief carries: prior thesis text + bottom_line + last_update_date
              + days_since + watchpoint list
              emits tag ∈ {REITERATE, UPDATE, FLIP}
      wave 2 (sequential):
        ➤ final-report — assemble per-ticker sections into a single memo
      post-flow:
        ➤ for any FLIP: thesis_register.add_update(ticker, what_changed, reason)

    Returns the same envelope shape as f1 plus ``f10_briefing`` (the
    per-ticker tagged summary) at the top level.
    """
    flow_context = flow_context or {}
    watchlist = [t.strip().upper() for t in watchlist if t.strip()]
    if not watchlist:
        raise ValueError(
            "f10 requires a non-empty `watchlist`; got 0 tickers. "
            "Pass --watchlist NVDA,AAPL,MSFT or set Config.watchlist."
        )
    if len(watchlist) > 20:
        raise ValueError(
            f"f10 caps the watchlist at 20 names; got {len(watchlist)}. "
            "For wider universes, narrow via a thematic screen (f6) first."
        )

    register = ThesisRegister()
    # Pre-wave: per-ticker prior-thesis lookup.
    prior_by_ticker: dict[str, dict | None] = {}
    for t in watchlist:
        # Read with a wider window so the brief has the "since when" context.
        rows = register.read_thesis(t, since_days=max(since_days * 7, 7))
        prior_by_ticker[t] = rows[0] if rows else None

    # Open catalysts across the watchlist (deterministic pull from the DB).
    open_catalysts: list[dict] = []
    for t in watchlist:
        for cat in register.list_open_catalysts(t):
            open_catalysts.append({"ticker": t, **cat})

    # Wave 1 — parallel fan-out, one senior-analyst per ticker with a prior.
    per_ticker_buffers: dict[str, list[Any]] = {t: [] for t in watchlist}
    per_ticker_envelopes: dict[str, dict[str, Any]] = {}

    def _run_one(tiker: str) -> dict[str, Any]:
        local_buf: list[Any] = []
        def _le(ev: Any) -> None:
            local_buf.append(ev)
            if emit_event is not None:
                emit_event(ev)
        prior = prior_by_ticker[tiker]
        sa_id = f"senior-analyst-{tiker}"
        if prior is None:
            # No prior thesis — still emit an envelope so the final-report
            # can list this ticker under the "no prior" section. The brief
            # asks for an empty read + an "onboard" recommendation.
            try:
                env, cost = call_agent(
                    "senior-analyst", json.dumps({
                        "from": "orchestrator",
                        "flow_id": "f10",
                        "task": (
                            f"No prior thesis for {tiker}. Emit a placeholder "
                            f"envelope with tag='NO_PRIOR' and a one-sentence "
                            f"recommendation to onboard via `analyze {tiker}`."
                        ),
                        "ticker": tiker,
                        "depth": "SCAN",
                        "compressed": True,
                    }), model,
                    paid_for=paid_for, emit_event=_le,
                    per_agent_model=per_agent_model,
                    stream_chunks=stream_chunks,
                )
            except Exception as exc:
                env = {"agent_id": sa_id, "ticker": tiker, "depth": "SCAN",
                       "compressed": True, "conclusion": f"failed: {exc}",
                       "tag": "NO_PRIOR"}
                cost = {"agent_id": sa_id, "in_tok": 0, "out_tok": 0,
                        "cost_usd_estimate": 0.0}
            per_ticker_buffers[tiker] = local_buf
            per_ticker_envelopes[tiker] = env
            return {"env": env, "cost": cost, "events": local_buf}

        # Has a prior — brief the senior-analyst with everything.
        last_update = prior.get("date", "unknown")
        days_since = (dt.date.today() - dt.date.fromisoformat(last_update)).days \
            if last_update != "unknown" else None
        try:
            env, cost = call_agent(
                "senior-analyst", json.dumps({
                    "from": "orchestrator",
                    "flow_id": "f10",
                    "task": (
                        f"Re-check {tiker} vs the prior thesis. "
                        f"Classify as REITERATE | UPDATE | FLIP and emit "
                        f"one-paragraph read + tag + tag_reason."
                    ),
                    "ticker": tiker,
                    "prior_thesis": prior,
                    "prior_thesis_text": prior.get("thesis_text", ""),
                    "prior_bottom_line": prior.get("bottom_line", {}),
                    "prior_conviction": prior.get("conviction"),
                    "last_update_date": last_update,
                    "days_since_prior": days_since,
                    "since_days": since_days,
                    "depth": depth,
                    "compressed": True,
                    "flow_context": flow_context,
                }), model,
                paid_for=paid_for, emit_event=_le,
                per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
            )
        except Exception as exc:
            env = {"agent_id": sa_id, "ticker": tiker, "depth": depth,
                   "compressed": True, "conclusion": f"failed: {exc}",
                   "tag": "ERROR"}
            cost = {"agent_id": sa_id, "in_tok": 0, "out_tok": 0,
                    "cost_usd_estimate": 0.0}
        per_ticker_buffers[tiker] = local_buf
        per_ticker_envelopes[tiker] = env
        return {"env": env, "cost": cost, "events": local_buf}

    # Fan out with a thread pool sized to the watchlist (cap 10 workers).
    import concurrent.futures as _cf
    pool_workers = min(max(len(watchlist), 1), 10)
    results: list[dict[str, Any]] = []
    with _cf.ThreadPoolExecutor(max_workers=pool_workers) as ex:
        futures = {ex.submit(_run_one, t): t for t in watchlist}
        for fut in _cf.as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                tiker = futures[fut]
                # Surface as an error envelope so final-report can list it.
                per_ticker_envelopes[tiker] = {
                    "agent_id": f"senior-analyst-{tiker}",
                    "ticker": tiker, "depth": depth, "compressed": True,
                    "conclusion": f"f10 fan-out failed: {exc}",
                    "tag": "ERROR",
                }

    # Wave 2 — final-report assembly.
    fr_brief = json.dumps({
        "from": "orchestrator",
        "flow_id": "f10",
        "task": (
            "Assemble the daily briefing memo. Sections in order: "
            "Header (counts), FLIP block (one paragraph each), UPDATE block, "
            "REITERATE block (one sentence each), No-prior section, "
            "Watchpoints, then a single-line Bottom Line."
        ),
        "watchlist": watchlist,
        "per_ticker": per_ticker_envelopes,
        "open_catalysts": open_catalysts,
        "since_days": since_days,
        "depth": depth,
        "compressed": True,
    })
    fr_env, fr_cost = call_agent(
        "final-report", fr_brief, model,
        paid_for=paid_for, emit_event=emit_event,
        per_agent_model=per_agent_model,
        stream_chunks=stream_chunks,
    )

    # Post-flow: auto-write `updates` rows for any FLIP-tagged ticker.
    flips_written: list[dict[str, Any]] = []
    for tiker, env in per_ticker_envelopes.items():
        tag = (env.get("tag") or "").upper()
        if tag == "FLIP" and prior_by_ticker.get(tiker) is not None:
            try:
                what_changed = (
                    env.get("what_changed")
                    or env.get("read")
                    or env.get("conclusion")
                    or "f10 auto-detected material change"
                )
                update_id = register.add_update(
                    ticker=tiker,
                    what_changed=str(what_changed)[:500],
                    reason="auto: f10 daily briefing tagged FLIP",
                )
                flips_written.append({
                    "ticker": tiker,
                    "update_id": update_id,
                    "what_changed": str(what_changed)[:500],
                })
            except Exception:
                # Don't fail the whole flow on a register write error;
                # the user can re-run f10 to retry, or f1 to write manually.
                pass

    # Cost rollup.
    costs: list[dict[str, Any]] = [r["cost"] for r in results]
    costs.append(fr_cost)

    # Attach the per-ticker summary at the top level for downstream consumers.
    f10_briefing = {
        "watchlist": watchlist,
        "since_days": since_days,
        "per_ticker": per_ticker_envelopes,
        "open_catalysts": open_catalysts,
        "flips_written": flips_written,
    }

    return {
        "final_envelope": fr_env,
        "f10_briefing": f10_briefing,
        "costs": costs,
        "envelopes": {
            **per_ticker_envelopes,
            "final-report": fr_env,
        },
    }


# --------------------------------------------------------------------------- #
# Flow f2 — Compare Tickers (concurrent fan-out + comparator)
# --------------------------------------------------------------------------- #
def execute_flow_f2(
    tickers: list[str],
    model: str,
    paid_for: list[str] | None,
    emit_event: "Callable[[Any], None] | None" = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
    flow_context: dict[str, Any] | None = None,
    rubric: str | list[str] | dict[str, float] | None = None,
    depth: str = "SCAN",
) -> dict[str, Any]:
    """Compare N tickers (2–5). Multi-agent fan-out per Anthropic's pattern:
    one senior-analyst agent per ticker in its own context, in parallel;
    then a deterministic comparator aggregates.

    Wave plan:
      pre-wave (sequential):
        ➤ orchestrator confirms tickers + rubric (or sets balanced default)
      wave 1 (parallel fan-out via ThreadPoolExecutor):
        ➤ for each ticker (concurrent.futures):
              senior-analyst (DEPTH=SCAN by default) — emits per-ticker
              bubble under agent_id="senior-analyst-{ticker}" so the TUI
              row is distinct, not clobbered by the single-name version
      wave 2 (sequential, deterministic):
        ➤ comparator (quant_comparator tool) — weighted rank + sensitivity
      wave 3 (sequential):
        ➤ final-report — builds the comparison table + ranking + bear
          case on the top pick

    The parallelism is critical because Anthropic's multi-agent paper
    shows breadth-first tasks like this earn the 15× token cost only
    with concurrent execution. Threads (not processes) because adapters
    are mostly HTTP and GIL is irrelevant.
    """
    flow_context = flow_context or {}
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    if len(tickers) < 2:
        raise ValueError(f"f2 requires at least 2 tickers; got {len(tickers)}")
    if len(tickers) > 5:
        # Soft cap — comparison table doesn't scale past ~5 cleanly.
        raise ValueError(
            f"f2 accepts 2-5 tickers for comparison; got {len(tickers)}. "
            f"For wider universe, use f5 (sector landscape) or f6 (screen)."
        )

    # Per-ticker agent_ids so the chat strip can mount distinct bubbles.
    per_ticker_agents = [f"senior-analyst-{t}" for t in tickers]

    # ---- Wave 1: parallel fan-out ----
    # Each thread has its own emit buffer; events merge after join.
    per_ticker_buffers: dict[str, list[Any]] = {t: [] for t in tickers}
    per_ticker_results: dict[str, dict[str, Any]] = {}

    def _run_senior_for_ticker(ticker: str) -> dict[str, Any]:
        agent_id = f"senior-analyst-{ticker}"
        # Sub-emit hook that tags events with this agent so events land
        # on the right bubble when merged.
        local_buffer: list[Any] = []

        def _local_emit(ev: Any) -> None:
            # Re-anchor AgentStarted/Chunk/Finished to this ticker's id
            # already set by call_agent. The chat handler reads .agent_id
            # so we just collect.
            local_buffer.append(ev)
            # Also bubble up to the outer emit_event so the user sees
            # streaming progress in real-time when supported.
            if emit_event is not None:
                emit_event(ev)

        brief = json.dumps({
            "from": "orchestrator",
            "flow_id": "f2",
            "task": f"Frame a 1-sentence SCAN-depth thesis + 4-5 dimension signals on {ticker}",
            "ticker": ticker,
            "rubric": rubric,                # pass rubric as hint for the dimensions dict
            "depth": depth,
            "compressed": True,              # keep fan-out cheap
            "flow_context": flow_context,
        })
        try:
            env, cost = call_agent(
                "senior-analyst", brief, model,
                paid_for=paid_for,
                emit_event=_local_emit,
                per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
            )
        except Exception as exc:
            return {
                "ticker": ticker,
                "agent_id": agent_id,
                "envelope": {
                    "agent_id": agent_id,
                    "ticker": ticker,
                    "conclusion": f"SENIOR-ANALYST FAILED: {exc}",
                    "thesis": {"one_sentence": f"Failed to analyze {ticker}: {exc}"},
                    "bottom_line": {"direction": "ABSTAIN", "conviction": 0,
                                    "flip_trigger": "n/a"},
                    "findings": [], "gaps": [str(exc)], "verification": {"warnings": [str(exc)]},
                    "citations": [],
                },
                "cost": {"cost_usd_estimate": 0.0},
            }
        # Re-tag agent_id so the comparator + final-report can use it.
        env = {**env, "agent_id": agent_id}
        per_ticker_buffers[ticker] = local_buffer
        return {"ticker": ticker, "agent_id": agent_id,
                "envelope": env, "cost": cost}

    max_workers = min(len(tickers), 5)
    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(_run_senior_for_ticker, t): t for t in tickers
        }
        for fut in cf.as_completed(future_to_ticker):
            ticker = future_to_ticker[fut]
            try:
                per_ticker_results[ticker] = fut.result()
            except Exception as exc:  # should not — _run_senior_for_ticker catches
                per_ticker_results[ticker] = {
                    "ticker": ticker,
                    "agent_id": f"senior-analyst-{ticker}",
                    "envelope": {
                        "agent_id": f"senior-analyst-{ticker}",
                        "ticker": ticker,
                        "conclusion": f"THREAD FAILED: {exc}",
                        "thesis": {"one_sentence": "unreachable"},
                        "bottom_line": {"direction": "ABSTAIN", "conviction": 0,
                                        "flip_trigger": "n/a"},
                        "findings": [], "gaps": [str(exc)], "verification": {"warnings": [str(exc)]},
                        "citations": [],
                    },
                    "cost": {"cost_usd_estimate": 0.0},
                }

    # ---- Wave 2: comparator (deterministic Python) ----
    # Populate comparator input from each ticker's senior-analyst output.
    # Senior-analyst is expected to emit a `dimensions` block and optional
    # `quant` block; otherwise comparator falls back to qualitative-only.
    comparator_input: dict[str, Any] = {"rubric": rubric, "tickers": []}
    for t in tickers:
        env = per_ticker_results[t]["envelope"]
        bottom = env.get("bottom_line", {})
        # Best-effort extract: comparator handles missing fields gracefully.
        comparator_input["tickers"].append({
            "ticker": t,
            "direction": bottom.get("direction", "ABSTAIN"),
            "conviction": int(bottom.get("conviction", 0) or 3),
            "dimensions": env.get("dimensions", {}),
            "quant": env.get("quant", {}),
            "citations": env.get("citations", []),
            "thesis_one_sentence": env.get("thesis", {}).get("one_sentence", ""),
            "fragile_assumption": env.get("thesis", {}).get("fragile_assumption", ""),
        })

    # Use the runtime.call_tool path so chat strip lights up
    # (this also gives us free ConnectorRequested/Completed events).
    from .call_tool import call_tool as _runtime_call_tool  # late import to avoid cycle

    events_comparator: list[Any] = []

    def _com_em(ev: Any) -> None:
        events_comparator.append(ev)
        if emit_event is not None:
            emit_event(ev)

    ct_result = _runtime_call_tool(
        "quant_comparator",
        requested_by_agent="comparator",  # not a real agent id; chat ignores unknown
        emit_event=_com_em,
        args=comparator_input,
    )

    comparator_output = ct_result.data or {"error": ct_result.note, "tickers_present": len(tickers)}

    # ---- Wave 3: final-report memo ----
    fr_brief = json.dumps({
        "from": "comparator",
        "flow_id": "f2",
        "task": f"Compare {len(tickers)} tickers with rubric and produce a memo",
        "tickers": tickers,
        "rubric": rubric,
        "per_ticker_envelopes": {t: per_ticker_results[t]["envelope"] for t in tickers},
        "comparator_output": comparator_output,
        "depth": depth,
        "compressed": False,
    })
    fr_env, fr_cost = call_agent(
        "final-report", fr_brief, model,
        paid_for=paid_for,
        emit_event=emit_event,
        per_agent_model=per_agent_model,
        stream_chunks=stream_chunks,
    )

    costs = [per_ticker_results[t]["cost"] for t in tickers]
    costs.append(comparator_output)
    costs.append(fr_cost)

    return {
        "final_envelope": fr_env,
        "comparator_output": comparator_output,
        "costs": costs,
        "envelopes": {
            "per_ticker": {t: per_ticker_results[t]["envelope"] for t in tickers},
            "final-report": fr_env,
        },
    }


# --------------------------------------------------------------------------- #
# Streaming entrypoint — what the TUI consumes (PROTOCOL.md §1)
# --------------------------------------------------------------------------- #
def run_flow_stream(
    flow_id: str,
    inputs: dict[str, Any],
    model: str,
    paid_for: list[str] | None = None,
    per_agent_model: dict[str, str] | None = None,
    stream_chunks: bool = False,
) -> Iterator[Any]:
    """
    Yield typed `Event` dataclasses as a flow progresses.

    Currently only `f1` is implemented; other flows raise NotImplementedError.

    The same business logic in `execute_flow_f1` runs (we pass it an `emit_event`
    callback), so this function never diverges from the CLI behaviour. New flows
    should add a corresponding `execute_flow_<id>` first, then a thin generator
    wrapper here that emits FlowStarted/ThesisPriorRead → per-agent → FlowFinished.

    `per_agent_model` (optional) maps agent_id → model string and is forwarded
    into `call_agent` for per-agent model routing.

    `stream_chunks` (optional) propagates down to `execute_flow_f1` → each
    `call_agent`. When True, every streamed text delta becomes its own
    AgentChunk event in the yield stream — the TUI consumes them and
    updates each agent's bubble incrementally. Default False preserves
    the pre-streaming CLI contract where each agent emits ONE chunk with
    the full body.
    """
    if flow_id not in ("f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9"):
        raise NotImplementedError(
            f"run_flow_stream: flow '{flow_id}' is not implemented yet. "
            f"All 8 base flows + f9 are wired in v1; add execute_flow_<flow_id> first."
        )

    # [runtime-4] Resume load: when inputs["resume_run_id"] is supplied,
    # pre-load the per-agent envelope cache from that prior run. Every
    # agent_id written under .runs/<resume_run_id>/agents/*.json becomes
    # replayable. ``resume_from`` (optional) names the agent AFTER which
    # we want fresh runs; agents at-or-after that id run normally. When
    # ``resume_from`` is omitted, every cached agent is replayed and
    # only later agents run (a "review the partial work without going
    # further" mode).
    global _RESUME_PARTIAL_ENVELOPES, _RESUME_FROM_RUN_ID
    prior_run_id = (inputs.get("resume_run_id") or "").strip()
    resume_from = (inputs.get("resume_from") or "").strip()
    if prior_run_id:
        loaded = load_prior_resume_envelopes(prior_run_id)
        # If `--resume-from <agent>` is supplied, drop agents at or
        # after that anchor from the replay set.
        if resume_from and resume_from in loaded:
            cutoff = sorted(loaded.keys()).index(resume_from)
            loaded = {k: v for i, (k, v) in enumerate(
                sorted(loaded.items())) if i < cutoff}
        _RESUME_PARTIAL_ENVELOPES = loaded
        _RESUME_FROM_RUN_ID = prior_run_id
        if loaded:
            print(f"# resume: replay {len(loaded)} cached agent envelopes "
                  f"from {prior_run_id} (anchor={'at ' + resume_from if resume_from else 'no fresh runs'}); "
                  f"agents: {','.join(sorted(loaded.keys()))}",
                  file=sys.stderr)
    else:
        _RESUME_PARTIAL_ENVELOPES = {}
        _RESUME_FROM_RUN_ID = ""

    ticker = inputs.get("ticker", "")  # cohort flows (f5/f6) often omit single ticker
    paid_for = paid_for or []
    cumulative_in = 0
    cumulative_out = 0
    cumulative_cost = 0.0

    yield FlowStarted(
        flow_id=flow_id,
        tickers=[ticker],
        ticker_join=ticker,
        thesis_register_snapshot=[],  # filled in below before the next yield
        depth=inputs.get("depth", "STANDARD"),
        compressed=inputs.get("compressed", False),
    )

    # Persist a snapshot of prior theses for the TUI's history diff.
    register = ThesisRegister()
    prior = register.read_thesis(ticker, since_days=14)
    yield ThesisPriorRead(ticker=ticker, prior_theses=prior)

    partial: dict[str, dict[str, Any]] = {}

    def emit(ev: Any) -> None:
        """Hook passed into execute_flow_f1 → call_agent. Wraps AgentFinished
        with a CostDelta so the TUI sidebar updates as each agent completes.
        Also persists the per-agent envelope to disk for [runtime-4] resume."""
        nonlocal cumulative_in, cumulative_out, cumulative_cost
        if isinstance(ev, AgentFinished):
            cumulative_in += ev.in_tokens
            cumulative_out += ev.out_tokens
            cumulative_cost += ev.cost_usd_estimate
            events_out.append(ev)
            events_out.append(CostDelta(
                agent_id=ev.agent_id,
                in_tokens=ev.in_tokens,
                out_tokens=ev.out_tokens,
                cost_usd_estimate=ev.cost_usd_estimate,
                cumulative_in=cumulative_in,
                cumulative_out=cumulative_out,
                cumulative_cost=cumulative_cost,
            ))
            partial[ev.agent_id] = ev.envelope
            # Persist the per-agent envelope to disk so a future
            # `--resume-from <agent>` call can replay from this point.
            # (If we got here because the agent was REPLAYED from a
            # prior cache rather than freshly invoked, ``envelope``
            # carries the cached envelope — it's safe to persist
            # idempotently over the disk copy. But our cache-handling
            # in call_agent pops the entry out instead of re-saving,
            # so the disk copy stays canonical.)
            if run_id:
                _persist_agent_envelope(run_id, ev.agent_id, ev.envelope)
        else:
            events_out.append(ev)

    # Use a list + drain pattern so generator semantics stay simple.
    events_out: list[Any] = []

    try:
        if flow_id == "f9":
            flow_ctx = inputs.get("flow_context") or {}
            result = execute_flow_f9(
                ticker=ticker,
                model=model,
                paid_for=paid_for,
                emit_event=emit,
                per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
                flow_context=flow_ctx,
            )
        elif flow_id == "f3":
            earnings_date = inputs.get("earnings_date") or "1900-01-01"  # placeholder
            if earnings_date == "1900-01-01":
                log.warning("f3: no --earnings-date supplied; using placeholder")
            result = execute_flow_f3(
                ticker=ticker,
                earnings_date=earnings_date,
                model=model,
                paid_for=paid_for,
                emit_event=emit,
                per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
                flow_context=inputs.get("flow_context") or {},
                thesis_id=inputs.get("thesis_id"),
                skip_devil=inputs.get("skip_devil", False),
                depth=inputs.get("depth", "SCAN"),
            )
        elif flow_id == "f4":
            earnings_date = inputs.get("earnings_date") or "1900-01-01"  # placeholder
            if earnings_date == "1900-01-01":
                log.warning("f4: no --earnings-date supplied; using placeholder")
            result = execute_flow_f4(
                ticker=ticker,
                earnings_date=earnings_date,
                model=model,
                paid_for=paid_for,
                emit_event=emit,
                per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
                flow_context=inputs.get("flow_context") or {},
                thesis_id=inputs.get("thesis_id"),
                depth=inputs.get("depth", "STANDARD"),
            )
        elif flow_id == "f2":
            tickers = inputs.get("tickers") or [ticker] if ticker else []
            result = execute_flow_f2(
                tickers=tickers,
                model=model,
                paid_for=paid_for,
                emit_event=emit,
                per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
                flow_context=inputs.get("flow_context") or {},
                rubric=inputs.get("rubric"),
                depth=inputs.get("depth", "SCAN"),
            )
        elif flow_id == "f5":
            universe = inputs.get("universe") or inputs.get("tickers") or ([ticker] if ticker else [])
            sector = inputs.get("sector") or ""
            result = execute_flow_f5(
                sector=sector,
                universe=universe,
                model=model,
                paid_for=paid_for,
                emit_event=emit,
                per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
                flow_context=inputs.get("flow_context") or {},
                rubric=inputs.get("rubric"),
                depth=inputs.get("depth", "SCAN"),
            )
        elif flow_id == "f6":
            seed = (inputs.get("seed_universe")
                    or inputs.get("universe")
                    or inputs.get("tickers")
                    or ([ticker] if ticker else []))
            thesis = inputs.get("thesis") or inputs.get("theme") or ""
            shortlist_size = int(inputs.get("shortlist_size", inputs.get("survivors_k", 8)))
            result = execute_flow_f6(
                thesis=thesis,
                seed_universe=seed,
                model=model,
                paid_for=paid_for,
                emit_event=emit,
                per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
                flow_context=inputs.get("flow_context") or {},
                shortlist_size=shortlist_size,
            )
        elif flow_id == "f7":
            exposed = inputs.get("exposed_tickers") or ([ticker] if ticker else [])
            event = inputs.get("event") or inputs.get("catalyst") or ""
            result = execute_flow_f7(
                event=event,
                exposed_tickers=exposed,
                model=model,
                paid_for=paid_for,
                emit_event=emit,
                per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
                flow_context=inputs.get("flow_context") or {},
                depth=inputs.get("depth", "SCAN"),
                skip_devil=inputs.get("skip_devil", False),
            )
        elif flow_id == "f8":
            macro = inputs.get("macro_shock") or inputs.get("macro_event") or ""
            thesis_ids = inputs.get("thesis_ids") or []
            result = execute_flow_f8(
                macro_shock=macro,
                thesis_ids=thesis_ids,
                model=model,
                paid_for=paid_for,
                emit_event=emit,
                per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
                flow_context=inputs.get("flow_context") or {},
                depth=inputs.get("depth", "STANDARD"),
                skip_devil=inputs.get("skip_devil", False),
            )
        else:
            result = execute_flow_f1(
                ticker=ticker,
                model=model,
                paid_for=paid_for,
                emit_event=emit,
                per_agent_model=per_agent_model,
                stream_chunks=stream_chunks,
            )
    except Exception as exc:
        # Drain everything the agent emitted before the crash, then FlowFailed.
        while events_out:
            yield events_out.pop(0)
        failed_agent = None
        # Best-effort: peek at the most recent AgentStarted we still haven't finished
        # (it's not in partial yet). The AgentFailed was already appended by call_agent.
        # We don't have it; partial carries everything that DID complete before failure.
        yield FlowFailed(
            flow_id=flow_id,
            reason=str(exc),
            failed_agent_id=failed_agent,
            partial_envelopes=partial,
        )
        return

    # Drain buffered events in emit order.
    while events_out:
        yield events_out.pop(0)

    yield FlowFinished(
        flow_id=flow_id,
        final_envelope=result["final_envelope"],
        total_cost_usd_estimate=cumulative_cost,
    )


# --------------------------------------------------------------------------- #
# Logging + run directory
# --------------------------------------------------------------------------- #
def make_run_id(flow: str, ticker: str | None) -> str:
    ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    suffix = (ticker or "no-ticker").replace(",", "_")
    h = hashlib.sha256(f"{flow}{ticker or ''}{ts}".encode()).hexdigest()[:8]
    return f"{ts}_{flow}_{suffix}_{h}"


# --------------------------------------------------------------------------- #
# Resume layer (runtime-4)
#
# When a flow fails at an agent AFTER some pre-agent envelopes have
# arrived, the user wants to re-run from the failed agent rather than
# starting over. The implementation is:
#
#   1. As each agent finishes, write its envelope to disk
#      (.runs/<run_id>/agents/<safe_agent_id>.json).
#   2. On `--resume-from <agent_id> --resume-run-id <run_id>`, the
#      orchestrator pre-loads every agent envelope written under that
#      run_id and assigns it to module-level `_RESUME_PARTIAL_ENVELOPES`.
#   3. ``call_agent`` consults that cache: if `agent_id` is in it,
#      the LLM call is skipped and the cached envelope is returned
#      with a 0.0 cost (no CostDelta emitted for replayed agents).
#
# The "resume-from" semantic: replay everything whose agent_id is in
# the cache, then run the named agent fresh. The CLI does *not* need
# to know the wave order — it just lists an agent_id and the flow's
# own dispatch logic decides replay vs fresh.
# --------------------------------------------------------------------------- #
_RESUME_PARTIAL_ENVELOPES: dict[str, dict[str, Any]] = {}
_RESUME_FROM_RUN_ID: str = ""


def _safe_agent_filename(agent_id: str) -> str:
    """Filesystem-safe slug for an agent_id used as a filename component.

    Matching convention with snippets.py / packs.py for consistency.
    """
    import re as _re
    s = _re.sub(r"[^A-Za-z0-9_-]+", "_", agent_id or "").strip("_")
    return (s.lower() or "unknown")[:64]


def _persist_agent_envelope(run_id: str, agent_id: str, env: Any) -> Path | None:
    """Write per-agent envelope to disk for later resume.

    Called whenever ``emit`` sees an AgentFinished. Idempotent: if the
    file already exists for the same (run_id, agent_id), we *don't*
    overwrite from a re-run — the persistent disk copy acts as the
    resume cache and a re-run is authorized by the user only when
    they're explicitly retrying the agent (i.e. via --resume-from with
    a DIFFERENT resume-run_id, or by saving a backup). For a re-run
    on the same run_id we leave the cache untouched.
    """
    if not run_id or not agent_id:
        return None
    try:
        p = RUNS_DIR / run_id / "agents"
        p.mkdir(parents=True, exist_ok=True)
        path = p / f"{_safe_agent_filename(agent_id)}.json"
        if not path.exists():
            path.write_text(json.dumps(env, indent=2), encoding="utf-8")
        return path
    except (OSError, TypeError, ValueError):
        return None


def load_prior_resume_envelopes(run_id: str) -> dict[str, dict[str, Any]]:
    """Read every ``.runs/<run_id>/agents/*.json`` into a dict.

    Keyed by ``agent_id`` from the envelope (falls back to the
    filename stem if missing). A file that fails to parse is skipped
    silently rather than crashing — a corrupt cache entry should not
    prevent the next resume attempt from working.
    """
    out: dict[str, dict[str, Any]] = {}
    if not run_id:
        return out
    agents_dir = RUNS_DIR / run_id / "agents"
    if not agents_dir.exists():
        return out
    for path in agents_dir.glob("*.json"):
        try:
            env = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(env, dict):
            continue
        agent_id = (env.get("agent_id") or path.stem).strip()
        if agent_id:
            out[agent_id] = env
    return out


def clear_resume_cache() -> None:
    """Reset the module-level resume cache.

    Tests use this between scenarios to ensure no leakage.
    """
    global _RESUME_PARTIAL_ENVELOPES
    _RESUME_PARTIAL_ENVELOPES = {}


def write_run_artifact(run_id: str, flow: str, ticker: str | None,
                       result: dict[str, Any], costs: list[dict[str, Any]]) -> Path:
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "final_envelope.json").write_text(
        json.dumps(result["final_envelope"], indent=2), encoding="utf-8"
    )
    (run_dir / "cost.json").write_text(json.dumps(costs, indent=2), encoding="utf-8")
    # Render memo to markdown
    memo_md = render_memo_markdown(result["final_envelope"])
    (run_dir / "memo.md").write_text(memo_md, encoding="utf-8")
    # Append to global cost log
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    global_log = []
    if COST_LOG.exists():
        try:
            global_log = json.loads(COST_LOG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            global_log = []
    global_log.extend(costs)
    COST_LOG.write_text(json.dumps(global_log, indent=2), encoding="utf-8")
    return run_dir


# --------------------------------------------------------------------------- #
# [--export] Export the rendered memo (and optionally the envelope) to a user path.
# --------------------------------------------------------------------------- #
def export_run_artifact(
    run_dir: Path,
    export_path: str | Path,
    *,
    envelope: dict[str, Any] | None = None,
) -> list[Path]:
    """Copy ``run_dir/memo.md`` (and optionally the envelope) to ``export_path``.

    Three shapes of ``export_path``:

    1. ``".md"`` suffix  → write only the rendered memo to that exact path.
    2. ``".json"`` suffix → write only the final envelope JSON to that exact path.
       Requires ``envelope``; raises ``ValueError`` otherwise.
    3. Directory (existing, trailing slash, or nested path) → write both
       ``memo.md`` AND ``final_envelope.json`` *inside* that directory.
       The directory is created if it doesn't exist.

    Bare names like ``out`` (no separator, no suffix) default to file
    mode — the user's mental model is "give me a file" → file mode
    produces ``./out.md``.

    Returns the list of paths actually written (always ≥ 1 unless
    ``export_path`` is the empty string). On any other error (permission
    denied, bad path) raises — the caller prints to stderr and exits
    non-zero so the user knows the export didn't land.
    """
    raw_input = str(export_path)
    target = Path(raw_input).expanduser()
    if not raw_input.strip():
        raise ValueError("--export path is empty")

    written: list[Path] = []

    # Case 1 + 2: explicit file path with extension
    suffix = target.suffix.lower()
    if suffix == ".md":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((run_dir / "memo.md").read_text(encoding="utf-8"),
                          encoding="utf-8")
        written.append(target)
        return written
    if suffix == ".json":
        if envelope is None:
            envelope_path = run_dir / "final_envelope.json"
            if envelope_path.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(envelope_path.read_text(encoding="utf-8"),
                                  encoding="utf-8")
                written.append(target)
                return written
            raise ValueError(
                f"--export {target} requested .json but no envelope available "
                f"at {envelope_path}"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
        written.append(target)
        return written

    # Case 3: directory. Two directory heuristics (after the .md/.json cases):
    #   a) raw input ends with a trailing separator (e.g. "exports/")
    #      — checked against raw_input because Path() normalises slashes away
    #   b) path exists and is a directory on disk
    #   c) path has more than one path component (e.g. "./exports",
    #      "/tmp/exports", "sub/exports") AND no recognized file extension.
    # Bare names like ``out`` or ``./out`` (no recognized suffix, single
    # component) default to file mode — the user's mental model is "give
    # me a file" → file mode produces ``./out.md``.
    ends_sep = raw_input.endswith("/") or raw_input.endswith(os.sep)
    is_dir = target.exists() and target.is_dir()
    multi_component = len(target.parts) > 1
    if ends_sep or is_dir or (multi_component and suffix == ""):
        target.mkdir(parents=True, exist_ok=True)
        memo_dest = target / "memo.md"
        memo_dest.write_text((run_dir / "memo.md").read_text(encoding="utf-8"),
                             encoding="utf-8")
        written.append(memo_dest)
        envelope_src = run_dir / "final_envelope.json"
        if envelope_src.exists():
            envelope_dest = target / "final_envelope.json"
            envelope_dest.write_text(envelope_src.read_text(encoding="utf-8"),
                                     encoding="utf-8")
            written.append(envelope_dest)
        return written

    # Case 4: ambiguous path that doesn't exist (e.g. ``out`` or ``out.tar``).
    # Default to writing a file by appending ``.md`` so the user gets the
    # common case: ``--export out`` → ``./out.md`` ; ``--export out.tar`` →
    # ``./out.tar.md``. Preserves whatever the user typed as the prefix.
    target = Path(str(target) + ".md")
    target.write_text((run_dir / "memo.md").read_text(encoding="utf-8"),
                      encoding="utf-8")
    written.append(target)
    return written


def render_memo_markdown(env: dict[str, Any]) -> str:
    """Render the final-report envelope into a memo that matches docs/flows/*.md templates."""
    memo = env.get("memo", {})
    bottom = memo.get("bottom_line", {}) or {}
    md = []
    md.append(f"# Bottom line — {bottom.get('direction', 'N/A')} (conviction {bottom.get('conviction', 'N/A')}/5)")
    md.append("")
    md.append(f"**{bottom.get('one_liner', '')}**")
    md.append("")
    md.append(f"**Flip trigger:** {bottom.get('flip_trigger', '')}")
    md.append("")
    md.append("## Bull case")
    md.append("")
    md.append(memo.get("bull_case", ""))
    md.append("")
    md.append("## Bear case")
    md.append("")
    md.append(memo.get("bear_case", ""))
    md.append("")
    md.append("## What an attacker would say")
    md.append("")
    md.append(memo.get("what_an_attacker_would_say", ""))
    md.append("")
    md.append("## Next three questions")
    md.append("")
    for q in memo.get("next_three_questions", []):
        md.append(f"- {q}")
    md.append("")
    md.append("## Citations")
    md.append("")
    for c in memo.get("citations_used", []):
        url = c.get("url") or "(no URL)"
        md.append(f"- **{c.get('name', '')}** ({c.get('type', '')}) — {c.get('date', '')} — {url}")
    md.append("")
    md.append(f"_Run confidence: {env.get('confidence', 'N/A')}_")
    md.append("")
    if env.get("gaps"):
        md.append("## Gaps")
        for g in env["gaps"]:
            md.append(f"- {g}")
        md.append("")
    return "\n".join(md)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def _run_cli_call_tool(args: argparse.Namespace) -> int:
    """`--call-tool` CLI dispatcher.

    Run a single connector from the registry, print events as they fire, write
    the ToolResult into `.runs/<run_id>/connector_<tool_id>.json` so the eval
    suite (``inventory`` etc.) picks the artifact up.
    """
    # When invoked as `python docs/runtime/runtime.py`, Python treats the file
    # as top-level (`__main__`), so neither relative imports (`from .call_tool`)
    # nor absolute `import runtime.call_tool` resolve automatically. We
    # explicitly load the `runtime` package init into sys.modules, then load
    # call_tool against the package. The same trick is used by the pilot scripts.
    if "runtime" not in sys.modules:
        _RUNTIME_PKG_PARENT = str(Path(__file__).resolve().parent.parent)
        if _RUNTIME_PKG_PARENT not in sys.path:
            sys.path.insert(0, _RUNTIME_PKG_PARENT)
        import importlib.util as _ilu
        _pkg_init = Path(__file__).resolve().parent / "__init__.py"
        if _pkg_init.exists():
            _spec = _ilu.spec_from_file_location("runtime", _pkg_init)
            _pkg = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_pkg)
            sys.modules["runtime"] = _pkg
    from runtime.call_tool import call_tool as call_tool_fn
    from runtime.call_tool import TOOL_REGISTRY  # noqa: F401  (exposed for tests)
    # Build kwargs from the generic arg flags. Tools that don't accept a given
    # key will raise inside the tool method, which call_tool catches and turns
    # into ConnectorFailed + a FAILED ToolResult.
    kwarg_candidates = {
        "ticker": args.ticker,
        "query": args.query,
        "since_days": args.since_days,
        "limit": args.limit,
        "forms": args.forms.split(",") if args.forms else None,
        "ciks": args.ciks.split(",") if args.ciks else None,
        "start": args.start,
        "end": args.end,
        "article_id": args.article_id,
        "resolution": args.resolution,
        "days_back": args.days_back,
    }
    # If caller provided a raw JSON --request, that wins. (Structured tools
    # like DCFTool / CompsTool / ComparatorTool take `request` / `subject`
    # / `tickers` dicts that the generic flag set can't fully express.)
    if args.request:
        try:
            tool_args = json.loads(args.request)
        except json.JSONDecodeError as exc:
            print(f"# call_tool: --request is not valid JSON: {exc}", file=sys.stderr)
            return 2
    else:
        tool_args = {k: v for k, v in kwarg_candidates.items() if v is not None}
    # Pull in any additional tool kwargs introduced since the strict whitelist.
    extra_kwargs = {
        "url": args.url,
        "period": args.period,
        "interval": args.interval,
        "kind": args.kind,
        "min_value": args.min_value,
        "since_quarters": args.since_quarters,
    }
    for k, v in extra_kwargs.items():
        if v is not None:
            tool_args[k] = v

    print(f"# call_tool: {args.call_tool} args={tool_args}", file=sys.stderr)
    events_emitted: list[Any] = []

    def _emit(ev: Any) -> None:
        events_emitted.append(ev)
        # Render as one-line log to stderr (so stdout stays clean).
        kind = type(ev).__name__
        if hasattr(ev, "__dict__"):
            payload = {k: v for k, v in ev.__dict__.items()
                       if not k.startswith("_")}
            print(f"#   \u21aa {kind}: {payload}", file=sys.stderr)

    result = call_tool_fn(
        tool_id=args.call_tool,
        requested_by_agent="cli-tool",
        emit_event=_emit,
        method=args.tool_method or None,
        args=tool_args,
    )

    run_id = make_run_id(f"tool-{args.call_tool}", args.ticker or "")
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    art = {
        "run_id": run_id,
        "tool_id": args.call_tool,
        "method": args.tool_method,
        "args": tool_args,
        "tool_result": result.__dict__ if hasattr(result, "__dict__") else str(result),
        "events": [e.__dict__ if hasattr(e, "__dict__") else str(e) for e in events_emitted],
        "as_of": dt.datetime.utcnow().isoformat() + "Z",
    }
    (run_dir / f"connector_{args.call_tool}.json").write_text(
        json.dumps(art, indent=2), encoding="utf-8")

    print(f"\n=== call_tool result ({args.call_tool}) ===")
    print(f"  status       : {result.status}")
    print(f"  as_of        : {result.as_of}")
    print(f"  source       : {result.source}")
    if result.note:
        print(f"  note         : {result.note[:200]}")
    summary = result.data
    if isinstance(summary, list):
        print(f"  rows returned: {len(summary)}")
        for i, row in enumerate(summary[:3]):
            print(f"    [{i}] {row}")
    elif isinstance(summary, dict):
        print(f"  data keys    : {sorted(summary.keys())}")
        for k in list(summary.keys())[:5]:
            v = summary[k]
            if isinstance(v, str) and len(v) > 200:
                v = v[:200] + "..."
            print(f"    {k}: {v!r}")
    print(f"\n# run_id: {run_id}", file=sys.stderr)
    print(f"# artifact: {run_dir / f'connector_{args.call_tool}.json'}", file=sys.stderr)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Labourious runtime — Analyst's Bench skeleton")
    p.add_argument("--flow", required=("--call-tool" not in sys.argv and "--list-tools" not in sys.argv),
                   choices=["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10"])
    p.add_argument("--ticker", help="Single ticker (e.g. NVDA)")
    p.add_argument("--tickers", help="Comma-separated tickers (for f2)")
    p.add_argument("--watchlist", help="Comma-separated tickers for f10 (daily briefing). "
                   "Falls back to Config.watchlist if unset.")
    p.add_argument("--briefing-days", type=int, default=1,
                   help="For f10: look-back window in days (default 1 = since yesterday). "
                        "Named differently from the tool-kwarg --since-days to avoid argparse conflict.")
    p.add_argument("--thesis", help="Thesis text (for f6)")
    p.add_argument("--model", required=("--dry-run" not in sys.argv and "--call-tool" not in sys.argv and "--list-tools" not in sys.argv),
                   help="e.g. ollama/llama3.3:70b, groq/llama-3.3-70b-versatile, anthropic/claude-sonnet-4-5 (skippable with --dry-run / --call-tool / --list-tools)")
    p.add_argument("--paid-for", help="Comma-separated agents to put on the paid model (e.g. final-report)")
    p.add_argument("--depth", default="STANDARD", choices=["SCAN", "STANDARD", "DEEP"])
    # --- [runtime-4] Resume partial-failure --------------------------------------
    # `--resume-run-id <id>` reads the per-agent envelope cache written by a
    # prior crashed/aborted run; `--resume-from <agent_id>` names the *next*
    # agent to run from. Every agent_id before ``--resume-from`` whose
    # envelope is on disk is replayed; ``--resume-from`` itself + later agents
    # are run fresh. Permitted patterns:
    #   --resume-run-id <id>            # replay every cached agent (read-only)
    #   --resume-run-id <id> --resume-from senior-analyst  # replay SA-and-before, run D-A + final-report fresh
    p.add_argument("--resume-run-id", help="Reuse the per-agent envelope cache from a prior run's <run_id>.")
    p.add_argument("--resume-from", help="Agent_id after which to run fresh; cached agents before this point are replayed.")
    p.add_argument("--compressed", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="Print the wave plan + brief structure; do not call models")
    # --- [--export] Save the rendered memo (and optionally the envelope) to disk
    # Three shapes:
    #   --export out.md             → write memo.md to ./out.md
    #   --export out.json           → write final_envelope.json to ./out.json
    #   --export /path/to/dir       → write BOTH memo.md + final_envelope.json into dir
    # Default behaviour (no --export) is unchanged: print memo to stdout,
    # write the canonical artifacts under docs/runtime/.runs/<run_id>/.
    p.add_argument("--export", dest="export_path", default=None, metavar="PATH",
                   help="Save the rendered memo to PATH. .md → memo, .json → envelope, "
                        "directory → both. Default: print to stdout only.")
    p.add_argument("--rubric", help="For f2: comparison rubric (e.g. 'growth, valuation, quality'). Defaults to balanced.")
    p.add_argument("--earnings-date", help="For f3/f4: ISO date of earnings print")
    p.add_argument("--thesis-id", type=int, help="For f3/f4: specific thesis_register row id")
    p.add_argument("--skip-devil", action="store_true",
                   help="For f3: skip the devils-advocate beat (cheaper pre-mortem)")
    # --- [cli-tool] Direct connector invocation ---------------------------------
    # `python docs/runtime/runtime.py --call-tool news_8k --ticker NVDA --since-days 30`
    # runs a single connector and prints ConnectorRequested → Completed/Failed.
    # Useful as the backend for the TUI /tool <name> slash command.
    p.add_argument("--call-tool",
                   help="Run a single tool from the registry and print events. "
                        "Pairs with --ticker/--query/etc. Examples: "
                        "--call-tool news_8k --ticker NVDA --since-days 30 ; "
                        "--call-tool sec_edgar_fulltext --query 'AI capex' --limit 5.")
    p.add_argument("--tool-method",
                   help="Override a tool's default method. e.g. transcripts/fetch_transcript "
                        "instead of the registry default.")
    p.add_argument("--list-tools", action="store_true",
                   help="Print the tool registry contents (id + default method + arg_keys) and exit.")
    # Generic kwargs accepted by every connector in the registry. Unknown kwargs for
    # the requested tool surface as ConnectorFailed (TypeError gets caught by call_tool).
    # (--ticker is already added above; we just add the rest here.)
    p.add_argument("--query", help="tool kwarg: search query string")
    p.add_argument("--since-days", type=int, help="tool kwarg: look back N days")
    p.add_argument("--limit", type=int, help="tool kwarg: max rows")
    p.add_argument("--forms", help="tool kwarg: comma-separated SEC form types (10-K,10-Q,8-K)")
    p.add_argument("--ciks", help="tool kwarg: comma-separated SEC CIK ids")
    p.add_argument("--start", help="tool kwarg: ISO start date")
    p.add_argument("--end", help="tool kwarg: ISO end date")
    p.add_argument("--article-id", help="tool kwarg: e.g. transcripts article_id")
    p.add_argument("--url", help="tool kwarg: e.g. web_fetch URL")
    p.add_argument("--period", help="tool kwarg: e.g. market_data period (1mo, 1y)")
    p.add_argument("--interval", help="tool kwarg: e.g. market_data interval (1d, 1h)")
    p.add_argument("--kind", help="tool kwarg: e.g. insider kind")
    p.add_argument("--min-value", type=int, help="tool kwarg: e.g. insider min_value")
    p.add_argument("--since-quarters", type=int, help="tool kwarg: e.g. transcripts since_quarters")
    p.add_argument("--resolution", help="tool kwarg: e.g. quotes_realtime resolution "
                   "(D, 60, 30, 15, 5, 1 — or alias: 1d, 1h, 5m, etc.)")
    p.add_argument("--days-back", type=int, help="tool kwarg: e.g. quotes_realtime lookback "
                   "(calendar days). Default: 365 for candles; quote ignores.")
    p.add_argument("--request", help="JSON-encoded call payload. "
                   "Overrides all other kwargs. Useful for tools (quant_dcf, "
                   "quant_comps, quant_comparator) that expect a structured request "
                   "dict instead of flat kwargs. Example: --request '{\"ticker\":\"NVDA\",\"as_of\":\"...\"}'")
    args = p.parse_args()

    if args.list_tools:
        if "runtime" not in sys.modules:
            _RUNTIME_PKG_PARENT = str(Path(__file__).resolve().parent.parent)
            if _RUNTIME_PKG_PARENT not in sys.path:
                sys.path.insert(0, _RUNTIME_PKG_PARENT)
            import importlib.util as _ilu
            _pkg_init = Path(__file__).resolve().parent / "__init__.py"
            if _pkg_init.exists():
                _spec = _ilu.spec_from_file_location("runtime", _pkg_init)
                _pkg = _ilu.module_from_spec(_spec)
                _spec.loader.exec_module(_pkg)
                sys.modules["runtime"] = _pkg
        from runtime.call_tool import TOOL_REGISTRY
        print("# tool registry:")
        for tid, binding in sorted(TOOL_REGISTRY.items()):
            print(f"#   {tid}: default={binding.default_method} args={','.join(binding.arg_keys)}")
        return 0

    if args.call_tool:
        return _run_cli_call_tool(args)

    if args.dry_run:
        # Sketch the wave plan and exit
        wave_plan = {
            "f1": ["orchestrator", "senior-analyst", "forensic-accounting || devils-advocate (parallel)", "final-report"],
            "f2": ["for each ticker: senior-analyst(SCAN)", "for each shortlisted ticker: forensic + devil (parallel)", "final-report (compare rubric)"],
            "f3": ["senior-analyst", "forensic-accounting + devils-advocate (parallel)", "final-report"],
            "f4": ["senior-analyst (loads prior thesis)", "forensic-accounting + devils-advocate (parallel)", "final-report (diff rubric)"],
            "f5": ["for each ticker in universe: senior-analyst(SCAN) + devils-advocate(SCAN)", "for shortlisted: forensic + devil (parallel)", "final-report (sector landscape)"],
            "f6": ["for each candidate: senior-analyst(SCAN)", "for shortlisted: forensic(SCAN) + devil(SCAN)", "final-report (screen rubric)"],
            "f7": ["senior-analyst", "forensic-accounting(SCAN) + devils-advocate(SCAN)", "final-report"],
            "f8": ["senior-analyst (loads thesis_ids)", "for each thesis: forensic(SCAN) + devil (parallel)", "final-report (macro overlay rubric)"],
            "f9": ["senior-analyst", "model-builder (DCF + comps)", "devils-advocate", "final-report"],
            "f10": ["for each watchlist ticker: senior-analyst (SCAN, re-check vs prior thesis)", "final-report (assemble REITERATE/UPDATE/FLIP tags)", "post: auto-write updates for FLIPs"],
        }
        plan_path = FLOWS_DIR / f"{args.flow}.md"
        print(f"# dry-run: {args.flow}")
        print(f"# flow recipe: {plan_path}")
        print(f"# wave plan:")
        for w in wave_plan.get(args.flow, []):
            print(f"#   • {w}")
        print(f"# model would be: {args.model}")
        if args.paid_for:
            print(f"# paid-for: {args.paid_for}")
        return 0

    paid_for = [a.strip() for a in (args.paid_for or "").split(",") if a.strip()] or None
    ticker = args.ticker or (args.tickers.split(",")[0] if args.tickers else None)

    # [runtime-4] Resume pre-load: if --resume-run-id is supplied,
    # populate the module-level cache consulted by call_agent. The
    # flow dispatch below (whether via execute_flow_f<N> directly or
    # via run_flow_stream) will then transparently skip fresh calls
    # for every agent whose envelope is on disk under that prior
    # run_id. --resume-from <agent_id> drops agents at-or-after the
    # anchor from the replay set so they run fresh.
    global _RESUME_PARTIAL_ENVELOPES, _RESUME_FROM_RUN_ID
    if args.resume_run_id:
        loaded = load_prior_resume_envelopes(args.resume_run_id)
        if args.resume_from and args.resume_from in loaded:
            sorted_agents = sorted(loaded.keys())
            cutoff = sorted_agents.index(args.resume_from)
            loaded = {k: v for i, (k, v) in enumerate(sorted_agents) if i < cutoff}
        _RESUME_PARTIAL_ENVELOPES = loaded
        _RESUME_FROM_RUN_ID = args.resume_run_id
        if loaded:
            print(f"# resume: replay {len(loaded)} cached agent envelopes from "
                  f"{args.resume_run_id} "
                  f"(resume-from={'(' + args.resume_from + ' and below)' if args.resume_from else '<all cached>'}); "
                  f"agents: {','.join(sorted(loaded.keys()))}",
                  file=sys.stderr)
        else:
            print(f"# resume: --resume-run-id {args.resume_run_id} had no cached "
                  f"envelopes (.runs/<id>/agents/*.{'{json}'} missing); running fresh",
                  file=sys.stderr)
    else:
        _RESUME_PARTIAL_ENVELOPES = {}
        _RESUME_FROM_RUN_ID = ""

    if args.flow == "f1":
        if not ticker:
            print("error: --ticker is required for f1", file=sys.stderr)
            return 2
        result = execute_flow_f1(ticker, args.model, paid_for=paid_for)
    elif args.flow == "f9":
        if not ticker:
            print("error: --ticker is required for f9", file=sys.stderr)
            return 2
        result = execute_flow_f9(ticker, args.model, paid_for=paid_for)
    elif args.flow == "f2":
        if not args.tickers:
            print("error: --tickers 'AAPL,MSFT' is required for f2", file=sys.stderr)
            return 2
        tickers_list = [t.strip() for t in args.tickers.split(",") if t.strip()]
        # --rubric optional; default = balanced.
        rubric = getattr(args, "rubric", None)
        result = execute_flow_f2(
            tickers=tickers_list,
            model=args.model,
            paid_for=paid_for,
            rubric=rubric,
            depth=getattr(args, "depth", "SCAN") or "SCAN",
        )
    elif args.flow in ("f3", "f4"):
        if not ticker:
            print(f"error: --ticker is required for {args.flow}", file=sys.stderr)
            return 2
        if not args.earnings_date:
            print(f"error: --earnings-date is required for {args.flow}", file=sys.stderr)
            return 2
        if args.flow == "f3":
            result = execute_flow_f3(
                ticker=ticker, earnings_date=args.earnings_date, model=args.model,
                paid_for=paid_for, thesis_id=args.thesis_id,
                skip_devil=args.skip_devil,
                depth=getattr(args, "depth", "SCAN") or "SCAN",
            )
        else:
            result = execute_flow_f4(
                ticker=ticker, earnings_date=args.earnings_date, model=args.model,
                paid_for=paid_for, thesis_id=args.thesis_id,
                depth=getattr(args, "depth", "STANDARD") or "STANDARD",
            )
    elif args.flow == "f5":
        if not args.tickers:
            print("error: --tickers 'AAPL,MSFT,...' is required for f5", file=sys.stderr)
            return 2
        sector = args.thesis or ""  # use --thesis as both sector name and CLI fallback
        tickers_list = [t.strip() for t in args.tickers.split(",") if t.strip()]
        rubric = getattr(args, "rubric", None)
        result = execute_flow_f5(
            sector=sector, universe=tickers_list,
            model=args.model, paid_for=paid_for,
            rubric=rubric,
            depth=getattr(args, "depth", "SCAN") or "SCAN",
        )
    elif args.flow == "f6":
        theme = args.thesis or ""
        if not args.tickers:
            print("error: --tickers <universe CSV> is required for f6", file=sys.stderr)
            return 2
        tickers_list = [t.strip() for t in args.tickers.split(",") if t.strip()]
        result = execute_flow_f6(
            thesis=theme, seed_universe=tickers_list,
            model=args.model, paid_for=paid_for,
            depth=getattr(args, "depth", "SCAN") or "SCAN",
            shortlist_size=int(getattr(args, "survivors_k", 8) or 8),
        )
    elif args.flow == "f7":
        if not ticker:
            print("error: --ticker is required for f7", file=sys.stderr)
            return 2
        event = args.thesis or "unspecified event"
        result = execute_flow_f7(
            event=event, exposed_tickers=[ticker],
            model=args.model, paid_for=paid_for,
            depth=getattr(args, "depth", "SCAN") or "SCAN",
            skip_devil=args.skip_devil,
        )
    elif args.flow == "f8":
        macro = args.thesis or ""
        if not macro:
            print("error: pass macro event via --thesis in this skeleton", file=sys.stderr)
            return 2
        # In CLI, thesis_ids defaults to "all open theses" — runtime resolves via register.
        result = execute_flow_f8(
            macro_shock=macro, thesis_ids=[],  # [] == all open
            model=args.model, paid_for=paid_for,
            depth=getattr(args, "depth", "SCAN") or "SCAN",
            skip_devil=args.skip_devil,
        )
    elif args.flow == "f10":
        # Resolve watchlist: --watchlist flag wins, otherwise Config.watchlist,
        # otherwise error. Empty watchlist is the only required-arg failure
        # beyond --model (which argparse already enforces).
        watchlist_str = (args.watchlist or "").strip()
        if not watchlist_str:
            try:
                from frontend.config_io import load_config  # type: ignore
                cfg = load_config()
                watchlist_str = ",".join(cfg.watchlist or [])
            except Exception:
                watchlist_str = ""
        if not watchlist_str:
            print("error: --watchlist 'NVDA,AAPL,...' is required for f10 "
                  "(or set Config.watchlist)", file=sys.stderr)
            return 2
        watchlist = [t.strip() for t in watchlist_str.split(",") if t.strip()]
        since_days = max(1, int(getattr(args, "briefing_days", 1) or 1))
        result = execute_flow_f10(
            watchlist=watchlist,
            model=args.model,
            paid_for=paid_for,
            since_days=since_days,
            depth=getattr(args, "depth", "SCAN") or "SCAN",
        )
    else:
        print(f"unknown flow: {args.flow}", file=sys.stderr)
        return 2

    run_id = make_run_id(args.flow, ticker or args.tickers)
    run_dir = write_run_artifact(run_id, args.flow, ticker or args.tickers,
                                  result, result["costs"])
    # [--export] Copy the rendered memo (and envelope) to the user-supplied path
    # before printing to stdout. Failures here are surfaced (non-zero exit)
    # so the user knows their `--export` didn't land — better than silent loss.
    if getattr(args, "export_path", None):
        try:
            written_paths = export_run_artifact(
                run_dir, args.export_path,
                envelope=result.get("final_envelope"),
            )
            for wp in written_paths:
                print(f"# exported: {wp}", file=sys.stderr)
        except (ValueError, OSError) as e:
            print(f"error: --export {args.export_path} failed: {e}", file=sys.stderr)
            return 3
    # Print memo to stdout
    print((run_dir / "memo.md").read_text(encoding="utf-8"))
    print(f"\n# run_id: {run_id}", file=sys.stderr)
    print(f"# artifacts: {run_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
