"""
picker_overlay.py — an inline picker that swaps in when a user presses
                    '+ add provider' or '+ add connector' inside Settings.

DESIGN: the picker is NOT a separate screen. It is rendered into the
body pane of SettingsScreen when a collection row's '+ add' is pressed.
This honors the project's "one screen, no useless pages" rule — every
state lives on the same SettingsScreen, the body pane just swaps its
contents.

The picker has:
    Header  — breadcrumb ("Settings / providers / add")
    Search  — slash-prefixed typed filter ("/ro" → groq, openrouter)
    List    — rows of (name, description); the selected row gets a
              neutral bar. Rows are real widgets: hover highlight and
              mouse click-to-select work natively (click the selected
              row again to confirm).

Mouse contract:
    click row        → select it
    click again      → confirm (posts PickerOverlay.Selected)
"""

from __future__ import annotations

from dataclasses import dataclass

from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Static


@dataclass(frozen=True)
class PickerItem:
    key: str           # canonical key the runtime stores (e.g. "groq")
    label: str         # display name (e.g. "groq")
    description: str   # short blurb (e.g. "Groq Cloud (free tier, very fast)")


class PickerOverlay(Vertical):
    """Search + filtered list of PickerItem.

    Search is live: any key the user types against the body filters
    items by `label` substring (case-insensitive). Empty filter shows
    all items. Up/Down navigates. Enter (or clicking the selected row)
    selects and posts `PickerOverlay.Selected`, which SettingsScreen
    listens for.
    """

    class Selected(Message):
        """Posted when the user picks an item. Carries PickerItem.key."""

        def __init__(self, key: str) -> None:
            super().__init__()
            self.key = key

    # ANSI tokens — muted palette from frontend/theme.py.
    _FG = "\x1b[38;2;212;212;212m"
    _DIM = "\x1b[38;2;110;120;135m"
    _FAINT = "\x1b[38;2;80;88;100m"
    _BRAND = "\x1b[1;38;2;140;220;220m"
    _RESET = "\x1b[0m"

    def __init__(
        self,
        items: list[PickerItem],
        breadcrumb: str = "add",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.add_class("picker-overlay")
        self._items = items
        self._breadcrumb = breadcrumb
        self._filter = ""
        self._visible: list[PickerItem] = list(items)
        self._index = 0

    # --------------------------------------------------------------- compose
    def compose(self):
        # Slug the breadcrumb so the id has no slashes (Textual validator).
        slug = self._breadcrumb.replace("/", "-")
        yield Static(self._render_breadcrumb(), markup=False, classes="picker-breadcrumb")
        yield Static(self._render_search(),     markup=False, classes="picker-search")
        with Vertical(classes="picker-list", id=f"picker-{slug}"):
            yield Vertical(id="picker-rows")

    def on_mount(self) -> None:
        # First paint of the list
        self._refilter()

    # --------------------------------------------------------------- rendering
    def _render_breadcrumb(self) -> str:
        return (
            f"{self._DIM}"
            f"Settings / {self._breadcrumb}{self._RESET}"
        )

    def _render_search(self) -> str:
        cursor = f"{self._BRAND}▌{self._RESET}"
        return (
            f"{self._BRAND}/{self._RESET}"
            f"{self._FG}{self._filter}{self._RESET}"
            f"{cursor}"
            "  "
            f"{self._DIM}"
            f"type to filter  ({(len(self._visible))}/{len(self._items)}){self._RESET}"
        )

    def _refilter(self) -> None:
        q = self._filter.strip().lower()
        if q:
            self._visible = [
                it for it in self._items
                if q in it.label.lower() or q in it.description.lower()
            ]
        else:
            self._visible = list(self._items)
        self._index = min(self._index, max(0, len(self._visible) - 1))
        self._repaint()

    def _repaint(self) -> None:
        """Rebuild the row widgets. Rows are real Statics so hover and
        mouse clicks work natively instead of being ANSI-painted text.

        Rows carry their index via the `_picker_idx` attribute (NOT via
        widget ids): Textual mounts are async, so re-mounting ided rows
        during a rapid ↑/↓ cycle can race the removal of the previous
        batch and raise DuplicateIds."""
        try:
            rows = self.query_one("#picker-rows", Vertical)
        except Exception:
            return
        rows.remove_children()
        if not self._visible:
            rows.mount(Static(
                f"{self._DIM}  (no matches){self._RESET}",
                markup=False, classes="picker-empty-row"))
            return
        for i, it in enumerate(self._visible):
            selected = (i == self._index)
            marker = "▌" if selected else " "
            text = (
                f" {marker}  {it.label}   "
                f"{self._DIM}{it.description}{self._RESET}"
            )
            row = Static(
                text,
                markup=False,
                classes="picker-row" + (" sel" if selected else ""),
            )
            row._picker_idx = i
            rows.mount(row)
        self._refresh_search_widget()

    # --------------------------------------------------------------- input handlers
    def type_char(self, ch: str) -> None:
        if ch and ch.isprintable():
            self._filter += ch
            self._refilter()

    def backspace(self) -> None:
        self._filter = self._filter[:-1]
        self._refilter()

    def select_next(self) -> None:
        if self._visible:
            self._index = (self._index + 1) % len(self._visible)
            self._repaint()

    def select_prev(self) -> None:
        if self._visible:
            self._index = (self._index - 1) % len(self._visible)
            self._repaint()

    def pick(self):
        """Return the chosen PickerItem, or None."""
        if not self._visible:
            return None
        return self._visible[self._index]

    # --------------------------------------------------------------- mouse
    def on_click(self, event) -> None:  # noqa: N802 — Textual handler name
        """Click a row: select it; clicking the already-selected row
        confirms the pick. Clicks on chrome (breadcrumb/search) are
        ignored."""
        # Walk up from the clicked Static to find a picker row (rows are
        # identified by their _picker_idx attribute, not widget ids).
        target = event.widget
        while target is not None and target is not self:
            idx = getattr(target, "_picker_idx", None)
            if idx is not None:
                event.stop()
                if 0 <= idx < len(self._visible):
                    if idx == self._index:
                        self.post_message(self.Selected(self._visible[idx].key))
                    else:
                        self._index = idx
                        self._repaint()
                return
            target = target.parent

    def _refresh_search_widget(self) -> None:
        try:
            s = self.query_one(".picker-search", Static)
            s.update(self._render_search())
        except Exception:
            pass
