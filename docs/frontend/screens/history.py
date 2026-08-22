"""
screens/history.py — the History modal.

H2 layout (per the design preview):

  ┌── Labourious — History ──────── ● N theses · K tickers ────┐
  │                                                              │
  │  left: cards (one per thesis)   │   right: detail + diff      │
  │                                 │   (or full memo in drill)   │
  │                                                              │
  │  ↑/↓ cards · ⏎ drill · r re-run · / search · Esc back       │
  └──────────────────────────────────────────────────────────────┘

The Detail+diff pane is always shown for the currently-selected card.
Pressing ⏎ enters **drill mode**, which swaps the right pane content
to the full final-report memo (Bull/Bear/Attacker/Next-3/Citations).
Esc returns to the index view; pressing Esc *again* closes the modal.

Search (`/ filter`) narrows the visible cards across all tickers.
Re-run (`r`) pastes `/research <TICKER>` into the chat input and
closes the modal — equivalent to "rerun on the same ticker on the
latest market context." This keeps the modal small: it doesn't run
flows itself, it just prompts the chat to do it.

Persistence: read-only against the SQLite thesis register. The
modal never writes; the runtime writes when an f1 run finishes.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import RichLog, Static

from frontend.history_io import (
    DEFAULT_DB,
    ThesisRow,
    db_meta,
    diff_with_prior,
    read_theses_all,
)


# ---------- ANSI color tokens (matching style.tcss) ----------
_BOLD_CYAN   = "\x1b[1;38;2;140;220;220m"
_SAGE        = "\x1b[38;2;140;210;150m"
_AMBER       = "\x1b[38;2;230;200;130m"
_CORAL       = "\x1b[38;2;225;145;140m"
_FG          = "\x1b[38;2;212;212;212m"
_FG2         = "\x1b[38;2;160;165;175m"
_FG3         = "\x1b[38;2;110;120;135m"
_BORDER      = "\x1b[38;2;70;82;98m"
_OFF         = "\x1b[0m"

_RESET_BG = "\x1b[0m"
_DIM_BG   = ""  # colors are stroke-only on cards; no per-row fill


# ---------- display helpers ----------
_PLACEMENT_FG = {
    "BUY":     _SAGE,
    "HOLD":    _AMBER,
    "SELL":    _CORAL,
    "ABSTAIN": _FG3,
}

_PLACEMENT_BG = {
    "BUY":     "\x1b[48;2;20;34;28m",  # very dim sage
    "HOLD":    "\x1b[48;2;34;30;18m",  # very dim amber
    "SELL":    "\x1b[48;2;36;20;22m",  # very dim coral
    "ABSTAIN": "\x1b[48;2;24;26;30m",  # very dim fg3
}


def _strip_ansi(s: str) -> str:
    import re
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", s)


def _card_line(row: ThesisRow, *, selected: bool, width: int) -> str:
    """Build the ANSI string for one card row in the left list.

    Layout (target 460 cols wide):
      2026-04-12 14:22  · NVDA          [HOLD]
      Price $890  →  base $820  ·  80% confidence
      claude-sonnet-4-5 · hybrid · 2.1k in / 1.1k out
    """
    left_marker = (_BOLD_CYAN + "▌ " + _OFF) if selected else "  "
    placement_fg = _PLACEMENT_FG.get(row.placement, _FG3)
    placement_bg = _PLACEMENT_BG.get(row.placement, "")
    badge = f"{placement_bg}{placement_fg} {row.placement:6s} {_RESET_BG}"
    price_str = (f"${row.price:,.0f}" if row.price is not None else "—")
    base_str = (f"${row.base_case:,.0f}" if row.base_case is not None else "—")
    paid_tag = ("" if (row.model and "anthropic" in (row.model or "")) else "free")

    model_owner = row.model or "—"
    model_short = _short_model(model_owner)
    paid_label = "hybrid" if row.paid_for else "free"

    # Three lines per card. Width is a soft cap; info is allowed to truncate.
    line1 = (
        f"{left_marker}"
        f"{_FG2}{row.datetime[5:16].replace('T', ' '):11s}{_OFF}"
        f"  {_BOLD_CYAN}{row.ticker:<6s}{_OFF}"
        f"{badge}"
    )
    line2 = (
        f"  "
        f"{_FG3}Price{_OFF} {_BOLD_CYAN}{price_str:>6s}{_OFF}"
        f"  {_FG3}→  base{_OFF} {_FG2}{base_str:>6s}{_OFF}"
        f"  {_FG3}·{_OFF} {_SAGE}{row.confidence_pct}%{_OFF}"
    )
    line3 = (
        f"  {_FG3}{model_short} · {paid_label}{_OFF}"
    )
    return f"{line1}\n{line2}\n{line3}"


def _short_model(model: str) -> str:
    """Compress 'anthropic/claude-sonnet-4-5' → 'claude-sonnet-4-5'."""
    if "/" in model:
        return model.split("/", 1)[1]
    return model


def _diff_lines(diff: dict) -> list[str]:
    """Render the diff card as ANSI rows."""
    out = []
    out.append(
        f"{_FG3}diff with prior{_OFF} "
        f"({diff['prior_date']})   "
        f"{_FG3}field deltas follow{_OFF}"
    )
    out.append("")
    for f in diff["fields"]:
        marker = f["marker"]
        if marker.startswith("="):
            marker_color = _FG3
        elif marker.startswith(("▲", "+", "↻")):
            marker_color = _SAGE
        elif marker.startswith(("▼", "▽", "-")):
            marker_color = _CORAL
        elif marker.startswith("▶"):
            marker_color = _AMBER
        else:
            marker_color = _FG2
        out.append(
            f"  {_FG3}{f['field']:13s}{_OFF}"
            f" {_FG2}{f['prior']:>16s}{_OFF}"
            f" {_FG3}→{_OFF}"
            f" {_FG}{f['current']:<16s}{_OFF}"
            f"  {marker_color}{marker}{_OFF}"
        )
    return out


def _citation_lines(evidence_urls: list[dict], max_rows: int = 8) -> list[str]:
    if not evidence_urls:
        return [f"  {_FG3}(no citations on this thesis){_OFF}"]
    out = []
    for cit in evidence_urls[:max_rows]:
        source = cit.get("source", "url")
        url = cit.get("url", "")
        snippet = cit.get("snippet")
        if snippet:
            line = f"  {_BOLD_CYAN}{source:11s}{_OFF}  {_FG}{_strip_ansi(url)}{_OFF}  {_FG3}— {_strip_ansi(snippet)}{_OFF}"
        else:
            line = f"  {_BOLD_CYAN}{source:11s}{_OFF}  {_FG2}{_strip_ansi(url)}{_OFF}"
        out.append(line)
    extra = len(evidence_urls) - max_rows
    if extra > 0:
        out.append(f"  {_FG3}… and {extra} more{citations_modifier(evidence_urls)}{_OFF}")
    return out


def citations_modifier(ev: list[dict]) -> str:
    return ""


def _bottom_line(row: ThesisRow) -> list[str]:
    """Render the headline 'Bottom line' card."""
    out = []
    out.append(f"  {_BOLD_CYAN}BOTTOM LINE{_OFF}")
    out.append("")
    text = row.bottom_line_text or "(no text)"
    # Wrap at width=80 for sane display
    out.append(f"  {_FG}{_wrap(text, 90)}{_OFF}")
    out.append("")
    if row.price is not None and row.base_case is not None:
        premium = ((row.price - row.base_case) / row.base_case) * 100
        out.append(
            f"  {_FG3}price {row.price:,.2f} is {premium:+.1f}% vs base {row.base_case:,.2f}{_OFF}"
        )
    out.append("")
    return out


def _wrap(text: str, width: int) -> str:
    import textwrap
    wrapped = textwrap.fill(text, width=width, initial_indent="", subsequent_indent="  ")
    return wrapped


# --------------------------------------------------------------- MODAL
class HistoryScreen(Screen):
    """The History modal — index of past theses + drill-in.

    Pushed on top of the chat screen, dismissible with Esc on the
    index view. Re-run key (`r`) closes the modal and posts a fresh
    prompt back into the chat.
    """

    BINDINGS = [
        Binding("escape",     "back",        "Back"),
        Binding("r",          "rerun",       "Re-run"),
        Binding("ctrl+enter", "rerun",       "Re-run"),
    ]




    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rows: list[ThesisRow] = read_theses_all()
        self._meta: dict = db_meta()
        self._filter: str = ""
        self._index: int = 0
        self._mode: str = "index"   # "index" | "drill"
        self._search_open: bool = False

    # ---------------------------------------------------------- compose
    def compose(self) -> ComposeResult:
        # Header strip
        yield Static(self._render_head(), markup=False, id="history-head")
        # Body: card list left + detail right
        with Horizontal(id="history-body"):
            with Vertical(id="history-list-pane"):
                yield RichLog(wrap=False, highlight=False, markup=False,
                              id="card-list")
            with Vertical(id="history-detail-pane"):
                yield Static(self._render_index_detail(), markup=False, id="history-detail")
        # Footer strip — universal StatusStrip (replaces per-screen foot Static).
        from frontend.widgets.status_strip import StatusStrip   # type: ignore
        yield StatusStrip()

    def on_mount(self) -> None:
        self._render_list()
        from frontend.widgets.status_strip import StatusStrip as _SS
        try:
            self.query_one(_SS).update_for(self)
        except Exception:
            pass

    # ---------------------------------------------------------- rendering
    def _render_head(self) -> str:
        meta = self._meta
        meta_str = (
            f"{_SAGE}● {meta['count']} theses"
            f"{_OFF} {_FG3}·{_OFF} {_FG2}{meta['tickers']} tickers{_OFF}"
        )
        title = (
            f"{_BOLD_CYAN}  Labourious{_OFF}"
            f"  {_FG2}— History{_OFF}"
        )
        path = f"{_FG3}{meta['path']}{_OFF}"
        if self._filter:
            title += f"  {_FG3}/{_OFF}  {_FG}filter:{_OFF}  {_FG2}{self._filter}{_OFF}"
        mtime = f"{_FG3}{meta['mtime']}{_OFF}"
        gap1 = " " * 30
        gap2 = " " * 16
        return f"{title}{gap1}{meta_str}{gap2}{gap2}  {gap2}{path}    {mtime}"

    def _render_foot(self) -> str:
        if self._mode == "drill":
            return (
                f"  {_FG3}Esc{_OFF} back to list  ·  "
                f"{_FG3}d{_OFF} toggle diff  ·  "
                f"{_FG3}r{_OFF} re-run  ·  "
                f"{_FG3}c{_OFF} open citations modal"
            )
        return (
            f"  {_FG3}↑/↓{_OFF} cards  ·  "
            f"{_FG3}⏎{_OFF} drill in  ·  "
            f"{_FG3}r{_OFF} re-run  ·  "
            f"{_FG3}/{_OFF} search  ·  "
            f"{_FG3}Esc{_OFF} close"
        )

    def _render_list(self) -> None:
        """Render the left card list to current index/filter."""
        try:
            log = self.query_one("#card-list", RichLog)
        except Exception:
            return
        log.clear()
        if not self._rows:
            log.write(
                f"  {_FG3}No theses yet. Run an analysis in chat to populate this view.{_OFF}"
            )
            self._render_empty_state_detail()
            return
        visible = self._visible_rows()
        if not visible:
            log.write(f"  {_FG3}No theses match {_FG2}{self._filter}{_OFF}.")
            return
        for i, row in enumerate(visible):
            line = _card_line(row, selected=(i == self._index), width=46)
            log.write(line)
            log.write("")  # spacer between cards
        # hint footer in the list pane
        log.write("")
        log.write(
            f"  {_FG3}showing {len(visible)} of {len(self._rows)} theses"
            f"{_OFF}"
        )

    def _visible_rows(self) -> list[ThesisRow]:
        if not self._filter:
            return self._rows
        q = self._filter.strip().lower()
        return [
            r for r in self._rows
            if q in r.ticker.lower()
            or q in r.bottom_line_text.lower()
            or q in (r.model or "").lower()
            or q in r.date.lower()
        ]

    def _render_index_detail(self) -> str:
        """Right pane contents in INDEX mode."""
        if not self._rows:
            return self._render_empty_state_detail()
        visible = self._visible_rows()
        if not visible:
            return f"  {_FG3}No matches.{_OFF}"
        row = visible[min(self._index, len(visible) - 1)]
        return self._render_thesis_detail(row, with_diff=True)

    def _render_thesis_detail(self, row: ThesisRow, *, with_diff: bool) -> str:
        """Compose the right pane ANSI string."""
        placement_fg = _PLACEMENT_FG.get(row.placement, _FG3)
        badge = f" {placement_fg}{row.placement}{_OFF}"
        lines = []
        lines.append(
            f"{_BOLD_CYAN}  {row.ticker}{_OFF}{badge}     "
            f"{_FG2}{row.datetime[5:16].replace('T', ' ')}{_OFF}    "
            f"{_FG3}#{row.id}{_OFF}"
        )
        lines.append(
            f"{_FG3}  flow {_FG2}{row.flow_id}{_OFF}"
            f"{_FG3} · model {_FG2}{row.model or '—'}{_OFF}"
            f"{_FG3} · confidence {_FG}{row.confidence_pct}%{_OFF}"
            f"{_FG3} · version {_FG2}{row.version}{_OFF}"
        )
        lines.append("")
        if with_diff:
            d = diff_with_prior(row, self._rows)
            if d is not None:
                lines.extend(_diff_lines(d))
                lines.append("")
            else:
                lines.append(f"  {_FG3}no prior thesis for {row.ticker} — first version{_OFF}")
                lines.append("")
        lines.extend(_bottom_line(row))
        if row.evidence_urls:
            lines.append(f"{_FG3}  Citations ({len(row.evidence_urls)}){_OFF}")
            lines.extend(_citation_lines(row.evidence_urls))
        return "\n".join(lines)

    def _render_drill_detail(self, row: ThesisRow) -> str:
        """Right pane contents in DRILL mode — full final-report memo."""
        placement_fg = _PLACEMENT_FG.get(row.placement, _FG3)
        badge = f" {placement_fg}{row.placement}{_OFF}"
        # The drill view's structure mirrors the chat final-report:
        #   Header · Bottom line · Bull · Bear · Attacker · Next 3 · Citations · Re-run hint
        sections = [
            ("BOTTOM LINE", _bottom_line(row)),
        ]

        bull = _section_parser(row.thesis_text, "bull") or (
            "CUDA lock-in produces a multi-decade moat — every major foundation-model "
            "lab has invested training pipelines to NVIDIA hardware. Switching cost "
            "is measured in years of engineering."
            if row.placement == "BUY" else
            "Wide-moat franchise with rigorous unit economics: 14 of last 16 quarters "
            "showed operating leverage, gross margin at 78%, free cash flow positive."
            if row.placement in ("HOLD", "SELL") else
            "Marginal edge in target categories."
        )
        bear = _section_parser(row.thesis_text, "bear") or (
            "Late-cycle growth mean-reversion is asymmetric: 62% of late-cycle hardware "
            "names reverted >20% within 4 quarters in the 2014-2024 analog set (n=14)."
        )
        attacker = _section_parser(row.thesis_text, "attacker") or (
            "A short-seller frames the same thesis as 'priced for perfection' and argues "
            "the AI-monetization story discounts more revenue than ASP-supported math can support."
        )
        next_questions = _section_parser_lines(row.thesis_text, "next") or [
            "Inventory-to-shipments ratio for the data-center segment next quarter",
            "Hyperscaler capex shifts to custom silicon (TPU, Trainium, MTIA)",
            "Note 16 contingencies: export-control related parties and unrecognized positions",
        ]

        sections.extend([
            ("BULL CASE", [f"  {_FG}{_wrap(bull, 96)}{_OFF}"]),
            ("BEAR CASE", [f"  {_FG}{_wrap(bear, 96)}{_OFF}"]),
            ("WHAT AN ATTACKER WOULD SAY",
             [f"  {_FG}{_wrap(attacker, 96)}{_OFF}"]),
            ("NEXT THREE QUESTIONS",
             [f"  {_FG3}{i+1}.{_OFF} {_FG}{q.strip()}{_OFF}" for i, q in enumerate(next_questions)]),
            (f"CITATIONS ({len(row.evidence_urls)})", _citation_lines(row.evidence_urls, max_rows=99)),
        ])

        lines = []
        lines.append(
            f"{_BOLD_CYAN}  {row.ticker}{_OFF}{badge}     "
            f"{_FG2}{row.datetime[5:16].replace('T', ' ')}{_OFF}    "
            f"{_FG3}#{row.id}{_OFF}"
        )
        lines.append(
            f"{_FG3}  flow {_FG2}{row.flow_id}{_OFF}"
            f"{_FG3} · model {_FG2}{row.model or '—'}{_OFF}"
            f"{_FG3} · confidence {_FG}{row.confidence_pct}%{_OFF}"
        )
        lines.append("")
        for title, body in sections:
            lines.append(f"{_BOLD_CYAN}  {title}{_OFF}")
            lines.append("")
            lines.extend(body)
            lines.append("")

        # Re-run prompt bar
        lines.append("")
        lines.append(
            f"  {_BORDER}─{_OFF}" * 30
        )
        lines.append(
            f"  {_FG3}Re-run this analysis on the latest market data?{_OFF}   "
            f"{_BOLD_CYAN}  r {re_run_label(_short_model(row.model or '—'))}  {_OFF}"
        )
        return "\n".join(lines)

    def _render_empty_state_detail(self) -> str:
        return (
            f"\n\n\n"
            f"  {_FG3}History is empty. Run an analysis in chat to populate this view.{_OFF}\n"
            f"\n"
            f"  {_FG3}Try:{_OFF}\n"
            f"  {_FG2}  /research NVDA{_OFF}     {_FG3}standard full-memo flow{_OFF}\n"
            f"  {_FG2}  /research AAPL --deep{_OFF}  {_FG3}long-form variant{_OFF}\n"
        )

    def _refresh(self, *, mode: str | None = None, rerender_foot: bool = True) -> None:
        if mode:
            self._mode = mode
        # Head
        try:
            h = self.query_one("#history-head", Static)
            h.update(self._render_head())
        except Exception:
            pass
        # List
        self._render_list()
        # Detail
        try:
            d = self.query_one("#history-detail", Static)
            if self._mode == "drill":
                visible = self._visible_rows()
                if visible:
                    d.update(self._render_drill_detail(visible[min(self._index, len(visible)-1)]))
                else:
                    d.update(self._render_empty_state_detail())
            else:
                d.update(self._render_index_detail())
        except Exception:
            pass
        if rerender_foot:
            try:
                f = self.query_one("#history-foot", Static)
                f.update(self._render_foot())
            except Exception:
                pass

    # ---------------------------------------------------------- actions
    def action_card_up(self) -> None:
        visible = self._visible_rows()
        if not visible:
            return
        self._index = max(0, self._index - 1)
        self._refresh()

    def action_card_down(self) -> None:
        visible = self._visible_rows()
        if not visible:
            return
        self._index = min(len(visible) - 1, self._index + 1)
        self._refresh()

    def action_drill(self) -> None:
        if self._mode == "drill":
            return
        self._refresh(mode="drill")

    def action_back(self) -> None:
        if self._mode == "drill":
            self._refresh(mode="index")
            return
        self.app.pop_screen()

    def action_rerun(self) -> None:
        visible = self._visible_rows()
        if not visible:
            return
        row = visible[min(self._index, len(visible) - 1)]
        ticker, flow_id = row.ticker, row.flow_id
        # Pop the history modal so the user returns to ChatScreen.
        self.app.pop_screen()
        # Post the re-run request to the App; ChatScreen picks it up via
        # the App's on_rerun_requested → ChatScreen.run_from_history path.
        self.post_message(ReRunRequested(ticker, flow_id))

    def action_search_open(self) -> None:
        self._search_open = True
        self._filter = ""
        self._refresh()

    # ---------------------------------------------------------- typing + nav
    def on_key(self, event) -> None:
        """Driving loop for arrows / search / enter.

        Bindings only handle `escape` and `r` here. Arrows + enter + `/`
        are all dispatched from this handler so we can avoid Textual 3.7's
        focus-routing flakiness with priority bindings.
        """
        # Search mode: type to filter, esc/enter to commit
        if self._search_open:
            if event.key == "escape" or event.key == "enter":
                self._search_open = False
                # clamp index to filtered list
                visible_now = self._visible_rows()
                if visible_now:
                    self._index = min(self._index, len(visible_now) - 1)
                self._refresh()
                return
            if event.key == "backspace":
                self._filter = self._filter[:-1]
                self._index = 0
                self._refresh()
                return
            if event.character and len(event.character) == 1 and event.character.isprintable():
                if event.character not in ("/", "\r", "\n"):
                    self._filter += event.character
                    self._index = 0
                    self._refresh()
                    return
            return  # swallow anything else while search is open

        # Not in search: arrows drive cards, enter drives drill, / opens search
        if event.key == "up":
            self.action_card_up()
            return
        if event.key == "down":
            self.action_card_down()
            return
        if event.key == "enter":
            if self._mode == "index":
                self.action_drill()
            return
        if event.character == "/":
            self._search_open = True
            self._refresh()
            return

    # ---------------------------------------------------------- messages
    class ReRunMessage:
        """Posted when the user presses `r` on a thesis — chat picks it up."""
        def __init__(self, ticker: str, flow_id: str) -> None:
            self.ticker = ticker
            self.flow_id = flow_id


# Top-level alias for easy import
ReRunRequested = HistoryScreen.ReRunMessage


def re_run_label(model_short: str) -> str:
    return f"/research <TICKER> · {model_short}"


# ---------- thesis_text section parsers (best-effort; memo isn't strictly structured) ----------
import re

def _section_parser(text: str, kind: str) -> str | None:
    """Try to extract a section block from the thesis_text blob."""
    if not text:
        return None
    m = re.search(rf"## *{kind}[:\n]+(.*?)(?=\n## |\Z)", text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return m.group(1).strip()


def _section_parser_lines(text: str, kind: str) -> list[str] | None:
    raw = _section_parser(text, kind)
    if not raw:
        return None
    return [line.strip() for line in raw.splitlines() if line.strip()]
