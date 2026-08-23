"""wizard_e2e_smoke.py — end-to-end wizard pilot inside the REAL app [ux-1].

Launches LabouriousApp (real ChatScreen) with an isolated, provider-free
config, so ChatScreen.on_mount pushes the real wizard. Drives it with real
key events via Textual's pilot and asserts the persisted config + dismissal.

Hermetic: redirects HOME to a temp dir and sets LABOURIOUS_TEST so the
storage backend is the test keyring and the user's real keychain/config
are never touched.

Scenarios:
  A. Fresh launch -> wizard auto-pushed, paints without crashing.
  B. Full happy path: type "ollama" + Enter -> default model Enter -> Finish.
     Config file must contain ollama provider + default_model.
  C. Relaunch with that config -> wizard NOT pushed (chat screen direct).
  D. Esc skip path on a fresh config -> dismissed, nothing written.
  E. Keyed provider (anthropic): select + model + type API key -> saved via
     keys_storage (file backend in this env) + api_key_env recorded.

Run: PYTHONPATH=docs python3 docs/runtime/smokes/wizard_e2e_smoke.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

# --- isolate everything before importing frontend modules -------------------
_TMP = Path(tempfile.mkdtemp(prefix="wizard-e2e-"))
os.environ["HOME"] = str(_TMP)
os.environ["LABOURIOUS_CONFIG"] = str(_TMP / "config.json")
# Hermetic key storage: with a redirected HOME the real macOS keychain is
# unavailable ("cannot find a keychain") — the test backend keeps the key
# in a file under the temp HOME and never touches the user's keychain.
os.environ["LABOURIOUS_TEST"] = "1"
# No providers configured -> wizard must auto-push on first mount.
_TMP_CFG = _TMP / "config.json"
_TMP_CFG.write_text("{}")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from frontend.app import LabouriousApp
from frontend.screens.welcome_wizard import WelcomeWizardScreen
from frontend.screens.chat import ChatScreen

ok = 0


def step(desc: str, cond: bool) -> None:
    global ok
    print(f"  {'✓' if cond else '✗ FAIL'} {desc}")
    if not cond:
        raise AssertionError(desc)
    ok += 1


@asynccontextmanager
async def launch():
    """Start the real app; yield (pilot, app) inside run_test."""
    app = LabouriousApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)
        yield pilot, app


async def main() -> None:
    # ── A. Fresh launch → wizard auto-push + paints ────────────────────────
    print("A. Fresh launch → wizard auto-pushed")
    async with launch() as (pilot, app):
        step("wizard is the current screen", isinstance(app.screen, WelcomeWizardScreen))
        step("wizard painted (no render crash)", app.screen._step == 0)
        body = app.screen.query_one("#wizard-body").renderable
        step("step 0 lists providers", "ollama" in str(body) and "anthropic" in str(body))
        await pilot.press("escape")
        await pilot.pause(0.2)
        step("Esc dismisses back to ChatScreen", isinstance(app.screen, ChatScreen))

    # ── B. Happy path — ollama (no key) ────────────────────────────────────
    print("B. Happy path: ollama → default model → finish")
    async with launch() as (pilot, app):
        step("wizard auto-pushed again", isinstance(app.screen, WelcomeWizardScreen))
        # type provider id
        await pilot.press(*"ollama")
        await pilot.pause(0.1)
        scr = app.screen
        step("typed id accumulated", scr._provider_input == "ollama")
        await pilot.press("enter")
        await pilot.pause(0.2)
        step("step 1 (model) after Enter", app.screen._step == 1)
        step("provider resolved", app.screen._provider["id"] == "ollama")
        # Enter on step 1 → default model
        await pilot.press("enter")
        await pilot.pause(0.2)
        step("step 2 (key) + default model", app.screen._step == 2 and app.screen._model == "llama3.3:70b")
        # Finish (no key needed)
        await pilot.press("enter")
        await pilot.pause(0.3)
        step("wizard dismissed to ChatScreen", isinstance(app.screen, ChatScreen))
        cfg = json.loads(_TMP_CFG.read_text())
        step("config has ollama provider", "ollama" in cfg.get("providers", {}))
        step("default_model persisted", cfg.get("default_model") == "ollama/llama3.3:70b")

    # ── C. Relaunch → wizard NOT re-pushed (providers exist) ───────────────
    print("C. Relaunch with saved config → no wizard")
    async with launch() as (pilot, app):
        step("chat screen directly, no wizard", isinstance(app.screen, ChatScreen))

    # ── D. Esc skip on empty config → nothing written ──────────────────────
    print("D. Esc skip path")
    os.unlink(_TMP_CFG)
    _TMP_CFG.write_text("{}")
    async with launch() as (pilot, app):
        step("wizard pushed on fresh config", isinstance(app.screen, WelcomeWizardScreen))
        await pilot.press("escape")
        await pilot.pause(0.3)
        step("Esc dismisses to ChatScreen", isinstance(app.screen, ChatScreen))
        step("nothing written to config", json.loads(_TMP_CFG.read_text()) == {})

    # ── E. Keyed provider: anthropic + typed API key ───────────────────────
    print("E. Keyed provider (anthropic) + stored key")
    async with launch() as (pilot, app):
        await pilot.press(*"anthropic")
        await pilot.press("enter")
        await pilot.pause(0.2)
        step("anthropic selected", app.screen._provider["id"] == "anthropic")
        await pilot.press("enter")
        await pilot.pause(0.2)
        step("step 2, default model", app.screen._step == 2 and app.screen._model == "claude-sonnet-4-5")
        # Type the API key char by char
        await pilot.press(*"sk-ant-test1234")
        await pilot.pause(0.2)
        step("api key accumulated", app.screen._api_key == "sk-ant-test1234")
        await pilot.press("enter")
        await pilot.pause(0.3)
        step("wizard dismissed", isinstance(app.screen, ChatScreen))
        cfg = json.loads(_TMP_CFG.read_text())
        step("anthropic provider in config", "anthropic" in cfg.get("providers", {}))
        step("api_key_env recorded", cfg["providers"]["anthropic"].get("api_key_env") == "ANTHROPIC_API_KEY")
        step("default_model anthropic", cfg.get("default_model") == "anthropic/claude-sonnet-4-5")
        # Key stored via keys_storage
        from frontend.keys_storage import get_key
        stored = get_key("anthropic")
        step("key retrievable from keys_storage", stored == "sk-ant-test1234")

    print(f"\n=== {ok}/{ok} ok ===\nall green")


if __name__ == "__main__":
    asyncio.run(main())