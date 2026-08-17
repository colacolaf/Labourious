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
import datetime as dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Project root (this file lives at docs/runtime/runtime.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = PROJECT_ROOT / "docs" / "prompts"
FLOWS_DIR = PROJECT_ROOT / "docs" / "flows"
RUNS_DIR = PROJECT_ROOT / "docs" / "runtime" / ".runs"
COST_LOG = PROJECT_ROOT / "docs" / "runtime" / ".runs" / "cost.json"

# Import local modules
sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapters import get_adapter  # type: ignore
from thesis_register.register import ThesisRegister  # type: ignore


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
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Calls an agent by loading its prompt, calling the model, parsing the JSON envelope.
    Returns (envelope, cost_record).
    """
    system_prompt = load_prompt(agent_id)
    # If --paid-for is set and this agent is in the list, override model.
    effective_model = model_name
    if paid_for and agent_id in paid_for:
        # Hybrid: senior-analyst -> free; final-report -> Sonnet by convention
        if agent_id == "final-report":
            effective_model = "anthropic/claude-sonnet-4-5"
        elif agent_id == "senior-analyst":
            if "anthropic" not in model_name:
                effective_model = "anthropic/claude-sonnet-4-5"
    adapter = get_adapter(effective_model)
    t0 = time.monotonic()
    response = adapter.call(
        messages=[{"role": "user", "content": user_brief}],
        system=system_prompt,
        options={"temperature": 0.2},
    )
    wallclock = time.monotonic() - t0
    # Parse envelope
    try:
        envelope = json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{agent_id} returned non-JSON: {exc}\nRaw: {response.text[:500]}") from exc
    ok, failures = validate_envelope(envelope, agent_id)
    if not ok:
        raise RuntimeError(f"{agent_id} envelope failed validation: {failures}")
    cost = {
        "agent_id": agent_id,
        "model": effective_model,
        "in_tokens": response.in_tokens,
        "out_tokens": response.out_tokens,
        "cache_hit_tokens": response.cache_hit_tokens,
        "cost_usd_estimate": response.cost_usd_estimate,
        "wallclock_s": round(wallclock, 2),
        "as_of": dt.datetime.utcnow().isoformat() + "Z",
    }
    return envelope, cost


# --------------------------------------------------------------------------- #
# Per-flow orchestrators
# --------------------------------------------------------------------------- #
def execute_flow_f1(ticker: str, model: str, paid_for: list[str] | None) -> dict[str, Any]:
    """
    Flagship f1 — analyze ticker. Returns the final envelope (final-report JSON).
    Sequences: orchestrator → senior-analyst → (forensic-accounting || devils-advocate) → final-report.
    Hybrid mode: senior-analyst + specialists on free; final-report on Sonnet.
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
    orch_env, orch_cost = call_agent("orchestrator", orch_brief, model, paid_for=paid_for)

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
    sr_env, sr_cost = call_agent("senior-analyst", sr_brief, model, paid_for=paid_for)

    # Wave 3: forensic-accounting + devils-advocate in parallel
    # (in this skeleton they are sequential; parallelization is a future enhancement)
    fa_brief = json.dumps({
        "from": "senior-analyst",
        "task": f"Earnings-quality review on {ticker}",
        "ticker": ticker,
        "depth": "STANDARD",
        "compressed": False,
    })
    fa_env, fa_cost = call_agent("forensic-accounting", fa_brief, model, paid_for=paid_for)

    da_brief = json.dumps({
        "from": "senior-analyst",
        "task": f"Counter-case on {ticker} thesis",
        "ticker": ticker,
        "thesis": sr_env.get("thesis", {}),
        "depth": "STANDARD",
        "compressed": False,
    })
    da_env, da_cost = call_agent("devils-advocate", da_brief, model, paid_for=paid_for)

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
    final_env, final_cost = call_agent("final-report", fr_brief, model, paid_for=paid_for)

    # Persist to thesis register
    register.write_thesis(
        ticker=ticker,
        thesis_text=sr_env.get("thesis", {}).get("one_sentence", ""),
        conviction=sr_env.get("bottom_line", {}).get("conviction", 0),
        bottom_line=sr_env.get("bottom_line", {}),
        evidence_urls=[c.get("url") for c in sr_env.get("citations", []) if c.get("url")],
        flow_id="f1",
    )

    return {
        "final_envelope": final_env,
        "costs": [orch_cost, sr_cost, fa_cost, da_cost, final_cost],
    }


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
    p.add_argument("--model", required=True, help="e.g. ollama/llama3.3:70b, groq/llama-3.3-70b-versatile, anthropic/claude-sonnet-4-5")
    p.add_argument("--paid-for", help="Comma-separated agents to put on the paid model (e.g. final-report)")
    p.add_argument("--depth", default="STANDARD", choices=["SCAN", "STANDARD", "DEEP"])
    p.add_argument("--compressed", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="Print the wave plan + brief structure; do not call models")
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
    elif args.flow == "f2":
        # Placeholder — f2 implementation deferred to P1
        print(f"# f2 not yet wired in skeleton. tickers={args.tickers}. See docs/flows/f2-compare-tickers.md",
              file=sys.stderr)
        return 2
    elif args.flow in ("f3", "f4", "f5", "f6", "f7", "f8"):
        print(f"# {args.flow} not yet wired in skeleton. See docs/flows/{args.flow}.md", file=sys.stderr)
        return 2
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
