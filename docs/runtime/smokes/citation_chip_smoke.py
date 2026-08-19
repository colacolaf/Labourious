"""
[domain-3] pilot — CitationChip key actions wire to open_in_browser /
copy_to_clipboard. Verifies:

  1. Chip with 1 citation + `o` → open_in_browser called once with that URL.
  2. Chip with 3 citations + `o` → open_in_browser called with the *first*
     URL (chip's current_idx default).
  3. Chip with 3 citations + `n` then `o` → open_in_browser called with
     the *second* URL (current_idx advances).
  4. Chip with 0 citations + `o` → open_in_browser NOT called; chat.py
     gets the empty-URL ActionRequested and *our flash helper sees it*.
  5. `y` key posts a copy action; copy_to_clipboard receives the URL.
  6. Native helpers are wired (mock and call recorders; no actual browser
     launches).
  7. host-label rendering for `[N citations]` flips from `[3 citations]`
     (single-citation or default) to `[2/3 sec.gov] ↵` after `n`.

The pilot deliberately does NOT pull in the whole Textual app for the
chip-level checks — it constructs a chip widget, monkey-patches
frontend.utils.platform helpers with recorders, drives the chip's
on_key directly with stubbed events, and asserts the messages posted.

For the chat.py-level routing check we instantiate the chip inside a
textual ``App`` headless pilot harness and dispatch the message.
"""

from __future__ import annotations

import sys, importlib.util, pathlib
from unittest.mock import patch, MagicMock
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Path setup — same trick as runtime/__init__.py
# ---------------------------------------------------------------------------
sys.path.insert(0, "docs")
_pkg = pathlib.Path("docs/frontend/__init__.py")
if _pkg.exists():
    _spec = importlib.util.spec_from_file_location("frontend", _pkg)
    _m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
    sys.modules["frontend"] = _m

import frontend.widgets.citation_chip as chip_mod        # type: ignore
import frontend.widgets.connection_banner as cb_mod      # type: ignore
from textual.widgets import Static  # noqa: F401
import textual.events as tevents  # type: ignore

OK = 0; FAIL = 0
def step(label, cond):
    global OK, FAIL
    if cond:
        print(f"  ok    | {label}"); OK += 1
    else:
        print(f"  FAIL  | {label}"); FAIL += 1

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def make_chip(citations: List[str], snippet_paths: List[str | None] | None = None) -> chip_mod.CitationChip:
    """Build a CitationChip outside a real app context for unit-style checks."""
    chip_id = f"test-chip-{len(citations)}"
    chip_kwargs = {"citations": citations, "id": chip_id}
    if snippet_paths is not None:
        chip_kwargs["snippet_paths"] = snippet_paths
    chip = chip_mod.CitationChip(**chip_kwargs)
    # `Static.__init__` requires `renderable=` or text arg; the chip's
    # constructor already passes self._label() — so the widget is ready
    # but cannot be mounted without an app. We work around this by
    # gathering messages posted *between* calls.
    posted: list = []
    chip.post_message = lambda m: posted.append(m)   # type: ignore[assignment]
    chip._posted_for_test = posted                    # type: ignore[attr-defined]
    return chip

def fake_key_event(key: str):
    """Build a Textual-like Key event with .key attribute and prevent_default/stop."""
    ev = MagicMock()
    ev.key = key
    return ev


# ---------------------------------------------------------------------------
# 1. Single URL: `o` posts open action for that URL
# ---------------------------------------------------------------------------
print("=== 1. single URL → `o` posts open-action with the URL ===")
chip = make_chip(["https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000789019"])
chip.on_key(fake_key_event("o"))
posted = chip._posted_for_test    # type: ignore[attr-defined]
step("1 message posted", len(posted) == 1)
step("message is ActionRequested (not Pressed)",
     isinstance(posted[0], chip_mod.CitationChip.ActionRequested))
m0 = posted[0]
step("action == 'open'", m0.action == "open")
step("url == the chip's URL", m0.url == "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000789019")
step("idx == 0", m0.idx == 0)

# ---------------------------------------------------------------------------
# 2. Three URLs: `o` posts open-action with the *first*
# ---------------------------------------------------------------------------
print("\n=== 2. three URLs → `o` defaults to idx=0 ===")
chip = make_chip([
    "https://www.sec.gov/edgar/1",
    "https://www.sec.gov/edgar/2",
    "https://www.sec.gov/edgar/3",
])
posted = chip._posted_for_test
chip.on_key(fake_key_event("o"))
step("action == 'open'", posted[-1].action == "open")
step("url == citations[0]", posted[-1].url == "https://www.sec.gov/edgar/1")
step("idx == 0", posted[-1].idx == 0)

# ---------------------------------------------------------------------------
# 3. `n` advances and the chip's label changes
# ---------------------------------------------------------------------------
print("\n=== 3. `n` advances current_idx and updates label ===")
chip = make_chip([
    "https://www.sec.gov/edgar/1",
    "https://www.reuters.com/article/1",
    "https://fred.stlouisfed.org/series/GDP",
])
posted = chip._posted_for_test
chip.on_key(fake_key_event("n"))
step("after 1 × `n`: idx == 1", chip._current_idx == 1)
step("requested url == citations[1]",
     posted[-1].url == "https://www.reuters.com/article/1")
chip.on_key(fake_key_event("n"))
step("after 2 × `n`: idx == 2", chip._current_idx == 2)
chip.on_key(fake_key_event("n"))
step("after 3 × `n`: wraps to 0", chip._current_idx == 0)
# `o` after wrap
posted.clear()
chip.on_key(fake_key_event("o"))
step("`o` after wrap uses citations[0]",
     posted[-1].url == "https://www.sec.gov/edgar/1")

# ---------------------------------------------------------------------------
# 4. Empty chip: `o` posts empty-URL action
# ---------------------------------------------------------------------------
print("\n=== 4. empty chip → `o` posts empty-URL marker ===")
chip = make_chip([])
posted = chip._posted_for_test
chip.on_key(fake_key_event("o"))
step("1 message posted", len(posted) == 1)
step("message is ActionRequested",
     isinstance(posted[0], chip_mod.CitationChip.ActionRequested))
step("action == 'open'", posted[0].action == "open")
step("url == ''", posted[0].url == "")
step("idx == -1 (empty)", posted[0].idx == -1)

# ---------------------------------------------------------------------------
# 5. `y` key posts a copy action
# ---------------------------------------------------------------------------
print("\n=== 5. `y` posts a copy-action ===")
chip = make_chip(["https://www.sec.gov/edgar/only"])
posted = chip._posted_for_test
chip.on_key(fake_key_event("y"))
step("action == 'copy'", posted[-1].action == "copy")
step("url == the chip's URL",
     posted[-1].url == "https://www.sec.gov/edgar/only")

# ---------------------------------------------------------------------------
# 6. click still posts Pressed (not ActionRequested)
# ---------------------------------------------------------------------------
print("\n=== 6. _on_click posts Pressed (existing behaviour intact) ===")
chip = make_chip(["https://www.sec.gov/clicked"])
posted = chip._posted_for_test
chip._on_click(MagicMock())
step("Pressed posted by click", isinstance(posted[0], chip_mod.CitationChip.Pressed))
step("ActionRequested NOT posted by click",
     not any(isinstance(m, chip_mod.CitationChip.ActionRequested) for m in posted))

# ---------------------------------------------------------------------------
# 7. host label rendering on the chip.text
# ---------------------------------------------------------------------------
print("\n=== 7. chip label rendering ===")
chip = make_chip([
    "https://www.sec.gov/edgar/1",
    "https://www.reuters.com/x",
])
# defaults to idx=0 in the indexed form: '[1/2 sec.gov]'
step("default label uses indexed form '1/2' + first host 'sec.gov'",
     "1/2" in chip._label() and "sec.gov" in chip._label())
# After 1× `n`: idx → 1, label flips to '[2/2 reuters.com]'
chip.on_key(fake_key_event("n"))
step("after 1× `n`: label flips to '2/2' and shows reuters.com",
     "2/2" in chip._label() and "reuters.com" in chip._label())
# Single-citation chip flips to the simple form (no idx)
single_chip = make_chip(["https://www.sec.gov/only"])
step("single-citation chip label uses simple form",
     "1 citation" in single_chip._label() and "/" not in single_chip._label())
# Empty chip renders the dedicated 'no citations' label
empty_chip = make_chip([])
step("empty chip label says 'no citations'",
     "no citations" in empty_chip._label())

# ---------------------------------------------------------------------------
# 8. Frontend-level: monkey-patch platform.open_in_browser + verify routing
# ---------------------------------------------------------------------------
print("\n=== 8. chat.py-level routing: monkey-patch platform + invoke handler ===")
# Import chat and the platform module after path setup
import frontend.utils.platform as plat_mod    # type: ignore
import frontend.screens.chat as chat_mod      # type: ignore

# Build a chip instance + a fake ChatScreen handler context.
# We don't need a full App for this — we can call the bound handler
# directly by simulating Textual message routing.
fake_msg = chip_mod.CitationChip.ActionRequested(
    chip_id="ignored", action="open",
    url="https://www.sec.gov/edgar/url-X", idx=0,
)
opener_calls: List[Tuple[str, ...]] = []
copier_calls: List[Tuple[str, ...]] = []
def fake_open(url): opener_calls.append((url,)); return (True, "")
def fake_copy(text): copier_calls.append((text,)); return (True, "")

# Bind the handlers to a stand-in object. We are NOT exercising the app;
# we want to verify that chat_screen's handler calls platform helpers.
class StubChat:
    on_citation_chip_action_requested = chat_mod.ChatScreen.on_citation_chip_action_requested
    _set_status_flash = chat_mod.ChatScreen._set_status_flash
    _set_banner_warning = chat_mod.ChatScreen._set_banner_warning
    _set_banner_ok = chat_mod.ChatScreen._set_banner_ok
    def query_one(self, *_a, **_kw): raise AssertionError("query_one should not be called in this stub path")

# Use a recording flash helper that captures whatever text/status it gets.
class StubChatWithFlash(StubChat):
    def __init__(self):
        self.flash_log: List[Tuple[str, str]] = []
    def _set_status_flash(self, msg, *, ok=False, warn=False, duration_s=0.0):
        self.flash_log.append((msg, "ok" if ok else ("warn" if warn else "info")))
    def query_one(self, *_a, **_kw):
        return MagicMock()  # never actually called for open/copy path

stub = StubChatWithFlash()

with patch.object(plat_mod, "open_in_browser", side_effect=fake_open):
    with patch.object(plat_mod, "copy_to_clipboard", side_effect=fake_copy):
        # open
        stub.on_citation_chip_action_requested(fake_msg)
        step("open_in_browser called once with the URL",
             len(opener_calls) == 1 and opener_calls[0][0] == "https://www.sec.gov/edgar/url-X")
        step("flash helper called with success line",
             any("opened" in m and tag == "ok" for m, tag in stub.flash_log))
        opener_calls.clear(); stub.flash_log.clear()

        # copy
        copy_msg = chip_mod.CitationChip.ActionRequested(
            chip_id="ignored", action="copy",
            url="https://www.reuters.com/x", idx=0,
        )
        stub.on_citation_chip_action_requested(copy_msg)
        step("copy_to_clipboard called once with the URL",
             len(copier_calls) == 1 and copier_calls[0][0] == "https://www.reuters.com/x")
        step("flash helper called with 'copied'",
             any("copied" in m and tag == "ok" for m, tag in stub.flash_log))
        copier_calls.clear(); stub.flash_log.clear()

        # open with empty URL (idx=-1) → flash helper gets warn, no opener
        empty_msg = chip_mod.CitationChip.ActionRequested(
            chip_id="ignored", action="open", url="", idx=-1,
        )
        stub.on_citation_chip_action_requested(empty_msg)
        step("empty-URL open: no opener call", len(opener_calls) == 0)
        step("empty-URL open: flash helper gets a warn-style msg",
             any(("no URL" in m or "modal" in m) and tag == "warn"
                 for m, tag in stub.flash_log))

# ---------------------------------------------------------------------------
# 9. ConnectionBanner.info round-trip
# ---------------------------------------------------------------------------
print("\n=== 9. ConnectionBanner.set_info + _is_info_active round-trip ===")
banner = cb_mod.ConnectionBanner()
step("default state hidden-ish", banner._is_info_active() is False)
banner.set_info("opened https://www.sec.gov/edgar/x")
step("after set_info: _is_info_active True", banner._is_info_active() is True)
step("renderable contains the info text",
     "opened https://www.sec.gov/edgar/x" in str(banner.render()))
banner.set_ok()
step("after set_ok: _is_info_active False", banner._is_info_active() is False)

# Verify set_warning clobbers info but set_info doesn't clobber warn
banner.set_warning("blocked network")
step("after set_warning: not info-active (warn wins)", banner._is_info_active() is False)
banner.set_info("✓ opened https://www.sec.gov/edgar/y")
step("after set_info: info-active again", banner._is_info_active() is True)
step("renderable shows opened, not the warn text",
     "opened" in str(banner.render()) and "blocked network" not in str(banner.render()))

# ---------------------------------------------------------------------------
# 10. snippet cache freshness — chip label flips to ⚠ ◫ when snippets
#     are past their TTL.  We exercise the runtime.snippets writer in a
#     temp dir, then verify the chip's ``_label()`` reads the sidecar
#     correctly. The chip imports runtime.snippets lazily at label
#     render time, so a real filesystem round-trip is the most
#     realistic end-to-end check we can do without the full Textual app.
# ---------------------------------------------------------------------------
print("\n=== 10. chip label reads snippet TTL freshness ===")
import tempfile, shutil as _shutil, os
import runtime.snippets as snip_mod          # type: ignore
from runtime.tools import ToolResult          # type: ignore
snip_tmp = pathlib.Path(tempfile.mkdtemp(prefix="chip-stale-"))
try:
    # Pin fake clock so we have a deterministic written_at
    os.environ["SNIPPET_NOW_OVERRIDE_S"] = "50000.0"
    # Force a tiny TTL so we can advance past it quickly.
    os.environ["SNIPPET_TTL_NEWS_8K_S"] = "60"
    _il = importlib if False else __import__("importlib")
    _il.reload(snip_mod); snip_mod = sys.modules["runtime.snippets"]

    tr_fresh = ToolResult(
        status="SUCCESS",
        data=[{"adsh": "FRESH-1", "company": "Acme", "ticker": "ACME"}],
        as_of="2026-08-19T18:00:00Z",
        source="news_8k",
        note="x",
    )
    sp_fresh = snip_mod.write_snippet_for(tr_fresh, "pilot", 0, base_dir=snip_tmp)
    chip_fresh = make_chip(
        ["https://www.reuters.com/x"],
        snippet_paths=[str(sp_fresh.path)],
    )
    label_fresh = chip_fresh._label()
    step("fresh snippet: label has ◫ (no ⚠)", "◫" in label_fresh and "⚠ ◫" not in label_fresh)

    # Advance the clock past 60s.  Same ToolResult path: the chip
    # reads sidecar at label time, so we don't need to re-write.
    os.environ["SNIPPET_NOW_OVERRIDE_S"] = "50061.0"   # +1s past 60s TTL
    label_stale = chip_fresh._label()
    step("after TTL elapses: label flips to ⚠ ◫", "⚠ ◫" in label_stale)
    # Multi-citation chip with mixed freshness: ☆ one fresh, one stale.
    tr_stale = ToolResult(
        status="SUCCESS",
        data=[{"adsh": "STALE-1", "company": "Stale", "ticker": "ZZZ"}],
        as_of="2026-08-19T18:00:00Z",
        source="news_8k",
        note="x",
    )
    os.environ["SNIPPET_NOW_OVERRIDE_S"] = "50100.0"
    sp_stale = snip_mod.write_snippet_for(tr_stale, "pilot", 1, base_dir=snip_tmp)
    # Backdate the second snippet so it's stale even at the chip's
    # current clock.
    import json as _json
    meta_p = pathlib.Path(sp_stale.path).with_suffix(
        pathlib.Path(sp_stale.path).suffix + ".meta.json"
    )
    meta_obj = _json.loads(meta_p.read_text("utf-8"))
    meta_obj["written_at"] = 40000.0   # very old
    meta_obj["ttl_seconds"] = 60
    meta_p.write_text(_json.dumps(meta_obj, indent=2), encoding="utf-8")
    # Re-set the clock to "now" (50100) so the freshness check
    # clearly distinguishes idx=0 (fresh) from idx=1 (stale).
    os.environ["SNIPPET_NOW_OVERRIDE_S"] = "50100.0"
    chip_mixed = make_chip(
        ["https://www.reuters.com/0", "https://www.reuters.com/1"],
        snippet_paths=[str(sp_fresh.path), str(sp_stale.path)],
    )
    label_mixed = chip_mixed._label()
    step("mixed chip: at least one stale → whole-chip badge is ⚠ ◫",
         "⚠ ◫" in label_mixed)

finally:
    os.environ.pop("SNIPPET_NOW_OVERRIDE_S", None)
    os.environ.pop("SNIPPET_TTL_NEWS_8K_S", None)
    _shutil.rmtree(snip_tmp, ignore_errors=True)
    _il.reload(snip_mod); snip_mod = sys.modules["runtime.snippets"]

# ---------------------------------------------------------------------------
# Final
# ---------------------------------------------------------------------------
print(f"\n=== pilot complete: {OK} ok / {FAIL} fail ===")
sys.exit(0 if FAIL == 0 else 1)
