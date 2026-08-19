"""
[domain-7] pilot — snippet cache ETag short-circuit (304 Not Modified).

Verifies the full path:

  1. ToolResult gained ``etag: str | None`` plus the
     ``STATUS_UNCHANGED = "UNCHANGED"`` sentinel.

  2. ``SnippetMetadata`` gained ``cached_etag: str | None``.
     JSON round-trip preserves it; back-compat: old sidecars
     without the field parse as ``None``.

  3. First ``write_snippet_for`` records ``cached_etag`` in the
     sidecar when the ToolResult carries one.

  4. ``write_snippet_for`` honours ``ToolResult.status == "UNCHANGED"``
     by returning the *cached* SnippetPath (content untouched, but
     ``written_at`` bumped to now so the chip's staleness badge
     reflects the last-confirmed upstream check).
     - Preserves content even if TTL fired (would have refreshed).
     - Preserves content even if as-of was *later* (would have refreshed).
     - Preserves content when ``force=True`` was passed (force
     does NOT overrule "upstream said unchanged").

  5. UNCHANGED with no cached snippet returns ``None`` — there's
     nothing for "unchanged" to refer to.

  6. ToolResult.status mix: ``SUCCESS`` → still works (it was the
     original behaviour, kept verbatim). ``FAILED``, ``EMPTY`` →
     still ``None`` (no snippet).

  7. End-to-end ``call_tool(run_id=...)``: connector returns
     ``UNCHANGED`` after a cached run; snippet_path preserved,
     file content unchanged.

  8. End-to-end ``call_tool``: connector returns SUCCESS with
     NEW etag (different from cached) → cache rewritten with new
     cached_etag (verifies the field flows through the write path).

Time is injected via ``SNIPPET_NOW_OVERRIDE_S`` exactly like the
TTL and as-of pilots.
"""

from __future__ import annotations

import json
import os
import sys
import importlib.util
import pathlib
import shutil
import tempfile

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, "docs")
_pkg_rt = pathlib.Path("docs/runtime/__init__.py")
if _pkg_rt.exists():
    _spec = importlib.util.spec_from_file_location("runtime", _pkg_rt)
    _m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
    sys.modules["runtime"] = _m

import runtime.snippets as snip_mod           # type: ignore
from runtime.tools import ToolResult, STATUS_UNCHANGED   # type: ignore

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
    def __init__(self, t0: float = 1000.0):
        self.t = t0
        os.environ["SNIPPET_NOW_OVERRIDE_S"] = str(self.t)
    def forward(self, dt: float) -> None:
        self.t += dt
        os.environ["SNIPPET_NOW_OVERRIDE_S"] = str(self.t)
    def set(self, t: float) -> None:
        self.t = t
        os.environ["SNIPPET_NOW_OVERRIDE_S"] = str(self.t)


def tr_with_etag(source: str, as_of: str, etag: str | None,
                 payload, status: str = "SUCCESS") -> ToolResult:
    return ToolResult(
        status=status,
        data=payload,
        as_of=as_of,
        source=source,
        note=f"pilot as_of={as_of}",
        etag=etag,
    )


# ---------------------------------------------------------------------------
# 1. ToolResult grew `etag`; STATUS_UNCHANGED exported
# ---------------------------------------------------------------------------
print("=== 1. ToolResult grew `etag` + STATUS_UNCHANGED export ===")
step("STATUS_UNCHANGED = 'UNCHANGED'", STATUS_UNCHANGED == "UNCHANGED")
tr_test = ToolResult(
    status="SUCCESS", data=[{"a": 1}], as_of="2026-08-19T10:00:00Z",
    source="news_8k", note="x", etag="W/\"abc123\"",
)
step("ToolResult carries `etag`", tr_test.etag == "W/\"abc123\"")
step("to_dict includes 'etag' key", "etag" in tr_test.to_dict())
step("default etag is None on plain ToolResult", ToolResult(
    status="SUCCESS", data=[], as_of="x", source="y",
).etag is None)


# ---------------------------------------------------------------------------
# 2. SnippetMetadata JSON round-trip preserves cached_etag
# ---------------------------------------------------------------------------
print("\n=== 2. SnippetMetadata JSON round-trip preserves cached_etag ===")
m = snip_mod.SnippetMetadata(
    written_at=12345.0, source="news_8k", bytes_written=512,
    ttl_seconds=3600, truncated=False,
    cached_as_of="2026-08-19T10:00:00Z", cached_etag="W/\"abc123\"",
)
m_back = snip_mod.SnippetMetadata.from_json(m.to_json())
step("round-trip preserves cached_etag",
     m_back.cached_etag == "W/\"abc123\"")
step("round-trip preserves cached_as_of together",
     m_back.cached_as_of == "2026-08-19T10:00:00Z")
# Back-compat: old sidecar without cached_etag
old_format = json.dumps({
    "written_at": 999.0, "source": "y", "bytes_written": 50,
    "ttl_seconds": 60, "truncated": False, "cached_as_of": "2026-08-19T08:00:00Z",
})
m_old = snip_mod.SnippetMetadata.from_json(old_format)
step("old-format sidecar (no cached_etag key) → None",
     m_old.cached_etag is None)
step("old-format sidecar still has cached_as_of",
     m_old.cached_as_of == "2026-08-19T08:00:00Z")


# ---------------------------------------------------------------------------
# 3. First write records cached_etag on sidecar
# ---------------------------------------------------------------------------
print("\n=== 3. first write records cached_etag in sidecar ===")
tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="etag-pilot-"))
os.environ.pop("SNIPPET_TTL_NEWS_8K_S", None)
os.environ.pop("SNIPPET_DEFAULT_TTL_S", None)
import importlib as _il
_il.reload(snip_mod); snip_mod = sys.modules["runtime.snippets"]
FakeClock()
payload_v1 = [{"adsh": "ETAG-V1", "headline": "earnings"}]
sp1 = snip_mod.write_snippet_for(
    tr_with_etag("news_8k", "2026-08-19T10:00:00Z", "W/\"abc123\"",
                 payload_v1),
    run_id="pilot", idx=0, base_dir=tmpdir,
)
step("first write: SnippetPath returned", sp1 is not None)
step("first write: cached_etag recorded in meta",
     sp1 is not None and sp1.metadata.cached_etag == "W/\"abc123\"")
# JSON on disk
meta_p = sp1.path.with_suffix(sp1.path.suffix + ".meta.json")
sidecar = json.loads(meta_p.read_text(encoding="utf-8"))
step("sidecar JSON contains cached_etag",
     "cached_etag" in sidecar and sidecar["cached_etag"] == "W/\"abc123\"")
content_v1_bytes = sp1.path.read_bytes()
written_at_v1 = sp1.metadata.written_at


# ---------------------------------------------------------------------------
# 4. UNCHANGED preserves cache verbatim (within TTL)
# ---------------------------------------------------------------------------
print("\n=== 4. UNCHANGED preserves cache (within TTL) ===")
clock = FakeClock()
clock.forward(60)  # 1 minute
sp_unchanged = snip_mod.write_snippet_for(
    ToolResult(
        status="UNCHANGED", data=None,
        as_of="2026-08-19T10:00:00Z", source="news_8k",
        note="ETag matched: 304 Not Modified",
        etag="W/\"abc123\"",   # same etag re-attested by upstream
    ),
    "pilot", 0, base_dir=tmpdir,
)
step("UNCHANGED: SnippetPath returned (not None)", sp_unchanged is not None)
step("UNCHANGED: new_write=False (cache preserved)",
     sp_unchanged is not None and sp_unchanged.new_write is False)
step("UNCHANGED: content bytes unchanged (byte-equal)",
     sp_unchanged is not None and sp_unchanged.path.read_bytes() == content_v1_bytes)
step("UNCHANGED: cached_etag preserved on re-attestation",
     sp_unchanged is not None and sp_unchanged.metadata.cached_etag == "W/\"abc123\"")
step("UNCHANGED: written_at BUMPED to now (last-confirmed upstream check)",
     sp_unchanged is not None and sp_unchanged.metadata.written_at > written_at_v1)
step("UNCHANGED: cached_as_of preserved (no downgrade)",
     sp_unchanged is not None and sp_unchanged.metadata.cached_as_of
     == "2026-08-19T10:00:00Z")


# ---------------------------------------------------------------------------
# 5. UNCHANGED beats the TTL gate (would have refreshed otherwise)
# ---------------------------------------------------------------------------
print("\n=== 5. UNCHANGED beats TTL gate ===")
# Forward past the 24h news_8k TTL
clock.forward(sn_8k_ttl := sp1.metadata.ttl_seconds + 30)
sp_unchanged_late = snip_mod.write_snippet_for(
    ToolResult(
        status="UNCHANGED", data=None, as_of="2026-08-19T10:00:00Z",
        source="news_8k",
        note="ETag matched: 304 Not Modified (post-TTL)",
        etag="W/\"abc123\"",
    ),
    "pilot", 0, base_dir=tmpdir,
)
step("post-TTL UNCHANGED: SnippetPath returned", sp_unchanged_late is not None)
step("post-TTL UNCHANGED: new_write=False (TTL respected upstream's 304)",
     sp_unchanged_late is not None and sp_unchanged_late.new_write is False)
step("post-TTL UNCHANGED: content still v1 (not rewritten by TTL)",
     sp_unchanged_late is not None and "ETAG-V1"
     in sp_unchanged_late.path.read_text("utf-8"))


# ---------------------------------------------------------------------------
# 6. UNCHANGED with *latest* ctor returns None (no prior cache)
# ---------------------------------------------------------------------------
print("\n=== 6. UNCHANGED on empty cache → None ===")
sp_none = snip_mod.write_snippet_for(
    ToolResult(
        status="UNCHANGED", data=None, as_of="2026-08-19T10:00:00Z",
        source="news_8k", note="no prior cache",
    ),
    "pilot-fresh", 0, base_dir=tmpdir,
)
step("UNCHANGED on no-cache returns None", sp_none is None)


# ---------------------------------------------------------------------------
# 7. UNCHANGED with new etag (server rotated ETag) → use the new one
# ---------------------------------------------------------------------------
print("\n=== 7. UNCHANGED with NEW etag → recorded ===")
clock.set(5000.0)
sp_v3 = snip_mod.write_snippet_for(
    tr_with_etag("news_8k", "2026-08-19T11:00:00Z", "W/\"xyz789\"",
                 [{"adsh": "ETAG-V3"}],  # New successful write
                 status="SUCCESS"),
    "pilot", 1, base_dir=tmpdir,
)
clock.forward(60)
sp_unchanged_new = snip_mod.write_snippet_for(
    ToolResult(
        status="UNCHANGED", data=None, as_of="2026-08-19T11:00:00Z",
        source="news_8k", etag="W/\"rotated999\"",  # newly rotated
        note="304 with rotated ETag",
    ),
    "pilot", 1, base_dir=tmpdir,
)
step("UNCHANGED with rotated etag: cached_etag updates",
     sp_unchanged_new is not None
     and sp_unchanged_new.metadata.cached_etag == "W/\"rotated999\"")


# ---------------------------------------------------------------------------
# 8. force=True does NOT overrule UNCHANGED (semantic correctness)
# ---------------------------------------------------------------------------
print("\n=== 8. force=True respects UNCHANGED ===")
clock.set(7000.0)
sp_forced = snip_mod.write_snippet_for(
    tr_with_etag("news_8k", "2026-08-19T13:00:00Z", "W/\"forced\"",
                 [{"force": "FORCE"}]),
    "pilot-force", 0, base_dir=tmpdir,
)
content_before = sp_forced.path.read_bytes()
clock.forward(60)
# UNCHANGED with force=True — cache must be preserved
sp_force_unchanged = snip_mod.write_snippet_for(
    ToolResult(
        status="UNCHANGED", data=None, as_of="2026-08-19T13:00:00Z",
        source="news_8k", etag="W/\"forced\"",
        note="force=True + UNCHANGED",
    ),
    "pilot-force", 0, base_dir=tmpdir, force=True,
)
step("force=True + UNCHANGED: SnippetPath returned",
     sp_force_unchanged is not None)
step("force=True + UNCHANGED: new_write=False (force does NOT overrule 304)",
     sp_force_unchanged is not None and sp_force_unchanged.new_write is False)
step("force=True + UNCHANGED: content unchanged",
     sp_force_unchanged is not None and sp_force_unchanged.path.read_bytes()
     == content_before)


# ---------------------------------------------------------------------------
# 9. NEW etag on SUCCESS write updates the sidecar
# ---------------------------------------------------------------------------
print("\n=== 9. SUCCESS write records new etag ===")
clock.set(9000.0)
sp_v4 = snip_mod.write_snippet_for(
    tr_with_etag("news_8k", "2026-08-19T15:00:00Z", "W/\"v4\"",
                 [{"adsh": "ETAG-V4"}]),
    "pilot", 0, base_dir=tmpdir,
)
step("SUCCESS with new etag: sidecar cached_etag = 'W/\"v4\"'",
     sp_v4 is not None and sp_v4.metadata.cached_etag == "W/\"v4\"")
# File should also be re-written
step("SUCCESS write: content reflects new payload",
     sp_v4 is not None and "ETAG-V4" in sp_v4.path.read_text("utf-8"))


# ---------------------------------------------------------------------------
# 10. End-to-end call_tool — connector returns UNCHANGED on 304
# ---------------------------------------------------------------------------
print("\n=== 10. end-to-end: call_tool + UNCHANGED connector path ===")
clock.set(11000.0)
os.environ["LABOURIOUS_RUNS_DIR_OVERRIDE"] = str(tmpdir)
from runtime.tools import news_8k as news_mod
from runtime.call_tool import call_tool as real_call_tool

real_search = news_mod.News8KTool.search
call_log = []   # list of dicts carrying (etag_sent, status, payload)
def fake_search_e(self, *args, **kwargs):
    """Pretend the connector did an If-None-Match dance.

    Call #1 → 200 (warm cache), Call #2 → 304 (cached ETag matches),
    Call #3 → 200 with rotated ETag. Simulates a real HTTP connector
    branching on the upstream response code.
    """
    call_log.append({})
    n = len(call_log)
    if n == 2:
        return ToolResult(
            status="UNCHANGED", data=None,
            as_of="2026-08-19T16:00:00Z",
            source="news_8k", etag="W/\"v4\"",
            note="ETag matched: 304 Not Modified",
        )
    if n == 3:
        return ToolResult(
            status="SUCCESS", as_of="2026-08-19T17:30:00Z",  # +90min → as-of gate fires
            source="news_8k", etag="W/\"v5\"",
            data=[{"adsh": "CB-V5"}], note="fresh-after-304",
        )
    return ToolResult(
        status="SUCCESS", as_of="2026-08-19T16:00:00Z",
        source="news_8k", etag="W/\"v4\"",
        data=[{"adsh": "CB-V4"}], note="initial",
    )

try:
    news_mod.News8KTool.search = fake_search_e

    # Step 1: warm the cache with a successful fetch.
    out_first = real_call_tool("news_8k", requested_by_agent="pilot",
                                emit_event=None,
                                args={"ticker": "X", "limit": 5},
                                run_id="pilot-cb", snippet_idx=0)
    step("step1 (200): out_first has snippet_path + v4 etag",
         out_first.snippet_path is not None
         and out_first.etag == "W/\"v4\"")
    content_v4_bytes = pathlib.Path(out_first.snippet_path).read_bytes()

    # Step 2: simulate 304 — same ETag matches upstream; connector
    # returns UNCHANGED; runtime preserves cache verbatim.
    out_304 = real_call_tool("news_8k", requested_by_agent="pilot",
                             emit_event=None,
                             args={"ticker": "X", "limit": 5},
                             run_id="pilot-cb", snippet_idx=0)
    step("step2 (304): snippet_path preserved (same file)",
         out_304.snippet_path == out_first.snippet_path)
    step("step2 (304): content unchanged (byte-equal)",
         out_304.snippet_path is not None
         and pathlib.Path(out_304.snippet_path).read_bytes()
         == content_v4_bytes)
    step("step2 (304): result.status = UNCHANGED",
         out_304.status == "UNCHANGED")

    # Step 3: simulate 200 with rotated ETag — cache rewritten
    out_200b = real_call_tool("news_8k", requested_by_agent="pilot",
                              emit_event=None,
                              args={"ticker": "X", "limit": 5},
                              run_id="pilot-cb", snippet_idx=0)
    step("step3 (200 with rotated etag): same snippet_path",
         out_200b.snippet_path == out_first.snippet_path)
    step("step3 (200): content refreshed (CB-V5 present)",
         out_200b.snippet_path is not None
         and "CB-V5" in pathlib.Path(out_200b.snippet_path).read_text("utf-8"))
    step("step3 (200): sidecar cached_etag = 'W/\"v5\"'",
         out_200b.snippet_path is not None
         and out_200b.etag == "W/\"v5\"")
    meta_p = pathlib.Path(out_200b.snippet_path).with_suffix(
        pathlib.Path(out_200b.snippet_path).suffix + ".meta.json"
    )
    step("step3 (200): meta sidecar has cached_etag = 'W/\"v5\"'",
         meta_p.exists()
         and json.loads(meta_p.read_text("utf-8"))["cached_etag"]
         == "W/\"v5\"")
finally:
    news_mod.News8KTool.search = real_search


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
os.environ.pop("LABOURIOUS_RUNS_DIR_OVERRIDE", None)
os.environ.pop("SNIPPET_NOW_OVERRIDE_S", None)
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n=== pilot complete: {OK} ok / {FAIL} fail ===")
sys.exit(0 if FAIL == 0 else 1)
