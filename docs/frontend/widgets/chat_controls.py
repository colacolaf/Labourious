"""
chat_controls.py — persistent control nodes on the chat input bar.

A one-line strip of real Buttons docked with the prompt, exposing the
session knobs users would otherwise have to remember slash commands for:

    depth [STANDARD]  — click cycles SCAN → STANDARD → DEEP
    compressed [off]  — click toggles compressed mode
    model [ollama/…]  — click cycles discovered/configured models
    per-agent         — click opens Settings → per-agent section
    ⚙ settings        — click opens Settings (also: Ctrl+O)
    ? help            — click opens the keyboard-shortcuts modal (?)

Per-agent model overrides live in Settings (rail section “per-agent”),
which is the screen that owns that editor — the per-agent node deep-links
there instead of duplicating it.

The strip never executes anything itself: each click posts a message and
ChatScreen decides (and persists via its existing set_* methods, which
already round-trip ~/.labourious/config.json).
"""

from __future__ import annotations

from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Static


class ChatControls(Horizontal):
    """Control nodes rendered inline with the chat input bar."""

    DEFAULT_CSS = """
    ChatControls {
        height: 1;
        width: 1fr;
        align: left middle;
        padding: 0 0 0 1;
    }
    ChatControls > Button {
        min-width: 6;
        width: auto;
        height: 1;
        border: none;
        padding: 0 1;
        margin: 0 1 0 0;
        background: #11141a;
        color: #a0a5af;
    }
    ChatControls > Button:hover {
        background: #1c232d;
        color: #f0f0f0;
    }
    ChatControls > Button:focus {
        border: none;
        text-style: bold;
    }
    ChatControls > .chatctl-sep {
        width: 1;
        color: #2a3441;
    }
    """

    class DepthPressed(Message):
        """Depth node clicked — screen cycles to the next depth."""

        def __init__(self) -> None:
            super().__init__()

    class CompressedPressed(Message):
        """Compressed node clicked — screen toggles the flag."""

        def __init__(self) -> None:
            super().__init__()

    class ModelPressed(Message):
        """Model node clicked — screen cycles the default model."""

        def __init__(self) -> None:
            super().__init__()

    class PerAgentPressed(Message):
        """Per-agent node clicked — screen opens Settings → per-agent."""

        def __init__(self) -> None:
            super().__init__()

    class SettingsPressed(Message):
        """Settings node clicked."""

        def __init__(self) -> None:
            super().__init__()

    class HelpPressed(Message):
        """Help node clicked."""

        def __init__(self) -> None:
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._depth: str = "STANDARD"
        self._compressed: bool = False
        self._model: str = ""

    # ------------------------------------------------------------- compose
    def compose(self):
        # depth node — cycles SCAN → STANDARD → DEEP
        yield Button("", id="chatctl-depth", classes="chatctl-btn",
                     variant="default")
        # compressed node — toggles on/off
        yield Button("", id="chatctl-compressed", classes="chatctl-btn",
                     variant="default")
        # model node — cycles the model list
        yield Button("", id="chatctl-model", classes="chatctl-btn",
                     variant="default")
        # per-agent deep link
        yield Button("⋈ per-agent", id="chatctl-peragent",
                     classes="chatctl-btn", variant="default")
        yield Static("│", classes="chatctl-sep")
        # settings + help nodes (top-right corner affordance)
        yield Button("⚙ settings", id="chatctl-settings",
                     classes="chatctl-btn", variant="default")
        yield Button("? help", id="chatctl-help",
                     classes="chatctl-btn", variant="default")

    # ------------------------------------------------------------- labels
    def refresh_labels(self, *, depth: str, compressed: bool,
                       model: str) -> None:
        """Repaint the node labels from live session state. Called by
        ChatScreen whenever depth / compressed / model changes."""
        self._depth = depth
        self._compressed = compressed
        self._model = model
        # Next value preview: the label shows what a click switches TO,
        # which makes the affordance self-explanatory.
        order = ("SCAN", "STANDARD", "DEEP")
        nxt = order[(order.index(depth) + 1) % len(order)] if depth in order else "STANDARD"
        depth_glyph = {"SCAN": "◌", "STANDARD": "◐", "DEEP": "●"}.get(depth, "◐")
        try:
            self.query_one("#chatctl-depth", Button).label = (
                f"{depth_glyph} depth:{nxt}")
            self.query_one("#chatctl-compressed", Button).label = (
                f"compressed:{'on' if compressed else 'off'}")
            model_short = model if len(model) <= 24 else model[:21] + "…"
            self.query_one("#chatctl-model", Button).label = (
                f"✦ {model_short}" if model_short else "✦ model")
        except Exception:
            # Buttons not mounted yet (pre-compose refresh) — labels are
            # set again by the next refresh_labels call.
            pass

    # ------------------------------------------------------------- clicks
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "chatctl-depth":
            self.post_message(self.DepthPressed())
        elif btn_id == "chatctl-compressed":
            self.post_message(self.CompressedPressed())
        elif btn_id == "chatctl-model":
            self.post_message(self.ModelPressed())
        elif btn_id == "chatctl-peragent":
            self.post_message(self.PerAgentPressed())
        elif btn_id == "chatctl-settings":
            self.post_message(self.SettingsPressed())
        elif btn_id == "chatctl-help":
            self.post_message(self.HelpPressed())
        # Buttons are can_focus=True by default; steal focus back to the
        # prompt so typing continues seamlessly. The screen does this in
        # its message handlers (it owns the input reference).
