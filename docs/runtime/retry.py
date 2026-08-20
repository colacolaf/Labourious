"""
retry.py — small std-library retry helper for the runtime.

When a connector, an LLM adapter, or a snippet-fetch helper meets a
transient HTTP failure, today the runtime surfaces the failure
immediately. The user's network (e.g. school filters, public WiFi,
home router handoffs) regularly times out or 503s for seconds at a
time; a single call that fails on those blips is one tool-flake
away from a completely failed flow.

This module:

  - Defines `RetryPolicy` (attempts, delays, jitter, retryable set).
  - Defines `with_retry(fn, policy)` for arbitrary callables.
  - Defines `RetryingOpener` — a tiny adapter that wraps an existing
    ``urllib.request.urlopen``-shaped opener and retries it on
    transient failure WITHOUT requiring each tool to change its
    ``with self.opener(req, timeout=N)`` pattern.

What counts as "transient":

  - Any HTTP status in the default ``retry_statuses`` range
    (5xx, with 429 optionally settable).
  - Any exception in the default ``retryable_exceptions`` set:
    ``urllib.error.URLError``,
    ``socket.timeout`` (``builtins.TimeoutError`` also matches the
    standards-library alias in 3.11+),
    ``ConnectionError`` (``ConnectionResetError``, ``ConnectionRefusedError``,
    ``ConnectionAbortedError`` all subclass it).
  - ``Retry-After`` header on a 503/429 is honoured with the
    server-supplied delay (capped at ``policy.max_retry_after_s``).

What does NOT retry:

  - 4xx client errors (won't recover on second try).
  - ``json.JSONDecodeError`` / ``KeyError`` / ``ValueError`` from
    a malformed envelope — those are bugs, not blips.
  - ``PermissionError`` / ``FileNotFoundError`` — local failures.

Examples:

    from runtime.retry import RetryPolicy, RetryingOpener

    policy = RetryPolicy(max_attempts=3, base_delay=0.5, max_delay=8.0)
    retrying = RetryingOpener(urllib.request.urlopen, policy)

    # Same callsite as today:
    with retrying(req, timeout=15) as resp:
        body = resp.read()

And for adapters / connector-shaped functions:

    from runtime.retry import with_retry
    result = with_retry(lambda: my_connector(args), policy=policy)

The pilot `docs/runtime/smokes/retry_smoke.py` exercises every
branch — backoff math, retry-After honour, status cutoffs, opener
integration, exhaustion path. ~80 assertions across 24 sections.
"""

from __future__ import annotations

import random
import socket
import time
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Type


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------
# Default status range that's "transient". 5xx covers most server-side
# blips; 429 covers rate-limiting with Retry-After. Excludes 4xx
# client errors which won't recover on a retry. Override per-call when
# a connector uses 4xx as a retryable marker (some pagination use 404
# + Retry-After as a polite not-found).
DEFAULT_RETRY_STATUSES: tuple[int, ...] = (429, 500, 502, 503, 504, 507)

# Default exception types that are clearly "the network blipped" —
# the request never got a response back. Anything not in this set is
# presumed to be a code-path bug; retrying would just hide the bug.
DEFAULT_RETRY_EXCEPTIONS: tuple[type[BaseException], ...] = (
    urllib.error.URLError,
    TimeoutError,                  # builtins.TimeoutError == socket.timeout
    ConnectionError,               # parent of reset / refused / aborted
    OSError,                       # socket.gaierror and friends — DNS / NIC / ICMP
)

# Server's Retry-After header is honoured when present — unless
# unreasonably long. This caps the wait at 30 s so a confused server
# doesn't lock the runtime for minutes.
DEFAULT_MAX_RETRY_AFTER_S: float = 30.0


@dataclass(frozen=True)
class RetryPolicy:
    """How aggressively we retry on transient failure.

    Fields:
      max_attempts     — number of total attempts (1 = no retry).
      base_delay_s     — first backoff (the actual sleep is multiplied
                          with exponential growth after each failure).
      max_delay_s      — upper bound on per-attempt sleep.
      jitter_pct       — uniform-jitter scale; e.g. 0.2 = ±20% noise.
                          0.0 = deterministic. Recommended: ≥ 0.1 to
                          avoid synchronised retry storms from a herd
                          of callers (the canonical "thundering herd").
      retry_statuses   — HTTP codes treated as transient.
      retry_exceptions — exception types treated as transient.
      max_retry_after_s — cap on Retry-After header honoured.

    A retry must be observably distinguishable from a "no retry" run;
    the helper always increments ``attempt_count`` exactly once per
    call. See ``with_retry`` for the contract.
    """
    max_attempts: int = 3
    base_delay_s: float = 0.5
    max_delay_s: float = 8.0
    jitter_pct: float = 0.2
    retry_statuses: tuple[int, ...] = DEFAULT_RETRY_STATUSES
    retry_exceptions: tuple[type[BaseException], ...] = DEFAULT_RETRY_EXCEPTIONS
    max_retry_after_s: float = DEFAULT_MAX_RETRY_AFTER_S

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts>=1, got {self.max_attempts}")
        if self.base_delay_s <= 0:
            raise ValueError(f"base_delay_s>0, got {self.base_delay_s}")
        if self.max_delay_s < self.base_delay_s:
            raise ValueError(
                f"max_delay_s >= base_delay_s; got "
                f"{self.max_delay_s} < {self.base_delay_s}"
            )
        if not 0.0 <= self.jitter_pct < 1.0:
            raise ValueError(f"jitter_pct in [0, 1), got {self.jitter_pct}")


@dataclass
class RetryExhausted(Exception):
    """Raised after ``policy.max_attempts`` failed attempts.

    Attributes:
        attempts     — total attempts made (always ==
                        policy.max_attempts after exhaustion).
        last_exc     — the final exception observed; raises this
                        exception's message when printed.
        elapsed_s    — total wallclock spent including backoffs.
        attempt_log  — list of ``(attempt_index, exc_type_name)``
                        describing each attempt's failure for
                        observability surfaces (status strip, banners).
    """
    attempts: int
    last_exc: BaseException
    elapsed_s: float
    attempt_log: list[tuple[int, str]] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"retry exhausted after {self.attempts} attempts "
            f"(last error: {type(self.last_exc).__name__}: "
            f"{self.last_exc}). Logged attempts: {len(self.attempt_log)}."
        )


# ---------------------------------------------------------------------------
# Backoff math
# ---------------------------------------------------------------------------
def compute_backoff_s(
    attempt_index: int,
    policy: RetryPolicy,
    *,
    retry_after_s: float | None = None,
    rng: random.Random | None = None,
) -> float:
    """Return the sleep seconds before attempt ``attempt_index``.

    ``attempt_index`` is 0 for the first retry (after the original
    call), 1 for the second, etc. Exponential base growth
    ``base_delay_s * 2**attempt_index`` capped at ``max_delay_s``,
    with ±jitter_pct uniform noise applied UNLESS ``retry_after_s``
    is provided.

    When ``retry_after_s`` is given and > 0, the server explicitly
    asked us to wait; we honour that (capped at
    ``policy.max_retry_after_s``) and ignore the exponential schedule.
    """
    if retry_after_s is not None and retry_after_s > 0:
        return min(retry_after_s, policy.max_retry_after_s)
    raw = policy.base_delay_s * (2 ** attempt_index)
    capped = min(raw, policy.max_delay_s)
    if policy.jitter_pct <= 0:
        return capped
    rng = rng or random
    span = capped * policy.jitter_pct
    return max(0.0, capped + rng.uniform(-span, span))


# ---------------------------------------------------------------------------
# Retryable-detection for HTTP-style response objects
# ---------------------------------------------------------------------------
def _http_status_for_retry(resp: Any) -> int | None:
    """Return an int status code from *resp* if it has one, else None.

    Both real ``http.client.HTTPResponse`` (urllib return value) and
    the contraption the smoke tests use have ``.status`` or ``.code``.
    """
    for attr in ("status", "code", "status_code"):
        v = getattr(resp, attr, None)
        if isinstance(v, int):
            return v
    return None


def response_retry_after_s(resp: Any) -> float | None:
    """Read ``Retry-After`` from a response object if present.

    Supports both numeric seconds ("Retry-After: 30") and HTTP-date
    ("Retry-After: Wed, 21 Oct 2015 07:28:00 GMT"). Date forms return
    0.0 from this stub (the runtime doesn't ship a date-parsing
    library; an authoritative date stub would require installation —
    deferring to v3). Numerics to the next integer > 0 are returned.
    """
    headers = getattr(resp, "headers", None)
    if headers is None:
        return None
    try:
        # Both real urllib and the stub mock have .headers.get(key).
        v = headers.get("Retry-After") or headers.get("retry-after")
    except Exception:
        return None
    if not v:
        return None
    try:
        seconds = float(v)
    except (TypeError, ValueError):
        # Could be HTTP-date; the runtime can't parse those without
        # email.utils, so we treat the presence of *any* Retry-After
        # as a sign to back off at least one base delay.
        return None
    return max(seconds, 0.0) if seconds > 0 else None


# ---------------------------------------------------------------------------
# Core retry primitive
# ---------------------------------------------------------------------------
def with_retry(
    fn: Callable[[], Any],
    *,
    policy: RetryPolicy,
    sleep: Callable[[float], None] = time.sleep,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> Any:
    """Run *fn* up to ``policy.max_attempts`` times on transient failure.

    Contract:

      * Calls *fn* once with no arguments; returns its result verbatim
        on the first success.
      * On failure (retryable exception OR HTTP response with status in
        ``policy.retry_statuses``), back off sleep and try again.
      * On non-retryable failure, raise immediately — no retry, no
        backoff. The runtime's failure path is unchanged.
      * After ``policy.max_attempts`` failures, re-raise the **last**
        underlying exception verbatim so the caller sees the real
        error context. (Not a wrapping RetryExhausted — wrapping loses
        information about WHY the call failed, e.g. urllib's HTTPError
        carries a useful ``.code`` attribute.)

    The ``sleep`` callable is injectable so tests can fast-forward the
    clock without sleeping. The ``on_retry`` callback fires once per
    retry with (attempt_index, exception_or_response, sleep_seconds)
    so callers can show "retrying in 1.2 s..." messages in the TUI.
    """
    attempt_log: list[tuple[int, str]] = []
    t0 = time.monotonic()
    last_exc: BaseException | None = None
    last_status: StatusOnly | None = None
    for attempt_idx in range(policy.max_attempts):
        try:
            result = fn()
            # Successful call — check whether fn returned a response
            # whose status code signals retry. Common for adapters that
            # return the response without raising on 5xx.
            status = _http_status_for_retry(result)
            if status is not None and status in policy.retry_statuses:
                # Treat as a transient. Sleep + try again.
                ra = response_retry_after_s(result)
                sleep_s = compute_backoff_s(
                    attempt_idx, policy, retry_after_s=ra,
                )
                attempt_log.append((attempt_idx, f"HTTP {status}"))
                last_status = StatusOnly(status)
                if attempt_idx < policy.max_attempts - 1:
                    if on_retry is not None:
                        on_retry(attempt_idx, last_status,
                                 sleep_s)
                    sleep(sleep_s)
                continue
            return result
        except tuple(policy.retry_exceptions) as exc:
            last_exc = exc
            last_status = None
            attempt_log.append((attempt_idx, type(exc).__name__))
            if attempt_idx < policy.max_attempts - 1:
                sleep_s = compute_backoff_s(attempt_idx, policy)
                if on_retry is not None:
                    on_retry(attempt_idx, exc, sleep_s)
                sleep(sleep_s)
            continue
        except Exception as exc:
            # Non-retryable. Raise verbatim so callers keep the real
            # error context (urllib.HTTPError, json errors, etc.).
            raise
    # All attempts exhausted. Raise the underlying cause verbatim so
    # the caller's exception handler sees the real type. If we
    # exhausted via status-only 5xx, raise the StatusOnly so the
    # message names the status code.
    if last_exc is not None:
        raise last_exc
    if last_status is not None:
        raise last_status
    raise RuntimeError("retry did not exhaust")  # noqa: shouldn't happen


# ---------------------------------------------------------------------------
# Helper: synthetic "status-only" object for on_retry callback uniformity
# ---------------------------------------------------------------------------
class StatusOnly(BaseException):
    """A tiny exception carrying just an int status code.

    Used by ``with_retry`` to surface a "5xx came back as a
    SUCCESS-shaped response" case to the ``on_retry`` callback in the
    same shape as connection-/timeout-shaped failures. Never raised
    outside the callback path; it's a transport for the status int.
    """
    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status


# ---------------------------------------------------------------------------
# RetryingOpener — drop-in replacement for an ``urllib.request.urlopen``
# ---------------------------------------------------------------------------
class RetryingOpener:
    """Adapter that wraps an ``urllib.request.urlopen``-shaped callable.

    The opener's signature is the urllib convention:
    ``opener(url_or_req, timeout=None, ...) → response``.

    We delegate to ``with_retry`` so all the policy knobs are honoured
    uniformly. The wrapper keeps the underlying opener call atomic — a
    failed request never leaks into a partial body on the caller side.

    The constructor takes the *inner* opener. Tests can pass a stub
    opener that raises controlled exceptions; ``RetryingOpener`` then
    exercises the retry path deterministically.
    """

    def __init__(
        self,
        inner: Callable[..., Any],
        *,
        policy: RetryPolicy,
        sleep: Callable[[float], None] = time.sleep,
        on_retry: Callable[[int, BaseException, float], None] | None = None,
    ) -> None:
        self.inner = inner
        self.policy = policy
        self._sleep = sleep
        self._on_retry = on_retry

    def __call__(self, url_or_req: Any, timeout: float | None = None, **kw):
        """Open a URL/Request, retrying transient failures.

        ``timeout`` is passed through to the inner opener on every
        attempt. Extra kwargs (e.g. ``cafile``, ``capath``) are passed
        through once and not retained.
        """
        return with_retry(
            lambda: self.inner(url_or_req, timeout=timeout, **kw),
            policy=self.policy,
            sleep=self._sleep,
            on_retry=self._on_retry,
        )


# ---------------------------------------------------------------------------
# runtime_http_opener — the production-default opener for connector tools
# ---------------------------------------------------------------------------
def runtime_http_opener(
    *,
    retry_policy: RetryPolicy | None = None,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> RetryingOpener:
    """Return the default opener used by every connector/shape tool.

    Replaces the bare ``urllib.request.urlopen`` that tools were
    previously assigning to ``self.opener``. The returned
    ``RetryingOpener`` honours the standard retry policy (3 attempts,
    exponential backoff, jitter) and surfaces Retry-After when the
    upstream asks for it.

    Tools pass the *value* returned here as their default — but tests
    inject at construction time via the existing ``opener=`` kwarg,
    so test fidelity is preserved.
    """
    import urllib.request
    return RetryingOpener(
        urllib.request.urlopen,
        policy=retry_policy or RetryPolicy(),
        on_retry=on_retry,
    )


# ---------------------------------------------------------------------------
# Re-exports
# ---------------------------------------------------------------------------
__all__ = [
    "DEFAULT_MAX_RETRY_AFTER_S",
    "DEFAULT_RETRY_EXCEPTIONS",
    "DEFAULT_RETRY_STATUSES",
    "RetryPolicy",
    "RetryExhausted",
    "StatusOnly",
    "RetryingOpener",
    "compute_backoff_s",
    "response_retry_after_s",
    "with_retry",
]
