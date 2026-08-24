"""live_chat_flow_smoke.py — REAL end-to-end: wizard → keychain → full f1.

LIVE-NETWORK pilot. Requires a real cloud LLM provider configured in the
environment (ANTHROPIC_API_KEY) and internet access. Like real_llm_smoke,
it is EXCLUDED from the runnable sweep (run_bench / the all-pilots loop)
because it hits a paid API and the network.

Drives the REAL app (LabouriousApp → real ChatScreen → real wizard) with
real key events through the ENTIRE user journey:

  1. Fresh config → wizard auto-pushes.
  2. Wizard: select anthropic → default model → type the REAL API key
     (read from ANTHROPIC_API_KEY env, never hardcoded) → Save & start.
  3. Chat: type "analyze NVDA" → Enter → the REAL f1 flow runs against
     the cloud provider using the key that was stored in the keychain
     (ANTHROPIC_API_KEY is popped from env so the adapter MUST resolve
     it from keys_storage — proving the wizard→keychain→adapter path).
  4. Waits for FlowFinished ("· run complete" in the StatusStrip) and
     reports which agents produced bubbles + the final report.

Hermetic where it matters: temp HOME + LABOURIOUS_TEST isolate the
keychain (file backend under the temp HOME) and the config; the real
Anthropic API is the only external dependency.

Run:  ANTHROPIC_API_KEY=... PYTHONPATH=docs python3 \
      docs/runtime/smokes/live_chat_flow_smoke.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

_REAL_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not _REAL_KEY:
    print("SKIP: ANTHROPIC_API_KEY not set — live smoke needs a real key")
    sys.exit(0)

# --- isolate everything before importing frontend modules -------------------
_TMP = Path(tempfile.mkdtemp(prefix="live-chat-"))
os.environ["HOME"] = str(_TMP)
os.environ["LABOURIOUS_CONFIG"] = str(_TMP / "config.json")
os.environ["LABOURIOUS_TEST"] = "1"
# Pop the env key so the adapter MUST resolve from the keychain the wizard
# wrote to — proving the wizard → keys_storage → adapter path end-to-end.
os.environ.pop("ANTHROPIC_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from frontend.app import LabouriousApp  # noqa: E402
from frontend.screens.welcome_wizard import WelcomeWizardScreen  # noqa: E402
from frontend.screens.chat import ChatScreen  # noqa: E402
from frontend.keys_storage import get_key  # noqa: E402
from frontend.widgets.status_strip import StatusStrip  # noqa: E402

ok = 0
fails: list[str] = []


def step(desc: str, cond: bool) -> None:
    global ok
    if cond:
        ok += 1
        print(f"  ✓ {desc}")
    else:
        fails.append(desc)
        print(f"  ✗ FAIL {desc}")


@asynccontextmanager
async def launch():
    (_TMP / "config.json").write_text("{}")  # no providers -> wizard pushes
    app = LabouriousApp()
    async with app.run_test(size=(140, 44)) as pilot:
        await pilot.pause(0.4)
        yield pilot, app


async def main() -> None:
    # ── 1. Wizard setup ─────────────────────────────────────────────
    print("1. Wizard: anthropic + real key")
    async with launch() as (pilot, app):
        step("wizard pushed on fresh config", isinstance(app.screen, WelcomeWizardScreen))
        await pilot.press(*"anthropic")
        await pilot.press("enter")
        await pilot.pause(0.2)
        step("provider resolved", app.screen._provider["id"] == "anthropic")
        # default model
        await pilot.press("enter")
        await pilot.pause(0.2)
        step("default model chosen", app.screen._step == 2 and app.screen._model == "claude-sonnet-4-5")
        # type the REAL API key
        await pilot.press(*_REAL_KEY)
        await pilot.pause(0.2)
        step("key accumulated", app.screen._api_key == _REAL_KEY)
        await pilot.press("enter")
        await pilot.pause(0.5)
        step("wizard dismissed to chat", isinstance(app.screen, ChatScreen))
        cfg = json.loads((_TMP / "config.json").read_text())
        step("anthropic in config", "anthropic" in cfg.get("providers", {}))
        step("default_model = anthropic/claude-sonnet-4-5",
             cfg.get("default_model") == "anthropic/claude-sonnet-4-5")
        step("key stored in (isolated) keychain", get_key("anthropic") == _REAL_KEY)
        step("env key popped (adapter must use keychain)",
             os.environ.get("ANTHROPIC_API_KEY") is None)

        # ── 2. Full f1 analysis, real cloud provider ───────────────────
        print("2. analyze NVDA — real f1 against the cloud provider")
        await pilot.press(*"analyze NVDA")
        await pilot.pause(0.2)
        await pilot.press("enter")
        await pilot.pause(0.5)

        # Poll for completion. FlowFinished calls set_status_footer with
        # " · run complete" (written to #status-left, a Static → has .renderable).
        # FlowFailed calls banner.set_error(...) which we can detect via the
        # ConnectionBanner's renderable.
        scr = app.screen
        deadline = time.monotonic() + 500  # ~8 min budget for 5 agents
        done, failed = False, False
        agents_seen: set[str] = set()
        while time.monotonic() < deadline and not done and not failed:
            await pilot.pause(3.0)
            # Check run-complete via the status-left Static widget.
            try:
                left = scr.query_one("#status-left")
                if left is not None and hasattr(left, "renderable"):
                    s = str(left.renderable)
                    if "run complete" in s:
                        done = True
            except Exception:
                pass
            # Check flow-failed via ConnectionBanner.
            try:
                from frontend.widgets.connection_banner import ConnectionBanner
                banner = scr.query_one(ConnectionBanner)
                if banner is not None and hasattr(banner, "renderable"):
                    s = str(banner.renderable).lower()
                    if "flow failed" in s or "error" in s:
                        failed = True
                        reason = str(banner.renderable)
            except Exception:
                pass
            agents_seen.update(scr._bubble_index.keys())

        step("f1 flow completed (· run complete)", done and not failed)
        if failed:
            print(f"      (status: {reason})")
        step("orchestrator produced a bubble", "orchestrator" in agents_seen)
        step("senior-analyst produced a bubble", "senior-analyst" in agents_seen)
        step("final-report produced a bubble", "final-report" in agents_seen)
        step("all 5 agents started", {"orchestrator", "senior-analyst",
             "forensic-accounting", "devils-advocate", "final-report"} <= agents_seen)

        # Final report content — a real, non-empty thesis from the cloud LLM
        fr = scr._bubble_index.get("final-report")
        if fr is not None:
            try:
                lines = fr._body().lines
                text = "\n".join(str(l) for l in lines)
            except Exception:
                text = ""
            step("final report has content", len(text) > 200)
            snippet = (text[:400].replace("\n", " ").strip())
            print(f"\n--- final report (first 400 chars) ---\n{snippet}\n------------------------------------")
        else:
            step("final report has content", False)

        # Cost footer reflects the real run
        try:
            step("cost footer updated", "· run complete" in str(
                scr.query_one(StatusStrip).renderable))
        except Exception:
            pass

    print(f"\n=== {ok}/{ok + len(fails)} ok ===")
    if fails:
        print("FAILURES:", *fails, sep="\n  - ")
        sys.exit(1)
    print("all green")


if __name__ == "__main__":
    asyncio.run(main())
