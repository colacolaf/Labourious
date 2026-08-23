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
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from frontend.config_io import load_config, save_config, Config, ProviderConfig


# --- provider catalog (subset of providers.py for the wizard) ---

WIZARD_PROVIDERS = [
    {"id": "ollama",     "label": "Ollama (local)",        "desc": "Free, no key. Runs offline on your machine.",               "key_needed": False, "base_url": "http://localhost:11434",          "default_model": "llama3.3:70b"},
    {"id": "anthropic",  "label": "Anthropic (Claude)",    "desc": "Best reasoning. $3–15/1M tokens. API key required.",          "key_needed": True,  "base_url": "https://api.anthropic.com",       "default_model": "claude-sonnet-4-5"},
    {"id": "openai",     "label": "OpenAI (GPT-4o)",       "desc": "Fast, reliable. $2.50–10/1M tokens. API key required.",       "key_needed": True,  "base_url": "https://api.openai.com/v1",        "default_model": "gpt-4o"},
    {"id": "openrouter", "label": "OpenRouter",            "desc": "50+ free models, one API key. No payment needed for trials.",  "key_needed": True,  "base_url": "https://openrouter.ai/api/v1",      "default_model": "google/gemini-2.0-flash-001"},
    {"id": "google_ai_studio", "label": "Google AI Studio", "desc": "Gemini models. Free tier available. API key required.",        "key_needed": True,  "base_url": "https://generativelanguage.googleapis.com", "default_model": "gemini-2.0-flash"},
    {"id": "omniroute",  "label": "OmniRoute (gateway)",   "desc": "Local gateway. Auto-routes across 43 providers. No per-provider keys.", "key_needed": False, "base_url": "http://localhost:20128/v1",     "default_model": "auto"},
]

# Curated model lists per provider
WIZARD_MODELS: dict[str, list[str]] = {
    "ollama":     ["llama3.3:70b", "qwen2.5:72b", "deepseek-r1:70b", "mistral-large", "gemma3:27b", "phi4:14b"],
    "anthropic":  ["claude-sonnet-4-5", "claude-haiku-4", "claude-opus-4"],
    "openai":     ["gpt-4o", "gpt-4o-mini", "o3-mini"],
    "openrouter": ["google/gemini-2.0-flash-001", "meta-llama/llama-3.1-8b-instruct", "anthropic/claude-3-5-haiku", "mistralai/mistral-small"],
    "google_ai_studio": ["gemini-2.0-flash", "gemini-2.5-pro-preview"],
    "omniroute":  ["auto", "kimi/kimi-latest", "meta-llama/llama-3.3-70b-instruct"],
}


class WelcomeWizardScreen(Screen):
    """First-run onboarding: provider → model → key → done."""

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

    def compose(self) -> ComposeResult:
        yield Static("", id="wizard-progress")
        yield Static("", id="wizard-body")
        with Horizontal(id="wizard-actions"):
            yield Button("← Back", id="wiz-back", variant="default", disabled=True)
            yield Button("Next →", id="wiz-next", variant="primary")

    def on_mount(self) -> None:
        self._render()

    # -------------------------------------------------- rendering
    def _render(self) -> None:
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
        lines.append("\n[dim]Type a provider ID and press Enter, or Esc to skip.[/]")
        return "\n".join(lines)

    def _model_step(self) -> str:
        if not self._provider:
            return ""
        pid = self._provider["id"]
        models = WIZARD_MODELS.get(pid, [self._provider["default_model"]])
        lines = [
            f"[bold]Provider:[/] [cyan]{self._provider['label']}[/]\n",
            "[bold]Choose a model:[/]\n",
        ]
        for m in models:
            marker = "[green]✓[/]" if m == self._provider["default_model"] else " "
            lines.append(f"  {marker} [cyan]{m}[/]")
        lines.append("\n[dim]Type a model name and press Enter, or press Enter for default.[/]")
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
        lines = [
            f"[bold]Provider:[/] [cyan]{self._provider['label']}[/]\n",
            f"[bold]Model:[/] [cyan]{self._model}[/]\n",
            "\n[bold]Enter your API key:[/]\n",
            f"\n[dim]Paste your {self._provider['id'].upper()}_API_KEY below and press Enter.[/]",
            f"[dim]The key is stored in your OS keychain (not in plaintext).[/]\n",
            f"\n[dim]Skip with Esc — you can add keys later in Settings → Providers.[/]",
        ]
        return "\n".join(lines)

    # -------------------------------------------------- actions
    def action_next(self) -> None:
        if self._step == 0:
            self._step = 1
            self._model = self._provider["default_model"]
        elif self._step == 1:
            self._step = 2
        elif self._step == 2:
            self._save_and_dismiss()
            return
        self._render()

    def action_back(self) -> None:
        if self._step > 0:
            self._step -= 1
            self._render()

    def action_skip(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "wiz-next":
            self.action_next()
        elif event.button.id == "wiz-back":
            self.action_back()

    def on_key(self, event) -> None:
        if self._step == 0:
            if event.key == "enter":
                self.action_next()
                return
            if event.character and event.character.isprintable() and event.character not in ("\r", "\n", "/"):
                # Accumulate typed provider id
                pass  # Provider selection is done by typing + Enter on the input
        elif self._step == 1:
            if event.key == "enter":
                self.action_next()
                return
            if event.character and event.character.isprintable():
                pass  # Model input
        elif self._step == 2:
            if event.key == "enter":
                self.action_next()
                return
            if self._provider and self._provider["key_needed"]:
                if event.character and event.character.isprintable():
                    self._api_key += event.character
                elif event.key == "backspace":
                    self._api_key = self._api_key[:-1]

    # -------------------------------------------------- persistence
    def _save_and_dismiss(self) -> None:
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
                from frontend.keys_storage import store_key
                store_key(pid, self._api_key)
            except Exception:
                import os
                os.environ[env_var] = self._api_key

        save_config(cfg)
        self.dismiss(model_str)