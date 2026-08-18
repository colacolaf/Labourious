"""
status_strip.py — the persistent bottom strip on every screen.

The strip renders two things, side-by-side, in one row:
  LEFT  — the current screen's key bindings (read from keys.STRIP_BY_SCREEN)
  RIGHT — the constant "? help" tag (always there, so users learn the muscle)

Why a custom widget instead of Textual's built-in Footer:
  - Footer's visual style doesn't match our brand tokens (we'd override half of
    its TCSS anyway)
  - We want the "?" tag as a *consistent affordance*, not just another footer key
  - The strip should show *one screen's* bindings — even when a modal is pushed
    on top of chat, the strip's content tracks the modal.

Architecture: the strip is a `Horizontal` containing two `Static` widgets:
  - `StatusStripLeft`  — the screen-aware key hints (refreshes with the screen)
  - `StatusStripRight` — the always-on "? help" tag (flips to "? close" when
                        the help modal itself is on top)

update_for(screen) refreshes BOTH ends. The Composed widget is `StatusStrip`.
"""

from __future__ import annotations

from textual.containers import Horizontal
from textual.widgets import Static

# ANSI tokens — mirror style.tcss `.footer--key` / `.brand` / `.fg3`
_RESET   = "\x1b[0m"
_DIM     = "\x1b[38;2;110;120;135m"   # FG3 — group label, soft
_BRIGHT  = "\x1b[38;2;140;220;220m"   # brand cyan — key glyphs
_FG      = "\x1b[38;2;212;212;212m"   # FG — pair label
_HAIR    = "\x1b[38;2;70;82;98m"      # border


def render_pairs_line(
    groups: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] | list,
) -> str:
    """Render the LEFT side of the strip from a (group_label, pairs) tuple."""
    parts: list[str] = []
    for gi, (label, pairs) in enumerate(groups):
        if gi > 0:
            parts.append(f"{_HAIR}│{_RESET} ")
        else:
            parts.append(" ")
        # Group label is uppercase + dim
        parts.append(f"{_DIM}{label.upper()}{_RESET} ")
        for ki, (key, text) in enumerate(pairs):
            if ki > 0:
                parts.append(" ")
            parts.append(f"{_BRIGHT}{key}{_RESET}{_DIM} {_FG}{text}{_RESET}")
    return "".join(parts)


def render_help_tag(mode: str = "open") -> str:
    """
    The right-corner tag.  mode:
      - "open"  → "?  help"  (default, open help modal)
      - "close" → "?  close" (help modal is on top, ? will toggle it closed)
      - "none"  → ""         (suppressed, e.g. help modal's own strip is fully compact)
    """
    if mode == "none":
        return ""
    # Pad left so the tag visually anchors to the right.
    # We use Soft-Hyphen-free approach: just put the tag at the end and rely on
    # CSS .status-right { align: right middle } to right-justify it.
    text = "?  help" if mode == "open" else "?  close"
    return f"{_BRIGHT}{text}{_RESET}"


class StatusStripRight(Static):
    """The always-on right side. ?  help / ?  close."""

    DEFAULT_CSS = """
    StatusStripRight {
        width: auto;
        color: #8cdcdc;
        background: #11141a;
        text-style: bold;
        padding: 0 1;
    }
    """

    def __init__(self, id: str | None = None) -> None:
        super().__init__("", markup=False, id=id or "status-right")
        self._mode: str = "open"

    def update_mode(self, mode: str) -> None:
        self._mode = mode
        self.update(render_help_tag(mode))


class StatusStripLeft(Static):
    """The screen-aware left side. Shows current screen's key hints."""

    DEFAULT_CSS = """
    StatusStripLeft {
        width: 1fr;
        height: 1;
        background: #11141a;
        color: #a0a5af;
        padding: 0 1;
    }
    """

    def __init__(self, id: str | None = None) -> None:
        super().__init__("", markup=False, id=id or "status-left")

    def update_groups(self, groups) -> None:
        self.update(render_pairs_line(groups))


class StatusStrip(Horizontal):
    """
    Bottom strip. Composed of left (pairs) + a 1-col gap + right (? help).
    Mount once per Screen via compose(). Call update_for(screen) on mount,
    on push_screen, and on pop_screen.
    """

    DEFAULT_CSS = """
    StatusStrip {
        height: 1;
        width: 100%;
        background: #11141a;
        layout: horizontal;
    }
    StatusStrip > StatusStripLeft {
        width: 1fr;
    }
    StatusStrip > StatusStripRight {
        width: auto;
    }
    """

    def __init__(self, id: str | None = None) -> None:
        super().__init__(id=id or "status-strip")
        self._left = StatusStripLeft()
        self._right = StatusStripRight()

    def compose(self):
        yield self._left
        yield self._right

    def update_for(self, screen) -> None:
        """Refresh for the given (top of stack) screen."""
        from frontend.keys import strip_for, L3_PROVIDERS_STRIP
        groups = strip_for(screen)
        # If we're on SettingsScreen AND the L3 providers panel is active,
        # swap to the L3-specific binding set.
        try:
            if (screen is not None
                and type(screen).__name__ == "SettingsScreen"
                and screen._rail_index == 0  # providers = first rail
                and not screen._picker_open
                and not screen._editing):
                groups = L3_PROVIDERS_STRIP
        except Exception:
            pass
        cls = type(screen).__name__.lower() if screen is not None else ""
        # Default: ? open. Flip on the help modal itself.
        if cls == "helpmodalscreen":
            mode = "close"
        else:
            mode = "open"
        self._left.update_groups(groups)
        self._right.update_mode(mode)

    def set_status(self, msg: str) -> None:
        """Append a transient status to the LEFT side of the strip.

        Format adds the message as a final pair: `... · <msg>`. Used by chat
        to drop '✓ run complete', '! flow failed', '⏳ running f1', etc.
        Resets to the screen's binding-based content when the next
        update_for() runs.
        """
        from frontend.keys import strip_for
        # Re-read the screen from app.screen and append msg to the right of
        # whatever group is currently shown.
        try:
            groups = strip_for(self.app.screen) if self.app and self.app.screen else ()
        except Exception:
            groups = ()
        if not groups:
            self._left.update_groups(())
            return
        last_label, last_pairs = groups[-1]
        # Treat the message as another pair in the last group.
        msg_pair = ("✓", msg) if msg.startswith("✓") else ("●", msg)
        augmented = list(groups)
        augmented[-1] = (last_label, tuple(list(last_pairs) + [msg_pair]))
        self._left.update_groups(tuple(augmented))

    def clear_status(self) -> None:
        """Drop any transient status pair and restore the screen's bindings."""
        self.update_for(self.app.screen)
