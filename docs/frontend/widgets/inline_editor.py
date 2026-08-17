"""
inline_editor.py — the inline-edit widgets used by the Settings modal.

Two variants:

  * InlineTextEditor     — Input + helper line. Used for default_model
                            and per_agent_model[name] (text validation).
  * InlineToggleEditor   — Two-option toggle. Used for defaults_depth
                            (STANDARD / DEEP) and defaults_compressed
                            (true / false).

Each variant posts typed Message events upward. The SettingsScreen
listens for those messages and decides what to do (commit, advance,
exit edit mode, show validation error).

Key wiring (Textual 3.7):
  Enter     Input.Submitted fires       -> validate -> commit
  Tab       InlineTextEditor.on_key     -> validate -> commit (and advance via screen)
  Esc       InlineTextEditor.BINDING    -> revert
  1 / 2     InlineToggleEditor.on_key   -> direct pick (auto-saves on commit)
  Tab       InlineToggleEditor.on_key   -> cycle (auto-saves on commit)
  Esc       InlineToggleEditor.BINDING  -> done (no-op save, screen exits)

Validation error UX (text fields): editor keeps the Input open and
shows a coral `● invalid: <reason>` line above it, plus an example
hint below. Screen keeps the editor mounted; the user fixes and
re-submits.
"""

from __future__ import annotations

import re
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Input, Static


# Source of truth for valid chars. Must match config_io._validate().
_MODEL_RE = re.compile(r"^[a-z0-9_-]+/[a-z0-9._:/-]{1,80}$", re.IGNORECASE)


def _validate_model(value: str) -> str | None:
    """Returns error string or None. Mirror of config_io.validate_model_id
    so we don't have to import config_io (avoids any circular import
    while the SettingsScreen is mid-import)."""
    v = (value or "").strip()
    if not v:
        return "empty"
    if not _MODEL_RE.match(v):
        return "expected provider/name (lowercase provider · slash · short id)"
    return None


def slug(s: str) -> str:
    """Textual widget ids must be alphanumeric + dashes + underscores."""
    return re.sub(r"[^a-zA-Z0-9_-]", "-", s)


# --------------------------------------------------------------- messages
class TextEditCommitted(Message):
    """User pressed Enter or Tab with a valid value.

    `via` is either "enter" (commit, no advance) or "tab" (commit + advance
    to next row in collection sections; commit + exit in single-row sections).
    """
    def __init__(self, editor_id: str, value: str, via: str = "enter") -> None:
        super().__init__()
        self.editor_id = editor_id
        self.value = value
        self.via = via


class TextEditReverted(Message):
    """User pressed Esc — discard changes, restore RichLog body."""
    def __init__(self, editor_id: str) -> None:
        super().__init__()
        self.editor_id = editor_id


class ToggleEditCommitted(Message):
    """Toggle option picked (Tab cycle or 1/2 direct). Auto-saves.

    `via` is "tab" if the user pressed Tab (advance to next row of
    collection sections), "pick" otherwise.
    """
    def __init__(self, editor_id: str, value: str, via: str = "pick") -> None:
        super().__init__()
        self.editor_id = editor_id
        self.value = value
        self.via = via


class ToggleEditDone(Message):
    """User pressed Esc on toggle — close editor (already saved each step)."""
    def __init__(self, editor_id: str) -> None:
        super().__init__()
        self.editor_id = editor_id


# --------------------------------------------------------------- text editor
class InlineTextEditor(Vertical):
    """Single text field with helper line above and preset chips below.

    Mounted inside a SectionCard, replacing the RichLog during edit. The
    Input gets focus on mount. The screen receives TextEditCommitted /
    TextEditReverted messages and decides what to do.
    """

    def __init__(
        self,
        editor_id: str,
        initial: str = "",
        presets: list[str] | None = None,
        field_label: str = "model",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.add_class("inline-editor")
        self.editor_id = editor_id
        self._initial = initial
        self._presets = list(presets or [])
        self._field_label = field_label
        self._error: str | None = None
        self.id = f"editor-{slug(editor_id)}"
        # Bindings fire when this widget or its children has focus.
        # Input's default Tab focus-cycling is over-ridden by our on_key.
        self.BINDINGS = [
            Binding("escape", "revert", "Cancel"),
        ]

    def compose(self) -> ComposeResult:
        # Helper line — shows validation errors or the normal hint.
        yield Static(
            self._render_help(),
            markup=False,
            classes="editor-help",
            id=f"help-{slug(self.editor_id)}",
        )
        # The actual input field.
        yield Input(
            value=self._initial,
            placeholder=self._field_label,
            id=f"input-{slug(self.editor_id)}",
            classes="editor-input",
        )
        # Preset chips below.
        if self._presets:
            yield Static(
                "\x1b[38;2;110;120;135m  ⎯ " + "   ".join(self._presets) + "\x1b[0m",
                markup=False,
                classes="editor-presets",
            )

    def on_mount(self) -> None:
        try:
            self.query_one(Input).focus()
        except Exception:
            pass

    # ----- Input.Submitted fires on Enter -----
    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = (event.value or "").strip()
        err = _validate_model(value)
        if err:
            self._set_error(err)
            return
        self._clear_error()
        self.post_message(TextEditCommitted(self.editor_id, value))

    # ----- Intercept Tab + Esc at the editor level so Input's defaults
    #       do not consume them. We on_key (not Bindings) here so we can
    #       stop propagation and prevent the screen's `escape` binding
    #       (which would otherwise pop this screen).
    def on_key(self, event) -> None:
        if event.key == "tab":
            value = self._read_input()
            err = _validate_model(value)
            if err:
                self._set_error(err)
                event.prevent_default()
                event.stop()
                return
            self._clear_error()
            self.post_message(TextEditCommitted(self.editor_id, value, via="tab"))
            event.prevent_default()
            event.stop()
            return
        if event.key == "shift+tab":
            value = self._read_input()
            err = _validate_model(value)
            if err:
                self._set_error(err)
                event.prevent_default()
                event.stop()
                return
            self._clear_error()
            self.post_message(TextEditCommitted(self.editor_id, value, via="tab"))
            event.prevent_default()
            event.stop()
            return
        if event.key == "escape":
            self.post_message(TextEditReverted(self.editor_id))
            event.prevent_default()
            event.stop()
            return

    # ----- Esc binding action -----
    def action_revert(self) -> None:
        self.post_message(TextEditReverted(self.editor_id))

    # ----- helpers -----
    def _read_input(self) -> str:
        try:
            return (self.query_one(Input).value or "").strip()
        except Exception:
            return ""

    def _set_error(self, msg: str) -> None:
        self._error = msg
        self.add_class("err")
        try:
            s = self.query_one(f"#help-{slug(self.editor_id)}", Static)
            s.update(self._render_help())
        except Exception:
            pass

    def _clear_error(self) -> None:
        self._error = None
        self.remove_class("err")
        try:
            s = self.query_one(f"#help-{slug(self.editor_id)}", Static)
            s.update(self._render_help())
        except Exception:
            pass

    def _render_help(self) -> str:
        if self._error:
            return (
                "\x1b[1;38;2;225;145;140m● invalid: " + self._error + "\x1b[0m"
                "   "
                "\x1b[38;2;160;165;175mpress Tab or Enter to re-validate · "
                "Esc to cancel\x1b[0m"
            )
        return (
            "\x1b[38;2;110;120;135m  "
            "⏎ save · Esc cancel · Tab save & advance\x1b[0m"
        )


# --------------------------------------------------------------- toggle editor
class InlineToggleEditor(Vertical):
    """Two-option toggle group with Tab cycle + 1/2 direct pick.

    Used for `defaults_depth` (STANDARD/DEEP) and `defaults_compressed`
    (true/false). Auto-saves on every option change.
    """

    def __init__(
        self,
        editor_id: str,
        current: str,
        options: tuple[str, ...],
    ) -> None:
        super().__init__()
        self.add_class("inline-toggle-editor")
        self.editor_id = editor_id
        self._options = tuple(options)
        if current in self._options:
            self._index = self._options.index(current)
        else:
            self._index = 0
        self.id = f"toggle-{slug(editor_id)}"
        self.BINDINGS = [
            Binding("escape", "done", "Done"),
        ]

    def compose(self) -> ComposeResult:
        yield Static(
            "\x1b[38;2;110;120;135m  Tab cycle · 1 / 2 pick · "
            "auto-saves · Esc done\x1b[0m",
            markup=False,
            classes="toggle-help",
            id=f"toggle-help-{slug(self.editor_id)}",
        )
        yield Static(
            "",
            markup=False,
            classes="toggle-display",
            id=f"toggle-display-{slug(self.editor_id)}",
        )

    def on_mount(self) -> None:
        self._refresh()
        # Toggle group has no focusable children by default; making the
        # outer container focusable lets Tab + 1/2 land here.
        self.can_focus = True
        self.focus()

    def on_key(self, event) -> None:
        if event.key == "tab":
            self._cycle(+1, via="tab")
            event.prevent_default()
            event.stop()
            return
        if event.key == "shift+tab":
            self._cycle(-1, via="tab")
            event.prevent_default()
            event.stop()
            return
        if event.key == "1":
            self._pick(0)
            event.prevent_default()
            event.stop()
            return
        if event.key == "2":
            self._pick(1)
            event.prevent_default()
            event.stop()
            return
        if event.key == "escape":
            # Already auto-saved; just notify the screen to close.
            self.post_message(ToggleEditDone(self.editor_id))
            event.prevent_default()
            event.stop()
            return

    def action_done(self) -> None:
        # We have already saved on every cycle; just ask the screen to close.
        self.post_message(ToggleEditDone(self.editor_id))

    def _cycle(self, delta: int, via: str = "cycle") -> None:
        if len(self._options) <= 1:
            return
        self._index = (self._index + delta) % len(self._options)
        self._refresh()
        self.post_message(ToggleEditCommitted(self.editor_id, self._options[self._index], via=via))

    def _pick(self, idx: int) -> None:
        if idx >= len(self._options):
            return
        if self._index == idx:
            return  # no change -> don't fire
        self._index = idx
        self._refresh()
        self.post_message(ToggleEditCommitted(self.editor_id, self._options[self._index]))

    def _refresh(self) -> None:
        try:
            d = self.query_one(f"#toggle-display-{slug(self.editor_id)}", Static)
        except Exception:
            return
        parts = []
        for i, opt in enumerate(self._options):
            if i == self._index:
                parts.append(
                    "\x1b[1;38;2;140;220;220m│\x1b[0m"
                    "\x1b[48;2;26;32;38m\x1b[38;2;212;212;212m " + opt + " \x1b[0m\x1b[0m"
                )
            else:
                parts.append("\x1b[38;2;110;120;135m  " + opt + "  \x1b[0m")
        d.update("  " + "  ".join(parts))
