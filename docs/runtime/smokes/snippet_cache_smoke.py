"""
[domain-4] pilot — snippet cache + chip `v` action + pager dispatch.

Verifies the full path:

  1. ``docs/runtime/snippets.write_snippet_for(tr, run_id, idx)`` writes
     the first 2 KB of ``ToolResult.data`` to disk under
     ``<RUNS_DIR>/<run_id>/snippets/<safe_source>_<idx>.txt`` and
     returns a SnippetPath with the on-disk path.

  2. The 2 KB cap is enforced when the data exceeds it; a tail
     ``\\n[truncated @ 2048 bytes]`` marker makes the cut visible in
     ``less``.

  3. Skips writing for FAILED / EMPTY / None results.

  4. Idempotent: a second call returns the same path with
     ``new_write=False`` (the file is *not* rewritten).

  5. ``ToolResult.to_dict()`` includes ``snippet_path`` (newly added).

  6. ``call_tool(..., run_id=...)`` invokes the snippet writer when
     the tool_id is in the snippet-cacheable set (sec_edgar_fulltext,
     news_8k, transcripts) and the result is SUCCESS.

  7. ``CitationChip.request_view()`` posts an ActionRequested with
     action='snippet' and url=snippet_paths[_current_idx].

  8. ChatScreen.on_citation_chip_action_requested routes ``snippet``
     to ``frontend.utils.platform.open_in_pager`` (mocked so the
     pager never actually launches).

  9. ``open_in_pager`` selects ``less`` (preferred) → ``bat`` →
     ``more`` → ``cat`` chain in order; returns the on-path pagers'
     name + path on success.

10. The chip itself shows a `` ◫`` snippet-badge in its label when
    any snippet is available, and a per-citation badge when the
    *current_idx*'s snippet is set.
"""

from __future__ import annotations

import json
import sys
import importlib.util
import pathlib
from unittest.mock import patch, MagicMock
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Path setup — same trick as runtime/__init__.py
# ---------------------------------------------------------------------------
sys.path.insert(0, "docs")
_pkg_rt = pathlib.Path("docs/runtime/__init__.py")
if _pkg_rt.exists():
    _spec = importlib.util.spec_from_file_location("runtime", _pkg_rt)
    _m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
    sys.modules["runtime"] = _m
_pkg_fe = pathlib.Path("docs/frontend/__init__.py")
if _pkg_fe.exists():
    _spec = importlib.util.spec_from_file_location("frontend", _pkg_fe)
    _m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
    sys.modules["frontend"] = _m

import runtime.snippets as snip_mod           # type: ignore
from runtime.tools import ToolResult           # type: ignore
import frontend.widgets.citation_chip as chip_mod   # type: ignore
import frontend.utils.platform as plat_mod    # type: ignore

OK = 0; FAIL = 0
def step(label, cond):
    global OK, FAIL
    if cond:
        print(f"  ok    | {label}"); OK += 1
    else:
        print(f"  FAIL  | {label}"); FAIL += 1


# ---------------------------------------------------------------------------
# 1. write_snippet_for writes file + SnippetPath
# ---------------------------------------------------------------------------
print("=== 1. write_snippet_for writes file + SnippetPath ===")
import tempfile, os
tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="snip-pilot-"))
tr_success = ToolResult(
    status="SUCCESS",
    data=[{"adsh": "0000320193-26-000123", "form": "10-K",
           "filing_date": "2026-01-15", "company": "Apple Inc.",
           "cik": "0000320193", "ticker": "AAPL"},
          {"adsh": "0000320193-26-000124", "form": "10-Q",
           "filing_date": "2026-04-15", "company": "Apple Inc.",
           "cik": "0000320193", "ticker": "AAPL"}],
    as_of="2026-08-19T18:00:00Z",
    source="sec_edgar_fulltext",
    note="EFTS: 2 of 200 hits for 'AAPL'.",
)
sp = snip_mod.write_snippet_for(tr_success, run_id="pilot-1", idx=0,
                                base_dir=tmpdir)
step("SnippetPath returned (not None)", sp is not None)
step("path is <tmpdir>/pilot-1/snippets/<safe>_0.txt",
     sp is not None and "pilot-1" in str(sp.path) and "snippets" in str(sp.path)
     and str(sp.path).endswith("_0.txt"))
step("file actually exists on disk",
     sp is not None and sp.path.exists())
step("new_write flag is True on first call",
     sp is not None and sp.new_write is True)
step("snippet content has at least one row's field key",
     sp is not None and "adsh=" in sp.path.read_text(encoding="utf-8"))
step("snippet has the [truncated] marker absent (data < 2 KB)",
     sp is not None and "[truncated" not in sp.path.read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# 2. 2 KB cap enforced on big data
# ---------------------------------------------------------------------------
print("\n=== 2. 2 KB cap enforced on big data ===")
big_payload = [{"adsh": f"0000320193-26-{i:06d}", "form": "10-K",
                "filing_date": "2026-01-15", "summary": "x" * 200,
                "company": "Apple Inc.", "cik": "0000320193",
                "ticker": "AAPL"} for i in range(50)]
big_tr = ToolResult(
    status="SUCCESS", data=big_payload,
    as_of="2026-08-19T18:00:00Z", source="news_8k",
    note=f"synthetic {len(big_payload)} rows",
)
sp2 = snip_mod.write_snippet_for(big_tr, run_id="pilot-1", idx=1,
                                 base_dir=tmpdir)
step("file written for big payload",
     sp2 is not None and sp2.path.exists())
step("file size <= MAX_SNIPPET_BYTES",
     sp2 is not None and sp2.bytes_written <= snip_mod.MAX_SNIPPET_BYTES)
step("truncated flag is True on big payload",
     sp2 is not None and sp2.truncated is True)
content = sp2.path.read_text(encoding="utf-8")
step("[truncated @ 2048 bytes] marker is in the file",
     "[truncated @ 2048 bytes]" in content)

# ---------------------------------------------------------------------------
# 3. FAILED / EMPTY / None results skip writes
# ---------------------------------------------------------------------------
print("\n=== 3. FAILED / EMPTY / None results skip writes ===")
failed_tr = ToolResult(status="FAILED", data=None,
                       as_of="2026-08-19T18:00:00Z",
                       source="sec_edgar_fulltext",
                       note="network error")
empty_tr = ToolResult(status="EMPTY", data=[],
                      as_of="2026-08-19T18:00:00Z",
                      source="sec_edgar_fulltext",
                      note="0 hits")
sp3a = snip_mod.write_snippet_for(failed_tr, run_id="pilot-1", idx=2,
                                  base_dir=tmpdir)
sp3b = snip_mod.write_snippet_for(empty_tr, run_id="pilot-1", idx=2,
                                  base_dir=tmpdir)
sp3c = snip_mod.write_snippet_for(None, run_id="pilot-1", idx=2,
                                  base_dir=tmpdir)
step("FAILED → None", sp3a is None)
step("EMPTY → None", sp3b is None)
step("None tool_result → None", sp3c is None)
# Snippet for *read* on a non-existent file → None
sp3d = snip_mod.snippet_for(failed_tr, run_id="pilot-1", idx=2,
                            base_dir=tmpdir)
step("snippet_for on FAILED → None (read-only)", sp3d is None)

# ---------------------------------------------------------------------------
# 4. Idempotency — second call doesn't rewrite
# ---------------------------------------------------------------------------
print("\n=== 4. Idempotency: second call returns same path without rewriting ===")
sp4a = snip_mod.write_snippet_for(tr_success, run_id="pilot-1", idx=0,
                                  base_dir=tmpdir)
step("second call returns SnippetPath", sp4a is not None)
step("second call: new_write is False", sp4a is not None and sp4a.new_write is False)
step("second call: same path", sp4a is not None and str(sp4a.path) == str(sp.path))
# Even with completely different data, no rewrite unless force=True.
# NB: same as_of as v1 to keep TTL+asof gate both satisfied — this test
# is about idempotency for *the same* upstream publication, not for
# later revisions; asof-driven refresh is tested in snippet_asof_smoke.
new_tr = ToolResult(status="SUCCESS", data=["totally different"],
                   as_of="2026-08-19T18:00:00Z",
                   source="sec_edgar_fulltext",
                   note="would-be-different")
sp4b = snip_mod.write_snippet_for(new_tr, run_id="pilot-1", idx=0,
                                  base_dir=tmpdir)
step("force=False ignores new data", sp4b is not None
     and "adsh=" in sp4b.path.read_text(encoding="utf-8"))
sp4c = snip_mod.write_snippet_for(new_tr, run_id="pilot-1", idx=0,
                                  base_dir=tmpdir, force=True)
step("force=True rewrites with new data", sp4c is not None
     and "totally different" in sp4c.path.read_text(encoding="utf-8")
     and sp4c.new_write is True)

# ---------------------------------------------------------------------------
# 5. ToolResult.to_dict includes snippet_path
# ---------------------------------------------------------------------------
print("\n=== 5. ToolResult.to_dict includes snippet_path ===")
tr_with_snip = ToolResult(
    status="SUCCESS", data=[{"a": 1}],
    as_of="2026-08-19T18:00:00Z",
    source="sec_edgar_fulltext",
    note="x",
    snippet_path="/tmp/some/path/snippet_0.txt",
)
d = tr_with_snip.to_dict()
step("to_dict() has 'snippet_path' key", "snippet_path" in d)
step("snippet_path value preserved", d["snippet_path"] == "/tmp/some/path/snippet_0.txt")
tr_no_snip = ToolResult(status="SUCCESS", data=[{"a": 1}],
                       as_of="2026-08-19T18:00:00Z",
                       source="sec_edgar_fulltext", note="x")
step("default snippet_path is None", tr_no_snip.snippet_path is None)
step("to_dict() default snippet_path → None",
     tr_no_snip.to_dict()["snippet_path"] is None)

# ---------------------------------------------------------------------------
# 6. call_tool with run_id sets snippet_path on SUCCESS
# ---------------------------------------------------------------------------
print("\n=== 6. call_tool(run_id=...) sets snippet_path for text-heavy tools ===")
from runtime.call_tool import call_tool as real_call_tool
# We can't easily simulate the network for sec_edgar_fulltext here
# (SSL would fail in pilot), but we can monkey-patch the connector's
# ``search`` method to return a synthetic SUCCESS and assert the
# snippet_writer side-effect fires.
from runtime.tools import sec_edgar_fulltext as sec_mod
real_search = sec_mod.SECEdgarFullTextTool.search
def fake_search(self, *args, **kwargs):
    return ToolResult(
        status="SUCCESS",
        data=[{"adsh": "0000320193-26-000123", "form": "10-K",
               "filing_date": "2026-01-15", "company": "Apple Inc.",
               "cik": "0000320193", "ticker": "AAPL"}],
        as_of="2026-08-19T18:00:00Z",
        source="sec_edgar_fulltext",
        note="synthetic pilot",
    )
os.environ["LABOURIOUS_RUNS_DIR_OVERRIDE"] = str(tmpdir)
try:
    sec_mod.SECEdgarFullTextTool.search = fake_search
    out = real_call_tool(
        tool_id="sec_edgar_fulltext",
        requested_by_agent="pilot",
        emit_event=None,
        args={"query": "AAPL", "limit": 5},
        run_id="pilot-e2e",
        snippet_idx=0,
    )
    step("call_tool returns SUCCESS", out.status == "SUCCESS")
    step("snippet_path set on the ToolResult",
         out.snippet_path is not None and "pilot-e2e" in out.snippet_path)
    step("snippet file exists on disk",
         out.snippet_path is not None and pathlib.Path(out.snippet_path).exists())
finally:
    sec_mod.SECEdgarFullTextTool.search = real_search

# And confirm a tool *not* in the snippet-cacheable set does NOT get snippet_path
from runtime.tools import market_data as md_mod
real_history = md_mod.MarketDataTool.price_history
def fake_history(self, *args, **kwargs):
    return ToolResult(
        status="SUCCESS", data=[{"date": "2026-08-19", "Close": 100.0}],
        as_of="2026-08-19T18:00:00Z", source="market_data", note="pilot",
    )
try:
    md_mod.MarketDataTool.price_history = fake_history
    out2 = real_call_tool(
        tool_id="market_data",
        requested_by_agent="pilot",
        emit_event=None,
        args={"ticker": "TEST", "period": "5d", "interval": "1d"},
        run_id="pilot-e2e",
        snippet_idx=0,
    )
    step("non-cacheable tool (market_data): status SUCCESS", out2.status == "SUCCESS")
    step("non-cacheable tool: snippet_path stays None",
         out2.snippet_path is None)
finally:
    md_mod.MarketDataTool.price_history = real_history

# ---------------------------------------------------------------------------
# 7. CitationChip.request_view posts ActionRequested with action='snippet'
# ---------------------------------------------------------------------------
print("\n=== 7. CitationChip.request_view posts snippet ActionRequested ===")
def make_chip(citations, snippet_paths=None):
    chip_id = f"test-chip-{len(citations)}"
    chip = chip_mod.CitationChip(citations=citations,
                                 snippet_paths=snippet_paths, id=chip_id)
    posted: list = []
    chip.post_message = lambda m: posted.append(m)               # type: ignore
    chip._posted_for_test = posted                                # type: ignore[attr-defined]
    return chip

chip7 = make_chip(
    ["https://www.sec.gov/1", "https://www.reuters.com/2"],
    ["/run/sec_edgar_fulltext_0.txt", None],
)
posted = chip7._posted_for_test
ret = chip7.request_view()
step("request_view returns the first snippet path",
     ret == "/run/sec_edgar_fulltext_0.txt")
step("1 action posted", len(posted) == 1)
m = posted[0]
step("message type is ActionRequested", isinstance(m, chip_mod.CitationChip.ActionRequested))
step("action == 'snippet'", m.action == "snippet")
step("url == the snippet path", m.url == "/run/sec_edgar_fulltext_0.txt")
step("idx == 0", m.idx == 0)

# Advance to idx=1 (no snippet) → posts empty-url marker
chip7._current_idx = 1
posted.clear()
ret2 = chip7.request_view()
step("idx=1 with no snippet: returns ''", ret2 == "")
step("empty action posted", len(posted) == 1 and posted[0].action == "snippet"
     and posted[0].url == "")

# Advance via `n` then `v` to test round-trip
chip7._current_idx = 0
posted.clear()
ev = MagicMock(key="v")
chip7.on_key(ev)
step("`v` dispatches request_view (idx=0)",
     len(posted) == 1 and posted[0].action == "snippet"
     and posted[0].url == "/run/sec_edgar_fulltext_0.txt")

chip7._current_idx = 1
posted.clear()
chip7.on_key(ev)
step("`v` on idx=1 posts empty-url", len(posted) == 1
     and posted[0].action == "snippet" and posted[0].url == "")

# ---------------------------------------------------------------------------
# 8. ChatScreen routing — snippet → open_in_pager
# ---------------------------------------------------------------------------
print("\n=== 8. ChatScreen routing: snippet-action → open_in_pager ===")
import frontend.screens.chat as chat_mod

# Stub ChatScreen to capture handler invocations.
class StubChat:
    on_citation_chip_action_requested = chat_mod.ChatScreen.on_citation_chip_action_requested
    _set_status_flash = chat_mod.ChatScreen._set_status_flash
    _set_banner_warning = chat_mod.ChatScreen._set_banner_warning
    _set_banner_ok = chat_mod.ChatScreen._set_banner_ok
    def query_one(self, *_a, **_kw): raise AssertionError("unused here")

class StubChatFlash(StubChat):
    def __init__(self):
        self.flash_log: List[Tuple[str, str]] = []
    def _set_status_flash(self, msg, *, ok=False, warn=False, duration_s=0.0):
        self.flash_log.append((msg, "ok" if ok else ("warn" if warn else "info")))

stub = StubChatFlash()

pager_calls: List[List[str]] = []
def fake_open_in_pager(path):
    pager_calls.append([path])
    return (True, f"less {path}")

snippet_msg_ok = chip_mod.CitationChip.ActionRequested(
    chip_id="ignored", action="snippet",
    url="/run/pilot/sec_edgar_fulltext_0.txt", idx=0,
)
snippet_msg_empty = chip_mod.CitationChip.ActionRequested(
    chip_id="ignored", action="snippet", url="", idx=-1,
)

with patch.object(plat_mod, "open_in_pager", side_effect=fake_open_in_pager):
    stub.on_citation_chip_action_requested(snippet_msg_ok)
    step("open_in_pager called once with the snippet path",
         len(pager_calls) == 1 and pager_calls[0][0] == "/run/pilot/sec_edgar_fulltext_0.txt")
    step("flash gets a success line 'pager:'",
         any(("pager:" in m or "✓" in m) and tag == "ok"
             for m, tag in stub.flash_log))
    pager_calls.clear(); stub.flash_log.clear()

    stub.on_citation_chip_action_requested(snippet_msg_empty)
    step("empty snippet: open_in_pager NOT called", len(pager_calls) == 0)
    step("empty snippet: flash gets a warn-style hint",
         any(("`o`" in m or "no cached" in m) and tag == "warn"
             for m, tag in stub.flash_log))

# ---------------------------------------------------------------------------
# 9. open_in_pager chain — current machine likely has `less` or `cat`
# ---------------------------------------------------------------------------
print("\n=== 9. open_in_pager: chain tries less → bat → more → cat ===")
# Build a real temporary file so open_in_pager has something to read.
real_tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
real_tmp.write("hello snippet\npage 1\n")
real_tmp.close()
real_tmp_path = real_tmp.name

# Force the chain by monkey-patching shutil.which to expose only one
# pager per call. Patch subprocess.Popen so we record but don't actually
# launch the pager.
class _PopenRecorder:
    calls: List[List[str]] = []
    def __call__(self, cmd, *args, **kwargs):
        type(self).calls.append(cmd)
        return MagicMock()

# Test 9a — only less exposed
import shutil as _shutil
real_which = _shutil.which
def which_only_less(name):
    return "/usr/bin/less" if name == "less" else None
real_popen = plat_mod.subprocess.Popen
plat_mod.subprocess.Popen = _PopenRecorder()
try:
    _shutil.which = which_only_less
    ok, msg = plat_mod.open_in_pager(real_tmp_path)
    step("only-less chain: returns ok=True", ok is True)
    step("only-less chain: msg identifies 'less'",
         "less" in msg and real_tmp_path in msg)
    step("only-less chain: subprocess.Popen called with ['less', path]",
         len(_PopenRecorder.calls) == 1
         and _PopenRecorder.calls[0][0] == "less"
         and _PopenRecorder.calls[0][1] == real_tmp_path)
finally:
    _shutil.which = real_which
    plat_mod.subprocess.Popen = real_popen
    _PopenRecorder.calls = []

# Test 9b — empty path fails clearly
ok, msg = plat_mod.open_in_pager("")
step("empty path: ok=False", ok is False)
step("empty path: msg mentions empty", "empty" in msg)

# Test 9c — nonexistent file fails clearly
ok, msg = plat_mod.open_in_pager("/nope/does/not/exist.txt")
step("nonexistent file: ok=False", ok is False)
step("nonexistent file: msg mentions not-found",
     "not found" in msg or "does not exist" in msg)

# ---------------------------------------------------------------------------
# 10. chip label carries snippet badges
# ---------------------------------------------------------------------------
print("\n=== 10. Chip label shows snippet badges ===")
chip10 = make_chip(
    ["https://www.sec.gov/1", "https://www.reuters.com/2"],
    ["/run/sec_0.txt", None],
)
label_default = chip10._label()
step("multi-citation chip with mixed snippets: shows ◫ in default label",
     "◫" in label_default)
step("indexed form shows host of idx=0 (sec.gov)",
     "sec.gov" in label_default)

chip10.on_key(MagicMock(key="n"))
label_after_n = chip10._label()
step("after `n`: chip is on idx=1 (no-snippet) — no per-idx badge",
     "◫" not in label_after_n and "reuters.com" in label_after_n)

chip10.on_key(MagicMock(key="n"))
label_after_w = chip10._label()
step("after wrap (idx=0): per-idx badge appears ◫",
     "◫" in label_after_w and "sec.gov" in label_after_w)

# Chip with ALL baselines (no snippets) — no badge
chip10b = make_chip(["u1", "u2"], [None, None])
step("chip with no snippets anywhere: never shows ◫",
     "◫" not in chip10b._label())

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
import shutil as _shutil2
_shutil2.rmtree(tmpdir, ignore_errors=True)
try:
    os.unlink(real_tmp_path)
except Exception:
    pass

print(f"\n=== pilot complete: {OK} ok / {FAIL} fail ===")
sys.exit(0 if FAIL == 0 else 1)
