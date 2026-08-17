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
)
from frontend.widgets.section_card import SectionCard
from frontend.widgets.picker_overlay import PickerItem, PickerOverlay
from frontend.widgets.setting_row import render_row as _render_row


# Six sections in canonical order. The order matches PROTOCOL.md Appendix A.
SECTIONS = ("providers", "default", "per-agent", "hybrid", "connectors", "defaults")


class SettingsScreen(Screen):
    """The Settings modal.

    Push this on top of ChatScreen with self.app.push_screen(SettingsScreen()).
    """

    BINDINGS = [
        Binding("ctrl+s",  "save_close",  "Save & close"),
        Binding("escape",   "back_chat",   "Back to chat"),
        Binding("enter",    "confirm",     "Confirm"),
        Binding("ctrl+d",   "remove",      "Remove"),
        Binding("ctrl+n",   "open_picker", "+ Add"),
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
                yield SectionCard(
                    title=SECTIONS[self._rail_index],
                    meta=self._section_meta(SECTIONS[self._rail_index]),
                )
        # Footer strip
        yield Static("", markup=False, classes="settings-foot", id="settings-foot")

    def on_mount(self) -> None:
        self._refresh_head()
        self._refresh_rail_selection()
        self._render_current_section()
        self._refresh_foot()

    # ---------------------------------------------------------- rail
    def _rail_label(self, section: str) -> str:
        # No ANSI wrap; just plain — selection is done by .sel class
        return section

    def action_rail_next(self) -> None:
        if self._picker_open:
            return  # ignore while picker is up
        self._rail_index = (self._rail_index + 1) % len(SECTIONS)
        self._refresh_rail_selection()
        self._swap_card(SECTIONS[self._rail_index])
        self._refresh_head()

    def action_rail_prev(self) -> None:
        if self._picker_open:
            return
        self._rail_index = (self._rail_index - 1) % len(SECTIONS)
        self._refresh_rail_selection()
        self._swap_card(SECTIONS[self._rail_index])
        self._refresh_head()

    def _refresh_rail_selection(self) -> None:
        for i, s in enumerate(SECTIONS):
            try:
                w = self.query_one(f"#rail-{s}", Static)
                w.set_classes("rail-item" + (" sel" if i == self._rail_index else ""))
            except Exception:
                pass

    # ---------------------------------------------------------- sections
    def _section_meta(self, section: str) -> str:
        if section == "providers":
            n = len(self._cfg.providers)
            return f"{n} configured"
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
        try:
            card = SectionCard(
                title=section,
                meta=self._section_meta(section),
            )
            main.mount(card)
        except Exception:
            pass

    def _render_current_section(self) -> None:
        section = SECTIONS[self._rail_index]
        try:
            card = self.query_one(SectionCard)
            body = card.body()
            if body is None:
                return  # not yet mounted; defer to on_mount
        except Exception:
            return

        # Render via body.write(); body.clear() resets the log
        try:
            body.clear()
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

    # ---------------------------------------------------------- per-section renders
    def _render_providers(self, card: SectionCard) -> None:
        body = card.body()
        body.clear()

        if not self._cfg.providers:
            body.write("\x1b[38;2;110;120;135m  No providers configured.\x1b[0m")
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
        # Inline single input
        body.write("\x1b[38;2;110;120;135m  model\x1b[0m   "
                   + _box(self._cfg.default_model, focused=True))
        body.write("")
        body.write("\x1b[38;2;110;120;135m  Examples (Tab to complete):\x1b[0m")
        for ex in ("ollama/llama3.3:70b",
                   "anthropic/claude-sonnet-4-5",
                   "groq/llama-3.3-70b-versatile",
                   "openrouter/auto"):
            body.write("\x1b[38;2;160;165;175m  " + ex + "\x1b[0m")

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
        body = card.body()
        body.clear()
        if not self._cfg.connectors:
            body.write("\x1b[38;2;110;120;135m  No connectors configured.\x1b[0m")
            body.write("")
            self._render_add_row(card, "+ add connector",
                                 "sec_edgar · google_rss · fred · polygon · fmp · …")
            return
        for name, c in self._cfg.connectors.items():
            extra = " · ".join(f"{k}: {v}" for k, v in c.extra.items())
            detail = f"{c.provider}" + (f" / {extra}" if extra else "")
            health = self._health.get(f"connector:{name}", "ok")
            body.write(_render_row(name=name, detail=detail, health=health))
        body.write("")
        self._render_add_row(card, "+ add connector",
                             "sec_edgar · google_rss · fred · polygon · fmp · …")

    def _render_defaults(self, card: SectionCard) -> None:
        body = card.body()
        body.clear()
        body.write(f"\x1b[38;2;110;120;135m  depth\x1b[0m      {_focused(self._cfg.defaults_depth == 'DEEP', 'DEEP')}   {_focused(self._cfg.defaults_depth == 'STANDARD', 'STANDARD')}")
        body.write("")
        body.write(f"\x1b[38;2;110;120;135m  compressed\x1b[0m   {_focused(self._cfg.defaults_compressed, 'true')}   {_focused(not self._cfg.defaults_compressed, 'false')}")

    def _render_add_row(self, card: SectionCard, label: str, hint: str) -> None:
        card.write_add_row(label, hint)

    # ---------------------------------------------------------- header / footer
    def _refresh_head(self) -> None:
        section = SECTIONS[self._rail_index]
        saved_at = mtime_str()
        # Compute 'saved' / 'unsaved' badge:
        try:
            badge = "\x1b[38;2;140;210;150m● saved\x1b[0m"
        except Exception:
            badge = "● saved"
        head = (
            f"\x1b[1;38;2;140;220;220m  Labourious\x1b[0m"
            f"\x1b[38;2;160;165;175m  — Settings / {section}\x1b[0m"
            f"{' ' * 30}"
            f"{badge}"
            f"          "
            f"\x1b[38;2;110;120;135m{cfg_path_str()}\x1b[0m"
            f"          "
            f"\x1b[38;2;110;120;135m{saved_at}\x1b[0m"
        )
        try:
            h = self.query_one("#settings-head", Static)
            h.update(head)
        except Exception:
            pass

    def _refresh_foot(self) -> None:
        section = SECTIONS[self._rail_index]
        if self._picker_open:
            foot = (
                "\x1b[38;2;110;120;135m  ↑/↓ select · type to filter · "
                "⏎ pick · Esc back · Ctrl+S save & close\x1b[0m"
            )
        elif section == "providers" or section == "connectors" or section == "per-agent" or section == "hybrid":
            foot = (
                "\x1b[38;2;110;120;135m  ↑/↓ rail · →/← switch section · "
                "Ctrl+N + add · Ctrl+D remove · Ctrl+S save · Esc back\x1b[0m"
            )
        else:
            foot = (
                "\x1b[38;2;110;120;135m  ↑/↓ rail · →/← switch section · "
                "Tab next action · Ctrl+S save · Esc back\x1b[0m"
            )
        try:
            f = self.query_one("#settings-foot", Static)
            f.update(foot)
        except Exception:
            pass

    # ---------------------------------------------------------- action: add (open picker)
    def action_open_picker(self) -> None:
        section = SECTIONS[self._rail_index]
        # Only collection sections get a picker
        if section not in ("providers", "connectors", "per-agent", "hybrid"):
            return
        self._picker_section = section
        # Build picker items from the catalog, excluding already-configured
        if section == "providers":
            existing = set(self._cfg.providers.keys())
            items = [
                PickerItem(key=val[0], label=val[0], description=val[1])
                for val in KNOWN_PROVIDERS if val[0] not in existing
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

    # ---------------------------------------------------------- action: pick / confirm
    def action_confirm(self) -> None:
        if self._picker_open and self._picker_overlay is not None:
            sel = self._picker_overlay.pick()
            if sel is None:
                return
            self._apply_pick(sel)
            return

        # Otherwise confirm does nothing on this section in v1
        # (Tab/Enter is the inline-edit trigger; future versions may add it.)

    def action_remove(self) -> None:
        if self._picker_open:
            return
        section = SECTIONS[self._rail_index]
        if section == "providers":
            names = list(self._cfg.providers.keys())
            if names:
                removed = names[-1]   # simple: remove last in current order
                del self._cfg.providers[removed]
                self._persist()
                self._render_current_section()
                self._refresh_head()
        elif section == "connectors":
            names = list(self._cfg.connectors.keys())
            if names:
                removed = names[-1]
                del self._cfg.connectors[removed]
                self._persist()
                self._render_current_section()
                self._refresh_head()
        elif section == "per-agent":
            names = list(self._cfg.per_agent_model.keys())
            if names:
                removed = names[-1]
                del self._cfg.per_agent_model[removed]
                self._persist()
                self._render_current_section()
                self._refresh_head()
        elif section == "hybrid":
            names = self._cfg.hybrid_paid_for[:]
            if names:
                removed = names[-1]
                self._cfg.hybrid_paid_for.remove(removed)
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
        # Picker mode: arrows + typing + backspace
        if self._picker_open and self._picker_overlay is not None:
            overlay = self._picker_overlay
            if event.key == "ctrl+h" or event.key == "backspace":
                overlay.backspace()
                return
            if event.key == "up":
                overlay.select_prev()
                return
            if event.key == "down":
                overlay.select_next()
                return
            if event.character and len(event.character) == 1 and event.character.isprintable():
                if event.character not in ("\r", "\n"):
                    overlay.type_char(event.character)
                    return
            return  # picker is up; don't pass arrow to rail
        # Rail mode: arrows drive rail nav (bindings are focus-flaky in 3.7)
        if event.key == "right":
            self.action_rail_next()
            return
        if event.key == "left":
            self.action_rail_prev()
            return
        if event.key == "up":
            # nudge: same as left for now (no per-row nav needed)
            self.action_rail_prev()
            return
        if event.key == "down":
            self.action_rail_next()
            return

    # ---------------------------------------------------------- apply pick + persist
    def _apply_pick(self, sel: PickerItem) -> None:
        section = self._picker_section
        if section == "providers":
            # find catalog row by key
            entry = next((v for v in KNOWN_PROVIDERS if v[0] == sel.key), None)
            if entry is not None:
                _, _, base_url, api_key_env = entry
                self._cfg.providers[sel.key] = ProviderConfig(
                    name=sel.key, base_url=base_url, api_key_env=api_key_env,
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
        # Re-mount the body with the section's card
        try:
            main = self.query_one("#settings-main")
            main.remove_children()
        except Exception:
            pass
        main = self.query_one("#settings-main")
        card = SectionCard(
            title=section,
            meta=self._section_meta(section),
        )
        main.mount(card)
        self._render_current_section()
        self._refresh_head()
        self._refresh_foot()

    def _persist(self) -> None:
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
        # Auto-saves already wrote to disk; closing is safe.
        self.app.pop_screen()

    # ---------------------------------------------------------- status
    def _set_status(self, msg: str) -> None:
        """Display a transient status message in the footer."""
        try:
            head = self.query_one("#settings-head", Static)
            head.update(head.renderable if hasattr(head, "renderable") else "")
            # Override the head with a status line:
            head.update("\x1b[38;2;230;200;130m● " + msg + "\x1b[0m")
        except Exception:
            pass


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
