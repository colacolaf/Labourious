"""domain_8_smoke.py — pilot for [domain-8] per-connector ETag round-trip.

The existing snippet_etag_smoke §10 monkey-patches the connector methods
to short-circuit *before* the actual HTTP layer; it confirms the snippet
cache + sidecar wiring but NOT the real network round-trip. This pilot
closes that gap by:

  1. Stubbing **only** the per-tool opener/urllib layer, NOT any
     connector method, so `_fetch()` / `search()` / `list_for_ticker()`
     run their actual code.

  2. Verifying the actual HTTP request sent to upstream carries the
     ``If-None-Match: <cached_etag>`` header (with the value from the
     sidecar).

  3. Verifying that an upstream response of 304 Not Modified
     causes the connector to return
     ``ToolResult(status="UNCHANGED", etag=...)`` with the "right"
     ETag (the upstream-echoed one, or fallback to the sent one).

  4. Exercising ALL THREE snippet-cacheable connectors:
        - ``news_8k.search``
        - ``sec_edgar_fulltext.search``
        - ``transcripts.list_for_ticker``

  5. Verifying the ``call_tool`` injection path: a prior successful run
     leaves a sidecar with ``cached_etag``; the *next* call through
     ``call_tool(run_id=...)`` injects it into the connector's call.

Counts: ~ 50 assertions across 11 sections.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.error as _urllib_error  # noqa: F401
import urllib.request as _urllib_request  # noqa: F401

sys.path.insert(0, "docs")

from runtime.tools import ToolResult  # noqa: E402
from runtime.tools.news_8k import News8KTool  # noqa: E402
from runtime.tools.sec_edgar_fulltext import SECEdgarFullTextTool  # noqa: E402
from runtime.tools.transcripts import TranscriptsTool  # noqa: E402


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
# Helpers: opener factories
# ---------------------------------------------------------------------------

def make_news_opener(captured, *, status=200, body=b"", etag=""):
    """Make a `_default_opener`-compatible function. 3-arg signature
    matching what `_fetch()` calls: (url, headers, if_none_match=None).
    """
    def fake(url, headers=None, *, if_none_match=None):
        captured.append({
            "url": url,
            "headers": dict(headers or {}),
            "if_none_match_sent": if_none_match,
        })
        return status, body, etag
    return fake


def make_aapl_efts_body(etag: str | None = None) -> bytes:
    """Real-shape EFTS payload for `ticker="AAPL"`. Includes display_names
    with ticker `(AAPL)` and `(CIK 0000320193)` so the local filter
    recognises the row.
    """
    return json.dumps({
        "hits": {
            "total": {"value": 1, "relation": "eq"},
            "hits": [{
                "_source": {
                    "adsh": "0000320193-24-000081",
                    "ciks": ["0000320193"],
                    "display_names": [
                        "Apple Inc. (AAPL) (CIK 0000320193)"
                    ],
                    "forms": "8-K",
                    "file_date": "2024-01-15",
                    "biz_locations": ["Cupertino, CA"],
                    "items": ["2.02"],
                },
                "_id": "000032019324000081:filename.htm",
            }],
        }
    }).encode("utf-8")


def make_sec_edgar_opener(captured, *, status=200, body=b"", etag="",
                            raise_http_error=None):
    """Make a urllib-compatible opener shim for sec_edgar.search().

    sec_edgar_fulltext's `search()` calls ``urllib.request.urlopen``
    directly (not through a `_opener` slot). So we patch urlopen at
    the urllib module level.
    """
    class _Resp:
        def __init__(self, body, headers=None, status=200):
            self._body = body
            self._h = headers or {}
            self.status = status
            self.code = status

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        @property
        def headers(self):
            return self._h

    def fake_urlopen(req, timeout=None):
        captured.append({
            "url": req.full_url,
            "headers": dict(req.header_items()),
        })
        if raise_http_error is not None:
            raise _urllib_request.HTTPError(
                req.full_url, raise_http_error,
                "Not Modified" if raise_http_error == 304 else "Error",
                {"ETag": etag} if etag else {}, None,
            )
        return _Resp(body, headers={"ETag": etag} if etag else {}, status=status)
    return fake_urlopen


# ---------------------------------------------------------------------------
# 1. news_8k.search sends If-None-Match when if_none_match provided
# ---------------------------------------------------------------------------

def test_1_news_8k_sends_inm():
    section("1. news_8k.search sends If-None-Match when provided (5)")
    captured = []
    body = make_aapl_efts_body()
    tool = News8KTool(opener=make_news_opener(
        captured, status=200, body=body, etag='W/"v1-abc"'))
    tr = tool.search(ticker="AAPL", if_none_match='W/"prior-v4"')
    check("1 captured call", len(captured) == 1)
    if captured:
        check("If-None-Match kwarg forwarded to opener",
              captured[0]["if_none_match_sent"] == 'W/"prior-v4"')
        check("User-Agent header is sent",
              "User-agent" in captured[0]["headers"]
              or "User-Agent" in captured[0]["headers"])
    check("ToolResult.status=SUCCESS (200 path)", tr.status == "SUCCESS")
    check("ToolResult.etag='W/\"v1-abc\"' (upstream echoed)",
          tr.etag == 'W/"v1-abc"')


# ---------------------------------------------------------------------------
# 2. news_8k 304 → UNCHANGED with fallback to sent ETag
# ---------------------------------------------------------------------------

def test_2_news_8k_304_no_upstream_etag():
    section("2. news_8k 304 (no upstream ETag) → UNCHANGED + fallback etag (3)")
    captured = []
    tool = News8KTool(opener=make_news_opener(
        captured, status=304, body=b"", etag=""))
    tr = tool.search(ticker="AAPL", if_none_match='W/"prior-v4"')
    check("status=UNCHANGED", tr.status == "UNCHANGED")
    check("etag falls back to the one we sent", tr.etag == 'W/"prior-v4"')
    check("note mentions ETag matched or 304",
          "ETag matched" in tr.note or "304" in tr.note
          or "Not Modified" in tr.note)


# ---------------------------------------------------------------------------
# 3. news_8k 304 with upstream ETAG echoed → that ETag
# ---------------------------------------------------------------------------

def test_3_news_8k_304_with_upstream_etag():
    section("3. news_8k 304 with upstream ETag → that ETag (2)")
    captured = []
    tool = News8KTool(opener=make_news_opener(
        captured, status=304, body=b"", etag='W/"rotated-v5"'))
    tr = tool.search(ticker="AAPL", if_none_match='W/"prior-v4"')
    check("status=UNCHANGED", tr.status == "UNCHANGED")
    check("etag is upstream-echoed (W/\"rotated-v5\")",
          tr.etag == 'W/"rotated-v5"')


# ---------------------------------------------------------------------------
# 4. news_8k no if_none_match → no kwarg passed in opener call
# ---------------------------------------------------------------------------

def test_4_news_8k_no_inm():
    section("4. news_8k no INM when if_none_match=None (2)")
    captured = []
    body = make_aapl_efts_body()
    tool = News8KTool(opener=make_news_opener(
        captured, status=200, body=body, etag='W/"v1"'))
    tr = tool.search(ticker="AAPL")
    check("If-None-Match kwarg None when not provided",
          captured and captured[0]["if_none_match_sent"] is None)
    check("ToolResult SUCCESS (200 path)", tr.status == "SUCCESS")


# ---------------------------------------------------------------------------
# 5. sec_edgar_fulltext.search sends If-None-Match
# ---------------------------------------------------------------------------

def test_5_sec_edgar_sends_inm():
    section("5. sec_edgar_fulltext.search sends If-None-Match (4)")
    captured = []
    fake = make_sec_edgar_opener(captured, status=200,
                                  body=json.dumps({
                                      "hits": {"total": {"value": 1,
                                                          "relation": "eq"},
                                               "hits": [{
                                                   "_id": "x",
                                                   "_source": {"adsh": "X",
                                                               "forms": "8-K"}}]}}).encode("utf-8"),
                                  etag='W/"edgar-v2"')
    import urllib.request as _urllib_mod
    orig = _urllib_mod.urlopen
    _urllib_mod.urlopen = fake
    try:
        tool = SECEdgarFullTextTool()
        tr = tool.search(query="AI capex", if_none_match='W/"edgar-prior"')
        check("1 outgoing request", len(captured) == 1)
        headers = captured[0]["headers"]
        inm = headers.get("If-none-match") or headers.get("If-None-Match")
        check("If-None-Match header sent",
              inm == 'W/"edgar-prior"')
        check("status=SUCCESS (200)", tr.status == "SUCCESS")
        check("ToolResult.etag='W/\"edgar-v2\"'",
              tr.etag == 'W/"edgar-v2"')
    finally:
        _urllib_mod.urlopen = orig


# ---------------------------------------------------------------------------
# 6. sec_edgar 304 → UNCHANGED
# ---------------------------------------------------------------------------

def test_6_sec_edgar_304_unchanged():
    section("6. sec_edgar 304 → UNCHANGED (3)")
    captured = []
    fake = make_sec_edgar_opener(captured, status=200,
                                  raise_http_error=304,
                                  etag='W/"edgar-confirmed"')
    import urllib.request as _urllib_mod
    orig = _urllib_mod.urlopen
    _urllib_mod.urlopen = fake
    try:
        tool = SECEdgarFullTextTool()
        tr = tool.search(query="AI capex", if_none_match='W/"edgar-prior"')
        check("status=UNCHANGED", tr.status == "UNCHANGED")
        check("etag is upstream-echoed (W/\"edgar-confirmed\")",
              tr.etag == 'W/"edgar-confirmed"')
        check("note mentions 304", "304" in tr.note)
    finally:
        _urllib_mod.urlopen = orig


# ---------------------------------------------------------------------------
# 7. sec_edgar 304 no upstream ETag → falls back to sent ETag
# ---------------------------------------------------------------------------

def test_7_sec_edgar_304_no_upstream_etag():
    section("7. sec_edgar 304 no upstream ETag → fallback to sent (2)")
    captured = []
    fake = make_sec_edgar_opener(captured, status=200,
                                  raise_http_error=304, etag="")
    import urllib.request as _urllib_mod
    orig = _urllib_mod.urlopen
    _urllib_mod.urlopen = fake
    try:
        tool = SECEdgarFullTextTool()
        tr = tool.search(query="AI capex", if_none_match='W/"edgar-prior"')
        check("status=UNCHANGED", tr.status == "UNCHANGED")
        check("etag falls back to the sent etag (W/\"edgar-prior\")",
              tr.etag == 'W/"edgar-prior"')
    finally:
        _urllib_mod.urlopen = orig


# ---------------------------------------------------------------------------
# 8. transcripts.list_for_ticker sends If-None-Match
# ---------------------------------------------------------------------------

def test_8_transcripts_send_inm():
    section("8. transcripts.list_for_ticker sends If-None-Match (3)")
    captured = []

    def fake_opener(url, headers=None):
        captured.append({"url": url, "headers": dict(headers or {})})
        return 200, ('<html><body>no articles</body></html>'), 'W/"transcript-v1"'

    tool = TranscriptsTool(opener=fake_opener)
    tr = tool.list_for_ticker("AAPL", if_none_match='W/"transcript-prior"')
    check("1 outgoing request", len(captured) == 1)
    headers = captured[0]["headers"]
    check("If-None-Match header sent in headers dict",
          headers.get("If-None-Match") == 'W/"transcript-prior"')
    check("User-Agent header sent",
          "User-Agent" in headers)


# ---------------------------------------------------------------------------
# 9. transcripts 304 → UNCHANGED (the bug found by this pilot)
# ---------------------------------------------------------------------------

def test_9_transcripts_304_unchanged():
    section("9. transcripts 304 → UNCHANGED (was ValueError before fix) (3)")
    def fake_opener(url, headers=None):
        return 304, "", 'W/"transcript-confirmed"'

    tool = TranscriptsTool(opener=fake_opener)
    tr = tool.list_for_ticker("AAPL", if_none_match='W/"transcript-prior"')
    check("status=UNCHANGED", tr.status == "UNCHANGED")
    check("etag is upstream-echoed (W/\"transcript-confirmed\")",
          tr.etag == 'W/"transcript-confirmed"')
    check("note mentions ETag matched",
          "ETag matched" in tr.note or "304" in tr.note)


# ---------------------------------------------------------------------------
# 10. transcripts.fetch_transcript also fixed (3-tuple unpack)
# ---------------------------------------------------------------------------

def test_10_transcripts_fetch_transcript_3tuple():
    section("10. transcripts.fetch_transcript — 3-tuple unpack (was ValueError) (2)")
    def fake_opener(url, headers=None):
        return 200, ("<html><body>article body here</body></html>"), 'W/"art"'

    tool = TranscriptsTool(opener=fake_opener)
    tr = tool.fetch_transcript(article_id="12345")
    check("status=SUCCESS (no ValueError from 3-tuple unpack)",
          tr.status in ("SUCCESS", "PARTIAL", "EMPTY"))
    # fetch_transcript doesn't necessarily surface etag in note, so
    # just confirm the call worked.
    check("note does not contain 'network error'",
          "network error" not in (tr.note or ""))


# ---------------------------------------------------------------------------
# 11. call_tool injects if_none_match from sidecar
# ---------------------------------------------------------------------------

def test_11_call_tool_injects_from_sidecar():
    section("11. call_tool injects if_none_match from sidecar (3)")

    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="labourious-domain8-")
    os.environ["LABOURIOUS_RUNS_DIR_OVERRIDE"] = tmpdir
    try:
        from runtime import snippets as _sn
        from runtime.snippets import (
            write_snippet_for,
        )
        run_id = "testrun-d8"
        tr_initial = ToolResult(
            status="SUCCESS", data="ORIGINAL",
            as_of="2024-01-15T10:00:00Z", source="news_8k",
            etag='W/"prior-on-disk"', note="first-write",
        )
        sp = write_snippet_for(tr_initial, run_id, idx=0,
                               base_dir=tmpdir)
        check("sidecar file written", sp is not None)

        # Now: re-issue via call_tool. Patch the news_8k DEFAULT
        # opener so the real HTTP path runs with our captured header.
        captured = []
        import runtime.tools.news_8k as _m
        orig = _m._default_opener
        _m._default_opener = make_news_opener(
            captured, status=304, body=b"", etag="")
        try:
            # But — the constructor default still points to the OLD
            # module-level _default_opener because Python binds
            # default values at def-time. So we *also* need to pass
            # opener= explicitly via call_tool. call_tool builds
            # tool_class() with no constructor args, so the default
            # closure wins → captured will be empty unless we
            # monkey-patch _default_opener BEFORE News8KTool class
            # was imported. The cleanest way: patch the call_tool
            # path's call to News8KTool(...) so we control the
            # opener:
            from runtime import call_tool as ct
            orig_call_tool = ct.TOOL_REGISTRY["news_8k"].tool_class

            class _CustomN8K(News8KTool):
                def __init__(self, *args, **kwargs):
                    # Always use our capture-mode opener.
                    super().__init__(opener=_m._default_opener)

            # ToolBinding is frozen=True; bypass with object.__setattr__.
            object.__setattr__(ct.TOOL_REGISTRY["news_8k"],
                               "tool_class", _CustomN8K)
            try:
                from runtime.call_tool import call_tool
                tr_304 = call_tool(
                    "news_8k", requested_by_agent="domain8-test",
                    emit_event=None, method="search",
                    args={"ticker": "X", "limit": 5},
                    run_id=run_id, snippet_idx=0,
                )
                check("captured call surface (call_tool path)",
                      len(captured) >= 1)
                if captured:
                    check("If-None-Match kwarg sent on second call",
                          captured[0]["if_none_match_sent"]
                          == 'W/"prior-on-disk"')
                check("ToolResult.status=UNCHANGED (server returned 304)",
                      tr_304.status == "UNCHANGED")
            finally:
                object.__setattr__(ct.TOOL_REGISTRY["news_8k"],
                                   "tool_class", orig_call_tool)
        finally:
            _m._default_opener = orig
    finally:
        os.environ.pop("LABOURIOUS_RUNS_DIR_OVERRIDE", None)
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 12. call_tool: sidecar without cached_etag → no injection
# ---------------------------------------------------------------------------

def test_12_call_tool_no_injection_when_no_etag():
    section("12. call_tool: sidecar w/o cached_etag → no INM (2)")
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="labourious-dom8-noetag-")
    os.environ["LABOURIOUS_RUNS_DIR_OVERRIDE"] = tmpdir
    try:
        from runtime.snippets import write_snippet_for
        run_id = "testrun-noetag"
        tr_initial = ToolResult(
            status="SUCCESS", data="X", as_of="2024-01-15T10:00:00Z",
            source="news_8k", etag=None,  # no etag
            note="first-write-no-etag",
        )
        write_snippet_for(tr_initial, run_id, idx=0, base_dir=tmpdir)

        captured = []
        import runtime.tools.news_8k as _m
        orig = _m._default_opener
        _m._default_opener = make_news_opener(
            captured, status=200, body=b'{"hits":{"hits":[]}}',
            etag='W/"v1"')

        try:
            from runtime import call_tool as ct
            orig_call_tool = ct.TOOL_REGISTRY["news_8k"].tool_class

            class _CustomN8K(News8KTool):
                def __init__(self, *args, **kwargs):
                    super().__init__(opener=_m._default_opener)

            object.__setattr__(ct.TOOL_REGISTRY["news_8k"],
                               "tool_class", _CustomN8K)
            try:
                from runtime.call_tool import call_tool
                body = make_aapl_efts_body()
                # Update captured target → status=200 (no 304)
                _m._default_opener = make_news_opener(
                    captured, status=200, body=body, etag='W/"v1"')
                tr = call_tool(
                    "news_8k", requested_by_agent="d8test",
                    emit_event=None, method="search",
                    args={"ticker": "AAPL", "limit": 5},
                    run_id=run_id, snippet_idx=0,
                )
                check("If-None-Match is NOT set (no cached etag)",
                      captured and captured[0]["if_none_match_sent"] is None)
                check("ToolResult SUCCESS (200 path)",
                      tr.status == "SUCCESS")
            finally:
                object.__setattr__(ct.TOOL_REGISTRY["news_8k"],
                                   "tool_class", orig_call_tool)
        finally:
            _m._default_opener = orig
    finally:
        os.environ.pop("LABOURIOUS_RUNS_DIR_OVERRIDE", None)
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_1_news_8k_sends_inm,
        test_2_news_8k_304_no_upstream_etag,
        test_3_news_8k_304_with_upstream_etag,
        test_4_news_8k_no_inm,
        test_5_sec_edgar_sends_inm,
        test_6_sec_edgar_304_unchanged,
        test_7_sec_edgar_304_no_upstream_etag,
        test_8_transcripts_send_inm,
        test_9_transcripts_304_unchanged,
        test_10_transcripts_fetch_transcript_3tuple,
        test_11_call_tool_injects_from_sidecar,
        test_12_call_tool_no_injection_when_no_etag,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            FAIL += 1
            print(f"  EXC in {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== {OK}/{OK + FAIL} assertions passed ===")
    sys.exit(1 if FAIL > 0 else 0)
