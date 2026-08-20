"""cost_footer_smoke.py — smoke pilot for the cost footer estimator.

Verifies (without launching the TUI):

  1. rate-table lookups for every known provider/model slug
  2. longest-prefix match handles dated model slugs (e.g.
     ``claude-3-5-sonnet-20241022`` → claude-3-5-sonnet rates)
  3. unknown model falls back to conservative Opus-class estimate
  4. ollama + groq free-tier models are is_free_model=True
  5. paid models are is_free_model=False
  6. estimate_run_cost returns (usd, agent_count, is_free) with sane values
  7. hybrid (paid_for) routes only the listed agents to Sonnet, others
     stay on the default (free) model
  8. format_cost_for_footer emits the three documented shapes:
       "free · N agents"
       "≈ $X.XX · N agents"
       "? · N agents"
  9. _FLOW_AGENTS covers f1..f9 with >= 3 agents each
 10. _AGENT_TOKEN_ESTIMATES covers SCAN/STANDARD/DEEP for every agent
     that appears in any flow
 11. chat.py imports + uses format_cost_for_footer (wired)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

THIS = Path(__file__).resolve()
DOCS = THIS.parents[2]
sys.path.insert(0, str(DOCS))


_passed = 0
_failed = 0


def step(label: str, ok: bool) -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ✓ {label}")
    else:
        _failed += 1
        print(f"  ✗ {label}")


def section(name: str) -> None:
    print(f"\n=== {name} ===")


# --------------------------------------------------------------------------- #
#  1. Rate lookups for known slugs
# --------------------------------------------------------------------------- #
section("1. rates_for_model — known slugs")
from runtime.rates import rates_for_model, is_free_model, estimate_run_cost, format_cost_for_footer

cases = [
    # (model_str, expected_in_rate, expected_out_rate)
    ("anthropic/claude-opus-4",       15.00, 75.00),
    ("anthropic/claude-sonnet-4",      3.00, 15.00),
    ("anthropic/claude-haiku-4",       1.00,  5.00),
    ("anthropic/claude-3-5-sonnet",    3.00, 15.00),
    ("anthropic/claude-3-haiku",       0.25,  1.25),
    ("openai/gpt-4o",                  2.50, 10.00),
    ("openai/gpt-4o-mini",             0.15,  0.60),
    ("openai/o1-mini",                 3.00, 12.00),
    ("groq/llama-3.3-70b-versatile",   0.0,   0.0),
    ("groq/llama-3.1-8b-instant",      0.0,   0.0),
    ("ollama/llama3.3:70b",            0.0,   0.0),
    ("ollama/qwen2.5:72b",             0.0,   0.0),
    ("gemini/gemini-2.5-pro",          1.25, 10.00),
    ("gemini/gemini-2.5-flash",        0.075, 0.30),
    ("cohere/command-r-plus",          2.50, 10.00),
]
for m, expected_in, expected_out in cases:
    in_rate, out_rate = rates_for_model(m)
    step(f"{m} → ({in_rate}, {out_rate})", in_rate == expected_in and out_rate == expected_out)


# --------------------------------------------------------------------------- #
#  2. Longest-prefix match for dated slugs
# --------------------------------------------------------------------------- #
section("2. rates_for_model — dated slugs use longest-prefix")
# claude-3-5-sonnet-20241022 should hit claude-3-5-sonnet (3.00, 15.00),
# not fall through to claude-3-sonnet (also 3.00, 15.00 here, but the
# mechanism is what matters).
in_rate, out_rate = rates_for_model("anthropic/claude-3-5-sonnet-20241022")
step("claude-3-5-sonnet-20241022 → (3.00, 15.00)",
     in_rate == 3.00 and out_rate == 15.00)

# A more discriminating test: gpt-4o-2024-08-06 should hit gpt-4o (2.50,
# 10.00), NOT gpt-4 (30, 60) by bare-prefix.
in_rate, out_rate = rates_for_model("openai/gpt-4o-2024-08-06")
step("gpt-4o-2024-08-06 → (2.50, 10.00), not gpt-4 (30, 60)",
     in_rate == 2.50 and out_rate == 10.00)

# Prefix that doesn't exist falls back gracefully.
in_rate, out_rate = rates_for_model("openai/gpt-99-future")
step("gpt-99-future → unknown default (5.00, 15.00)",
     in_rate == 5.00 and out_rate == 15.00)


# --------------------------------------------------------------------------- #
#  3. Unknown model falls back to conservative default
# --------------------------------------------------------------------------- #
section("3. Unknown model — conservative fall-back")
in_rate, out_rate = rates_for_model("totally-unknown/big-model")
step("unknown → (5.00, 15.00) conservative default",
     in_rate == 5.00 and out_rate == 15.00)
in_rate, out_rate = rates_for_model("garbage")
step("no provider prefix → conservative default",
     in_rate == 5.00 and out_rate == 15.00)


# --------------------------------------------------------------------------- #
#  4-5. is_free_model
# --------------------------------------------------------------------------- #
section("4-5. is_free_model — ollama + groq free tier = True, others = False")
step("ollama/llama3.3:70b is free",      is_free_model("ollama/llama3.3:70b"))
step("ollama/qwen2.5:72b is free",       is_free_model("ollama/qwen2.5:72b"))
step("groq/llama-3.3-70b-versatile is free",
     is_free_model("groq/llama-3.3-70b-versatile"))
step("anthropic/claude-sonnet-4 NOT free", not is_free_model("anthropic/claude-sonnet-4"))
step("openai/gpt-4o NOT free", not is_free_model("openai/gpt-4o"))
step("unknown/anything NOT free (conservative)",
     not is_free_model("unknown/foo"))


# --------------------------------------------------------------------------- #
#  6. estimate_run_cost returns (usd, agent_count, is_free)
# --------------------------------------------------------------------------- #
section("6. estimate_run_cost — sane shapes")
usd, count, free = estimate_run_cost("f1", "ollama/llama3.3:70b")
step("f1 ollama: usd==0.0", usd == 0.0)
step("f1 ollama: count==5", count == 5)
step("f1 ollama: free==True", free is True)

usd, count, free = estimate_run_cost("f1", "anthropic/claude-sonnet-4-5")
step("f1 sonnet: usd > 0", usd > 0)
step("f1 sonnet: 0.05 < usd < 0.30 (sane range)", 0.05 < usd < 0.30)
step("f1 sonnet: count==5", count == 5)
step("f1 sonnet: free==False", free is False)

usd, count, free = estimate_run_cost("f1", "anthropic/claude-opus-4")
step("f1 opus: usd > f1 sonnet (more expensive)", usd > 0.30)
step("f1 opus: usd < 2.00 (still under $2 for a single run)", usd < 2.00)


# --------------------------------------------------------------------------- #
#  7. Hybrid (paid_for) routes only listed agents to Sonnet
# --------------------------------------------------------------------------- #
section("7. Hybrid — paid_for routes only listed agents")
# Default ollama + paid_for=[final-report] → only final-report is Sonnet.
# 4 agents ollama (free) + 1 agent sonnet ≈ 1/5 of all-sonnet cost.
usd_hybrid, _, free = estimate_run_cost(
    "f1", "ollama/llama3.3:70b", paid_for=["final-report"]
)
usd_all_sonnet, _, _ = estimate_run_cost("f1", "anthropic/claude-sonnet-4-5")
step("hybrid cost is 0 < hybrid < all-sonnet",
     0 < usd_hybrid < usd_all_sonnet)
step("hybrid is roughly 1/5 of all-sonnet (within 0.5x-3x)",
     (usd_all_sonnet / 5) * 0.5 < usd_hybrid < (usd_all_sonnet / 5) * 3)
step("hybrid not is_free (some agents are paid)",
     free is False)

# Multiple paid agents
usd_multi, _, _ = estimate_run_cost(
    "f1", "ollama/llama3.3:70b",
    paid_for=["final-report", "senior-analyst"]
)
step("multi-paid > single-paid but <= all-sonnet",
     usd_multi > usd_hybrid and usd_multi <= usd_all_sonnet)


# --------------------------------------------------------------------------- #
#  8. format_cost_for_footer — three documented shapes
# --------------------------------------------------------------------------- #
section("8. format_cost_for_footer — three shapes")
seg = format_cost_for_footer("f1", "ollama/llama3.3:70b")
step("ollama → 'free · 5 agents'", seg == "free · 5 agents")

seg = format_cost_for_footer("f1", "anthropic/claude-sonnet-4-5")
step("sonnet → '≈ $0.16 · 5 agents' shape",
     seg == "≈ $0.16 · 5 agents" or seg.startswith("≈ $0.1"))

seg = format_cost_for_footer("f1", "totally-unknown/anything")
step("unknown → '? · 5 agents' (not free, not recognised)",
     seg == "? · 5 agents")

# Per-agent override that routes all to free wins.
seg = format_cost_for_footer(
    "f1", "anthropic/claude-sonnet-4-5",
    per_agent_model={
        "orchestrator": "ollama/llama3.3:70b",
        "senior-analyst": "ollama/llama3.3:70b",
        "forensic-accounting": "ollama/llama3.3:70b",
        "devils-advocate": "ollama/llama3.3:70b",
        "final-report": "ollama/llama3.3:70b",
    },
)
step("per_agent override to all-ollama → 'free · 5 agents'",
     seg == "free · 5 agents")


# --------------------------------------------------------------------------- #
#  9. _FLOW_AGENTS covers f1..f9 with >= 3 agents each
# --------------------------------------------------------------------------- #
section("9. _FLOW_AGENTS — f1..f9 each >= 3 agents")
from runtime.rates import _FLOW_AGENTS
for flow_id in ("f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9"):
    agents = _FLOW_AGENTS.get(flow_id)
    step(f"{flow_id} has >= 3 agents", agents is not None and len(agents) >= 3)
    step(f"{flow_id} includes orchestrator + final-report",
         agents is not None and "orchestrator" in agents and "final-report" in agents)


# --------------------------------------------------------------------------- #
# 10. _AGENT_TOKEN_ESTIMATES covers SCAN/STANDARD/DEEP for every agent
# --------------------------------------------------------------------------- #
section("10. _AGENT_TOKEN_ESTIMATES — SCAN/STANDARD/DEEP × every agent")
from runtime.rates import _AGENT_TOKEN_ESTIMATES
all_agents = set()
for flow_agents in _FLOW_AGENTS.values():
    all_agents.update(flow_agents)
for depth in ("SCAN", "STANDARD", "DEEP"):
    table = _AGENT_TOKEN_ESTIMATES.get(depth, {})
    step(f"depth={depth} exists", bool(table))
    for agent_id in all_agents:
        est = table.get(agent_id)
        step(f"  {depth}/{agent_id} has (in>0, out>0)",
             est is not None and est[0] > 0 and est[1] > 0)
    # SCAN < STANDARD < DEEP for each shared agent
    for agent_id in all_agents:
        scan = _AGENT_TOKEN_ESTIMATES["SCAN"].get(agent_id, (0, 0))
        std  = _AGENT_TOKEN_ESTIMATES["STANDARD"].get(agent_id, (0, 0))
        deep = _AGENT_TOKEN_ESTIMATES["DEEP"].get(agent_id, (0, 0))
        step(f"  {agent_id} SCAN < STANDARD < DEEP",
             scan[0] < std[0] < deep[0] and scan[1] < std[1] < deep[1])


# --------------------------------------------------------------------------- #
# 11. chat.py imports + uses format_cost_for_footer
# --------------------------------------------------------------------------- #
section("11. chat.py wires format_cost_for_footer into _update_footer_hint")
chat_src = (DOCS / "frontend" / "screens" / "chat.py").read_text(encoding="utf-8")
step("imports format_cost_for_footer", "from runtime.rates import format_cost_for_footer" in chat_src)
step("calls it inside _update_footer_hint", "format_cost_for_footer(" in chat_src)
step("passes self.flow_id", "self.flow_id" in chat_src.split("def _update_footer_hint")[1].split("def ")[0])
step("passes self.model", "self.model" in chat_src.split("def _update_footer_hint")[1].split("def ")[0])
step("passes self.paid_for", "paid_for=self.paid_for" in chat_src)
step("passes self.depth", "depth=self.depth" in chat_src)
step("passes self.per_agent_model", "per_agent_model=self.per_agent_model" in chat_src)
step("formats 'cost_segment' into the footer base",
     "{cost_segment}" in chat_src.split("def _update_footer_hint")[1].split("def ")[0])

# Footer still has the old fields (model, paid-for, depth).
step("still includes model in footer base",
     "self.model" in chat_src.split("def _update_footer_hint")[1].split("def ")[0])
step("still includes paid-for in footer base",
     "paid-for:" in chat_src.split("def _update_footer_hint")[1].split("def ")[0])
step("still includes depth in footer base",
     "depth:" in chat_src.split("def _update_footer_hint")[1].split("def ")[0])


print()
total = _passed + _failed
print(f"{_passed}/{total} ok")
if _failed:
    print(f"{_failed} FAIL")
    sys.exit(1)
print("0 fail")
print("all green")
sys.exit(0)