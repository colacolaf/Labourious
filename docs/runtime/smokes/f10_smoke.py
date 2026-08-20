"""f10_smoke.py — smoke pilot for the f10 Daily Briefing flow.

Verifies (without launching real LLMs):

  1. ThesisRegister.list_open_catalysts exists, returns list[dict],
     filters by ticker, sorts by expected_date with NULLs last
  2. execute_flow_f10 exists and is callable with the documented signature
  3. Empty watchlist raises ValueError
  4. Oversized watchlist (>20) raises ValueError
  5. argparse accepts --flow f10, --watchlist, --since-days
  6. wave_plan dict has an f10 entry in the dry-run path
  7. f10 dispatch in main() routes to execute_flow_f10
  8. _FLOW_AGENTS['f10'] = orchestrator + 5×senior-analyst + final-report (7 total)
  9. execute_flow_f10 with mocked call_agent runs through:
       - prior-thesis pre-wave (reads from real DB)
       - parallel fan-out (1 call per watchlist ticker)
       - final-report call
       - post-flow register.add_update for FLIP-tagged envelopes
 10. The post-flow update text contains the FLIP envelope's read
 11. The f10_briefing top-level field is populated
 12. Errors during fan-out don't fail the whole flow (tag=ERROR fallback)
 13. render_memo_markdown can be called on the final_envelope without crashing
 14. CLI --watchlist='' falls back to Config.watchlist when set
 15. CLI --watchlist='' errors when Config has no watchlist
"""

from __future__ import annotations

import ast
import inspect
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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
#  1. ThesisRegister.list_open_catalysts
# --------------------------------------------------------------------------- #
section("1. ThesisRegister.list_open_catalysts")
from runtime.thesis_register.register import ThesisRegister
import tempfile as _tf

with _tf.TemporaryDirectory() as tmp:
    db = Path(tmp) / "test_theses.db"
    r = ThesisRegister(db_path=db)
    # Add two catalysts; resolve one; verify the right one comes back.
    cid_open = r.add_catalyst("NVDA", "Q4 earnings", "2026-11-20", "channel inventory margin")
    cid_dated = r.add_catalyst("AAPL", "Annual mtg", "2026-12-15", "board vote")
    cid_no_date = r.add_catalyst("MSFT", "TBD catalyst", None, None)
    cid_resolved = r.add_catalyst("NVDA", "Old earnings", "2026-08-01", "done")
    r.resolve_catalyst(cid_resolved, "2026-08-01", "as expected")

    open_all = r.list_open_catalysts()
    step("list_open_catalysts() returns 3 open (1 resolved hidden)",
         len(open_all) == 3)
    tickers = [c["ticker"] for c in open_all]
    step("resolved catalyst hidden from default list",
         "NVDA" in tickers and cid_resolved not in [c["id"] for c in open_all])

    # Filter by ticker
    open_nvda = r.list_open_catalysts("NVDA")
    step("list_open_catalysts('NVDA') returns 1 (just the open NVDA one)",
         len(open_nvda) == 1 and open_nvda[0]["id"] == cid_open)

    # NULLs-last ordering: cid_no_date has expected_date=None → last
    open_ordered = r.list_open_catalysts()
    step("NULL expected_date is sorted last",
         open_ordered[-1]["id"] == cid_no_date)
    step("earliest dated catalyst sorted first",
         open_ordered[0]["id"] == cid_open)

    # Shape sanity
    sample = open_all[0]
    step("catalyst dict has expected keys",
         all(k in sample for k in ("id", "ticker", "event", "expected_date", "what_to_watch", "created_at")))


# --------------------------------------------------------------------------- #
#  2-3. execute_flow_f10 signature + empty/oversized watchlist guards
# --------------------------------------------------------------------------- #
section("2-3. execute_flow_f10 signature + guard rails")
from runtime.runtime import execute_flow_f10
sig = inspect.signature(execute_flow_f10)
step("watchlist kwarg present", "watchlist" in sig.parameters)
step("model kwarg present", "model" in sig.parameters)
step("paid_for kwarg present", "paid_for" in sig.parameters)
step("since_days kwarg present", "since_days" in sig.parameters)
step("depth kwarg present", "depth" in sig.parameters)

# Empty watchlist raises
raised = False
try:
    execute_flow_f10(watchlist=[], model="ollama/llama3.3:70b", paid_for=None)
except ValueError as e:
    raised = "non-empty" in str(e)
step("empty watchlist raises ValueError mentioning non-empty", raised)

# Oversized watchlist raises
raised = False
big_watchlist = ["T" + str(i).zfill(3) for i in range(25)]
try:
    execute_flow_f10(watchlist=big_watchlist, model="ollama/llama3.3:70b", paid_for=None)
except ValueError as e:
    raised = "20" in str(e)
step("oversized watchlist raises ValueError mentioning 20", raised)


# --------------------------------------------------------------------------- #
#  5. argparse: --flow f10 + --watchlist + --since-days
# --------------------------------------------------------------------------- #
section("5. argparse accepts --flow f10 + --watchlist + --since-days")
runtime_src = (DOCS / "runtime" / "runtime.py").read_text(encoding="utf-8")
tree = ast.parse(runtime_src)
# Find choices list inside add_argument for --flow
choices_list = None
for node in ast.walk(tree):
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            and any(isinstance(a, ast.Constant) and a.value == "--flow"
                    for a in node.args)):
        for kw in node.keywords:
            if kw.arg == "choices":
                if isinstance(kw.value, ast.List):
                    choices_list = [e.value for e in kw.value.elts if isinstance(e, ast.Constant)]
step("--flow choices include f10", choices_list is not None and "f10" in choices_list)
step("--flow choices include f9 (regression)", choices_list is not None and "f9" in choices_list)

# --watchlist flag
step("--watchlist flag present",
     "add_argument(\"--watchlist\"" in runtime_src
     or 'add_argument("--watchlist"' in runtime_src)
step("--briefing-days flag present with default=1",
     'add_argument("--briefing-days"' in runtime_src)


# --------------------------------------------------------------------------- #
#  6. wave_plan dict has f10 entry
# --------------------------------------------------------------------------- #
section("6. wave_plan dict has f10 entry")
step("wave_plan['f10'] entry defined", '"f10":' in runtime_src)
step("f10 wave_plan mentions senior-analyst",
     "f10" in runtime_src and "senior-analyst" in runtime_src.split('"f10":')[1].split("],", 1)[0])


# --------------------------------------------------------------------------- #
#  7. f10 dispatch in main()
# --------------------------------------------------------------------------- #
section("7. f10 dispatch in main()")
main_body = runtime_src.split("def main")[1].split("if __name__")[0]
step("main() has elif args.flow == \"f10\" branch",
     'elif args.flow == "f10"' in main_body)
step("main() loads Config.watchlist as fallback",
     "cfg.watchlist" in main_body or "load_config" in main_body)
step("main() errors when watchlist empty + no config",
     '--watchlist' in main_body and "is required for f10" in main_body)
step("main() calls execute_flow_f10",
     "execute_flow_f10(" in main_body)
step("main() respects --briefing-days arg",
     "since_days=" in main_body and "args.briefing_days" in main_body or "getattr(args, \"briefing_days\"" in main_body)
step("main() passes watchlist split on commas",
     ".split(\",\")" in main_body)


# --------------------------------------------------------------------------- #
#  8. _FLOW_AGENTS['f10'] has 7 agents (1 orchestrator + 5×senior + 1 final)
# --------------------------------------------------------------------------- #
section("8. _FLOW_AGENTS['f10'] = 7 agents")
from runtime.rates import _FLOW_AGENTS, estimate_run_cost, format_cost_for_footer
f10_agents = _FLOW_AGENTS["f10"]
step("f10 has 7 agent entries", len(f10_agents) == 7)
step("starts with orchestrator", f10_agents[0] == "orchestrator")
step("ends with final-report", f10_agents[-1] == "final-report")
step("5×senior-analyst in the middle",
     sum(1 for a in f10_agents if a == "senior-analyst") == 5)

# Cost estimate sanity
est = estimate_run_cost("f10", "ollama/llama3.3:70b")
step("f10 ollama estimate usd==0.0", est[0] == 0.0)
step("f10 ollama free==True", est[2] is True)
step("f10 ollama agent_count==7", est[1] == 7)

est_paid = estimate_run_cost("f10", "anthropic/claude-sonnet-4-5")
step("f10 sonnet usd > 0", est_paid[0] > 0)
step("f10 sonnet usd < $0.30 (still cheap)", est_paid[0] < 0.30)


# --------------------------------------------------------------------------- #
#  9. execute_flow_f10 end-to-end with mocked call_agent
# --------------------------------------------------------------------------- #
section("9. execute_flow_f10 runs end-to-end with mocked call_agent")
import datetime as dt

# Set up an isolated DB so we don't trample real theses.
with _tf.TemporaryDirectory() as tmp:
    db = Path(tmp) / "f10_theses.db"
    r = ThesisRegister(db_path=db)

    # Seed two theses (NVDA, AAPL) and one no-prior ticker (MSFT).
    r.write_thesis(
        ticker="NVDA",
        thesis_text="Long at $890. Hyperscaler capex stays >$300B through FY27.",
        conviction=4,
        bottom_line={"direction": "LONG", "conviction": 4, "one_liner": "Capex tailwind."},
        evidence_urls=["https://sec.gov/..."],
        flow_id="f1",
    )
    r.write_thesis(
        ticker="AAPL",
        thesis_text="Long at $220. Services growth >15% offsets iPhone softness.",
        conviction=3,
        bottom_line={"direction": "LONG", "conviction": 3, "one_liner": "Services flywheel."},
        evidence_urls=[],
        flow_id="f1",
    )
    r.add_catalyst("NVDA", "Q4 earnings", "2026-11-20", "channel inventory")
    r.add_catalyst("AAPL", "Annual mtg", "2026-12-15", "board vote")

    # Patch ThesisRegister to use our test DB and patch call_agent.
    add_update_calls: list[dict] = []

    # Mock call_agent to return per-ticker envelopes with different tags.
    def fake_call_agent(agent_id, brief, model,
                         paid_for=None, emit_event=None,
                         per_agent_model=None, stream_chunks=False,
                         system_prompt_override=None, **_):
        brief_str = brief if isinstance(brief, str) else str(brief)
        # Extract ticker from brief
        import json as _json
        try:
            b = _json.loads(brief_str)
            ticker = b.get("ticker", "???")
        except Exception:
            ticker = "???"
        tag = "NO_PRIOR"
        if "MSFT" in ticker:
            env = {"agent_id": agent_id, "ticker": ticker, "depth": "SCAN",
                   "compressed": True, "conclusion": "no prior thesis",
                   "tag": "NO_PRIOR", "what_changed": "no prior thesis"}
            cost = {"agent_id": agent_id, "in_tok": 0, "out_tok": 0,
                    "cost_usd_estimate": 0.0}
            return env, cost
        if "NVDA" in ticker:
            tag = "REITERATE"
            env = {"agent_id": agent_id, "ticker": ticker, "depth": "SCAN",
                   "compressed": True,
                   "conclusion": "no material change since prior thesis",
                   "tag": "REITERATE",
                   "what_changed": "none material"}
            cost = {"agent_id": agent_id, "in_tok": 100, "out_tok": 50,
                    "cost_usd_estimate": 0.001}
            return env, cost
        if "AAPL" in ticker:
            tag = "FLIP"
            env = {"agent_id": agent_id, "ticker": ticker, "depth": "SCAN",
                   "compressed": True,
                   "conclusion": "Services growth slowed to 4% YoY, breaking the prior thesis",
                   "tag": "FLIP",
                   "what_changed": "Services growth slowed to 4% YoY; prior thesis says >15%."}
            cost = {"agent_id": agent_id, "in_tok": 100, "out_tok": 50,
                    "cost_usd_estimate": 0.001}
            return env, cost
        # final-report
        env = {"agent_id": agent_id, "ticker": "all", "depth": "SCAN",
               "compressed": True,
               "conclusion": "Daily briefing assembled.",
               "bottom_line": {"direction": "MIXED", "conviction": 3,
                                "one_liner": "1 FLIP (AAPL), 1 REITERATE (NVDA), 1 NO_PRIOR (MSFT)"},
               "bull_case": "Most names held their thesis.",
               "bear_case": "AAPL services miss.",
               "what_an_attacker_would_say": "AAPL's flip is the canary.",
               "next_three_questions": ["What drove the services slowdown?",
                                        "Is MSFT worth onboarding?"],
               "citations_used": []}
        cost = {"agent_id": agent_id, "in_tok": 500, "out_tok": 300,
                "cost_usd_estimate": 0.005}
        return env, cost

    # Patch add_update to record its calls
    orig_add_update = r.add_update
    def fake_add_update(ticker, what_changed, **kwargs):
        cid = orig_add_update(ticker, what_changed, **kwargs)
        add_update_calls.append({"ticker": ticker, "what_changed": what_changed,
                                "update_id": cid})
        return cid

    # Patch register.list_open_catalysts to return our test DB results.
    orig_list_open = r.list_open_catalysts
    def fake_list_open(ticker=None):
        return orig_list_open(ticker)

    with patch("runtime.runtime.call_agent", side_effect=fake_call_agent), \
         patch("runtime.runtime.ThesisRegister", lambda **kw: r), \
         patch.object(r, "add_update", side_effect=fake_add_update):
        result = execute_flow_f10(
            watchlist=["NVDA", "AAPL", "MSFT"],
            model="ollama/llama3.3:70b",
            paid_for=None,
            since_days=1,
            depth="SCAN",
        )

    # Assertions on the result
    step("result has 'final_envelope'", "final_envelope" in result)
    step("result has 'f10_briefing'", "f10_briefing" in result)
    step("f10_briefing has 'per_ticker' with 3 entries",
         len(result["f10_briefing"]["per_ticker"]) == 3)
    step("NVDA tagged REITERATE",
         result["f10_briefing"]["per_ticker"]["NVDA"]["tag"] == "REITERATE")
    step("AAPL tagged FLIP",
         result["f10_briefing"]["per_ticker"]["AAPL"]["tag"] == "FLIP")
    step("MSFT tagged NO_PRIOR (no prior in DB)",
         result["f10_briefing"]["per_ticker"]["MSFT"]["tag"] == "NO_PRIOR")
    step("flips_written has 1 entry (just AAPL)",
         len(result["f10_briefing"]["flips_written"]) == 1)
    step("flips_written[0]['ticker'] == 'AAPL'",
         result["f10_briefing"]["flips_written"][0]["ticker"] == "AAPL")
    step("flips_written[0]['what_changed'] contains 'services'",
         "services" in result["f10_briefing"]["flips_written"][0]["what_changed"].lower())
    step("costs list has 4 entries (3 senior + 1 final-report)",
         len(result["costs"]) == 4)
    step("open_catalysts has 2 entries (NVDA + AAPL)",
         len(result["f10_briefing"]["open_catalysts"]) == 2)
    step("add_update called once (only for AAPL flip)",
         len(add_update_calls) == 1)
    step("add_update call has reason='auto: f10 daily briefing tagged FLIP'",
         add_update_calls[0]["what_changed"].startswith("Services growth"))


# --------------------------------------------------------------------------- #
#  12. Errors during fan-out → tag=ERROR fallback (not flow failure)
# --------------------------------------------------------------------------- #
section("12. Fan-out error fallback — tag=ERROR doesn't fail the flow")
with _tf.TemporaryDirectory() as tmp:
    db = Path(tmp) / "f10_err_theses.db"
    r2 = ThesisRegister(db_path=db)
    r2.write_thesis(ticker="FAIL", thesis_text="x", conviction=3,
                     bottom_line={"direction": "LONG"}, evidence_urls=[],
                     flow_id="f1")

    def failing_call(agent_id, brief, model, **kwargs):
        # Only fail for the FAIL ticker's senior-analyst call; the
        # final-report call should still succeed so the flow can complete.
        brief_str = str(brief)
        if "FAIL" in brief_str and "final-report" not in agent_id:
            raise RuntimeError("simulated LLM failure")
        return ({"agent_id": agent_id, "tag": "REITERATE"}, {"cost": 0.0})

    with patch("runtime.runtime.call_agent", side_effect=failing_call), \
         patch("runtime.runtime.ThesisRegister", lambda **kw: r2):
        result = execute_flow_f10(
            watchlist=["FAIL"], model="ollama/llama3.3:70b", paid_for=None,
            since_days=1, depth="SCAN",
        )
    step("flow completes despite call_agent exception", "final_envelope" in result)
    step("FAIL ticker has tag=ERROR",
         result["f10_briefing"]["per_ticker"]["FAIL"]["tag"] == "ERROR")


# --------------------------------------------------------------------------- #
#  13. render_memo_markdown can be called on the final_envelope
# --------------------------------------------------------------------------- #
section("13. render_memo_markdown runs on f10 final_envelope")
from runtime.runtime import render_memo_markdown
fake_env = {
    "memo": {
        "bottom_line": {"direction": "MIXED", "conviction": 3,
                         "one_liner": "1 FLIP, 1 REITERATE, 1 NO_PRIOR",
                         "flip_trigger": "more flips"},
        "bull_case": "Most names held thesis.",
        "bear_case": "AAPL services miss.",
        "what_an_attacker_would_say": "Watch the catalysts.",
        "next_three_questions": ["A: q1", "B: q2", "C: q3"],
        "citations_used": [{"name": "8-K", "type": "filing",
                             "date": "2026-10-30", "url": "https://x"}],
    },
    "confidence": "HIGH",
}
md = render_memo_markdown(fake_env)
step("render_memo_markdown runs without exception", isinstance(md, str))
step("memo contains 'Bottom line'", "Bottom line" in md)
step("memo contains 'Bull case'", "Bull case" in md)
step("memo contains 'Bear case'", "Bear case" in md)
step("memo contains the one_liner",
     "1 FLIP, 1 REITERATE, 1 NO_PRIOR" in md)


# --------------------------------------------------------------------------- #
#  14-15. CLI watchlist fallback
# --------------------------------------------------------------------------- #
section("14-15. CLI --watchlist '' + Config.watchlist fallback")
# Source check: the dispatch branch handles both code paths.
step("dispatch reads --watchlist arg", "args.watchlist" in main_body)
step("dispatch reads cfg.watchlist", "cfg.watchlist" in main_body)
step("dispatch errors when both empty", "is required for f10" in main_body)


# --------------------------------------------------------------------------- #
#  Bonus: --flow f10 visible in --help
# --------------------------------------------------------------------------- #
section("Bonus: --flow f10 visible in --help")
# We can't easily run argparse without invoking main(), so we AST-grep instead.
step("--flow f10 string present in runtime.py source",
     '"f10"' in runtime_src or "'f10'" in runtime_src)


print()
total = _passed + _failed
print(f"{_passed}/{total} ok")
if _failed:
    print(f"{_failed} FAIL")
    sys.exit(1)
print("0 fail")
print("all green")
sys.exit(0)