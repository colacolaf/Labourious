"""
chat_header.py — the chat screen's top bar with corner action buttons.

A single 1-row Horizontal bar:

    Labourious · analyst's bench · v0          14:03:22   ⚙  ?

Built from plain ``Static`` children (NOT a nested Textual ``Header``).
The real Header's own DEFAULT_CSS (``dock: top`` + ``width: 100%``) makes
it escape any plain container it is nested in — grid, Horizontal, you
name it — which is exactly why earlier attempts pushed the buttons
off-screen. Statics have no such baggage: they lay out in normal flow.

ChatScreen handles the Button.Pressed events and routes them through
``App.action_open_settings`` / ``App.action_open_help`` — the same paths
as the keyboard shortcuts, so toggle/stack behavior stays identical.
Buttons are can_focus=False, so they never steal focus from the prompt.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Button, Static


class _TitleLine(Static):
    """Left side of the bar — renders the app title + subtitle in one line."""


class _ClockLine(Static):
    """Right-side clock, updated once a second by the widget's own timer."""

    time: reactive[str] = reactive(lambda: "")

    def on_mount(self) -> None:
        self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        from datetime import datetime
        self.time = datetime.now().strftime("%H:%M:%S")

    def render(self) -> str:
        return self.time


class ChatHeader(Horizontal):
    """Top bar: title (left) · clock + ⚙ / ? buttons (right)."""

    DEFAULT_CSS = """
    ChatHeader {
        dock: top;
        width: 100%;
        height: 1;
    }
    ChatHeader #hdr-title {
        width: 1fr;
        height: 1;
        color: #8cdcdc;
        text-style: bold;
        padding: 0 1;
    }
    ChatHeader #hdr-clock {
        width: auto;
        height: 1;
        color: #6e7887;
        padding: 0 1;
    }
    ChatHeader Button {
        width: auto;
        height: 1;
        border: none;
        min-width: 3;
        padding: 0 1;
        margin: 0;
        background: #141a21;
        color: #8cdcdc;
        text-style: bold;
    }
    ChatHeader Button:hover {
        background: #1c232d;
        color: #f0f0f0;
    }
    ChatHeader Button:focus {
        border: none;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Labourious · analyst's bench · v0", id="hdr-title")
        yield _ClockLine("", id="hdr-clock")
        # Top-right corner affordances. Tooltips double as discovery for
        # the equivalent keyboard shortcuts. Click-only: can_focus=False
        # keeps them out of the tab/auto-focus chain (keyboard users have
        # Ctrl+O / ?), so they can never steal focus from the prompt.
        for btn_id, glyph, tip in (
            ("hdr-settings", "⚙", "Settings (Ctrl+O)"),
            ("hdr-help", "?", "Keyboard shortcuts (?)"),
        ):
            btn = Button(glyph, id=btn_id, variant="default", tooltip=tip)
            btn.can_focus = False
            yield btn
