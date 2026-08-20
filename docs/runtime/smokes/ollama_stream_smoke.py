"""ollama_stream_smoke.py — pilot for OllamaAdapter.stream(...) (P1 item).

Goals: the new `stream()` method on OllamaAdapter correctly yields
StreamChunks from Ollama's newline-delimited JSON streaming response,
finishes with a StreamChunk carrying `usage` + `finish_reason="stop"`,
and (when the upstream chokes) raises a clean RuntimeError instead of
returning malformed chunks.

Counterpart tests:
- providers that support stream(): also bound in openai_compat, anthropic,
  cohere, gemini. The Ollama/stream path was the only gap.

Approach: monkey-patch the adapter's underlying urllib opener to feed
synthetic NDJSON lines mirroring Ollama's `/api/chat?stream=true`
format. Then assert the public shape of the StreamChunk sequence.

Counts: ~ 32 assertions across 8 sections.
"""
from __future__ import annotations

import io
import json
import os
import sys
import urllib.error as _urllib_error  # noqa: F401

sys.path.insert(0, "docs")

from runtime.adapters.ollama import OllamaAdapter  # noqa: E402
from runtime.adapters._streaming import StreamChunk  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers: synthetic NDJSON pulse that mimics Ollama's stream
# ---------------------------------------------------------------------------

def _ndjson_lines(chunks, final):
    """Build the NDJSON body Ollama emits.

    `chunks` is a list of (delta_text, _done_bool_unused) tuples — all
    chunks are emitted as `done: false` here; the trailing summary
    line is `done: true` and carries usage counts.

    For tests that need the FINAL delta + done=true collapsed onto a
    single line (Ollama sometimes does this), use ``_single_done_line``
    instead.
    """
    body_lines: list[str] = []
    for i, (delta, _done) in enumerate(chunks):
        body_lines.append(json.dumps({
            "model": "fake-3b",
            "created_at": "2024-01-15T10:00:00Z",
            "message": {"role": "assistant", "content": delta},
            "done": False,
        }))
    body_lines.append(json.dumps({
        "model": "fake-3b",
        "done": True,
        "prompt_eval_count": final.get("in", 50),
        "eval_count": final.get("out", 0),
        "total_duration": final.get("dur", 1_000_000_000),
    }))
    return ("\n".join(body_lines) + "\n").encode("utf-8")


class _FakeRawResp(io.BytesIO):
    """Acts like the file-like object urllib.request.urlopen returns.

    Iter over it yields bytes lines; close() is a no-op; the body is
    exposed via the buffer.
    """

    def __init__(self, body: bytes):
        super().__init__(body)

    def __iter__(self):
        return iter(self.getvalue().splitlines(keepends=True))

    def close(self):
        pass


def _make_resp_iter(body: bytes):
    obj = _FakeRawResp(body)
    return obj


def _fake_opener_factory(plan):
    """plan = list of (url_substr, body_bytes_or_status_int)."""
    queue = [{"sub": p[0], "body": p[1], "status": p[2], "fresh": True}
             for p in plan]
    receipts: list[str] = []

    def opener(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
        body = b""
        for e in queue:
            if e["sub"] in url and e["fresh"]:
                e["fresh"] = False
                receipts.append(url)
                if e["status"] != 0:
                    raise _urllib_error.HTTPError(
                        url, e["status"],
                        f"HTTP {e['status']}", {}, None,
                    )
                body = e["body"]
                break
        else:
            raise AssertionError(f"no plan entry matched URL: {url}")
        return _make_resp_iter(body)

    opener.plan_receipts = lambda: list(receipts)
    poster = opener
    return poster


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
# 1. Basic stream — 3 deltas + final usage
# ---------------------------------------------------------------------------

def test_1_basic_stream():
    section("1. stream emits deltas + final usage (3 chunks)")
    chunks = [
        ("Hello", False),
        (", world", False),
        ("!", True),
    ]
    body = _ndjson_lines(chunks, final={"in": 12, "out": 3, "dur": 1_000_000})
    opener = _fake_opener_factory([("chat", body, 0)])
    tool = OllamaAdapter(model="ollama/llama3.2:3b")
    # Adapter uses urllib.request.urlopen by default. Monkey-patch.
    import runtime.adapters.ollama as _oll_mod
    orig = _oll_mod.urllib.request.urlopen
    _oll_mod.urllib.request.urlopen = opener
    try:
        chunks_out: list[StreamChunk] = list(
            tool.stream([{"role": "user", "content": "hi"}],
                        system="be terse"))
    finally:
        _oll_mod.urllib.request.urlopen = orig

    non_final = [c for c in chunks_out if c.delta]
    final = next((c for c in chunks_out if c.finish_reason == "stop"), None)
    check("3 delta chunks emitted", len(non_final) == 3)
    check("final chunk exists", final is not None)
    check("deltas concat = 'Hello, world!'",
          "".join(c.delta for c in non_final) == "Hello, world!")
    if final is not None:
        check("final finish_reason='stop'", final.finish_reason == "stop")
        check("final usage.out_tokens=3",
              final.usage and final.usage["completion_tokens"] == 3)
        check("final usage.cost_usd_estimate=0.0 (local LLM)",
              final.usage and final.usage["cost_usd_estimate"] == 0.0)


# ---------------------------------------------------------------------------
# 2. Empty upstream stream (no deltas, just done=true)
# ---------------------------------------------------------------------------

def test_2_empty_stream():
    section("2. empty stream still emits final chunk (2)")
    chunks = []  # no deltas
    body = b'{"model":"fake","done":true,"prompt_eval_count":0,"eval_count":0}\n'
    opener = _fake_opener_factory([("chat", body, 0)])
    tool = OllamaAdapter(model="ollama/llama3.2:3b")
    import runtime.adapters.ollama as _oll_mod
    orig = _oll_mod.urllib.request.urlopen
    _oll_mod.urllib.request.urlopen = opener
    try:
        chunks_out = list(tool.stream([{"role": "user", "content": ""}],
                                       system=""))
    finally:
        _oll_mod.urllib.request.urlopen = orig
    non_final = [c for c in chunks_out if c.delta]
    final = next((c for c in chunks_out if c.finish_reason == "stop"), None)
    check("no delta chunks emitted", len(non_final) == 0)
    check("final chunk still emitted", final is not None)


# ---------------------------------------------------------------------------
# 3. Single delta, then done=true on same line
# ---------------------------------------------------------------------------

def test_3_single_line_done_in_one():
    section("3. done=true on a delta line is treated as final (3)")
    # Ollama sometimes collapses the last delta + done + counts into one line.
    body = (
        b'{"model":"fake","message":{"role":"assistant","content":"ALL done"},'
        b'"done":true,"prompt_eval_count":5,"eval_count":1}\n'
    )
    opener = _fake_opener_factory([("chat", body, 0)])
    tool = OllamaAdapter(model="ollama/llama3.2:3b")
    import runtime.adapters.ollama as _oll_mod
    orig = _oll_mod.urllib.request.urlopen
    _oll_mod.urllib.request.urlopen = opener
    try:
        chunks_out = list(tool.stream([{"role": "user", "content": "x"}],
                                       system=""))
    finally:
        _oll_mod.urllib.request.urlopen = orig
    # It depends on the upstream model — some emit delta+done as one
    # chunk with both done+content. Our stream now emits the delta
    # first (delta with content) and the final usage chunks at the
    # very end of all iterations, regardless. So we expect 1 or 2
    # chunks total: 1 delta ("ALL done") + 1 final stop chunk.
    non_final = [c for c in chunks_out if c.delta]
    final = next((c for c in chunks_out if c.finish_reason == "stop"), None)
    check("delta chunk (with content) emitted", len(non_final) == 1)
    check("final chunk exists", final is not None)
    if final is not None:
        # Counts come from the same line that has done+delta because
        # the upstream emitted only one line. Whatever the body has,
        # the final stop chunk reports it.
        check("final usage carries the counts from the same line",
              final.usage["prompt_tokens"] == 5
              and final.usage["completion_tokens"] == 1)


# ---------------------------------------------------------------------------
# 4. Malformed JSON line — silently dropped
# ---------------------------------------------------------------------------

def test_4_malformed_json():
    section("4. malformed JSON line dropped, rest still emitted (3)")
    body = (
        b"{this-is-not-json}\n"
        b'{"message":{"role":"assistant","content":"good"},"done":false}\n'
        b'still-broken\n'
        b'{"message":{"role":"assistant","content":"bye"},"done":true,'  # + final done
        b'"prompt_eval_count":2,"eval_count":2}\n'
    )
    opener = _fake_opener_factory([("chat", body, 0)])
    tool = OllamaAdapter(model="ollama/llama3.2:3b")
    import runtime.adapters.ollama as _oll_mod
    orig = _oll_mod.urllib.request.urlopen
    _oll_mod.urllib.request.urlopen = opener
    try:
        chunks_out = list(tool.stream([{"role": "user", "content": "x"}],
                                       system=""))
    finally:
        _oll_mod.urllib.request.urlopen = orig
    non_final = [c for c in chunks_out if c.delta]
    check("2 valid deltas kept", len(non_final) == 2)
    check("non-final concatenated = 'goodbye'",
          "".join(c.delta for c in non_final) == "goodbye")
    final = next((c for c in chunks_out if c.finish_reason == "stop"), None)
    check("final chunk still emitted (after partial noise)",
          final is not None)


# ---------------------------------------------------------------------------
# 5. HTTP 503 raises RuntimeError
# ---------------------------------------------------------------------------

def test_5_http_503():
    section("5. HTTP 503 → RuntimeError (1)")
    opener = _fake_opener_factory([("chat", b"oops", 503)])
    tool = OllamaAdapter(model="ollama/llama3.2:3b")
    import runtime.adapters.ollama as _oll_mod
    orig = _oll_mod.urllib.request.urlopen
    _oll_mod.urllib.request.urlopen = opener
    try:
        try:
            list(tool.stream([{"role": "user", "content": "x"}], system=""))
            err = None
        except RuntimeError as e:
            err = e
        check("503 surfaces as RuntimeError", err is not None and "503" in str(err))
    finally:
        _oll_mod.urllib.request.urlopen = orig


# ---------------------------------------------------------------------------
# 6. URLError (Ollama not running) → RuntimeError
# ---------------------------------------------------------------------------

def test_6_url_error():
    section("6. URLError (Ollama down) → RuntimeError (1)")
    def boom(req, timeout=None):
        raise _urllib_error.URLError("connection refused")
    tool = OllamaAdapter(model="ollama/llama3.2:3b")
    import runtime.adapters.ollama as _oll_mod
    orig = _oll_mod.urllib.request.urlopen
    _oll_mod.urllib.request.urlopen = boom
    try:
        try:
            list(tool.stream([{"role": "user", "content": "x"}], system=""))
            err = None
        except RuntimeError as e:
            err = e
        check("URLError surfaces as RuntimeError",
              err is not None and "not reachable" in str(err))
    finally:
        _oll_mod.urllib.request.urlopen = orig


# ---------------------------------------------------------------------------
# 7. StreamChunk attribute shape
# ---------------------------------------------------------------------------

def test_7_chunk_shape():
    section("7. StreamChunk shape contracts (5)")
    body = (b'{"message":{"role":"assistant","content":"x"},"done":true,'
            b'"prompt_eval_count":1,"eval_count":1}\n')
    opener = _fake_opener_factory([("chat", body, 0)])
    tool = OllamaAdapter(model="ollama/llama3.2:3b")
    import runtime.adapters.ollama as _oll_mod
    orig = _oll_mod.urllib.request.urlopen
    _oll_mod.urllib.request.urlopen = opener
    try:
        chunks_out = list(tool.stream([{"role": "user", "content": "x"}],
                                       system=""))
    finally:
        _oll_mod.urllib.request.urlopen = orig
    final = chunks_out[-1]
    check("final.delta is empty string",
          isinstance(final.delta, str) and final.delta == "")
    check("final.finish_reason is str 'stop'",
          isinstance(final.finish_reason, str) and final.finish_reason == "stop")
    check("final.usage is dict",
          isinstance(final.usage, dict))
    check("'prompt_tokens' key on final.usage",
          "prompt_tokens" in final.usage)
    check("'cost_usd_estimate' key on final.usage",
          "cost_usd_estimate" in final.usage)


# ---------------------------------------------------------------------------
# 8. body sets stream=true
# ---------------------------------------------------------------------------

def test_8_body_stream_true():
    section("8. POST body has stream: true (2)")
    captured: list[dict] = []
    out_body = (
        b'{"message":{"role":"assistant","content":"ok"},"done":true,'
        b'"prompt_eval_count":1,"eval_count":1}\n'
    )

    def capture(req, timeout=None):
        body_bytes = req.data if isinstance(req.data, bytes) else req.data.encode("utf-8")
        captured.append(json.loads(body_bytes))
        return _make_resp_iter(out_body)

    tool = OllamaAdapter(model="ollama/llama3.2:3b")
    import runtime.adapters.ollama as _oll_mod
    orig = _oll_mod.urllib.request.urlopen
    _oll_mod.urllib.request.urlopen = capture
    try:
        list(tool.stream([{"role": "user", "content": "x"}], system="hi"))
    finally:
        _oll_mod.urllib.request.urlopen = orig
    check("body.stream == True", captured[0]["stream"] is True)
    check("body has 'messages' list",
          isinstance(captured[0]["messages"], list)
          and len(captured[0]["messages"]) >= 2
          and captured[0]["messages"][0]["role"] == "system")


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_1_basic_stream,
        test_2_empty_stream,
        test_3_single_line_done_in_one,
        test_4_malformed_json,
        test_5_http_503,
        test_6_url_error,
        test_7_chunk_shape,
        test_8_body_stream_true,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            FAIL += 1
            print(f"  EXC in {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== {OK}/{OK + FAIL} assertions passed ===")
    sys.exit(1 if FAIL > 0 else 0)
