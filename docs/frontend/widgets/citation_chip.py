"""
citation_chip.py — the `[N citations]` footer chip on each agent bubble.

The chip is a focusable Static. Pressing Enter — or clicking it with the
mouse — posts a `CitationChip.Pressed` message upward. The chat screen
catches that message and pushes `CitationModalScreen`, which renders the
full URL list and lets the user open in browser / copy / browse each
source.

The chip carries:
    - ``citations``    : list[str] of evidence URLs (the only v1 field)
    - ``agent_id``     : e.g. ``final-report`` — used for the modal title
    - ``thesis_id``    : int row id of the thesis (optional)
    - ``version``      : e.g. ``v3`` (optional)
    - ``timestamp``    : ISO-ish string (optional)

The data lives on the chip itself rather than behind a lookup so that
chat.py doesn't need to remember which bubble the chip is attached to.
Falls back to ``[N citations]`` rendering when chip data has not been
populated yet (e.g. by an old code path).
"""

from __future__ import annotations

from textual.message import Message
from textual.widgets import Static


class CitationChip(Static):
    """Clickable footer chip showing how many citations an agent produced."""

    DEFAULT_CSS = """
    CitationChip { /* tightened in style.tcss */ }
    """

    class Pressed(Message):
        """Posted when the user clicks the chip or presses Enter on it.

        The chat screen listens for this and pushes a
        ``CitationModalScreen`` carrying the chip's citations.
        """
        def __init__(self, chip_id: str) -> None:
            super().__init__()
            self.chip_id = chip_id

    def __init__(
        self,
        count: int = 0,
        *,
        citations: list[str] | None = None,
        agent_id: str = "",
        thesis_id: int | None = None,
        version: str | None = None,
        timestamp: str | None = None,
        **kwargs,
    ) -> None:
        # If we got a citations list, derive count from it; otherwise fall
        # back to the legacy ``count`` arg so old callers still work.
        if citations is not None:
            self.citations: list[str] = list(citations)
            count = len(self.citations)
        else:
            self.citations = []
        self.count = count
        self.agent_id = agent_id
        self.thesis_id = thesis_id
        self.version = version
        self.timestamp = timestamp
        super().__init__(self._label(), markup=True, **kwargs)
        self.add_class("citation-chip")
        if self.count == 0:
            self.add_class("chip-empty")
        self.can_focus = True

    def _label(self) -> str:
        if self.count == 0:
            return "[no citations] ↵"
        word = "citation" if self.count == 1 else "citations"
        return f"[{self.count} {word}] ↵"

    def set_count(self, count: int) -> None:
        self.count = count
        # NB: callers that want to update citations separately should use
        # ``set_citations`` so the URL list and count stay in sync.
        if count == 0:
            self.add_class("chip-empty")
        else:
            self.remove_class("chip-empty")
        self.update(self._label())

    def set_citations(
        self,
        citations: list[str],
        *,
        agent_id: str = "",
        thesis_id: int | None = None,
        version: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        """Replace the chip's data in one call."""
        self.citations = list(citations or [])
        self.count = len(self.citations)
        if agent_id:
            self.agent_id = agent_id
        if thesis_id is not None:
            self.thesis_id = thesis_id
        if version is not None:
            self.version = version
        if timestamp is not None:
            self.timestamp = timestamp
        if self.count == 0:
            self.add_class("chip-empty")
        else:
            self.remove_class("chip-empty")
        self.update(self._label())

    # ----- input handlers ------------------------------------------------
    def on_key(self, event) -> None:
        """Enter on the chip opens the modal."""
        if event.key == "enter":
            self.post_message(self.Pressed(self.id or ""))
            event.prevent_default()
            event.stop()
            return

    def _on_click(self, event) -> None:
        """Mouse click opens the modal."""
        # Note: Textual passes a generic click event; we just post the
        # same message regardless of button. Right-clicks are rare in
        # TUI; if needed, branch on event.button.
        self.post_message(self.Pressed(self.id or ""))
