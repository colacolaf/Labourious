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
    """
    system_prompt = load_prompt(agent_id)
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
        # Parse envelope
        try:
            envelope = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{agent_id} returned non-JSON: {exc}\nRaw: {text[:500]}") from exc
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

    # Wave 1: orchestrator
    orch_brief = json.dumps({
        "flow_id": "f1",
        "user_query": f"Analyze {ticker}",
        "ticker": ticker,
        "relevant_history": prior_thesis,
        "depth": "STANDARD",
        "compressed": False,
    })
    orch_env, orch_cost = call_agent("orchestrator", orch_brief, model,
                                     stream_chunks=stream_chunks,
                                     paid_for=paid_for, emit_event=emit_event,
                                     per_agent_model=per_agent_model)

    # Wave 2: senior-analyst
    sr_brief = json.dumps({
        "from": "orchestrator",
        "situation": f"User wants analysis of {ticker}",
        "task": f"Build thesis skeleton on {ticker}",
        "ticker": ticker,
        "relevant_history": prior_thesis,
        "depth": "STANDARD",
        "compressed": False,
    })
    sr_env, sr_cost = call_agent("senior-analyst", sr_brief, model,
                                 paid_for=paid_for, emit_event=emit_event,
                                 per_agent_model=per_agent_model,
                                 stream_chunks=stream_chunks)

    # Wave 3: forensic-accounting + devils-advocate (sequential; future: parallel)
    fa_brief = json.dumps({
        "from": "senior-analyst",
        "task": f"Earnings-quality review on {ticker}",
        "ticker": ticker,
        "depth": "STANDARD",
        "compressed": False,
    })
    fa_env, fa_cost = call_agent("forensic-accounting", fa_brief, model,
                                 paid_for=paid_for, emit_event=emit_event,
                                 per_agent_model=per_agent_model,
                                 stream_chunks=stream_chunks)

    da_brief = json.dumps({
        "from": "senior-analyst",
        "task": f"Counter-case on {ticker} thesis",
        "ticker": ticker,
        "thesis": sr_env.get("thesis", {}),
        "depth": "STANDARD",
        "compressed": False,
    })
    da_env, da_cost = call_agent("devils-advocate", da_brief, model,
                                 paid_for=paid_for, emit_event=emit_event,
                                 per_agent_model=per_agent_model,
                                 stream_chunks=stream_chunks)

    # Wave 4: final-report
    fr_brief = json.dumps({
        "from": "senior-analyst",
        "flow_id": "f1",
        "thesis_synthesis": sr_env,
        "forensic_output": fa_env,
        "bear_case": da_env,
        "depth": "STANDARD",
        "compressed": False,
    })
    final_env, final_cost = call_agent("final-report", fr_brief, model,
                                       paid_for=paid_for, emit_event=emit_event,
                                       per_agent_model=per_agent_model,
                                       stream_chunks=stream_chunks)

    # Persist to thesis register
    thesis_row = register.write_thesis(
        ticker=ticker,
        thesis_text=sr_env.get("thesis", {}).get("one_sentence", ""),
        conviction=sr_env.get("bottom_line", {}).get("conviction", 0),
        bottom_line=sr_env.get("bottom_line", {}),
        evidence_urls=[c.get("url") for c in sr_env.get("citations", []) if c.get("url")],
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
        with a CostDelta so the TUI sidebar updates as each agent completes."""
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
def main() -> int:
    p = argparse.ArgumentParser(description="Labourious runtime — Analyst's Bench skeleton")
    p.add_argument("--flow", required=True, choices=["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8"])
    p.add_argument("--ticker", help="Single ticker (e.g. NVDA)")
    p.add_argument("--tickers", help="Comma-separated tickers (for f2)")
    p.add_argument("--thesis", help="Thesis text (for f6)")
    p.add_argument("--model", required=("--dry-run" not in sys.argv), help="e.g. ollama/llama3.3:70b, groq/llama-3.3-70b-versatile, anthropic/claude-sonnet-4-5 (skippable with --dry-run)")
    p.add_argument("--paid-for", help="Comma-separated agents to put on the paid model (e.g. final-report)")
    p.add_argument("--depth", default="STANDARD", choices=["SCAN", "STANDARD", "DEEP"])
    p.add_argument("--compressed", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="Print the wave plan + brief structure; do not call models")
    p.add_argument("--rubric", help="For f2: comparison rubric (e.g. 'growth, valuation, quality'). Defaults to balanced.")
    p.add_argument("--earnings-date", help="For f3/f4: ISO date of earnings print")
    p.add_argument("--thesis-id", type=int, help="For f3/f4: specific thesis_register row id")
    p.add_argument("--skip-devil", action="store_true",
                   help="For f3: skip the devils-advocate beat (cheaper pre-mortem)")
    args = p.parse_args()

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
    else:
        print(f"unknown flow: {args.flow}", file=sys.stderr)
        return 2

    run_id = make_run_id(args.flow, ticker or args.tickers)
    run_dir = write_run_artifact(run_id, args.flow, ticker or args.tickers,
                                  result, result["costs"])
    # Print memo to stdout
    print((run_dir / "memo.md").read_text(encoding="utf-8"))
    print(f"\n# run_id: {run_id}", file=sys.stderr)
    print(f"# artifacts: {run_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
