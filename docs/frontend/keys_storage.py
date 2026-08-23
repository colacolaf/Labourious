"""
keys_storage.py — OS-encrypted storage for provider API keys.

Single API surface:
    get_key(provider)       -> str | None
    set_key(provider, key)  -> None
    delete_key(provider)    -> None
    key_present(provider)   -> bool
    probe_endpoint(url)     -> bool           # for the panel dot
    status_for(entry)       -> ProviderStatus

Storage policy:
  1. Try OS keyring first (macOS Keychain / Linux Secret Service /
     Windows Credential Manager) via the `keyring` lib.
  2. If `keyring` is not installed — OR the keyring fails at call time
     (no keychain found, locked chain, redirected HOME): fall back to
     ~/.labourious/keys.json, written with chmod 600 (POSIX only).
  3. If both fail: in-memory dict only (no disk write) — useful in
     pilot / CI environments without a keychain backend.

All backends share the same functions; callers never branch. The keyring
path is re-validated at call time, so a degraded keychain (missing,
locked, or redirected HOME) degrades to the on-disk file backend instead
of silently dropping the key.
"""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------- backend selection
_BACKEND: str  # one of: "keyring", "file", "memory"


try:
    import keyring as _kr  # type: ignore
    _KEYRING_OK = True
except ImportError:
    _kr = None  # type: ignore
    _KEYRING_OK = False

# Even when `keyring` is installed, set a deterministic backend for pilots:
# - In CI / tests: use the in-memory backend (PlaintextKeyring on file)
# - On dev machines: use the real keyring
if os.environ.get("LABOURIOUS_TEST"):
    # Pilot / unit-test environment → file-based mock, no OS prompts.
    if _KEYRING_OK:
        try:
            from keyrings.alt.file import PlaintextKeyring  # type: ignore
            _TEST_FILE = Path.home() / ".labourious" / ".keys-test"
            _TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
            kr = PlaintextKeyring()  # type: ignore
            kr.file_path = str(_TEST_FILE)  # type: ignore[attr-defined]
            _BACKEND = "keyring-mock"
        except Exception:
            _BACKEND = "memory"
    else:
        _BACKEND = "memory"
else:
    _BACKEND = "keyring" if _KEYRING_OK else "file"


# ---------------------------------------------------------- file fallback
_FILE_PATH = Path.home() / ".labourious" / "keys.json"

_in_mem: dict[str, str] = {}


def _file_load() -> dict[str, str]:
    if not _FILE_PATH.exists():
        return {}
    try:
        return json.loads(_FILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _file_save(d: dict[str, str]) -> None:
    _FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _FILE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, _FILE_PATH)
    try:
        os.chmod(_FILE_PATH, 0o600)  # POSIX only; silently no-op on Windows
    except Exception:
        pass


# ---------------------------------------------------------- public surface
SERVICE_NAME = "labourious"


def get_key(provider: str) -> str | None:
    if _BACKEND == "keyring" or _BACKEND == "keyring-mock":
        try:
            return _kr.get_password(SERVICE_NAME, provider)  # type: ignore
        except Exception:
            # Keychain unavailable at read time — check the file fallback.
            return _file_load().get(provider)
    if _BACKEND == "file":
        return _file_load().get(provider)
    return _in_mem.get(provider)


def set_key(provider: str, key: str) -> None:
    if not key:
        delete_key(provider)
        return
    if _BACKEND == "keyring" or _BACKEND == "keyring-mock":
        try:
            _kr.set_password(SERVICE_NAME, provider, key)  # type: ignore
            return
        except Exception:
            # Keychain unavailable (no chain, locked, redirected HOME):
            # degrade to the on-disk file backend instead of dropping the
            # key into memory where a later read would miss it.
            d = _file_load()
            d[provider] = key
            _file_save(d)
            return
    if _BACKEND == "file":
        d = _file_load()
        d[provider] = key
        _file_save(d)
        return
    _in_mem[provider] = key


def delete_key(provider: str) -> None:
    if _BACKEND == "keyring" or _BACKEND == "keyring-mock":
        try:
            _kr.delete_password(SERVICE_NAME, provider)  # type: ignore
        except Exception:
            pass
        # Also clear any file-fallback copy (covers a degraded keychain
        # that was previously written via the on-disk fallback).
        d = _file_load()
        if provider in d:
            del d[provider]
            _file_save(d)
        return
    if _BACKEND == "file":
        d = _file_load()
        if provider in d:
            del d[provider]
            _file_save(d)
        return
    _in_mem.pop(provider, None)


def key_present(provider: str) -> bool:
    return get_key(provider) is not None


def backend_name() -> str:
    """Useful in the panel footer to show users where their key is stored."""
    return _BACKEND


# ---------------------------------------------------------- endpoint probe
def probe_endpoint(base_url: str | None, timeout: float = 0.4) -> bool:
    """Cheap connectivity probe used by the panel dot.

    For local: try a TCP connect to host:port.
    For cloud: HEAD request via urllib (no body, no key).
    """
    if not base_url:
        return False
    try:
        if base_url.startswith("http://localhost") or base_url.startswith("http://127."):
            # Strip scheme + path; parse host:port
            tail = base_url.split("://", 1)[1]
            host_port = tail.split("/", 1)[0]
            host, _, port = host_port.partition(":")
            port = int(port) if port else 80
            with socket.create_connection((host, port), timeout=timeout):
                return True
        # Remote: cheap HEAD probe
        import urllib.request
        req = urllib.request.Request(base_url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status < 500
    except Exception:
        return False


# ---------------------------------------------------------- status helper
@dataclass(frozen=True)
class _Status:
    state: str
    detail: str


def status_for(entry) -> _Status:
    """Compute the row dot state. Catalog lives in providers.py."""
    from frontend.providers import ProviderEntry  # noqa: F401
    if entry.tier == "local":
        if probe_endpoint(entry.base_url):
            return _Status("ready", f"● connected · {entry.default_model}")
        return _Status("not-running", "— not running")
    if entry.tier in ("free", "paid", "custom"):
        if key_present(entry.name):
            return _Status("key-loaded", "● ready · key in keychain")
        return _Status("auth-missing", "— no API key")
    return _Status("config-not-set", "— config not set")
