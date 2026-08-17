"""
citation_chip.py — the `[N citations]` footer chip on each agent bubble.

For v1 the chip is read-only (clicking it just lists in a static scroll back).
The full CitationModalScreen with URL+snippet preview is P2 — the chip is wired
into the bubble lifecycle now so P2 is purely additive.
"""

from __future__ import annotations

from textual.widgets import Static


class CitationChip(Static):
    """Clickable footer chip showing how many citations an agent produced."""

    def __init__(self, count: int = 0, **kwargs) -> None:
        self.count = count
        super().__init__(self._label(), markup=True, **kwargs)
        self.add_class("citation-chip")
        if count == 0:
            self.add_class("chip-empty")
        self.can_focus = True

    def _label(self) -> str:
        if self.count == 0:
            return "[no citations]"
        word = "citation" if self.count == 1 else "citations"
        return f"[{self.count} {word}] ↵"

    def set_count(self, count: int) -> None:
        self.count = count
        if count == 0:
            self.add_class("chip-empty")
        else:
            self.remove_class("chip-empty")
        self.update(self._label())
