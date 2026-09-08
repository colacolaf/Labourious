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

from frontend.utils.ansi import visible_len


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
        # Optional callback (set by SettingsScreen before mount): invoked from
        # on_mount, i.e. AFTER this card's children (incl. the RichLog body)
        # have composed. Rendering from the screen via call_after_refresh races
        # the async compose; rendering here never does.
        self.on_render = None

    def compose(self):
        # Slug the title so the id has no slashes (Textual validator).
        slug = self._title.lower().replace("/", "-").replace(" ", "-")
        yield Static(self._render_header(), markup=False, classes="section-card-head")
        yield RichLog(wrap=False, highlight=False, markup=False,
                      classes="section-card-body", id=f"body-{slug}")

    def on_mount(self) -> None:
        """Render an empty placeholder message if body has nothing yet."""
        self._ensure_body_attached()
        # Body exists now (compose has run) — render the section content.
        if callable(self.on_render):
            try:
                self.on_render()
            except Exception:
                pass

    def on_resize(self, event) -> None:  # noqa: N802 — Textual handler name
        """Re-render on resize: rows were composed for the old width, and
        RichLog (wrap=False) crops longer-than-widget lines, which showed
        as hints cut mid-sentence after any terminal resize."""
        if callable(self.on_render):
            try:
                self._render_header_now()
                self.on_render()
            except Exception:
                pass

    def _render_header_now(self) -> None:
        try:
            head = self.query_one(".section-card-head", Static)
            head.update(self._render_header())
        except Exception:
            pass

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
        # Width budget: the card's real container width when laid out,
        # else the 110-col design width. visible-width math so any future
        # ANSI in title/meta can't skew the gap.
        try:
            width = self.size.width or 110
        except Exception:
            width = 110
        width = max(40, width - 2)  # card padding
        used = len(self._title.upper()) + len(self._meta) + 2
        gap = " " * max(1, width - used)
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

    def mount_editor(self, editor_widget) -> None:
        """Replace the RichLog body with an inline editor widget.

        Used by SettingsScreen when entering edit mode for a section.
        """
        try:
            body = self.query_one(RichLog)
            body.remove()
        except Exception:
            pass
        self.add_class("editing")
        # Track the editor; do not give it our title slug — the editor
        # assigns its own id.
        self._editor = editor_widget
        self.mount(editor_widget)

    def exit_edit_mode(self):
        """Remove the editor; remount a fresh RichLog body. Returns it."""
        try:
            for w in list(self.children):
                # Remove any editor classes we mounted.
                cls = w.classes or ""
                if "inline-editor" in cls or "inline-toggle-editor" in cls:
                    w.remove()
        except Exception:
            pass
        slug = self._title.lower().replace("/", "-").replace(" ", "-")
        body = RichLog(
            wrap=False, highlight=False, markup=False,
            classes="section-card-body",
            id=f"body-{slug}",
        )
        self.mount(body)
        self.remove_class("editing")
        return body
