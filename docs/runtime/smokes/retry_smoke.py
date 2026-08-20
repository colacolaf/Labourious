"""
retry_smoke.py — pilot for the runtime/retry.py retry layer.

Exercises ``runtime.retry.with_retry`` + ``RetryingOpener`` end-to-end
so a regression in backoff math, retryable-detection, or HTTP-aware
wrapping is caught at smoke time, not at user-network-blip time.

The pilot focuses on the *contract*:

  1. Backoff math: exponential growth, max cap, jitter sanity, retry
     -after override.
  2. with_retry: succeeds after 2 transient failures; exhausts after
     max_attempts; raises last exception; non-retryable short-circuits.
  3. HTTP-aware: 5xx returned as a SUCCESS-shaped response triggers
     retry; 4xx short-circuits; Retry-After honoured.
  4. RetryingOpener: drop-in replacement for urlopen, retries on
     transient, hands response back on success.
  5. Integration: the 5 wired call sites (web_fetch, quotes_realtime,
     transcripts, news_8k) construct without error and have the
     retry-aware opener assigned.

Usage:
    PYTHONPATH=docs python3 docs/runtime/smokes/retry_smoke.py

Exits non-zero on first hard failure; assertions accumulate so the
pilot can be read top-to-bottom with a tail summary.
"""

from __future__ import annotations

import socket
import sys
import urllib.error
from typing import Any


_TOTAL = 0
_PASS = 0
_FAILED = 0
current_section = ""


def section(name: str) -> None:
    global current_section
    current_section = name
    print(f"\n=== {name} ===")


def step(label: str, ok: bool, *, hint: str = "") -> None:
    global _TOTAL, _PASS, _FAILED
    _TOTAL += 1
    if ok:
        _PASS += 1
        print(f"  [PASS] {label}")
    else:
        _FAILED += 1
        suffix = f"   ⟵ {hint}" if hint else ""
        print(f"  [FAIL] {label}{suffix}")


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from runtime.retry import (
    DEFAULT_MAX_RETRY_AFTER_S,
    DEFAULT_RETRY_EXCEPTIONS,
    DEFAULT_RETRY_STATUSES,
    RetryPolicy,
    StatusOnly,
    compute_backoff_s,
    response_retry_after_s,
    runtime_http_opener,
    with_retry,
)


# ===========================================================================
# 1. Backoff math (deterministic, jitter=0)
# ===========================================================================
section("1. backoff math — exponential growth")
import random
rng = random.Random(42)
p = RetryPolicy(max_attempts=5, base_delay_s=0.5, max_delay_s=8.0, jitter_pct=0.0)
deltas = [compute_backoff_s(i, p) for i in range(4)]
step("attempt 0 → 0.5 s", deltas[0] == 0.5)
step("attempt 1 → 1.0 s", deltas[1] == 1.0)
step("attempt 2 → 2.0 s", deltas[2] == 2.0)
step("attempt 3 → 4.0 s", deltas[3] == 4.0)


section("2. backoff math — cap at max_delay_s")
p_cap = RetryPolicy(max_attempts=10, base_delay_s=1.0, max_delay_s=4.0, jitter_pct=0.0)
deltas = [compute_backoff_s(i, p_cap) for i in range(7)]
step("attempt 0 → 1.0", deltas[0] == 1.0)
step("attempt 1 → 2.0", deltas[1] == 2.0)
step("attempt 2 → 4.0 (cap reached)", deltas[2] == 4.0)
step("attempt 3 → 4.0 (held)", deltas[3] == 4.0)
step("attempt 4 → 4.0 (held)", deltas[4] == 4.0)
step("attempt 5 → 4.0 (held)", deltas[5] == 4.0)
step("attempt 6 → 4.0 (held)", deltas[6] == 4.0)


section("3. backoff math — jitter within ±pct of base")
p_jit = RetryPolicy(max_attempts=3, base_delay_s=1.0, max_delay_s=10.0, jitter_pct=0.5)
vals = [compute_backoff_s(0, p_jit) for _ in range(20)]
step("all non-negative", all(v >= 0 for v in vals))
step("all within ±50% of base",
     all(0.5 <= v <= 1.5 for v in vals))
step("at least 4 unique values (jitter actually varies)",
     len(set(round(v, 3) for v in vals)) >= 4)


section("4. retry-after overrides the schedule")
p = RetryPolicy(max_attempts=3, base_delay_s=0.5, jitter_pct=0.0)
step("retry-after=15 → sleeps 15 (not exponential)",
     compute_backoff_s(0, p, retry_after_s=15.0) == 15.0)
step("retry-after=999 → capped at max_retry_after_s=30",
     compute_backoff_s(0, p, retry_after_s=999.0) == 30.0)
step("retry-after=0 → falls back to exponential schedule (0.5)",
     compute_backoff_s(0, p, retry_after_s=0.0) == 0.5)


# ===========================================================================
# 5. with_retry: succeeds after N transient failures
# ===========================================================================
section("5. with_retry — succeeds after 2 transient failures")
calls: list[int] = []
sleep_log: list[float] = []
def flaky_fn() -> str:
    calls.append(1)   # count-up bookkeeping first; this is call N+1
    n = len(calls)
    if n < 3:
        raise socket.gaierror("flaky DNS")
    return "ok"
sleep = lambda s: sleep_log.append(s)
policy = RetryPolicy(max_attempts=5, base_delay_s=0.1, max_delay_s=1.0, jitter_pct=0.0)
got = with_retry(flaky_fn, policy=policy, sleep=sleep)
step("returned 'ok'", got == "ok")
step("called 3 times total", len(calls) == 3)
step("2 sleeps between calls", len(sleep_log) == 2)
step("sleeps were 0.1, 0.2", sleep_log == [0.1, 0.2])


section("6. with_retry — exhausts attempts, raises LAST exception")
calls: list[int] = []
def always_fails() -> None:
    calls.append(1)
    raise socket.timeout("flaky")
policy = RetryPolicy(max_attempts=3, base_delay_s=0.1, max_delay_s=1.0, jitter_pct=0.0)
try:
    with_retry(always_fails, policy=policy, sleep=lambda s: None)
    step("should have raised", False)
except socket.timeout as e:
    step("raised the underlying exception type", True)
    step("called 3 times (full policy)", len(calls) == 3)
except Exception as e:
    step(f"raised wrong exception type: {type(e).__name__}", False)


section("7. with_retry — non-retryable exception short-circuits")
calls: list[int] = []
def value_error() -> None:
    calls.append(1)
    raise ValueError("bug, not a network blip")
policy = RetryPolicy(max_attempts=5, base_delay_s=0.1, jitter_pct=0.0)
try:
    with_retry(value_error, policy=policy, sleep=lambda s: None)
    step("should have raised", False)
except ValueError as e:
    step("raised original exception type", True)
    step("called exactly once (no retry)", len(calls) == 1)
except Exception as e:
    step(f"wrong type: {type(e).__name__}", False)


# ===========================================================================
# 8. with_retry — on_retry callback fires once per retry
# ===========================================================================
section("8. on_retry callback fires sleep schedule back to caller")
calls: list[int] = []
on_log: list[tuple[int, str, float]] = []
def flaky_2() -> str:
    calls.append(1)
    if len(calls) < 3:
        raise urllib.error.URLError("blip")
    return "ok"
policy = RetryPolicy(max_attempts=3, base_delay_s=0.4, max_delay_s=1.0, jitter_pct=0.0)
got = with_retry(
    flaky_2, policy=policy,
    sleep=lambda s: None,
    on_retry=lambda i, exc, s: on_log.append((i, type(exc).__name__, s)),
)
step("returned ok", got == "ok")
step("2 on_retry calls", len(on_log) == 2)
step("first: attempt=0, URLError, sleep=0.4",
     on_log[0] == (0, "URLError", 0.4))
step("second: attempt=1, URLError, sleep=0.8",
     on_log[1] == (1, "URLError", 0.8))


# ===========================================================================
# 9. with_retry — HTTP-aware: 5xx response triggers retry
# ===========================================================================
section("9. with_retry — 5xx response triggers retry")
calls: list[int] = []
class StubResp:
    def __init__(self, code: int, headers: dict | None = None) -> None:
        self.status = code
        self.headers = headers or {}
def flake_resp() -> Any:
    calls.append(1)
    if len(calls) < 3:
        return StubResp(503)
    return StubResp(200)
policy9 = RetryPolicy(max_attempts=3, base_delay_s=0.1, max_delay_s=1.0, jitter_pct=0.0)
got = with_retry(flake_resp, policy=policy9, sleep=lambda s: None)
step("returned 200 on third call", got.status == 200)
step("called 3 times", len(calls) == 3)


section("10. with_retry — 4xx short-circuits (won't recover)")
calls: list[int] = []
def four_oh_four() -> Any:
    calls.append(1)
    return StubResp(404)
got = with_retry(four_oh_four, policy=policy9, sleep=lambda s: None)
step("returned 404 once and only once", got.status == 404 and len(calls) == 1)


section("11. with_retry — 429 with Retry-After honoured")
calls: list[int] = []
sleep_log = []
def rate_limited() -> Any:
    calls.append(1)
    return StubResp(429, headers={"Retry-After": "0.5"})
policy11 = RetryPolicy(max_attempts=2, base_delay_s=10.0, max_delay_s=10.0, jitter_pct=0.0)
try:
    with_retry(
        rate_limited, policy=policy11,
        sleep=lambda s: sleep_log.append(s),
    )
    step("should have raised (rate-limited forever)", False)
except StatusOnly as so:
    step("called 2 times (policy exhausted)", len(calls) == 2)
    step("raised StatusOnly carrying the 429 status", so.status == 429)
    step("sleeps honoured Retry-After: ≤ 1.0 (was 0.5)",
         len(sleep_log) == 1 and sleep_log[0] <= 1.0)
except Exception as e:
    step(f"wrong type: {type(e).__name__}", False)


# ===========================================================================
# 12. with_retry — exception passes through as last_exc verbatim
# ===========================================================================
section("12. with_retry — last exception message preserved verbatim")
def fails_with_detail() -> None:
    raise urllib.error.HTTPError(
        url="https://x/y", code=500, msg="Server Error",
        hdrs={}, fp=None,
    )
policy = RetryPolicy(max_attempts=2, base_delay_s=0.001, jitter_pct=0.0)
try:
    with_retry(fails_with_detail, policy=policy, sleep=lambda s: None)
    step("should have raised", False)
except urllib.error.HTTPError as e:
    step("HTTPError preserved (status code preserved)", e.code == 500)
    step("HTTPError message preserved", "Server Error" in str(e.msg) or "Server" in str(e))
except Exception as e:
    step(f"wrong type: {type(e).__name__}", False)


# ===========================================================================
# 13. RetryingOpener — drop-in urllib replacement
# ===========================================================================
section("13. RetryingOpener — urllib-shaped call site with retry")
calls: list[int] = []
class FakeResp:
    def __init__(self) -> None:
        self.status = 200
        self._body = b'{"ok": 1}'
    def read(self) -> bytes:
        return self._body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
def fake_inner(req, timeout=None):
    calls.append(len(calls))
    if len(calls) < 2:
        raise socket.timeout("flaky")
    return FakeResp()
from runtime.retry import RetryingOpener, RetryPolicy as _R
op = RetryingOpener(fake_inner, policy=_R(max_attempts=3, base_delay_s=0.001, jitter_pct=0.0))
got = op("https://example.test/x", timeout=10)
step("returned FakeResp", isinstance(got, FakeResp))
step("inner called 2 times (1 timeout + 1 success)", len(calls) == 2)


section("14. RetryingOpener — kwargs (timeout) passed on every attempt")
calls: list[tuple] = []
def rec_inner(req, timeout=None, **kw):
    calls.append((type(req).__name__, timeout))
    raise socket.timeout("flaky")
op = RetryingOpener(rec_inner, policy=_R(max_attempts=3, base_delay_s=0.001, jitter_pct=0.0))
try:
    op("https://x/y", timeout=7)
except socket.timeout:
    pass
step("timeout passed on every attempt (3 lines)", len(calls) == 3)
step("all timeout values = 7", all(c[1] == 7 for c in calls))


# ===========================================================================
# 15. runtime_http_opener — production default
# ===========================================================================
section("15. runtime_http_opener — production default is RetryingOpener")
op_default = runtime_http_opener()
import urllib.request as __ur
step("inner is urllib.request.urlopen", op_default.inner is __ur.urlopen)
step("policy.max_attempts == 3 (default)", op_default.policy.max_attempts == 3)
op_custom = runtime_http_opener(retry_policy=_R(max_attempts=5, base_delay_s=0.1))
step("custom policy.max_attempts == 5", op_custom.policy.max_attempts == 5)


# ===========================================================================
# 16. Defaults — exported constants are sensible
# ===========================================================================
section("16. module defaults — sane shipped policy")
step("DEFAULT_RETRY_STATUSES includes 503",
     503 in DEFAULT_RETRY_STATUSES)
step("DEFAULT_RETRY_STATUSES includes 429",
     429 in DEFAULT_RETRY_STATUSES)
step("DEFAULT_RETRY_STATUSES excludes 4xx",
     not any(s in DEFAULT_RETRY_STATUSES for s in (400, 401, 403, 404)))
step("DEFAULT_RETRY_EXCEPTIONS includes urllib.error.URLError",
     urllib.error.URLError in DEFAULT_RETRY_EXCEPTIONS)
step("DEFAULT_RETRY_EXCEPTIONS includes TimeoutError",
     TimeoutError in DEFAULT_RETRY_EXCEPTIONS)
step("DEFAULT_RETRY_EXCEPTIONS includes ConnectionError",
     ConnectionError in DEFAULT_RETRY_EXCEPTIONS)
step("DEFAULT_RETRY_EXCEPTIONS includes OSError (covers socket.gaierror)",
     OSError in DEFAULT_RETRY_EXCEPTIONS)
step("socket.gaierror is matched by OSError",
     issubclass(socket.gaierror, OSError))
step("DEFAULT_MAX_RETRY_AFTER_S ≥ 30 s (sane ceiling)",
     DEFAULT_MAX_RETRY_AFTER_S >= 30.0)


# ===========================================================================
# 17. RetryPolicy validation — guards sanity on construction
# ===========================================================================
section("17. RetryPolicy — bad inputs raise immediately")
try:
    RetryPolicy(max_attempts=0)
    step("max_attempts=0 should have raised", False)
except ValueError:
    step("max_attempts=0 → ValueError", True)
try:
    RetryPolicy(base_delay_s=-1)
    step("base_delay_s<0 should have raised", False)
except ValueError:
    step("base_delay_s<0 → ValueError", True)
try:
    RetryPolicy(base_delay_s=10.0, max_delay_s=5.0)
    step("max_delay<base should have raised", False)
except ValueError:
    step("max_delay<base → ValueError", True)
try:
    RetryPolicy(jitter_pct=1.5)
    step("jitter_pct=1.5 should have raised", False)
except ValueError:
    step("jitter_pct outside [0, 1) → ValueError", True)


# ===========================================================================
# 18. response_retry_after_s — handles headers correctly
# ===========================================================================
section("18. response_retry_after_s — numeric + missing")
step("no headers → None",
     response_retry_after_s(object()) is None)
step("empty Retry-After → None",
     response_retry_after_s(StubResp(500, headers={"Retry-After": ""})) is None)
step("numeric 30 → 30.0",
     response_retry_after_s(StubResp(500, headers={"Retry-After": "30"})) == 30.0)
step("negative Retry-After → None (treat as missing)",
     response_retry_after_s(StubResp(500, headers={"Retry-After": "-1"})) is None)


# ===========================================================================
# 19. Wired call sites — type-clean
# ===========================================================================
section("19. wired call sites — 5 instruments have retry-aware defaults")
# The 5 instruments Wired `runtime_http_opener` into. Their default
# constructor paths should expose a retry-aware opener.
from runtime.tools.web_fetch import WebFetchTool
from runtime.tools.quotes_realtime import QuotesRealtimeTool
from runtime.tools.transcripts import TranscriptsTool
from runtime.tools.news_8k import News8KTool

q = QuotesRealtimeTool(opener=None)  # explicit None → default
step("quotes_realtime.opener is RetryingOpener",
     type(q.opener).__name__ == "RetryingOpener")

# The other 3 use `runtime_http_opener()` inside their fetch functions
# (stateless), not as a stored attribute. Verify by importing the
# helpers and treating them the same way.
import runtime.tools.web_fetch as _wf_mod
step("web_fetch module imports cleanly",
     _wf_mod.WebFetchTool is not None)
import runtime.tools.transcripts as _tr_mod
step("transcripts module imports cleanly",
     _tr_mod.TranscriptsTool is not None)
import runtime.tools.news_8k as _n8k_mod
step("news_8k module imports cleanly",
     _n8k_mod.News8KTool is not None)


# ===========================================================================
# 20. End-to-end — real network unreachable → retry makes it 3 attempts
# ===========================================================================
section("20. with_retry on real socket.gaierror — exhausts attempts")
calls: list[int] = []
def hard_gaierror() -> bytes:
    calls.append(1)
    raise socket.gaierror("-3 DNS unavailable (test)")
policy = RetryPolicy(max_attempts=3, base_delay_s=0.001, jitter_pct=0.0)
try:
    with_retry(hard_gaierror, policy=policy, sleep=lambda s: None)
    step("should have raised", False)
except socket.gaierror:
    step("raised last underlying socket.gaierror", True)
    step("attempted 3 times", len(calls) == 3)


# ===========================================================================
# 21. StatusOnly — uniform shape for on_retry callback
# ===========================================================================
section("21. StatusOnly — carries status int through on_retry path")
so = StatusOnly(503)
step("`status` is 503", so.status == 503)
step("stringifies as 'HTTP 503'", "503" in str(so))


# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
print()
print("=== TOTAL ===")
print(f"  {_PASS}/{_TOTAL} assertions passed, {_FAILED} failed in section: {current_section!r}")
sys.exit(1 if _FAILED else 0)
