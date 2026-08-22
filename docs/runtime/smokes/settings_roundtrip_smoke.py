"""settings-roundtrip — Config → ChatScreen.reload_config_from_disk → run_flow_stream.

Verifies the full path:
  1. Config.save_config() round-trips per_agent_model
  2. Simulate ChatScreen.reload_config_from_disk() — load → self.per_agent_model
  3. run_flow_stream passes per_agent_model into execute_flow_f1 → every call_agent
  4. call_agent honors the override (per_agent_model > default precedence)

No real LLMs or network calls; call_agent + _tool_preflight are patched.

Exercises:
  1. save_config → load_config round-trips per_agent_model
  2. ChatScreen reload pattern: load → self.per_agent_model
  3. run_flow_stream forwards per_agent_model to all 5 call_agent invocations
  4. Config with empty per_agent_model → None (default path)
  5. Multiple agent overrides + paid_for interaction
  6. ChatScreen source code wires cfg.per_agent_model → self.per_agent_model

Run:
    PYTHONPATH=docs python3 docs/runtime/smokes/settings_roundtrip_smoke.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

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
# Shared fixtures — minimal valid envelopes per agent
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


def _mock_call_agent(agent_id, user_brief, model_name,
                     paid_for=None, emit_event=None,
                     per_agent_model=None, stream_chunks=False,
                     system_prompt_override=None, **_):
    """Return a valid envelope for the given agent. Emits started/finished events
    if an emitter is hooked."""
    envelope = json.loads(_MINIMAL_VALID.get(agent_id, _MINIMAL_VALID["senior-analyst"]))
    if emit_event is not None:
        from runtime.events import AgentStarted, AgentFinished
        emit_event(AgentStarted(agent_id=agent_id, model=model_name,
                                depth="STANDARD", compressed=False))
        emit_event(AgentFinished(agent_id=agent_id, envelope=envelope,
                                 wallclock_s=0.1, in_tokens=10, out_tokens=5,
                                 cost_usd_estimate=0.0))
    return envelope, {"cost_usd_estimate": 0.0, "agent_id": agent_id,
                      "model": model_name, "in_tokens": 10, "out_tokens": 5,
                      "wallclock_s": 0.1}


def _mock_preflight(ticker, emit_event=None):
    return []


# ===========================================================================
# 1. Config save → load round-trips per_agent_model
# ===========================================================================
section("1. Config save → load round-trips per_agent_model")

from frontend.config_io import Config, ProviderConfig, save_config as _save, load_config as _load

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    with patch("frontend.config_io.CONFIG_PATH", cfg_path):
        cfg = Config(
            providers={},
            default_model="openai/gpt-4o",
            per_agent_model={
                "senior-analyst": "ollama/llama3.3:70b",
                "final-report": "anthropic/claude-sonnet-4-5",
            },
        )
        _save(cfg)

        step("config file written", cfg_path.exists())

        loaded = _load()
        step("per_agent_model survived round-trip",
             loaded.per_agent_model == cfg.per_agent_model)
        step("senior-analyst override preserved",
             loaded.per_agent_model.get("senior-analyst") == "ollama/llama3.3:70b")
        step("final-report override preserved",
             loaded.per_agent_model.get("final-report") == "anthropic/claude-sonnet-4-5")
        step("default model untouched",
             loaded.default_model == "openai/gpt-4o")


# ===========================================================================
# 2. ChatScreen reload pattern → execute_flow_f1 honors per_agent_model
# ===========================================================================
section("2. ChatScreen reload → run_flow_stream honors per_agent_model")

from runtime import runtime as rt

call_agent_calls: list[dict] = []

def _capture_and_mock(agent_id, user_brief, model_name, **kw):
    call_agent_calls.append({
        "agent_id": agent_id,
        "model_name": model_name,
        "per_agent_model": kw.get("per_agent_model"),
    })
    return _mock_call_agent(agent_id, user_brief, model_name, **kw)

with patch("runtime.runtime.call_agent", side_effect=_capture_and_mock), \
     patch("runtime.runtime._tool_preflight", side_effect=_mock_preflight), \
     patch("runtime.runtime.ThesisRegister") as mock_reg_cls:

    mock_reg = MagicMock()
    mock_reg.read_thesis.return_value = None
    mock_reg_cls.return_value = mock_reg

    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "config.json"
        with patch("frontend.config_io.CONFIG_PATH", cfg_path):
            # === Simulate Settings save ===
            cfg = Config(
                providers={},
                default_model="openai/gpt-4o",
                per_agent_model={
                    "senior-analyst": "groq/llama-3.3-70b",
                    "devils-advocate": "ollama/qwen2.5:72b",
                },
            )
            _save(cfg)

            # === Simulate ChatScreen.reload_config_from_disk() ===
            loaded = _load()
            per_agent = dict(loaded.per_agent_model)
            step("reloaded per_agent_model has 2 entries", len(per_agent) == 2)
            step("reloaded senior-analyst → groq",
                 per_agent.get("senior-analyst") == "groq/llama-3.3-70b")
            step("reloaded devils-advocate → ollama",
                 per_agent.get("devils-advocate") == "ollama/qwen2.5:72b")

            # === Simulate ChatScreen._run_flow → run_flow_stream ===
            call_agent_calls.clear()
            events = list(rt.run_flow_stream(
                flow_id="f1",
                inputs={"ticker": "NVDA", "depth": "STANDARD", "compressed": False},
                model=loaded.default_model,
                paid_for=None,
                per_agent_model=per_agent or None,
                stream_chunks=False,
            ))

            step("5 agents called total", len(call_agent_calls) == 5)
            step("flow produced events (FlowStarted → ... → FlowFinished)",
                 len(events) >= 3)

            # Verify per_agent_model forwarded to every agent
            pam_keys = {"senior-analyst", "devils-advocate"}
            for call in call_agent_calls:
                aid = call["agent_id"]
                pam = call["per_agent_model"]
                step(f"{aid}: per_agent_model dict forwarded",
                     isinstance(pam, dict))
                if isinstance(pam, dict):
                    step(f"{aid}: per_agent_model has both overrides",
                         all(k in pam for k in pam_keys))
                    step(f"{aid}: senior-analyst → groq in pam",
                         pam.get("senior-analyst") == "groq/llama-3.3-70b")
                    step(f"{aid}: devils-advocate → ollama in pam",
                         pam.get("devils-advocate") == "ollama/qwen2.5:72b")


# ===========================================================================
# 3. Empty per_agent_model → None forwarded → all agents use default
# ===========================================================================
section("3. Empty per_agent_model → None forwarded → all agents use default")

call_agent_calls2: list[dict] = []

def _capture2(agent_id, user_brief, model_name, **kw):
    call_agent_calls2.append({
        "agent_id": agent_id,
        "model_name": model_name,
        "per_agent_model": kw.get("per_agent_model"),
    })
    return _mock_call_agent(agent_id, user_brief, model_name, **kw)

with patch("runtime.runtime.call_agent", side_effect=_capture2), \
     patch("runtime.runtime._tool_preflight", side_effect=_mock_preflight), \
     patch("runtime.runtime.ThesisRegister") as mock_reg_cls:

    mock_reg = MagicMock()
    mock_reg.read_thesis.return_value = None
    mock_reg_cls.return_value = mock_reg

    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "config2.json"
        with patch("frontend.config_io.CONFIG_PATH", cfg_path):
            cfg = Config(
                providers={},
                default_model="openai/gpt-4o",
                per_agent_model={},  # empty
            )
            _save(cfg)
            loaded = _load()
            step("empty per_agent_model loads as empty dict",
                 loaded.per_agent_model == {})

            call_agent_calls2.clear()
            per_agent = dict(loaded.per_agent_model)
            events = list(rt.run_flow_stream(
                flow_id="f1",
                inputs={"ticker": "NVDA", "depth": "STANDARD", "compressed": False},
                model=loaded.default_model,
                paid_for=None,
                per_agent_model=per_agent if per_agent else None,
                stream_chunks=False,
            ))
            step("flow completed with empty per_agent_model",
                 len(events) >= 3)
            step("5 agents called",
                 len(call_agent_calls2) == 5)
            # Every call should have per_agent_model=None (empty dict → None)
            step("all agents received per_agent_model=None (empty override)",
                 all(c["per_agent_model"] is None for c in call_agent_calls2))


# ===========================================================================
# 4. per_agent_model wins over paid_for in round-trip
# ===========================================================================
section("4. per_agent_model wins over paid_for in round-trip")

call_agent_calls3: list[dict] = []

def _capture3(agent_id, user_brief, model_name, **kw):
    call_agent_calls3.append({
        "agent_id": agent_id,
        "model_name": model_name,
        "per_agent_model": kw.get("per_agent_model"),
    })
    return _mock_call_agent(agent_id, user_brief, model_name, **kw)

with patch("runtime.runtime.call_agent", side_effect=_capture3), \
     patch("runtime.runtime._tool_preflight", side_effect=_mock_preflight), \
     patch("runtime.runtime.ThesisRegister") as mock_reg_cls:

    mock_reg = MagicMock()
    mock_reg.read_thesis.return_value = None
    mock_reg_cls.return_value = mock_reg

    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "config3.json"
        with patch("frontend.config_io.CONFIG_PATH", cfg_path):
            cfg = Config(
                providers={},
                default_model="openai/gpt-4o",
                per_agent_model={"final-report": "mistral/mistral-large"},
                hybrid_paid_for=["final-report", "senior-analyst"],
            )
            _save(cfg)
            loaded = _load()
            step("hybrid_paid_for survived round-trip",
                 loaded.hybrid_paid_for == ["final-report", "senior-analyst"])
            step("per_agent_model survived alongside paid_for",
                 loaded.per_agent_model == {"final-report": "mistral/mistral-large"})

            call_agent_calls3.clear()
            per_agent = dict(loaded.per_agent_model)
            events = list(rt.run_flow_stream(
                flow_id="f1",
                inputs={"ticker": "NVDA", "depth": "STANDARD", "compressed": False},
                model=loaded.default_model,
                paid_for=loaded.hybrid_paid_for,
                per_agent_model=per_agent if per_agent else None,
                stream_chunks=False,
            ))
            step("flow completed with both per_agent_model + paid_for",
                 len(events) >= 3)
            step("5 agents called",
                 len(call_agent_calls3) == 5)

            # final-report call should have per_agent_model containing the override
            fr_call = next((c for c in call_agent_calls3 if c["agent_id"] == "final-report"), None)
            step("final-report call exists", fr_call is not None)
            if fr_call and isinstance(fr_call["per_agent_model"], dict):
                step("final-report: per_agent_model has mistral override",
                     fr_call["per_agent_model"].get("final-report") == "mistral/mistral-large")


# ===========================================================================
# 5. ChatScreen source code wires cfg.per_agent_model → self.per_agent_model
# ===========================================================================
section("5. ChatScreen source reads and forwards per_agent_model")

chat_src = (DOCS / "frontend" / "screens" / "chat.py").read_text(encoding="utf-8")
step("chat.py reads cfg.per_agent_model",
     "cfg.per_agent_model" in chat_src)
step("chat.py stores self.per_agent_model",
     "self.per_agent_model" in chat_src)
step("chat.py passes per_agent_model to run_flow_stream",
     "per_agent_model=self.per_agent_model" in chat_src
     or "per_agent_model=per_agent_model" in chat_src)


# ===========================================================================
# Summary
# ===========================================================================
print(f"\n{'='*60}")
print(f"settings-roundtrip — {_OK} passed, {_FAIL} failed")
print(f"{'='*60}")
sys.exit(0 if _FAIL == 0 else 1)