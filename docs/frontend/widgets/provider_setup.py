"""
provider_setup.py — the per-provider connect form for Settings → Providers.

Every provider gets its OWN connection settings because they genuinely
differ: local servers take an endpoint but no key, cloud providers take
a pasted key, OpenAI-compatible ones may override both, and model lists
are provider-specific. One generic form covers all of them by rendering
only the fields the selected provider actually has.

The form owns only form state + the asynchronous real connection test
(probe_provider_form → same adapter the production flow uses). Persistence
lives in SettingsScreen so secrets never enter config.json — keys go to
the OS keychain via keys_storage, endpoints/models to config.json.

Mirrors OmniRouteSetup's UX contract (test must pass before Save) so
muscle memory transfers.
"""

from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Static
from textual.widget import Widget

from frontend.providers import ProviderEntry
from frontend.widgets.omniroute_setup import normalize_endpoint


def validate_model_id(value: str) -> tuple[str | None, str | None]:
    """Return (clean_id, error). Short, space-free model id."""
    model = (value or "").strip()
    if not model:
        return None, "model is required"
    if any(ch.isspace() for ch in model) or len(model) > 160:
        return None, "model must be a short id without spaces"
    return model, None


def validate_api_key(value: str) -> tuple[str | None, str | None]:
    """Return (clean_key, error). Keys may contain most printable chars
    but not whitespace (keys are never whitespace-delimited)."""
    key = (value or "").strip()
    if not key:
        return None, None  # blank is allowed (means: remove / keep stored)
    if any(ch.isspace() for ch in key) or len(key) > 500:
        return None, "API key contains whitespace or is too long"
    return key, None


class ProviderSetup(Widget):
    """Connect form for ONE provider — fields tailored to its entry."""

    class Saved(Message):
        """Posted on Save after a passing test. Carries the exact tuple tested."""

        def __init__(self, provider: str, endpoint: str | None, model: str,
                     api_key: str) -> None:
            super().__init__()
            self.provider = provider
            self.endpoint = endpoint          # None = keep provider default
            self.model = model
            self.api_key = api_key            # "" = clear / none stored

    class Cancelled(Message):
        pass

    def __init__(self, entry: ProviderEntry, *, has_key: bool = False,
                 endpoint_override: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.add_class("provider-setup")
        self._entry = entry
        self._has_key = has_key
        self._endpoint_override = endpoint_override
        self._tested_fingerprint: tuple | None = None
        self._testing = False

    # ------------------------------------------------------------- helpers
    @property
    def _is_local(self) -> bool:
        return self._entry.tier == "local"

    def _endpoint_label(self) -> str:
        if self._is_local:
            return "endpoint"
        return "endpoint · OpenAI-compatible override (blank = official API)"

    def _models_line(self, models: tuple[str, ...] | list[str] | None = None) -> str:
        models = self._entry.models if models is None else models
        if not models:
            return "type any model id this endpoint serves"
        shown = "  ".join(list(models)[:5])
        if len(models) > 5:
            shown += f"  +{len(models) - 5}"
        return shown

    # ------------------------------------------------------------- compose
    def compose(self) -> ComposeResult:
        e = self._entry
        yield Static(
            f"{e.display} · connect",
            markup=False,
            classes="omni-title",
        )
        yield Static(
            e.description,
            markup=False,
            classes="omni-help",
        )
        with Vertical(classes="omni-fields"):
            # Endpoint — shown for every provider. Locals need it to point
            # at their server; cloud users can leave it blank for the
            # official API (or override for proxies/self-hosted gateways).
            yield Static(self._endpoint_label(), classes="omni-label")
            yield Input(
                value=self._endpoint_override or (e.base_url or ""),
                placeholder=e.base_url or "https://…/v1",
                id="prv-endpoint",
            )
            # Model — input seeded with the default. The 'available' line
            # refreshes with LIVE models fetched from the endpoint
            # (ollama /api/tags, openai /models, …) via _refresh_models();
            # until that lands it shows the curated fallback list.
            yield Static(f"model · available: {self._models_line()}",
                         classes="omni-label", id="prv-models-label")
            yield Input(
                value=e.default_model,
                placeholder=e.default_model,
                id="prv-model",
            )
            # API key — only for providers that take one.
            if e.env_var:
                yield Static(
                    f"API key · stored in OS keychain · env fallback {e.env_var}",
                    classes="omni-label",
                )
                yield Input(
                    placeholder=("saved in OS keychain · leave blank to keep it"
                                 if self._has_key else
                                 f"paste your {e.display} key here"),
                    password=True,
                    id="prv-key",
                )
        with Horizontal(classes="omni-actions"):
            yield Button("Test connection", id="prv-test", variant="primary")
            yield Button("Save", id="prv-save", variant="success", disabled=True)
            yield Button("Cancel", id="prv-cancel", variant="default")
        yield Static("\u25cb not tested", markup=False,
                     id="prv-status", classes="omni-status")

    def on_mount(self) -> None:
        self.query_one("#prv-endpoint", Input).focus()
        self._refresh_models()

    # ------------------------------------------------------------- live model discovery
    def _refresh_models(self, *, force: bool = False) -> None:
        """Fetch the endpoint's live model list in a worker thread and
        update the 'available' line. Falls back to the curated list with
        an honest hint when the endpoint is unreachable."""
        endpoint = ""
        try:
            endpoint = self.query_one("#prv-endpoint", Input).value.strip()
        except Exception:
            pass
        key = ""
        if self._entry.env_var:
            try:
                key = self.query_one("#prv-key", Input).value.strip()
            except Exception:
                pass
        # Only spawn when attached to a running app (bare instances in
        # smokes have no message pump).
        if self.is_attached:
            self.app.run_worker(
                self._fetch_models_worker(endpoint, key, force), exclusive=True,
                group="prv-models", exit_on_error=False,
            )

    async def _fetch_models_worker(self, endpoint: str, key: str,
                                   force: bool) -> None:
        from frontend.models_catalog import fetch_models_result
        try:
            result = await asyncio.to_thread(
                fetch_models_result,
                self._entry.name,
                base_url=endpoint or None,
                api_key=key or None,
                force=force,
            )
        except Exception:
            return  # never let discovery break the form
        try:
            label = self.query_one("#prv-models-label", Static)
        except Exception:
            return
        if result.status == "ok":
            label.update(
                f"model · available: {self._models_line(result.models)}"
                f"  \u00b7 {result.detail}")
        else:
            hint = {
                "unreachable": "endpoint down — showing curated defaults",
                "auth": "key needed to list models — showing curated defaults",
                "error": result.detail[:80],
            }.get(result.status, result.detail[:80])
            label.update(
                f"model · available: {self._models_line(result.fallback)}"
                f"  \u00b7 {hint}")

    # ------------------------------------------------------------- events
    def on_input_changed(self, event: Input.Changed) -> None:
        # Any edit invalidates the prior probe; Save must correspond to what
        # the user is actually about to persist.
        self._tested_fingerprint = None
        self._set_save_enabled(False)
        if not self._testing:
            self._set_status("\u25cb not tested")
        # Endpoint/key edits re-point discovery; worker group is exclusive
        # so rapid typing collapses into one in-flight fetch.
        if event.input.id in ("prv-endpoint", "prv-key"):
            self._refresh_models(force=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "prv-test":
            self._start_test()
        elif event.button.id == "prv-save":
            self._save_if_tested()
        elif event.button.id == "prv-cancel":
            self.post_message(self.Cancelled())

    # ------------------------------------------------------------- values
    def _values(self) -> tuple[tuple[str, str, str] | None, str | None]:
        """Collect + validate the form. Returns (endpoint, model, key) or error."""
        endpoint, err = normalize_endpoint(
            self.query_one("#prv-endpoint", Input).value)
        if err:
            return None, err
        model, err = validate_model_id(
            self.query_one("#prv-model", Input).value)
        if err:
            return None, err
        key = ""
        if self._entry.env_var:
            key, err = validate_api_key(
                self.query_one("#prv-key", Input).value)
            if err:
                return None, err
        assert endpoint is not None and model is not None
        return (endpoint, model, key or ""), None

    # ------------------------------------------------------------- test
    def _start_test(self) -> None:
        values, error = self._values()
        if error:
            self._set_status(f"\u00d7 {error}", error=True)
            return
        assert values is not None
        self._testing = True
        self._tested_fingerprint = None
        self._set_save_enabled(False)
        self._set_status("\u21bb testing\u2026")
        self.query_one("#prv-test", Button).disabled = True
        self.app.run_worker(self._test_connection(*values), exclusive=True)

    async def _test_connection(self, endpoint: str, model: str, key: str) -> None:
        try:
            from runtime.providers import probe_provider_form
            result = await asyncio.to_thread(
                probe_provider_form,
                self._entry.name,
                model,
                api_key=key or None,
                base_url=endpoint or None,
                timeout_s=8.0,
            )
            if result.status == "OK":
                self._tested_fingerprint = (endpoint, model, key)
                latency = (f" · {result.latency_ms}ms"
                           if result.latency_ms is not None else "")
                self._set_status(f"\u2713 connected · {model}{latency}",
                                 success=True)
                self._set_save_enabled(True)
            else:
                self._set_status(
                    f"\u00d7 {result.status.lower()} · "
                    f"{(result.error_message or 'request failed')[:140]}",
                    error=True,
                )
        except Exception as exc:
            self._set_status(
                f"\u00d7 test failed · {type(exc).__name__}: {exc}", error=True)
        finally:
            self._testing = False
            try:
                self.query_one("#prv-test", Button).disabled = False
            except Exception:
                pass

    # ------------------------------------------------------------- save
    def _save_if_tested(self) -> None:
        values, error = self._values()
        if error:
            self._set_status(f"\u00d7 {error}", error=True)
            return
        assert values is not None
        if values != self._tested_fingerprint:
            self._set_status("\u00d7 test the current values before saving",
                             error=True)
            return
        self.post_message(self.Saved(self._entry.name, *values))

    # ------------------------------------------------------------- status
    def _set_save_enabled(self, enabled: bool) -> None:
        try:
            self.query_one("#prv-save", Button).disabled = not enabled
        except Exception:
            pass

    def _set_status(self, text: str, *, success: bool = False,
                    error: bool = False) -> None:
        try:
            status = self.query_one("#prv-status", Static)
            status.update(text)
            status.set_classes(
                "omni-status"
                + (" success" if success else " error" if error else "")
            )
        except Exception:
            pass


__all__ = ["ProviderSetup", "validate_model_id", "validate_api_key"]
