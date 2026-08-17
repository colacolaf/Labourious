"""
setting_row.py — builds the ANSI text for one configuration row inside the
                  Settings modal.

The Settings modal renders its rows as ANSI strings written into RichLog
(SectionCard.body). That avoided the Static-with-str layout versioning
bug we hit in Textual 3.7. This module owns the row-formatting rules so
the styling lives in one place.

Pattern per row (110-col target):

      ●  <name col 16ch>   <detail cap 54ch>          <health 12ch>  ✕

Where:
    bullet glyph + color    health ("set" / "missing" / "ok" / "local")
    name col cyan/brand     health chip sage/amber/fg3
    detail col fg3          ✕ glyph in fg3 (focus-visible cyan later)

Nothing here returns a widget. The row is a *string* that the
SettingsScreen writes into the SectionCard.body RichLog. This keeps the
implementation lean (no per-row widget recompose on every change).
"""

from __future__ import annotations

import re
from dataclasses import replace

# ---- color ANSI strings (matching style.tcss) ---------------------------------
_BOLD_CYAN  = "1;38;2;140;220;220"
_SAGE       = "38;2;140;210;150"
_AMBER      = "38;2;230;200;130"
_FG3        = "38;2;110;120;135"
_FG2        = "38;2;160;165;175"
_FG         = "38;2;212;212;212"

_BULLET = {
    "set":     ("●", _SAGE),
    "ok":      ("●", _SAGE),
    "local":   ("●", _FG3),
    "missing": ("●", _AMBER),
    "warn":    ("⚠", _AMBER),
    "err":     ("⛔", "38;2;225;145;140"),
}


def _health_label(h: str) -> tuple[str, str]:
    """Returns (label, ansi-prefix-for-health-color)."""
    return {
        "set":     ("● set",     _SAGE),
        "missing": ("● missing", _AMBER),
        "ok":      ("● ok",      _SAGE),
        "local":   ("● ok",      _FG3),
        "warn":    ("⚠ stale",   _AMBER),
        "err":     ("⛔ error",   "38;2;225;145;140"),
    }.get(h, ("● ok", _SAGE))


def render_row(name: str, detail: str = "", health: str = "ok",
               removable: bool = True, width: int = 110) -> str:
    """Build the ANSI string for one Settings row.

    width: target terminal width; layout adjusts the detail column.
    """
    bullet_glyph, bullet_ansi = _BULLET.get(health, ("●", _FG3))
    hl, hl_ansi = _health_label(health)

    # Column widths: 16 (name), 12 (health), 3 (x) leaves ~75 for detail,
    # minus 4 fixed glyphs, ± edge padding.
    name_col = name[:16].ljust(16)
    detail_budget = max(8, width - 16 - 12 - 8)
    detail_clean = _strip_ansi(detail)[:detail_budget].ljust(detail_budget)
    health_col = hl.rjust(12)

    parts = [
        f"\x1b[{bullet_ansi}m  {bullet_glyph}\x1b[0m",
        f"\x1b[{_BOLD_CYAN}m{name_col}\x1b[0m",
        f"\x1b[{_FG2}m  {detail_clean}\x1b[0m",
        f"\x1b[{hl_ansi}m{health_col}\x1b[0m",
    ]
    if removable:
        parts.append(f"\x1b[{_FG3}m  ✕\x1b[0m")
    return "".join(parts)


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


# Kept for legacy imports
class SettingRow:
    """Empty compatibility shim. The Settings modal calls render_row()
    directly; this class is retained so the import surface doesn't break.
    """
    def __init__(self, **_kw) -> None:
        raise NotImplementedError(
            "SettingRow is a render helper, not a widget. "
            "Use render_row(name, detail, health) to build an ANSI row."
        )
