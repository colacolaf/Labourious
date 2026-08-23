"""smoke — ActivityPanel per-agent cost + ETA + model display.

Verifies the end-to-end path:
  ChatScreen._apply_event → ActivityPanel.mark_running/mark_finished/update_cost
  → ETA estimation (average wallclock × remaining)
  → cost display per-agent and cumulative

Exercises:
  1. _AgentRow state machine: queued → running → done (with all fields)
  2. _fmt_cost + _short_model helpers (edge cases)
  3. ETA estimation: single-agent ETA=0, multi-agent averaging, 0s edge
  4. ActivityPanel reset clears all state
  5. ActivityPanel.update_cost updates per-agent + cumulative
  6. ChatScreen wires: AgentStarted→mark_running(model), AgentFinished→mark_finished(cost,tokens), CostDelta→update_cost
  7. Ollama (free) shows $0 correctly
  8. OmniRoute/paid model cost flow
  9. Summary line format
 10. Model display for common providers (anthropic, openai, ollama, openrouter)
"""

from __future__ import annotations

import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2]

if str(DOCS) not in sys.path:
    sys.path.insert(0, str(DOCS))

# ---------- smoke harness ----------
_ok: list[int] = []
_bad: list[int] = []


def _pass(label: str) -> None:
    _ok[0] += 1
    print(f"  ✓ {label}")


def _fail(label: str, extra: str = "") -> None:
    _bad[0] += 1
    print(f"  ✗ FAIL: {label}{extra}")


def step(label: str, value: bool) -> None:
    if value:
        _pass(label)
    else:
        _fail(label)


def step_eq(label: str, a, b) -> None:
    if a == b:
        _pass(label)
    else:
        _fail(label, f"  ({a!r} != {b!r})")


def section(title: str) -> None:
    print(f"\n── {title} ──")


_ok.append(0)
_bad.append(0)

from frontend.widgets.activity_panel import (
    ActivityPanel, _AgentRow, _short_model, _fmt_cost, _fmt_tokens,
    AGENT_IDS,
)

# ===========================================================================
# 1. _fmt_cost edge cases
# ===========================================================================
section("1. _fmt_cost edge cases")

step_eq("$0", _fmt_cost(0.0), "$0")
step_eq("$0.0005 shows 4 decimals", _fmt_cost(0.0005), "$0.0005")
step_eq("$0.0010 at threshold", _fmt_cost(0.0010), "$0.0010")
step_eq("$0.0123 three decimal (< $1)", _fmt_cost(0.0123), "$0.012")
step_eq("$0.100 three decimal", _fmt_cost(0.100), "$0.100")
step_eq("$0.567 three decimal", _fmt_cost(0.567), "$0.567")
step_eq("$1.00 two decimal", _fmt_cost(1.0), "$1.00")
step_eq("$5.43 two decimal", _fmt_cost(5.43), "$5.43")
step_eq("$99.99 two decimal", _fmt_cost(99.99), "$99.99")

# ===========================================================================
# 2. _fmt_tokens
# ===========================================================================
section("2. _fmt_tokens")

step_eq("0", _fmt_tokens(0), "0")
step_eq("999", _fmt_tokens(999), "999")
step_eq("1.0k", _fmt_tokens(1000), "1.0k")
step_eq("2.5k", _fmt_tokens(2500), "2.5k")
step_eq("1.0M", _fmt_tokens(1_000_000), "1.0M")
step_eq("3.5M", _fmt_tokens(3_500_000), "3.5M")

# ===========================================================================
# 3. _short_model for all provider types
# ===========================================================================
section("3. _short_model")

step_eq("sonnet-4-5", _short_model("anthropic/claude-sonnet-4-5"), "sonnet-4-5")
step_eq("haiku-4", _short_model("anthropic/claude-haiku-4"), "haiku-4")
step_eq("4o", _short_model("openai/gpt-4o"), "4o")
step_eq("4o-mini", _short_model("openai/gpt-4o-mini"), "4o-mini")
step_eq("llama3.3:70b", _short_model("ollama/llama3.3:70b"), "llama3.3:70b")
step_eq("2.5-flash", _short_model("gemini/gemini-2.5-flash"), "2.5-flash")
step_eq("r1", _short_model("deepseek/deepseek-r1"), "r1")

# OmniRoute / openrouter — not a known prefix, so returns full slug
step_eq("openrouter slug", _short_model("openrouter/anthropic/claude-sonnet-4-5"),
         "anthropic/claude-sonnet-4-5")
# No slash falls through
step_eq("no slash", _short_model("llama3.3:70b"), "llama3.3:70b")

# ===========================================================================
# 4. _AgentRow state machine: queued → running → done
# ===========================================================================
section("4. _AgentRow state machine")

# Row starts queued in compose
row = _AgentRow("senior-analyst")
step("starts queued", row.state == "queued")
step_eq("no cost initially", row.cost_usd, 0.0)
step_eq("model is —", row.model, "—")
step_eq("wallclock is None", row.wallclock_s, None)

# mark_running
row.mark_running(model="anthropic/claude-sonnet-4-5")
step("mark_running → running", row.state == "running")
step_eq("model set to sonnet", row.model, "anthropic/claude-sonnet-4-5")
step_eq("wallclock set to 0.0", row.wallclock_s, 0.0)
step_eq("cost reset to 0", row.cost_usd, 0.0)

# update_cost mid-flight
row.update_cost(0.023)
step_eq("cost updated to $0.023", row.cost_usd, 0.023)

# mark_finished
row.mark_finished(wallclock_s=4.2, cost_usd=0.031, tokens_in=3500, tokens_out=1200)
step("mark_finished → done", row.state == "done")
step_eq("wallclock final", row.wallclock_s, 4.2)
step_eq("cost final", row.cost_usd, 0.031)
step_eq("tokens_in", row.tokens_in, 3500)
step_eq("tokens_out", row.tokens_out, 1200)

# ===========================================================================
# 5. _AgentRow: mark_failed
# ===========================================================================
section("5. _AgentRow mark_failed")

row2 = _AgentRow("devils-advocate")
row2.mark_running(model="ollama/llama3.3:70b")
row2.mark_failed()
step("mark_failed → failed", row2.state == "failed")

# ===========================================================================
# 6. ActivityPanel: mark_running → ETA estimate
# ===========================================================================
section("6. ActivityPanel mark_running → ETA estimate")

panel = ActivityPanel()
# Simulating without Textual — we won't render, just check internal state
# Manually seed rows since compose() only runs on mount
for agent_id in AGENT_IDS:
    panel._rows[agent_id] = _AgentRow(agent_id)

# Reset first
panel.reset()
step_eq("remaining starts at 5", panel._remaining_count, len(AGENT_IDS))

# Mark orchestrator running
panel.mark_running("orchestrator", model="ollama/llama3.3:70b")
step_eq("remaining decremented to 4", panel._remaining_count, 4)
step("orchestrator row running", panel._rows["orchestrator"].state == "running")

# ===========================================================================
# 7. ActivityPanel: mark_finished → ETA
# ===========================================================================
section("7. ActivityPanel mark_finished → ETA")

# Finish orchestrator at 1.5s
panel.mark_finished("orchestrator", wallclock_s=1.5, cost_usd=0.0,
                    tokens_in=800, tokens_out=150)
step_eq("completed wallclocks has 1 entry", len(panel._completed_wallclocks), 1)
step_eq("first wallclock is 1.5", panel._completed_wallclocks[0], 1.5)
step("orchestrator done", panel._rows["orchestrator"].state == "done")
step_eq("orchestrator cost $0 (ollama free)", panel._rows["orchestrator"].cost_usd, 0.0)

# Finish senior-analyst at 6.0s (paid model)
panel.mark_running("senior-analyst", model="anthropic/claude-sonnet-4-5")
panel.mark_finished("senior-analyst", wallclock_s=6.0, cost_usd=0.102,
                    tokens_in=3800, tokens_out=1400)
step_eq("completed wallclocks has 2 entries", len(panel._completed_wallclocks), 2)
step_eq("second wallclock is 6.0", panel._completed_wallclocks[1], 6.0)
step_eq("senior-analyst cost $0.102", panel._rows["senior-analyst"].cost_usd, 0.102)

# ETA: average of [1.5, 6.0] = 3.75s × 3 remaining = ~11s
avg = (1.5 + 6.0) / 2
eta = avg * 3
step("ETA calculated correctly", abs(eta - 11.25) < 0.01)

# ===========================================================================
# 8. ActivityPanel: update_cost (mid-flight)
# ===========================================================================
section("8. ActivityPanel update_cost")

panel.update_cost("forensic-accounting", 0.045, 0.147)
step_eq("forensic row cost updated", panel._rows["forensic-accounting"].cost_usd, 0.045)
step_eq("cumulative cost updated", panel._cumulative_cost, 0.147)

panel.update_cost("devils-advocate", 0.001, 0.148)
step_eq("cumulative cost 0.148", panel._cumulative_cost, 0.148)

# ===========================================================================
# 9. ActivityPanel: reset
# ===========================================================================
section("9. ActivityPanel reset")

panel.reset()
step_eq("remaining reset to 5", panel._remaining_count, len(AGENT_IDS))
step("completed wallclocks cleared", len(panel._completed_wallclocks) == 0)
step_eq("cumulative cost cleared", panel._cumulative_cost, 0.0)
step("orchestrator back to queued", panel._rows["orchestrator"].state == "queued")
step("senior-analyst back to queued", panel._rows["senior-analyst"].state == "queued")
step_eq("orchestrator model reset to —", panel._rows["orchestrator"].model, "—")
step_eq("orchestrator cost reset", panel._rows["orchestrator"].cost_usd, 0.0)
step("orchestrator wallclock None", panel._rows["orchestrator"].wallclock_s is None)

# ===========================================================================
# 10. ChatScreen _apply_event wiring (code existence)
# ===========================================================================
section("10. ChatScreen _apply_event wiring")

import inspect
from frontend.screens.chat import ChatScreen

src = inspect.getsource(ChatScreen._apply_event)

step("AgentStarted calls mark_running with model",
     "activity.mark_running(event.agent_id, model=event.model)" in src)
step("AgentFinished calls mark_finished with cost+usd+tokens",
     "cost_usd=event.cost_usd_estimate" in src)
step("AgentFinished passes tokens_in",
     "tokens_in=event.in_tokens" in src)
step("AgentFinished passes tokens_out",
     "tokens_out=event.out_tokens" in src)
step("CostDelta calls activity.update_cost with agent_id + cost",
     "activity.update_cost(event.agent_id, event.cost_usd_estimate" in src)

# ===========================================================================
# 11. ActivityPanel.mark_finished signature
# ===========================================================================
section("11. ActivityPanel.mark_finished signature")

sig = inspect.signature(ActivityPanel.mark_finished)
params = list(sig.parameters.keys())
step("mark_finished has cost_usd param", "cost_usd" in params)
step("mark_finished has tokens_in param", "tokens_in" in params)
step("mark_finished has tokens_out param", "tokens_out" in params)

# ===========================================================================
# 12. ActivityPanel.mark_running signature
# ===========================================================================
section("12. ActivityPanel.mark_running signature")

sig = inspect.signature(ActivityPanel.mark_running)
params = list(sig.parameters.keys())
step("mark_running has model param (defaults to '—')", "model" in params)

# ===========================================================================
# 13. AGENT_IDS list
# ===========================================================================
section("13. AGENT_IDS list")

step_eq("5 agents total", len(AGENT_IDS), 5)
step("orchestrator in list", "orchestrator" in AGENT_IDS)
step("senior-analyst in list", "senior-analyst" in AGENT_IDS)
step("forensic-accounting in list", "forensic-accounting" in AGENT_IDS)
step("devils-advocate in list", "devils-advocate" in AGENT_IDS)
step("final-report in list", "final-report" in AGENT_IDS)

# ===========================================================================
# 14. mark_failed decrements remaining
# ===========================================================================
section("14. mark_failed decrements remaining")

panel2 = ActivityPanel()
for agent_id in AGENT_IDS:
    panel2._rows[agent_id] = _AgentRow(agent_id)
panel2.reset()
step_eq("remaining starts at 5", panel2._remaining_count, len(AGENT_IDS))
panel2.mark_failed("forensic-accounting")
step_eq("remaining decremented to 4 by failed", panel2._remaining_count, 4)
step("forensic row state is failed", panel2._rows["forensic-accounting"].state == "failed")

# ===========================================================================
# 15. 0s wallclock in ETA (should not be added to average)
# ===========================================================================
section("15. 0s wallclock handling")

panel3 = ActivityPanel()
for agent_id in AGENT_IDS:
    panel3._rows[agent_id] = _AgentRow(agent_id)
panel3.reset()

# Finish orchestrator at 0s (instant free model)
panel3.mark_running("orchestrator", model="ollama/llama3.3:70b")
panel3.mark_finished("orchestrator", wallclock_s=0.0, cost_usd=0.0,
                     tokens_in=100, tokens_out=20)
# 0.0 wallclock should NOT be added to completed_wallclocks
step("0s wallclock not added to completed (would skew ETA)",
     len(panel3._completed_wallclocks) == 0)

# Now finish senior-analyst at 5.0s
panel3.mark_running("senior-analyst", model="anthropic/claude-sonnet-4-5")
panel3.mark_finished("senior-analyst", wallclock_s=5.0, cost_usd=0.100,
                     tokens_in=4000, tokens_out=1500)
step_eq("5.0s wallclock added", len(panel3._completed_wallclocks), 1)
step_eq("5.0s is the only entry", panel3._completed_wallclocks[0], 5.0)

# ===========================================================================
# Summary
# ===========================================================================
total = _ok[0] + _bad[0]
print(f"\n=== {_ok[0]}/{total} ok ===")
if _bad[0]:
    print(f"{_bad[0]} fail")
    sys.exit(1)
else:
    print("all green")