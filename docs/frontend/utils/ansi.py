"""
ansi.py — visible-width-aware helpers for hand-rendered ANSI strings.

The settings surface renders rows as inline-ANSI strings written into
RichLog widgets. Every fixed-width layout computed with plain ``len()``
breaks the moment a row contains escape sequences (each escape adds up
to ~19 invisible chars to ``len()`` but zero visible columns), so rows
wrap, misalign, or paint stray blocks. These helpers measure the
*visible* width only and pad/crop accordingly.

All helpers are pure string functions — no Textual imports — so they can
be used from widgets, screens, and smokes alike.
"""

from __future__ import annotations

import re

from rich.text import Text as _RichText

# Any CSI escape sequence (SGR colors, cursor moves, …).
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def to_text(s: str):
    """Convert an inline-ANSI string to a ``rich.text.Text``.

    Textual 8 does NOT interpret ANSI SGR sequences in ``Static`` or
    ``RichLog`` content — a raw string paints its escapes as literal
    ``[38;2;110;120;135m`` garbage (the "ghost text" class of bugs).
    Every widget that paints a hand-rendered ANSI string must funnel it
    through this helper so the escapes become real style spans.
    """
    return _RichText.from_ansi(s)

# Terminal width the panel renders assume when the real width is unknown
# (headless smokes, __main__ previews). Conservative: narrow terminals
# wrap rather than crop, which degrades gracefully.
DEFAULT_WIDTH = 110


def strip_ansi(s: str) -> str:
    """Remove every CSI escape sequence from `s`."""
    return _ANSI_RE.sub("", s)


def visible_len(s: str) -> int:
    """Length of `s` in visible columns (ignores escape sequences)."""
    return len(strip_ansi(s))


def pad_to(s: str, width: int) -> str:
    """Right-pad `s` with spaces to `width` visible columns.

    Never truncates — a string wider than `width` is returned unchanged
    (the terminal wraps it rather than eating content).
    """
    pad = width - visible_len(s)
    return s + " " * max(0, pad)


def crop_to(s: str, width: int, *, ellipsis: str = "\u2026") -> str:
    """Crop `s` to at most `width` visible columns, preserving escapes.

    Cuts in visible space, then re-appends whatever escape sequences
    followed the cut so trailing SGR state (colors) is kept intact. An
    ellipsis is appended when cropping actually happened.
    """
    if visible_len(s) <= width:
        return s
    if width <= 0:
        return ""
    # Reserve room for the ellipsis so the *total* visible width,
    # ellipsis included, never exceeds `width`.
    keep = max(0, width - (len(ellipsis) if ellipsis else 0))
    out: list[str] = []
    used = 0
    truncated = False
    i = 0
    while i < len(s):
        if s[i] == "\x1b":
            m = _ANSI_RE.match(s, i)
            if m:
                out.append(m.group(0))
                i = m.end()
                continue
        if used >= keep:
            truncated = True
            break
        out.append(s[i])
        used += 1
        i += 1
    if truncated:
        if ellipsis:
            out.append(ellipsis)
        # Keep any escape sequences that follow the cut (e.g. a trailing
        # reset) — they cost zero visible columns.
        out.extend(re.findall(_ANSI_RE, s[i:]))
    return "".join(out)


def fit_to(s: str, width: int, *, ellipsis: str = "\u2026") -> str:
    """Crop then pad `s` to exactly `width` visible columns."""
    return pad_to(crop_to(s, width, ellipsis=ellipsis), width)


def two_columns(left: str, right: str, width: int = DEFAULT_WIDTH) -> str:
    """Lay out `left` … `right` on one line, right column flush right.

    Both inputs may contain ANSI. The right column is cropped first so a
    long status string can never push the line past `width`.
    """
    left = " " + left
    right_max = max(4, width - visible_len(left) - 1)
    right = crop_to(right, right_max)
    gap = width - visible_len(left) - visible_len(right)
    if gap < 1:
        # Left too wide — crop it so the right column stays flush right.
        overflow = 1 - gap
        left = crop_to(left, visible_len(left) - overflow, ellipsis="")
        gap = 1
    return left + " " * gap + right


def reset_at_end(s: str) -> str:
    """Ensure `s` ends with an SGR reset so color never bleeds."""
    if not s:
        return s
    if visible_len(s) == 0:
        # Escapes only — append reset unless the tail already is one.
        return s if s.endswith("\x1b[0m") else s + "\x1b[0m"
    # If the last escape in the string is a reset we're done.
    escapes = _ANSI_RE.findall(s)
    if escapes and escapes[-1] == "\x1b[0m":
        return s
    return s + "\x1b[0m"
