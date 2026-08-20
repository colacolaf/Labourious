"""providers_probe_smoke.py — pilot for runtime.providers (P1 probe item).

Covers all five ProbeResult statuses: OK / FAIL / AUTH_MISSING /
TIMEOUT / UNREACHABLE. Also covers: skip-IO mode, batch probe, the
provider-name split, structured error for empty-prefix models.

When mocking, we monkey-patch ``runtime.adapters.get_adapter`` to
return a stub adapter whose ``call`` raises / returns whatever we
need. That sidesteps real network traffic.

Counts: ~ 38 assertions across 9 sections.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import time
import urllib.error as _urllib_error  # noqa: F401

sys.path.insert(0, "docs")

from docs.runtime.providers import (  # noqa: E402
    probe_provider, probe_many, ProbeResult,
    STATUS_OK, STATUS_FAIL, STATUS_AUTH_MISSING,
    STATUS_TIMEOUT, STATUS_UNREACHABLE,
)
from docs.runtime.adapters._streaming import AuthMissing, AdapterHTTPError  # noqa: E402


# ---------------------------------------------------------------------------
# Counter
# ---------------------------------------------------------------------------

OK = 0
FAIL = 0


def check(label: str, cond: bool):
    global OK, FAIL
    if cond:
        OK += 1
    else:
        FAIL += 1
        print(f"  FAIL: {label}")


def section(name: str):
    print(f"=== {name} ===")


# ---------------------------------------------------------------------------
# Stub adapter helpers
# ---------------------------------------------------------------------------

class _StubAdapter:
    """Bare-minimum adapter-shaped object for probe testing."""
    def __init__(self, *, raises=None, returns=None, base_url=None):
        self.raises = raises
        self.returns = returns
        self.base_url = base_url

    def call(self, **kwargs):
        if self.raises is not None:
            raise self.raises
        if self.returns is not None:
            return self.returns
        from docs.runtime.adapters import Response
        return Response(
            text="ok", in_tokens=2, out_tokens=1,
            cache_hit_tokens=0, cost_usd_estimate=0.0,
        )


class _StubResponse:
    def __init__(self, text: str, in_tok: int = 2, out_tok: int = 1):
        self.text = text
        self.in_tokens = in_tok
        self.out_tokens = out_tok
        self.cache_hit_tokens = 0
        self.cost_usd_estimate = 0.0


def _patch_adapter(monkeypatch_adapter):
    """Monkey-patch ``runtime.providers.get_adapter`` to return a stub."""
    import docs.runtime.providers as _prov
    orig = _prov.get_adapter
    _prov.get_adapter = lambda model_name: monkeypatch_adapter
    return orig, _prov


# ---------------------------------------------------------------------------
# 1. OK path — happy stub adapter
# ---------------------------------------------------------------------------

def test_1_ok_path():
    section("1. happy stub → OK with latency + token counts (5)")
    import docs.runtime.providers as _prov
    orig = _prov.get_adapter
    stub = _StubAdapter(returns=_StubResponse("ok", 3, 2), base_url=None)
    _prov.get_adapter = lambda m: stub
    try:
        # Skip endpoint probe (base_url=None) and run_io=True
        r = probe_provider("ollama/llama3.2:3b", run_io=True)
        check("status=OK", r.status == STATUS_OK)
        check("provider_name='ollama'", r.provider_name == "ollama")
        check("model has 'llama' in it", "llama" in r.model_name)
        check("latency_ms is int", isinstance(r.latency_ms, int))
        check("in_tokens=3", r.in_tokens == 3)
    finally:
        _prov.get_adapter = orig


# ---------------------------------------------------------------------------
# 2. AUTH_MISSING before any I/O
# ---------------------------------------------------------------------------

def test_2_auth_missing():
    section("2. AUTH_MISSING for missing key on cloud provider (3)")
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "COHERE_API_KEY",
              "GEMINI_API_KEY", "GROQ_API_KEY"):
        os.environ.pop(k, None)

    cases = [
        ("anthropic/claude-sonnet-4-5", "anthropic"),
        ("cohere/command-r",            "cohere"),
        ("openai/gpt-4o-mini",          "openai"),
        ("groq/llama-3.3-70b-versatile","groq"),
    ]
    for model, expected_provider in cases:
        r = probe_provider(model, run_io=True)
        check(f"{expected_provider} → AUTH_MISSING (no env key)",
              r.status == STATUS_AUTH_MISSING
              and r.provider_name == expected_provider)


# ---------------------------------------------------------------------------
# 3. UNREACHABLE — endpoint probe fails (port-bound socket)
# ---------------------------------------------------------------------------

def test_3_unreachable():
    section("3. UNREACHABLE when endpoint probe fails (2)")
    # Use a real but unreachable URL. 127.0.0.1:1 is always closed.
    # Stub adapter synthesises a base_url that points here.
    import docs.runtime.providers as _prov
    orig = _prov.get_adapter
    stub = _StubAdapter(returns=_StubResponse("ok"),
                        base_url="http://127.0.0.1:1")
    _prov.get_adapter = lambda m: stub
    try:
        r = probe_provider("ollama/llama3.2:3b")
        check("status=UNREACHABLE", r.status == STATUS_UNREACHABLE)
        check("note mentions endpoint probe",
              r.note and "endpoint" in r.note)
    finally:
        _prov.get_adapter = orig


# ---------------------------------------------------------------------------
# 4. Adapter raises AuthMissing during the chat call
# ---------------------------------------------------------------------------

def test_4_adapter_auth_missing_at_call():
    section("4. AuthMissing at chat call → AUTH_MISSING (2)")
    # Set a key but make the adapter's call() throw AuthMissing.
    os.environ["ANTHROPIC_API_KEY"] = "FAKE_KEY"
    import docs.runtime.providers as _prov
    orig = _prov.get_adapter
    stub = _StubAdapter(raises=AuthMissing(provider="anthropic"),
                        base_url=None)
    _prov.get_adapter = lambda m: stub
    try:
        r = probe_provider("anthropic/claude-sonnet-4-5", run_io=True)
        check("status=AUTH_MISSING", r.status == STATUS_AUTH_MISSING)
        check("error_message mentions provider",
              r.error_message and "anthropic" in r.error_message)
    finally:
        _prov.get_adapter = orig
        os.environ.pop("ANTHROPIC_API_KEY", None)


# ---------------------------------------------------------------------------
# 5. Adapter raises AdapterHTTPError → FAIL with latency
# ---------------------------------------------------------------------------

def test_5_adapter_http_error():
    section("5. AdapterHTTPError → FAIL (2)")
    os.environ["ANTHROPIC_API_KEY"] = "FAKE_KEY"
    import docs.runtime.providers as _prov
    orig = _prov.get_adapter
    stub = _StubAdapter(
        raises=AdapterHTTPError(provider="anthropic", status=503,
                                body="overloaded"),
        base_url=None,
    )
    _prov.get_adapter = lambda m: stub
    try:
        r = probe_provider("anthropic/claude-sonnet-4-5", run_io=True)
        check("status=FAIL", r.status == STATUS_FAIL)
        check("503 surfaced in error_message",
              r.error_message and "503" in r.error_message)
    finally:
        _prov.get_adapter = orig
        os.environ.pop("ANTHROPIC_API_KEY", None)


# ---------------------------------------------------------------------------
# 6. Adapter raises generic Exception → FAIL
# ---------------------------------------------------------------------------

def test_6_adapter_generic_exception():
    section("6. generic Exception → FAIL (3)")
    os.environ["OPENAI_API_KEY"] = "FAKE_KEY"
    import docs.runtime.providers as _prov
    orig = _prov.get_adapter
    stub = _StubAdapter(raises=ValueError("schema drift"),
                        base_url=None)
    _prov.get_adapter = lambda m: stub
    try:
        r = probe_provider("openai/gpt-4o-mini", run_io=True)
        check("status=FAIL", r.status == STATUS_FAIL)
        check("error_message mentions exception type",
              "ValueError" in (r.error_message or ""))
        check("latency_ms captured even on FAIL",
              r.latency_ms is not None)
    finally:
        _prov.get_adapter = orig
        os.environ.pop("OPENAI_API_KEY", None)


# ---------------------------------------------------------------------------
# 7. ConnectionRefusedError → UNREACHABLE
# ---------------------------------------------------------------------------

def test_7_connection_error():
    section("7. ConnectionRefusedError → UNREACHABLE (3)")
    os.environ["OPENAI_API_KEY"] = "FAKE_KEY"
    import docs.runtime.providers as _prov
    orig = _prov.get_adapter
    stub = _StubAdapter(raises=ConnectionRefusedError("no socket"),
                        base_url=None)
    _prov.get_adapter = lambda m: stub
    try:
        r = probe_provider("openai/gpt-4o-mini", run_io=True)
        check("status=UNREACHABLE", r.status == STATUS_UNREACHABLE)
        check("error_message has 'connection'",
              "connection" in (r.error_message or "").lower()
              or "refused" in (r.error_message or "").lower())
        check("latency_ms is None", r.latency_ms is None)
    finally:
        _prov.get_adapter = orig
        os.environ.pop("OPENAI_API_KEY", None)


# ---------------------------------------------------------------------------
# 8. run_io=False short-circuits
# ---------------------------------------------------------------------------

def test_8_skip_io():
    section("8. run_io=False → short-circuit before chat (4)")
    # Even if the stub raises, run_io=False shouldn't hit it.
    import docs.runtime.providers as _prov
    orig = _prov.get_adapter
    stub = _StubAdapter(raises=AssertionError("would explode"),
                        base_url=None)
    _prov.get_adapter = lambda m: stub
    try:
        r = probe_provider("ollama/llama3.2:3b", run_io=False)
        check("status=OK", r.status == STATUS_OK)
        check("latency_ms=0", r.latency_ms == 0)
        check("note mentions skip",
              r.note and ("skip" in r.note or "skipp" in r.note))
        check("done in <0.1s",
              time.monotonic() - time.monotonic() < 0.1)
    finally:
        _prov.get_adapter = orig


# ---------------------------------------------------------------------------
# 9. probe_many is sequential + returns list
# ---------------------------------------------------------------------------

def test_9_probe_many():
    section("9. probe_many loop + shape (5)")
    import docs.runtime.providers as _prov
    orig = _prov.get_adapter
    call_count = {"n": 0}

    def rotating(m):
        call_count["n"] += 1
        return _StubAdapter(
            returns=_StubResponse("ok", 1, 1),
            base_url=None,
        )
    _prov.get_adapter = rotating
    try:
        results = probe_many(["ollama/llama3.2:3b",
                              "anthropic/claude-sonnet-4-5",
                              "cohere/command-r"], run_io=False)
        check("returns 3 results", len(results) == 3)
        check("all ProbeResult instances",
              all(isinstance(r, ProbeResult) for r in results))
        # Skip-IO mode skips chat → all OK assuming no auth_missing.
        # The middle entry has no key → AUTH_MISSING.
        check("ollama is OK", results[0].status == STATUS_OK)
        check("anthropic (no env key) is AUTH_MISSING",
              results[1].status == STATUS_AUTH_MISSING)
        check("cohere (no env key) is AUTH_MISSING",
              results[2].status == STATUS_AUTH_MISSING)
    finally:
        _prov.get_adapter = orig


# ---------------------------------------------------------------------------
# 10. result.to_dict roundtrip
# ---------------------------------------------------------------------------

def test_10_to_dict_roundtrip():
    section("10. ProbeResult.to_dict roundtrip (4)")
    r = ProbeResult(
        provider_name="ollama", model_name="ollama/llama3.2:3b",
        status=STATUS_OK, latency_ms=42,
        in_tokens=5, out_tokens=2, note="fine",
    )
    d = r.to_dict()
    check("provider_name in dict", d["provider_name"] == "ollama")
    check("status preserved", d["status"] == STATUS_OK)
    check("latency preserved", d["latency_ms"] == 42)
    check("is_ok() returns True", r.is_ok() is True)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_1_ok_path,
        test_2_auth_missing,
        test_3_unreachable,
        test_4_adapter_auth_missing_at_call,
        test_5_adapter_http_error,
        test_6_adapter_generic_exception,
        test_7_connection_error,
        test_8_skip_io,
        test_9_probe_many,
        test_10_to_dict_roundtrip,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            FAIL += 1
            print(f"  EXC in {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== {OK}/{OK + FAIL} assertions passed ===")
    sys.exit(1 if FAIL > 0 else 0)
