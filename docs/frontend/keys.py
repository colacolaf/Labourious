"""
keys.py — keybindings + the `/`-prefixed command palette + the help-modal catalog.

The binding catalog below is the *single source of truth* for both:
  - the persistent bottom strip on every screen (STRIP_BY_SCREEN)
  - the Help modal (BINDING_CATALOG)
  - the actual screen BINDINGS lists (each screen reads its own slice)

If a binding appears here, every screen renders it consistently — no
divergence between the strip's "what can I press" and the help modal's
"what does this do."
"""

from __future__ import annotations

# Single-letter shortcuts active from any focus except the chat Input.
APP_BINDINGS = [
    ("s",            "open_settings", "Settings"),
    ("h",            "open_history",  "History"),
    ("question_mark", "open_help",     "Help"),
    ("ctrl+q",       "quit",          "Quit"),
]


# --------------------------------------------------------------- BINDING_CATALOG
# Used by the Help modal. Each entry:
#   group:   which screen context the key applies to
#   key:     the literal key combo shown to the user
#   label:   short description (one line)
#   hint:    optional longer-form text
#
# Ordering matters — this is the order the cards appear in the modal.
#
# Field `glyph` lets us render ⏎ vs Enter etc consistently. The renderer
# normalizes ⏎ (U+23CE) as the Enter glyph and ⌘ alongside Ctrl when needed.
def _entries(*rows):
    return tuple({"key": k, "label": l, "hint": h} for (k, l, h) in rows)

BINDING_CATALOG: tuple[dict, ...] = (
    {"group": "Global", "note": "4 keys · any focus", "entries": _entries(
        ("s",       "Settings",                       ""),
        ("h",       "History",                        ""),
        ("?",       "Help",                           "toggle this modal"),
        ("Ctrl+Q",  "Quit",                           ""),
    )},
    {"group": "Chat",   "note": "input focused",      "entries": _entries(
        ("⏎",       "Send the prompt",                ""),
        ("Ctrl+L",  "Clear input",                    ""),
        ("Ctrl+R",  "Re-run last flow",               ""),
        ("/",       "Command palette",                "/flow /ticker /model /paid-for /depth /compressed /settings /history /help /clear /quit"),
        ("↑",       "Recall previous prompt",         ""),
    )},
    {"group": "Settings", "note": "modal scope",      "entries": _entries(
        ("Esc",          "Back to chat",            "cancels pending"),
        ("⏎",            "Confirm selection in picker", ""),
        ("Ctrl+S",       "Save & close",            ""),
        ("Ctrl+N",       "+ add",                    "provider / connector / override"),
        ("Ctrl+D",       "Remove selected row",     ""),
        ("e / ⏎",        "Edit field row",          ""),
        ("Tab",          "Save & advance",          "to next row"),
        ("1 / 2",        "Pick toggle",             "depth · compressed"),
        ("↑ / ↓",        "Rail",                     "between sections"),
        ("→ / ←",        "Section",                  "between fields"),
    )},
    {"group": "History",   "note": "modal scope",      "entries": _entries(
        ("Esc",     "Back to chat",                  ""),
        ("⏎",       "Drill into memo",               ""),
        ("/",       "Search past runs",              ""),
        ("r",       "Re-run this flow",              ""),
    )},
    {"group": "Citation",  "note": "chip → modal",     "entries": _entries(
        ("Esc / q",  "Back to chat",                 ""),
        ("⏎",        "Open URL in default browser",  ""),
        ("y",        "Copy selected URL",            ""),
        ("O",        "Open all",                     "launch every URL via webbrowser.open with throttle"),
        ("C",        "Copy all",                     "newline-joined list of every URL"),
        ("↑ / ↓",    "Navigate rows",                ""),
        ("1–9",      "Jump-and-open row",            ""),
    )},
    {"group": "Help",      "note": "this modal",       "entries": _entries(
        ("Esc", "Close this modal",                  ""),
        ("?",   "Toggle this modal",                 "open or close"),
    )},
)


# --------------------------------------------------- STRIP_BY_SCREEN (CSS-class key)
# The key in this dict must match the CSS class on the active Screen's container.
# The class is auto-set by Textual based on the class name, lowercased:
#   ChatScreen  → .chatscreen
#   SettingsScreen  → .settingsscreen
# We use suffixes so a screen pushed on top of chat still shows its own strip.
#
# Each value is a tuple of (group_label, [(key, label), ...]) which the
# StatusStrip widget renders left-to-right.
#
# The trailing special key "?" is appended by the widget itself — no need to
# add it here.
STRIP_BY_SCREEN: dict[str, tuple] = {
    "chatscreen": (
        ("chat", (
            ("⏎",      "send"),
            ("Ctrl+L", "clear"),
            ("Ctrl+R", "re-run"),
            ("/",      "commands"),
        )),
        ("global", (
            ("s", "settings"),
            ("h", "history"),
        )),
    ),
    "historyscreen": (
        ("history", (
            ("⏎", "drill"),
            ("/",  "search"),
            ("r",  "re-run"),
        )),
        ("exit", (
            ("Esc", "back"),
        )),
    ),
    "settingsscreen": (
        ("settings", (
            ("⏎",            "confirm"),
            ("e",             "edit row"),
            ("Ctrl+S",        "save & close"),
            ("Ctrl+N",        "+ add"),
            ("Ctrl+D",        "remove"),
            ("Tab",           "save & advance"),
            ("↑/↓", "rail"),
            ("→/←", "section"),
        )),
        ("exit", (
            ("Esc", "back"),
        )),
    ),

    "citationmodalscreen": (
        ("citation", (
            ("⏎",   "open"),
            ("y",   "copy"),
            ("O",   "open-all"),
            ("C",   "copy-all"),
            ("↑/↓", "row"),
            ("1–9", "jump"),
        )),
        ("exit", (
            ("Esc", "back"),
        )),
    ),
    "helpmodalscreen": (
        ("help", (
            ("Esc", "close"),
            ("?",   "toggle"),
        )),
        ("here", ()),
    ),
}


# -------------------------------------------------- L3 providers strip override
# Used by StatusStrip.update_for when the user is on SettingsScreen's
# providers section AND not in picker/edit mode.
L3_PROVIDERS_STRIP: tuple = (
    ("providers", (
        ("Tab",   "filter"),
        ("↑/↓",   "row"),
        ("⏎",     "expand"),
        ("e",     "edit"),
    )),
    ("global", (
        ("Ctrl+S", "save & close"),
    )),
    ("exit", (
        ("Esc", "collapse"),
    )),
)


# --------------------------------------------- Input-mode command palette
# Anything starting with `/` is intercepted by the Input widget before the
# model sees it. The chat screen parses these.
#
#   /flow f1                — choose a flow (f1-f8)
#   /ticker NVDA            — set the ticker
#   /model ollama/...       — set the default model
#   /paid-for final-report  — toggle hybrid (comma-separated agents)
#   /depth STANDARD         — SCAN | STANDARD | DEEP
#   /compressed             — toggle compressed mode
#   /settings               — open Settings modal
#   /history                — open History modal
#   /help                   — show help card
#   /clear                  — clear chat (alias: Ctrl+L)
#   /quit                   — quit (alias: Ctrl+Q)
COMMAND_PALETTE_PREFIX = "/"


def strip_for(screen: "Screen | None") -> tuple:
    """Return the right strip tuple for a given screen (or empty default)."""
    if screen is None:
        return ()
    # Match by class-name lowercased. Each `Screen` subclass gets the suffix
    # of its class name. We strip the trailing "screen" so the keys line up
    # with the CSS-class names in STRIP_BY_SCREEN.
    cls = type(screen).__name__.lower()
    return STRIP_BY_SCREEN.get(cls, ())
