"""
[domain-6] pilot — snippet cache as-of-aware refresh gate.

Adds a second refresh trigger alongside the wallclock TTL: when the
upstream ``ToolResult.as_of`` is *strictly later* than the cache's
``cached_as_of`` (recorded in the sidecar), the snippet is rewritten
even if the wallclock TTL hasn't elapsed. This handles the case where
the same connector publishes a *successor* 8-K within the same TTL
window — we want the latest, not the cached one.

Verifies:
  1. ``_iso_compare`` lexicographic ISO ordering; ``Z`` suffix
     normalized to ``+00:00`` (so ``...Z`` and ``...+00:00`` compare equal).
  2. ``None``-vs-string returns ``-1`` for non-None.
  3. First write stores ``cached_as_of`` in the sidecar from
     ``ToolResult.as_of``.
  4. Second write at t+60s with **later** as_of → ``new_write=True``
     even within 24h TTL. cached_as_of in meta updates.
  5. Second write at t+60s with **equal** as_of → reused
     (``new_write=False``) — gate doesn't trigger on equality.
  6. Second write at t+60s with **older** as_of → reused
     (``new_write=False``) — refuse to downgrade cache to an older
     revision of the source.
  7. Second write at t+60s with **missing** as_of → only TTL gate
     applies; if TTL is intact, reused.
  8. ``force=True`` overrides the as-of gate (force-rewrite always).
  9. TTL still fires when as_of is equal (no double-refresh needed).
 10. End-to-end ``call_tool(run_id=...)`` second call within TTL window
     with later ``as_of`` → snippet file is rewritten.
 11. ``SnippetMetadata`` JSON round-trip preserves ``cached_as_of``.
 12. ``force_refresh(path, new_metadata_overrides={cached_as_of: ...})``
     exposes the new field for symmetric updates.

Time is injected via ``SNIPPET_NOW_OVERRIDE_S`` env var exactly like
the TTL pilot — no real sleeping.
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
from typing import Optional

# Path setup
sys.path.insert(0, "docs")
_pkg_rt = pathlib.Path("docs/runtime/__init__.py")
if _pkg_rt.exists():
    _spec = importlib.util.spec_from_file_location("runtime", _pkg_rt)
    _m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
    sys.modules["runtime"] = _m

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
    def __init__(self, t0: float = 2000.0):
        self.t = t0
        os.environ["SNIPPET_NOW_OVERRIDE_S"] = str(self.t)
    def forward(self, dt: float) -> None:
        self.t += dt
        os.environ["SNIPPET_NOW_OVERRIDE_S"] = str(self.t)
    def set(self, t: float) -> None:
        self.t = t
        os.environ["SNIPPET_NOW_OVERRIDE_S"] = str(self.t)


def tr_with_asof(source: str, as_of: Optional[str], payload) -> ToolResult:
    return ToolResult(
        status="SUCCESS",
        data=payload,
        as_of=as_of or "",
        source=source,
        note=f"synthetic pilot as_of={as_of}",
    )


# ---------------------------------------------------------------------------
# 1. _iso_compare — lexicographic ordering
# ---------------------------------------------------------------------------
print("=== 1. _iso_compare lexicographic + Z normalization ===")
step("equal strings → 0", snip_mod._iso_compare("2026-08-19T10:00:00Z",
                                                 "2026-08-19T10:00:00Z") == 0)
step("earlier < later", snip_mod._iso_compare("2026-08-19T09:00:00Z",
                                               "2026-08-19T10:00:00Z") == -1)
step("later > earlier", snip_mod._iso_compare("2026-08-19T10:00:00Z",
                                               "2026-08-19T09:00:00Z") == 1)
step("Z and +00:00 compare equal",
     snip_mod._iso_compare("2026-08-19T10:00:00Z",
                           "2026-08-19T10:00:00+00:00") == 0)
step("Z vs +05:30 returns non-zero (different offsets)",
     snip_mod._iso_compare("2026-08-19T10:00:00Z",
                           "2026-08-19T15:30:00+05:30") != 0)
step("None vs string: returns -1 (string is 'less than' None)",
     snip_mod._iso_compare("2026-08-19T10:00:00Z", None) == -1)
step("string vs None: returns +1 (string is 'less than' None)",
     snip_mod._iso_compare(None, "2026-08-19T10:00:00Z") == 1)
step("None vs None: 0", snip_mod._iso_compare(None, None) == 0)


# ---------------------------------------------------------------------------
# 2. cached_as_of stored on first write
# ---------------------------------------------------------------------------
print("\n=== 2. first write records cached_as_of in sidecar ===")
tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="asof-pilot-"))
# Use a long TTL (24h) so the TTL gate doesn't trigger prematurely.
os.environ.pop("SNIPPET_TTL_NEWS_8K_S", None)
os.environ.pop("SNIPPET_DEFAULT_TTL_S", None)
import importlib as _il
_il.reload(snip_mod); snip_mod = sys.modules["runtime.snippets"]
FakeClock()
sp1 = snip_mod.write_snippet_for(
    tr_with_asof("news_8k", "2026-08-19T10:00:00Z",
                 [{"adsh": "F1", "headline": "earnings beat"}]),
    run_id="pilot", idx=0, base_dir=tmpdir,
)
step("first write: SnippetPath returned", sp1 is not None)
step("first write: cached_as_of recorded in meta",
     sp1 is not None and sp1.metadata is not None
     and sp1.metadata.cached_as_of == "2026-08-19T10:00:00Z")
# Verify the JSON sidecar on disk has the field too
meta_p = sp1.path.with_suffix(sp1.path.suffix + ".meta.json")
sidecar = json.loads(meta_p.read_text(encoding="utf-8"))
step("sidecar JSON contains cached_as_of key",
     "cached_as_of" in sidecar
     and sidecar["cached_as_of"] == "2026-08-19T10:00:00Z")


# ---------------------------------------------------------------------------
# 3. Later as_of → refresh within TTL
# ---------------------------------------------------------------------------
print("\n=== 3. later as_of refreshes even within 24h TTL ===")
clock = FakeClock()
clock.forward(60)  # 1 minute — far inside 24h
tr_later = tr_with_asof("news_8k", "2026-08-19T11:00:00Z",  # +1h
                        [{"adsh": "F2-LATER", "headline": "guidance update"}])
sp_3 = snip_mod.write_snippet_for(tr_later, "pilot", 0, base_dir=tmpdir)
step("later as_of: SnippetPath returned", sp_3 is not None)
step("later as_of: new_write=True (forced refresh)",
     sp_3 is not None and sp_3.new_write is True)
step("later as_of: content refreshed to v2",
     sp_3 is not None and "F2-LATER" in sp_3.path.read_text("utf-8"))
step("later as_of: cached_as_of advanced",
     sp_3 is not None and sp_3.metadata.cached_as_of == "2026-08-19T11:00:00Z")
step("later as_of: written_at advanced too (force_refresh bump)",
     sp_3 is not None and sp_3.metadata.written_at > sp1.metadata.written_at)


# ---------------------------------------------------------------------------
# 4. Equal as_of → no refresh (within TTL)
# ---------------------------------------------------------------------------
print("\n=== 4. equal as_of reuses cached (does NOT trigger gate) ===")
clock.set(sp3_written_at := sp_3.metadata.written_at)
sp_3b = snip_mod.write_snippet_for(
    tr_with_asof("news_8k", "2026-08-19T11:00:00Z",
                 [{"adsh": "SHOULD-NOT-REPLACE"}]),
    "pilot", 0, base_dir=tmpdir,
)
step("equal as_of within TTL: new_write=False",
     sp_3b is not None and sp_3b.new_write is False)
step("equal as_of: cached content (F2-LATER) preserved",
     sp_3b is not None and "F2-LATER" in sp_3b.path.read_text("utf-8")
     and "SHOULD-NOT-REPLACE" not in sp_3b.path.read_text("utf-8"))


# ---------------------------------------------------------------------------
# 5. Older as_of → no downgrade of the cache
# ---------------------------------------------------------------------------
print("\n=== 5. older as_of does NOT downgrade the cache ===")
clock.forward(60)
tr_older = tr_with_asof("news_8k", "2026-08-19T09:30:00Z",
                        [{"adsh": "STALE-VERSION"}])
sp_5 = snip_mod.write_snippet_for(tr_older, "pilot", 0, base_dir=tmpdir)
step("older as_of within TTL: new_write=False",
     sp_5 is not None and sp_5.new_write is False)
step("older as_of: cache stays at v2 (F2-LATER)",
     sp_5 is not None and "F2-LATER" in sp_5.path.read_text("utf-8")
     and "STALE-VERSION" not in sp_5.path.read_text("utf-8"))
step("older as_of: cached_as_of stays at v2's as_of",
     sp_5 is not None and sp_5.metadata.cached_as_of == "2026-08-19T11:00:00Z")


# ---------------------------------------------------------------------------
# 6. Missing as_of on the second call: TTL gate only
# ---------------------------------------------------------------------------
print("\n=== 6. missing as_of on second call: TTL gate only ===")
clock.set(sp5_written_at := sp_5.metadata.written_at)
tr_no_asof = tr_with_asof("news_8k", None,  # missing as_of
                          [{"adsh": "ASOF-NONE"}])
sp_6 = snip_mod.write_snippet_for(tr_no_asof, "pilot", 0, base_dir=tmpdir)
step("missing as_of within TTL: new_write=False (TTL still says fresh)",
     sp_6 is not None and sp_6.new_write is False)
step("missing as_of: content unchanged",
     sp_6 is not None and "F2-LATER" in sp_6.path.read_text("utf-8")
     and "ASOF-NONE" not in sp_6.path.read_text("utf-8"))
# But, missing as_of WITH TTL elapsed → refreshes.
clock.forward(sp_6.metadata.ttl_seconds + 30)
sp_6b = snip_mod.write_snippet_for(tr_no_asof, "pilot", 0, base_dir=tmpdir)
step("missing as_of + TTL elapsed: new_write=True",
     sp_6b is not None and sp_6b.new_write is True)
step("missing as_of + TTL: cache now contains ASOF-NONE",
     sp_6b is not None and "ASOF-NONE" in sp_6b.path.read_text("utf-8"))
step("missing as_of: cached_as_of cleared to None",
     sp_6b is not None and sp_6b.metadata.cached_as_of in (None, ""))


# ---------------------------------------------------------------------------
# 7. force=True overrides the as-of gate (always rewrites)
# ---------------------------------------------------------------------------
print("\n=== 7. force=True overrides the as-of gate ===")
clock.set(5000.0)
sp_7a = snip_mod.write_snippet_for(
    tr_with_asof("news_8k", "2026-08-19T20:00:00Z", [{"v": "A"}]),
    "pilot-force", 0, base_dir=tmpdir,
)
clock.forward(60)
sp_7b = snip_mod.write_snippet_for(
    tr_with_asof("news_8k", "2026-08-19T19:00:00Z",  # OLDER asof
                 [{"v": "FORCED"}]),
    "pilot-force", 0, base_dir=tmpdir, force=True,
)
step("force=True: new_write=True even with older as_of",
     sp_7b is not None and sp_7b.new_write is True)
step("force=True: content is the forced one",
     sp_7b is not None and "FORCED" in sp_7b.path.read_text("utf-8"))
step("force=True: cached_as_of reflects the FORCED (older) entry",
     sp_7b is not None and sp_7b.metadata.cached_as_of == "2026-08-19T19:00:00Z")


# ---------------------------------------------------------------------------
# 8. TTL still fires when as_of stays equal
# ---------------------------------------------------------------------------
print("\n=== 8. TTL still fires independently of as_of ===")
clock.set(6000.0)
sp_8a = snip_mod.write_snippet_for(
    tr_with_asof("news_8k", "2026-08-19T20:30:00Z", [{"id": "TTL-A"}]),
    "pilot-ttl", 0, base_dir=tmpdir,
)
ttl_v = sp_8a.metadata.ttl_seconds
clock.forward(ttl_v + 30)  # past TTL
sp_8b = snip_mod.write_snippet_for(
    tr_with_asof("news_8k", "2026-08-19T20:30:00Z",  # same as_of
                 [{"id": "TTL-B"}]),
    "pilot-ttl", 0, base_dir=tmpdir,
)
step("TTL elapsed + same as_of: new_write=True (TTL fired)",
     sp_8b is not None and sp_8b.new_write is True)
step("TTL: content swapped",
     sp_8b is not None and "TTL-B" in sp_8b.path.read_text("utf-8"))


# ---------------------------------------------------------------------------
# 9. SnippetMetadata JSON round-trip preserves cached_as_of
# ---------------------------------------------------------------------------
print("\n=== 9. SnippetMetadata JSON round-trip preserves cached_as_of ===")
m = snip_mod.SnippetMetadata(
    written_at=12345.0, source="news_8k", bytes_written=512,
    ttl_seconds=3600, truncated=False, cached_as_of="2026-08-19T22:00:00Z",
)
m_back = snip_mod.SnippetMetadata.from_json(m.to_json())
step("round-trip preserves cached_as_of",
     m_back.cached_as_of == "2026-08-19T22:00:00Z")
# None round-trip too
m_none = snip_mod.SnippetMetadata(
    written_at=1.0, source="x", bytes_written=1,
    ttl_seconds=60, cached_as_of=None,
)
m_none_back = snip_mod.SnippetMetadata.from_json(m_none.to_json())
step("round-trip preserves None cached_as_of",
     m_none_back.cached_as_of is None)
# Old-format sidecar without cached_as_of (back-compat)
old_format = json.dumps({
    "written_at": 999.0, "source": "y", "bytes_written": 50,
    "ttl_seconds": 60, "truncated": False,
})
m_old = snip_mod.SnippetMetadata.from_json(old_format)
step("old-format sidecar (no cached_as_of key) → None",
     m_old.cached_as_of is None)


# ---------------------------------------------------------------------------
# 10. force_refresh(path, new_metadata_overrides={cached_as_of: ...})
# ---------------------------------------------------------------------------
print("\n=== 10. force_refresh supports cached_as_of in overrides ===")
clock.set(7000.0)
sp_fra = snip_mod.write_snippet_for(
    tr_with_asof("news_8k", "2026-08-19T21:00:00Z",
                 [{"adsh": "FR-A"}]),
    "pilot-fr", 0, base_dir=tmpdir,
)
clock.forward(60)
sp_frb = snip_mod.force_refresh(
    sp_fra.path,
    new_metadata_overrides={"cached_as_of": "2026-08-19T22:00:00Z"},
    base_dir=tmpdir,
)
step("force_refresh with overrides returns SnippetPath",
     sp_frb is not None)
step("force_refresh: cached_as_of overridden",
     sp_frb is not None and sp_frb.metadata.cached_as_of == "2026-08-19T22:00:00Z")


# ---------------------------------------------------------------------------
# 11. end-to-end call_tool(run_id=...) with later as_of → refresh
# ---------------------------------------------------------------------------
print("\n=== 11. call_tool end-to-end: later as_of triggers refresh ===")
clock.set(8000.0)
os.environ["LABOURIOUS_RUNS_DIR_OVERRIDE"] = str(tmpdir)
from runtime.tools import news_8k as news_mod
from runtime.call_tool import call_tool as real_call_tool

# Two feeds of "what the connector returns"
asof_calls = [
    ("2026-08-19T12:00:00Z", [{"adsh": "RT-A1", "headline": "earnings"}]),
    ("2026-08-19T12:30:00Z", [{"adsh": "RT-A2", "headline": "guidance"}]),
    ("2026-08-19T12:15:00Z", [{"adsh": "OLD", "headline": "should-not-win"}]),
]
call_idx = 0
def fake_search_news(self, *args, **kwargs):
    global call_idx
    asof, payload = asof_calls[call_idx]
    call_idx += 1
    return ToolResult(
        status="SUCCESS", data=payload, as_of=asof,
        source="news_8k", note="asof-pilot",
    )
real_search = news_mod.News8KTool.search
try:
    news_mod.News8KTool.search = fake_search_news

    # Call 1: A1 + asof T
    out_a = real_call_tool("news_8k", requested_by_agent="pilot",
                           emit_event=None, args={"ticker":"X","limit":5},
                           run_id="pilot-cb", snippet_idx=0)
    c1 = pathlib.Path(out_a.snippet_path).read_text("utf-8")
    step("call_tool 1: out_a has snippet_path with RT-A1",
         out_a.snippet_path is not None and "RT-A1" in c1)

    # Wallclock: 1 min later (well within 24h)
    clock.forward(60)
    # Call 2: A2 + asof T+1h — should refresh
    out_b = real_call_tool("news_8k", requested_by_agent="pilot",
                           emit_event=None, args={"ticker":"X","limit":5},
                           run_id="pilot-cb", snippet_idx=0)
    c2 = pathlib.Path(out_b.snippet_path).read_text("utf-8")
    step("call_tool 2 (later as_of): snippet_path preserved",
         out_b.snippet_path == out_a.snippet_path)
    step("call_tool 2 (later as_of): content refreshed to RT-A2",
         "RT-A2" in c2 and "RT-A1" not in c2)

    # Wallclock: 30s later (still within TTL)
    clock.forward(30)
    # Call 3: OLD + asof T+15m (OLDER than T+1h) — should NOT downgrade
    out_c = real_call_tool("news_8k", requested_by_agent="pilot",
                           emit_event=None, args={"ticker":"X","limit":5},
                           run_id="pilot-cb", snippet_idx=0)
    c3 = pathlib.Path(out_c.snippet_path).read_text("utf-8")
    step("call_tool 3 (older as_of): cached version preserved (RT-A2)",
         "RT-A2" in c3 and "OLD" not in c3)
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
