"""
ticker_shortcuts.py — the welcome-screen ticker shortcut chips.

A row of small ``Button`` widgets, one per common ticker. On press, the
parent ``ChatScreen`` is asked to populate the prompt input with
``analyze <TICKER>`` and submit (same path as a typed Enter).

The default ticker list is curated: liquid US mega-caps where 80% of
"what does this company actually do" requests land. Users with a real
`watchlist` in config get their own list; otherwise the default.

Why a dedicated widget instead of inline Buttons in the welcome card?
- Easier to mount/unmount as state changes (welcome → running → cleared)
- Easier to test in isolation
- Easier to style via `styles.ticker_chip` CSS class

Public API:
- TickerShortcuts.DEFAULT_TICKERS   the curated fallback
- TickerShortcuts(tickers=...)      the widget itself
- TickerShortcuts.Pressed           message class the parent binds to

Threading: textual widgets run on the app thread; we just emit Pressed.
"""

from __future__ import annotations

from typing import Iterable

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Static


DEFAULT_TICKERS: tuple[str, ...] = (
    # Liquid US mega-caps + a couple of beloved meme/WiFi names.
    "NVDA", "AAPL", "MSFT", "GOOG", "AMZN", "META", "TSLA",
)
"""Curated default list. Override via Config.watchlist or constructor kwarg."""


class TickerShortcuts(Static):
    """A row of clickable ticker chip Buttons.

    Pressing a chip emits ``TickerShortcuts.Pressed(ticker)``.
    The parent ``ChatScreen`` binds that to populate the input + submit.

    Usage in compose()::

        yield TickerShortcuts(id="ticker-shortcuts")
        yield Input(id="prompt", ...)

    The widget is hidden when there's content in the chat-log; see
    ``ChatScreen._sync_shortcuts_visibility``.
    """

    DEFAULT_CSS = ""  # real CSS lives in style.tcss under `TickerShortcuts`

    class Pressed(Message):
        """Bubble upward when the user clicks one of the chips."""

        def __init__(self, ticker: str) -> None:
            super().__init__()
            self.ticker = ticker

    def __init__(
        self,
        tickers: Iterable[str] | None = None,
        *,
        id: str | None = None,  # noqa: A002 — textual id kwarg
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._tickers: tuple[str, ...] = tuple(tickers) if tickers else DEFAULT_TICKERS

    # ------------------------------------------------------------------ compose
    def compose(self) -> ComposeResult:
        # A tiny label "Quick:" sits inline with the chips. Hidden via CSS
        # when the parent decides this widget should be invisible.
        with Horizontal(id="ticker-shortcuts-row", classes="ticker_shortcuts_row"):
            yield Static("Quick: ", classes="ticker_shortcuts_label")
            for t in self._tickers:
                yield Button(t, id=f"chip-{t}", classes="ticker_chip", variant="primary")

    # -------------------------------------------------------------- message bus
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Translate a chip press into our higher-level ``Pressed`` message.

        Why not just let Button.Pressed bubble? Because the parent's
        handler should not depend on button-ids (``chip-NVDA``); the
        parent only cares about the ticker string.
        """
        btn_id = event.button.id or ""
        if not btn_id.startswith("chip-"):
            return
        ticker = btn_id[len("chip-"):]
        if ticker not in self._tickers:
            return
        self.post_message(self.Pressed(ticker))

    # --------------------------------------------------------------- accessors
    @property
    def tickers(self) -> tuple[str, ...]:
        return self._tickers