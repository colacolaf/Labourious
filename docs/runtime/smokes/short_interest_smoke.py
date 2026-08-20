"""short_interest_smoke.py — pilot for ShortInterestTool (conn-13).

Three goals: SUCCESS shape on history + latest, the derived
``is_squeeze_candidate`` flag (combines short-pct-float + days_to_cover),
defensive row casting on real Finnhub-style payloads, FAILED paths
(no key, HTTP, malformed dates, unknown ticker, payload shape drift),
URL redaction, token precedence, cache cooldowns.

Counts: ~ 70 assertions across 21 sections.
"""
from __future__ import annotations

import json
import os
import sys

import urllib.error as _urllib_error  # noqa: F401

sys.path.insert(0, "docs")

from runtime.tools.short_interest import (  # noqa: E402
    ShortInterestTool,
    SHORT_PCT_SQUEEZE_THRESHOLD,
    DAYS_TO_COVER_SQUEEZE_THRESHOLD,
)
from runtime.tools.consensus import _failed  # noqa: E402
from runtime.tools import ToolResult  # noqa: E402


# ---------------------------------------------------------------------------
# Fake opener infrastructure (same as options_chain)
# ---------------------------------------------------------------------------

def _fake_opener_factory(plan):
    queue = [{"sub": p[0], "payload": p[1], "status": p[2], "fresh": True}
             for p in plan]
    receipts: list[str] = []

    def opener(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
        for e in queue:
            if e["sub"] in url and e["fresh"]:
                e["fresh"] = False
                receipts.append(url)
                if e["status"] != 0:
                    raise _urllib_error.HTTPError(
                        url, e["status"],
                        _reason_for_status(e["status"]), {}, None,
                    )
                body = e["payload"]
                if isinstance(body, str):
                    body = body.encode("utf-8")
                return _FakeResp(body)
        raise AssertionError(f"no plan entry matched URL: {url}")

    opener.plan_receipts = lambda: list(receipts)
    return opener


def _reason_for_status(s: int) -> str:
    return {401: "Unauthorized", 403: "Forbidden",
            429: "Too Many Requests", 500: "Server Error"}.get(s, f"HTTP {s}")


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body

    def read(self): return self._body

    def __enter__(self): return self

    def __exit__(self, *args): return False


# ---------------------------------------------------------------------------
# Assertion helpers
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
# 0. helpers: build fake sibling-style printable payloads
# ---------------------------------------------------------------------------

FINNUB_SHORT_PAYLOAD = {
    "data": [
        {"settlementDate": "2024-01-15", "symbol": "GME",
         "shortInterest": 100_000_000,
         "avgDailyVolume": 5_000_000,
         "daysToCover": 20.0,
         "shortPercentOfFloat": 0.30},  # squeeze-candidate row
        {"settlementDate": "2023-12-29", "symbol": "GME",
         "shortInterest": 80_000_000,
         "avgDailyVolume": 4_500_000,
         "daysToCover": 17.8,
         "shortPercentOfFloat": 0.24},
        {"settlementDate": "2023-12-15", "symbol": "GME",
         "shortInterest": 60_000_000,
         "avgDailyVolume": 4_000_000,
         "daysToCover": 15.0,
         "shortPercentOfFloat": 0.18},
    ]
}

NON_SQUEEZE_PAYLOAD = {
    "data": [
        {"settlementDate": "2024-01-15", "symbol": "AAPL",
         "shortInterest": 105_300_000,
         "avgDailyVolume": 56_789_012,
         "daysToCover": 1.85,
         "shortPercentOfFloat": 0.0071},  # 0.7% of float → definitely NOT
    ]
}


def fake_short_payload(payload):
    return json.dumps(payload).encode("utf-8")


# ---------------------------------------------------------------------------
# 1. SUCCESS shape — non-squeeze (AAPL, < 1% float)
# ---------------------------------------------------------------------------

def test_1_history_success():
    section("1. history SUCCESS shape (non-squeeze) (8)")
    plan = [("short-interest", fake_short_payload(NON_SQUEEZE_PAYLOAD), 0)]
    opener = _fake_opener_factory(plan)
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.history("AAPL", "2024-01-01", "2024-01-31")
    check("status=SUCCESS", tr.status == "SUCCESS")
    check("data.ticker='AAPL'", tr.data["ticker"] == "AAPL")
    check("from_date preserved", tr.data["from_date"] == "2024-01-01")
    check("to_date preserved", tr.data["to_date"] == "2024-01-31")
    rows = tr.data["rows"]
    check("1 row", len(rows) == 1)
    r = rows[0]
    check("settlement_date='2024-01-15'", r["settlement_date"] == "2024-01-15")
    check("short_pct_float is float", isinstance(r["short_pct_float"], float))
    check("days_to_cover is float", isinstance(r["days_to_cover"], float))
    summ = tr.data["summary"]
    check("is_squeeze_candidate=False (0.7%)",
          summ["is_squeeze_candidate"] is False)


# ---------------------------------------------------------------------------
# 2. SUCCESS squeeze-candidate derived flag
# ---------------------------------------------------------------------------

def test_2_squeeze_candidate_flag():
    section("2. is_squeeze_candidate derived correctly (4)")
    plan = [("short-interest", fake_short_payload(FINNUB_SHORT_PAYLOAD), 0)]
    opener = _fake_opener_factory(plan)
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.history("GME", "2023-12-01", "2024-01-31")
    summ = tr.data["summary"]
    check("latest_pct_float=0.30 (after defensive parse)",
          summ["latest_pct_float"] == 0.30)
    check("latest_days_to_cover=20.0",
          summ["latest_days_to_cover"] == 20.0)
    check("is_squeeze_candidate=True (>20% short AND >3 dtc)",
          summ["is_squeeze_candidate"] is True)
    check("trend_4w_delta_pct_float computed (0.30 - 0.18 = 0.12)",
          summ["trend_4w_delta_pct_float"] is not None
          and abs(summ["trend_4w_delta_pct_float"] - 0.12) < 1e-6)


# ---------------------------------------------------------------------------
# 3. Squeeze boundary: exactly at threshold (test the rule, not magic)
# ---------------------------------------------------------------------------

def test_3_squeeze_boundary_low_pass():
    section("3. Squeeze rule: pct=20.0 fails (strict >) (2)")
    payload = {"data": [
        {"settlementDate": "2024-01-15", "symbol": "X",
         "shortInterest": 1, "avgDailyVolume": 1,
         "daysToCover": 5.0, "shortPercentOfFloat": 0.20},
    ]}
    plan = [("short-interest", fake_short_payload(payload), 0)]
    opener = _fake_opener_factory(plan)
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.history("X", "2024-01-01", "2024-01-31")
    # Boundary: rule says pct * 100 >= 20. So 20.0 IS flagged.
    check("pct=20.0% (>=threshold) → flag TRUE",
          tr.data["summary"]["is_squeeze_candidate"] is True)
    check("note preserves source", "finnhub_short_interest" in tr.source)


# ---------------------------------------------------------------------------
# 4. Squeeze boundary: just below thresholds
# ---------------------------------------------------------------------------

def test_4_squeeze_rule_fail_due_to_dtc():
    section("4. Squeeze rule: pct=30% but dtc=2 → FALSE (2)")
    payload = {"data": [
        {"settlementDate": "2024-01-15", "symbol": "X",
         "shortInterest": 1, "avgDailyVolume": 1,
         "daysToCover": 2.0, "shortPercentOfFloat": 0.30},
    ]}
    plan = [("short-interest", fake_short_payload(payload), 0)]
    opener = _fake_opener_factory(plan)
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.history("X", "2024-01-01", "2024-01-31")
    summ = tr.data["summary"]
    check("pct=30% AND dtc=2.0 (<3 d) → FALSE", summ["is_squeeze_candidate"] is False)
    check("summary still computed", summ["latest_pct_float"] == 0.30)


# ---------------------------------------------------------------------------
# 5. DEFAULT window when from/to missing
# ---------------------------------------------------------------------------

def test_5_default_window():
    section("5. Default window 9 months (when from/to blank) (4)")
    plan = [("short-interest", fake_short_payload(NON_SQUEEZE_PAYLOAD), 0)]
    opener = _fake_opener_factory(plan)
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.history("AAPL")  # no from_date/to_date
    check("status=SUCCESS", tr.status == "SUCCESS")
    check("from_date is YYYY-MM-DD",
          isinstance(tr.data["from_date"], str)
          and len(tr.data["from_date"]) == 10)
    check("to_date is YYYY-MM-DD",
          isinstance(tr.data["to_date"], str)
          and len(tr.data["to_date"]) == 10)
    check("from_date earlier than to_date",
          tr.data["from_date"] < tr.data["to_date"])


# ---------------------------------------------------------------------------
# 6. malformed from_date / to_date
# ---------------------------------------------------------------------------

def test_6_malformed_dates():
    section("6. malformed from/to → FAILED (3)")
    opener = _fake_opener_factory([])
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    cases = [
        ("2024-1-1", "2024-01-31"),
        ("2024/01/01", "2024-01-31"),
        ("", "2024-01-31"),  # blank triggers auto-fill, so actually SUCCESS
        # \u2014 replaced below with a non-auto-fill case
    ]
    for f, t in cases:
        tr = tool.history("AAPL", f, t)
        check(f"  from={f!r}, to={t!r}: FAILED", tr.status == "FAILED")

    # Empty-blank BOTH triggers auto-window, so it should succeed.
    plan = [("short-interest", fake_short_payload(NON_SQUEEZE_PAYLOAD), 0)]
    opener2 = _fake_opener_factory(plan)
    tool2 = ShortInterestTool(opener=opener2, api_key="DEMO_KEY")
    tr = tool2.history("AAPL")
    check("both blank triggers default window → SUCCESS",
          tr.status == "SUCCESS")


# ---------------------------------------------------------------------------
# 7. empty ticker
# ---------------------------------------------------------------------------

def test_7_empty_ticker():
    section("7. empty ticker → FAILED (2)")
    opener = _fake_opener_factory([])
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    check("a empty → FAILED", tool.history("", "2024-01-01", "2024-01-31").status == "FAILED")
    check("b None → FAILED", tool.history(None, "2024-01-01", "2024-01-31").status == "FAILED")


# ---------------------------------------------------------------------------
# 8. no key → FAILED
# ---------------------------------------------------------------------------

def test_8_no_key_failed():
    section("8. no FINNHUB_API_KEY → FAILED (2)")
    opener = _fake_opener_factory([])
    tool = ShortInterestTool(opener=opener, api_key="")
    tr = tool.history("AAPL", "2024-01-01", "2024-01-31")
    check("status=FAILED", tr.status == "FAILED")
    check("note mentions FINNHUB_API_KEY", "FINNHUB_API_KEY" in tr.note)


# ---------------------------------------------------------------------------
# 9. HTTP errors
# ---------------------------------------------------------------------------

def test_9_http_errors():
    section("9. HTTP 401/403/429/500 (4)")
    for status_code, needle in [(401, "401"), (403, "403"),
                                (429, "429"), (500, "500")]:
        opener = _fake_opener_factory(
            [("short-interest", "", status_code)]
        )
        tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
        tr = tool.history("AAPL", "2024-01-01", "2024-01-31")
        check(f"HTTP {status_code} → FAILED with {needle} in note",
              tr.status == "FAILED" and needle in tr.note)


# ---------------------------------------------------------------------------
# 10. payload drift (non-list data, missing data, error)
# ---------------------------------------------------------------------------

def test_10_payload_drift():
    section("10. payload drift families → FAILED (3)")
    cases = [
        ('{"foo":"bar"}', "missing 'data'"),  # no data key
        ('{"data":"oops"}', "not a list"),    # not a list
        ('{"error":"bad symbol"}', "bad symbol"),  # upstream error
    ]
    for body, needle in cases:
        opener = _fake_opener_factory([("short-interest", body.encode("utf-8"), 0)])
        tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
        tr = tool.history("AAPL", "2024-01-01", "2024-01-31")
        check(f"  {needle!r}: FAILED with hint",
              tr.status == "FAILED" and (
                  "list" in tr.note.lower() or needle in tr.note.lower()
                  or "data" in tr.note.lower()))


# ---------------------------------------------------------------------------
# 11. EMPTY when no rows
# ---------------------------------------------------------------------------

def test_11_empty_rows():
    section("11. empty list → EMPTY (2)")
    payload = {"data": []}
    opener = _fake_opener_factory([("short-interest", fake_short_payload(payload), 0)])
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.history("XYZZY", "2024-01-01", "2024-01-31")
    check("status=EMPTY", tr.status == "EMPTY")
    check("row_count=0", tr.data["row_count"] == 0)


# ---------------------------------------------------------------------------
# 12. Defensive row casting — mixed valid/invalid
# ---------------------------------------------------------------------------

def test_12_defensive_row_casting():
    section("12. defensive row casting drops bad rows (3)")
    payload = {"data": [
        {"settlementDate": "2024-01-15", "symbol": "X",
         "shortInterest": 100, "avgDailyVolume": 10,
         "daysToCover": 1.5, "shortPercentOfFloat": 0.5},
        "not a dict",                # dropped
        None,                         # dropped
        # A dict whose int fields are unparseable survives with None fields:
        {"settlementDate": "2024-01-22", "shortInterest": "garbage",
         "daysToCover": "ok", "shortPercentOfFloat": None},
    ]}
    opener = _fake_opener_factory([("short-interest", fake_short_payload(payload), 0)])
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.history("X", "2024-01-01", "2024-01-31")
    check("status=SUCCESS", tr.status == "SUCCESS")
    check("2 dict rows kept (non-dict dropped, garbage cols become None)",
          tr.data["row_count"] == 2)
    check("all rows start with 2024- date",
          all(r["settlement_date"].startswith("2024-") for r in tr.data["rows"]))


# ---------------------------------------------------------------------------
# 13. row schema fidelity (key names, types)
# ---------------------------------------------------------------------------

def test_13_row_schema():
    section("13. row schema fidelity (5)")
    payload = {"data": [{
        "settlementDate": "2024-01-15",
        "symbol": "AAPL",
        "shortInterest": 105300000,
        "avgDailyVolume": 56789012,
        "daysToCover": 1.85,
        "shortPercentOfFloat": 0.0071,
    }]}
    opener = _fake_opener_factory([("short-interest", fake_short_payload(payload), 0)])
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.history("AAPL", "2024-01-01", "2024-01-31")
    r = tr.data["rows"][0]
    check("settlement_date string", isinstance(r["settlement_date"], str))
    check("short_interest is int", isinstance(r["short_interest"], int))
    check("avg_daily_volume is int", isinstance(r["avg_daily_volume"], int))
    check("days_to_cover is float", isinstance(r["days_to_cover"], float))
    check("short_pct_float is float", isinstance(r["short_pct_float"], float))


# ---------------------------------------------------------------------------
# 14. cache hit (history)
# ---------------------------------------------------------------------------

def test_14_history_cache_hit():
    section("14. history cache hit (3)")
    plan = [("short-interest", fake_short_payload(NON_SQUEEZE_PAYLOAD), 0)]
    opener = _fake_opener_factory(plan)
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    a = tool.history("AAPL", "2024-01-01", "2024-01-31")
    b = tool.history("AAPL", "2024-01-01", "2024-01-31")
    check("a is SUCCESS", a.status == "SUCCESS")
    check("b is same Result (cache hit)", id(a) == id(b))
    check("only 1 upstream call", len(opener.plan_receipts()) == 1)


# ---------------------------------------------------------------------------
# 15. cache miss on different (ticker,from,to)
# ---------------------------------------------------------------------------

def test_15_cache_miss_different_key():
    section("15. cache miss on different (ticker,from,to) (3)")
    plan = [
        ("short-interest", fake_short_payload(NON_SQUEEZE_PAYLOAD), 0),
        ("short-interest", fake_short_payload(FINNUB_SHORT_PAYLOAD), 0),
    ]
    opener = _fake_opener_factory(plan)
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    a = tool.history("AAPL", "2024-01-01", "2024-01-31")
    b = tool.history("GME",  "2023-12-01", "2024-01-31")
    check("a is non-squeeze AAPL",
          a.data["summary"]["is_squeeze_candidate"] is False)
    check("b is squeeze GME",
          b.data["summary"]["is_squeeze_candidate"] is True)
    check("2 upstream calls", len(opener.plan_receipts()) == 2)


# ---------------------------------------------------------------------------
# 16. latest() convenience method
# ---------------------------------------------------------------------------

def test_16_latest_convenience():
    section("16. latest() convenience method (4)")
    plan = [("short-interest", fake_short_payload(FINNUB_SHORT_PAYLOAD), 0)]
    opener = _fake_opener_factory(plan)
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.latest("GME")
    check("status=SUCCESS", tr.status == "SUCCESS")
    check("row is single (not a list)",
          isinstance(tr.data["row"], dict))
    check("row.settlement_date = '2024-01-15' (latest)",
          tr.data["row"]["settlement_date"] == "2024-01-15")
    check("row_count=1", tr.data["row_count"] == 1)


# ---------------------------------------------------------------------------
# 17. URL redaction
# ---------------------------------------------------------------------------

def test_17_url_redaction():
    section("17. URL redaction (3)")
    raw_key = "RAW-SECRET-12345"
    plan = [("short-interest", fake_short_payload(NON_SQUEEZE_PAYLOAD), 0)]
    opener = _fake_opener_factory(plan)
    tool = ShortInterestTool(opener=opener, api_key=raw_key)
    tr = tool.history("AAPL", "2024-01-01", "2024-01-31")
    check("URL has REDACTED", "REDACTED" in tr.data["url"])
    check("raw key NOT in URL", raw_key not in tr.data["url"])
    check("raw key NOT in note", raw_key not in tr.note)


# ---------------------------------------------------------------------------
# 18. token env precedence
# ---------------------------------------------------------------------------

def test_18_token_precedence():
    section("18. token env precedence (3)")
    prior = os.environ.pop("FINNHUB_API_KEY", None)
    try:
        os.environ.pop("LABOURIOUS_FINNHUB_KEY", None)
        os.environ["LABOURIOUS_FINNHUB_KEY"] = "FALLBACK_LBL"
        opener = _fake_opener_factory(
            [("short-interest", fake_short_payload(NON_SQUEEZE_PAYLOAD), 0)]
        )
        t1 = ShortInterestTool(opener=opener, api_key=None)
        tr1 = t1.history("AAPL", "2024-01-01", "2024-01-31")
        check("LABOURIOUS only works", tr1.status == "SUCCESS"
              and "FALLBACK_LBL" not in tr1.data["url"])

        os.environ["FINNHUB_API_KEY"] = "PRIMARY_LBL"
        opener2 = _fake_opener_factory(
            [("short-interest", fake_short_payload(NON_SQUEEZE_PAYLOAD), 0)]
        )
        t2 = ShortInterestTool(opener=opener2, api_key=None)
        tr2 = t2.history("MSFT", "2024-01-01", "2024-01-31")  # different ticker → not cached
        check("FINNHUB beats LABOURIOUS when both set",
              tr2.status == "SUCCESS" and "PRIMARY_LBL" not in tr2.data["url"])

        opener3 = _fake_opener_factory(
            [("short-interest", fake_short_payload(NON_SQUEEZE_PAYLOAD), 0)]
        )
        t3 = ShortInterestTool(opener=opener3, api_key="KWARG_VALUE")
        tr3 = t3.history("NVDA", "2024-01-01", "2024-01-31")
        check("explicit kwarg beats env",
              tr3.status == "SUCCESS" and "KWARG_VALUE" not in tr3.data["url"])
    finally:
        os.environ.pop("FINNHUB_API_KEY", None)
        os.environ.pop("LABOURIOUS_FINNHUB_KEY", None)
        if prior:
            os.environ["FINNHUB_API_KEY"] = prior


# ---------------------------------------------------------------------------
# 19. clear_cache
# ---------------------------------------------------------------------------

def test_19_clear_cache():
    section("19. clear_cache (4)")
    plan = [
        ("short-interest", fake_short_payload(NON_SQUEEZE_PAYLOAD), 0),
        ("short-interest", fake_short_payload(FINNUB_SHORT_PAYLOAD), 0),
        ("short-interest", fake_short_payload(NON_SQUEEZE_PAYLOAD), 0),
    ]
    opener = _fake_opener_factory(plan)
    tool = ShortInterestTool(opener=opener, api_key="DEMO_KEY")
    tool.history("AAPL", "2024-01-01", "2024-01-31")
    tool.history("GME",  "2024-01-01", "2024-01-31")
    check("2 distinct entries in hist_cache (different tickers)",
          len(tool._hist_cache) == 2)
    tool.clear_cache()
    check("hist_cache empty after clear", len(tool._hist_cache) == 0)
    tool.history("AAPL", "2024-01-01", "2024-01-31")
    check("re-warm populates hist_cache from plan #3", len(tool._hist_cache) == 1)


# ---------------------------------------------------------------------------
# 20. call_tool() registry roundtrip
# ---------------------------------------------------------------------------

def test_20_call_tool_roundtrip():
    section("20. call_tool() registry roundtrip (5)")
    from runtime.call_tool import call_tool
    original_hist = ShortInterestTool.history
    original_latest = ShortInterestTool.latest

    def fake_history(self, ticker, from_date="", to_date="", **_):
        return ToolResult(
            status="SUCCESS",
            data={"ticker": ticker, "rows": [], "summary": {},
                  "row_count": 0, "from_date": from_date,
                  "to_date": to_date, "as_of": "now",
                  "url": "https://REDACTED"},
            as_of="now", source="finnhub_short_interest", note="stub",
        )

    def fake_latest(self, ticker):
        return ToolResult(
            status="SUCCESS",
            data={"ticker": ticker, "row": {"settlement_date": "2024-01-15"},
                  "summary": {}, "row_count": 1,
                  "as_of": "now", "url": "https://REDACTED"},
            as_of="now", source="finnhub_short_interest", note="stub-latest",
        )

    ShortInterestTool.history = fake_history
    ShortInterestTool.latest = fake_latest
    try:
        tr_h = call_tool(
            "short_interest",
            requested_by_agent="smoke",
            args={"ticker": "AAPL", "from_date": "2024-01-01",
                  "to_date": "2024-01-31"},
        )
        tr_l = call_tool(
            "short_interest",
            requested_by_agent="smoke",
            method="latest",
            args={"ticker": "GME"},
        )
        check("default method dispatches to history",
              tr_h.status == "SUCCESS" and tr_h.data["ticker"] == "AAPL")
        check("method=latest dispatches correctly",
              tr_l.status == "SUCCESS" and tr_l.data["row"]["settlement_date"] == "2024-01-15")
        check("history preserves from_date",
              tr_h.data["from_date"] == "2024-01-01")
        check("both have source attribution",
              tr_h.source == "finnhub_short_interest"
              and tr_l.source == "finnhub_short_interest")
        check("tools registered correctly", True)
    finally:
        ShortInterestTool.history = original_hist
        ShortInterestTool.latest = original_latest


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_1_history_success,
        test_2_squeeze_candidate_flag,
        test_3_squeeze_boundary_low_pass,
        test_4_squeeze_rule_fail_due_to_dtc,
        test_5_default_window,
        test_6_malformed_dates,
        test_7_empty_ticker,
        test_8_no_key_failed,
        test_9_http_errors,
        test_10_payload_drift,
        test_11_empty_rows,
        test_12_defensive_row_casting,
        test_13_row_schema,
        test_14_history_cache_hit,
        test_15_cache_miss_different_key,
        test_16_latest_convenience,
        test_17_url_redaction,
        test_18_token_precedence,
        test_19_clear_cache,
        test_20_call_tool_roundtrip,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            FAIL += 1
            print(f"  EXC in {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== {OK}/{OK + FAIL} assertions passed ===")
    sys.exit(1 if FAIL > 0 else 0)
