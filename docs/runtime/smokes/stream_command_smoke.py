"""smoke — /stream on|off|<ms> slash command.

Verifies the full path:
  ChatScreen._handle_command → set_stream → state change → config persist → reload

Exercises:
  1. set_stream("on") → stream_chunks=True, typewriter_ms=0
  2. set_stream("off") → stream_chunks=False, typewriter_ms=0
  3. set_stream("<N>") → stream_chunks=True, typewriter_ms=N
  4. set_stream("") → defaults to "on"
  5. set_stream("999") → clamped to 500
  6. set_stream("-5") → clamped to 0
  7. set_stream("garbage") → no-op (ignored)
  8. Config round-trip: save → load → values preserved
  9. Command dispatch in _handle_command routes "/stream" → set_stream
 10. Config schema has stream_chunks + stream_typewriter_ms
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2]

if str(DOCS) not in sys.path:
    sys.path.insert(0, str(DOCS))

# ---------- smoke harness ----------
_ok: list[int] = []
_bad: list[int] = []


def _pass(label: str) -> None:
    _ok[0] += 1
    print(f"  ✓ {label}")


def _fail(label: str, extra: str = "") -> None:
    _bad[0] += 1
    print(f"  ✗ FAIL: {label}{extra}")


def step(label: str, value: bool) -> None:
    if value:
        _pass(label)
    else:
        _fail(label)


def step_eq(label: str, a, b) -> None:
    if a == b:
        _pass(label)
    else:
        _fail(label, f"  ({a!r} != {b!r})")


def section(title: str) -> None:
    print(f"\n── {title} ──")


_ok.append(0)
_bad.append(0)


def _make_chat_screen() -> "ChatScreen":
    """Create a fresh ChatScreen without Textual overhead."""
    return ChatScreen()


# ===========================================================================
# 1. set_stream("on")
# ===========================================================================
section("1. set_stream(\"on\")")

import frontend.config_io as cio
from frontend.config_io import Config, load_config, save_config
from frontend.screens.chat import ChatScreen  # noqa: F811

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path

    try:
        cfg = Config(stream_chunks=False, stream_typewriter_ms=100)
        save_config(cfg)

        cs = _make_chat_screen()
        cs.stream_chunks = False
        cs.stream_typewriter_ms = 100

        cs.set_stream("on")
        step("stream_chunks is True", cs.stream_chunks)
        step_eq("stream_typewriter_ms is 0", cs.stream_typewriter_ms, 0)

        loaded = load_config()
        step("config.stream_chunks is True", loaded.stream_chunks)
        step_eq("config.stream_typewriter_ms is 0", loaded.stream_typewriter_ms, 0)
    finally:
        cio.CONFIG_PATH = real_path

# ===========================================================================
# 2. set_stream("off")
# ===========================================================================
section("2. set_stream(\"off\")")

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path

    try:
        cfg = Config(stream_chunks=True, stream_typewriter_ms=50)
        save_config(cfg)

        cs = _make_chat_screen()
        cs.stream_chunks = True
        cs.stream_typewriter_ms = 50

        cs.set_stream("off")
        step("stream_chunks is False", not cs.stream_chunks)
        step_eq("stream_typewriter_ms is 0", cs.stream_typewriter_ms, 0)

        loaded = load_config()
        step("config.stream_chunks is False", not loaded.stream_chunks)
        step_eq("config.stream_typewriter_ms is 0", loaded.stream_typewriter_ms, 0)
    finally:
        cio.CONFIG_PATH = real_path

# ===========================================================================
# 3. set_stream("<N>") — numeric typewriter delay
# ===========================================================================
section("3. set_stream(\"<N>\") — numeric")

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path

    try:
        cfg = Config(stream_chunks=False, stream_typewriter_ms=0)
        save_config(cfg)

        cs = _make_chat_screen()
        cs.stream_chunks = False
        cs.stream_typewriter_ms = 0

        cs.set_stream("80")
        step("stream_chunks is True (ms implies on)", cs.stream_chunks)
        step_eq("stream_typewriter_ms is 80", cs.stream_typewriter_ms, 80)

        loaded = load_config()
        step("config.stream_chunks is True", loaded.stream_chunks)
        step_eq("config.stream_typewriter_ms is 80", loaded.stream_typewriter_ms, 80)
    finally:
        cio.CONFIG_PATH = real_path

# ===========================================================================
# 4. set_stream("") — empty defaults to on
# ===========================================================================
section("4. set_stream(\"\") — empty defaults to \"on\"")

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path

    try:
        cfg = Config(stream_chunks=False, stream_typewriter_ms=200)
        save_config(cfg)

        cs = _make_chat_screen()
        cs.stream_chunks = False
        cs.stream_typewriter_ms = 200

        cs.set_stream("")
        step("stream_chunks is True (default on)", cs.stream_chunks)
        step_eq("stream_typewriter_ms is 0", cs.stream_typewriter_ms, 0)
    finally:
        cio.CONFIG_PATH = real_path

# ===========================================================================
# 5. set_stream("999") — clamped to 500
# ===========================================================================
section("5. set_stream(\"999\") — clamped to 500")

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path

    try:
        cfg = Config()
        save_config(cfg)

        cs = _make_chat_screen()
        cs.set_stream("999")
        step("stream_chunks is True", cs.stream_chunks)
        step_eq("typewriter_ms clamped to 500", cs.stream_typewriter_ms, 500)

        loaded = load_config()
        step_eq("config clamped to 500", loaded.stream_typewriter_ms, 500)
    finally:
        cio.CONFIG_PATH = real_path

# ===========================================================================
# 6. set_stream("-5") — clamped to 0
# ===========================================================================
section("6. set_stream(\"-5\") — clamped to 0")

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path

    try:
        cfg = Config()
        save_config(cfg)

        cs = _make_chat_screen()
        cs.set_stream("-5")
        step("stream_chunks is True", cs.stream_chunks)
        step_eq("typewriter_ms clamped to 0", cs.stream_typewriter_ms, 0)
    finally:
        cio.CONFIG_PATH = real_path

# ===========================================================================
# 7. set_stream("garbage") — no-op
# ===========================================================================
section("7. set_stream(\"garbage\") — no-op (ignored)")

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path

    try:
        cfg = Config(stream_chunks=True, stream_typewriter_ms=80)
        save_config(cfg)

        cs = _make_chat_screen()
        cs.stream_chunks = True
        cs.stream_typewriter_ms = 80

        cs.set_stream("garbage")
        step("stream_chunks unchanged", cs.stream_chunks)
        step_eq("typewriter_ms unchanged", cs.stream_typewriter_ms, 80)

        loaded = load_config()
        step("config.stream_chunks unchanged", loaded.stream_chunks)
        step_eq("config.typewriter_ms unchanged", loaded.stream_typewriter_ms, 80)
    finally:
        cio.CONFIG_PATH = real_path

# ===========================================================================
# 8. set_stream("0") — explicit zero
# ===========================================================================
section("8. set_stream(\"0\") — explicit zero")

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path

    try:
        cfg = Config()
        save_config(cfg)

        cs = _make_chat_screen()
        cs.set_stream("0")
        step("stream_chunks is True", cs.stream_chunks)
        step_eq("typewriter_ms is 0", cs.stream_typewriter_ms, 0)
    finally:
        cio.CONFIG_PATH = real_path

# ===========================================================================
# 9. set_stream("500") — upper bound exactly
# ===========================================================================
section("9. set_stream(\"500\") — upper bound exactly")

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path

    try:
        cfg = Config()
        save_config(cfg)

        cs = _make_chat_screen()
        cs.set_stream("500")
        step_eq("typewriter_ms is 500", cs.stream_typewriter_ms, 500)
    finally:
        cio.CONFIG_PATH = real_path

# ===========================================================================
# 10. Config reload round-trip (reload_config_from_disk)
# ===========================================================================
section("10. Config reload round-trip")

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path

    try:
        cfg = Config(stream_chunks=False, stream_typewriter_ms=120,
                     default_model="ollama/llama3.3:70b")
        save_config(cfg)

        cs = _make_chat_screen()
        cs.stream_chunks = True
        cs.stream_typewriter_ms = 0

        cs.reload_config_from_disk()
        step("reload: stream_chunks from disk (False)", not cs.stream_chunks)
        step_eq("reload: typewriter_ms from disk (120)", cs.stream_typewriter_ms, 120)
    finally:
        cio.CONFIG_PATH = real_path

# ===========================================================================
# 11. Command dispatch: _handle_command routes "/stream" → set_stream
# ===========================================================================
section("11. Command dispatch routes \"/stream\" to set_stream")

import inspect
from frontend.screens.chat import ChatScreen

src = inspect.getsource(ChatScreen._handle_command)
step("cmd == \"stream\" check present", "cmd == \"stream\"" in src)
step("set_stream(arg) call present", "self.set_stream(arg)" in src)

# ===========================================================================
# 12. Config schema
# ===========================================================================
section("12. Config schema includes stream fields")

from dataclasses import fields as dc_fields

cfg_fields = {f.name: f.type for f in dc_fields(Config)}
step("Config has stream_chunks field", "stream_chunks" in cfg_fields)
step("Config has stream_typewriter_ms field", "stream_typewriter_ms" in cfg_fields)

# ===========================================================================
# 13. set_stream is a public ChatScreen method
# ===========================================================================
section("13. set_stream is a public ChatScreen method")

step("set_stream is callable", callable(getattr(ChatScreen, "set_stream", None)))
sig = inspect.signature(ChatScreen.set_stream)
params = list(sig.parameters.keys())
step_eq("set_stream takes 2 params (self, value)", len(params), 2)
step("param name is 'value'", params[1] == "value")

# ===========================================================================
# 14. Toggle chaining: off → on → 80 → off
# ===========================================================================
section("14. Toggle chaining: off → on → 80 → off")

with tempfile.TemporaryDirectory() as tmp:
    cfg_path = Path(tmp) / "config.json"
    real_path = cio.CONFIG_PATH
    cio.CONFIG_PATH = cfg_path

    try:
        cfg = Config()
        save_config(cfg)

        cs = _make_chat_screen()

        cs.set_stream("off")
        step("chain step 1: off", not cs.stream_chunks)
        step_eq("chain step 1: ms 0", cs.stream_typewriter_ms, 0)

        cs.set_stream("on")
        step("chain step 2: on", cs.stream_chunks)
        step_eq("chain step 2: ms 0", cs.stream_typewriter_ms, 0)

        cs.set_stream("80")
        step("chain step 3: on (from ms)", cs.stream_chunks)
        step_eq("chain step 3: ms 80", cs.stream_typewriter_ms, 80)

        cs.set_stream("off")
        step("chain step 4: off", not cs.stream_chunks)
        step_eq("chain step 4: ms 0", cs.stream_typewriter_ms, 0)
    finally:
        cio.CONFIG_PATH = real_path

# ===========================================================================
# Summary
# ===========================================================================
total = _ok[0] + _bad[0]
print(f"\n=== {_ok[0]}/{total} ok ===")
if _bad[0]:
    print(f"{_bad[0]} fail")
    sys.exit(1)
else:
    print("all green")