"""
mock_runtime.py — deterministic event generator for pilots + demos + local UI work.

Yields the SAME `Event` dataclasses as runtime.runtime.run_flow_stream, but
without making any LLM call. Useful for:

  - End-to-end pilots (verify the chat screen handles every event type)
  - Visual demos (run the TUI without an API key)
  - Local UI work (iterate on bubble/citation/diff layouts without spending tokens)

Toggled via the `LABOURIOUS_MOCK=1` env var (read in runtime.runtime.run_flow_stream).
Or imported directly: `from runtime.mock_runtime import run_mock_flow_stream`.

The output is realistic: per-agent prose that sounds like an analyst memo,
realistic token counts, plausible wallclock, real-looking citation URLs.
"""

from __future__ import annotations

import os
import time
from typing import Iterator, Any


# Latency profile per agent (simulated wallclock).
_AGENT_LATENCY: dict[str, float] = {
    "orchestrator":       0.4,
    "senior-analyst":     2.1,
    "forensic-accounting": 3.4,
    "devils-advocate":    2.0,
    "final-report":       1.5,
}


# Token estimate per agent (in / out).
_AGENT_TOKENS: dict[str, tuple[int, int]] = {
    "orchestrator":       (118, 84),
    "senior-analyst":     (1180, 210),
    "forensic-accounting": (980, 280),
    "devils-advocate":    (720, 140),
    "final-report":       (1240, 410),
}


# Plausible per-agent prose. Kept short (≤240 chars) so a single AgentChunk
# event yields the whole thing and the RichLog can show it in one frame.
_AGENT_PROSE: dict[str, str] = {
    "orchestrator": (
        "Routing to f1 (Analyze ticker). Reading 4 prior theses for NVDA. "
        "STANDARD depth, free-model stack (ollama/llama3.3:70b)."
    ),
    "senior-analyst": (
        "Wide-moat franchise intact at $890. Price 22% above base-case $728. "
        "Two legs: (1) data-center capex still ramping; (2) software-traction "
        "metrics (NIM) holding >70%. Confidence MEDIUM because mid-cap peer "
        "set compressed and earnings dispersion is wide this cycle."
    ),
    "forensic-accounting": (
        "Note 2(b) of the 10-Q: revenue recognition shifted in Q2 — multi-year "
        "license renewals now booked upfront. Owners' earnings != reported "
        "earnings by ~$0.9B TTM. Caveat: this is transparency risk, not fraud. "
        "Flag for the final memo."
    ),
    "devils-advocate": (
        "Steelmanned bull breaks on three legs: (1) China-export controls "
        "re-tightening Q4 (known catalyst); (2) hyperscaler capex cut chatter "
        "(MSFT/GOOGL guidance shifts); (3) Blackwell ramp slips beyond Q1 "
        "(supply-chain risk). None confirmed; all are known unknowns. "
        "Flip trigger: <= $720 OR confirmatory 10-Q."
    ),
    "final-report": (
        "# Bottom line — HOLD (4/5)\n\n"
        "Wide-moat franchise at $890 carries 22% premium to base-case $728. "
        "The thesis survives the Q3 print because earnings dispersion is wider "
        "than usual, not because fundamentals are weakening.\n\n"
        "## Bull case\nDC capex tailwinds persist; software-traction metrics hold "
        "NIM >70%. Server-net-revenue guides above consensus.\n\n"
        "## Bear case\nNote 2(b) transparency risk — owners' earnings trail "
        "reported by ~$0.9B TTM. China-export controls re-tighten Q4.\n\n"
        "## What an attacker would say\nPay 3.0x-4.5x sales on a stock whose "
        "franchise you can't isolate from the AI-cycle narrative.\n\n"
        "## Flip trigger\n<= $720 OR confirmatory 10-Q shows owners' earnings "
        "< reported.\n\n"
        "## Citations\n6 sources: 2 SEC filings, 2 news, 1 macro, 1 web."
    ),
}


# Realistic citation URLs (host-typed: filing/news/macro/web).
_CITATION_URLS: list[str] = [
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001045810&type=10-Q",
    "https://www.sec.gov/Archives/edgar/data/0001045810/nvda-10q-2024-q3.htm",
    "https://www.reuters.com/markets/companies/NVDA-OQ",
    "https://www.ft.com/content/83c5d2a4-7c40-4d40-9a3e-aa3c7b2b5f9c",
    "https://fred.stlouisfed.org/series/DPNS",
    "https://www.wsj.com/articles/nvidia-q3-earnings-data-center-revenue",
]


def run_mock_flow_stream(
    flow_id: str = "f1",
    inputs: dict | None = None,
    model: str = "ollama/llama3.3:70b",
    paid_for: list[str] | None = None,
    per_agent_model: dict[str, str] | None = None,
) -> Iterator[Any]:
    """
    Yield FlowStarted → ThesisPriorRead → 5×(AgentStarted → AgentChunk + cost →
    AgentFinished) → ThesisWritten → FlowFinished.

    Honors the `sleep` keyword in inputs (default 0.0) so the pilot can slow
    it down to test streaming visualization.
    """
    from runtime.events import (
        FlowStarted, ThesisPriorRead,
        AgentStarted, AgentChunk, AgentFinished,
        CostDelta, ThesisWritten, FlowFinished,
    )

    inputs = inputs or {}
    sleep_s = float(inputs.get("_mock_sleep_s", 0.0) or 0.0)
    ticker = inputs.get("ticker", "NVDA")
    depth = inputs.get("depth", "STANDARD")
    compressed = inputs.get("compressed", False)
    paid_for = paid_for or []
    per_agent_model = per_agent_model or {}

    cumulative_in = 0
    cumulative_out = 0
    cumulative_cost = 0.0

    # --- 1. flow_started -----------------------------------------------
    prior_snapshot = [
        {"thesis_id": 39, "version": "v1", "conviction": 3,
         "created_at": "10d ago", "bottom_line": "WATCH — wide moat but priced."},
        {"thesis_id": 40, "version": "v2", "conviction": 4,
         "created_at": "3d ago",  "bottom_line": "HOLD — premium to base-case 28%."},
    ]
    yield FlowStarted(
        flow_id=flow_id,
        tickers=[ticker],
        ticker_join=ticker,
        thesis_register_snapshot=prior_snapshot,
        depth=depth,
        compressed=compressed,
    )
    if sleep_s: time.sleep(sleep_s * 0.05)

    # --- 2. thesis_prior_read ------------------------------------------
    yield ThesisPriorRead(ticker=ticker, prior_theses=prior_snapshot)
    if sleep_s: time.sleep(sleep_s * 0.05)

    # --- 3. 5 × (agent_started → chunk → finished) ---------------------
    agents_seen = []
    for agent_id in ("orchestrator", "senior-analyst", "forensic-accounting",
                     "devils-advocate", "final-report"):
        agents_seen.append(agent_id)
        wc = _AGENT_LATENCY[agent_id]
        in_t, out_t = _AGENT_TOKENS[agent_id]
        # Resolve the effective model so the AgentStarted event surfaces
        # what the runtime *actually* picked. Precedence matches call_agent:
        # per_agent_model[agent_id] > paid_for hybrid > chat default.
        effective_model = per_agent_model.get(agent_id, model)
        if agent_id not in per_agent_model and paid_for and agent_id in paid_for:
            if agent_id == "final-report":
                effective_model = "anthropic/claude-sonnet-4-5"
            elif agent_id == "senior-analyst" and "anthropic" not in model:
                effective_model = "anthropic/claude-sonnet-4-5"

        yield AgentStarted(
            agent_id=agent_id,
            model=effective_model,
            depth=depth,
            compressed=compressed,
        )
        if sleep_s: time.sleep(sleep_s * 0.05)

        yield AgentChunk(agent_id=agent_id, delta=_AGENT_PROSE[agent_id])
        if sleep_s: time.sleep(sleep_s * 0.05)

        # Build the per-agent envelope so the bubble can render
        # confidence + citation count + chip.
        envelope: dict[str, Any] = {
            "agent_id": agent_id,
            "confidence": "HIGH" if agent_id == "final-report" else "MEDIUM",
            "citations": _CITATION_URLS if agent_id == "final-report" else [],
            "thesis_text": _AGENT_PROSE[agent_id],
        }

        yield AgentFinished(
            agent_id=agent_id,
            envelope=envelope,
            wallclock_s=wc,
            in_tokens=in_t,
            out_tokens=out_t,
            cost_usd_estimate=0.0,
        )
        if sleep_s: time.sleep(sleep_s * 0.05)

        cumulative_in += in_t
        cumulative_out += out_t
        cumulative_cost += 0.0
        yield CostDelta(
            agent_id=agent_id,
            in_tokens=in_t,
            out_tokens=out_t,
            cost_usd_estimate=0.0,
            cumulative_in=cumulative_in,
            cumulative_out=cumulative_out,
            cumulative_cost=cumulative_cost,
        )
        if sleep_s: time.sleep(sleep_s * 0.05)

    # --- 4. thesis_written ---------------------------------------------
    yield ThesisWritten(
        ticker=ticker,
        thesis_id=41,
        version="v3",
        thesis_text=_AGENT_PROSE["final-report"],
        conviction=4,
        bottom_line={"action": "HOLD", "conviction": 4, "price": 890,
                     "base_case": 728, "flip_trigger": "<= $720"},
        evidence_urls=list(_CITATION_URLS),
    )
    if sleep_s: time.sleep(sleep_s * 0.05)

    # --- 5. flow_finished ----------------------------------------------
    final_envelope = {
        "agent_id": "final-report",
        "confidence": "HIGH",
        "thesis_text": _AGENT_PROSE["final-report"],
        "conviction": 4,
        "_prior_thesis": prior_snapshot,
    }
    yield FlowFinished(
        flow_id=flow_id,
        final_envelope=final_envelope,
        total_cost_usd_estimate=cumulative_cost,
    )


def mock_runtime_available() -> bool:
    """True when the mock runtime is requested via the env flag."""
    return os.environ.get("LABOURIOUS_MOCK", "").strip() in ("1", "true", "yes")
