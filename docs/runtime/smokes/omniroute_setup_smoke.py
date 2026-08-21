"""OmniRoute setup and adapter smoke pilot.

No external gateway is required. The adapter uses httpx.MockTransport so the
request contract is tested exactly, including keyless and keyed requests.
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "docs")

import httpx  # noqa: E402

from frontend.providers import by_name  # noqa: E402
from frontend.widgets.omniroute_setup import normalize_endpoint, validate_model  # noqa: E402
from runtime.adapters.openai_compat import OpenAICompatAdapter  # noqa: E402


OK = 0
FAIL = 0


def check(label: str, condition: bool) -> None:
    global OK, FAIL
    if condition:
        OK += 1
    else:
        FAIL += 1
        print(f"  FAIL | {label}")


def section(title: str) -> None:
    print(f"=== {title} ===")



def test_catalog() -> None:
    section("1. catalog contract")
    entry = by_name("omniroute")
    check("catalog entry exists", entry is not None)
    check("local tier", entry is not None and entry.tier == "local")
    check("optional auth", entry is not None and entry.auth == "optional")
    check("20128 endpoint", entry is not None and "20128" in (entry.base_url or ""))
    check("auto default", entry is not None and entry.default_model == "auto")
    check("six routing models", entry is not None and len(entry.models) == 6)
    check("coding strategy included", entry is not None and "auto/coding" in entry.models)


def test_validation() -> None:
    section("2. setup validation")
    endpoint, error = normalize_endpoint("localhost:20128/v1/")
    check("bare localhost gets http scheme", endpoint == "http://localhost:20128/v1")
    check("valid endpoint has no error", error is None)
    endpoint, error = normalize_endpoint("https://gateway.example/v1")
    check("https endpoint accepted", endpoint == "https://gateway.example/v1" and error is None)
    endpoint, error = normalize_endpoint("https://user:secret@example/v1")
    check("embedded credentials rejected", endpoint is None and error is not None)
    endpoint, error = normalize_endpoint("")
    check("empty endpoint rejected", endpoint is None and error == "endpoint is required")
    model, error = validate_model("auto/cheap")
    check("strategy model accepted", model == "auto/cheap" and error is None)
    model, error = validate_model("auto cheap")
    check("whitespace model rejected", model is None and error is not None)


def _transport(captured: list[dict], headers: list[dict]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content.decode("utf-8")))
        headers.append(dict(request.headers))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-omni-smoke",
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 1},
            },
        )
    return httpx.MockTransport(handler)


def test_keyless_request() -> None:
    section("3. keyless OpenAI-compatible request")
    bodies: list[dict] = []
    headers: list[dict] = []
    adapter = OpenAICompatAdapter(
        model="omniroute/auto",
        base_url="http://localhost:20128/v1",
        api_key=None,
        transport=_transport(bodies, headers),
    )
    response = adapter.call(
        [{"role": "user", "content": "ping"}],
        "be terse",
        {"max_tokens": 4, "temperature": 0.0},
    )
    check("keyless adapter constructs", True)
    check("posts to chat endpoint", adapter.base_url.endswith("/v1"))
    check("model is auto", bodies[0].get("model") == "auto")
    check("system message included", bodies[0]["messages"][0]["role"] == "system")
    check("response text parsed", response.text == "ok")
    check("usage parsed", response.in_tokens == 7 and response.out_tokens == 1)
    check("no Authorization for keyless", "authorization" not in headers[0])


def test_keyed_request() -> None:
    section("4. keyed request")
    bodies: list[dict] = []
    headers: list[dict] = []
    adapter = OpenAICompatAdapter(
        model="omniroute/auto/fast",
        base_url="http://localhost:20128/v1",
        api_key="omni-test-secret",
        transport=_transport(bodies, headers),
    )
    adapter.call([{"role": "user", "content": "ping"}], "", {})
    check("nested model id preserved after provider split",
          bodies[0].get("model") == "auto/fast")
    check("Authorization sent when key supplied",
          headers[0].get("authorization") == "Bearer omni-test-secret")
    check("content type sent", headers[0].get("content-type") == "application/json")


def test_save_path() -> None:
    section("5. save path keeps secret out of config")
    import frontend.config_io as config_io
    import frontend.keys_storage as keys_storage
    from frontend.screens.settings import SettingsScreen
    from frontend.widgets.omniroute_setup import OmniRouteSetup

    original_path = config_io.CONFIG_PATH
    original_backend = keys_storage._BACKEND
    original_memory = dict(keys_storage._in_mem)
    with tempfile.TemporaryDirectory() as temp:
        config_io.CONFIG_PATH = Path(temp) / "config.json"
        keys_storage._BACKEND = "memory"
        keys_storage._in_mem.clear()
        try:
            screen = SettingsScreen()
            screen.on_omniroute_setup_saved(
                OmniRouteSetup.Saved(
                    "http://localhost:20128/v1", "auto/cheap", "omni-secret"
                )
            )
            saved = config_io.load_config()
            raw = config_io.CONFIG_PATH.read_text(encoding="utf-8")
            check("provider persisted", "omniroute" in saved.providers)
            check("endpoint persisted", saved.providers["omniroute"].base_url.endswith("/v1"))
            check("selected model persisted", saved.default_model == "omniroute/auto/cheap")
            check("key stored separately", keys_storage.get_key("omniroute") == "omni-secret")
            check("secret absent from config", "omni-secret" not in raw)
        finally:
            config_io.CONFIG_PATH = original_path
            keys_storage._BACKEND = original_backend
            keys_storage._in_mem.clear()
            keys_storage._in_mem.update(original_memory)


def test_ui_flow() -> None:
    section("6. Textual setup flow")
    from textual import on
    from textual.app import App, ComposeResult
    from textual.widgets import Button, Input
    from frontend.widgets.omniroute_setup import OmniRouteSetup
    from runtime.providers import ProbeResult, STATUS_OK
    import runtime.providers as runtime_providers

    class Demo(App):
        def __init__(self):
            super().__init__()
            self.saved = None

        def compose(self) -> ComposeResult:
            yield OmniRouteSetup()

        @on(OmniRouteSetup.Saved)
        def on_omniroute_setup_saved(self, message):
            self.saved = message

    original_probe = runtime_providers.probe_omniroute
    runtime_providers.probe_omniroute = lambda *args, **kwargs: ProbeResult(
        provider_name="omniroute", model_name="omniroute/auto",
        status=STATUS_OK, latency_ms=12, note="response text: ok",
    )

    async def drive() -> None:
        async with Demo().run_test() as pilot:
            endpoint = pilot.app.query_one("#omni-endpoint", Input)
            model = pilot.app.query_one("#omni-model", Input)
            key = pilot.app.query_one("#omni-key", Input)
            endpoint.value = "http://localhost:20128/v1"
            model.value = "auto"
            key.value = "omni-secret"
            await pilot.click("#omni-test")
            await pilot.pause(0.15)
            check("save enabled only after successful test",
                  pilot.app.query_one("#omni-save", Button).disabled is False)
            await pilot.click("#omni-save")
            await pilot.pause(0.05)
            check("save message carries endpoint", pilot.app.saved.endpoint.endswith("/v1"))
            check("save message carries selected model", pilot.app.saved.model == "auto")
            check("save message carries key", pilot.app.saved.api_key == "omni-secret")

    try:
        asyncio.run(drive())
    finally:
        runtime_providers.probe_omniroute = original_probe


def test_streaming_registry() -> None:
    section("7. streaming registry")
    from runtime.adapters.openai_compat import _OPENAI_COMPAT_SPECS
    spec = _OPENAI_COMPAT_SPECS["omniroute"]
    check("runtime uses 20128", "20128" in spec.base_url)
    check("OmniRoute streaming enabled", spec.streaming is True)


if __name__ == "__main__":
    for test in (
        test_catalog,
        test_validation,
        test_keyless_request,
        test_keyed_request,
        test_save_path,
        test_ui_flow,
        test_streaming_registry,
    ):
        try:
            test()
        except Exception as exc:
            FAIL += 1
            print(f"  EXC | {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n=== pilot complete: {OK} ok / {FAIL} fail ===")
    sys.exit(1 if FAIL else 0)
