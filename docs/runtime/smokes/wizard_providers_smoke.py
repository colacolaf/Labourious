"""wizard_providers_smoke.py — every wizard provider: key stored AND loaded.

Drives the REAL app (real ChatScreen → real wizard) through ALL SIX
wizard providers. For each one it verifies:
  - the wizard completes (no dead-end / "stuck" step)
  - the config gains the provider + correct default_model
  - key-requiring providers: the typed API key is retrievable from
    keys_storage under the SAME name the runtime adapter looks up, and
    the runtime adapter for that provider's default model resolves it.

Why this matters: the wizard stores keys under its provider id
(anthropic / openai / openrouter / google_ai_studio), while each runtime
adapter resolves keys by provider name. If those names diverged, the key
would store fine but never load at chat time. This pilot pins the
wizard-id == adapter-name contract for every provider.

Hermetic: temp HOME + LABOURIOUS_TEST so the user's real keychain and
config are never touched.

Run: PYTHONPATH=docs python3 docs/runtime/smokes/wizard_providers_smoke.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

# --- isolate everything before importing frontend modules -------------------
_TMP = Path(tempfile.mkdtemp(prefix="wizard-providers-"))
os.environ["HOME"] = str(_TMP)
os.environ["LABOURIOUS_CONFIG"] = str(_TMP / "config.json")
os.environ["LABOURIOUS_TEST"] = "1"
# Clear provider env vars so the test exercises the KEYCHAIN path, not env
# precedence (adapters prefer env var over stored key). The developer's
# shell env must not leak into this hermetic pilot.
for _env in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
             "GOOGLE_API_KEY", "GEMINI_API_KEY", "OMNIROUTE_API_KEY"):
    os.environ.pop(_env, None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from frontend.app import LabouriousApp  # noqa: E402
from frontend.screens.welcome_wizard import WelcomeWizardScreen  # noqa: E402
from frontend.screens.chat import ChatScreen  # noqa: E402
from frontend.keys_storage import get_key, delete_key  # noqa: E402

ok = 0
fails: list[str] = []


def step(desc: str, cond: bool) -> None:
    global ok
    if cond:
        ok += 1
    else:
        fails.append(desc)
        print(f"  ✗ FAIL {desc}")


@asynccontextmanager
async def launch():
    _TMP_CFG = _TMP / "config.json"
    _TMP_CFG.write_text("{}")  # empty providers -> wizard auto-pushes
    app = LabouriousApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)
        yield pilot, app


# provider_id -> (key_needed, expected default model)
PROVIDERS = [
    ("ollama",          False, "ollama/llama3.3:70b"),
    ("anthropic",       True,  "anthropic/claude-sonnet-4-5"),
    ("openai",          True,  "openai/gpt-4o"),
    ("openrouter",      True,  "openrouter/google/gemini-2.0-flash-001"),
    ("google_ai_studio", True, "google_ai_studio/gemini-2.0-flash"),
    ("omniroute",       False, "omniroute/auto"),
]


async def drive_one(pid: str, key_needed: bool, expected_model: str) -> None:
    test_key = f"sk-test-{pid}"
    async with launch() as (pilot, app):
        step(f"[{pid}] wizard pushed on empty config",
             isinstance(app.screen, WelcomeWizardScreen))
        # type provider id
        await pilot.press(*pid)
        await pilot.press("enter")
        await pilot.pause(0.2)
        step(f"[{pid}] provider resolved",
             app.screen._provider is not None and app.screen._provider["id"] == pid)
        # Enter on step 1 -> default model
        await pilot.press("enter")
        await pilot.pause(0.2)
        step(f"[{pid}] step 2 + default model",
             app.screen._step == 2 and app.screen._model != "")
        if key_needed:
            # type the API key
            await pilot.press(*test_key)
            await pilot.pause(0.2)
            step(f"[{pid}] key accumulated", app.screen._api_key == test_key)
        # Finish / Save & start
        await pilot.press("enter")
        await pilot.pause(0.3)
        step(f"[{pid}] wizard dismissed", isinstance(app.screen, ChatScreen))
        cfg = json.loads((_TMP / "config.json").read_text())
        step(f"[{pid}] provider in config", pid in cfg.get("providers", {}))
        step(f"[{pid}] default_model persisted", cfg.get("default_model") == expected_model)

    if key_needed:
        # 1) key retrievable under the wizard's id
        stored = get_key(pid)
        step(f"[{pid}] key stored under wizard id", stored == test_key)
        # 2) the runtime adapter for this provider's model resolves the key
        #    through the SAME name the wizard stored it under.
        from runtime.adapters import get_adapter
        try:
            adapter = get_adapter(expected_model)
            if pid == "google_ai_studio":
                # GeminiAdapter resolves at construction: self.api_key
                resolved = getattr(adapter, "api_key", None)
            elif pid in ("openai", "openrouter"):
                # openai_sdk path stores key inside the client, not an attr;
                # verify via the compat resolve path used by both.
                from runtime.adapters.openai_compat import _resolve_key
                from runtime.adapters.openai_compat import _OPENAI_COMPAT_SPECS
                spec = _OPENAI_COMPAT_SPECS[pid]
                resolved = _resolve_key(spec.name, spec.env_var)
            else:  # anthropic — SDK adapter holds the key inside the client;
                # force client creation (no network) to prove resolution.
                client = adapter._client_or_create()
                resolved = getattr(getattr(client, "_client", client), "api_key", None) or \
                    getattr(client, "api_key", None)
            step(f"[{pid}] adapter resolves key", resolved == test_key)
        except Exception as e:  # noqa: BLE001
            step(f"[{pid}] adapter resolves key (no exception)", False)
            print(f"      (adapter error: {e!r})")
        # clean up the test key
        delete_key(pid)


async def main() -> None:
    for pid, key_needed, expected_model in PROVIDERS:
        print(f"── {pid} (key={key_needed}) ──")
        await drive_one(pid, key_needed, expected_model)
    print(f"\n=== {ok}/{ok + len(fails)} ok ===")
    if fails:
        print("FAILURES:", fails)
        sys.exit(1)
    print("all green")


if __name__ == "__main__":
    asyncio.run(main())
