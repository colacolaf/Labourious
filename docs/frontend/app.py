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
from frontend.keys import APP_BINDINGS  # type: ignore


class LabouriousApp(App):
    """The Analyst's Bench — terminal interface."""

    TITLE = "Labourious"
    SUB_TITLE = "analyst's bench · v0"
    BINDINGS = APP_BINDINGS

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Default model — overridden by Settings; runtime-style config lives at
        # ~/.labourious/config.json (PROTOCOL.md Appendix A).
        # For v1 we just pass a CLI override or fall back to ollama.
        import os
        env_model = os.environ.get("LABOURIOUS_MODEL")
        if env_model:
            self._initial_model = env_model
        else:
            self._initial_model = "ollama/llama3.3:70b"

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
        """P2: full Settings modal. For v1, show a notification banner."""
        try:
            chat = self.screen
            assert isinstance(chat, ChatScreen)
            chat._set_banner_warning(
                "Settings modal is P2. Edit ~/.labourious/config.json directly. See PROTOCOL.md Appendix A."
            )
        except Exception:
            pass

    def action_open_history(self) -> None:
        """P2: full History browser. For v1, show a notification banner."""
        try:
            chat = self.screen
            assert isinstance(chat, ChatScreen)
            chat._set_banner_warning(
                "History modal is P2. Use `python docs/runtime/thesis_register/register.py show <TICKER>` for now."
            )
        except Exception:
            pass

    def action_open_help(self) -> None:
        try:
            chat = self.screen
            assert isinstance(chat, ChatScreen)
            chat._show_welcome(force=True)
        except Exception:
            pass


def main() -> int:
    """Run the App. Returns the exit code."""
    LabouriousApp().run(headless=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
