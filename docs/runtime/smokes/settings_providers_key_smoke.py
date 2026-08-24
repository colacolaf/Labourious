"""settings_providers_key_smoke.py — Settings → Providers key round-trip.

Drives the REAL app (real LabouriousApp → real SettingsScreen) with real
key events through Settings → Providers → add omniroute → the OmniRoute
setup form, and verifies the API key round-trips through the keychain:

  SAVE   — typing a key + Test connection (REAL HTTP to a local mock
           OmniRoute gateway) + Save stores it via keys_storage.set_key.
           Assert: get_key("omniroute") == key, key_present True, the
           secret is ABSENT from config.json (never written to disk in
           plaintext), and the providers panel reports key-loaded.
  KEEP   — reopening the form with the key field blank + Save keeps the
           existing key ("leave blank to keep it").
  DELETE — delete_key() clears it; the panel + status reflect auth-missing.

The mock gateway is a real HTTP server (127.0.0.1:random-port) that
answers POST /chat/completions the way OmniRoute does, so the entire
probe path (TCP probe → OpenAI-compat chat request) is exercised for
real — no function mocking.

Hermetic: temp HOME + LABOURIOUS_TEST (file keychain backend under the
temp HOME), and OMNIROUTE_API_KEY cleared so the adapter can't fall back
to a developer's real env var.

Run: PYTHONPATH=docs python3 docs/runtime/smokes/settings_providers_key_smoke.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import threading
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# --- isolate everything before importing frontend modules -------------------
_TMP = Path(tempfile.mkdtemp(prefix="settings-key-"))
os.environ["HOME"] = str(_TMP)
os.environ["LABOURIOUS_CONFIG"] = str(_TMP / "config.json")
os.environ["LABOURIOUS_TEST"] = "1"
os.environ.pop("OMNIROUTE_API_KEY", None)
os.environ.pop("OPENAI_COMPAT_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from frontend.app import LabouriousApp  # noqa: E402
from frontend.screens.settings import SettingsScreen  # noqa: E402
from frontend.screens.chat import ChatScreen  # noqa: E402
from frontend.keys_storage import get_key, set_key, delete_key, key_present  # noqa: E402

ok = 0
fails: list[str] = []


def step(desc: str, cond: bool) -> None:
    global ok
    if cond:
        ok += 1
    else:
        fails.append(desc)
        print(f"  ✗ FAIL {desc}")


# ---------------------------------------------------------- mock OmniRoute
class _MockOmniRoute(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 (http.server API)
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)  # body not needed for the probe
        body = json.dumps({
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 0,
            "model": "auto",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: object) -> None:  # silence
        pass


class _Gateway:
    """Real local OmniRoute-compatible server for the test-connection probe."""

    def __init__(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _MockOmniRoute)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"


@asynccontextmanager
async def launch():
    # Seed a provider so the welcome wizard does NOT auto-push; we want to
    # land directly on ChatScreen and open Settings ourselves.
    (_TMP / "config.json").write_text(json.dumps({
        "providers": {"ollama": {"base_url": "http://localhost:11434"}},
        "default_model": "ollama/llama3.3:70b",
    }))
    app = LabouriousApp()
    async with app.run_test(size=(140, 44)) as pilot:
        await pilot.pause(0.3)
        yield pilot, app


async def open_omniroute_form(pilot, app) -> None:
    """Real keys: `s` → Settings; Ctrl+N → picker; type id; Enter → form."""
    await pilot.press("s")
    await pilot.pause(0.2)
    step("Settings opened (providers rail)", isinstance(app.screen, SettingsScreen))
    await pilot.press("ctrl+n")
    await pilot.pause(0.2)
    step("picker open", app.screen._picker_open)
    # type the provider id to filter the picker to a single match
    await pilot.press(*"omniroute")
    await pilot.pause(0.2)
    await pilot.press("enter")
    await pilot.pause(0.3)
    step("OmniRoute setup form open", app.screen._omniroute_setup_open)


async def main() -> None:
    gateway = _Gateway()
    gateway.start()
    try:
        # ── A. SAVE round-trip: type key → test (real HTTP) → save ─────────
        print("A. Save round-trip (keychain)")
        async with launch() as (pilot, app):
            await open_omniroute_form(pilot, app)
            form = app.screen._omniroute_setup
            from textual.widgets import Input, Button
            form.query_one("#omni-endpoint", Input).value = gateway.endpoint
            form.query_one("#omni-model", Input).value = "auto"
            form.query_one("#omni-key", Input).value = "omni-secret-123"
            await pilot.click("#omni-test")
            await pilot.pause(0.8)  # real HTTP round-trip
            step("test connection passed (real HTTP)",
                 form.query_one("#omni-save", Button).disabled is False)
            status = form.query_one("#omni-status").renderable
            step("status shows connected", "connected" in str(status))
            await pilot.click("#omni-save")
            await pilot.pause(0.4)
            step("form closed after save", not app.screen._omniroute_setup_open)
            # keychain round-trip
            step("key stored in keychain", get_key("omniroute") == "omni-secret-123")
            step("key_present True", key_present("omniroute"))
            # config.json: provider persisted but secret ABSENT
            raw = (_TMP / "config.json").read_text()
            cfg = json.loads(raw)
            step("omniroute provider in config", "omniroute" in cfg.get("providers", {}))
            step("secret absent from config.json", "omni-secret-123" not in raw)
            step("api_key_env None (key in keychain, not config)",
                 cfg["providers"]["omniroute"].get("api_key_env") is None)
            # providers panel reflects the key
            from frontend.widgets.providers_panel import ProvidersPanel
            try:
                panel = app.screen.query_one(ProvidersPanel)
                step("panel reports key present",
                     panel._key_present.get("omniroute") is True)
            except Exception as exc:
                step("panel reports key present", False)
                print(f"      (panel query error: {exc!r})")

        # ── B. KEEP round-trip: reopen, blank key, save → key survives ─────
        print("B. Keep-blank round-trip")
        async with launch() as (pilot, app):
            await open_omniroute_form(pilot, app)
            form = app.screen._omniroute_setup
            from textual.widgets import Input, Button
            step("form knows a key exists (keep placeholder)",
                 "leave blank to keep" in str(form.query_one("#omni-key", Input).placeholder))
            form.query_one("#omni-endpoint", Input).value = gateway.endpoint
            form.query_one("#omni-model", Input).value = "auto"
            # key field left BLANK
            await pilot.click("#omni-test")
            await pilot.pause(0.8)
            step("test passed again", form.query_one("#omni-save", Button).disabled is False)
            await pilot.click("#omni-save")
            await pilot.pause(0.4)
            step("key preserved after blank save", get_key("omniroute") == "omni-secret-123")

        # ── C. DELETE round-trip: storage delete → panel reflects it ───────
        print("C. Delete round-trip")
        step("delete removes key", delete_key("omniroute") is None and
             get_key("omniroute") is None and not key_present("omniroute"))
        async with launch() as (pilot, app):
            await open_omniroute_form(pilot, app)
            form = app.screen._omniroute_setup
            from textual.widgets import Input
            step("form now offers fresh key entry",
                 "optional gateway key" in str(form.query_one("#omni-key", Input).placeholder))
            # set endpoint + a fresh key to confirm re-entry works after delete
            from textual.widgets import Button as _Btn
            form.query_one("#omni-endpoint", Input).value = gateway.endpoint
            form.query_one("#omni-model", Input).value = "auto"
            form.query_one("#omni-key", Input).value = "omni-secret-456"
            await pilot.click("#omni-test")
            await pilot.pause(0.8)
            _st = str(form.query_one("#omni-status").renderable)
            print(f"      (debug C status: {_st!r})")
            step("re-test passed after delete",
                 form.query_one("#omni-save", _Btn).disabled is False)
            await pilot.click("#omni-save")
            await pilot.pause(0.4)
            print(f"      (debug: form closed={not app.screen._omniroute_setup_open}, "
                  f"get_key={get_key('omniroute')!r})")
            step("fresh key stored after delete", get_key("omniroute") == "omni-secret-456")
            delete_key("omniroute")
            step("cleaned up", not key_present("omniroute"))
    finally:
        gateway.stop()

    print(f"\n=== {ok}/{ok + len(fails)} ok ===")
    if fails:
        print("FAILURES:", *fails, sep="\n  - ")
        sys.exit(1)
    print("all green")


if __name__ == "__main__":
    asyncio.run(main())
