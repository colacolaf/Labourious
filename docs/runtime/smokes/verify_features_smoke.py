"""verify_features_smoke.py — one-off E2E pilot for the new chat features.

Drives the REAL app with LABOURIOUS_MOCK=1 (deterministic, no API key):
  1. ChatHeader corner buttons exist (⚙ / ?) and open Settings / Help
  2. ChatControls nodes exist: depth / compressed / model / per-agent / ⚙ / ?
  3. Depth node click cycles depth and updates the label
  4. Compressed node toggles the flag
  5. Slash palette: typing "/" mounts it; typing more filters it
  6. Palette Tab-completes into the input
  7. Palette Enter runs the command (/depth DEEP)
  8. Esc closes the palette
  9. Full mock f1 run via typed prompt + Enter produces agent bubbles
 10. Ticker chips still present on welcome screen
Run:  PYTHONPATH=docs python3 docs/runtime/smokes/verify_features_smoke.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

THIS = Path(__file__).resolve()
DOCS = THIS.parents[2]
sys.path.insert(0, str(DOCS))

# Isolate config + force mock runtime BEFORE importing frontend.
_TMP = Path(tempfile.mkdtemp(prefix="verify-feats-"))
os.environ["LABOURIOUS_CONFIG"] = str(_TMP / "config.json")
os.environ["LABOURIOUS_MOCK"] = "1"
os.environ.pop("LABOURIOUS_MODEL", None)
(_TMP / "config.json").write_text(
    '{"providers": {"ollama": {"base_url": "http://localhost:11434"}},'
    ' "default_model": "ollama/llama3.2:3b"}'
)

_passed = 0
_failed = 0
_fails: list[str] = []


def step(label: str, ok: bool) -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ✓ {label}")
    else:
        _failed += 1
        _fails.append(label)
        print(f"  ✗ FAIL {label}")


async def main() -> None:
    from frontend.app import LabouriousApp
    from frontend.screens.chat import ChatScreen
    from frontend.screens.settings import SettingsScreen
    from frontend.screens.help import HelpModalScreen
    from frontend.widgets.chat_controls import ChatControls
    from frontend.widgets.chat_command_palette import CommandPalette, COMMANDS
    from frontend.widgets.chat_header import ChatHeader
    from frontend.widgets.ticker_shortcuts import TickerShortcuts
    from textual.widgets import Input

    app = LabouriousApp()
    async with app.run_test(size=(140, 44)) as pilot:
        await pilot.pause(0.4)
        scr = app.screen
        step("chat screen up", isinstance(scr, ChatScreen))

        # -- 1. header corner buttons --------------------------------------
        chat = scr
        hdr = chat.query_one(ChatHeader)
        btns = {b.id for b in hdr.query("Button")}
        step("header has hdr-settings + hdr-help",
             {"hdr-settings", "hdr-help"} <= btns)

        await pilot.click("#hdr-settings")
        await pilot.pause(0.2)
        step("⚙ opens Settings", isinstance(app.screen, SettingsScreen))
        await pilot.press("escape")
        await pilot.pause(0.2)
        step("back on chat", isinstance(app.screen, ChatScreen))

        await pilot.click("#hdr-help")
        await pilot.pause(0.2)
        step("? opens Help", isinstance(app.screen, HelpModalScreen))
        await pilot.press("escape")
        await pilot.pause(0.2)

        # -- 2. control nodes ----------------------------------------------
        ctl = chat.query_one("#chat-controls", ChatControls)
        ids = {b.id for b in ctl.query("Button")}
        step("controls: depth/compressed/model/per-agent/settings/help",
             {"chatctl-depth", "chatctl-compressed", "chatctl-model",
              "chatctl-peragent", "chatctl-settings", "chatctl-help"} <= ids)

        # -- 3. depth cycle --------------------------------------------------
        chat.depth = "STANDARD"
        await pilot.click("#chatctl-depth")
        await pilot.pause(0.2)
        step("depth click: STANDARD → DEEP", chat.depth == "DEEP")
        await pilot.click("#chatctl-depth")
        await pilot.pause(0.2)
        step("depth click: DEEP → SCAN", chat.depth == "SCAN")
        step("depth persisted to config", '"SCAN"' in
             (_TMP / "config.json").read_text() or "SCAN" in
             (_TMP / "config.json").read_text())

        # -- 4. compressed toggle --------------------------------------------
        chat.compressed = False
        await pilot.click("#chatctl-compressed")
        await pilot.pause(0.2)
        step("compressed click: off → on", chat.compressed is True)
        await pilot.click("#chatctl-compressed")
        await pilot.pause(0.2)
        step("compressed click: on → off", chat.compressed is False)

        # -- 5-8. slash palette ------------------------------------------------
        prompt = chat.query_one("#prompt", Input)
        chat.set_focus(prompt)
        await pilot.pause(0.1)

        await pilot.press("/")
        await pilot.pause(0.2)
        pal = None
        try:
            pal = chat.query_one("#chat-command-palette", CommandPalette)
        except Exception:
            pass
        step("typing '/' mounts palette", pal is not None)
        if pal is not None:
            step("palette lists all commands with empty filter",
                 len(pal._visible) == len(COMMANDS))

        await pilot.press(*"dep")
        await pilot.pause(0.2)
        step("filter 'dep' narrows to /depth",
             len(pal._visible) == 1 and pal._visible[0].name == "depth")

        await pilot.press("tab")
        await pilot.pause(0.2)
        step("tab completes '/depth ' into input",
             prompt.value.startswith("/depth"))
        step("palette still open after tab (args expected)",
             chat._palette_for() is not None)

        await pilot.press(*"DEEP")
        await pilot.pause(0.2)
        await pilot.press("enter")
        await pilot.pause(0.4)
        step("enter runs /depth DEEP", chat.depth == "DEEP")
        step("palette closed after run", chat._palette_for() is None)

        # Esc-close path
        chat.set_focus(prompt)
        prompt.value = "/"
        await pilot.pause(0.2)
        step("palette re-opens on '/'",
             chat._palette_for() is not None)
        await pilot.press("escape")
        await pilot.pause(0.2)
        step("esc closes palette", chat._palette_for() is None)

        # -- 9. mock flow run through the real submit path --------------------
        chat.set_focus(prompt)
        await pilot.press(*"analyze NVDA")
        await pilot.pause(0.1)
        await pilot.press("enter")
        # Mock stream is quick but give it a generous wall-clock budget.
        done = False
        for _ in range(40):
            await pilot.pause(0.5)
            if "run complete" in str(chat.query_one("#status-left").visual):
                done = True
                break
        step("mock f1 run completed", done)
        step("agents produced bubbles",
             {"orchestrator", "final-report"} <= set(chat._bubble_index.keys()))

        # -- 10. ticker chips --------------------------------------------------
        chips = chat.query_one("#ticker-shortcuts", TickerShortcuts)
        step("ticker chips widget present", chips is not None)

    print(f"\n=== {_passed}/{_passed + _failed} ok ===")
    if _fails:
        print("FAILURES:", *_fails, sep="\n  - ")
        sys.exit(1)
    print("all green")


if __name__ == "__main__":
    asyncio.run(main())
