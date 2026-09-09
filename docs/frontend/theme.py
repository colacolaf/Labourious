"""theme.py — the app-wide Textual theme.

Why this exists
===============
Textual ships a builtin dark theme whose `$primary` is a vivid blue
(#0178D4). Without an override, that blue leaks through every widget we
don't explicitly style: focused Input borders, cursors, scrollbars,
Button variants, Collapsible arrows. That was the source of the random
"blue spots" reported across the TUI.

This module registers a restrained theme derived from the palette in
style.tcss (brand cyan reserved for *identity*, never for focus):
    primary  = warm gray   (Input borders, cursors, selection)
    accent   = deep slate  (active chips, links)
    success  = sage        (positive status)
    warning  = amber       (stale/missing status)
    error    = muted coral (failures)

`register_theme()` must be called before `LabouriousApp().run()`.
"""

from __future__ import annotations

from textual.theme import Theme

# Hex mirrors of the style.tcss anchors.
HEX_BRAND = "#8cdcdc"   # brand cyan — identity only (titles, logo)
HEX_FG = "#d4d4d4"      # warm gray foreground
HEX_FG2 = "#a0a5af"     # soft gray
HEX_FG3 = "#6e7887"     # dim gray
HEX_HAIRLINE = "#465262"  # hairline borders
HEX_BG = "#0e1014"      # screen background
HEX_BG_ALT = "#11141a"  # surface background
HEX_OK = "#8cd296"      # sage
HEX_WARN = "#e6c87e"    # amber
HEX_ERR = "#e19194"     # muted coral

# ANSI SGR bodies for the render-only panels (same values as hex above).
# Panels embed ANSI codes in plain strings, so they can't use Textual
# variables — these keep the two systems in lockstep.
ANSI = {
    "brand":    "1;38;2;140;220;220",
    "fg":       "38;2;212;212;212",
    "fg2":      "38;2;160;165;175",
    "fg3":      "38;2;110;120;135",
    "faint":    "38;2;80;88;100",
    "ok":       "38;2;140;210;150",
    "warn":     "38;2;230;200;130",
    "err":      "38;2;225;145;140",
    "bg_sel":   "48;2;26;32;40",    # focused row background
    "bg_hover": "48;2;20;25;31",    # hovered row background
    "bg_card":  "48;2;22;26;33",    # expanded card background
}

LABOURIOUS_THEME = Theme(
    name="labourious",
    primary=HEX_FG,        # focus rings, cursors, Input borders → warm gray
    secondary=HEX_FG2,
    accent=HEX_HAIRLINE,   # active chips / highlights → deep slate, not blue
    success=HEX_OK,
    warning=HEX_WARN,
    error=HEX_ERR,
    foreground=HEX_FG,
    background=HEX_BG,
    surface=HEX_BG_ALT,
    panel=HEX_BG_ALT,
    variables={
        # Focus cursor: warm gray block, dark text.
        "block-cursor-background": HEX_FG,
        "block-cursor-foreground": HEX_BG,
        "block-cursor-blurred-background": HEX_FG3,
        "block-cursor-blurred-foreground": HEX_BG,
        "input-cursor-background": HEX_FG,
        "input-cursor-foreground": HEX_BG,
        "input-selection-background": "rgba(140, 220, 220, 0.20)",
        # Widget borders (Inputs, Selects, tooltips) — hairline, not blue.
        "border": HEX_HAIRLINE,
        "border-blurred": "#2a3441",
        # Scrollbars — deep slate, subtle against #0e1014.
        "scrollbar": "#2a3441",
        "scrollbar-hover": HEX_FG3,
        "scrollbar-active": HEX_FG2,
        "scrollbar-background": HEX_BG,
        "scrollbar-background-hover": HEX_BG,
        "scrollbar-background-active": HEX_BG,
        "scrollbar-corner-color": HEX_BG,
        "link-color": HEX_BRAND,
        "link-hover": "#f0f0f0",
    },
)


def register_theme(app) -> None:
    """Register the theme on an App instance (Textual 8 API — instance
    method). Call from LabouriousApp.__init__ before the first compose."""
    app.register_theme(LABOURIOUS_THEME)


__all__ = ["ANSI", "LABOURIOUS_THEME", "register_theme"]
