"""
chat_command_palette.py — inline "/"-command palette for the chat prompt.

When the user types "/" as the first character of the chat input, a popup
mounts directly above the input bar listing every command that still
matches what they've typed. Full keyboard control from inside the Input:

    type          live-filter (case-insensitive substring on cmd + desc)
    ↑ / ↓         move the selection (wraps)
    Tab / →       complete the selected command into the input
    Enter         pick and EXECUTE the command immediately
    Esc           close the popup (input keeps the typed text)

The popup is mounted by the ChatScreen (see on_input_changed there) and
posts CommandPalette.Picked when the user commits. The screen owns
execution — the palette never runs commands itself.

Rows are real Static widgets (hover + click work natively, same pattern
as PickerOverlay in the settings screen): click once to select, click the
selected row again to execute.
"""

from __future__ import annotations

from dataclasses import dataclass

from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Static

from frontend.utils.ansi import to_text


@dataclass(frozen=True)
class CommandItem:
    """One row in the palette. `name` excludes the leading slash."""

    name: str
    args: str          # argument hint, e.g. "STANDARD|DEEP"
    description: str


# The catalog mirrors frontend/keys.py COMMAND_PALETTE_PREFIX docs — one
# entry per branch in ChatScreen._handle_command.
COMMANDS: tuple[CommandItem, ...] = (
    CommandItem("model", "<provider/model>", "switch the default model"),
    CommandItem("depth", "SCAN|STANDARD|DEEP", "analysis depth for the next run"),
    CommandItem("paid-for", "<agents>", "toggle per-agent paid (hybrid) routing"),
    CommandItem("ticker", "<TICKER>", "set the ticker for the next run"),
    CommandItem("flow", "f1-f8", "choose which flow to run"),
    CommandItem("stream", "on|off|<ms>", "streaming chunks + typewriter delay"),
    CommandItem("compressed", "", "toggle compressed mode"),
    CommandItem("settings", "", "open Settings"),
    CommandItem("history", "", "open History"),
    CommandItem("help", "", "show the welcome card"),
    CommandItem("clear", "", "clear the chat (alias: Ctrl+L)"),
    CommandItem("quit", "", "quit (alias: Ctrl+Q)"),
)


class CommandPalette(Vertical):
    """The popup list. Mounted by ChatScreen above the prompt input."""

    DEFAULT_CSS = """
    CommandPalette {
        layer: overlay;
        dock: bottom;
        width: 100%;
        max-height: 10;
        background: #0e1014;
        border: round #465262;
        padding: 0 0 1 0;
        margin: 0 0 0 0;
    }
    """

    class Picked(Message):
        """User committed a command (Enter on a row / second click).
        Carries the full command text INCLUDING the leading slash."""

        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command

    class Dismissed(Message):
        """User pressed Esc — the screen should unmount the palette."""

        def __init__(self) -> None:
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._filter: str = ""
        self._visible: list[CommandItem] = list(COMMANDS)
        self._index: int = 0

    # ------------------------------------------------------------- compose
    def compose(self):
        yield Static("", markup=False, classes="cmdpal-hint")
        with Vertical(classes="cmdpal-list", id="cmdpal-rows"):
            pass
        self._refilter()

    def on_mount(self) -> None:
        self._refilter()

    # ------------------------------------------------------------- filtering
    def set_filter(self, text: str) -> None:
        """Filter to commands matching the typed fragment (after the '/')."""
        q = (text or "").strip().lower()
        if q == self._filter:
            return
        self._filter = q
        self._refilter()

    def _refilter(self) -> None:
        if self._filter:
            self._visible = [
                c for c in COMMANDS
                if self._filter in c.name
                or self._filter in c.description.lower()
                or self._filter in c.args.lower()
            ]
        else:
            self._visible = list(COMMANDS)
        if self._index >= len(self._visible):
            self._index = 0
        self._repaint()

    # ------------------------------------------------------------- rendering
    def _render_hint(self) -> str:
        if not self._visible:
            return (
                "\x1b[38;2;110;120;135m  no matching command — "
                "Esc to close\x1b[0m"
            )
        sel = self._visible[self._index]
        hint = f"{sel.args} — {sel.description}" if sel.args else sel.description
        return (
            "\x1b[38;2;110;120;135m  ↑/↓ pick · "
            "\x1b[1;38;2;140;220;220mtab\x1b[0m"
            "\x1b[38;2;110;120;135m complete · "
            "\x1b[1;38;2;140;220;220m⏎\x1b[0m"
            "\x1b[38;2;110;120;135m run · Esc close\x1b[0m"
            f"    \x1b[38;2;80;88;100m{hint}\x1b[0m"
        )

    def _repaint(self) -> None:
        try:
            hint = self.query_one(".cmdpal-hint", Static)
            # to_text: the hint embeds ANSI SGR codes — a raw str would
            # paint them as literal [38;2;…m garbage in Textual 8.
            hint.update(to_text(self._render_hint()))
        except Exception:
            pass
        try:
            rows = self.query_one("#cmdpal-rows", Vertical)
        except Exception:
            return
        rows.remove_children()
        if not self._visible:
            rows.mount(Static(
                to_text("\x1b[38;2;110;120;135m  (no matching command)\x1b[0m"),
                markup=False, classes="cmdpal-row-empty"))
            return
        for i, cmd in enumerate(self._visible):
            selected = (i == self._index)
            marker = "▌" if selected else " "
            arg = f" \x1b[38;2;80;88;100m{cmd.args}\x1b[0m" if cmd.args else ""
            text = (
                f" {marker} \x1b[1;38;2;140;220;220m/{cmd.name}\x1b[0m"
                f"{arg}"
                f"  \x1b[38;2;110;120;135m{cmd.description}\x1b[0m"
            )
            row = Static(to_text(text), markup=False,
                         classes="cmdpal-row" + (" sel" if selected else ""))
            row._cmdpal_idx = i
            rows.mount(row)

    # ------------------------------------------------------------- keyboard
    def move_selection(self, delta: int) -> None:
        if not self._visible:
            return
        self._index = (self._index + delta) % len(self._visible)
        self._repaint()

    def completion_text(self) -> str | None:
        """The full command text (with slash) for the current selection."""
        if not self._visible:
            return None
        sel = self._visible[self._index]
        return f"/{sel.name} " if sel.args else f"/{sel.name}"

    def complete(self) -> None:
        """Tab: put the selected command into the input (no execution)."""
        text = self.completion_text()
        if text is not None:
            self.post_message(self.Complete(text))

    class Complete(Message):
        """Tab-completion: fill the input but don't run."""

        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def commit(self) -> None:
        """Enter: execute the selected command now."""
        if not self._visible:
            return
        sel = self._visible[self._index]
        self.post_message(self.Picked(f"/{sel.name}"))

    # ------------------------------------------------------------- mouse
    def on_click(self, event) -> None:  # noqa: N802 — Textual handler name
        target = event.widget
        while target is not None and target is not self:
            idx = getattr(target, "_cmdpal_idx", None)
            if idx is not None:
                event.stop()
                if 0 <= idx < len(self._visible):
                    if idx == self._index:
                        self.post_message(
                            self.Picked(f"/{self._visible[idx].name}"))
                    else:
                        self._index = idx
                        self._repaint()
                return
            target = target.parent
