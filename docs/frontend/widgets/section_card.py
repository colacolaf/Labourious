"""
section_card.py — a card-shaped group of SettingRow widgets.

Header: hairline-bordered top strip with UPPERCASE title + right-aligned meta
        ("PROVIDERS — 2 of 4 configured").
Body:   a RichLog containing SettingRow widgets, one per configured item.

The body uses RichLog rather than Static.update(str) to sidestep the
Textual 3.7 'str has no attribute get_height' layout-versioning bug
when we mutate a Static's renderable in place. We learned this in v1.
"""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import RichLog, Static


class SectionCard(Vertical):
    """A bordered section group. Header strip + body row container."""

    def __init__(
        self,
        title: str,
        meta: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.add_class("section-card")
        self._title = title
        self._meta = meta

    def compose(self):
        # Slug the title so the id has no slashes (Textual validator).
        slug = self._title.lower().replace("/", "-").replace(" ", "-")
        yield Static(self._render_header(), markup=False, classes="section-card-head")
        yield RichLog(wrap=False, highlight=False, markup=False,
                      classes="section-card-body", id=f"body-{slug}")

    def on_mount(self) -> None:
        """Render an empty placeholder message if body has nothing yet."""
        self._ensure_body_attached()

    def _ensure_body_attached(self) -> RichLog:
        try:
            return self.query_one(RichLog)
        except Exception:
            # has not composed yet — defer; mount will run compose first
            return None  # type: ignore

    def _render_header(self) -> str:
        """Header strip — title (left) + meta (right), dim border."""
        title_part = f"\x1b[38;2;160;165;175m{self._title.upper()}\x1b[0m"
        meta_part = (
            f"\x1b[38;2;110;120;135m{self._meta}\x1b[0m" if self._meta else ""
        )
        # Left-aligned title, right-aligned meta with 110-col budget
        gap = " " * max(1, 110 - len(self._title) - len(self._meta) - 4)
        return title_part + gap + meta_part

    def update_meta(self, meta: str) -> None:
        """Update only the right-aligned meta text in the header."""
        self._meta = meta
        try:
            head = self.query_one(".section-card-head", Static)
            head.update(self._render_header())
        except Exception:
            pass  # not yet mounted; will pick up on remount

    def set_title(self, title: str) -> None:
        self._title = title
        try:
            head = self.query_one(".section-card-head", Static)
            head.update(self._render_header())
        except Exception:
            pass

    # --------------------------------------------------------------- body api
    def body(self) -> RichLog | None:
        try:
            return self.query_one(RichLog)
        except Exception:
            return None

    def write_row(self, line: str) -> None:
        b = self.body()
        if b is not None:
            b.write(line)

    def write_blank(self) -> None:
        b = self.body()
        if b is not None:
            b.write("")

    def write_add_row(self, label: str, hint: str) -> None:
        """Write the visual +add row."""
        line = (
            "\x1b[38;2;110;120;135m  +  \x1b[0m"
            f"\x1b[38;2;160;165;175m{label}\x1b[0m"
            f"\x1b[38;2;110;120;135m   {hint}\x1b[0m"
        )
        b = self.body()
        if b is not None:
            b.write(line)
