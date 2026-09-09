"""
welcome_wizard.py — first-run guided setup.

A modal Screen pushed on top of ChatScreen when no providers are configured.
Guides through 3 steps:
  1. Pick a provider (Ollama, Anthropic, OpenAI, OpenRouter, Gemini, OmniRoute)
  2. Pick a model (provider-specific curated list)
  3. Enter API key (if needed) or confirm → saves config → starts chat

Dismissed with Esc (skips wizard, stays on empty chat). The wizard writes
to ~/.labourious/config.json via config_io so the next launch skips it.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.events import Paste
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from frontend.config_io import load_config, save_config, Config, ProviderConfig
from frontend.providers import by_name as _provider_entry


# --- provider catalog (subset of providers.py for the wizard) ---

WIZARD_PROVIDERS = [
    {"id": "ollama",     "label": "Ollama (local)",        "desc": "Free, no key. Runs offline on your machine.",               "key_needed": False, "base_url": "http://localhost:11434",          "default_model": "llama3.3:70b"},
    {"id": "anthropic",  "label": "Anthropic (Claude)",    "desc": "Best reasoning. $3–15/1M tokens. API key required.",          "key_needed": True,  "base_url": "https://api.anthropic.com",       "default_model": "claude-sonnet-4-5"},
    {"id": "openai",     "label": "OpenAI (GPT-4o)",       "desc": "Fast, reliable. $2.50–10/1M tokens. API key required.",       "key_needed": True,  "base_url": "https://api.openai.com/v1",        "default_model": "gpt-4o"},
    {"id": "openrouter", "label": "OpenRouter",            "desc": "50+ free models, one API key. No payment needed for trials.",  "key_needed": True,  "base_url": "https://openrouter.ai/api/v1",      "default_model": "google/gemini-2.0-flash-001"},
    {"id": "google_ai_studio", "label": "Google AI Studio", "desc": "Gemini models. Free tier available. API key required.",        "key_needed": True,  "base_url": "https://generativelanguage.googleapis.com", "default_model": "gemini-2.0-flash"},
    {"id": "omniroute",  "label": "OmniRoute (gateway)",   "desc": "Local gateway. Auto-routes across 43 providers. No per-provider keys.", "key_needed": False, "base_url": "http://localhost:20128/v1",     "default_model": "auto"},
]

# Curated model lists per provider — FALLBACK ONLY. The model step asks
# the endpoint what it actually serves (ollama /api/tags, openai /models,
# …) via frontend.models_catalog; the curated list is used when the
# endpoint is unreachable or returns nothing.
WIZARD_MODELS: dict[str, list[str]] = {
    "ollama":     ["llama3.2:3b", "llama3.2:8b", "llama3.3:70b", "qwen2.5:72b", "deepseek-r1:70b"],
    "anthropic":  ["claude-sonnet-4-5", "claude-haiku-4", "claude-opus-4"],
    "openai":     ["gpt-4o", "gpt-4o-mini", "o3-mini"],
    "openrouter": ["google/gemini-2.0-flash-001", "meta-llama/llama-3.1-8b-instruct", "anthropic/claude-3-5-haiku", "mistralai/mistral-small"],
    "google_ai_studio": ["gemini-2.0-flash", "gemini-2.5-pro-preview"],
    "omniroute":  ["auto", "kimi/kimi-latest", "meta-llama/llama-3.3-70b-instruct"],
}

# Live discovery results per provider id, filled by the async fetch on
# step 1. Read by _models_for(); falls back to WIZARD_MODELS when absent.
_LIVE_MODELS: dict[str, list[str]] = {}


class WelcomeWizardScreen(ModalScreen):
    """First-run onboarding: provider → model → key → done.

    Modal so app-level bindings (s → Settings, h → History) don't fire
    while the wizard is open — otherwise typing "anthropic" would open
    unrelated screens.
    """

    # Class-level cursor defaults so render helpers work even on a bare
    # __new__-constructed instance (the smokes introspect them directly).
    _provider_cursor: int = 0
    _model_cursor: int = 0
    _provider_chosen: bool = False   # True once ↑/↓ moved the cursor

    # The key-paste Input lives in the flow (not a modal) so Esc/Enter
    # bindings keep working; hide it except on the key step.
    DEFAULT_CSS = """
    #wizard-key-input {
        display: none;
        height: 1;
        margin: 0 2 1 2;
    }
    """

    # Opt out of App.AUTO_FOCUS ("*"): auto-focus grabs the first focusable
    # widget on mount, and a display:none Input still counts as focusable —
    # it silently swallowed every typed provider id. Note `None` would just
    # inherit the App's "*" — an empty string is what actually disables it.
    # The wizard manages focus itself: none on steps 0/1 (screen bindings own
    # Enter/typing), the key Input focused when the key step shows it.
    AUTO_FOCUS = ""

    BINDINGS = [
        Binding("escape", "skip", "Skip", key_display="Esc"),
        Binding("enter",  "next", "Next", key_display="⏎"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._step = 0                 # 0=provider, 1=model, 2=key
        self._provider: dict | None = None
        self._model: str = ""
        self._api_key: str = ""
        self._provider_input: str = ""   # typed on step 0, resolved on Enter
        self._model_input: str = ""       # typed on step 1, resolved on Enter
        self._pending_error: str = ""     # last validation message
        # ↑/↓ selection cursors. Arrows move the ▶ cursor and mark the
        # provider as chosen; Enter then picks the item under the cursor.
        # Typing still works (explicit id). A fresh wizard with no arrow
        # press and no typed id stays on step 0 with a helpful error.
        self._provider_cursor: int = 0
        self._model_cursor: int = 0
        self._provider_chosen: bool = False

    def compose(self) -> ComposeResult:
        yield Static("", id="wizard-progress")
        yield Static("", id="wizard-body")
        # Step 2 (key entry) mounts a real Input over the body so long API
        # keys can be pasted; hidden on other steps.
        yield Input(
            placeholder="paste your API key here (right-click / Ctrl+V)",
            password=True,
            id="wizard-key-input",
        )
        with Horizontal(id="wizard-actions"):
            yield Button("← Back", id="wiz-back", variant="default", disabled=True)
            yield Button("Next →", id="wiz-next", variant="primary")

    def on_mount(self) -> None:
        self.redraw()
        # Prewarm live model discovery for the default provider so step 1
        # shows REAL installed models (ollama /api/tags) instead of the
        # curated fallback. Runs in a worker thread — never blocks the UI;
        # a dead endpoint just leaves the fallback list in place.
        if self._can_spawn_worker():
            self.run_worker(self._prewarm_models(), exclusive=False,
                            group="wizard-models", exit_on_error=False)

    def _can_spawn_worker(self) -> bool:
        """True only when this screen is attached to a running App.
        Bare __new__-constructed instances (smoke tests introspect them)
        have no message pump — workers must not be spawned there."""
        try:
            return self.app is not None and self._parent is not None
        except Exception:
            return False

    async def _prewarm_models(self) -> None:
        import asyncio
        from frontend.models_catalog import fetch_models_result
        try:
            result = await asyncio.to_thread(fetch_models_result, "ollama")
        except Exception:
            return
        if result.status == "ok" and result.models:
            _LIVE_MODELS["ollama"] = list(result.models)
            # If the user is already on step 1, refresh the list live.
            if self._step == 1 and self._provider \
                    and self._provider["id"] == "ollama":
                self._model_cursor = min(self._model_cursor,
                                         len(result.models) - 1)
                self._render_step()

    def _kick_live_models(self, pid: str) -> None:
        """Fire a background discovery fetch for the provider the user just
        picked, so step 1's list is LIVE (ollama /api/tags, openai /models…)
        rather than the curated fallback. Never blocks — the step renders
        with fallback immediately and re-renders when the fetch lands.
        Skips silently when not attached to a running app (bare smoke
        instances have no message pump to spawn workers on)."""
        if pid in _LIVE_MODELS:  # already have (or fetching) live data
            return
        if not self._can_spawn_worker():
            return
        import asyncio
        from frontend.models_catalog import fetch_models_result
        entry = _provider_entry(pid)
        if entry is None:
            return

        async def _fetch() -> None:
            try:
                result = await asyncio.to_thread(
                    fetch_models_result, pid,
                    base_url=entry.base_url, force=False)
            except Exception:
                return
            if result.status == "ok" and result.models:
                _LIVE_MODELS[pid] = list(result.models)
                if (self._step == 1 and self._provider
                        and self._provider["id"] == pid):
                    self._model_cursor = min(self._model_cursor,
                                             len(result.models) - 1)
                    self._render_step()

        try:
            self.run_worker(_fetch(), exclusive=False,
                            group=f"wizard-models-{pid}", exit_on_error=False)
        except Exception:
            pass  # never let discovery break the wizard

    def on_focus(self, _event) -> None:  # noqa: N802 — Textual handler name
        # Guard against the hidden key Input grabbing focus on mount: a
        # focused-but-hidden Input silently swallows every typed key
        # (provider ids, model ids), which bricked steps 0 and 1.
        try:
            key_input = self.query_one("#wizard-key-input", Input)
            if not key_input.display and self.focused is key_input:
                self.set_focus(None)
        except Exception:
            pass

    # -------------------------------------------------- rendering
    # NOTE: named `redraw`, NOT `_render` — overriding Textual's internal
    # Widget._render() (which must return a Rich renderable) with a
    # None-returning method crashes the paint pipeline with
    # `AttributeError: 'NoneType' object has no attribute 'render_strips'`.
    def redraw(self) -> None:
        self._render_progress()
        self._render_step()
        self._render_actions()

    def _render_progress(self) -> None:
        steps = ["1. Provider", "2. Model", "3. Key & done"]
        parts = []
        for i, s in enumerate(steps):
            if i < self._step:
                parts.append(f"[green]● {s}[/]")
            elif i == self._step:
                parts.append(f"[bold cyan]▶ {s}[/]")
            else:
                parts.append(f"[dim]○ {s}[/]")
        self.query_one("#wizard-progress", Static).update("  " + "  →  ".join(parts))

    def _render_step(self) -> None:
        body = self.query_one("#wizard-body", Static)
        if self._step == 0:
            body.update(self._provider_step())
        elif self._step == 1:
            body.update(self._model_step())
        else:
            body.update(self._key_step())

    def _render_actions(self) -> None:
        back = self.query_one("#wiz-back", Button)
        next_btn = self.query_one("#wiz-next", Button)
        back.disabled = self._step == 0
        if self._step == 2 and self._provider and not self._provider["key_needed"]:
            next_btn.label = "✓ Finish"
        elif self._step == 2:
            next_btn.label = "✓ Save & start"
        else:
            next_btn.label = "Next →"
        # The paste field only exists on the key step. A display:none
        # widget can still HOLD focus in Textual, so when hiding it we
        # explicitly move focus back to the screen — otherwise typed keys
        # vanish into the hidden buffer.
        try:
            key_input = self.query_one("#wizard-key-input", Input)
            key_input.display = (
                self._step == 2 and self._provider is not None
                and bool(self._provider["key_needed"])
            )
            if key_input.display:
                key_input.value = self._api_key
                key_input.focus()
            elif self.focused is key_input:
                self.set_focus(None)
        except Exception:
            pass

    # -------------------------------------------------- step content
    def _provider_step(self) -> str:
        lines = [
            "[bold]Welcome to Labourious[/] — the analyst's bench.\n",
            "Choose a provider to get started.\n",
        ]
        for p in WIZARD_PROVIDERS:
            tag = "[green]free · no key[/]" if not p["key_needed"] else "[yellow]key required[/]"
            lines.append(f"  [bold cyan]{p['id']}[/]  {p['label']}  {tag}")
            lines.append(f"    [dim]{p['desc']}[/]\n")
        # Selection list: ▶ marks the arrow-key cursor; ✓ marks the default.
        for i, p in enumerate(WIZARD_PROVIDERS):
            marker = "[bold cyan]▶[/]" if i == self._provider_cursor else " "
            lines.append(f"  {marker} [bold cyan]{p['id']}[/]  {p['label']}")
        lines.append("")
        lines.append("[dim]↑/↓ to choose · Enter to confirm · or type a provider id · Esc skips[/]")
        lines.append("")
        lines.append("[bold cyan]▶ " + (self._provider_input or "type a provider id…") + "[/]")
        if self._pending_error:
            lines.append(f"\n[yellow]⚠ {self._pending_error}[/]")
        return "\n".join(lines)

    def _models_for(self, pid: str) -> list[str]:
        """Models offered on step 1: live discovery results when the
        endpoint answered, else the curated list."""
        live = _LIVE_MODELS.get(pid)
        if live:
            return live
        return WIZARD_MODELS.get(pid, [])

    def _model_step(self) -> str:
        if not self._provider:
            return ""
        pid = self._provider["id"]
        models = self._models_for(pid) or [self._provider["default_model"]]
        lines = [
            f"[bold]Provider:[/] [cyan]{self._provider['label']}[/]\n",
            "[bold]Choose a model:[/]\n",
        ]
        for i, m in enumerate(models):
            marker = "[bold cyan]▶[/]" if i == self._model_cursor else " "
            lines.append(f"  {marker} {m}")
        current = self._model_input or self._provider["default_model"]
        lines.append("\n[bold cyan]Type> " + current + "[/]")
        lines.append("[dim]↑/↓ pick · type a model name · Enter (blank = default)[/]")
        if not _LIVE_MODELS.get(pid):
            lines.append("[dim]· showing suggested models — live list unavailable" +
                         (" (is the server running?)" if pid == "ollama" else "") + "[/]")
        if self._pending_error:
            lines.append(f"\n[yellow]⚠ {self._pending_error}[/]")
        return "\n".join(lines)

    def _key_step(self) -> str:
        if not self._provider:
            return ""
        if not self._provider["key_needed"]:
            lines = [
                f"[bold]Provider:[/] [cyan]{self._provider['label']}[/] — [green]no key needed[/]\n",
                f"[bold]Model:[/] [cyan]{self._model}[/]\n",
                "\n[bold green]Ready to start![/] Press Enter to finish.\n",
                f"\n[dim]This will set {self._provider['id']}/{self._model} as your default.[/]",
            ]
            return "\n".join(lines)
        masked = ("•" * min(len(self._api_key), 48)) if self._api_key else "(nothing pasted yet)"
        lines = [
            f"[bold]Provider:[/] [cyan]{self._provider['label']}[/]\n",
            f"[bold]Model:[/] [cyan]{self._model}[/]\n",
            "\n[bold]Paste your API key into the field below:[/]\n",
            f"[dim]Right-click → Paste, or Ctrl+V — bracketed paste is supported, "
            f"multi-line pastes are flattened.[/]\n",
            f"\n[dim]Key on file: {masked}[/]",
            f"\n[dim]The key is stored in your OS keychain (not in plaintext).[/]",
            f"[dim]Skip with Esc — you can add keys later in Settings → Providers.[/]",
        ]
        return "\n".join(lines)

    # -------------------------------------------------- actions
    def _resolve_provider(self) -> dict | None:
        """Match the typed provider id (case-insensitive) against the catalog.

        Blank input resolves to the item under the ↑/↓ cursor (default:
        the first provider), so pure arrow-key selection works. A non-blank
        id that matches nothing returns None.
        """
        query = self._provider_input.strip().lower()
        if not query:
            # Blank input: the ↑/↓ cursor's item, but only if the user
            # actually moved the cursor (or picked earlier). Otherwise
            # nothing is chosen yet — error out with the id list.
            if self._provider_chosen or self._provider is not None:
                return WIZARD_PROVIDERS[self._provider_cursor % len(WIZARD_PROVIDERS)]
            return self._provider
        for p in WIZARD_PROVIDERS:
            if p["id"] == query:
                return p
        return None

    def _resolve_model(self) -> str | None:
        """Return the chosen model for the provider.

        Blank input → the FIRST LIVE model when discovery answered (the
        user's server actually serves it), else the curated default.
        Typed names must be in the provider's model list — live results
        first, curated list second (case-insensitive).
        """
        if not self._provider:
            return None
        pid = self._provider["id"]
        query = self._model_input.strip().lower()
        if not query:
            # Blank Enter: the first LIVE model when discovery answered
            # (this server really serves it), else the curated default.
            live = _LIVE_MODELS.get(pid)
            if live:
                return live[self._model_cursor % len(live)]
            return self._provider["default_model"]
        for m in self._models_for(pid):
            if m.lower() == query:
                return m
        return None

    def action_next(self) -> None:
        if self._step == 0:
            provider = self._resolve_provider()
            if provider is None:
                if not self._provider_input.strip():
                    self._pending_error = (
                        "no provider selected — press ↑/↓ to choose, or type an id: "
                        + ", ".join(p["id"] for p in WIZARD_PROVIDERS)
                    )
                else:
                    self._pending_error = (
                        "unknown provider — type one of: "
                        + ", ".join(p["id"] for p in WIZARD_PROVIDERS)
                    )
                self._render_step()
                return
            if provider is not self._provider:
                self._provider = provider
                self._model_input = ""
                self._model_cursor = 0
                self._kick_live_models(provider["id"])
            self._pending_error = ""
            self._step = 1
            self.redraw()
            return
        if self._step == 1:
            # Blank input resolves via _resolve_model (first live model,
            # else the curated default). A moved cursor already set
            # _model_input in on_key, so nothing to stuff here.
            model = self._resolve_model()
            if model is None:
                self._pending_error = "unknown model — pick one from the list (or leave blank for default)"
                self._render_step()
                return
            self._model = model
            self._pending_error = ""
            self._step = 2
            self.redraw()
            return
        if self._step == 2:
            self._save_and_dismiss()
            return

    # -------------------------------------------------- key input wiring
    def _sync_key_input(self) -> None:
        """Pull the Input's value into `_api_key` (keeps the smoke-tested
        `_api_key` attribute as the single source of truth)."""
        try:
            self._api_key = self.query_one("#wizard-key-input", Input).value.strip()
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "wizard-key-input":
            # Flatten multi-line pastes: keys never contain newlines.
            cleaned = "".join(str(event.value).split())
            if cleaned != event.value:
                event.input.value = cleaned
            self._api_key = cleaned

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter inside the key Input advances the wizard.

        The focused Input consumes Enter (its own submit binding) before
        the screen's `enter → next` binding can fire, so the final Enter
        after pasting a key would otherwise do nothing.
        """
        if event.input.id == "wizard-key-input":
            self._sync_key_input()
            event.stop()
            event.prevent_default()
            self.action_next()

    def on_paste(self, event: Paste) -> None:
        """Bracketed-paste safety net for the key step.

        Textual delivers a terminal paste as a Paste event. The focused
        Input consumes it natively when focused; this handler covers the
        case where focus is elsewhere (or the driver splits the paste) so
        the key still lands in `_api_key` instead of being eaten char by
        char by on_key's printable-character capture.
        """
        if (self._step == 2 and self._provider is not None
                and self._provider["key_needed"]):
            text = "".join(str(event.text).split())
            self._api_key = text
            try:
                self.query_one("#wizard-key-input", Input).value = text
            except Exception:
                pass
            self._render_step()
            event.stop()
            event.prevent_default()

    def action_back(self) -> None:
        if self._step > 0:
            self._step -= 1
            self._pending_error = ""
            self.redraw()

    def action_skip(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "wiz-next":
            self.action_next()
        elif event.button.id == "wiz-back":
            self.action_back()

    def on_key(self, event) -> None:
        """Accumulate typed input per step. Enter is handled by the BINDINGS
        ('enter' → action_next), so resolution lives in action_next.

        Consumed characters stop propagation so they never reach parent
        screens or the app (defense in depth on top of ModalScreen).
        """
        handled = False
        if self._step == 0:
            if event.key == "up":
                n = len(WIZARD_PROVIDERS)
                self._provider_cursor = (self._provider_cursor - 1) % n
                self._provider_chosen = True
                self._pending_error = ""
                handled = True
            elif event.key == "down":
                n = len(WIZARD_PROVIDERS)
                self._provider_cursor = (self._provider_cursor + 1) % n
                self._provider_chosen = True
                self._pending_error = ""
                handled = True
            elif event.key == "backspace":
                self._provider_input = self._provider_input[:-1]
                self._pending_error = ""
                handled = True
            elif event.character and event.character.isprintable():
                self._provider_input += event.character
                self._pending_error = ""
                handled = True
            if handled:
                event.stop()
                self._render_step()
        elif self._step == 1:
            models = self._models_for(
                self._provider["id"] if self._provider else "")
            if event.key == "up":
                if models:
                    self._model_cursor = (self._model_cursor - 1) % len(models)
                    self._model_input = models[self._model_cursor]
                self._pending_error = ""
                handled = True
            elif event.key == "down":
                if models:
                    self._model_cursor = (self._model_cursor + 1) % len(models)
                    self._model_input = models[self._model_cursor]
                self._pending_error = ""
                handled = True
            elif event.key == "backspace":
                self._model_input = self._model_input[:-1]
                self._pending_error = ""
                handled = True
            elif event.character and event.character.isprintable():
                self._model_input += event.character
                self._pending_error = ""
                handled = True
            if handled:
                self._render_step()
        elif self._step == 2:
            # The paste Input owns keyboard entry on the key step when it is
            # visible (a widget-level on_key runs before this screen handler
            # and Input stops printable keys itself) — anything reaching here
            # is a stray key while focus is elsewhere. Don't echo it into a
            # hidden buffer: the visible masked state comes from _api_key via
            # on_input_changed / on_paste only.
            if (self._provider is not None and self._provider["key_needed"]
                    and not self._key_input_visible()):
                if event.character and event.character.isprintable():
                    self._api_key += event.character
                    handled = True
                elif event.key == "backspace":
                    self._api_key = self._api_key[:-1]
                    handled = True
                if handled:
                    self._render_step()
        if handled:
            event.stop()

    # -------------------------------------------------- persistence
    def _key_input_visible(self) -> bool:
        try:
            return self.query_one("#wizard-key-input", Input).display
        except Exception:
            return False

    def _save_and_dismiss(self) -> None:
        if (self._step == 2 and self._provider is not None
                and self._provider["key_needed"]):
            self._sync_key_input()
        cfg = load_config()
        pid = self._provider["id"]
        base_url = self._provider["base_url"]

        # Build provider config
        env_var = f"{pid.upper()}_API_KEY" if self._provider["key_needed"] else None
        cfg.providers[pid] = ProviderConfig(name=pid, base_url=base_url, api_key_env=env_var)

        # Set defaults
        model_str = f"{pid}/{self._model}"
        cfg.default_model = model_str

        # Save API key to keychain if provided
        if self._api_key and self._provider["key_needed"]:
            try:
                from frontend.keys_storage import set_key
                set_key(pid, self._api_key)
            except Exception:
                import os
                os.environ[env_var] = self._api_key

        save_config(cfg)
        self.dismiss(model_str)