"""
citation.py — the Citation modal screen.

Same one-screen shape as Settings / History. The screen renders the full
list of citations for one agent's envelope. The user can:

   - press Enter on the selected row to open the URL in the default browser
   - press `y` to copy the URL to the clipboard
   - press 1–9 to jump-and-open the Nth citation immediately
   - press ↑/↓ to move selection
   - press Esc to pop back to the chat

Header strip shows:
   brand · Citations / <agent_id> · per-source-type badge counts ·
   thesis_id · version · timestamp

Footer shows context-aware keys (open / copy / navigate) based on whether
the list has 1 or N rows.

ANSI rendering uses RichLog like Settings / History did; we cached the
row strings because render time per selection change is dominated by the
write loop, not the formatting.

The modal does not own state — it only receives evidence URLs at
construction time. Anything more (snippets, content snippets) is a
later additive extension.
"""

from __future__ import annotations

import webbrowser  # noqa: F401  (re-exported for tests patching the module attr)

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import RichLog, Static

from frontend.utils import platform as _plat
# Re-bind for readability; the screen calls _plat.<fn> so tests can
# monkey-patch _plat.open_in_browser and have it stick.
copy_to_clipboard = _plat.copy_to_clipboard
open_in_browser    = _plat.open_in_browser
source_type_from_url = _plat.source_type_from_url


# ---------------------------------------------------------------------------
# Color tokens (matching style.tcss palette already used by ChatScreen).
# ---------------------------------------------------------------------------
_BRAND = "1;38;2;140;220;220"
_FG    = "38;2;212;212;212"
_FG2   = "38;2;160;165;175"
_FG3   = "38;2;110;120;135"
_OK    = "38;2;140;210;150"
_WARN  = "38;2;230;200;130"
_ERR   = "38;2;225;145;140"

# Per-source-type accent colors (same hues as the preview-citation.html).
_TYPE_COLOR = {
    "filing": "38;2;136;180;212",   # pastel blue
    "news":   "38;2;201;165;120",   # pastel amber
    "macro":  "38;2;180;212;136",   # pastel sage
    "web":    "38;2;176;161;201",   # pastel lavender
}
_TYPE_LABEL = {
    "filing": "SecFilings",
    "news":   "News",
    "macro":  "Macro",
    "web":    "Web",
}

# Items per row column widths. Tuned for 110-col terminals; flexible below.
_COL_IDX = 4
_COL_SRC = 14
_COL_URL = 70
_COL_ACT = 14

# Whitelisted number keys 1-9 for jump-and-open.
_JUMP_KEYS = {"1", "2", "3", "4", "5", "6", "7", "8", "9"}


def _ansi(strip: bool = False) -> str:
    """Reset escape sequence."""
    return "\x1b[0m" if strip else "\x1b[0m"


def _render_caption() -> str:
    """The fixed column-header bar above the citation rows."""
    parts = [
        f"\x1b[{_FG3}m{'':<{_COL_IDX}}\x1b[0m",
        f"\x1b[{_FG3}m{'source':<{_COL_SRC}}\x1b[0m",
        f"\x1b[{_FG3}m{'url'}\x1b[0m",
        f"\x1b[{_FG3}m    {'action':>{_COL_ACT}}\x1b[0m",
    ]
    return "".join(parts)


def _render_citation_row(
    idx: int,
    url: str,
    *,
    selected: bool,
    opened: bool = False,
) -> str:
    """Build the ANSI line for one citation row."""
    bullet = "▌" if selected else " "
    if selected:
        # Wrap the row in a subtle inverted bg + leading brand-cyan strip.
        leading = f"\x1b[{_BRAND}m{bullet}\x1b[0m"
        bg = "\x1b[48;2;18;24;30m"
        end_bg = "\x1b[0m"
    else:
        leading = f"\x1b[{_FG3}m{bullet}\x1b[0m"
        bg = ""
        end_bg = ""
    src_type = source_type_from_url(url)
    src_color = _TYPE_COLOR.get(src_type, _FG3)
    src_label = _TYPE_LABEL.get(src_type, "Web")

    idx_str = f"{idx + 1}."
    idx_rendered = f"\x1b[{_BRAND}m{idx_str:<{_COL_IDX}}\x1b[0m" if selected \
                   else f"\x1b[{_FG3}m{idx_str:<{_COL_IDX}}\x1b[0m"

    # Source pill (color-coded).
    pill_fg = src_color
    pill_bg = _BRAND  # cyan tint for the cyan-bordered selected row gauge
    src_rendered = (
        f"\x1b[{pill_fg}m{('● ' + src_label):<{_COL_SRC}}\x1b[0m"
    )

    # URL — clamp to width budget; ellipsize if longer.
    url_budget = max(20, _COL_URL)
    raw = url or ""
    if len(raw) > url_budget:
        visible = raw[:url_budget - 1] + "…"
    else:
        visible = raw
    url_rendered = f"\x1b[{_FG if selected else _FG2}m{visible}\x1b[0m"

    # Action glyph — flips between "⌘ ↗ open" and "✓ opened".
    if opened:
        action = f"\x1b[{_OK}m{'✓ opened'}\x1b[0m"
    elif selected:
        action = f"\x1b[{_BRAND}m{'⌘ ↗ open'}\x1b[0m"
    else:
        action = f"\x1b[{_FG3}m{'⌘ ↗ open'}\x1b[0m"
    action_padded = f"{action:>{_COL_ACT + 10}}"

    return f"{bg}{leading}{idx_rendered}{src_rendered} {url_rendered} {action_padded}{end_bg}"


def _render_empty_row() -> str:
    return (
        f"\x1b[{_BRAND}m{'':<{_COL_IDX}}\x1b[0m"
        f"\x1b[{_WARN}m  ● no citations recorded\x1b[0m"
    )


def _render_blank() -> str:
    return ""


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------
class CitationModalScreen(Screen):
    """Full-screen modal listing citations for one agent.

    Constructor:
        agent_id   : e.g. ``final-report``
        citations  : list[str] of evidence URLs
        thesis_id  : int | None
        version    : str  | None
        timestamp  : str  | None
    """

    BINDINGS = [
        Binding("escape", "back_chat",  "Back"),
        Binding("enter",  "open_selected", "Open"),
        Binding("y",      "yank_url",   "Copy URL"),
        Binding("up",     "row_up",     "Prev"),
        Binding("down",   "row_down",   "Next"),
    ]

    def __init__(
        self,
        *,
        agent_id: str = "",
        citations: list[str] | None = None,
        thesis_id: int | None = None,
        version: str | None = None,
        timestamp: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._agent_id: str = agent_id or ""
        self._citations: list[str] = list(citations or [])
        self._thesis_id = thesis_id
        self._version = version
        self._timestamp = timestamp
        self._selected: int = 0 if self._citations else -1
        self._opened_idx: int = -1   # last-opened row index, for "✓ opened" flash
        self._opened_until: float = 0.0
        # Per-source-type counts (computed once).
        self._type_counts: dict[str, int] = {
            "filing": 0, "news": 0, "macro": 0, "web": 0,
        }
        for u in self._citations:
            self._type_counts[source_type_from_url(u)] += 1
        # Body RichLog id (slug-safe).
        self.id = f"citation-{slugify(agent_id)}"

    # ------------------------------------------------------------------ compose
    def compose(self) -> ComposeResult:
        yield Static("", markup=False, classes="modal-head", id="citation-head")
        with Horizontal(id="citation-body-row"):
            with Vertical(id="citation-body", classes="modal-body"):
                yield RichLog(
                    wrap=False, highlight=False, markup=False,
                    classes="modal-body-log", id="citation-body-log",
                )
        # Transient toast under the body.
        yield Static("", markup=False, classes="citation-toast", id="citation-toast")
        # Universal StatusStrip replaces the per-screen foot Static.
        from frontend.widgets.status_strip import StatusStrip   # type: ignore
        yield StatusStrip()

    def on_mount(self) -> None:
        self._refresh_head()
        self._refresh_body()
        self._refresh_foot()
        from frontend.widgets.status_strip import StatusStrip as _SS
        try:
            self.query_one(_SS).update_for(self)
        except Exception:
            pass

    # ------------------------------------------------------------------ head / body / foot
    def _refresh_head(self) -> None:
        n = len(self._citations)
        crumb = f"— Citations / {self._agent_id or '(unknown)'}"
        # Type-count badges.
        badges = []
        if n:
            for stype in ("filing", "news", "macro", "web"):
                cnt = self._type_counts.get(stype, 0)
                if cnt:
                    color = _TYPE_COLOR[stype]
                    labels_short = {"filing": "filings", "news": "news",
                                    "macro": "macro", "web": "web"}
                    badges.append(
                        f"\x1b[{color}m{stype} \u00b7 {cnt}\x1b[0m"
                    )
        badges_s = "    ".join(badges) if badges else ""
        # Meta line.
        meta_bits = []
        if self._thesis_id is not None:
            meta_bits.append(f"\x1b[{_FG3}mthesis_id {self._thesis_id}\x1b[0m")
        if self._version:
            meta_bits.append(f"\x1b[{_FG3}m{self._version}\x1b[0m")
        if self._timestamp:
            meta_bits.append(f"\x1b[{_FG3}m{self._timestamp}\x1b[0m")
        meta_s = "    ".join(meta_bits) if meta_bits else ""

        head = (
            f"\x1b[{_BRAND}m  Labourious\x1b[0m"
            f"\x1b[{_FG2}m  \u2014 Citations / {self._agent_id or '(unknown)'}\x1b[0m"
            + (" " * max(1, 30 - len(self._agent_id)))
            + badges_s
            + "          "
            + meta_s
        )
        try:
            h = self.query_one("#citation-head", Static)
            h.update(head)
        except Exception:
            pass

    def _refresh_body(self) -> None:
        try:
            body = self.query_one("#citation-body-log", RichLog)
        except Exception:
            return
        body.clear()
        if not self._citations:
            body.write(_render_empty_row())
            body.write(_render_blank())
            body.write(
                f"\x1b[{_FG3}m  This agent envelope did not include an evidence list "
                f"\u2014 violation of\x1b[0m"
            )
            body.write(
                f"\x1b[{_FG3}m  \x1b[{_BRAND}mcitations-required\x1b[0m"
                f"\x1b[{_FG3}m discipline (\x1b[0m"
                f"\x1b[{_FG2}meval/test_hallucination.py \u00b7 test_citation_required_for_every_claim\x1b[0m"
                f"\x1b[{_FG3}m).\x1b[0m"
            )
            return
        body.write(_render_caption())
        body.write(_render_blank())
        for i, url in enumerate(self._citations):
            body.write(_render_citation_row(
                i, url,
                selected=(i == self._selected),
                opened=(i == self._opened_idx),
            ))

    def _refresh_foot(self) -> None:
        n = len(self._citations)
        if n == 0:
            foot = f"\x1b[{_FG3}m  \x1b[{_BRAND}mEsc\x1b[0m\x1b[{_FG3}m back to chat\x1b[0m"
        elif n == 1:
            foot = (
                f"\x1b[{_FG3}m  \x1b[{_BRAND}m1\x1b[0m\x1b[{_FG3}m open in browser \u00b7 "
                f"\x1b[{_BRAND}my\x1b[0m\x1b[{_FG3}m copy URL \u00b7 "
                f"\x1b[{_BRAND}mEsc\x1b[0m\x1b[{_FG3}m back\x1b[0m"
            )
        else:
            jumpkeys = " \u00b7 ".join(
                f"\x1b[{_BRAND}m{i+1}\x1b[0m" if i < 9 else
                f"\x1b[{_FG3}m{i+1}\x1b[0m"
                for i in range(min(n, 9))
            )
            foot = (
                f"\x1b[{_FG3}m  \x1b[{_BRAND}m\u2191/\u2193\x1b[0m\x1b[{_FG3}m navigate \u00b7 "
                f"\x1b[{_BRAND}m\u23ce\x1b[0m\x1b[{_FG3}m open in browser \u00b7 "
                f"\x1b[{_BRAND}my\x1b[0m\x1b[{_FG3}m copy URL \u00b7 {jumpkeys} \u00b7 "
                f"\x1b[{_BRAND}mEsc\x1b[0m\x1b[{_FG3}m back\x1b[0m"
            )
        try:
            f = self.query_one("#citation-foot", Static)
            f.update(foot)
        except Exception:
            pass

    # ------------------------------------------------------------------ actions
    def action_back_chat(self) -> None:
        self.app.pop_screen()

    def action_row_up(self) -> None:
        if not self._citations:
            return
        self._selected = max(0, self._selected - 1)
        self._refresh_body()

    def action_row_down(self) -> None:
        if not self._citations:
            return
        self._selected = min(len(self._citations) - 1, self._selected + 1)
        self._refresh_body()

    def action_open_selected(self) -> None:
        if not self._citations:
            return
        self._open_index(self._selected)

    def action_yank_url(self) -> None:
        if not self._citations:
            self._toast("nothing to copy", warn=True)
            return
        url = self._citations[self._selected]
        ok, msg = copy_to_clipboard(url)
        if ok:
            self._toast(f"\u2713 copied: {short_url(url)}", ok=True)
        else:
            self._toast(f"copy failed: {msg}", warn=True)

    # ------------------------------------------------------------------ on_key
    def on_key(self, event) -> None:
        # Arrow keys navigate the citation rows. We handle them here
        # because the body's RichLog may capture arrows for its own
        # scroll behaviour, and we want selection (not scroll) on Up/Down.
        if event.key == "up":
            self.action_row_up()
            event.prevent_default()
            event.stop()
            return
        if event.key == "down":
            self.action_row_down()
            event.prevent_default()
            event.stop()
            return
        # 1-9 jump-and-open on top of selection change.
        if event.character and event.character in _JUMP_KEYS:
            idx = int(event.character) - 1
            if 0 <= idx < len(self._citations):
                self._selected = idx
                self._refresh_body()
                self._open_index(idx)
                event.prevent_default()
                event.stop()
                return

    # ------------------------------------------------------------------ helpers
    def _open_index(self, idx: int) -> None:
        if not (0 <= idx < len(self._citations)):
            return
        url = self._citations[idx]
        try:
            ok, msg = open_in_browser(url)
        except Exception as e:
            ok, msg = False, f"{type(e).__name__}: {e}"
        if ok:
            self._opened_idx = idx
            self._refresh_body()
            self._toast(f"\u2713 opened in default browser \u00b7 {short_url(url)}", ok=True)
        else:
            self._toast(f"browser refused: {msg}", warn=True)

    def _toast(self, msg: str, *, ok: bool = False, warn: bool = False) -> None:
        try:
            t = self.query_one("#citation-toast", Static)
        except Exception:
            return
        if ok:
            ansi = f"\x1b[{_OK}m\u25cf {msg}\x1b[0m"
        elif warn:
            ansi = f"\x1b[{_WARN}m\u25cf {msg}\x1b[0m"
        else:
            ansi = f"\x1b[{_FG3}m\u25cf {msg}\x1b[0m"
        try:
            t.update(ansi)
        except Exception:
            pass


# --------------------------------------------------------------------------- helpers
def slugify(s: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9_-]", "-", s or "x")


def short_url(url: str, n: int = 56) -> str:
    if len(url) <= n:
        return url
    return url[:n - 1] + "…"
