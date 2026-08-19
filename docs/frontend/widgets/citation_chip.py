"""
citation_chip.py — the `[N citations]` footer chip on each agent bubble.

The chip is a focusable Static. Pressing Enter — or clicking it with the
mouse — posts a `CitationChip.Pressed` message upward. The chat screen
catches that message and pushes `CitationModalScreen`, which renders the
full URL list and lets the user open in browser / copy / browse each
source.

Quick actions (no modal needed for the common case):
    `o`  →  Open the *first* (or currently-selected) URL in OS browser.
    `y`  →  Copy that URL to the system clipboard.
    `v`  →  View cached snippet (`.runs/<run_id>/snippets/<n>.txt`) in
             `less`/`bat`. Populated by the runtime's snippet cache when
             the citation came from `sec_edgar_fulltext`, `news_8k`, or
             `transcripts`. Without a snippet a toast warns the user.
    `n`  →  Advance the chip's current-URL index to the next one and
             flash its preview in the chip label. (Purely local; no
             side-effect beyond the chip updating its label.)

The chip carries:
    - ``citations``     : list[str] of evidence URLs (the only v1 field)
    - ``snippet_paths`` : parallel list[str|None] of cached-snippet file
                          paths. ``None`` for citations whose connector
                          never wrote a snippet (or whose fetch failed).
                          Length should match ``citations`` length.
    - ``agent_id``      : e.g. ``final-report`` — used for the modal title
    - ``thesis_id``     : int row id of the thesis (optional)
    - ``version``       : e.g. ``v3`` (optional)
    - ``timestamp``     : ISO-ish string (optional)
    - ``_current_idx``  : int — which citation ``o``/``y``/`v`/``n`` act
                          on (defaults to 0)

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

    class ActionRequested(Message):
        """Posted when the user presses ``o`` / ``y`` / ``n`` on the chip.

        The chat screen listens for this and calls
        ``frontend.utils.platform.open_in_browser`` /
        ``copy_to_clipboard`` for ``action='open'/'copy'``, and updates
        an inline label preview for ``action='preview'``. The chip does
        NOT call the platform helper itself — keeping the side-effect
        in one place lets tests monkey-patch the single function and
        assert behaviour without actually launching a browser.

        Attributes:
            chip_id : str  — the widget id
            action  : str  — one of "open", "copy", "preview"
            url     : str  — the URL the user acted on ("" if no citations)
            idx     : int  — index into the citations list (``-1`` if none)
        """
        def __init__(self, chip_id: str, action: str, url: str, idx: int) -> None:
            super().__init__()
            self.chip_id = chip_id
            self.action = action
            self.url = url
            self.idx = idx

    def __init__(
        self,
        count: int = 0,
        *,
        citations: list[str] | None = None,
        snippet_paths: list[str | None] | None = None,
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
        # Snippet paths must align with citations. Pad to length with
        # ``None`` for missing entries; ignore extras (defensive).
        if snippet_paths:
            self.snippet_paths: list[str | None] = list(snippet_paths)[: count]
            while len(self.snippet_paths) < count:
                self.snippet_paths.append(None)
        else:
            self.snippet_paths = [None] * count
        self.count = count
        self.agent_id = agent_id
        self.thesis_id = thesis_id
        self.version = version
        self.timestamp = timestamp
        self._current_idx: int = 0 if self.citations else -1
        super().__init__(self._label(), markup=True, **kwargs)
        self.add_class("citation-chip")
        if self.count == 0:
            self.add_class("chip-empty")
        else:
            self.add_class("chip-has-data")
        # Snippet badge: chip shows ◫ if any citation has a snippet
        if any(p for p in self.snippet_paths):
            self.add_class("chip-has-snippets")
        self.can_focus = True

    # ----- label rendering -----------------------------------------------
    def _short_host(self, url: str) -> str:
        """Compact host-only rendering for the chip's hover label."""
        if not url:
            return ""
        try:
            from urllib.parse import urlparse
            host = (urlparse(url).hostname or "").lower()
            return host[4:] if host.startswith("www.") else host
        except Exception:
            return ""

    def _label(self) -> str:
        if self.count == 0:
            return "[no citations] ↵"
        word = "citation" if self.count == 1 else "citations"
        snippet_count = sum(1 for p in self.snippet_paths if p)
        # Whole-chip snippet badge: shows ◫ if any cached snippet is
        # fresh, ⚠ ◫ if at least one is past its TTL, and nothing if
        # no snippets at all. We pick the *worst* state — a stale
        # badge always wins over a fresh one — so reviewers can't miss it.
        if snippet_count:
            snippet_badge = " ⚠ ◫" if self._any_snippet_stale() else " ◫"
        else:
            snippet_badge = ""
        if self.count == 1 or self._current_idx < 0:
            return f"[{self.count} {word}{snippet_badge}] ↵"
        host = self._short_host(self._current_url()) or "?"
        # Per-citation snippet mini-badge if THIS idx has a cached snippet.
        per_idx_stale, per_idx_present = self._idx_snippet_stale()
        if per_idx_present:
            per_idx_snip = " ⚠ ◫" if per_idx_stale else " ◫"
        else:
            per_idx_snip = ""
        # Show "idx/n · host" so the user knows which one `o` will fire.
        return f"[{self._current_idx + 1}/{self.count} {host}{per_idx_snip}] ↵"

    def _any_snippet_stale(self) -> bool:
        """True if at least one snippet's cache TTL has elapsed.

        Reads the sidecar metadata on disk each time, so a re-rendered
        chip picks up freshness changes without needing a remount.
        Failure to read sidecar is treated as fresh (the conservative
        choice — better than flashing ⚠ on a malformed meta file).
        """
        try:
            from runtime.snippets import snippet_metadata_for
        except Exception:
            # Best-effort: pure-frontend label rendering shouldn't
            # crash when runtime import is unavailable.
            return False
        for p in self.snippet_paths:
            if not p:
                continue
            meta = snippet_metadata_for(p)
            if meta is not None and meta.is_stale():
                return True
        return False

    def _idx_snippet_stale(self) -> tuple[bool, bool]:
        """Return ``(is_stale, has_snippet)`` for the current idx."""
        if (self._current_idx < 0
            or self._current_idx >= len(self.snippet_paths)
            or not self.snippet_paths[self._current_idx]):
            return (False, False)
        try:
            from runtime.snippets import snippet_metadata_for
        except Exception:
            return (False, True)
        meta = snippet_metadata_for(self.snippet_paths[self._current_idx])
        if meta is None:
            return (False, True)
        return (meta.is_stale(), True)

    def _current_url(self) -> str:
        if not self.citations or self._current_idx < 0:
            return ""
        if self._current_idx >= len(self.citations):
            return ""
        return self.citations[self._current_idx]

    def set_count(self, count: int) -> None:
        self.count = count
        # NB: callers that want to update citations separately should use
        # ``set_citations`` so the URL list and count stay in sync.
        if count == 0:
            self.add_class("chip-empty")
            self.remove_class("chip-has-data")
        else:
            self.add_class("chip-has-data")
            self.remove_class("chip-empty")
        # Drop current_idx back to a safe value if the list shrank.
        if self._current_idx >= count:
            self._current_idx = 0 if count else -1
        self.update(self._label())

    def set_citations(
        self,
        citations: list[str],
        *,
        snippet_paths: list[str | None] | None = None,
        agent_id: str = "",
        thesis_id: int | None = None,
        version: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        """Replace the chip's data in one call."""
        self.citations = list(citations or [])
        self.count = len(self.citations)
        if snippet_paths:
            self.snippet_paths = list(snippet_paths)[: self.count]
            while len(self.snippet_paths) < self.count:
                self.snippet_paths.append(None)
        else:
            self.snippet_paths = [None] * self.count
        if agent_id:
            self.agent_id = agent_id
        if thesis_id is not None:
            self.thesis_id = thesis_id
        if version is not None:
            self.version = version
        if timestamp is not None:
            self.timestamp = timestamp
        self._current_idx = 0 if self.citations else -1
        if self.count == 0:
            self.add_class("chip-empty")
            self.remove_class("chip-has-data")
            self.remove_class("chip-has-snippets")
        else:
            self.add_class("chip-has-data")
            self.remove_class("chip-empty")
        if any(p for p in self.snippet_paths):
            self.add_class("chip-has-snippets")
        self.update(self._label())

    # ----- action methods (testable directly) ----------------------------
    def request_open(self) -> str:
        """Post an ``action='open'`` message; return the URL we'd act on.

        Returns ``""`` (and posts a no-op marker) if there are no
        citations — chat.py can route that to a toast.
        """
        url = self._current_url()
        if not url:
            self.post_message(self.ActionRequested(self.id or "", "open", "", -1))
            return ""
        self.post_message(self.ActionRequested(self.id or "", "open", url, self._current_idx))
        return url

    def request_copy(self) -> str:
        """Post an ``action='copy'`` message; return the URL we'd act on."""
        url = self._current_url()
        if not url:
            self.post_message(self.ActionRequested(self.id or "", "copy", "", -1))
            return ""
        self.post_message(self.ActionRequested(self.id or "", "copy", url, self._current_idx))
        return url

    def request_view(self) -> str:
        """Post an ``action='snippet'`` message; return the snippet path.

        The path is the on-disk cached excerpt the runtime wrote for
        this citation. Empty/no snippet path → empty-url marker so
        chat.py can toast "no snippet for this citation".
        """
        if not self.snippet_paths or self._current_idx < 0:
            self.post_message(self.ActionRequested(self.id or "", "snippet", "", self._current_idx))
            return ""
        path = self.snippet_paths[self._current_idx] if self._current_idx < len(self.snippet_paths) else None
        if not path:
            self.post_message(self.ActionRequested(self.id or "", "snippet", "", self._current_idx))
            return ""
        self.post_message(self.ActionRequested(self.id or "", "snippet", path, self._current_idx))
        return path

    def request_preview(self) -> str:
        """Advance to next URL and post a ``preview`` message with it."""
        if not self.citations:
            self.post_message(self.ActionRequested(self.id or "", "preview", "", -1))
            return ""
        self._current_idx = (self._current_idx + 1) % len(self.citations)
        url = self._current_url()
        self.update(self._label())
        self.post_message(self.ActionRequested(self.id or "", "preview", url, self._current_idx))
        return url

    # ----- input handlers ------------------------------------------------
    def on_key(self, event) -> None:
        """Route keys on the focused chip.

        ``enter``  → open the modal (existing).
        ``o``      → open this chip's current URL in the OS browser.
        ``y``      → copy that URL to clipboard.
        ``v``      → view cached snippet for the current citation in
                     ``less``/``bat``.
        ``n``      → advance to the next URL in the chip's local index.
        """
        if event.key == "enter":
            self.post_message(self.Pressed(self.id or ""))
            event.prevent_default()
            event.stop()
            return
        if event.key == "o":
            self.request_open()
            event.prevent_default()
            event.stop()
            return
        if event.key == "y":
            self.request_copy()
            event.prevent_default()
            event.stop()
            return
        if event.key == "v":
            self.request_view()
            event.prevent_default()
            event.stop()
            return
        if event.key == "n":
            self.request_preview()
            event.prevent_default()
            event.stop()
            return

    def _on_click(self, event) -> None:
        """Mouse click opens the modal."""
        # Note: Textual passes a generic click event; we just post the
        # same message regardless of button. Right-clicks are rare in
        # TUI; if needed, branch on event.button.
        self.post_message(self.Pressed(self.id or ""))
