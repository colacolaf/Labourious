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
    List    — scrollable rows of (name, description) with a cyan
              selection bar + tint on the focused row.
"""

from __future__ import annotations

from dataclasses import dataclass

from textual.widgets import RichLog, Static
from textual.containers import Vertical


@dataclass(frozen=True)
class PickerItem:
    key: str           # canonical key the runtime stores (e.g. "groq")
    label: str         # display name (e.g. "groq")
    description: str   # short blurb (e.g. "Groq Cloud (free tier, very fast)")


class PickerOverlay(Vertical):
    """Renders a single column with search + filtered list of PickerItem.

    Search is live: any key the user types against the body filters
    items by `label` substring (case-insensitive). Empty filter shows
    all items. Up/Down navigates. Enter selects and emits a posted
    message (PickerOverlay.Selected) the SettingsScreen listens to.
    """

    class Selected(Static.__mro__[0].__bases__[0]):  # type: ignore[misc]
        """Posted when the user picks an item. Carries PickerItem.key.

        Implemented as a plain class so we don't import textual.message
        (some versions differ in import path); SettingsScreen checks
        `isinstance(msg, PickerOverlay.Selected)`.
        """
        def __init__(self, key: str) -> None:
            self.key = key

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
        yield RichLog(wrap=False, highlight=False, markup=False,
                      classes="picker-list", id=f"picker-{slug}")

    def on_mount(self) -> None:
        # First paint of the list
        self._refilter()

    # --------------------------------------------------------------- rendering
    def _render_breadcrumb(self) -> str:
        return (
            "\x1b[38;2;110;120;135m"
            f"Settings / {self._breadcrumb}\x1b[0m"
        )

    def _render_search(self) -> str:
        cursor = "\x1b[1;38;2;140;220;220m▌\x1b[0m" if self._filter or True else ""
        return (
            "\x1b[1;38;2;140;220;220m/\x1b[0m"
            f"\x1b[38;2;212;212;212m{self._filter}\x1b[0m"
            f"{cursor}"
            "  "
            "\x1b[38;2;110;120;135m"
            f"type to filter  ({(len(self._visible))}/{len(self._items)})\x1b[0m"
        )

    def _render_list_row(self, item: PickerItem, selected: bool) -> str:
        marker = "│" if selected else " "
        bar_color = "1;38;2;140;220;220" if selected else "38;2;110;120;135"
        name_color = "1;38;2;140;220;220" if selected else "38;2;212;212;212"
        desc_color = "38;2;160;165;175" if selected else "38;2;110;120;135"
        return (
            f"\x1b[{bar_color}m  {marker}  \x1b[0m"
            f"\x1b[{name_color}m{item.label}\x1b[0m"
            f"\x1b[{desc_color}m   {item.description}\x1b[0m"
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
        try:
            log = self.query_one(RichLog)
        except Exception:
            return
        log.clear()
        if not self._visible:
            log.write("\x1b[38;2;110;120;135m  (no matches)\x1b[0m")
            return
        for i, it in enumerate(self._visible):
            log.write(self._render_list_row(it, selected=(i == self._index)))

    # --------------------------------------------------------------- input handlers
    def type_char(self, ch: str) -> None:
        if ch and ch.isprintable():
            self._filter += ch
            self._refresh_search_widget()
            self._refilter()

    def backspace(self) -> None:
        self._filter = self._filter[:-1]
        self._refresh_search_widget()
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

    def _refresh_search_widget(self) -> None:
        try:
            s = self.query_one(".picker-search", Static)
            s.update(self._render_search())
        except Exception:
            pass
