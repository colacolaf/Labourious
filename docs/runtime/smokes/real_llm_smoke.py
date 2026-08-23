"""
smoke — [domain-1] real-LLM f1 end-to-end (ollama/llama3.2:3b).

Runs f1 against a real local Ollama model (llama3.2:3b, ~2 GB).
Verifies:
  1. Ollama probe returns a response
  2. Flow completes (FlowFinished, not crashed)
  3. ≥ 4/5 agents finish with valid envelopes (orchestrator, senior,
     forensic, final-report — devil's advocate is the hardest envelope
     for a 3B model and may fail validation, which is expected)
  4. Envelopes parse as valid JSON, pass validate_envelope
  5. Token counts and wallclock are positive
  6. Cost = $0 (ollama is free)

Expected runtime: ~4 minutes on CPU, ~1 minute on GPU.

Usage:
    PYTHONPATH=docs python3 docs/runtime/smokes/real_llm_smoke.py
"""

from __future__ import annotations

import os, sys, time

DOCS = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, DOCS)

MODEL = "ollama/llama3.2:3b"
TICKER = "NVDA"

passes = 0
fails_c = 0

def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def step(label: str, cond: bool) -> None:
    global passes, fails_c
    if cond:
        print(f"  ✅ {label}")
        passes += 1
    else:
        print(f"  ❌ FAIL: {label}")
        fails_c += 1


# ===========================================================================
# 1. Probe
# ===========================================================================
section("1. Ollama probe (llama3.2:3b)")

from runtime.adapters.ollama import OllamaAdapter
OllamaAdapter.request_timeout_s = 600  # bump for cold model load

adapter = OllamaAdapter(model=MODEL)
try:
    resp = adapter.call(
        messages=[{"role": "user", "content": "Say OK"}],
        system="Reply with ONLY the word OK.",
        options={"temperature": 0.1},
    )
    step("ollama responds", "OK" in resp.text.strip().upper())
    step(f"in_tokens > 0 ({resp.in_tokens})", resp.in_tokens > 0)
    step(f"out_tokens > 0 ({resp.out_tokens})", resp.out_tokens > 0)
    step("cost = $0", resp.cost_usd_estimate == 0.0)
except Exception as e:
    step(f"probe failed: {e}", False)
    print("Aborting — ollama not responding.")
    raise SystemExit(1)


# ===========================================================================
# 2. Run f1
# ===========================================================================
section("2. Run f1 flow")

from runtime.runtime import execute_flow_f1

t0 = time.monotonic()
events, envelopes, costs = [], {}, {}

def emit(ev):
    events.append(ev)
    if hasattr(ev, 'kind'):
        k = ev.kind
        aid = getattr(ev, 'agent_id', '')
        if k == 'agent_started':
            print(f"  ⏳ {aid} started ...", flush=True)
        elif k == 'agent_finished':
            envelopes[aid] = ev.envelope
            costs[aid] = {"wall": ev.wallclock_s, "in": ev.in_tokens, "out": ev.out_tokens, "$": ev.cost_usd_estimate}
            print(f"  ✅ {aid} done ({ev.wallclock_s:.0f}s, {ev.in_tokens}+{ev.out_tokens} tok)", flush=True)
        elif k == 'agent_failed':
            err = getattr(ev, 'error', 'unknown')[:80]
            print(f"  ❌ {aid} FAILED: {err}", flush=True)

try:
    result = execute_flow_f1(TICKER, MODEL, None, emit_event=emit, stream_chunks=False)
    elapsed = time.monotonic() - t0
    step("flow completed", True)
    step(f"wallclock: {elapsed:.0f}s ({elapsed/60:.1f} min)", elapsed > 0)
except Exception as e:
    elapsed = time.monotonic() - t0
    step(f"flow crashed: {e}", False)
    raise SystemExit(1)


# ===========================================================================
# 3. Agent completion
# ===========================================================================
section("3. Agent completion (target: ≥ 4/5)")

expected = ["orchestrator", "senior-analyst", "forensic-accounting", "devils-advocate", "final-report"]
finished = 0
for aid in expected:
    ok = aid in envelopes
    if ok:
        finished += 1
        print(f"  ✅ {aid}: {costs.get(aid,{}).get('wall',0):.0f}s")
    else:
        print(f"  ❌ {aid}: missing")

step(f"≥ 4/5 agents finished ({finished}/5)", finished >= 4)


# ===========================================================================
# 4. Envelope validation
# ===========================================================================
section("4. Envelope validation")

from runtime.runtime import validate_envelope

for aid in sorted(envelopes):
    env = envelopes[aid]
    ok, failures = validate_envelope(env, aid)
    step(f"{aid}: validate {'OK' if ok else f'{len(failures)} failures'}", ok)
    if not ok:
        for f in failures[:3]:
            print(f"    ⚠️  {f}")


# ===========================================================================
# 5. Token/cost summary
# ===========================================================================
section("5. Token + cost summary")

total_in = sum(c.get("in", 0) for c in costs.values())
total_out = sum(c.get("out", 0) for c in costs.values())
total_wall = sum(c.get("wall", 0) for c in costs.values())
print(f"  📊 Tokens: {total_in:,} in / {total_out:,} out")
print(f"  ⏱️  Wallclock: {total_wall:.0f}s agent time / {elapsed:.0f}s wall")
print(f"  💰 Cost: $0.0000 (free/ollama)")
step("total in_tokens > 0", total_in > 0)
step("total out_tokens > 0", total_out > 0)


# ===========================================================================
# Summary
# ===========================================================================
print(f"\n{'='*60}")
print(f"  real-llm: {passes}/{passes+fails_c} ok ({finished}/5 agents)")
print(f"  model: {MODEL} ({elapsed:.0f}s total)")
if fails_c == 0:
    print(f"  ✅ ALL GREEN")
else:
    print(f"  ⚠️  {fails_c} non-critical failures")
print(f"{'='*60}")
sys.exit(0 if fails_c == 0 else 1)