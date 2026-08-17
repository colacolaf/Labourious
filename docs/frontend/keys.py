"""
keys.py — keybindings + the `/`-prefixed command palette.

Single-letter commands (`s`, `h`, `q`) are bound at the *App* level but only fire
when the chat Input is not focused (Textual's `priority=True` and a small
`Input.is_focused` check in the App handle that). Enter, Ctrl+L, Ctrl+R are
handled in the ChatScreen directly.
"""

from __future__ import annotations

# App-level bindings (single-letter shortcuts).
APP_BINDINGS = [
    ("s",        "open_settings", "Settings"),
    ("h",        "open_history",  "History"),
    ("ctrl+q",   "quit",          "Quit"),
    ("question_mark", "open_help", "Help"),
]

# Input-mode command palette. Anything starting with `/` is intercepted by the
# Input widget itself before it reaches the model. The chat screen parses these.
#
#   /flow f1                — choose a flow (f1-f8)
#   /ticker NVDA            — set the ticker
#   /model ollama/...       — set the default model
#   /paid-for final-report  — toggle hybrid (comma-separated agents)
#   /depth STANDARD         — SCAN | STANDARD | DEEP
#   /compressed             — toggle compressed mode (carried by the prompt)
#   /settings               — open Settings modal
#   /history                — open History modal
#   /help                   — show help card
#   /clear                  — clear chat (alias: Ctrl+L)
#   /quit                   — quit (alias: Ctrl+Q)
COMMAND_PALETTE_PREFIX = "/"
