"""
providers_panel.py — the L3 accordion widget rendered inside Settings → Providers.

Layout (L3 pick from the preview):
  ┌── settings/providers ──  N visible ─── N total ─────────┐
  │ chips: [All] [Free] [Local] [Paid] [Custom]             │
  │ ▼ Local (5)                                            │
  │   ▾ ● Ollama . . . llama3.3:70b loaded    [expanded]   │
  │     ┌───────── base URL  http://...   ─────────┐        │
  │     │          model     ▾ llama3.3:70b        │        │
  │     │          auth      ● ready              │        │
  │     │          [Test connection] [Reset]      │        │
  │     └─────────────────────────────────────────┘        │
  │   ▸   LM Studio . . . — not running                   │
  │   ▸   ...                                               │
  │ ▶ Free (7)  ▶ Paid (4) ▶ Custom (4)                  │
  └────────────────────────────────────────────────────────┘

Public surface:
  ProvidersPanel.update(
      filter_tier=None|"free"|"local"|"paid"|"custom",
      expanded=None|"ollama"|...,
      providers_cfg=dict[str, ConfigProvider],  # existing entries from settings
      flash=None|"saved"|"auth-missing",
  )

The panel is render-only. SettingsScreen owns the state and the
bindings; this widget just paints.

v2 rendering notes (the bug list this rewrite closes):
  * Every row is composed through frontend.utils.ansi helpers, which
    measure *visible* width (escape sequences cost 0 columns). The old
    code mixed raw len() math with ANSI-laden strings, so rows wrapped
    and painted stray blocks at any width below ~140 columns.
  * The expanded box used a box_close string that was a lone ESC
    sequence ("" + box sides) — Rich rendered it as a run of stray
    colored blocks down the panel. Box top/bottom are now plain
    strings.
  * The panel tracks its container width on resize and re-renders, so
    shrinking the terminal reflows instead of clipping.
"""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static

from frontend.providers import (
    ALL_PROVIDERS,
    TIER_LABEL,
    TIER_ORDER,
    ProviderEntry,
    by_tier,
    recommended,
    status_for,
)
from frontend.theme import ANSI as _THEME_ANSI
from frontend.utils.ansi import (
    DEFAULT_WIDTH,
    fit_to,
    reset_at_end,
    two_columns,
    visible_len,
)


# ANSI tokens — single source of truth: frontend/theme.py (mirrors style.tcss).
# Focused/selected rows highlight with a neutral background bar + bold white
# name; brand cyan is identity-only.
def _sgr(key: str) -> str:
    return f"\x1b[{_THEME_ANSI[key]}m"


_FG = _sgr("fg")
_DIM = _sgr("fg3")
_FAINT = _sgr("faint")
_BRAND = "\x1b[1;38;2;232;232;232m"   # bold near-white — focus, not cyan
_OK = _sgr("ok")
_WARN = _sgr("warn")
_ERR = _sgr("err")
_BG_SURFACE = _sgr("bg_card")
_BG_HOVER = _sgr("bg_sel")
_RESET = "\x1b[0m"
_HOVER_BG = _sgr("bg_hover")
_UL = "\u2500"  # ─
_CARET_OPEN = "\u25be"  # ▾
_CARET_CLOSED = "\u25b8"  # ▸

# Expanded-pane box drawing (plain strings — no bare escape runs).
_BOX_V = f"{_BRAND}\u2502{_RESET}"          # │
_BOX_TL = f"{_BRAND}\u256d{_RESET}"          # ╭
_BOX_TR = f"{_BRAND}\u256e{_RESET}"          # ╮
_BOX_BL = f"{_BRAND}\u2570{_RESET}"          # ╰
_BOX_BR = f"{_BRAND}\u256f{_RESET}"          # ╯


@dataclass
class ProviderRowState:
    """Per-row runtime snapshot — read from runtime probes."""
    entry: ProviderEntry
    state: str       # ready | key-loaded | auth-missing | not-running | etc
    detail: str
    configured: bool  # user has explicitly added it to config.json
    key_present: bool


def _dot(state: str) -> str:
    return {
        "ready": f"{_OK}\u25cf{_RESET}",       # ●
        "key-loaded": f"{_OK}\u25cf{_RESET}",
        "auth-missing": f"{_WARN}\u25cf{_RESET}",
        "not-running": f"{_WARN}\u25cf{_RESET}",
        "not-installed": f"{_ERR}\u25cf{_RESET}",
        "config-not-set": f"{_ERR}\u25cf{_RESET}",
    }.get(state, f"{_FAINT}\u25cb{_RESET}")    # ○


# ----------------------------------------------------------- main widget
class ProvidersPanel(Widget):
    """Render-only. Settings owns state."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Will be set by SettingsScreen before each update()
        self._filter_tier: str | None = None
        self._expanded: str | None = None
        self._flash: str | None = None
        self._configured: dict[str, bool] = {}  # name -> present in config.json
        self._key_present: dict[str, bool] = {}
        self._focus_idx: int = 0
        self._last_width: int = 0
        # Mouse-click bookkeeping: the painted line records (from the last
        # _repaint) + the last clicked row, so "click again to expand" works.
        self._last_render_rows: list[dict] = []
        self._last_click_idx: int | None = None

    # ---------------------------------------------------- public API
    def update(
        self,
        *,
        filter_tier: str | None,
        expanded: str | None,
        configured_names: set[str],
        key_present: dict[str, bool],
        focus_idx: int = 0,
        flash: str | None = None,
    ) -> None:
        self._filter_tier = filter_tier
        self._expanded = expanded
        self._configured = {n: True for n in configured_names}
        self._key_present = dict(key_present)
        self._focus_idx = max(0, focus_idx)
        if flash is not None:
            self._flash = flash
        self._repaint()

    # ---------------------------------------------------- compose
    def compose(self) -> ComposeResult:
        yield Static("", markup=False, classes="providers-chips",
                     id="providers-chips")
        with Vertical(id="providers-scroll", classes="providers-scroll"):
            yield Static("", markup=False, classes="providers-tiers",
                         id="providers-tiers")
        # The universal StatusStrip (screen-level) renders the bottom hints,
        # so no per-panel foot widget is needed.

    def on_mount(self) -> None:
        self._repaint()

    def on_resize(self, event) -> None:  # noqa: N802 — Textual handler name
        """Re-render when the container width changes so rows reflow
        instead of wrapping into stray blocks."""
        width = getattr(event, "size", None)
        width = getattr(width, "width", 0) if width is not None else 0
        if width and width != self._last_width:
            self._repaint()

    # ---------------------------------------------------- rendering
    def _width(self) -> int:
        """Render budget = container width - padding, clamped."""
        w = self._last_width or self.size.width or 0
        if w <= 20:  # not laid out yet (or a smoke-driven bare instance)
            w = DEFAULT_WIDTH
        return max(40, w - 4)

    def _repaint(self) -> None:
        """Render the whole panel from current state."""
        try:
            self._last_width = self.size.width or self._last_width
            self.query_one("#providers-chips", Static).update(
                self._render_chips())
            tiers_text = self._render_tiers()
            self.query_one("#providers-tiers", Static).update(tiers_text)
            # Record the painted line ranges of each provider row so mouse
            # clicks can be mapped back to a row index (see _row_line_index).
            records: list[dict] = []
            idx_so_far = 0
            line_no = 1  # +1: the chips line occupies y=0
            for tier in TIER_ORDER:
                entries = by_tier(tier)  # type: ignore[arg-type]
                if self._filter_tier is not None and tier != self._filter_tier:
                    continue
                line_no += 1  # tier header line
                for entry in entries:
                    rows = 1
                    if self._expanded == entry.name:
                        rows += self._expanded_line_count(entry)
                    records.append({
                        "kind": "row", "idx": idx_so_far,
                        "y0": line_no, "y1": line_no + rows,
                    })
                    line_no += rows
                    idx_so_far += 1
                line_no += 1  # blank separator line after each tier
            self._last_render_rows = records
        except Exception:
            pass  # not yet composed

    # ---------------------------------------------------- chip row
    def _render_chips(self) -> str:
        # Filter order: All, Free, Local, Paid, Custom
        # (Free first to signal our default tier philosophy.)
        chips = []
        active = (self._filter_tier is None)
        if active:
            chips.append(f"{_BRAND}\u25c6 All · {len(ALL_PROVIDERS)}{_RESET}")
        else:
            chips.append(f"{_DIM}\u25c6 All · {len(ALL_PROVIDERS)}{_RESET}")
        for label, tier in (("Free", "free"), ("Local", "local"),
                            ("Paid", "paid"), ("Custom", "custom")):
            count = len(by_tier(tier))  # type: ignore[arg-type]
            if self._filter_tier == tier:
                chips.append(
                    f"{_BRAND}\u25c6 {label} · {count}{_RESET}")
            else:
                chips.append(
                    f"{_DIM}\u25c6 {label} · {count}{_RESET}")
        visible_n = self._visible_count()
        meta = (f"{_FAINT}\u2500\u2500\u2500 {visible_n} visible "
                f"\u2500\u2500\u2500{_RESET}")
        line = "  " + "   ".join(chips) + "   " + meta
        # Crop to the panel budget so a narrow terminal wraps nothing;
        # the meta segment is first to go thanks to its trailing position.
        return reset_at_end(fit_to(line, self._width()))

    def _visible_count(self) -> int:
        if self._filter_tier is None:
            return len(ALL_PROVIDERS)
        return len(by_tier(self._filter_tier))  # type: ignore[arg-type]

    def _expanded_line_count(self, entry) -> int:
        """Lines the expanded pane adds under a provider row (used for
        click-hit-testing). Keep in sync with _render_expanded()."""
        has_auth = entry.env_var is not None
        # top + base URL + model + auth? + status + separator + actions + bottom
        return 7 + (1 if has_auth else 1)

    # ---------------------------------------------------- tier list
    def _render_tiers(self) -> str:
        out: list[str] = []
        idx_so_far = 0
        width = self._width()
        for tier in TIER_ORDER:
            entries = by_tier(tier)  # type: ignore[arg-type]
            if self._filter_tier is not None and tier != self._filter_tier:
                # When a single tier is active, skip divider headers so the
                # list reads continuously.
                continue
            out.append(self._render_tier_header(tier, len(entries), width))
            for entry in entries:
                is_focused = idx_so_far == self._focus_idx
                out.append(self._render_row(entry, is_focused=is_focused,
                                            width=width))
                if self._expanded == entry.name:
                    out.append(self._render_expanded(entry, width))
                idx_so_far += 1
            out.append("")
        return "\n".join(out).rstrip()

    def _render_tier_header(self, tier: str, count: int, width: int) -> str:
        label = f"{TIER_LABEL[tier]}  {count}"
        prefix = f"  {_FAINT}{label}{_RESET}  "
        rule = max(8, width - visible_len(prefix) - 2)
        return (f"  {_FAINT}{label}{_RESET}"
                f"  {_FAINT}{_UL * rule}{_RESET}")

    # ---- mouse support: click a provider row to focus + expand it ----------
    # The rows live in one Static as ANSI text, so clicks are mapped back to
    # the row under the mouse via the same render order used to paint.
    def _row_line_index(self) -> int:
        """Absolute line index of the provider row under self.mouse_y, or -1."""
        rows = self._last_render_rows  # painted line records, see _repaint
        y = self.mouse_y
        if y is None:
            return -1
        for rec in rows:
            if rec["kind"] == "row" and rec["y0"] <= y < rec["y1"]:
                return rec["idx"]
        return -1

    # ---------------------------------------------------- collapsed row
    def _row_status_text(self, entry: ProviderEntry, status) -> str:
        if entry.tier == "local":
            return status.detail if status.state == "ready" else "\u2014 not running"
        present = self._key_present.get(entry.name, False)
        if present:
            return "\u25cf ready · key in keychain"
        return "\u2014 no API key"

    def _render_row(self, entry: ProviderEntry, *, is_focused: bool = False,
                    width: int | None = None) -> str:
        width = width if width is not None else self._width()
        status = status_for(entry)
        st_text = self._row_status_text(entry, status)
        is_open = self._expanded == entry.name
        caret = _CARET_OPEN if is_open else _CARET_CLOSED
        dot = _dot(status.state)
        # Focus bar marker (left rail) — neutral; bright enough to find,
        # quiet enough to scan past.
        focus_bar = f"{_FG}\u2588{_RESET}" if is_focused else " "
        # open rows: brand-colored name; collapsed muted ones when no key
        if is_open:
            name_styled = f"{_BRAND}{entry.display}{_RESET}"
            row_bg = _BG_SURFACE
        elif is_focused:
            name_styled = f"{_BRAND}{entry.display}{_RESET}"
            row_bg = _BG_HOVER
        elif self._key_present.get(entry.name) or status.state == "ready":
            name_styled = f"{_FG}{entry.display}{_RESET}"
            row_bg = ""
        else:
            name_styled = f"{_DIM}{entry.display}{_RESET}"
            row_bg = ""
        # tier tag (one character height)
        tag = f"{_FAINT}[{entry.tier}]{_RESET}"
        left = (f" {focus_bar} {caret} {dot} {name_styled} {tag}")
        left = left.replace(" ", "\u00a0") if False else left  # keep plain spaces
        return reset_at_end(two_columns(left, st_text, width))

    # ---------------------------------------------------- expanded pane
    def _render_expanded(self, entry: ProviderEntry, width: int | None = None) -> str:
        width = width if width is not None else self._width()
        # All pane rows are pre-indented by 2 and fitted to the full width.
        inner = max(24, width - 10)
        top = f"  {_BOX_TL}{_BRAND}{_UL * inner}{_BOX_TR}{_RESET}"
        bottom = f"  {_BOX_BL}{_BRAND}{_UL * inner}{_BOX_BR}{_RESET}"
        bar = _BOX_V

        rows: list[str] = [top]
        # base URL
        rows.append(self._exp_field(bar, "base URL",
                                    entry.base_url or "(set your custom URL)",
                                    width))
        # model — LIVE list when discovery has answered for this provider
        # (cached, filled by SettingsScreen's prewarm worker), otherwise
        # the curated fallback with an honest 'showing defaults' hint.
        live = None
        try:
            from frontend.models_catalog import cached_models
            live = cached_models(entry.name, entry.base_url)
        except Exception:
            live = None
        if live is not None and live.status == "ok" and live.models:
            models_str = "  ".join(live.models[:5])
            if len(live.models) > 5:
                models_str += f"  +{len(live.models) - 5}"
            avail_hint = f"{_FAINT}installed: {models_str}{_RESET}"
        else:
            if entry.models:
                models_str = "  ".join(entry.models[:5])
                if len(entry.models) > 5:
                    models_str += f"  +{len(entry.models) - 5}"
                avail_hint = f"{_FAINT}suggested: {models_str}{_RESET}"
            else:
                models_str = ""
                avail_hint = ""
        if entry.models or (live is not None and live.models):
            rows.append(self._exp_field(bar, "model",
                                        f"\u25be {entry.default_model}",
                                        width,
                                        hint=avail_hint))
        # auth
        if entry.env_var is None:
            auth_field = f"{_OK}none{_RESET}  {_FAINT}[no-key]{_RESET}"
            rows.append(self._exp_field(bar, "auth", auth_field, width))
        else:
            present = self._key_present.get(entry.name, False)
            if present:
                auth_field = (f"{_OK}\u25cf ready · key in keychain{_RESET} "
                              f"{_FAINT}[{entry.env_var}]{_RESET}")
            else:
                auth_field = (f"{_WARN}\u26a0 no key{_RESET}  "
                              f"{_FAINT}[{entry.env_var}]{_RESET}  "
                              f"{_BRAND}press e to connect + paste key{_RESET}")
            rows.append(self._exp_field(bar, "auth", auth_field, width))
        # status / connection
        status = status_for(entry)
        status_color = _OK if status.state == "ready" else _WARN
        rows.append(self._exp_field(bar, "status",
                                    f"{status_color}{status.detail}{_RESET}",
                                    width))
        # separator + actions
        rows.append(f"  {bar} {_DIM}{_UL * max(8, inner - 4)}{_RESET}")
        rows.append(self._exp_field(
            bar, "",
            f"{_DIM}[e connect · Enter collapse · Ctrl+Y remove]{_RESET}",
            width))
        rows.append(bottom)
        return "\n".join(reset_at_end(fit_to(r, width)) for r in rows)

    def _exp_field(self, bar: str, label: str, value: str, width: int,
                   hint: str = "") -> str:
        if hint:
            line = (f"  {bar} {_FAINT}{label:<11}{_RESET} "
                    f"{_FG}{value}{_RESET}  {hint}")
        elif not label:
            line = f"  {bar} {value}"
        else:
            line = (f"  {bar} {_FAINT}{label:<11}{_RESET} "
                    f"{_FG}{value}{_RESET}")
        return fit_to(line, width)


# ----------------------------------------------------------- welcome state
def render_empty_state() -> str:
    """Settings → providers empty state when no providers configured."""
    head = f"{_BRAND}Set up your first provider{_RESET}"
    body = (
        f"\n  {_DIM}Pick a provider to begin. {_OK}Ollama{_DIM} runs locally with zero config.\n"
        f"  {_BRAND}OpenRouter{_DIM} gives one key to 500+ models (free tier rotates daily).\n"
        f"  {_BRAND}Groq{_DIM} is the fastest free cloud inference.\n\n"
        f"  {_BRAND}\u25c6 All · {len(ALL_PROVIDERS)}{_RESET}  "
        f"  {_DIM}\u25c6 Free · {len(by_tier('free'))}{_RESET}  "
        f"  {_DIM}\u25c6 Local · {len(by_tier('local'))}{_RESET}  "
        f"  {_DIM}\u25c6 Paid · {len(by_tier('paid'))}{_RESET}  "
        f"  {_DIM}\u25c6 Custom · {len(by_tier('custom'))}{_RESET}\n\n"
    )
    out = [head, body]
    for entry in recommended():
        if entry.tier == "local":
            tag = "\u25cf recommended · zero config"
            color = _OK
        else:
            tag = "\u25cb recommended"
            color = _BRAND
        caret = _CARET_OPEN if entry.name == "ollama" else _CARET_CLOSED
        out.append(f"  {caret} {_OK}\u25cf{_RESET} "
                   f"{_BRAND}{entry.display}{_RESET}  "
                   f"{_DIM}{entry.tier}{_RESET}  {color}{tag}{_RESET}")
    return "\n".join(out)


# ----------------------------------------------------------- tests
if __name__ == "__main__":
    # Smoke render
    p = ProvidersPanel()
    p.update(filter_tier=None, expanded="ollama",
             configured_names=set(), key_present={})
    print(p._render_chips())
    print()
    print(p._render_tier_header("local", 5, 110))
    print(p._render_row(ALL_PROVIDERS[0]))
    print(p._render_expanded(ALL_PROVIDERS[0], 110))
