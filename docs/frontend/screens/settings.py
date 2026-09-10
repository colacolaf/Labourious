"""
settings.py — the Settings modal.

One screen, six sections, configured-only rendering, atomic save.

THE SETTINGS MODEL
==================

Six sections live in this screen (each in the left rail):

  providers     — only configured providers shown; + add opens picker
  default       — single inline input for default_model
  per-agent     — only overrides shown; + add opens picker (agent + model)
  hybrid        — only paid_for agents shown; + add opens picker (agent)
  connectors    — only configured connectors shown; + add opens picker
  defaults      — depth (STANDARD/DEEP) + compressed (true/false)

The Picker is NOT a separate screen — it swaps in for the body pane.
This honors the project's "no useless pages" rule.

The file ~/.labourious/config.json is canonical. Writes are atomic
(write-to-tmp + rename). Every edit auto-saves on Tab/Enter; Ctrl+S
closes; Esc returns to chat without losing unsaved work (because each
edit is auto-saved).
"""

from __future__ import annotations

from dataclasses import replace

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static

from frontend.config_io import (
    Config,
    ConfigValidationError,
    KNOWN_CONNECTORS,
    KNOWN_PROVIDERS,
    ConnectorConfig,
    ProviderConfig,
    cfg_path_str,
    health_check,
    load_config,
    mtime_str,
    save_config,
    validate_field as _validate_field_io,
)
from frontend.widgets.section_card import SectionCard
from frontend.widgets.picker_overlay import PickerItem, PickerOverlay
from frontend.widgets.setting_row import render_row as _render_row
from frontend.widgets.inline_editor import (
    InlineTextEditor,
    InlineToggleEditor,
    TextEditCommitted,
    TextEditReverted,
    ToggleEditCommitted,
    ToggleEditDone,
)
from frontend.widgets.providers_panel import (
    ProvidersPanel, render_empty_state,
)
from frontend.widgets.omniroute_setup import OmniRouteSetup
from frontend.widgets.provider_setup import ProviderSetup
from frontend.keys_storage import get_key, set_key, delete_key, key_present
from frontend.models_catalog import fetch_models_result
from frontend.utils.ansi import to_text
from frontend.providers import (
    ALL_PROVIDERS, by_name, by_tier, TIER_ORDER, total_count,
    status_for, ProviderEntry,
)


# Six sections in canonical order. The order matches PROTOCOL.md Appendix A.
SECTIONS = ("providers", "default", "per-agent", "hybrid", "connectors", "defaults", "streaming")

# Filter chip order matches the L3 preview (Free first → recommendation).
_FILTER_CHIPS: tuple[tuple[str, str | None], ...] = (
    ("All", None),
    ("Free", "free"),
    ("Local", "local"),
    ("Paid", "paid"),
    ("Custom", "custom"),
)
_CHIP_BY_KEY: dict[str | None, str] = {
    None: "All", "free": "Free", "local": "Local",
    "paid": "Paid", "custom": "Custom",
}

# Each editable section's inline-edit row schema. Order matters: rows
# are walked in tuple order. A row is ("text", "model") or
# ("toggle", "depth" | "compressed").
_EDITABLE_ROWS: dict[str, tuple[tuple[str, str], ...]] = {
    "default":   (("text", "model"),),
    "per-agent": (("text", "model"),),
    "defaults":  (("toggle", "depth"), ("toggle", "compressed")),
    "streaming": (("toggle", "chunks"), ("text", "typewriter_ms")),
}

# Fallback preset chips shown beneath the text editor input when no live
# model list is available. The ollama entries are replaced by REAL models
# discovered from the local server (GET /api/tags) when it responds —
# see SettingsScreen._model_presets().
_MODEL_PRESETS_STATIC = [
    "anthropic/claude-sonnet-4-5",
    "groq/llama-3.3-70b-versatile",
    "openrouter/auto",
]


class SettingsScreen(Screen):
    """The Settings modal.

    Push this on top of ChatScreen with self.app.push_screen(SettingsScreen()).
    """

    BINDINGS = [
        Binding("ctrl+s",    "save_close",   "Save & close"),
        Binding("escape",     "back_chat",    "Back to chat"),
        Binding("enter",      "confirm",      "Confirm"),
        Binding("ctrl+d",     "remove",       "Remove"),
        Binding("ctrl+n",     "open_picker",  "+ Add"),
        # ctrl+o / ctrl+y mirror ctrl+n / ctrl+d because in real terminals the
        # ctrl+n / ctrl+p Readline-style keys (and some tmux configs) eat them.
        Binding("ctrl+o",     "open_picker",  "+ Add"),
        Binding("ctrl+y",     "remove",       "Remove"),
        Binding("e",          "start_edit",   "Edit"),
        Binding("tab",        "next_filter",  "Next chip"),
        Binding("shift+tab",  "prev_filter",  "Prev chip"),
    ]

    # ---------------------------------------------------------- compose
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._cfg: Config = load_config()
        self._health: dict[str, str] = health_check(self._cfg)
        self._rail_index: int = 0                  # selected section
        self._picker_open: bool = False            # are we in 'add' mode?
        self._picker_section: str | None = None    # which section we're adding to
        self._picker_overlay: PickerOverlay | None = None
        self._row_lines_cache: list[str] = []      # cached ANSI for current section
        self._row_index: int = 0                   # selected row in current card
        # Two-scope navigation: "rail" (left column) vs "pane" (body card).
        # ←/→ switch scopes; ↑/↓ move within the active scope.
        self._nav_scope: str = "rail"
        # Inline-edit state
        self._editing: bool = False                # editor is mounted?
        self._edit_section: str | None = None      # which section we're editing
        self._edit_row: int = 0                    # which row within that section
        # Providers L3 state (only valid when section == "providers")
        self._provider_filter: str | None = None   # current chip key
        self._provider_expanded: str | None = None # current expanded provider name
        self._provider_focus_idx: int = 0          # focused row within visible list
        self._omniroute_setup_open: bool = False
        self._omniroute_setup: OmniRouteSetup | None = None
        self._provider_setup_open: bool = False
        self._provider_setup: ProviderSetup | None = None
        self._provider_setup_entry: ProviderEntry | None = None
        self._key_cache: dict[str, bool] | None = None  # built lazily; see _key_present_map

    def compose(self) -> ComposeResult:
        # Header strip
        yield Static("", markup=False, classes="settings-head", id="settings-head")
        # Body: rail + main panel
        with Horizontal(id="settings-body"):
            with Vertical(id="settings-rail", classes="settings-rail"):
                for s in SECTIONS:
                    yield Static(
                        self._rail_label(s),
                        markup=False,
                        classes="rail-item" + (" sel" if s == SECTIONS[0] else ""),
                        id=f"rail-{s}",
                    )
            with Vertical(id="settings-main"):
                # The body is mounted by on_mount → _swap_card(): the providers
                # section gets the L3 ProvidersPanel, every other section gets
                # a SectionCard. (Mounting the card here meant that on open the
                # providers screen showed the legacy configured-only card and
                # the full catalog panel only appeared after nav away+back.)
                pass
        # Footer strip — universal StatusStrip, screen-aware key hints.
        from frontend.widgets.status_strip import StatusStrip   # type: ignore
        yield StatusStrip()

    # ---------------------------------------------------------- L3 providers helpers
    def _visible_providers(self) -> tuple[ProviderEntry, ...]:
        if self._provider_filter is None:
            return ALL_PROVIDERS
        return by_tier(self._provider_filter)  # type: ignore[arg-type]

    def _refresh_providers_panel(self, *, flash: str | None = None) -> None:
        """Re-paint the L3 panel from current state."""
        try:
            panel = self.query_one(ProvidersPanel)
        except Exception:
            return  # not mounted yet (e.g., another section active)
        visible = self._visible_providers()
        # Clamp focus to the visible list so ↓ past the last row can't
        # leave the highlight parked on a nonexistent index.
        focus_idx = min(self._provider_focus_idx, max(0, len(visible) - 1))
        panel.update(
            filter_tier=self._provider_filter,
            expanded=self._provider_expanded,
            configured_names=set(self._cfg.providers.keys()),
            key_present=self._key_present_map(),
            focus_idx=focus_idx,
            flash=flash,
        )
        self._update_strip()

    def _key_present_map(self) -> dict[str, bool]:
        """One keychain lookup per provider, cached per screen instance.

        key_present() used to be called for all ~20 providers on every
        repaint; on macOS each call round-trips the Security agent, which
        made the panel visibly sluggish (and popped keychain permission
        dialogs). keys_storage now caches reads, and this map is built
        once per Settings open.
        """
        if self._key_cache is None:
            self._key_cache = {
                entry.name: key_present(entry.name) for entry in ALL_PROVIDERS
            }
        return self._key_cache

    def _mount_providers_panel(self) -> None:
        """Mount the L3 panel inside #settings-main, replacing any card."""
        try:
            main = self.query_one("#settings-main")
            main.remove_children()
        except Exception:
            pass
        panel = ProvidersPanel(id="settings-providers-panel")
        try:
            main.mount(panel)
        except Exception:
            pass
        self._refresh_providers_panel()
        # The strip picks L3_PROVIDERS_STRIP on update_for() if rail_index==0
        self._update_strip()

    def _update_strip(self) -> None:
        """Refresh the bottom-strip bindings to match current screen state."""
        from frontend.widgets.status_strip import StatusStrip as _SS
        try:
            self.query_one(_SS).update_for(self)
        except Exception:
            pass

    def on_mount(self) -> None:
        self._refresh_head()
        self._refresh_rail_selection()
        # Mount the right body for the initial section (providers → L3 panel).
        self._swap_card(SECTIONS[self._rail_index])
        # _refresh_foot() still updates the legacy per-screen foot Static (if
        # present) — the new StatusStrip below now drives the universal strip.
        self._refresh_foot()
        from frontend.widgets.status_strip import StatusStrip as _SS
        try:
            self.query_one(_SS).update_for(self)
        except Exception:
            pass
        # Prewarm the live model cache in a worker thread so preset chips
        # and the provider panel show REAL installed models without ever
        # blocking the UI on a network call.
        self.run_worker(self._prewarm_models(), exclusive=False,
                        group="prewarm-models", exit_on_error=False)

    async def _prewarm_models(self) -> None:
        import asyncio
        try:
            await asyncio.to_thread(fetch_models_result, "ollama")
        except Exception:
            pass  # discovery failures are fine — curated lists remain

    def _model_presets(self) -> list[str]:
        """Preset chips for the model text editor.

        Live ollama models first (fetched in a worker on open; the cache
        makes this call instant), then a couple of cloud defaults. Falls
        back to the static list when ollama is down."""
        try:
            result = fetch_models_result("ollama")
        except Exception:
            result = None
        presets: list[str] = []
        if result is not None and result.status == "ok":
            presets.extend(f"ollama/{m}" for m in result.models[:4])
        else:
            presets.append("ollama/llama3.2:3b")
        presets.extend(_MODEL_PRESETS_STATIC)
        return presets

    # ---------------------------------------------------------- rail
    def _rail_label(self, section: str) -> str:
        # No ANSI wrap; just plain — selection is done by .sel class
        return section

    def action_rail_next(self) -> None:
        if (self._picker_open or self._omniroute_setup_open
                or self._provider_setup_open):
            return  # ignore while picker is up
        self._rail_index = (self._rail_index + 1) % len(SECTIONS)
        self._refresh_rail_selection()
        self._swap_card(SECTIONS[self._rail_index])
        self._refresh_head()
        self._update_strip()

    def action_rail_prev(self) -> None:
        if (self._picker_open or self._omniroute_setup_open
                or self._provider_setup_open):
            return
        self._rail_index = (self._rail_index - 1) % len(SECTIONS)
        self._refresh_rail_selection()
        self._swap_card(SECTIONS[self._rail_index])
        self._refresh_head()
        self._update_strip()

    # ---------------------------------------------------------- two-scope nav
    # RAIL scope: ↑/↓ walk the left section column.
    # PANE scope: ↑/↓ walk the rows of the body card (providers entries,
    # config rows, editable fields). → enters the pane, ← returns to rail.
    # Mouse clicks set the scope directly (click rail = rail, click pane = pane).
    def _enter_pane(self) -> None:
        """→ from the rail: focus the section's body pane."""
        if self._picker_open or self._editing \
                or self._omniroute_setup_open or self._provider_setup_open:
            return
        self._nav_scope = "pane"
        self._refresh_rail_selection()
        self._update_strip()

    def _leave_pane(self) -> None:
        """← from the pane: back to the section rail."""
        self._nav_scope = "rail"
        self._refresh_rail_selection()
        self._update_strip()

    def _pane_rows(self) -> int:
        """How many focusable rows the current section's pane has."""
        section = SECTIONS[self._rail_index]
        if section == "providers":
            return len(self._visible_providers())
        if section == "per-agent":
            return max(1, len(self._cfg.per_agent_model))
        if section == "hybrid":
            return max(1, len(self._cfg.hybrid_paid_for))
        if section == "connectors":
            return max(1, len(self._cfg.connectors))
        if section == "default":
            return 1
        if section == "defaults":
            return 2
        if section == "streaming":
            return 2
        return 1

    def action_pane_next(self) -> None:
        """↓ inside the pane: advance the pane's row cursor."""
        if self._picker_open or self._editing \
                or self._omniroute_setup_open or self._provider_setup_open:
            return
        n = self._pane_rows()
        section = SECTIONS[self._rail_index]
        if section == "providers":
            self.action_provider_focus_next()
            return
        self._row_index = (self._row_index + 1) % n
        self._render_current_section()

    def action_pane_prev(self) -> None:
        """↑ inside the pane: rewind the pane's row cursor."""
        if self._picker_open or self._editing \
                or self._omniroute_setup_open or self._provider_setup_open:
            return
        n = self._pane_rows()
        section = SECTIONS[self._rail_index]
        if section == "providers":
            self.action_provider_focus_prev()
            return
        self._row_index = (self._row_index - 1) % n
        self._render_current_section()

    # ---------------------------------------------------------- L3 chip navigation
    def action_next_filter(self) -> None:
        """`tab` key cycles the chip filter when on the providers section."""
        if (self._picker_open or self._editing
                or self._omniroute_setup_open or self._provider_setup_open):
            return
        if SECTIONS[self._rail_index] != "providers":
            return
        idx = next(
            (i for i, (_, k) in enumerate(_FILTER_CHIPS) if k == self._provider_filter),
            0,
        )
        new_idx = (idx + 1) % len(_FILTER_CHIPS)
        self._provider_filter = _FILTER_CHIPS[new_idx][1]
        # Collapsing everything when filter changes
        self._provider_expanded = None
        self._provider_focus_idx = 0
        self._refresh_providers_panel()

    def action_prev_filter(self) -> None:
        """`shift+tab` cycles the chip filter backward."""
        if (self._picker_open or self._editing
                or self._omniroute_setup_open or self._provider_setup_open):
            return
        if SECTIONS[self._rail_index] != "providers":
            return
        idx = next(
            (i for i, (_, k) in enumerate(_FILTER_CHIPS) if k == self._provider_filter),
            0,
        )
        new_idx = (idx - 1) % len(_FILTER_CHIPS)
        self._provider_filter = _FILTER_CHIPS[new_idx][1]
        self._provider_expanded = None
        self._provider_focus_idx = 0
        self._refresh_providers_panel()

    def action_toggle_expand(self) -> None:
        """Enter on the providers section toggles expand on the focused row."""
        if (self._picker_open or self._editing
                or self._omniroute_setup_open or self._provider_setup_open):
            return
        if SECTIONS[self._rail_index] != "providers":
            return
        visible = self._visible_providers()
        if not visible:
            return
        idx = max(0, min(self._provider_focus_idx, len(visible) - 1))
        entry = visible[idx]
        if self._provider_expanded == entry.name:
            self._provider_expanded = None  # collapse
        else:
            self._provider_expanded = entry.name
        self._refresh_providers_panel(flash=None)

    def action_provider_focus_next(self) -> None:
        if (self._picker_open or self._editing
                or self._omniroute_setup_open or self._provider_setup_open):
            return
        if SECTIONS[self._rail_index] != "providers":
            return
        visible = self._visible_providers()
        if not visible:
            return
        self._provider_focus_idx = (self._provider_focus_idx + 1) % len(visible)
        self._refresh_providers_panel()

    def action_provider_focus_prev(self) -> None:
        if (self._picker_open or self._editing
                or self._omniroute_setup_open or self._provider_setup_open):
            return
        if SECTIONS[self._rail_index] != "providers":
            return
        visible = self._visible_providers()
        if not visible:
            return
        self._provider_focus_idx = (self._provider_focus_idx - 1) % len(visible)
        self._refresh_providers_panel()

    def _refresh_rail_selection(self) -> None:
        pane = self._nav_scope == "pane"
        for i, s in enumerate(SECTIONS):
            try:
                w = self.query_one(f"#rail-{s}", Static)
                # Selected rail item dims when the pane has focus — the
                # section is still active but navigation lives in the pane.
                cls = "rail-item"
                if i == self._rail_index:
                    cls += " sel" if not pane else " sel-pane"
                w.set_classes(cls)
            except Exception:
                pass

    # ---------------------------------------------------------- mouse support
    # Every settings surface is click-targetable: rail items switch
    # sections, provider rows select/expand, card rows select, +add opens
    # the picker. Handlers live here; rows identify themselves by id.
    def on_click(self, event) -> None:  # noqa: N802 — Textual handler name
        widget = event.widget
        wid = getattr(widget, "id", None)
        # 1) Rail items — click switches section (scope stays on rail).
        if wid and str(wid).startswith("rail-"):
            section = str(wid)[5:]
            if section in SECTIONS:
                self._nav_scope = "rail"
                self._rail_index = SECTIONS.index(section)
                self._refresh_rail_selection()
                self._swap_card(section)
                self._refresh_head()
                self._update_strip()
                event.stop()
            return
        # 2) Provider rows — the panel is one ANSI-painted Static, so map
        # the click position back to a row index via the panel's paint
        # records (works whichever descendant was clicked). The absolute
        # screen Y rides on the event; Widget has no mouse_y in Textual 8
        # (that AttributeError was the crash on every panel click).
        target = widget
        while target is not None and target is not self:
            if isinstance(target, ProvidersPanel):
                idx = target._row_line_index(event.screen_y)
                if idx >= 0:
                    self._nav_scope = "pane"
                    self._provider_focus_idx = idx
                    self._refresh_providers_panel()
                    # Second click on the focused row expands/collapses it.
                    if target._last_click_idx == idx:
                        self.action_toggle_expand()
                        target._last_click_idx = None
                    else:
                        target._last_click_idx = idx
                    event.stop()
                return
            target = target.parent
        # 3) '+ add' rows inside cards post SectionCard.AddClicked (bubbles
        #    to the screen's @on handler) — nothing to do here.
        # 4) Card clicks generally: enter the pane scope so ↑/↓ move rows.
        try:
            main = self.query_one("#settings-main")
        except Exception:
            return
        pane_widget = widget
        in_pane = False
        while pane_widget is not None:
            if pane_widget is main:
                in_pane = True
                break
            pane_widget = pane_widget.parent
        if in_pane:
            self._nav_scope = "pane"
            self._refresh_rail_selection()
            event.stop()

    # ---------------------------------------------------------- sections
    def _section_meta(self, section: str) -> str:
        if section == "providers":
            chip = _CHIP_BY_KEY.get(self._provider_filter, "All")
            n_visible = len(self._visible_providers())
            return f"{chip} · {n_visible} visible · {total_count()} total"
        if section == "default":
            return f"current: {self._cfg.default_model}"
        if section == "per-agent":
            n = len(self._cfg.per_agent_model)
            return f"{n} override{'s' if n != 1 else ''}"
        if section == "hybrid":
            n = len(self._cfg.hybrid_paid_for)
            return f"{n} paid-for agent{'s' if n != 1 else ''}"
        if section == "connectors":
            n = len(self._cfg.connectors)
            return f"{n} configured"
        if section == "defaults":
            return f"depth {self._cfg.defaults_depth} · compressed {self._cfg.defaults_compressed}"
        return ""

    def _swap_card(self, section: str) -> None:
        # Replace the current SectionCard with one for the new section.
        try:
            main = self.query_one("#settings-main")
        except Exception:
            return
        try:
            main.remove_children()  # clears only children of this container
        except Exception:
            pass
        # The "providers" section gets the L3 panel; others get SectionCard.
        if section == "providers":
            self._mount_providers_panel()
            return
        try:
            card = SectionCard(
                title=section,
                meta=self._section_meta(section),
            )
            # Render from the card's own on_mount (children composed by
            # then) — call_after_refresh from the screen raced the async
            # compose and produced empty cards.
            card.on_render = self._render_current_section
            main.mount(card)
        except Exception:
            pass
        self._update_strip()

    def _render_current_section(self) -> None:
        section = SECTIONS[self._rail_index]
        try:
            card = self.query_one(SectionCard)
            body = card.body()
            if body is None:
                # The card's RichLog body is composed one refresh after the
                # card mounts (Textual composes children asynchronously).
                # Retry on the next refresh instead of giving up — otherwise
                # rail-navigated sections rendered an empty card.
                self.call_after_refresh(self._render_current_section)
                return
        except Exception:
            # No SectionCard at all (e.g. the providers L3 panel is mounted
            # instead) — nothing to render into.
            return

        # Render via body.write(); body.clear() resets the log
        try:
            body.clear()
            card._add_row_lines = set()  # stale '+add' hit-test lines go too
        except Exception:
            pass

        if section == "providers":
            self._render_providers(card)
        elif section == "default":
            self._render_default(card)
        elif section == "per-agent":
            self._render_per_agent(card)
        elif section == "hybrid":
            self._render_hybrid(card)
        elif section == "connectors":
            self._render_connectors(card)
        elif section == "defaults":
            self._render_defaults(card)
        elif section == "streaming":
            self._render_streaming(card)

    # ---------------------------------------------------------- per-section renders
    def _render_providers(self, card: SectionCard) -> None:
        """Legacy configured-only view. Kept for _render_current_section_into
        (post-edit re-render), but never used as the initial providers body —
        on_mount mounts the full L3 ProvidersPanel instead.\n\n        Rendering the empty-catalog hint here made it look like the
        catalog was broken on first open (the card showed 'No providers
        configured' even though the catalog has 20 entries)."""
        body = card.body()
        if body is None:
            return
        body.clear()

        if not self._cfg.providers:
            body.write("\x1b[38;2;110;120;135m  No providers configured — the full catalog is the default view.\x1b[0m")
            body.write("")
            self._render_add_row(card, "+ add provider", "groq · openrouter · openai · google · mistral · cohere")
            return

        i = 0
        for name, p in self._cfg.providers.items():
            detail = p.api_key_env if p.api_key_env else "(local)"
            health = self._health.get(f"provider:{name}", "ok")
            if health == "local":
                health = "local"
            body.write(_render_row(name=name, detail=detail, health=health))
            i += 1
        body.write("")
        self._render_add_row(card, "+ add provider", "groq · openrouter · openai · google · mistral · cohere")

    def _render_default(self, card: SectionCard) -> None:
        body = card.body()
        body.clear()
        # Single editable row + edit hint.
        body.write(_render_row(name="default", detail=self._cfg.default_model,
                               health="set", removable=False))
        body.write("")
        body.write("\x1b[38;2;110;120;135m   \u23af press \x1b[1;38;2;140;220;220me"
                   "\x1b[0m\x1b[38;2;110;120;135m or \x1b[1;38;2;140;220;220m\u23ce"
                   "\x1b[0m\x1b[38;2;110;120;135m to edit this value\x1b[0m")
        body.write("")
        body.write("\x1b[38;2;110;120;135m   Examples: "
                   "\x1b[38;2;160;165;175mollama/llama3.3:70b"
                   "\x1b[38;2;110;120;135m  \u00b7  "
                   "\x1b[38;2;160;165;175manthropic/claude-sonnet-4-5"
                   "\x1b[38;2;110;120;135m  \u00b7  "
                   "\x1b[38;2;160;165;175mgroq/llama-3.3-70b-versatile"
                   "\x1b[38;2;110;120;135m  \u00b7  "
                   "\x1b[38;2;160;165;175mopenrouter/auto"
                   "\x1b[0m")

    def _render_per_agent(self, card: SectionCard) -> None:
        body = card.body()
        body.clear()
        if not self._cfg.per_agent_model:
            body.write("\x1b[38;2;110;120;135m  No per-agent overrides. Default applies to all agents.\x1b[0m")
            body.write("")
            self._render_add_row(card, "+ add override",
                                 "orchestrator · senior-analyst · forensic-accounting · devils-advocate · final-report")
            return
        for agent, mid in self._cfg.per_agent_model.items():
            detail = f"\u2192  {mid}"
            body.write(_render_row(name=agent, detail=detail, health="set"))
        body.write("")
        body.write("\x1b[38;2;110;120;135m   \u23af press \x1b[1;38;2;140;220;220me"
                   "\x1b[0m\x1b[38;2;110;120;135m or \x1b[1;38;2;140;220;220m\u23ce"
                   "\x1b[0m\x1b[38;2;110;120;135m to edit \u00b7 "
                   "\x1b[1;38;2;140;220;220mtab\x1b[0m"
                   "\x1b[38;2;110;120;135m to advance to the next override\x1b[0m")
        body.write("")
        self._render_add_row(card, "+ add override",
                             "orchestrator · senior-analyst · forensic-accounting · devils-advocate · final-report")

    def _render_hybrid(self, card: SectionCard) -> None:
        body = card.body()
        body.clear()
        body.write("\x1b[38;2;160;165;175m  Agents running on a paid model:\x1b[0m")
        body.write("")
        if not self._cfg.hybrid_paid_for:
            body.write("\x1b[38;2;110;120;135m  No paid-for agents. Default model runs every agent.\x1b[0m")
        else:
            for agent in self._cfg.hybrid_paid_for:
                mid = self._cfg.per_agent_model.get(agent, self._cfg.default_model)
                body.write(_render_row(name=agent, detail=f"\u2192  {mid}", health="set", removable=False))
        body.write("")
        self._render_add_row(card, "+ add agent", "orchestrator · senior-analyst · forensic-accounting · devils-advocate · final-report")

    def _render_connectors(self, card: SectionCard) -> None:
        from frontend.connectors_catalog import by_name, TIER_LABEL  # type: ignore
        body = card.body()
        body.clear()
        # Render-only handlers for side-channel indicators.
        def _key_chip(entry) -> str:
            if entry.keyless or entry.key_env is None:
                return "\x1b[38;2;140;210;150mkeyless\x1b[0m"
            return "\x1b[38;2;230;200;130m$" + entry.key_env + "\x1b[0m"
        # Empty state — surface the MVP-5 count to invite first-run setup.
        if not self._cfg.connectors:
            from frontend.connectors_catalog import recommended  # type: ignore
            n_rec = len(recommended())
            body.write(
                "\x1b[38;2;110;120;135m  No connectors configured — "
                f"{n_rec} ship on by default. Press \x1b[1;38;2;140;220;220m"
                "Ctrl+O\x1b[0m\x1b[38;2;110;120;135m below, then "
                "\x1b[1;38;2;140;220;220m↑/↓\x1b[0m\x1b[38;2;110;120;135m "
                "to pick.\x1b[0m"
            )
            body.write("")
            self._render_add_row(card, "+ add connector",
                                 "sec_edgar · quotes · transcripts · insider · 13F · …")
            return
        # One row per configured connector, with the catalog's long label as
        # the help text instead of the raw provider name (the old render showed
        # `"provider": "edgar_rest"` — meaningless to users).
        for name, c in self._cfg.connectors.items():
            entry = by_name(name)
            long_label = entry.label if entry else c.provider
            star = "\x1b[1;38;2;140;220;220m\u2605\x1b[0m " if (entry and entry.recommended) else ""
            key_text = _key_chip(entry) if entry else ""
            detail = f"{star}{long_label} \u00b7 {key_text}"
            health = self._health.get(f"connector:{name}", "ok")
            body.write(_render_row(name=name, detail=detail, health=health))
        body.write("")
        self._render_add_row(card, "+ add connector",
                             "sec_edgar · quotes · transcripts · insider · 13F · …")

    def _render_streaming(self, card: SectionCard) -> None:
        body = card.body()
        body.clear()
        # Two editable rows: stream_chunks (toggle), typewriter_ms (text).
        # The toggle is laid out like defaults_depth / defaults_compressed for muscle-memory parity.
        body.write("\x1b[38;2;110;120;135m   chunks\x1b[0m        "
                   + "\x1b[1;38;2;140;220;220m│\x1b[0m"
                   + "\x1b[48;2;26;32;38m\x1b[38;2;212;212;212m "
                   + ("true" if self._cfg.stream_chunks else "false")
                   + " \x1b[0m\x1b[0m"
                   + "    \x1b[38;2;110;120;135m"
                   + ("false" if self._cfg.stream_chunks else "true")
                   + "\x1b[0m")
        body.write("")
        # Typewriter delay (ms) — 0 means "no artificial delay" (provider speed wins).
        body.write("\x1b[38;2;110;120;135m   typewriter_ms\x1b[0m "
                   + "\x1b[1;38;2;140;220;220m│\x1b[0m"
                   + "\x1b[48;2;26;32;38m\x1b[38;2;212;212;212m "
                   + str(self._cfg.stream_typewriter_ms) + " ms \x1b[0m\x1b[0m"
                   + "    \x1b[38;2;110;120;135m0 = off · 80 ≈ human typing speed\x1b[0m")
        body.write("")
        body.write("\x1b[38;2;110;120;135m   \u23af press \x1b[1;38;2;140;220;220me"
                   "\x1b[0m\x1b[38;2;110;120;135m or \x1b[1;38;2;140;220;220m\u23ce"
                   "\x1b[0m\x1b[38;2;110;120;135m to edit · toggles flip, "
                   "typewriter_ms is a number 0..500\x1b[0m")

    def _render_defaults(self, card: SectionCard) -> None:
        body = card.body()
        body.clear()
        # Two editable rows + edit hint.
        body.write("\x1b[38;2;110;120;135m   depth\x1b[0m      "
                   + "\x1b[1;38;2;140;220;220m│\x1b[0m"
                   + "\x1b[48;2;26;32;38m\x1b[38;2;212;212;212m "
                   + self._cfg.defaults_depth + " \x1b[0m\x1b[0m"
                   + "    \x1b[38;2;110;120;135m"
                   + ("DEEP" if self._cfg.defaults_depth == "STANDARD" else "STANDARD")
                   + "\x1b[0m")
        body.write("")
        body.write("\x1b[38;2;110;120;135m   compressed\x1b[0m   "
                   + "\x1b[1;38;2;140;220;220m│\x1b[0m"
                   + "\x1b[48;2;26;32;38m\x1b[38;2;212;212;212m "
                   + ("true" if self._cfg.defaults_compressed else "false")
                   + " \x1b[0m\x1b[0m"
                   + "    \x1b[38;2;110;120;135m"
                   + ("false" if self._cfg.defaults_compressed else "true")
                   + "\x1b[0m")
        body.write("")
        body.write("\x1b[38;2;110;120;135m   \u23af press \x1b[1;38;2;140;220;220me"
                   "\x1b[0m\x1b[38;2;110;120;135m or \x1b[1;38;2;140;220;220m\u23ce"
                   "\x1b[0m\x1b[38;2;110;120;135m to toggle between options"
                   " \u00b7 \x1b[1;38;2;140;220;220mtab\x1b[0m"
                   "\x1b[38;2;110;120;135m to advance\x1b[0m")

    def _render_add_row(self, card: SectionCard, label: str, hint: str) -> None:
        card.write_add_row(label, hint)

    # ---------------------------------------------------------- header / footer
    def _refresh_head(self) -> None:
        section = SECTIONS[self._rail_index]
        saved_at = mtime_str()
        if self._omniroute_setup_open:
            badge = "\x1b[38;2;230;200;130m● testing setup\x1b[0m"
            crumb = "Settings / providers / omniroute"
        elif self._provider_setup_open:
            who = (self._provider_setup_entry.display
                   if self._provider_setup_entry else "provider")
            badge = "\x1b[38;2;230;200;130m● connect " + who + "\x1b[0m"
            crumb = "Settings / providers / connect"
        elif self._picker_open:
            badge = "\x1b[38;2;230;200;130m● adding " + (self._picker_section or "") + "\x1b[0m"  # noqa: E501
            crumb = f"Settings / {section} / add"
        elif self._editing:
            crumb = f"Settings / {section} / editing"
            rows = _EDITABLE_ROWS.get(section, ())
            if rows:
                idx = min(self._edit_row, len(rows) - 1)
                kind, key = rows[idx]
                if kind == "text":
                    label = key
                elif key == "depth":
                    label = "depth (STANDARD / DEEP)"
                else:
                    label = "compressed (true / false)"
                badge = "\x1b[38;2;230;200;130m● " + label + "\x1b[0m"
            else:
                badge = "\x1b[38;2;230;200;130m● editing\x1b[0m"
        else:
            badge = "\x1b[38;2;140;210;150m● saved\x1b[0m"
            crumb = f"Settings / {section}"

        # Compact head: brand · crumb · badge · path · mtime
        head = (
            "\x1b[1;38;2;140;220;220m  Labourious\x1b[0m"
            "\x1b[38;2;160;165;175m  \u2014 " + crumb + "\x1b[0m"
            + (" " * max(1, 30 - len(crumb)))
            + badge
            + "          "
            + "\x1b[38;2;110;120;135m" + cfg_path_str() + "\x1b[0m"
            + "          "
            + "\x1b[38;2;110;120;135m" + saved_at + "\x1b[0m"
        )
        try:
            h = self.query_one("#settings-head", Static)
            h.update(to_text(head))
        except Exception:
            pass

    def _refresh_foot(self) -> None:
        section = SECTIONS[self._rail_index]
        if self._omniroute_setup_open or self._provider_setup_open:
            foot = (
                "\x1b[38;2;110;120;135m  Test connection must pass before Save \u00b7 "
                "keys go to OS keychain \u00b7 Esc cancel\x1b[0m"
            )
        elif self._picker_open:
            foot = (
                "\x1b[38;2;110;120;135m  \u2191/\u2193 select \u00b7 type to filter \u00b7 "
                "\x1b[1;38;2;140;220;220m\u23ce\x1b[0m\x1b[38;2;110;120;135m pick \u00b7 "
                "Esc back \u00b7 Ctrl+S save & close\x1b[0m"
            )
        elif self._editing:
            rows = _EDITABLE_ROWS.get(section, ())
            idx = min(self._edit_row, len(rows) - 1) if rows else 0
            is_toggle = bool(rows and rows[idx][0] == "toggle")
            if is_toggle:
                foot = (
                    "\x1b[38;2;110;120;135m  \x1b[1;38;2;140;220;220mtab\x1b[0m\x1b[38;2;110;120;135m "
                    "cycle \u00b7 1 / 2 pick \u00b7 auto-saves \u00b7 Esc done\x1b[0m"
                )
            else:
                foot = (
                    "\x1b[38;2;110;120;135m  \x1b[1;38;2;140;220;220m\u23ce\x1b[0m\x1b[38;2;110;120;135m save \u00b7 "
                    "Esc cancel \u00b7 \x1b[1;38;2;140;220;220mtab\x1b[0m\x1b[38;2;110;120;135m save & "
                    "advance \u00b7 Ctrl+S save & close\x1b[0m"
                )
        elif section in ("providers", "connectors", "per-agent", "hybrid"):
            foot = (
                "\x1b[38;2;110;120;135m  \x1b[1;38;2;140;220;220m\u2191/\u2193\x1b[0m\x1b[38;2;110;120;135m navigate \u00b7 "
                "\u2192/\u2190 switch section \u00b7 "
                "\x1b[1;38;2;140;220;220me\x1b[0m\x1b[38;2;110;120;135m edit \u00b7 "
                "Ctrl+O + add \u00b7 Ctrl+Y remove \u00b7 Ctrl+S save \u00b7 Esc back\x1b[0m"
            )
        else:
            # default / defaults read-only view, when not editing
            foot = (
                "\x1b[38;2;110;120;135m  \x1b[1;38;2;140;220;220m\u2191/\u2193\x1b[0m\x1b[38;2;110;120;135m rail \u00b7 "
                "\u2192/\u2190 switch section \u00b7 "
                "\x1b[1;38;2;140;220;220me\x1b[0m or "
                "\x1b[1;38;2;140;220;220m\u23ce\x1b[0m"
                "\x1b[38;2;110;120;135m edit \u00b7 Ctrl+S save \u00b7 Esc back\x1b[0m"
            )
        try:
            f = self.query_one("#settings-foot", Static)
            f.update(to_text(foot))
        except Exception:
            pass

    # ---------------------------------------------------------- action: add (open picker)
    def action_open_picker(self) -> None:
        if self._omniroute_setup_open or self._provider_setup_open:
            return
        section = SECTIONS[self._rail_index]
        # Only collection sections get a picker
        if section not in ("providers", "connectors", "per-agent", "hybrid"):
            return
        self._picker_section = section
        # Build picker items from the catalog, excluding already-configured
        if section == "providers":
            # Full 20-provider catalog, not the legacy 9-entry config list —
            # the picker must offer every router/provider the runtime speaks.
            existing = set(self._cfg.providers.keys())
            items = [
                PickerItem(key=e.name, label=e.display, description=e.description)
                for e in ALL_PROVIDERS if e.name not in existing
            ]
        elif section == "connectors":
            existing = set(self._cfg.connectors.keys())
            items = [
                PickerItem(key=val[0], label=val[0], description=val[1])
                for val in KNOWN_CONNECTORS if val[0] not in existing
            ]
        elif section == "per-agent":
            existing_agents = set(self._cfg.per_agent_model.keys())
            AGENTS = ["orchestrator", "senior-analyst",
                      "forensic-accounting", "devils-advocate", "final-report"]
            items = [
                PickerItem(key=a, label=a, description="override default model for this agent")
                for a in AGENTS if a not in existing_agents
            ]
        elif section == "hybrid":
            existing_agents = set(self._cfg.hybrid_paid_for)
            # Same agent catalog as per-agent
            AGENTS = ["orchestrator", "senior-analyst",
                      "forensic-accounting", "devils-advocate", "final-report"]
            items = [
                PickerItem(key=a, label=a, description="(paid) override default · uses per_agent_model")
                for a in AGENTS if a not in existing_agents
            ]
        else:
            items = []

        if not items:
            # Nothing to add
            self._set_status("All known items already configured.")
            return

        # Swap the body for the picker
        try:
            main = self.query_one("#settings-main")
            main.remove_children()
        except Exception:
            pass
        self._picker_overlay = PickerOverlay(items=items, breadcrumb=f"{section}/add")
        try:
            self._picker_overlay.border_title = f"add {section}"
            main = self.query_one("#settings-main")
            main.mount(self._picker_overlay)
        except Exception as e:
            self._set_status(f"picker mount failed: {e}")
            return
        self._picker_open = True
        self._refresh_head()
        self._refresh_foot()

    @on(SectionCard.AddClicked)
    def on_card_add_clicked(self, _event: SectionCard.AddClicked) -> None:
        """Mouse: user clicked a '+ add' row in the section card."""
        self.action_open_picker()

    @on(PickerOverlay.Selected)
    def on_picker_selected(self, event: PickerOverlay.Selected) -> None:
        """Mouse confirm from the picker: click-selected + click-confirmed
        (or Enter on the selected row, which posts the same message)."""
        if not self._picker_open:
            return
        sel = next((it for it in self._picker_overlay._visible
                    if it.key == event.key), None)
        if sel is not None:
            self._apply_pick(sel)

    # ---------------------------------------------------------- action: pick / confirm
    def action_confirm(self) -> None:
        if self._picker_open and self._picker_overlay is not None:
            sel = self._picker_overlay.pick()
            if sel is None:
                return
            self._apply_pick(sel)
            return
        # While editing, Enter is owned by the InlineTextEditor's
        # Input.Submitted handler. Don't preempt it.
        if self._editing:
            return
        # While a connect form is open, its Inputs own Enter — don't
        # toggle-expand behind the form.
        if self._omniroute_setup_open or self._provider_setup_open:
            return
        # On providers section, Enter toggles expand on the focused row.
        # The focus check stops the Input's own Enter-to-submit from
        # swallowing the key when the editor's text field has focus.
        if SECTIONS[self._rail_index] == "providers" and not self._editing:
            self.action_toggle_expand()
            return
        # No picker, not editing: Enter starts inline edit on editable sections.
        if self._is_editable_section(SECTIONS[self._rail_index]) and not self._editing:
            self._enter_or_advance_edit()
            return

    # ---------------------------------------------------------- inline-edit action
    def action_start_edit(self) -> None:
        """`e` key: open the focused provider's connect form (OmniRoute keeps
        its bespoke form) or edit a normal field."""
        if (self._picker_open or self._editing
                or self._omniroute_setup_open or self._provider_setup_open):
            return
        section = SECTIONS[self._rail_index]
        if section == "providers":
            visible = self._visible_providers()
            if visible:
                idx = max(0, min(self._provider_focus_idx, len(visible) - 1))
                entry = visible[idx]
                if entry.name == "omniroute":
                    self._open_omniroute_setup()
                else:
                    self._open_provider_setup(entry)
            return
        if self._is_editable_section(section):
            self._enter_or_advance_edit()

    def _open_omniroute_setup(self) -> None:
        """Swap the providers body for the real OmniRoute setup form."""
        existing = self._cfg.providers.get("omniroute")
        endpoint = existing.base_url if existing and existing.base_url else "http://localhost:20128/v1"
        model = "auto"
        if self._cfg.default_model.startswith("omniroute/"):
            model = self._cfg.default_model.split("/", 1)[1] or "auto"
        setup = OmniRouteSetup(
            endpoint=endpoint,
            model=model,
            has_key=key_present("omniroute"),
            id="omniroute-setup-form",
        )
        try:
            main = self.query_one("#settings-main")
            main.remove_children()
            main.mount(setup)
        except Exception as exc:
            self._set_status(f"OmniRoute form failed: {exc}")
            return
        self._omniroute_setup = setup
        self._omniroute_setup_open = True
        self._refresh_head()
        self._refresh_foot()

    def _close_omniroute_setup(self) -> None:
        self._omniroute_setup = None
        self._omniroute_setup_open = False
        try:
            main = self.query_one("#settings-main")
            main.remove_children()
            self._mount_providers_panel()
        except Exception:
            pass
        self._refresh_head()
        self._refresh_foot()

    @on(OmniRouteSetup.Saved)
    def on_omniroute_setup_saved(self, message: OmniRouteSetup.Saved) -> None:
        """Persist endpoint/model in config and the optional secret in keychain."""
        self._cfg.providers["omniroute"] = ProviderConfig(
            name="omniroute",
            base_url=message.endpoint,
            api_key_env=None,
        )
        self._cfg.default_model = f"omniroute/{message.model}"
        # A blank key means "keep an existing key" when editing. A key is
        # never written to config.json or rendered into the settings rows.
        if message.api_key:
            set_key("omniroute", message.api_key)
        elif not key_present("omniroute"):
            delete_key("omniroute")
        self._persist()
        self._close_omniroute_setup()
        self._set_status("OmniRoute saved · default model updated")

    @on(OmniRouteSetup.Cancelled)
    def on_omniroute_setup_cancelled(self, _message: OmniRouteSetup.Cancelled) -> None:
        self._close_omniroute_setup()

    # ---------------------------------------------------------- per-provider connect form
    def _open_provider_setup(self, entry: ProviderEntry) -> None:
        """Swap the providers body for THIS provider's connect form.

        Each router/provider differs — endpoint, model list, key handling —
        so every row gets its own connection settings. The form tests a
        pasted key with a real round-trip before Save is enabled; keys are
        written to the OS keychain, never config.json.
        """
        existing = self._cfg.providers.get(entry.name)
        endpoint_override = None
        if (existing and existing.base_url
                and existing.base_url != (entry.base_url or "")):
            endpoint_override = existing.base_url
        setup = ProviderSetup(
            entry,
            has_key=key_present(entry.name),
            endpoint_override=endpoint_override,
            id="provider-setup-form",
        )
        try:
            main = self.query_one("#settings-main")
            main.remove_children()
            main.mount(setup)
        except Exception as exc:
            self._set_status(f"connect form failed: {exc}")
            return
        self._provider_setup = setup
        self._provider_setup_entry = entry
        self._provider_setup_open = True
        self._refresh_head()
        self._refresh_foot()

    def _close_provider_setup(self) -> None:
        self._provider_setup = None
        self._provider_setup_entry = None
        self._provider_setup_open = False
        try:
            main = self.query_one("#settings-main")
            main.remove_children()
            self._mount_providers_panel()
        except Exception:
            pass
        self._refresh_head()
        self._refresh_foot()

    @on(ProviderSetup.Saved)
    def on_provider_setup_saved(self, message: ProviderSetup.Saved) -> None:
        """Persist endpoint/model in config; the pasted key goes to the OS
        keychain — never into config.json."""
        entry = by_name(message.provider)
        self._cfg.providers[message.provider] = ProviderConfig(
            name=message.provider,
            base_url=message.endpoint or (entry.base_url if entry else ""),
            api_key_env=entry.env_var if entry else None,
        )
        self._cfg.default_model = f"{message.provider}/{message.model}"
        # Blank key on save means "no key stored" — delete any stale one so
        # the panel's dot stays honest.
        if message.api_key:
            set_key(message.provider, message.api_key)
        else:
            delete_key(message.provider)
        self._persist()
        self._close_provider_setup()
        self._set_status(
            f"{message.provider} connected · default model "
            f"{message.provider}/{message.model}")

    @on(ProviderSetup.Cancelled)
    def on_provider_setup_cancelled(self, _message: ProviderSetup.Cancelled) -> None:
        self._close_provider_setup()

    def _is_editable_section(self, section: str) -> bool:
        return section in _EDITABLE_ROWS

    def _enter_or_advance_edit(self) -> None:
        """Enter edit mode for the current row, or advance to the next row
        if already editing a text section."""
        section = SECTIONS[self._rail_index]
        rows = _EDITABLE_ROWS[section]
        if not self._editing:
            self._editing = True
            self._edit_section = section
            self._edit_row = 0
        else:
            # Already editing — advance the row index (for per-agent only — others
            # have a single editable row).
            if section == "per-agent" and self._edit_row + 1 < len(self._cfg.per_agent_model):
                self._exit_edit_mode_no_remount()
                self._edit_row += 1
                self._editing = True
                self._edit_section = section
            else:
                # Single-row sections (default, defaults row 0/1): commit + exit
                self._exit_edit_mode()
                return
        self._render_or_mount_editor()

    def _render_or_mount_editor(self) -> None:
        """Mount (or re-mount) the editor for the current (_edit_section,
        _edit_row) pair and update head/foot."""
        section = self._edit_section
        row_idx = self._edit_row
        if section is None:
            return
        rows = _EDITABLE_ROWS[section]
        # For per-agent there is one schema row but N data rows;
        # `row_idx` is a data index, so clamp to schema size.
        idx = min(row_idx, len(rows) - 1)
        kind, key = rows[idx]
        editor_id = f"{section}:{key}:{row_idx}"

        if kind == "text":
            initial = self._read_field(section, key)
            # typewriter_ms is an integer ms field — don't show the model presets
            # so the user isn't tempted to type a model id; show a few delays
            # (0, 10, 30, 80, 150) for quick pick instead.
            if section == "streaming" and key == "typewriter_ms":
                presets = ["0", "10", "30", "80", "150"]
            else:
                presets = self._model_presets()
            editor = InlineTextEditor(
                editor_id=editor_id,
                initial=initial,
                presets=presets,
                field_label=key,
            )
        else:  # toggle
            if key == "depth":
                current = self._cfg.defaults_depth
                options = ("STANDARD", "DEEP")
            elif key == "chunks":
                current = "true" if self._cfg.stream_chunks else "false"
                options = ("true", "false")
            else:  # compressed
                current = "true" if self._cfg.defaults_compressed else "false"
                options = ("true", "false")
            editor = InlineToggleEditor(
                editor_id=editor_id,
                current=current,
                options=options,
            )

        # Mount into the SectionCard.
        try:
            card = self.query_one(SectionCard)
        except Exception:
            return
        card.mount_editor(editor)
        self._refresh_head()
        self._refresh_foot()

    def _read_field(self, section: str, key: str) -> str:
        if section == "default":
            return self._cfg.default_model
        if section == "per-agent":
            agents = list(self._cfg.per_agent_model.keys())
            if self._edit_row < len(agents):
                return self._cfg.per_agent_model[agents[self._edit_row]]
            return ""
        if section == "defaults":
            if key == "depth":
                return self._cfg.defaults_depth
            if key == "compressed":
                return "true" if self._cfg.defaults_compressed else "false"
        if section == "streaming":
            if key == "chunks":
                return "true" if self._cfg.stream_chunks else "false"
            if key == "typewriter_ms":
                return str(self._cfg.stream_typewriter_ms)
        return ""

    def _write_field(self, section: str, key: str, value: str) -> tuple[bool, str | None]:
        """Apply value to the Config dataclass. Returns (ok, error_str)."""
        if section == "default":
            err = _validate_field_io("default", "model", value)
            if err:
                return False, err
            self._cfg.default_model = value
            return True, None
        if section == "per-agent":
            err = _validate_field_io("per-agent", "model", value)
            if err:
                return False, err
            agents = list(self._cfg.per_agent_model.keys())
            if self._edit_row >= len(agents):
                return False, "row out of range"
            agent = agents[self._edit_row]
            self._cfg.per_agent_model[agent] = value
            return True, None
        if section == "defaults":
            if key == "depth":
                err = _validate_field_io("defaults", "depth", value)
                if err:
                    return False, err
                self._cfg.defaults_depth = value
                return True, None
            if key == "compressed":
                err = _validate_field_io("defaults", "compressed", value)
                if err:
                    return False, err
                self._cfg.defaults_compressed = (value == "true")
                return True, None
        if section == "streaming":
            if key == "chunks":
                err = _validate_field_io("streaming", "chunks", value)
                if err:
                    return False, err
                self._cfg.stream_chunks = (value == "true")
                return True, None
            if key == "typewriter_ms":
                err = _validate_field_io("streaming", "typewriter_ms", value)
                if err:
                    return False, err
                # Already validated to be 0..500 by validate_field.
                self._cfg.stream_typewriter_ms = int(value)
                return True, None
        return False, "unknown section/key"

    # ----- inline-edit message handlers -----
    def on_text_edit_committed(self, message: TextEditCommitted) -> None:
        section = self._edit_section
        rows = _EDITABLE_ROWS.get(section, ())
        if not rows:
            return
        kind, key = rows[self._edit_row]
        ok, err = self._write_field(section, key, message.value)
        if not ok:
            self._set_status(err or "validation failed")
            return
        self._persist()
        # Tab advances; Enter (and shift+tab at last row) exits.
        if message.via == "tab":
            # Advance to next row if any, else exit.
            next_row = self._edit_row + 1
            # For per-agent with N overrides, advance while next_row < len.
            # For single-row sections (default / defaults row 0 or 1), exit.
            if section == "per-agent":
                # Guard against a removal shrinking the dict between
                # entering and advancing edit mode.
                agents = self._cfg.per_agent_model
                if next_row < len(agents):
                    self._exit_edit_mode_no_remount()
                    self._edit_row = next_row
                    self._editing = True
                    self._edit_section = section
                    self._render_or_mount_editor()
                    return
            # fall through to exit
        self._exit_edit_mode()

    def on_text_edit_reverted(self, message: TextEditReverted) -> None:
        self._exit_edit_mode()

    def on_toggle_edit_committed(self, message: ToggleEditCommitted) -> None:
        section = self._edit_section
        rows = _EDITABLE_ROWS.get(section, ())
        if not rows:
            return
        kind, key = rows[self._edit_row]
        ok, err = self._write_field(section, key, message.value)
        if not ok:
            self._set_status(err or "toggle write failed")
            return
        self._persist()
        # Tab advances to next toggle row (only `defaults` has 2).
        # 1/2 direct pick keeps current row open for further cycling.
        if message.via == "tab":
            next_row = self._edit_row + 1
            if section == "defaults" and next_row < len(rows):
                self._exit_edit_mode_no_remount()
                self._edit_row = next_row
                self._editing = True
                self._edit_section = section
                self._render_or_mount_editor()
                return
            # Last toggle row — exit.
            self._exit_edit_mode()
            return
        # Refresh head meta; stay in edit mode for further cycling.
        self._refresh_head()

    def on_toggle_edit_done(self, message: ToggleEditDone) -> None:
        self._exit_edit_mode()

    def _exit_edit_mode_no_remount(self) -> None:
        """Used by `_enter_or_advance_edit` to clean up the prior editor
        without re-rendering the read-only view (we immediately remount)."""
        try:
            card = self.query_one(SectionCard)
            for w in list(card.children):
                cls = w.classes or ""
                if "inline-editor" in cls or "inline-toggle-editor" in cls:
                    w.remove()
        except Exception:
            pass
        self._editing = False

    def _exit_edit_mode(self) -> None:
        """Exit edit mode and re-render the section's read-only view."""
        section = self._edit_section
        self._editing = False
        self._edit_section = None
        self._edit_row = 0
        try:
            card = self.query_one(SectionCard)
            new_body = card.exit_edit_mode()
        except Exception:
            new_body = None
        # Re-render the section's read-only body.
        self._render_current_section_into(new_body)
        self._refresh_head()
        self._refresh_foot()

    def _render_current_section_into(self, body) -> None:
        """Same as `_render_current_section` but uses an explicit body."""
        if body is None:
            self._render_current_section()
            return
        section = SECTIONS[self._rail_index]
        try:
            body.clear()
        except Exception:
            pass
        if section == "providers":
            self._render_providers_body(body)
        elif section == "default":
            self._render_default_body(body)
        elif section == "per-agent":
            self._render_per_agent_body(body)
        elif section == "hybrid":
            self._render_hybrid_body(body)
        elif section == "connectors":
            self._render_connectors_body(body)
        elif section == "defaults":
            self._render_defaults_body(body)

    def action_remove(self) -> None:
        """Remove the **selected** row in the current section (not the
        last one in dict order). Falls back to last if no selection state
        is tracked for that section.
        """
        if (self._picker_open or self._omniroute_setup_open
                or self._provider_setup_open):
            return
        section = SECTIONS[self._rail_index]

        def _remove_by_index(names: list[str]) -> str | None:
            if not names:
                return None
            idx = self._row_index
            if idx < 0 or idx >= len(names):
                idx = len(names) - 1
            return names[idx]

        if section == "providers":
            names = list(self._cfg.providers.keys())
            removed = _remove_by_index(names)
            if removed:
                del self._cfg.providers[removed]
                self._row_index = max(0, self._row_index - 1) if self._row_index > 0 else 0
                self._persist()
                self._render_current_section()
                self._refresh_head()
        elif section == "connectors":
            names = list(self._cfg.connectors.keys())
            removed = _remove_by_index(names)
            if removed:
                del self._cfg.connectors[removed]
                self._row_index = max(0, self._row_index - 1) if self._row_index > 0 else 0
                self._persist()
                self._render_current_section()
                self._refresh_head()
        elif section == "per-agent":
            names = list(self._cfg.per_agent_model.keys())
            removed = _remove_by_index(names)
            if removed:
                del self._cfg.per_agent_model[removed]
                self._row_index = max(0, self._row_index - 1) if self._row_index > 0 else 0
                self._persist()
                self._render_current_section()
                self._refresh_head()
        elif section == "hybrid":
            names = self._cfg.hybrid_paid_for[:]
            removed = _remove_by_index(names)
            if removed:
                self._cfg.hybrid_paid_for.remove(removed)
                self._row_index = max(0, self._row_index - 1) if self._row_index > 0 else 0
                self._persist()
                self._render_current_section()
                self._refresh_head()

    # ---------------------------------------------------------- navigation up/down inside picker
    def action_nav_up(self) -> None:
        if self._picker_open and self._picker_overlay:
            self._picker_overlay.select_prev()

    def action_nav_down(self) -> None:
        if self._picker_open and self._picker_overlay:
            self._picker_overlay.select_next()

    # ---------------------------------------------------------- typing into the picker + rail nav
    def on_key(self, event) -> None:
        """Arrows + typing handled directly here so they don't depend on
        binding priority or focus. Bindings handle ctrl-* shortcuts only.
        """
        # When the inline text editor's Input is focused, its on_key handler
        # (running on the focused widget first) intercepts tab/escape; but
        # arrows still bubble here. While editing, arrows must edit text,
        # not move rows — swallow them.
        if (self._editing or self._omniroute_setup_open
                or self._provider_setup_open):
            if event.key in ("up", "down", "left", "right"):
                event.stop()
            return
        # Picker mode: arrows + typing + backspace
        if self._picker_open and self._picker_overlay is not None:
            overlay = self._picker_overlay
            if event.key == "ctrl+h" or event.key == "backspace":
                overlay.backspace()
                return
            if event.key == "up":
                overlay.select_prev()
                event.stop()
                return
            if event.key == "down":
                overlay.select_next()
                event.stop()
                return
            if event.character and len(event.character) == 1 and event.character.isprintable():
                if event.character not in ("\r", "\n"):
                    overlay.type_char(event.character)
                    return
            return  # picker is up; don't pass arrow to rail
        # Two-scope navigation — ← moves between scopes, ↓ moves within a scope:
        #   RAIL scope:  ↑/↓ change section, → enters the section pane
        #   PANE scope:  ↑/↓ move the focused row/entry in the card,
        #                ← returns to the rail, → acts per-section
        #                (providers: expand; editors: nothing).
        # Tab / Shift+Tab still cycle the provider filter chips when the
        # providers pane is active.
        scope = self._nav_scope
        if event.key == "right":
            if scope == "rail":
                self._enter_pane()
            elif SECTIONS[self._rail_index] == "providers":
                self.action_toggle_expand()
            return
        if event.key == "left":
            if scope == "pane":
                self._leave_pane()
            return
        if event.key == "up":
            if scope == "rail":
                self.action_rail_prev()
            else:
                self.action_pane_prev()
            return
        if event.key == "down":
            if scope == "rail":
                self.action_rail_next()
            else:
                self.action_pane_next()
            return
        if event.key == "tab" and scope == "pane" \
                and SECTIONS[self._rail_index] == "providers":
            self.action_next_filter()
            return
        if event.key == "shift+tab" and scope == "pane" \
                and SECTIONS[self._rail_index] == "providers":
            self.action_prev_filter()
            return

    # ---------------------------------------------------------- apply pick + persist
    def _close_picker(self) -> None:
        """Dismiss the add-picker and restore the section body."""
        self._picker_open = False
        self._picker_overlay = None
        try:
            main = self.query_one("#settings-main")
            main.remove_children()
        except Exception:
            pass
        section = SECTIONS[self._rail_index]
        if section == "providers":
            self._mount_providers_panel()
        else:
            try:
                main = self.query_one("#settings-main")
                card = SectionCard(
                    title=section,
                    meta=self._section_meta(section),
                )
                main.mount(card)
            except Exception:
                pass
            self.call_after_refresh(self._render_current_section)
        self._refresh_head()
        self._refresh_foot()

    def _apply_pick(self, sel: PickerItem) -> None:
        section = self._picker_section
        if section == "providers":
            # OmniRoute keeps its bespoke gateway form; other keyed providers
            # open their connect form immediately so the API key is pasted
            # (and tested) in the same flow instead of persisting a row that
            # can never authenticate. Keyless local providers persist catalog
            # defaults right away — no test gate for a server that may simply
            # not be started yet.
            entry = by_name(sel.key)
            if entry is not None:
                self._picker_open = False
                self._picker_overlay = None
                if entry.name == "omniroute":
                    self._open_omniroute_setup()
                    return
                if entry.env_var:
                    self._open_provider_setup(entry)
                    return
                self._cfg.providers[entry.name] = ProviderConfig(
                    name=entry.name, base_url=entry.base_url or "",
                    api_key_env=None,
                )
        elif section == "connectors":
            entry = next((v for v in KNOWN_CONNECTORS if v[0] == sel.key), None)
            if entry is not None:
                _, _, extra = entry
                self._cfg.connectors[sel.key] = ConnectorConfig(
                    name=sel.key, provider=extra["provider"], extra={
                        k: v for k, v in extra.items() if k != "provider"
                    },
                )
        elif section == "per-agent":
            # Use default_model as the initial value; user can edit later
            self._cfg.per_agent_model[sel.key] = self._cfg.default_model
        elif section == "hybrid":
            if sel.key not in self._cfg.hybrid_paid_for:
                self._cfg.hybrid_paid_for.append(sel.key)

        self._picker_open = False
        self._picker_overlay = None
        self._persist()
        # Re-mount the body: providers gets the L3 panel, others a card.
        try:
            main = self.query_one("#settings-main")
            main.remove_children()
        except Exception:
            pass
        if section == "providers":
            self._mount_providers_panel()
        else:
            main = self.query_one("#settings-main")
            card = SectionCard(
                title=section,
                meta=self._section_meta(section),
            )
            main.mount(card)
            self.call_after_refresh(self._render_current_section)
        self._refresh_head()
        self._refresh_foot()

    def _persist(self) -> None:
        # Key writes (OmniRoute form) happen just before persist; drop the
        # screen-level keychain cache so the providers panel reflects the
        # new key immediately.
        self._key_cache = None
        try:
            save_config(self._cfg)
            self._health = health_check(self._cfg)
        except ConfigValidationError as e:
            self._set_status(f"validation failed: {e}")
        except Exception as e:
            self._set_status(f"save failed: {type(e).__name__}: {e}")

    # ---------------------------------------------------------- save / close
    def action_save_close(self) -> None:
        # Auto-saves already happened on each change. Closing just dismisses.
        self.app.pop_screen()

    def action_back_chat(self) -> None:
        # Esc while the add-picker is up backs out of "add" only — it must
        # not throw away the whole Settings screen.
        if self._picker_open:
            self._close_picker()
            return
        if self._omniroute_setup_open:
            self._close_omniroute_setup()
            return
        if self._provider_setup_open:
            self._close_provider_setup()
            return
        # On providers L3, Esc collapses the expanded row first.
        if (not self._picker_open
            and not self._editing
            and SECTIONS[self._rail_index] == "providers"
            and self._provider_expanded is not None):
            self._provider_expanded = None
            self._refresh_providers_panel()
            return
        # Auto-saves already wrote to disk; closing is safe.
        self.app.pop_screen()

    # ---------------------------------------------------------- status
    def _set_status(self, msg: str) -> None:
        """Display a transient status message in the footer."""
        try:
            head = self.query_one("#settings-head", Static)
            # Override the head with a status line:
            head.update(to_text("\x1b[38;2;230;200;130m● " + msg + "\x1b[0m"))
        except Exception:
            pass


    # ---------------------------------------------------------- helpers for body re-rendering
    def _render_providers_body(self, body):
        """Post-edit re-render body for the providers section (mirrors
        _render_providers; the L3 panel owns the primary view)."""
        if not self._cfg.providers:
            body.write("\x1b[38;2;110;120;135m  No providers configured — the full catalog is the default view.\x1b[0m")
            body.write("")
            return
        for name, p in self._cfg.providers.items():
            detail = p.api_key_env if p.api_key_env else "(local)"
            health = self._health.get(f"provider:{name}", "ok")
            body.write(_render_row(name=name, detail=detail, health=health))
        body.write("")
        try:
            self._render_add_row(self.query_one(SectionCard), "+ add provider",
                                 "groq \u00b7 openrouter \u00b7 openai \u00b7 google \u00b7 mistral \u00b7 cohere")
        except Exception:
            pass

    def _render_per_agent_body(self, body):
        if not self._cfg.per_agent_model:
            body.write("\x1b[38;2;110;120;135m  No per-agent overrides. Default applies to all agents.\x1b[0m")
            body.write("")
            return
        for agent, mid in self._cfg.per_agent_model.items():
            body.write(_render_row(name=agent, detail=f"\u2192  {mid}", health="set"))
        body.write("")
        try:
            self._render_add_row(self.query_one(SectionCard), "+ add override",
                                 "orchestrator \u00b7 senior-analyst \u00b7 forensic-accounting \u00b7 devils-advocate \u00b7 final-report")
        except Exception:
            pass

    def _render_hybrid_body(self, body):
        body.write("\x1b[38;2;160;165;175m  Agents running on a paid model:\x1b[0m")
        body.write("")
        if not self._cfg.hybrid_paid_for:
            body.write("\x1b[38;2;110;120;135m  No paid-for agents.\x1b[0m")
        else:
            for agent in self._cfg.hybrid_paid_for:
                mid = self._cfg.per_agent_model.get(agent, self._cfg.default_model)
                body.write(_render_row(name=agent, detail=f"\u2192  {mid}", health="set", removable=False))
        body.write("")
        try:
            self._render_add_row(self.query_one(SectionCard), "+ add agent",
                                 "orchestrator \u00b7 senior-analyst \u00b7 forensic-accounting \u00b7 devils-advocate \u00b7 final-report")
        except Exception:
            pass

    def _render_connectors_body(self, body):
        if not self._cfg.connectors:
            body.write("\x1b[38;2;110;120;135m  No connectors configured.\x1b[0m")
            body.write("")
            return
        for name, c in self._cfg.connectors.items():
            extra = " \u00b7 ".join(f"{k}: {v}" for k, v in c.extra.items())
            detail = f"{c.provider}" + (f" / {extra}" if extra else "")
            body.write(_render_row(name=name, detail=detail,
                                   health=self._health.get(f"connector:{name}", "ok")))
        body.write("")
        try:
            self._render_add_row(self.query_one(SectionCard), "+ add connector",
                                 "sec_edgar \u00b7 google_rss \u00b7 fred \u00b7 polygon \u00b7 fmp \u2026")
        except Exception:
            pass

    def _render_default_body(self, body):
        self._render_default(self.query_one(SectionCard))

    def _render_defaults_body(self, body):
        self._render_defaults(self.query_one(SectionCard))


# ------------------------------------------------------------- helpers
def _box(text: str, focused: bool = False, caret: bool = True) -> str:
    bar = ("\x1b[1;38;2;140;220;220m│\x1b[0m" if focused
           else "\x1b[38;2;70;82;98m│\x1b[0m")
    caret_glyph = "\x1b[1;38;2;140;220;220m▌\x1b[0m" if focused and caret else ""
    bg = "\x1b[48;2;22;26;33m" if focused else ""
    end_bg = "\x1b[0m" if focused else ""
    return f"{bar}{bg}\x1b[38;2;212;212;212m{text}\x1b[0m{caret_glyph}{end_bg}{bar}"


def _focused(active: bool, label: str) -> str:
    if active:
        return "\x1b[1;38;2;140;220;220m│\x1b[0m\x1b[48;2;22;26;33m\x1b[38;2;212;212;212m " + label + " \x1b[0m\x1b[0m"
    return "\x1b[38;2;110;120;135m  " + label + "  \x1b[0m"

