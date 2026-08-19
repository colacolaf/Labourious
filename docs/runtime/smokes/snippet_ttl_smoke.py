"""
[domain-5] pilot — snippet cache TTL behavior.

Verifies:
  1. ``_resolve_ttl`` returns per-source TTL (news_8k=1h, sec_edgar_fulltext=24h,
     transcripts=7d, default=24h).
  2. ``SNIPPET_DEFAULT_TTL_S`` env override flips the default.
  3. ``SNIPPET_TTL_NEWS_8K_S`` env override flips one source.
  4. ``write_snippet_for`` writes a sidecar ``<path>.meta.json`` with
     ``written_at``, ``source``, ``bytes_written``, ``ttl_seconds``,
     ``truncated``.
  5. Second ``write_snippet_for`` within the TTL window returns
     ``SnippetPath(new_write=False)`` and the file is *unchanged*
     (verified via byte size + content hash).
  6. Second call **after** the TTL window returns ``new_write=True``
     and the file's ``written_at`` advances.
  7. ``force=True`` rewrites regardless of TTL.
  8. ``SnippetPath.is_stale`` returns True inside the gate logic when
     metadata's age >= ttl_seconds.
  9. ``SnippetPath.ttl_remaining_s`` is positive within window, 0 after.
 10. ``snippet_metadata_for`` parses sidecar correctly; corrupt JSON
     returns ``None``.
 11. ``SnippetMetadata.to_json()`` / ``from_json()`` round-trip.
 12. ``force_refresh(path, new_excerpt_text=...)`` replaces content
     and bumps ``written_at`` to current.
 13. ``call_tool(run_id=...)`` second call within window keeps file
     content unchanged but still attaches ``snippet_path`` to the
     (possibly new) ToolResult.
 14. Per-source TTL via env: news_8k TTL set to 5s forces the news snippet
     to refresh after 6s.

The pilot controls time strictly via the ``SNIPPET_NOW_OVERRIDE_S``
env var injected into ``_now_s()``. No real sleeping.
"""

from __future__ import annotations

import json
import os
import sys
import importlib.util
import pathlib
import shutil
import tempfile
from unittest.mock import patch
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Path setup
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

OK = 0; FAIL = 0
def step(label, cond):
    global OK, FAIL
    if cond:
        print(f"  ok    | {label}"); OK += 1
    else:
        print(f"  FAIL  | {label}"); FAIL += 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class FakeClock:
    """Minimal monotonic clock for testing. Sets SNIPPET_NOW_OVERRIDE_S
    on every read so ``_now_s()`` resolves to whatever we want."""
    def __init__(self, t0: float = 1000.0):
        self.t = t0
        os.environ["SNIPPET_NOW_OVERRIDE_S"] = str(self.t)
    def forward(self, dt: float) -> None:
        self.t += dt
        os.environ["SNIPPET_NOW_OVERRIDE_S"] = str(self.t)
    def set(self, t: float) -> None:
        self.t = t
        os.environ["SNIPPET_NOW_OVERRIDE_S"] = str(self.t)

def tr_for(source: str, payload: List[dict]) -> ToolResult:
    return ToolResult(
        status="SUCCESS",
        data=payload,
        as_of="2026-08-19T18:00:00Z",
        source=source,
        note=f"synthetic pilot for {source}",
    )


# ---------------------------------------------------------------------------
# 1. Per-source TTL defaults
# ---------------------------------------------------------------------------
print("=== 1. per-source TTL defaults ===")
# Clear all overrides for this section
for k in (
    "SNIPPET_DEFAULT_TTL_S",
    "SNIPPET_TTL_NEWS_8K_S", "SNIPPET_TTL_SEC_EDGAR_FULLTEXT_S",
    "SNIPPET_TTL_TRANSCRIPTS_S",
):
    os.environ.pop(k, None)
# Re-resolve (force _resolve_ttl to re-read env)
import importlib as _il
_il.reload(snip_mod)
snip_mod = sys.modules["runtime.snippets"]

step("default TTL = 86400 (24h)", snip_mod.DEFAULT_TTL_S == 86_400)
step("news_8k TTL = 3600 (1h)", snip_mod.SOURCE_TTL.get("news_8k") == 3_600)
step("sec_edgar_fulltext TTL = 86400 (24h)",
     snip_mod.SOURCE_TTL.get("sec_edgar_fulltext") == 86_400)
step("transcripts TTL = 604800 (7d)", snip_mod.SOURCE_TTL.get("transcripts") == 604_800)
step("_resolve_ttl('news_8k') = 3600", snip_mod._resolve_ttl("news_8k") == 3_600)
step("_resolve_ttl('sec_edgar_fulltext') = 86400",
     snip_mod._resolve_ttl("sec_edgar_fulltext") == 86_400)
step("_resolve_ttl('transcripts') = 604800",
     snip_mod._resolve_ttl("transcripts") == 604_800)
step("_resolve_ttl('unknown_source') = default (86400)",
     snip_mod._resolve_ttl("unknown_source_xyz") == snip_mod.DEFAULT_TTL_S)

# ---------------------------------------------------------------------------
# 2. Env overrides — global + per-source
# ---------------------------------------------------------------------------
print("\n=== 2. env overrides for TTL ===")
os.environ["SNIPPET_DEFAULT_TTL_S"] = "10"
_il.reload(snip_mod); snip_mod = sys.modules["runtime.snippets"]
step("SNIPPET_DEFAULT_TTL_S=10 → _resolve_ttl('unknown') = 10",
     snip_mod._resolve_ttl("anything") == 10)
step("per-source still hits SOURCE_TTL (news_8k=3600)",
     snip_mod._resolve_ttl("news_8k") == 3_600)
os.environ["SNIPPET_TTL_NEWS_8K_S"] = "5"
_il.reload(snip_mod); snip_mod = sys.modules["runtime.snippets"]
step("SNIPPET_TTL_NEWS_8K_S=5 → _resolve_ttl('news_8k') = 5",
     snip_mod._resolve_ttl("news_8k") == 5)
step("SNIPPET_TTL_NEWS_8K_S=5 leaves sec_edgar_fulltext at 86400",
     snip_mod._resolve_ttl("sec_edgar_fulltext") == 86_400)
os.environ["SNIPPET_TTL_SEC_EDGAR_FULLTEXT_S"] = "999"
_il.reload(snip_mod); snip_mod = sys.modules["runtime.snippets"]
step("SNIPPET_TTL_SEC_EDGAR_FULLTEXT_S=999 overrides source TTL",
     snip_mod._resolve_ttl("sec_edgar_fulltext") == 999)
# Cleanup overrides
for k in ("SNIPPET_DEFAULT_TTL_S", "SNIPPET_TTL_NEWS_8K_S",
          "SNIPPET_TTL_SEC_EDGAR_FULLTEXT_S"):
    os.environ.pop(k, None)
_il.reload(snip_mod); snip_mod = sys.modules["runtime.snippets"]

# ---------------------------------------------------------------------------
# 3. SnippetMetadata JSON round-trip
# ---------------------------------------------------------------------------
print("\n=== 3. SnippetMetadata JSON round-trip ===")
m1 = snip_mod.SnippetMetadata(
    written_at=12345.6, source="sec_edgar_fulltext",
    bytes_written=1024, ttl_seconds=86400, truncated=True,
)
m1_back = snip_mod.SnippetMetadata.from_json(m1.to_json())
step("round-trip equal-written_at", m1_back.written_at == m1.written_at)
step("round-trip equal-source", m1_back.source == m1.source)
step("round-trip equal-bytes_written", m1_back.bytes_written == m1.bytes_written)
step("round-trip equal-ttl_seconds", m1_back.ttl_seconds == m1.ttl_seconds)
step("round-trip equal-truncated", m1_back.truncated == m1.truncated)

# ---------------------------------------------------------------------------
# 4. write_snippet_for writes sidecar + returns SnippetPath with metadata
# ---------------------------------------------------------------------------
print("\n=== 4. write_snippet_for writes sidecar + metadata ===")
tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="ttl-pilot-"))
FakeClock()
tr_data = [{"adsh": "0000320193-26-000123", "form": "10-K",
            "company": "Apple Inc.", "ticker": "AAPL"}]
sp = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", tr_data),
    run_id="pilot-1", idx=0, base_dir=tmpdir,
)
step("SnippetPath returned", sp is not None)
step("content path exists", sp is not None and sp.path.exists())
meta_path = sp.path.with_suffix(sp.path.suffix + ".meta.json")
step("sidecar meta path exists", meta_path.exists())
step("metadata carried in SnippetPath", sp is not None and sp.metadata is not None)
step("metadata.written_at matches injected clock (1000.0)",
     sp is not None and sp.metadata.written_at == 1000.0)
step("metadata.ttl_seconds = 86400 (sec_edgar_fulltext default)",
     sp is not None and sp.metadata.ttl_seconds == 86_400)
step("metadata.source = 'sec_edgar_fulltext'",
     sp is not None and sp.metadata.source == "sec_edgar_fulltext")

# ---------------------------------------------------------------------------
# 5. Within-window write returns same content
# ---------------------------------------------------------------------------
print("\n=== 5. within-window write → cached snippet reused ===")
FakeClock()
sp1 = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", tr_data),
    run_id="pilot-1", idx=0, base_dir=tmpdir,
)
content_h1 = sp1.path.read_bytes()
meta_h1 = snip_mod.snippet_metadata_for(sp1.path)
clock = FakeClock(t0=1000.0)
clock.forward(60)  # 1 minute later — well within 24h
tr_data_altered = [{"adsh": "DIFFERENT", "form": "99-Z",
                    "company": "Different Inc.", "ticker": "ZZZ"}]
sp2 = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", tr_data_altered),
    run_id="pilot-1", idx=0, base_dir=tmpdir,
)
step("second call returned SnippetPath", sp2 is not None)
step("second call: new_write = False (cached under TTL)",
     sp2 is not None and sp2.new_write is False)
step("content on disk unchanged (byte-equal)",
     sp2 is not None and sp2.path.read_bytes() == content_h1)
step("written_at in meta unchanged from first write",
     sp2 is not None and sp2.metadata.written_at == meta_h1.written_at)
step("is_stale is False on the cached result",
     sp2 is not None and not sp2.is_stale)

# ---------------------------------------------------------------------------
# 6. After-TTL write rewrites with new content
# ---------------------------------------------------------------------------
print("\n=== 6. after-TTL write → cache refreshed ===")
clock.set(1000.0)
sp3_a = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", tr_data),
    run_id="pilot-2", idx=0, base_dir=tmpdir,
)
written_at_v1 = sp3_a.metadata.written_at
content_v1 = sp3_a.path.read_bytes()
# Forward past the 24h TTL
clock.forward(86_401 + 30)  # 24h + 30s
tr_data_v2 = [{"adsh": "0000320193-26-999999", "form": "10-Q",
               "company": "Apple Inc.", "ticker": "AAPL"}]
sp3_b = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", tr_data_v2),
    run_id="pilot-2", idx=0, base_dir=tmpdir,
)
step("after-TTL call returned SnippetPath", sp3_b is not None)
step("after-TTL: new_write = True", sp3_b is not None and sp3_b.new_write is True)
step("after-TTL: content bytes differ from v1",
     sp3_b is not None and sp3_b.path.read_bytes() != content_v1)
step("after-TTL: written_at advanced",
     sp3_b is not None and sp3_b.metadata.written_at > written_at_v1)
step("after-TTL: new content's adsh present",
     sp3_b is not None and "0000320193-26-999999" in sp3_b.path.read_text("utf-8"))
step("is_stale is True on the previous result (would have been)",
     sp3_a is not None and sp3_a.is_stale is True
     if clock.t > written_at_v1 + 86_401
     else False)  # reflect runtime check
# Actually the metadata.is_stale check uses _now_s() — which follows clock.
step("SnippetPath.is_stale returns True AFTER TTL elapses",
     sp3_a is not None and sp3_a.is_stale)

# ---------------------------------------------------------------------------
# 7. force=True rewrites inside window
# ---------------------------------------------------------------------------
print("\n=== 7. force=True rewrites inside the TTL window ===")
clock.set(2000.0)
tr_data_f1 = [{"adsh": "FORCE-1", "company": "Force Inc."}]
tr_data_f2 = [{"adsh": "FORCE-2", "company": "Force2 Inc."}]
spf1 = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", tr_data_f1),
    run_id="pilot-3", idx=0, base_dir=tmpdir,
)
content_f1 = spf1.path.read_bytes()
clock.forward(60)  # well within 24h
spf2 = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", tr_data_f2),
    run_id="pilot-3", idx=0, base_dir=tmpdir, force=True,
)
step("force=True returns SnippetPath", spf2 is not None)
step("force=True: new_write = True (overrode TTL)",
     spf2 is not None and spf2.new_write is True)
step("force=True: content changed to second payload",
     spf2 is not None and "FORCE-2" in spf2.path.read_text("utf-8"))

# ---------------------------------------------------------------------------
# 8. ttl_remaining_s positive / zero
# ---------------------------------------------------------------------------
print("\n=== 8. ttl_remaining_s hygiene ===")
clock.set(5000.0)
sp_t1 = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", [{"a": 1}]),
    run_id="pilot-4", idx=0, base_dir=tmpdir,
)
clock.forward(3600)  # 1h in
ttl_left = sp_t1.ttl_remaining_s()
step("ttl_remaining_s = 86400 - 3600 ≈ 82_800 (within window)",
     82_799 <= ttl_left <= 82_801)
step("ttl_remaining_s is positive", ttl_left > 0)
clock.forward(86_400)  # now 24h+ past written_at
ttl_left_after = sp_t1.ttl_remaining_s()
step("ttl_remaining_s = 0 after TTL", ttl_left_after == 0)

# ---------------------------------------------------------------------------
# 9. snippet_for carries metadata → is_stale usable
# ---------------------------------------------------------------------------
print("\n=== 9. snippet_for read-only carries metadata ===")
clock.set(6000.0)
sp_r1 = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", [{"x": 1}]),
    run_id="pilot-5", idx=0, base_dir=tmpdir,
)
clock.forward(60)
tr_alt = tr_for("sec_edgar_fulltext", [{"should_not_appear": True}])
sp_r2 = snip_mod.snippet_for(tr_alt, "pilot-5", 0, base_dir=tmpdir)
step("snippet_for returns SnippetPath (cached)", sp_r2 is not None)
step("snippet_for carries metadata from sidecar",
     sp_r2 is not None and sp_r2.metadata is not None)
step("snippet_for: is_stale is False within window",
     sp_r2 is not None and sp_r2.is_stale is False)
step("snippet_for: content unchanged on disk (cache reused)",
     sp_r2 is not None and "x" in sp_r2.path.read_text("utf-8")
     and "should_not_appear" not in sp_r2.path.read_text("utf-8"))

# ---------------------------------------------------------------------------
# 10. Per-source TTL via env override
# ---------------------------------------------------------------------------
print("\n=== 10. per-source TTL via env override ===")
os.environ["SNIPPET_TTL_NEWS_8K_S"] = "5"
_il.reload(snip_mod); snip_mod = sys.modules["runtime.snippets"]
clock.set(7000.0)
sp_news1 = snip_mod.write_snippet_for(
    tr_for("news_8k", [{"adsh": "NEWS-1", "headline": "earnings beat"}]),
    run_id="pilot-6", idx=0, base_dir=tmpdir,
)
step("news_8k with override TTL=5s: writes new", sp_news1 is not None
     and sp_news1.metadata.ttl_seconds == 5)
clock.forward(6)  # past 5s TTL
sp_news2 = snip_mod.write_snippet_for(
    tr_for("news_8k", [{"adsh": "NEWS-2", "headline": "guidance cut"}]),
    run_id="pilot-6", idx=0, base_dir=tmpdir,
)
step("after-TTL news_8k: new_write=True", sp_news2 is not None
     and sp_news2.new_write is True)
step("news content refreshed to v2",
     sp_news2 is not None and "NEWS-2" in sp_news2.path.read_text("utf-8"))
os.environ.pop("SNIPPET_TTL_NEWS_8K_S", None)
_il.reload(snip_mod); snip_mod = sys.modules["runtime.snippets"]

# ---------------------------------------------------------------------------
# 11. force_refresh(path, new_excerpt_text=...) replaces content + meta
# ---------------------------------------------------------------------------
print("\n=== 11. force_refresh replaces content + bumps written_at ===")
clock.set(8000.0)
sp_ref = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", [{"original": True}]),
    run_id="pilot-7", idx=0, base_dir=tmpdir,
)
content_ref_before = sp_ref.path.read_bytes()
clock.forward(30)  # inside 24h window
sp_after = snip_mod.force_refresh(
    sp_ref.path, new_excerpt_text="manually corrected\n",
    base_dir=tmpdir,
)
step("force_refresh returned SnippetPath",
     sp_after is not None)
step("force_refresh: new_write = True", sp_after.new_write is True)
step("force_refresh: content replaced",
     sp_after.path.read_text("utf-8") == "manually corrected\n")
step("force_refresh: written_at advanced",
     sp_after.metadata.written_at > sp_ref.metadata.written_at)
step("force_refresh: bytes_written reflects new length",
     sp_after.bytes_written == len("manually corrected\n".encode("utf-8")))

# ---------------------------------------------------------------------------
# 12. call_tool(run_id=...) — second call within window keeps content
# ---------------------------------------------------------------------------
print("\n=== 12. call_tool(run_id=...) respects TTL across re-runs ===")
os.environ["LABOURIOUS_RUNS_DIR_OVERRIDE"] = str(tmpdir)
from runtime.tools import sec_edgar_fulltext as sec_mod
fake_data_v1 = [{"adsh": "RT-1", "company": "TLM Inc."}]
fake_data_v2 = [{"adsh": "RT-2", "company": "TLM Inc."}]
rt_calls = []  # FIFO list
def fake_search_rt(self, *args, **kwargs):
    payload = rt_calls.pop(0) if rt_calls else fake_data_v1
    return tr_for("sec_edgar_fulltext", payload)
real_search = sec_mod.SECEdgarFullTextTool.search
clock.set(9000.0)
from runtime.call_tool import call_tool as real_call_tool
try:
    sec_mod.SECEdgarFullTextTool.search = fake_search_rt
    rt_calls.append(fake_data_v1)  # first call returns v1
    out_a = real_call_tool(
        tool_id="sec_edgar_fulltext", requested_by_agent="pilot",
        emit_event=None, args={"query": "X", "limit": 5},
        run_id="pilot-rt", snippet_idx=0,
    )
    c1 = pathlib.Path(out_a.snippet_path).read_text("utf-8")
    c1_meta_path = pathlib.Path(out_a.snippet_path).with_suffix(
        pathlib.Path(out_a.snippet_path).suffix + ".meta.json"
    )
    c1_written_at = json.loads(c1_meta_path.read_text("utf-8"))["written_at"]
    clock.forward(60)  # within window
    out_b = real_call_tool(
        tool_id="sec_edgar_fulltext", requested_by_agent="pilot",
        emit_event=None, args={"query": "X", "limit": 5},
        run_id="pilot-rt", snippet_idx=0,
    )
    c2 = pathlib.Path(out_b.snippet_path).read_text("utf-8")
    step("call_tool first call: snippet_path set",
         out_a.snippet_path is not None and "RT-1" in c1)
    step("call_tool second call within window: snippet_path still set",
         out_b.snippet_path is not None)
    step("call_tool second call within window: content NOT refreshed (URL RT-1 stays)",
         out_b.snippet_path == out_a.snippet_path and "RT-1" in c2)
finally:
    sec_mod.SECEdgarFullTextTool.search = real_search

# Now after-TTL call_tool re-runs the connector and refreshes snippet
clock.set(c1_written_at + 86_401 + 100)
try:
    sec_mod.SECEdgarFullTextTool.search = fake_search_rt
    rt_calls.append(fake_data_v2)  # after-TTL: forces refresh → v2 wins
    out_c = real_call_tool(
        tool_id="sec_edgar_fulltext", requested_by_agent="pilot",
        emit_event=None, args={"query": "X", "limit": 5},
        run_id="pilot-rt", snippet_idx=0,
    )
    c3 = pathlib.Path(out_c.snippet_path).read_text("utf-8")
    step("after-TTL call_tool: same run_id → same snippet path",
         out_c.snippet_path == out_a.snippet_path)
    step("after-TTL call_tool: content refreshed to v2 (RT-2 present)",
         "RT-2" in c3)
finally:
    sec_mod.SECEdgarFullTextTool.search = real_search

# ---------------------------------------------------------------------------
# 13. snippet_metadata_for parses corrupt JSON → None
# ---------------------------------------------------------------------------
print("\n=== 13. snippet_metadata_for handles corrupt sidecar ===")
sp_corrupt = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", [{"x": 1}]),
    run_id="pilot-corrupt", idx=0, base_dir=tmpdir,
)
# Sabotage the sidecar
meta_p = sp_corrupt.path.with_suffix(sp_corrupt.path.suffix + ".meta.json")
meta_p.write_text("{not valid json at all", encoding="utf-8")
result = snip_mod.snippet_metadata_for(sp_corrupt.path)
step("corrupt sidecar → snippet_metadata_for returns None", result is None)
# And write_snippet_for falls through to a fresh write under those conditions
sp_recover = snip_mod.write_snippet_for(
    tr_for("sec_edgar_fulltext", [{"x": 2}]),
    run_id="pilot-corrupt", idx=0, base_dir=tmpdir,
)
step("corrupt meta → next write treats it as no-cache, returns new_write=True",
     sp_recover.new_write is True)

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
os.environ.pop("LABOURIOUS_RUNS_DIR_OVERRIDE", None)
os.environ.pop("SNIPPET_NOW_OVERRIDE_S", None)
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n=== pilot complete: {OK} ok / {FAIL} fail ===")
sys.exit(0 if FAIL == 0 else 1)
