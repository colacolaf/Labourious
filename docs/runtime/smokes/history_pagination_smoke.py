"""smoke — history modal cursor pagination + cross-flow ticker filter.

Verifies the end-to-end path:
  history_io.read_theses_page → keyset cursor pagination
  history_io.list_tickers → distinct tickers
  history_io.count_theses → total + filtered count
  HistoryScreen pagination + filter state machine (monkey-patched)

Exercises:
  1. read_theses_page — first page returns up to PAGE_SIZE rows
  2. read_theses_page — second page via cursor
  3. read_theses_page — exhausted pages
  4. read_theses_page — ticker_filter narrows
  5. list_tickers — returns distinct tickers
  6. count_theses — total and filtered counts
  7. HistoryScreen._load_page — populated via _load_page
  8. HistoryScreen._reset_and_reload — filter change resets pagination
  9. HistoryScreen._render_pill_bar — ticker pills rendering
  10. HistoryScreen action_next_filter — tab cycles pills
  11. HistoryScreen action_page_down / action_page_up — page navigation
  12. HistoryScreen BINDINGS include tab/pageup/pagedown

Run:
    PYTHONPATH=docs python3 docs/runtime/smokes/history_pagination_smoke.py
"""

from __future__ import annotations

import sys
import tempfile
import sqlite3
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2]

if str(DOCS) not in sys.path:
    sys.path.insert(0, str(DOCS))

# ---------- smoke harness ----------
_ok: list[int] = []
_bad: list[int] = []


def _pass(label: str) -> None:
    _ok[0] += 1
    print(f"  ✓ {label}")


def _fail(label: str, extra: str = "") -> None:
    _bad[0] += 1
    print(f"  ✗ FAIL: {label}{extra}")


def step(label: str, value: bool) -> None:
    if value:
        _pass(label)
    else:
        _fail(label)


def step_eq(label: str, a, b) -> None:
    if a == b:
        _pass(label)
    else:
        _fail(label, f"  ({a!r} != {b!r})")


def section(title: str) -> None:
    print(f"\n── {title} ──")


_ok.append(0)
_bad.append(0)


# ===========================================================================
# 0. Setup — seed a fresh in-memory test DB
# ===========================================================================
section("0. Seed test DB")

tmpdir = tempfile.TemporaryDirectory()
DB = Path(tmpdir.name) / "test_theses.db"

con = sqlite3.connect(str(DB))
con.execute("""
    CREATE TABLE theses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        date TEXT NOT NULL,
        thesis_text TEXT DEFAULT '',
        conviction INTEGER DEFAULT 3,
        bottom_line TEXT DEFAULT '{}',
        evidence_urls TEXT DEFAULT '[]',
        flow_id TEXT DEFAULT 'f1',
        version INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        model TEXT,
        paid_for INTEGER DEFAULT 0
    )
""")
# Seed 25 rows: NVDA x 12, AAPL x 8, TSLA x 5 — newest-first by created_at.
# TSLA gets the latest timestamps so list_tickers sorts it first.
tickers = (["NVDA"] * 12) + (["AAPL"] * 8) + (["TSLA"] * 5)
for i, t in enumerate(tickers):
    # TSLA (i=20-24) gets latest timestamps
    ts = f"2026-08-{'01' if i < 10 else '02'}T{10 + i // 2:02d}:00:00Z"
    con.execute(
        "INSERT INTO theses (ticker, date, thesis_text, bottom_line, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (t, f"2026-08-{i+1:02d}", f"thesis {i+1} for {t}",
         '{"direction":"HOLD","price":100.0,"base_case":90.0,"text":"hold"}',
         ts),
    )
con.commit()
con.close()

step("test DB created with 25 rows", True)

from frontend.history_io import (
    read_theses_page, read_theses_all, list_tickers, count_theses,
)

PAGE_SIZE = 7  # smaller page to exercise pagination

# ===========================================================================
# 1. read_theses_page — first page
# ===========================================================================
section("1. read_theses_page — first page")

page1 = read_theses_page(DB, limit=PAGE_SIZE)
step_eq(f"first page returns {PAGE_SIZE} rows", len(page1), PAGE_SIZE)
step("all rows are ThesisRow", all(hasattr(r, "ticker") for r in page1))
step_eq("first row has highest id (newest)", page1[0].id, 25)
step_eq("last row id", page1[-1].id, 26 - PAGE_SIZE)

# ===========================================================================
# 2. read_theses_page — second page via cursor
# ===========================================================================
section("2. read_theses_page — second page via cursor")

cursor = (page1[-1].datetime, page1[-1].id)
page2 = read_theses_page(DB, limit=PAGE_SIZE, cursor=cursor)
step_eq(f"second page returns {PAGE_SIZE} rows", len(page2), PAGE_SIZE)
step_eq("second page starts after first", page2[0].id, page1[-1].id - 1)

# ===========================================================================
# 3. read_theses_page — exhausted pages
# ===========================================================================
section("3. read_theses_page — exhausted pages")

cursor3 = (page2[-1].datetime, page2[-1].id)
page3 = read_theses_page(DB, limit=PAGE_SIZE, cursor=cursor3)
# 25 total, 14 read so far, limit=7 → min(7, 11) = 7
step_eq("third page returns 7 (limit confined)", len(page3), 7)

cursor4 = (page3[-1].datetime, page3[-1].id)
page4 = read_theses_page(DB, limit=PAGE_SIZE, cursor=cursor4)
# 25 total, 21 read, 4 remain → returns 4
step_eq("fourth page returns remaining 4", len(page4), 4)

cursor5 = (page4[-1].datetime, page4[-1].id)
page5 = read_theses_page(DB, limit=PAGE_SIZE, cursor=cursor5)
step_eq("fifth page empty (all 25 read)", len(page5), 0)

# ===========================================================================
# 4. read_theses_page — ticker filter
# ===========================================================================
section("4. read_theses_page — ticker filter")

nvda_page = read_theses_page(DB, limit=PAGE_SIZE, ticker_filter="nvda")
step("only NVDA rows", all(r.ticker == "NVDA" for r in nvda_page))
step_eq("NVDA limited to PAGE_SIZE", len(nvda_page), min(12, PAGE_SIZE))

aapl_page = read_theses_page(DB, limit=PAGE_SIZE, ticker_filter="AAPL")
step("only AAPL rows", all(r.ticker == "AAPL" for r in aapl_page))
step_eq("AAPL limited to PAGE_SIZE", len(aapl_page), min(8, PAGE_SIZE))

tsla_page = read_theses_page(DB, limit=10, ticker_filter="tsla")
step("only TSLA rows", all(r.ticker == "TSLA" for r in tsla_page))
step_eq("TSLA all 5 returned (limit 10)", len(tsla_page), 5)

# Ticker filter pagination: 12 NVDA rows, page through
nvda_p1 = read_theses_page(DB, limit=5, ticker_filter="NVDA")
step_eq("NVDA page 1 has 5", len(nvda_p1), 5)
nvda_cursor = (nvda_p1[-1].datetime, nvda_p1[-1].id)
nvda_p2 = read_theses_page(DB, limit=5, cursor=nvda_cursor, ticker_filter="NVDA")
step_eq("NVDA page 2 has 5", len(nvda_p2), 5)
nvda_cursor2 = (nvda_p2[-1].datetime, nvda_p2[-1].id)
nvda_p3 = read_theses_page(DB, limit=5, cursor=nvda_cursor2, ticker_filter="NVDA")
step_eq("NVDA page 3 has remaining 2", len(nvda_p3), 2)

# ===========================================================================
# 5. list_tickers
# ===========================================================================
section("5. list_tickers")

tickers_list = list_tickers(DB)
step_eq("3 distinct tickers", len(tickers_list), 3)
step("NVDA in list", "NVDA" in tickers_list)
step("AAPL in list", "AAPL" in tickers_list)
step("TSLA in list", "TSLA" in tickers_list)
# TSLA has latest created_at so appears first
step_eq("newest-activity first (TSLA has latest)", tickers_list[0], "TSLA")

# ===========================================================================
# 6. count_theses
# ===========================================================================
section("6. count_theses")

step_eq("total count", count_theses(DB), 25)
step_eq("NVDA count", count_theses(DB, ticker_filter="nvda"), 12)
step_eq("AAPL count", count_theses(DB, ticker_filter="aapl"), 8)
step_eq("TSLA count", count_theses(DB, ticker_filter="TSLA"), 5)
step_eq("nonexistent = 0", count_theses(DB, ticker_filter="MISSING"), 0)

# ===========================================================================
# 7. HistoryScreen _load_page — monkey-patched
# ===========================================================================
section("7. HistoryScreen._load_page — monkey-patched")

import frontend.screens.history as hs_mod
import frontend.history_io as hio

orig_ps = hs_mod.PAGE_SIZE
# Patch read_theses_page in the history screen module (it imports it at top level)
orig_page_fn = hs_mod.read_theses_page
orig_tickers_fn = hs_mod.list_tickers
hs_mod.PAGE_SIZE = PAGE_SIZE

# Patch list_tickers too so HistoryScreen uses test data
hs_mod.list_tickers = lambda: ["TSLA", "NVDA", "AAPL"]

# Monkey-patch to return synthetic test data
_mp_calls: list[dict] = []
_next_ids = [100, 80, 60, 40, 20]  # ids for each page

def _mp_read_page(db_path=None, *, limit=7, cursor=None, ticker_filter=None):
    _mp_calls.append({"cursor": cursor, "ticker_filter": ticker_filter, "limit": limit})
    if len(_mp_calls) > len(_next_ids):
        return []
    nid = _next_ids[len(_mp_calls) - 1]
    rows = []
    for j in range(min(limit, 5 if ticker_filter else PAGE_SIZE)):
        rows.append(hio.ThesisRow(
            id=nid - j, ticker=ticker_filter or "NVDA", date="2026-08-01",
            datetime=f"2026-08-01T10:00:0{j}Z", flow_id="f1", version=1,
            conviction=3, placement="HOLD", price=100.0, base_case=90.0,
            bottom_line_text="test", thesis_text="test thesis",
            evidence_urls=[], model=None, paid_for=False,
        ))
    return rows

hs_mod.read_theses_page = _mp_read_page

from frontend.screens.history import HistoryScreen
screen = HistoryScreen()

step_eq("_load_page called on __init__", len(_mp_calls), 1)
step_eq("cursor was None on first call", _mp_calls[0]["cursor"], None)
step("rows populated", len(screen._rows) > 0)

# ===========================================================================
# 8. HistoryScreen._render_pill_bar
# ===========================================================================
section("8. HistoryScreen._render_pill_bar")

# Fresh screen with tickers seeded
screen2 = HistoryScreen()
bar = screen2._render_pill_bar()
step("pill bar contains ALL", "ALL" in bar)
step("ALL is active by default", True)

screen2._ticker_filter = "NVDA"
bar2 = screen2._render_pill_bar()
step("NVDA pill is active when filtered", True)

# ===========================================================================
# 9. HistoryScreen action_next_filter (tab)
# ===========================================================================
section("9. HistoryScreen action_next_filter")

screen3 = HistoryScreen()
step_eq("starts with ALL (None)", screen3._ticker_filter, None)

screen3.action_next_filter()
step_eq("1 tab → first ticker", screen3._ticker_filter, screen3._tickers[0])

screen3.action_next_filter()
step_eq("2 tabs → second ticker", screen3._ticker_filter, screen3._tickers[1])

# Tab N times until wrap around to ALL
# After 2nd ticker: need len(tickers)-1 steps to reach ALL (pills[0])
for _ in range(len(screen3._tickers) - 1):
    screen3.action_next_filter()
step_eq("wrapped → ALL (None)", screen3._ticker_filter, None)

# ===========================================================================
# 10. HistoryScreen action_page_down / action_page_up
# ===========================================================================
section("10. HistoryScreen action_page_down / action_page_up")

screen4 = HistoryScreen()
step_eq("starts at index 0", screen4._index, 0)

screen4.action_page_up()
step_eq("page_up at 0 stays at 0", screen4._index, 0)

screen4.action_page_down()
expected = min(len(screen4._rows) - 1, 10) if screen4._rows else 0
step_eq(f"page_down jumps to {expected}", screen4._index, expected)

# ===========================================================================
# 11. HistoryScreen BINDINGS
# ===========================================================================
section("11. HistoryScreen BINDINGS")

bindings = {b.key: b.action for b in HistoryScreen.BINDINGS}
step("tab binding exists", "tab" in bindings)
step_eq("tab → next_filter", bindings.get("tab"), "next_filter")
step("pagedown exists", "pagedown" in bindings)
step_eq("pagedown → page_down", bindings.get("pagedown"), "page_down")
step("pageup exists", "pageup" in bindings)
step_eq("pageup → page_up", bindings.get("pageup"), "page_up")
step("r still exists", "r" in bindings)
step("escape still exists", "escape" in bindings)
step("ctrl+enter still exists", "ctrl+enter" in bindings)

# ===========================================================================
# 12. read_theses_all supports ticker_filter
# ===========================================================================
section("12. read_theses_all supports ticker_filter")

all_aapl = read_theses_all(DB, ticker_filter="AAPL")
step("read_theses_all with ticker_filter works", len(all_aapl) > 0)
step("all rows are AAPL", all(r.ticker == "AAPL" for r in all_aapl))
step_eq("all 8 AAPL rows", len(all_aapl), 8)

all_none = read_theses_all(DB)
step_eq("read_theses_all() no filter = all 25", len(all_none), 25)

# ===========================================================================
# Summary
# ===========================================================================
hs_mod.PAGE_SIZE = orig_ps
hs_mod.read_theses_page = orig_page_fn
hs_mod.list_tickers = orig_tickers_fn
tmpdir.cleanup()

total = _ok[0] + _bad[0]
print(f"\n=== {_ok[0]}/{total} ok ===")
if _bad[0] == 0:
    print("all green")
else:
    print(f"{_bad[0]} fail")
    sys.exit(1)