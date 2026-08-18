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
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Input, Static

from frontend.providers import (
    ALL_PROVIDERS,
    TIER_LABEL,
    TIER_ORDER,
    ProviderEntry,
    by_tier,
    recommended,
    status_for,
)


# Helper: tiny inline-ANSI helpers so we can compose the panel rows in
# tight, fixed-width strings (matches what the rest of the settings screen
# does — no full CSS layout for these).
_FG = "\x1b[38;2;212;212;212m"
_DIM = "\x1b[38;2;110;120;135m"
_FAINT = "\x1b[38;2;80;88;100m"
_BRAND = "\x1b[1;38;2;140;220;220m"
_OK = "\x1b[38;2;140;210;150m"
_WARN = "\x1b[38;2;230;200;130m"
_ERR = "\x1b[38;2;230;140;140m"
_BG_SURFACE = "\x1b[48;2;22;26;33m"
_BG_HOVER = "\x1b[48;2;30;36;46m"
_RESET = "\x1b[0m"
_UL = "\u2500"  # ─
_ARROW = "\u2192"  # →
_BULLET = "\u2022"  # •
_CARET_OPEN = "\u25be"  # ▾
_CARET_CLOSED = "\u25b8"  # ▸


@dataclass
class ProviderRowState:
    """Per-row runtime snapshot — read from runtime probes."""
    entry: ProviderEntry
    state: str       # ready | key-loaded | auth-missing | not-running | etc
    detail: str
    configured: bool # user has explicitly added it to config.json
    key_present: bool


def _wid(s: str, n: int) -> str:
    """Widen a string with spaces to n columns (auto-strips ANSI)."""
    visible = re.sub(r"\x1b\[[0-9;]*m", "", s)
    pad = max(0, n - len(visible))
    return s + " " * pad


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

    # ---------------------------------------------------- rendering
    def _repaint(self) -> None:
        """Render the whole panel from current state."""
        try:
            self.query_one("#providers-chips", Static).update(
                self._render_chips())
            self.query_one("#providers-tiers", Static).update(
                self._render_tiers())
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
        total = len(ALL_PROVIDERS)
        meta = f"{_FAINT}\u2500\u2500\u2500 {visible_n} visible \u2500\u2500\u2500 {_RESET}"
        line = "  " + "  ".join(chips) + "  " + meta
        # Pad to a stable width so the next rows align
        return _wid(line, 110)

    def _visible_count(self) -> int:
        if self._filter_tier is None:
            return len(ALL_PROVIDERS)
        return len(by_tier(self._filter_tier))  # type: ignore[arg-type]

    # ---------------------------------------------------- tier list
    def _render_tiers(self) -> str:
        out: list[str] = []
        idx_so_far = 0
        for tier in TIER_ORDER:
            entries = by_tier(tier)  # type: ignore[arg-type]
            if self._filter_tier is not None and tier != self._filter_tier:
                # When a single tier is active, skip divider headers so the
                # list reads continuously.
                continue
            out.append(self._render_tier_header(tier, len(entries)))
            for entry in entries:
                is_focused = idx_so_far == self._focus_idx
                out.append(self._render_row(entry, is_focused=is_focused))
                if self._expanded == entry.name:
                    out.append(self._render_expanded(entry))
                idx_so_far += 1
            out.append("")
        return "\n".join(out).rstrip()

    def _render_tier_header(self, tier: str, count: int) -> str:
        return (
            f"{_FAINT}{TIER_LABEL[tier]}  {count}"
            f"{_RESET}"
            + " " * max(1, 110 - len(TIER_LABEL[tier]) - 4)
            + f"{_FAINT}{_UL * 60}{_RESET}"
        )

    # ---------------------------------------------------- collapsed row
    def _render_row(self, entry: ProviderEntry, *, is_focused: bool = False) -> str:
        status = status_for(entry)
        if entry.tier == "local":
            running = status.state == "ready"
            st_text = status.detail if running else "— not running"
        else:
            present = self._key_present.get(entry.name, False)
            if present:
                st_text = "● ready · key in keychain"
            else:
                st_text = "— no API key"
        is_open = self._expanded == entry.name
        caret = _CARET_OPEN if is_open else _CARET_CLOSED
        dot = _dot(status.state)
        name_part = entry.display
        # Focus bar marker (left rail)
        focus_bar = f"{_BRAND}\u2588{_RESET}" if is_focused else " "
        # open rows: brand-colored name; collapsed muted ones when no key
        if is_open:
            name_styled = f"{_BRAND}{name_part}{_RESET}"
            row_bg = _BG_SURFACE
        elif is_focused:
            name_styled = f"{_BRAND}{name_part}{_RESET}"
            row_bg = _BG_HOVER
        elif self._key_present.get(entry.name) or status.state == "ready":
            name_styled = f"{_FG}{name_part}{_RESET}"
            row_bg = ""
        else:
            name_styled = f"{_DIM}{name_part}{_RESET}"
            row_bg = ""
        # tier tag (one character height)
        tag = f"{_FAINT}[{entry.tier}]{_RESET}"
        # row line
        left = (f"{row_bg}{focus_bar} {caret} {row_bg}{dot} {row_bg}"
                f"{name_styled}{row_bg} {tag}{row_bg}")
        right = f"{_DIM}{st_text}{_RESET}"
        gap = " " * max(1, 100 - len(re.sub(r"\x1b\[[0-9;]*m", "", left))
                          - len(re.sub(r"\x1b\[[0-9;]*m", "", right)))
        return left + gap + right + _RESET

    # ---------------------------------------------------- expanded pane
    def _render_expanded(self, entry: ProviderEntry) -> str:
        bar = f"{_BRAND}|{_RESET}"
        box_open = f"{_BRAND}\u256d{_UL * 60}\u256e{_RESET}"
        box_close = f"{_BRAND}\u256f{_UL * 60}\u256d{_RESET}"[0] + f"{_UL * 60}\u2570{_RESET}"

        rows: list[str] = []
        rows.append(box_open)
        # base URL
        rows.append(self._exp_field(bar, "base URL",
                                    entry.base_url or "(set your custom URL)"))
        # model
        if entry.models:
            models_str = "  ".join(entry.models[:5])
            if len(entry.models) > 5:
                models_str += f"  +{len(entry.models) - 5}"
            rows.append(self._exp_field(bar, "model",
                                        f"\u25be {entry.default_model}",
                                        hint=f"{_FAINT}  available: {models_str}{_RESET}"))
        # auth
        if entry.env_var is None:
            auth_field = (f"{_OK}none{_RESET}  {_FAINT}[no-key]{_RESET}")
            rows.append(self._exp_field(bar, "auth", auth_field))
        else:
            present = self._key_present.get(entry.name, False)
            if present:
                auth_field = (f"{_OK}\u25cf ready · key in keychain{_RESET} "
                              f"{_FAINT}[{entry.env_var}]{_RESET}")
                rows.append(self._exp_field(bar, "auth", auth_field))
            else:
                auth_field = (f"{_WARN}\u26a0 no key{_RESET}  "
                              f"{_FAINT}[{entry.env_var}]{_RESET}  "
                              f"{_BRAND}+ add key{_RESET}")
                rows.append(self._exp_field(bar, "auth", auth_field))
        # status / connection
        status = status_for(entry)
        if status.state == "ready":
            rows.append(self._exp_field(bar, "status",
                                        f"{_OK}{status.detail}{_RESET}",
                                        ))
        else:
            rows.append(self._exp_field(bar, "status",
                                        f"{_WARN}{status.detail}{_RESET}"))
        # separator + buttons
        rows.append(f"  {_DIM}{_UL * 60}{_RESET}")
        rows.append(self._exp_field(
            bar, "",
            f"{_DIM}[Test]{_RESET}   {_DIM}[Reset]{_RESET}   {_DIM}[Save]{_RESET}"))
        rows.append(box_close)
        return "  " + "\n  ".join(rows)

    def _exp_field(self, bar: str, label: str, value: str,
                   hint: str = "") -> str:
        if hint:
            return (f"  {bar} {_FAINT}{label:<11}{_RESET} "
                    f"{_FG}{value}{_RESET}  {hint}")
        if not label:
            return f"  {bar} {value}"
        return (f"  {bar} {_FAINT}{label:<11}{_RESET} "
                f"{_FG}{value}{_RESET}")


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
            tag = "● recommended · zero config"
            color = _OK
        else:
            tag = "○ recommended"
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
    print(p._render_tier_header("local", 5))
    print(p._render_row(ALL_PROVIDERS[0]))
    print(p._render_expanded(ALL_PROVIDERS[0]))
