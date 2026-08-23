"""
smoke — [runtime-3] per-agent timeout_s budget.

Verifies that call_agent accepts timeout_s, wraps the model call in a
daemon thread, and raises AgentTimedOut (with AgentFailed emitted) when
the budget is exceeded.

Exercises:
  1. AgentTimedOut is a RuntimeError
  2. timeout_s in signatures (call_agent, execute_flow_f1, run_flow_stream)
  3. timeout fires → AgentTimedOut raised + AgentFailed emitted
  4. timeout_s larger than call duration → call completes normally
  5. timeout_s=0 → no timeout guard (same as None)
  6. _do_model_call returns correct tuple shape
  7. Thread+queue timeout guard fires under 1s
"""

from __future__ import annotations

import os, sys, time, threading, queue, inspect

DOCS = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, DOCS)

import runtime.runtime as rt_mod
from runtime.runtime import (
    call_agent, execute_flow_f1, run_flow_stream,
    AgentTimedOut, _do_model_call, _RESUME_PARTIAL_ENVELOPES,
)

passes = 0
fails = 0

def section(title: str) -> None:
    print(f"\n── {title} ──")

def step(label: str, cond: bool) -> None:
    global passes, fails
    if cond:
        print(f"  ✓ {label}")
        passes += 1
    else:
        print(f"  ✗ FAIL: {label}")
        fails += 1

def step_eq(label: str, a, b) -> None:
    step(label, a == b)


# Save originals for cleanup
_orig_get_adapter = rt_mod.get_adapter
_orig_model_call = rt_mod._do_model_call
_orig_load_prompt = rt_mod.load_prompt
_orig_resume = rt_mod._RESUME_PARTIAL_ENVELOPES
_orig_validate = rt_mod.validate_envelope

# Patch validate_envelope to always pass (we're testing timeout, not JSON structure)
rt_mod.validate_envelope = lambda env, agent_id: (True, [])


# ===========================================================================
# 1. AgentTimedOut exception
# ===========================================================================
section("1. AgentTimedOut is RuntimeError")
step("is RuntimeError", issubclass(AgentTimedOut, RuntimeError))
try:
    raise AgentTimedOut("test timeout 5s")
except AgentTimedOut as e:
    step_eq("message", str(e), "test timeout 5s")


# ===========================================================================
# 2. Signatures
# ===========================================================================
section("2. timeout_s in signatures")
for fn, name in [(call_agent, "call_agent"), (execute_flow_f1, "execute_flow_f1"), (run_flow_stream, "run_flow_stream")]:
    sig = inspect.signature(fn)
    step(f"{name} has timeout_s", "timeout_s" in sig.parameters)
    step_eq(f"{name} default None", sig.parameters["timeout_s"].default, None)


# ===========================================================================
# 3. Thread+queue guard fires
# ===========================================================================
section("3. thread+queue timeout detection")
rq = queue.Queue()
eq = queue.Queue()
def _hang():
    time.sleep(10)
    rq.put("done")
t0 = time.monotonic()
w = threading.Thread(target=_hang, daemon=True)
w.start()
w.join(timeout=0.05)
elapsed = time.monotonic() - t0
step("worker still alive (hung)", w.is_alive())
step(f"timeout detection < 1s ({elapsed:.2f}s)", elapsed < 1.0)


# ===========================================================================
# 4. timeout fires → AgentTimedOut + AgentFailed
# ===========================================================================
section("4. timeout fires → AgentTimedOut + AgentFailed")

events = []

class _FakeAdapter:
    pass

def _hanging_call(*args, **kwargs):
    time.sleep(10)
    return ("{}", 0, 0, 0.0)

rt_mod.get_adapter = lambda model: _FakeAdapter()
rt_mod.load_prompt = lambda agent_id: "fake system prompt"
rt_mod._do_model_call = _hanging_call
rt_mod._RESUME_PARTIAL_ENVELOPES = {}

caught = False
try:
    call_agent(
        "senior-analyst", "brief", "openai/gpt-4o",
        emit_event=lambda ev: events.append(ev),
        timeout_s=0.05,
    )
except AgentTimedOut as e:
    caught = True
    step("AgentTimedOut raised", True)
    step("mentions timeout", "timed out" in str(e))
    step("mentions agent_id", "senior-analyst" in str(e))
except Exception as e:
    step(f"unexpected: {type(e).__name__}: {e}", False)

step("AgentTimedOut was caught", caught)

failed = [e for e in events if getattr(e, 'kind', '') == 'agent_failed']
step("AgentFailed emitted", len(failed) >= 1)
if failed:
    step_eq("AgentFailed agent_id", failed[0].agent_id, "senior-analyst")
    step("AgentFailed mentions timeout", "timed out" in failed[0].error)

started = [e for e in events if getattr(e, 'kind', '') == 'agent_started']
step("AgentStarted emitted", len(started) >= 1)


# ===========================================================================
# 5. No timeout — call completes normally
# ===========================================================================
section("5. timeout_s large enough → call completes")

events2 = []

def _fast_call(*args, **kwargs):
    time.sleep(0.01)
    return ('{"agent_id":"senior-analyst","conviction":3}', 10, 5, 0.0001)

rt_mod._do_model_call = _fast_call
rt_mod._RESUME_PARTIAL_ENVELOPES = {}

call_agent(
    "senior-analyst", "brief", "openai/gpt-4o",
    emit_event=lambda ev: events2.append(ev),
    timeout_s=5.0,
)
step("call completed", True)

finished = [e for e in events2 if getattr(e, 'kind', '') == 'agent_finished']
step("AgentFinished emitted", len(finished) >= 1)

failed2 = [e for e in events2 if getattr(e, 'kind', '') == 'agent_failed']
step("no AgentFailed", len(failed2) == 0)


# ===========================================================================
# 6. timeout_s=0 → no guard
# ===========================================================================
section("6. timeout_s=0 → no timeout guard")

def _quick_call(*args, **kwargs):
    return ('{"agent_id":"senior-analyst","conviction":4}', 5, 2, 0.00005)

rt_mod._do_model_call = _quick_call
rt_mod._RESUME_PARTIAL_ENVELOPES = {}

try:
    result = call_agent("senior-analyst", "brief", "openai/gpt-4o", timeout_s=0)
    step("timeout_s=0 returned result", isinstance(result, tuple))
except Exception as e:
    step(f"failed: {e}", False)


# ===========================================================================
# 7. _do_model_call returns correct tuple
# ===========================================================================
section("7. _do_model_call returns (text, in_tok, out_tok, cost)")

class _RespAdapter:
    def call(self, messages, system, options):
        class R:
            text = '{"agent_id":"test","conviction":5}'
            in_tokens = 200
            out_tokens = 80
            cost_usd_estimate = 0.002
        return R()

text, in_tok, out_tok, cost = _do_model_call(
    _RespAdapter(), "brief", "sys", False, None, "test"
)
step("text is str", isinstance(text, str))
step("in_tokens is int", isinstance(in_tok, int))
step("out_tokens is int", isinstance(out_tok, int))
step("cost is float", isinstance(cost, float))


# ===========================================================================
# Cleanup
# ===========================================================================
rt_mod.get_adapter = _orig_get_adapter
rt_mod._do_model_call = _orig_model_call
rt_mod.load_prompt = _orig_load_prompt
rt_mod._RESUME_PARTIAL_ENVELOPES = _orig_resume


# ===========================================================================
# Summary
# ===========================================================================
print(f"\n=== {passes}/{passes + fails} ok ===")
if fails == 0:
    print("all green")
else:
    print(f"{fails} fail")
    sys.exit(1)