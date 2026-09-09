"""
app.py — Textual App entrypoint.

Run with:
    python docs/frontend/app.py

Or, once installed as a script:
    labourious

Stack: Textual v4 + Rich. Settings + History modals are stubs (P2) — for now
they just print a placeholder so the keybindings work without crashing.
"""

from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App

# Make `frontend/` and `runtime/` importable as sibling packages under `docs/`
# when invoked via `python docs/frontend/app.py`. Without this, sys.path only
# contains scripts/, so neither package resolves.
_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parent.parent))                # docs/  — lets docs.frontend + docs.runtime work as packages

from frontend.screens import ChatScreen  # type: ignore
from frontend.screens.history import ReRunRequested  # type: ignore
from frontend.keys import APP_BINDINGS  # type: ignore
from frontend.theme import LABOURIOUS_THEME

# The class attribute below + the register_theme call in __init__ activate
# the restrained app theme before the first compose. Without it, Textual's
# builtin dark theme (vivid blue #0178D4 primary) leaks through focused
# Inputs, cursors, scrollbars and Buttons — the source of the stray blue
# spots across the TUI.


class LabouriousApp(App):
    """The Analyst's Bench — terminal interface."""

    TITLE = "Labourious"
    SUB_TITLE = "analyst's bench · v0"
    CSS_PATH = Path(__file__).with_name("style.tcss")
    BINDINGS = APP_BINDINGS

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Textual 8: register_theme is an instance method, and the active
        # theme is the `theme` reactive attribute. Register ours, then
        # activate it BEFORE the first compose so no default-blue styling
        # (builtin $primary #0178D4) ever paints.
        self.register_theme(LABOURIOUS_THEME)
        self.theme = "labourious"
        # Default model resolution order:
        #   1. LABOURIOUS_MODEL env override
        #   2. default_model saved in ~/.labourious/config.json (canonical)
        #   3. ollama/llama3.2:3b fallback (small, fast, common local pull)
        import os

        from frontend.config_io import load_config
        env_model = os.environ.get("LABOURIOUS_MODEL")
        if env_model:
            self._initial_model = env_model
        else:
            try:
                self._initial_model = load_config().default_model
            except Exception:
                self._initial_model = ""
            if not self._initial_model:
                self._initial_model = "ollama/llama3.2:3b"

    # ---------------------------------------------------------- compose
    def get_default_screen(self) -> Screen:
        """The chat screen is the only screen at startup. P2 modals will push
        themselves on top via `self.app.push_screen(...)`."""
        from frontend.screens import ChatScreen  # type: ignore
        chat = ChatScreen()
        chat._initial_model = self._initial_model
        return chat

    # ---------------------------------------------------------- actions
    def action_open_settings(self) -> None:
        """Push the Settings modal on top of the current screen."""
        from frontend.screens import SettingsScreen  # type: ignore
        self.push_screen(SettingsScreen())

    def action_open_history(self) -> None:
        """Push the History modal on top of the current screen."""
        from frontend.screens import HistoryScreen  # type: ignore
        self.push_screen(HistoryScreen())

    def on_rerun_requested(self, message: ReRunRequested) -> None:
        """Forward re-run request from HistoryScreen to ChatScreen."""
        if isinstance(self.screen, ChatScreen):
            self.screen.run_from_history(message.ticker, message.flow_id)

    def action_open_help(self) -> None:
        """Toggle behavior: if the Help modal is on top, pop it; otherwise push."""
        from frontend.screens import HelpModalScreen  # type: ignore
        # If the top of stack IS the help modal, treat ? as toggle-close.
        if isinstance(self.screen, HelpModalScreen):
            self.pop_screen()
            return
        # Otherwise push a fresh one. Textual retains the new instance's
        # state across pushes.
        self.push_screen(HelpModalScreen())


def main() -> int:
    """Run the App. Returns the exit code."""
    LabouriousApp().run(headless=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
