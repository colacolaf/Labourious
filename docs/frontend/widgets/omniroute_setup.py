"""Inline OmniRoute setup widget.

The widget owns only form state and the asynchronous real connection test.
SettingsScreen owns persistence so secrets never enter config.json.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlsplit

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Static
from textual.widget import Widget


_DEFAULT_ENDPOINT = "http://localhost:20128/v1"
_DEFAULT_MODEL = "auto"


def normalize_endpoint(value: str) -> tuple[str | None, str | None]:
    """Return a safe normalized HTTP(S) base URL or a short validation error."""
    raw = (value or "").strip()
    if not raw:
        return None, "endpoint is required"
    if "://" not in raw:
        raw = "http://" + raw
    raw = raw.rstrip("/")
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None, "endpoint is not a valid URL"
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None, "use an http:// or https:// endpoint"
    if parsed.username or parsed.password:
        return None, "endpoint must not contain embedded credentials"
    if len(raw) > 500:
        return None, "endpoint is too long"
    return raw, None


def validate_model(value: str) -> tuple[str | None, str | None]:
    model = (value or "").strip()
    if not model:
        return None, "model is required"
    if any(ch.isspace() for ch in model) or len(model) > 160:
        return None, "model must be a short id without spaces"
    return model, None


class OmniRouteSetup(Widget):
    """Compact form for one OmniRoute gateway configuration."""

    class Saved(Message):
        def __init__(self, endpoint: str, model: str, api_key: str) -> None:
            super().__init__()
            self.endpoint = endpoint
            self.model = model
            self.api_key = api_key

    class Cancelled(Message):
        pass

    def __init__(
        self,
        *,
        endpoint: str = _DEFAULT_ENDPOINT,
        model: str = _DEFAULT_MODEL,
        has_key: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.add_class("omniroute-setup")
        self._initial_endpoint = endpoint or _DEFAULT_ENDPOINT
        self._initial_model = model or _DEFAULT_MODEL
        self._has_key = has_key
        self._tested_fingerprint: tuple[str, str, str] | None = None
        self._testing = False

    def compose(self) -> ComposeResult:
        yield Static(
            "OmniRoute · local OpenAI-compatible gateway",
            markup=False,
            classes="omni-title",
        )
        yield Static(
            "Test sends one minimal chat request. Keys are stored in the OS keychain, never config.json.",
            markup=False,
            classes="omni-help",
        )
        with Vertical(classes="omni-fields"):
            yield Static("endpoint", classes="omni-label")
            yield Input(
                value=self._initial_endpoint,
                placeholder=_DEFAULT_ENDPOINT,
                id="omni-endpoint",
            )
            yield Static("model", classes="omni-label")
            yield Input(
                value=self._initial_model,
                placeholder=_DEFAULT_MODEL,
                id="omni-model",
            )
            yield Static("API key · optional for fresh keyless installs", classes="omni-label")
            yield Input(
                placeholder=("saved in OS keychain · leave blank to keep it"
                             if self._has_key else "optional gateway key"),
                password=True,
                id="omni-key",
            )
        with Horizontal(classes="omni-actions"):
            yield Button("Test connection", id="omni-test", variant="primary")
            yield Button("Save", id="omni-save", variant="success", disabled=True)
            yield Button("Cancel", id="omni-cancel", variant="default")
        yield Static("○ not tested", markup=False, id="omni-status", classes="omni-status")

    def on_mount(self) -> None:
        self.query_one("#omni-endpoint", Input).focus()

    def on_input_changed(self, _event: Input.Changed) -> None:
        # Any edit invalidates the prior probe; Save must correspond to what
        # the user is actually about to persist.
        self._tested_fingerprint = None
        self._set_save_enabled(False)
        if not self._testing:
            self._set_status("○ not tested")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "omni-test":
            self._start_test()
        elif event.button.id == "omni-save":
            self._save_if_tested()
        elif event.button.id == "omni-cancel":
            self.post_message(self.Cancelled())

    def _values(self) -> tuple[tuple[str, str, str] | None, str | None]:
        endpoint, endpoint_err = normalize_endpoint(
            self.query_one("#omni-endpoint", Input).value
        )
        if endpoint_err:
            return None, endpoint_err
        model, model_err = validate_model(
            self.query_one("#omni-model", Input).value
        )
        if model_err:
            return None, model_err
        key = self.query_one("#omni-key", Input).value.strip()
        if len(key) > 500 or any(ch.isspace() for ch in key):
            return None, "API key contains whitespace or is too long"
        return (endpoint or "", model or "", key), None

    def _start_test(self) -> None:
        values, error = self._values()
        if error:
            self._set_status(f"× {error}", error=True)
            return
        assert values is not None
        self._testing = True
        self._tested_fingerprint = None
        self._set_save_enabled(False)
        self._set_status("↻ testing OmniRoute…")
        self.query_one("#omni-test", Button).disabled = True
        self.app.run_worker(self._test_connection(*values), exclusive=True)

    async def _test_connection(self, endpoint: str, model: str, key: str) -> None:
        try:
            from runtime.providers import probe_omniroute
            result = await asyncio.to_thread(
                probe_omniroute,
                endpoint,
                model,
                api_key=key or None,
                timeout_s=8.0,
            )
            if result.status == "OK":
                self._tested_fingerprint = (endpoint, model, key)
                latency = f" · {result.latency_ms}ms" if result.latency_ms is not None else ""
                self._set_status(f"✓ connected · {model}{latency}", success=True)
                self._set_save_enabled(True)
            else:
                self._set_status(
                    f"× {result.status.lower()} · {(result.error_message or 'request failed')[:140]}",
                    error=True,
                )
        except Exception as exc:
            self._set_status(f"× test failed · {type(exc).__name__}: {exc}", error=True)
        finally:
            self._testing = False
            self.query_one("#omni-test", Button).disabled = False

    def _save_if_tested(self) -> None:
        values, error = self._values()
        if error:
            self._set_status(f"× {error}", error=True)
            return
        assert values is not None
        if values != self._tested_fingerprint:
            self._set_status("× test the current values before saving", error=True)
            return
        self.post_message(self.Saved(*values))

    def _set_save_enabled(self, enabled: bool) -> None:
        try:
            self.query_one("#omni-save", Button).disabled = not enabled
        except Exception:
            pass

    def _set_status(
        self,
        text: str,
        *,
        success: bool = False,
        error: bool = False,
    ) -> None:
        try:
            status = self.query_one("#omni-status", Static)
            status.update(text)
            status.set_classes(
                "omni-status" + (" success" if success else " error" if error else "")
            )
        except Exception:
            pass


__all__ = ["OmniRouteSetup", "normalize_endpoint", "validate_model"]
