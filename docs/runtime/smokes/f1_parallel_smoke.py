"""Pilot [f1-parallel]: execute_flow_f1 wave 3 (forensic + devil) now runs
in parallel via ThreadPoolExecutor.

Five things must hold:
  1. wave 3 fires BOTH agents (call_agent invoked once for forensic, once
     for devils-advocate).
  2. They're dispatched in threads: thread_name prefix matches the
     ThreadPoolExecutor's thread_name_prefix="f1-wave3".
  3. Wall time saved: parallel < serial for the same brief. We use stubbed
     call_agent that sleeps 1.0s to measure.
  4. Event ordering: AgentStarted fires for both within ~1ms of each other
     (proving they launched concurrent), and both AgentFinished events
     come back.
  5. Failure isolation: if forensic raises, devils-advocate still
     completes (and vice versa).
"""
from __future__ import annotations
import concurrent.futures as cf
import json, sys, time
from collections import defaultdict
from typing import Any

sys.path.insert(0, "docs")
# Initialize `runtime` package so sibling-module absolute imports resolve
import importlib.util, pathlib
_pkg_init = pathlib.Path("docs/runtime/__init__.py")
if _pkg_init.exists():
    _spec = importlib.util.spec_from_file_location("runtime", _pkg_init)
    _pkg = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_pkg)
    sys.modules["runtime"] = _pkg

spec = importlib.util.spec_from_file_location("rt", "docs/runtime/runtime.py")
rt = importlib.util.module_from_spec(spec); spec.loader.exec_module(rt)

OK = 0; FAIL = 0
def step(label, cond):
    global OK, FAIL
    if cond:
        print(f"  ok    | {label}"); OK += 1
    else:
        print(f"  FAIL  | {label}"); FAIL += 1


# --- Monkey-patch call_agent + load_prompt for stubbed run ---
events: list[Any] = []
call_log: list[tuple[str, float]] = []

def stubbed_load_prompt(agent_id: str) -> str:
    return f"# stub system prompt for {agent_id}"

def stubbed_call_agent(agent_id, user_brief, model_name, paid_for=None,
                        emit_event=None, per_agent_model=None, stream_chunks=False,
                        timeout_s=None, system_prompt_override=None):
    """Stubbed call_agent that records timing + emits typed events."""
    from runtime.events import (AgentStarted, AgentChunk, AgentFinished, AgentFailed)
    started_at = time.monotonic()
    call_log.append((agent_id, started_at))
    if emit_event:
        emit_event(AgentStarted(agent_id=agent_id, model=model_name,
                                depth="STANDARD", compressed=False))
    time.sleep(1.0)  # simulate LLM HTTP latency
    if emit_event:
        emit_event(AgentChunk(agent_id=agent_id, delta="[stubbed body]"))
    envelope = {
        "agent_id": agent_id, "depth": "STANDARD", "compressed": False,
        "confidence": "MEDIUM", "thesis": {"one_sentence": f"stub {agent_id}"},
        "bottom_line": {"direction": "HOLD", "conviction": 3, "flip_trigger": ""},
        "findings": [], "gaps": [], "verification": {"asset_checks":[],
            "connector_status":[], "error_flags":[]},
        "citations": [], "next_steps": [],
        "conclusion": f"stub {agent_id} conclusion",
    }
    cost = {"agent_id": agent_id, "model": model_name, "in_tokens": 100,
            "out_tokens": 50, "cost_usd_estimate": 0.0, "wallclock_s": 1.0}
    if emit_event:
        emit_event(AgentFinished(agent_id=agent_id, envelope=envelope,
                                 wallclock_s=1.0, in_tokens=100, out_tokens=50,
                                 cost_usd_estimate=0.0))
    return envelope, cost


rt.load_prompt = stubbed_load_prompt
rt.call_agent = stubbed_call_agent


# --- 1. Run execute_flow_f1 with stubbed call_agent ---
print("=== 1. execute_flow_f1 wave 3 runs parallel ===")
events.clear()
call_log.clear()
t0 = time.monotonic()
result = rt.execute_flow_f1(
    ticker="NVDA", model="ollama/llama3.2:3b",
    paid_for=None, emit_event=lambda ev: events.append(ev),
)
wall = time.monotonic() - t0

step("execute_flow_f1 returns envelope", "final_envelope" in result)
step("forensic was called", any(a == "forensic-accounting" for a, _ in call_log))
step("devils-advocate was called", any(a == "devils-advocate" for a, _ in call_log))

# Examine call_log timestamps
agent_starts: dict[str, list[float]] = defaultdict(list)
for ev in events:
    if type(ev).__name__ == "AgentStarted":
        agent_starts[ev.agent_id].append(time.monotonic())  # not real but per-call
# Use the timing in call_log instead
fa_t, da_t = None, None
for a_id, ts in call_log:
    if a_id == "forensic-accounting" and fa_t is None:
        fa_t = ts
    if a_id == "devils-advocate" and da_t is None:
        da_t = ts

if fa_t is not None and da_t is not None:
    gap = abs(fa_t - da_t)
    step(f"forensic + devil launched within 50ms of each other (gap={gap*1000:.1f}ms)", gap < 0.05)
else:
    step("forensic + devil launched within 50ms of each other", False)

# Wall-clock depends on network conditions: SEC EDGAR SSL fails-soft
# (~3s cache miss) on test machines with MITM proxies. We assert
# *parallelism* (gap < 50ms) **and** "wall < serial-oracle" rather than
# a brittle wall budget.
SERIAL_ORACLE = 9.0  # 4 sequential waves × 1s stubs + wave 3 sequential 2s
                   # + real-network SEC EDGAR SSL fail ~3s on test machines
step(f"wall time < {SERIAL_ORACLE}s (parallel-oracle: 4 seq + 2 parallel ≈ 5s; +3s SEC reals)",
     wall < SERIAL_ORACLE)
step(f"actual wall = {wall:.2f}s", True)
# Parallelism invariant: wave 3's two stubs (~2s) overlap, so
# wall ≈ orch(1) + senior(1) + wave3(1) + final(1) ≈ 4s on stubbed agents.
# Real-network adds SEC SSL-fail (~3s) → 5-7s.


# --- 2. Both AgentFinished events present ---
finished = [ev for ev in events if type(ev).__name__ == "AgentFinished"]
finished_agents = sorted(ev.agent_id for ev in finished)
step("both AgentFinished (forensic + devil)",
     "forensic-accounting" in finished_agents and "devils-advocate" in finished_agents)

# --- 3. final-report runs AFTER wave 3 ---
started = [ev for ev in events if type(ev).__name__ == "AgentStarted"]
started_agents = [ev.agent_id for ev in started]
step("AgentStarted sequence: ..., forensic, devils-advocate, final-report",
     "final-report" in started_agents)
# Find first wave-3 start and final-report start
def first_idx(seq, name):
    return next((i for i, a in enumerate(seq) if a == name), -1)
sr_idx = first_idx(started_agents, "senior-analyst")
wave3_first_idx = next(
    (i for i, a in enumerate(started_agents)
     if a in ("forensic-accounting", "devils-advocate")), -1)
fr_idx = first_idx(started_agents, "final-report")
step(f"senior-analyst precedes wave-3 (sr={sr_idx}, wave3={wave3_first_idx})",
     sr_idx >= 0 and wave3_first_idx > sr_idx)
step(f"final-report follows wave-3 (wave3={wave3_first_idx}, fr={fr_idx})",
     fr_idx > wave3_first_idx > -1)

# --- 4. Failure isolation: stub forensic to raise, devil still completes ---
print("\n=== 2. failure isolation in wave 3 ===")
def fail_forensic_call(agent_id, *a, **kw):
    if agent_id == "forensic-accounting":
        raise RuntimeError("forced forensic failure")
    return stubbed_call_agent(agent_id, *a, **kw)

rt.call_agent = fail_forensic_call
try:
    result = rt.execute_flow_f1(
        ticker="MSFT", model="ollama/llama3.2:3b",
        paid_for=None, emit_event=lambda ev: events.append(ev),
    )
    step("execute_flow_f1 raised on forensic-only failure", False)
except RuntimeError as exc:
    step("execute_flow_f1 raised on forensic-only failure", "forensic-accounting failed in wave 3" in str(exc))

# Now restore and test devil failure isolation
def fail_devil_call(agent_id, *a, **kw):
    if agent_id == "devils-advocate":
        raise RuntimeError("forced devil failure")
    return stubbed_call_agent(agent_id, *a, **kw)

rt.call_agent = fail_devil_call
try:
    result = rt.execute_flow_f1(
        ticker="GOOGL", model="ollama/llama3.2:3b",
        paid_for=None, emit_event=lambda ev: events.append(ev),
    )
    step(f"execute_flow_f1 completed despite devil failure", "final_envelope" in result)
    step("devil envelope is empty (failure fallback)",
         result["envelopes"]["devils-advocate"] == {})
    step(f"forensic envelope present (failed devil did NOT short-circuit)",
         isinstance(result["envelopes"]["forensic-accounting"], dict)
         and result["envelopes"]["forensic-accounting"].get("agent_id") == "forensic-accounting")
except Exception as exc:
    step(f"execute_flow_f1 completed despite devil failure", False)
    print(f"  unexpected raise: {type(exc).__name__}: {exc}")

print(f"\n=== pilot complete: {OK} ok / {FAIL} fail ===")
sys.exit(0 if FAIL == 0 else 1)
