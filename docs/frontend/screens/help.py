"""
help.py — full-screen Help modal.

Renders every binding in `keys.BINDING_CATALOG`, grouped by screen. Designed
to be opened from anywhere via `?` and dismissed via `Esc` (or `?` again — see
App.action_open_help for the toggle logic).

Layout (matches Settings modal head/body/foot contract):
   head   — brand · "help" crumb · status "? open"
   intro  — one-line toggle hint
   body   — 2-column grid of cards (one per catalog group)
   foot   — Esc, ?, source-of-truth signature

Read-only. No state mutation. Pushed on top of any screen.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from frontend.config_io import cfg_path_str, mtime_str, load_config

# Catalog brought in from the single source of truth.
from frontend.keys import BINDING_CATALOG

# Tokens mirrored from style.tcss so we can write ANSI inline where needed.
_FG_DIM = "\x1b[38;2;110;120;135m"
_FG     = "\x1b[38;2;212;212;212m"
_BRAND  = "\x1b[38;2;140;220;220m"


class HelpCard(Static):
    """One card in the help grid: header + rows of (key · label · hint)."""

    DEFAULT_CSS = """
    HelpCard {
        layout: vertical;
        height: auto;
        background: #161a20;
        border: solid #465262;
        margin: 0 0 1 0;
        padding: 0;
    }
    HelpCard > .help-card-head {
        height: 1;
        background: #11141a;
        color: #8cdcdc;
        text-style: bold;
        padding: 0 1;
    }
    HelpCard > .help-card-rows {
        layout: vertical;
        height: auto;
        padding: 0 1 1 1;
    }
    HelpCard > .help-card-rows > .help-row {
        layout: horizontal;
        height: 1;
        margin: 0;
        padding: 0;
    }
    HelpCard > .help-card-rows > .help-row > .k {
        width: 14;
        color: #8cdcdc;
        text-style: bold;
    }
    HelpCard > .help-card-rows > .help-row > .v {
        width: 1fr;
        color: #d4d4d4;
    }
    HelpCard > .help-card-rows > .help-row > .hint {
        color: #6e7887;
    }
    """

    def __init__(self, group: dict, *, id: str | None = None) -> None:
        super().__init__(markup=False, id=id, classes="help-card")
        self._group: dict = group

    def compose(self) -> ComposeResult:
        head = f"  {self._group['group'].upper():<14}{self._group['note']}"
        yield Static(head, classes="help-card-head")
        with Vertical(classes="help-card-rows"):
            for entry in self._group["entries"]:
                # key + label + optional hint, all on one line
                if entry["hint"]:
                    text = f"\x1b[38;2;140;220;220m{entry['key']:<10}\x1b[0m \x1b[38;2;212;212;212m{entry['label']}\x1b[0m \x1b[38;2;110;120;135m— {entry['hint']}\x1b[0m"
                else:
                    text = f"\x1b[38;2;140;220;220m{entry['key']:<10}\x1b[0m \x1b[38;2;212;212;212m{entry['label']}\x1b[0m"
                yield Static(text, classes="help-row")


class HelpModalScreen(Screen):
    """
    The Help modal. Push on top of any screen via self.app.push_screen(...).
    Closes on Esc (`back_chat`) and on ? (`toggle_help`).
    """

    BINDINGS = [
        Binding("escape",      "back_chat", "Back"),
        Binding("question_mark", "toggle_help", "Toggle"),
    ]

    DEFAULT_CSS = """
    HelpModalScreen {
        background: #0e1014;
        align: center top;
    }
    HelpModalScreen > .help-modal-head {
        height: 1;
        width: 100%;
        background: #11141a;
        color: #d4d4d4;
        padding: 0 1;
        border-bottom: solid #465262;
    }
    HelpModalScreen > .help-modal-head > .brand-dot {
        width: 1;
        color: #8cdcdc;
        text-style: bold;
    }
    HelpModalScreen > .help-modal-intro {
        height: 1;
        width: 100%;
        background: #161a20;
        color: #a0a5af;
        padding: 0 1;
    }
    HelpModalScreen > .help-modal-body {
        width: 100%;
        height: 1fr;
        background: #0e1014;
        padding: 1 1;
    }
    HelpModalScreen > .help-modal-grid {
        layout: horizontal;
        width: 100%;
        height: auto;
    }
    HelpModalScreen > .help-modal-grid > .col {
        width: 1fr;
        height: auto;
    }
    HelpModalScreen > .help-modal-foot {
        height: 1;
        width: 100%;
        background: #11141a;
        color: #6e7887;
        padding: 0 1;
        border-top: solid #465262;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Cached for the foot signature line
        try:
            cfg = load_config()
            self._path: str = cfg_path_str()
            self._mtime: str = mtime_str()
        except Exception:
            self._path = "~/.labourious/config.json"
            self._mtime = "—"

    def compose(self) -> ComposeResult:
        # HEAD
        yield Static(
            f"  \x1b[38;2;140;220;220m●\x1b[0m  Labourious / help        "
            f"\x1b[38;2;110;120;135m·\x1b[0m  "
            f"\x1b[38;2;140;220;220m?\x1b[0m\x1b[38;2;110;120;135m toggle this modal ·\x1b[0m "
            f"\x1b[38;2;140;220;220mEsc\x1b[0m\x1b[38;2;110;120;135m close\x1b[0m",
            classes="help-modal-head",
        )
        # INTRO
        yield Static(
            "  Keyboard shortcuts — grouped by where they apply.  "
            f"\x1b[38;2;110;120;135m{len(BINDING_CATALOG)} groups · "
            f"{sum(len(g['entries']) for g in BINDING_CATALOG)} keys\x1b[0m",
            classes="help-modal-intro",
        )
        # BODY (scrollable grid)
        with VerticalScroll(classes="help-modal-body"):
            with Horizontal(classes="help-modal-grid"):
                # Split the catalog into two columns.
                half = (len(BINDING_CATALOG) + 1) // 2
                col_a = list(BINDING_CATALOG[:half])
                col_b = list(BINDING_CATALOG[half:])
                with Vertical(classes="col"):
                    for g in col_a:
                        yield HelpCard(g)
                with Vertical(classes="col"):
                    for g in col_b:
                        yield HelpCard(g)
        # Source-of-truth signature (one thin line, sits above the strip).
        yield Static(
            f"  \x1b[38;2;110;120;135m"
            f"source:\x1b[0m \x1b[38;2;212;212;212mdocs/frontend/keys.py\x1b[0m"
            f"\x1b[38;2;110;120;135m  ·  {self._path}  ·  {self._mtime}\x1b[0m",
            classes="help-modal-sig",
        )
        # Universal StatusStrip at the very bottom — shows help-modal keys.
        from frontend.widgets.status_strip import StatusStrip   # type: ignore
        yield StatusStrip()

    # --------------------------------------------------------------- actions
    def action_back_chat(self) -> None:
        self.app.pop_screen()

    def action_toggle_help(self) -> None:
        """
        Pressing `?` while the help modal is open closes it.
        App.action_open_help already toggles, so this is a fallback in case
        the screen receives the key first.
        """
        self.app.pop_screen()

    # --------------------------------------------------------------- helpers
    def on_mount(self) -> None:
        # Refresh the bottom strip to show help-modal keys (Esc + ?).
        from frontend.widgets.status_strip import StatusStrip as _SS
        try:
            self.query_one(_SS).update_for(self)
        except Exception:
            pass
