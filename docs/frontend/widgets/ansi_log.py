"""
ansi_log.py — RichLog that interprets inline ANSI SGR strings.

Textual 8 does NOT interpret ANSI escape sequences in RichLog content:
``log.write("\\x1b[38;2;140;220;220mhi\\x1b[0m")`` paints the literal
``[38;2;140;220;220m`` text (the "ghost text" bug class). The codebase
has many hand-rendered ANSI rows (settings rows, provider tiers, history
cards, citation tables), so this subclass converts every ``str`` write
through ``rich.text.Text.from_ansi`` — the one paint path that turns
escapes into real style spans. ``Text``/``Content`` writes pass through
untouched.

Use this anywhere a RichLog receives hand-rendered ANSI rows; plain
ASCII writes behave identically.
"""

from __future__ import annotations

from rich.text import Text as _RichText
from textual.widgets import RichLog


class AnsiRichLog(RichLog):
    """RichLog whose ``write()`` accepts raw ANSI strings safely."""

    def write(self, data, *args, **kwargs) -> None:  # noqa: D102 — see module doc
        if isinstance(data, str):
            # Only pay the conversion cost when escapes are present.
            if "\x1b" in data:
                data = _RichText.from_ansi(data)
        super().write(data, *args, **kwargs)


__all__ = ["AnsiRichLog"]
