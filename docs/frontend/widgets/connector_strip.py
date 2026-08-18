"""
connector_strip.py — the '▾ via: SEC EDGAR · transcripts · OpenInsider' line
                      under each agent bubble.

Owns shape; chat owns state.  ChatScreen feeds ConnectorCompleted / ConnectorFailed
events into the bubble's strip via `BubbleConnectorStrip.record()`.

States per chip (from cheap to expensive):
    fired      SUCCESS — just ran this call, returned something
    stale      SUCCESS, but the as_of is older than the freshness tier cutoff
    partial    PARTIAL — ran, but with caveats (note)
    failed     FAILED — connector threw or returned FAILED ToolResult
    skipped    not even attempted (the orchestrator bypassed it this wave)

Render shape (one line, terminal-width capped via _wid):
    ▾  via:  ● sec_edgar  ● transcripts  ⚠ insider 1 stale  ·  3 connectors

Glyphs:
    fired       ● (sage)
    stale       ⚠ (amber)        ← as_of > freshness tier
    partial     ◐ (amber)
    failed      ✗ (red)
    skipped     ○ (dim)

Pure ANSI-string renderer — no React-style state. The widget is a `Static` whose
content is `strip_line(state)` of the current chip set. Re-runs full line on
record() — small dict size, cheap to render.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from textual.widget import Widget
from textual.widgets import Static

from frontend.connectors_catalog import ConnectorEntry, ALL_CONNECTORS, by_name

# ---- ANSI tokens (mirror style.tcss) ----------------------------------------
_RESET   = "\x1b[0m"
_DIM     = "\x1b[38;2;110;120;135m"
_FG      = "\x1b[38;2;212;212;212m"
_FG3     = "\x1b[38;2;160;165;175m"
_BRAND   = "\x1b[1;38;2;140;220;220m"
_SAGE    = "\x1b[38;2;140;210;150m"
_AMBER   = "\x1b[38;2;230;200;130m"
_RED     = "\x1b[38;2;225;145;140m"

ChipState = Literal["fired", "stale", "partial", "failed", "skipped"]

# The freshness tier width in seconds. Anything older than this is "stale".
TIER_FRESHNESS_S = {
    "free": 86400 * 2,    # 2 days — RSS / market data plenty fresh
    "tier2": 86400 * 7,   # 1 week — fundamentals OK
    "tier3": 86400 * 30,  # 1 month — premium sources
}

# Connector names treated as "macro / fundamentals / quarterly" — wider tolerance.
_LONG_FRESHNESS = {"13F", "EFTS", "EDGAR"}


@dataclass
class Chip:
    """One chip in the strip. The widget owns these in render order."""
    name: str
    label: str
    state: ChipState = "skipped"
    note: str = ""
    as_of: str | None = None        # ISO timestamp from the runtime
    duration_ms: int | None = None  # tool round-trip
    is_recommended: bool = False    # show name in bold brand cyan when True


@dataclass
class ConnectorStripState:
    """State for one bubble's strip.  Rebuild via render_line()."""
    chips: dict[str, Chip] = field(default_factory=dict)

    def record_fired(
        self,
        *,
        tool: str,
        status: str,           # SUCCESS | PARTIAL | FAILED | EMPTY
        as_of: str,
        note: str,
        data_summary: str | None = None,  # short string summary; appended to note
        duration_ms: int | None = None,
        agent_id: str | None = None,
        strip_label: str | None = None,  # override default short label (used by strip)
    ) -> None:
        entry = by_name(tool)
        if entry is None:
            label = tool
            tier = "free"
        else:
            label = strip_label or entry.short
            tier = entry.tier
        # Map runtime status → chip state, factoring freshness.
        if status == "FAILED":
            state: ChipState = "failed"
        elif status == "EMPTY":
            state = "skipped"
        elif status == "PARTIAL":
            state = "partial"
        else:  # SUCCESS
            state = _freshness_state(as_of, tier, label if entry else tool)
        # Combine note + data_summary into a displayable string for the chip.
        chip_note = note
        if data_summary and data_summary not in (chip_note or ""):
            chip_note = (chip_note + " \u00b7 " + data_summary) if chip_note else data_summary
        chip = Chip(
            name=tool,
            label=label,
            state=state,
            note=chip_note,
            as_of=as_of,
            duration_ms=duration_ms,
            is_recommended=bool(entry and entry.recommended),
        )
        # Preserve existing entry's agent if already present (allows multi-call).
        self.chips[tool] = chip

    def record_failed(self, *, tool: str, error: str) -> None:
        entry = by_name(tool)
        label = (entry.short if entry else tool)
        self.chips[tool] = Chip(
            name=tool,
            label=label,
            state="failed",
            note=error[:60],
            is_recommended=bool(entry and entry.recommended),
        )

    def summary_counts(self) -> dict[str, int]:
        """For the footer counter. Buckets per state."""
        out: dict[str, int] = {"fired": 0, "stale": 0, "failed": 0, "skipped": 0, "partial": 0}
        for c in self.chips.values():
            out[c.state] = out.get(c.state, 0) + 1
        return out


def _freshness_state(as_of: str, tier: str, tool: str | None = None) -> ChipState:
    """'stale' if `as_of` older than the per-tier cutoff, else 'fired'."""
    if not as_of:
        return "fired"
    try:
        ts = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta_s = (now - ts).total_seconds()
    except (ValueError, TypeError):
        return "fired"
    # Quarterly-disclosure sources (13F, full-text filings) tolerate longer gaps.
    if tool in _LONG_FRESHNESS:
        return "stale" if delta_s > 86400 * 90 else "fired"  # 90 days
    return "stale" if delta_s > TIER_FRESHNESS_S.get(tier, 86400) else "fired"


# ----------------------------------------------------------- render
_STATE_GLYPH = {
    "fired":   (f"{_SAGE}\u25cf{_RESET}", _SAGE),       # ●
    "stale":   (f"{_AMBER}\u26a0{_RESET}", _AMBER),     # ⚠
    "partial": (f"{_AMBER}\u25d0{_RESET}", _AMBER),     # ◐
    "failed":  (f"{_RED}\u2717{_RESET}",   _RED),       # ✗
    "skipped": (f"{_DIM}\u25cb{_RESET}",   _DIM),       # ○
}


def render_line(state: ConnectorStripState, *, width: int = 110) -> str:
    """
    The single line that goes under an agent's bubble.

    Pattern:
        ▾  via: ●sec_edgar ●transcripts ⚠openinsider · 3 connectors
    """
    chips = list(state.chips.values())
    # Show in catalog order so the line reads consistently across agents.
    order = {c.name: i for i, c in enumerate(ALL_CONNECTORS)}
    chips.sort(key=lambda c: order.get(c.name, 999))

    if not chips:
        return f"{_DIM}\u25be{_RESET}  {_BRAND}via:{_RESET} {_DIM}(none fired){_RESET}"

    parts: list[str] = [
        f"{_DIM}\u25be{_RESET}",   # ▾
        f"  {_BRAND}via:{_RESET} ",
    ]
    for i, ch in enumerate(chips):
        if i > 0:
            parts.append(f" {_DIM}\u00b7{_RESET} ")  # ·
        glyph, _ = _STATE_GLYPH[ch.state]
        parts.append(glyph)
        label_color = _BRAND if ch.is_recommended else _FG
        parts.append(f"{label_color}{ch.label}{_RESET}")

    n_total = len(chips)
    counts = state.summary_counts()
    badge_bits: list[str] = []
    if counts["failed"]:
        badge_bits.append(f"{_RED}{counts['failed']} failed{_RESET}")
    if counts["stale"]:
        badge_bits.append(f"{_AMBER}{counts['stale']} stale{_RESET}")
    badge = "  \u00b7  " + "  \u00b7  ".join(badge_bits) if badge_bits else ""
    summary = f"  {_DIM}\u00b7  {n_total} connector{'s' if n_total != 1 else ''}{_RESET}"

    line = "".join(parts) + summary + badge
    if width > 0:
        # Clamp to width — strip ANSI before measuring.
        import re as _re
        visible_len = len(_re.sub(r"\x1b\[[0-9;]*m", "", line))
        if visible_len > width:
            # Naive clamp; rare because chips are short.
            visible = _re.sub(r"\x1b\[[0-9;]*m", "", line)[: max(0, width - 1)]
            line = visible + "\u2026"
    return line


def render_footer_chip(state: ConnectorStripState) -> str:
    """
    Compact counter for the chat footer: 'connectors: 3/9 active (1 stale)'.

    "active" = fired (any status other than skipped). Shown alongside model +
    paid-for + flow id in the existing footer hint.
    """
    counts = state.summary_counts()
    fired_like = counts["fired"] + counts["stale"] + counts["partial"]
    n_total = len(state.chips) or _DISPLAY_TOTAL_FALLBACK
    out = f"{_BRAND}connectors:{_RESET} {fired_like}/{n_total} active"
    if counts["stale"]:
        out += f"  {_AMBER}({counts['stale']} stale){_RESET}"
    if counts["failed"]:
        out += f"  {_RED}({counts['failed']} failed){_RESET}"
    return out


# What we show when nothing has fired yet — defaults to the catalog size, so
# users see '0/9 active' on a fresh chat, not '0/0'.
_DISPLAY_TOTAL_FALLBACK = 9


# ----------------------------------------------------------- widget
class BubbleConnectorStrip(Static):
    """
    The strip widget embedded inside (or directly below) a MessageBubble.

    Single child of a `Vertical`; chat calls `update_state(st)` on each
    ConnectorCompleted/Failed.  Renders the live line via `render_line(st)`.

    Stateless beyond a single buffer:
        self._state: ConnectorStripState
    """

    DEFAULT_CSS = """
    BubbleConnectorStrip {
        height: 1;
        padding: 0 1;
        color: #d4d4d4;
        background: #11141a;
        text-style: none;
    }
    """

    def __init__(self, *, width: int = 110, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._state = ConnectorStripState()
        self._width = width

    def update_state(self, st: ConnectorStripState) -> None:
        self._state = st
        self.update(render_line(st, width=self._width))

    def record_fired(self, **kw) -> None:
        self._state.record_fired(**kw)
        self.update(render_line(self._state, width=self._width))

    def record_failed(self, **kw) -> None:
        self._state.record_failed(**kw)
        self.update(render_line(self._state, width=self._width))


# ----------------------------------------------------------- footer chip helper
def connectors_footer_segment(active_state: ConnectorStripState | None) -> str:
    """
    String to PREPEND into the existing footer hint; finally-formatted.

    Returns '' when there is nothing to report yet, so chat.py can keep
    `_update_footer_hint` clean by just prepending when non-empty.
    """
    return render_footer_chip(active_state) if active_state is not None else ""
