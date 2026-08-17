"""
connection_banner.py — single-line status banner for the chat screen.

Shows a red or amber message when:
  - an API key is missing for the requested model
  - a tool / connector failed on the last run

Best-effort: this widget never raises; it just renders text. It defaults to
collapsed (height=1) so it doesn't reserve layout space when nothing is wrong.

Usage:
    banner = ConnectionBanner()
    banner.set_warning("Missing ANTHROPIC_API_KEY — open Settings (s).")
    banner.set_ok()  # clear
"""

from __future__ import annotations

from textual.widgets import Static


class ConnectionBanner(Static):
    """Single-line banner. Visible only when warning or error is set."""

    DEFAULT_TEXT = ""

    def __init__(self, **kwargs) -> None:
        super().__init__(self.DEFAULT_TEXT, markup=True, **kwargs)
        self.add_class("connection-banner")

    def set_warning(self, msg: str) -> None:
        self.update(f"⚠  {msg}")
        self.add_class("warn")
        self.remove_class("error")
        self.remove_class("hide")

    def set_error(self, msg: str) -> None:
        self.update(f"⛔  {msg}")
        self.add_class("error")
        self.remove_class("warn")
        self.remove_class("hide")

    def set_ok(self) -> None:
        self.update("")
        self.remove_class("warn")
        self.remove_class("error")
        self.add_class("hide")
