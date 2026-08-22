"""smoke-2 — per-agent model routing from settings end-to-end.

Verifies that ``per_agent_model`` overrides flow all the way from
config -> ChatScreen -> execute_flow_f1 -> call_agent, and that the
precedence rule (per_agent_model > paid_for > default) holds.

No real LLMs are called; call_agent is mocked.

Exercises:
  1. call_agent honors per_agent_model[agent_id] over the default model
  2. call_agent ignores per_agent_model for agents NOT in the dict
  3. per_agent_model wins over paid_for (precedence rule #1 > #2)
  4. execute_flow_f1 passes per_agent_model through to every call_agent
  5. ChatScreen reads cfg.per_agent_model and forwards to run_flow_stream
  6. config_io round-trips per_agent_model through save -> load
  7. Missing per_agent_model -> None -> call_agent uses default path

Run:
    PYTHONPATH=docs python3 docs/runtime/smokes/per_agent_routing_smoke.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

THIS = Path(__file__).resolve()
DOCS = THIS.parents[2]
sys.path.insert(0, str(DOCS))


_OK = 0
_FAIL = 0


def step(label: str, ok: bool) -> None:
    global _OK, _FAIL
    if ok:
        _OK += 1
    else:
        _FAIL += 1
        print(f"  X {label}")


def section(name: str) -> None:
    print(f"\n=== {name} ===")

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
_MINIMAL_VALID = {
    "orchestrator": json.dumps({
        "agent_id": "orchestrator", "answer": "ok", "key_takeaways": [],
        "options": [], "evidence": [], "activity": [],
        "confidence": "MODERATE", "verification": {"asset_checks": [], "connector_status": [], "error_flags": []},
        "next_steps": [], "compressed": False,
    }),
    "senior-analyst": json.dumps({
        "agent_id": "senior-analyst", "depth": "STANDARD", "compressed": False,
        "conclusion": "mock", "confidence": "MIXED",
        "thesis": {"one_sentence": "mock", "bull_case": "mock", "fragile_assumption": "mock", "primary_source_priorities": []},
        "bottom_line": {"direction": "HOLD", "conviction": 3, "flip_trigger": "none"},
        "findings": [], "gaps": [], "verification": {"asset_checks": [], "connector_status": [], "error_flags": []},
        "citations": [], "next_steps": [],
    }),
    "forensic-accounting": json.dumps({
        "agent_id": "forensic-accounting", "depth": "STANDARD", "compressed": False,
        "conclusion": "mock", "confidence": "MIXED", "verdict": "CLEAN",
        "findings": [], "gaps": [], "verification": {"asset_checks": [], "connector_status": [], "error_flags": []},
        "citations": [], "next_steps": [],
    }),
    "devils-advocate": json.dumps({
        "agent_id": "devils-advocate", "depth": "STANDARD", "compressed": False,
        "conclusion": "mock", "confidence": "MIXED",
        "steelmanned_bull": "x", "bear_case": "x", "fragile_assumption": "x",
        "what_an_attacker_would_say": "x",
        "findings": [], "gaps": [], "verification": {"asset_checks": [], "connector_status": [], "error_flags": []},
        "citations": [], "next_steps": [],
    }),
    "final-report": json.dumps({
        "agent_id": "final-report", "flow_id": "f1", "depth": "STANDARD", "compressed": False,
        "memo": {"bottom_line": {"direction": "HOLD", "conviction": 3, "flip_trigger": "n", "one_liner": "x"},
                 "bull_case": "x", "bear_case": "x", "what_an_attacker_would_say": "x",
                 "next_three_questions": [], "citations_used": []},
        "confidence": "MODERATE", "gaps": [],
        "verification": {"asset_checks": [], "connector_status": [], "error_flags": []},
    }),
}


def _infer_agent_id_from_system(system_prompt: str) -> str:
    """Guess agent_id from the prompt's title line (first 3 lines only)."""
    title = "\n".join(system_prompt.splitlines()[:3]).lower()
    title_clean = title.replace("'", "").replace('"', "").replace("(", "").replace(")", "")
    for aid in _MINIMAL_VALID:
        normalized = aid.replace("-", " ")
        if normalized in title_clean:
            return aid
    return "senior-analyst"


def _make_mock_adapter_class():
    """Factory to produce adapter class with its own calls list."""
    class _A:
        def __init__(self):
            self.calls: list[dict] = []
        def call(self, messages, system, options):
            self.calls.append({})
            agent_id = _infer_agent_id_from_system(system)
            envelope_text = _MINIMAL_VALID.get(agent_id, _MINIMAL_VALID["senior-analyst"])
            from runtime.adapters import Response
            return Response(
                text=envelope_text,
                in_tokens=10, out_tokens=5, cost_usd_estimate=0.0,
            )
    return _A


from runtime import runtime as rt
from runtime.adapters import Response

orig_get = rt.get_adapter

# ===========================================================================
# 1. call_agent honours per_agent_model
# ===========================================================================
section("1. call_agent honours per_agent_model[agent_id] over default")

MockA = _make_mock_adapter_class()
mock_adapter = MockA()
model_log: list[str] = []

def _fake_get(model_name: str):
    model_log.append(model_name)
    return mock_adapter

rt.get_adapter = _fake_get

try:
    model_log.clear()
    env, cost = rt.call_agent(
        "senior-analyst",
        user_brief='{"ticker":"NVDA","flow_id":"f1"}',
        model_name="openai/gpt-4o",
        per_agent_model={"senior-analyst": "ollama/llama3.3:70b"},
    )
    step("get_adapter called with ollama/llama3.3:70b (per_agent_model wins)",
         "ollama/llama3.3:70b" in model_log)
    step("get_adapter NOT called with gpt-4o (default overridden)",
         "openai/gpt-4o" not in model_log)
    step("call_agent returned a valid envelope",
         env is not None and env.get("agent_id") == "senior-analyst")

    model_log.clear()
    env2, _ = rt.call_agent(
        "senior-analyst",
        user_brief='{"ticker":"NVDA"}',
        model_name="openai/gpt-4o",
    )
    step("without per_agent_model -> get_adapter called with gpt-4o",
         "openai/gpt-4o" in model_log)

finally:
    rt.get_adapter = orig_get


# ===========================================================================
# 2. per_agent_model ignores agents NOT in the dict
# ===========================================================================
section("2. per_agent_model only applies to listed agents")

MockB = _make_mock_adapter_class()
mock_adapter2 = MockB()
model_log2: list[str] = []

def _fake_get2(model_name: str):
    model_log2.append(model_name)
    return mock_adapter2

rt.get_adapter = _fake_get2
try:
    model_log2.clear()
    env, _ = rt.call_agent(
        "devils-advocate",
        user_brief='{"ticker":"NVDA"}',
        model_name="openai/gpt-4o",
        per_agent_model={"senior-analyst": "ollama/llama3.3:70b"},
    )
    step("devils-advocate NOT in per_agent_model -> uses default gpt-4o",
         "openai/gpt-4o" in model_log2)
    step("devils-advocate NOT routed to ollama override",
         "ollama/llama3.3:70b" not in model_log2)
    step("envelope returned with correct agent_id",
         env is not None and env.get("agent_id") == "devils-advocate")
finally:
    rt.get_adapter = orig_get


# ===========================================================================
# 3. per_agent_model wins over paid_for
# ===========================================================================
section("3. per_agent_model > paid_for (precedence rule #1 > #2)")

MockC = _make_mock_adapter_class()
mock_adapter3 = MockC()
model_log3: list[str] = []

def _fake_get3(model_name: str):
    model_log3.append(model_name)
    return mock_adapter3

rt.get_adapter = _fake_get3
try:
    model_log3.clear()
    env, _ = rt.call_agent(
        "final-report",
        user_brief='{"ticker":"NVDA"}',
        model_name="openai/gpt-4o",
        paid_for=["final-report", "senior-analyst"],
        per_agent_model={"final-report": "groq/llama-3.3-70b"},
    )
    step("per_agent_model final-report=groq beats paid_for->sonnet default",
         "groq/llama-3.3-70b" in model_log3)
    step("NOT using sonnet (paid_for avoided for per_agent_model agent)",
         not any("sonnet" in m.lower() for m in model_log3 if isinstance(m, str)))

    model_log3.clear()
    env, _ = rt.call_agent(
        "final-report",
        user_brief='{"ticker":"NVDA"}',
        model_name="openai/gpt-4o",
        paid_for=["final-report", "senior-analyst"],
    )
    step("final-report in paid_for (no per_agent) -> sonnet",
         any("sonnet" in m.lower() for m in model_log3 if isinstance(m, str)))
finally:
    rt.get_adapter = orig_get


# ===========================================================================
# 4. execute_flow_f1 passes per_agent_model through to every call_agent
# ===========================================================================
section("4. execute_flow_f1 forwards per_agent_model to all call_agent calls")

call_agent_args: list[dict] = []

def _capture_call_agent(agent_id, user_brief, model_name,
                         paid_for=None, emit_event=None,
                         per_agent_model=None, stream_chunks=False,
                         system_prompt_override=None, **_):
    call_agent_args.append({
        "agent_id": agent_id,
        "model_name": model_name,
        "per_agent_model": per_agent_model,
    })
    # Build valid envelope per agent from the shared minimal set
    import json as _json
    valid_str = _MINIMAL_VALID.get(agent_id, _MINIMAL_VALID["senior-analyst"])
    return _json.loads(valid_str), {"cost_usd_estimate": 0.0, "agent_id": agent_id}

def _fake_preflight(ticker, emit_event=None):
    return []

with patch("runtime.runtime.call_agent", side_effect=_capture_call_agent), \
     patch("runtime.runtime._tool_preflight", side_effect=_fake_preflight), \
     patch("runtime.runtime.ThesisRegister") as mock_reg_class:

    mock_reg = MagicMock()
    mock_reg.read_thesis.return_value = None
    mock_reg_class.return_value = mock_reg

    call_agent_args.clear()
    result = rt.execute_flow_f1(
        ticker="NVDA",
        model="openai/gpt-4o",
        paid_for=None,
        per_agent_model={
            "senior-analyst": "ollama/llama3.3:70b",
            "final-report": "anthropic/claude-sonnet-4-5",
        },
    )
    step("5 agents called total", len(call_agent_args) == 5)
    for call in call_agent_args:
        step(f"  {call['agent_id']}: per_agent_model dict forwarded",
             call["per_agent_model"] is not None)
        step(f"  {call['agent_id']}: has both overrides",
             call["per_agent_model"] is not None
             and call["per_agent_model"].get("senior-analyst") == "ollama/llama3.3:70b"
             and call["per_agent_model"].get("final-report") == "anthropic/claude-sonnet-4-5")
    step("result has final_envelope", "final_envelope" in result)


# ===========================================================================
# 5. ChatScreen reads cfg.per_agent_model and forwards to run_flow_stream
# ===========================================================================
section("5. ChatScreen -> run_flow_stream wiring")

chat_src = (DOCS / "frontend" / "screens" / "chat.py").read_text(encoding="utf-8")
step("chat.py reads cfg.per_agent_model",
     "per_agent_model" in chat_src)
step("chat.py passes per_agent_model to run_flow_stream",
     "per_agent_model=self.per_agent_model" in chat_src
     or "per_agent_model=per_agent_model" in chat_src)
step("chat.py stores self.per_agent_model from config",
     "self.per_agent_model" in chat_src and "cfg.per_agent_model" in chat_src)


# ===========================================================================
# 6. config_io round-trips per_agent_model
# ===========================================================================
section("6. config_io saves and loads per_agent_model")

from frontend.config_io import load_config, save_config, Config, ProviderConfig

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    cfg = Config(
        providers={"ollama": ProviderConfig(
            name="ollama", base_url="http://localhost:11434", api_key_env=None)},
        default_model="openai/gpt-4o",
        per_agent_model={
            "senior-analyst": "ollama/llama3.3:70b",
            "final-report": "anthropic/claude-sonnet-4-5",
        },
    )
    import frontend.config_io as cio
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path
    try:
        save_config(cfg)
        loaded = load_config()
        step("per_agent_model survives save -> load",
             loaded.per_agent_model == cfg.per_agent_model)
        step("per_agent_model has 2 entries after round-trip",
             len(loaded.per_agent_model) == 2)
        step("senior-analyst override persisted",
             loaded.per_agent_model.get("senior-analyst") == "ollama/llama3.3:70b")
        step("final-report override persisted",
             loaded.per_agent_model.get("final-report") == "anthropic/claude-sonnet-4-5")
    finally:
        cio.CONFIG_PATH = real_path


# ===========================================================================
# 7. Missing per_agent_model -> None path
# ===========================================================================
section("7. None per_agent_model -> call_agent uses default path")

call_agent_args.clear()

with patch("runtime.runtime.call_agent", side_effect=_capture_call_agent), \
     patch("runtime.runtime._tool_preflight", side_effect=_fake_preflight), \
     patch("runtime.runtime.ThesisRegister") as mock_reg_class:

    mock_reg = MagicMock()
    mock_reg.read_thesis.return_value = None
    mock_reg_class.return_value = mock_reg

    call_agent_args.clear()
    result = rt.execute_flow_f1(
        ticker="NVDA",
        model="openai/gpt-4o",
        paid_for=None,
        per_agent_model=None,
    )
    step("5 agents called (None per_agent is same as empty)",
         len(call_agent_args) == 5)
    for call in call_agent_args:
        step(f"  {call['agent_id']}: per_agent_model is None",
             call["per_agent_model"] is None)


# ===========================================================================
# Summary
# ===========================================================================
print()
total = _OK + _FAIL
print(f"\n=== {_OK}/{total} ok ===")
if _FAIL:
    print(f"{_FAIL} FAIL")
    sys.exit(1)
print("0 fail")
print("all green")
sys.exit(0)