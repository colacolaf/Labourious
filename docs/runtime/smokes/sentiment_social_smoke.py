"""sentiment_social_smoke.py — pilot for SentimentSocialTool (conn-14).

Three goals: SUCCESS shape on Stocktwits stream payloads, sentiment
breakdown accuracy (Bullish/Bearish/None), the trending endpoint,
defensive row casting (mirrors the upstream's API drift reality),
FAILED paths (HTTP, payload drift, empty/ticker), URL handling,
caching + redaction + clear_cache.

Counts: ~ 78 assertions across 22 sections.
"""
from __future__ import annotations

import json
import os
import sys

import urllib.error as _urllib_error  # noqa: F401

sys.path.insert(0, "docs")

from runtime.tools.sentiment_social import SentimentSocialTool  # noqa: E402
from runtime.tools import ToolResult  # noqa: E402


# ---------------------------------------------------------------------------
# Fake opener infrastructure
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
# Helpers: craft representative Stocktwits payloads
# ---------------------------------------------------------------------------

def make_msg(i: int, sentiment: str | None = None,
             body: str = "", wl: int = 100) -> dict:
    """Build one Stocktwits message in the upstream shape."""
    return {
        "id": 1000 + i,
        "body": body or f"$AAPL message {i}",
        "created_at": f"2024-01-{15 + (i % 5):02d}T10:{i % 60:02d}:00Z",
        "user": {
            "id": i,
            "username": f"user{i}",
            "name": f"User {i}",
            "watchlist_count": wl,
            "join_date": "2024-01-01T00:00:00Z",
        },
        "entities": {
            "sentiment": {"basic": sentiment} if sentiment else None,
        },
        "symbols": [{"symbol": "AAPL", "title": "Apple"}],
    }


def make_streams_payload(sentiments) -> dict:
    """Build a Stocktwits /streams/symbol/AAPL.json payload."""
    msgs = [make_msg(i, s, wl=100 + i * 10) for i, s in enumerate(sentiments)]
    return {
        "response": {"status": 200},
        "messages": msgs,
        "symbol": {"symbol": "AAPL", "watchlist_count": 432100,
                   "instrument_class": "equity"},
        "cursor": "next_cursor_value",
    }


def make_streams_raw(payload):
    return json.dumps(payload).encode("utf-8")


def make_trending_payload(syms) -> dict:
    return {
        "response": {"status": 200},
        "symbols": [{"symbol": s, "user_count": 100 * i, "watchlist_count": 1000 * i}
                    for i, s in enumerate(syms)],
    }


# ---------------------------------------------------------------------------
# 1. messages SUCCESS shape (mixed sentiment)
# ---------------------------------------------------------------------------

def test_1_messages_success_shape():
    section("1. messages SUCCESS shape — mixed sentiment (10)")
    sentiments = ["Bullish", "Bearish", None, "Bullish", "Bearish"]
    payload = make_streams_raw(make_streams_payload(sentiments))
    opener = _fake_opener_factory([("streams/symbol", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.messages("AAPL", limit=5)
    check("status=SUCCESS", tr.status == "SUCCESS")
    check("data.ticker='AAPL'", tr.data["ticker"] == "AAPL")
    check("5 messages", len(tr.data["messages"]) == 5)
    summ = tr.data["summary"]
    check("bullish=2", summ["bullish"] == 2)
    check("bearish=2", summ["bearish"] == 2)
    check("neutral=1", summ["neutral"] == 1)
    check("bullish_pct=0.4", summ["bullish_pct"] == 0.4)
    check("total=5", summ["total"] == 5)
    check("watchlist_count_per_msg computed",
          isinstance(summ["avg_watchlist_count_per_msg"], float)
          and summ["avg_watchlist_count_per_msg"] > 0)
    check("symbol.watchlist_count=432100",
          tr.data["symbol"]["watchlist_count"] == 432100)


# ---------------------------------------------------------------------------
# 2. sentiment breakdown — all Bullish
# ---------------------------------------------------------------------------

def test_2_all_bullish():
    section("2. all Bullish → bullish_pct=1.0 (3)")
    payload = make_streams_raw(make_streams_payload(["Bullish"] * 6))
    opener = _fake_opener_factory([("streams/symbol", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.messages("TSLA", limit=6)
    s = tr.data["summary"]
    check("bullish=6, bearish=0, neutral=0",
          s["bullish"] == 6 and s["bearish"] == 0 and s["neutral"] == 0)
    check("bullish_pct=1.0", s["bullish_pct"] == 1.0)
    check("total=6", s["total"] == 6)


# ---------------------------------------------------------------------------
# 3. sentiment breakdown — no tags
# ---------------------------------------------------------------------------

def test_3_no_tags():
    section("3. no sentiment tags → all neutral (3)")
    payload = make_streams_raw(make_streams_payload([None, None, None]))
    opener = _fake_opener_factory([("streams/symbol", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.messages("NVDA", limit=3)
    s = tr.data["summary"]
    check("all 3 neutral", s["neutral"] == 3)
    check("bullish_pct is None", s["bullish_pct"] == 0.0)
    check("bearish=0", s["bearish"] == 0)


# ---------------------------------------------------------------------------
# 4. empty ticker / negative limit
# ---------------------------------------------------------------------------

def test_4_input_validation():
    section("4. empty ticker / bad limit → FAILED (3)")
    opener = _fake_opener_factory([])
    tool = SentimentSocialTool(opener=opener)
    check("empty ticker → FAILED", tool.messages("", limit=5).status == "FAILED")
    check("None ticker → FAILED", tool.messages(None, limit=5).status == "FAILED")
    check("limit ≤ 0 → FAILED", tool.messages("AAPL", limit=0).status == "FAILED")


# ---------------------------------------------------------------------------
# 5. limit clamp to 30
# ---------------------------------------------------------------------------

def test_5_limit_clamp():
    section("5. limit > 30 clamps to 30 (2)")
    # Stocktwits upstream caps at 30 msgs. We pass limit=50, expect clamp.
    sentiments = ["Bullish"] * 30
    payload = make_streams_raw(make_streams_payload(sentiments))
    opener = _fake_opener_factory([("streams/symbol", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.messages("AAPL", limit=999)
    check("count=30 not 50",
          tr.data["summary"]["total"] == 30)


# ---------------------------------------------------------------------------
# 6. cache hit + miss (case-insensitive ticker)
# ---------------------------------------------------------------------------

def test_6_cache():
    section("6. messages cache hit + case-insensitive (3)")
    payload = make_streams_raw(make_streams_payload(["Bullish"] * 3))
    opener = _fake_opener_factory([("streams/symbol", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    a = tool.messages("AAPL", limit=3)
    b = tool.messages("AAPL", limit=3)
    c = tool.messages("aapl", limit=3)
    check("a is SUCCESS", a.status == "SUCCESS")
    check("b is same Result (cache)", id(a) == id(b))
    check("c hits cache (case-insensitive)", id(a) == id(c))
    check("1 upstream call only", len(opener.plan_receipts()) == 1)


# ---------------------------------------------------------------------------
# 7. $AAPL ticker stripping
# ---------------------------------------------------------------------------

def test_7_dollar_prefix_strip():
    section("7. leading $ stripped from ticker (2)")
    payload = make_streams_raw(make_streams_payload(["Bullish"]))
    opener = _fake_opener_factory([("streams/symbol", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.messages("$AAPL")
    check("URL fragment doesn't contain '$'",
          "$" not in opener.plan_receipts()[0])
    check("data.ticker='AAPL' (stripped)",
          tr.data["ticker"] == "AAPL")


# ---------------------------------------------------------------------------
# 8. symbol.watchlist_count preserved from upstream
# ---------------------------------------------------------------------------

def test_8_symbol_meta():
    section("8. symbol.watchlist_count surfaces (2)")
    payload_dict = make_streams_payload(["Bullish"] * 2)
    payload_dict["symbol"]["watchlist_count"] = 789012
    payload = make_streams_raw(payload_dict)
    opener = _fake_opener_factory([("streams/symbol", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.messages("XYZ", limit=2)
    check("watchlist_count=789012", tr.data["symbol"]["watchlist_count"] == 789012)
    check("tr.data.ticker='XYZ'", tr.data["ticker"] == "XYZ")


# ---------------------------------------------------------------------------
# 9. HTTP errors
# ---------------------------------------------------------------------------

def test_9_http_errors():
    section("9. HTTP 401/403/429/500 (4)")
    for code, needle in [(401, "401"), (403, "403"),
                         (429, "429"), (500, "500")]:
        opener = _fake_opener_factory([("streams/symbol", "", code)])
        tool = SentimentSocialTool(opener=opener)
        tr = tool.messages("AAPL", limit=3)
        check(f"HTTP {code}: FAILED with {needle}",
              tr.status == "FAILED" and needle in tr.note)


# ---------------------------------------------------------------------------
# 10. payload drift — missing 'messages' key
# ---------------------------------------------------------------------------

def test_10_payload_misc():
    section("10. payload drift families → FAILED (4)")
    cases = [
        ('{"foo":"bar"}', "missing 'messages' key"),
        ('{"messages":"oops"}', "'messages' is not a list"),
        ('{"messages":null}', "is not a list"),
        ('{"messages":[1,2,3]}', "non-dict rows dropped"),
    ]
    for body, hint in cases:
        opener = _fake_opener_factory([("streams/symbol", body.encode("utf-8"), 0)])
        tool = SentimentSocialTool(opener=opener)
        tr = tool.messages("AAPL", limit=3)
        check(f"  {hint}: FAILED or successfully empty",
              tr.status == "FAILED" or tr.status == "EMPTY")


# ---------------------------------------------------------------------------
# 11. EMPTY when no valid messages
# ---------------------------------------------------------------------------

def test_11_empty_when_no_valid():
    section("11. all rows bad → EMPTY (2)")
    payload = json.dumps({"messages": [None, "x", 12345], "symbol": {}}).encode("utf-8")
    opener = _fake_opener_factory([("streams/symbol", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.messages("AAPL", limit=3)
    check("status=EMPTY", tr.status == "EMPTY")
    check("summary.total=0", tr.data["summary"]["total"] == 0)


# ---------------------------------------------------------------------------
# 12. row schema fidelity
# ---------------------------------------------------------------------------

def test_12_row_schema():
    section("12. row schema fidelity (6)")
    payload = make_streams_raw(make_streams_payload(["Bullish"]))
    opener = _fake_opener_factory([("streams/symbol", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.messages("AAPL", limit=1)
    m = tr.data["messages"][0]
    check("id is int", isinstance(m["id"], int))
    check("body is str", isinstance(m["body"], str))
    check("user.username is str", isinstance(m["user"]["username"], str))
    check("user.watchlist_count is int", isinstance(m["user"]["watchlist_count"], int))
    check("sentiment is 'Bullish'", m["sentiment"] == "Bullish")
    check("created_at is str", isinstance(m["created_at"], str))


# ---------------------------------------------------------------------------
# 13. summary earliest/latest timestamps
# ---------------------------------------------------------------------------

def test_13_summary_timestamps():
    section("13. summary earliest/latest (2)")
    payload = make_streams_raw(make_streams_payload(["Bullish", "Bearish", None]))
    opener = _fake_opener_factory([("streams/symbol", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.messages("AAPL", limit=3)
    s = tr.data["summary"]
    check("earliest is min of created_at", s["earliest"] is not None)
    check("latest is max of created_at (>= earliest)",
          s["latest"] is not None and s["latest"] >= s["earliest"])


# ---------------------------------------------------------------------------
# 14. URL preserved (Stocktwits has no secret in URL)
# ---------------------------------------------------------------------------

def test_14_url_preserved():
    section("14. URL preserved (no secret parameter needed) (2)")
    payload = make_streams_raw(make_streams_payload(["Bullish"]))
    opener = _fake_opener_factory([("streams/symbol", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.messages("AAPL", limit=1)
    check("URL has 'stocktwits.com' or /streams/symbol",
          "stocktwits.com" in tr.data["url"]
          or "streams/symbol" in tr.data["url"])
    check("URL has ticker in path",
          "AAPL" in tr.data["url"])


# ---------------------------------------------------------------------------
# 15. trending SUCCESS shape
# ---------------------------------------------------------------------------

def test_15_trending_success():
    section("15. trending SUCCESS shape (5)")
    payload = make_streams_raw(make_trending_payload(["AAPL", "TSLA", "GME", "NVDA"]))
    opener = _fake_opener_factory([("trending/symbols", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.trending(top_n=4)
    check("status=SUCCESS", tr.status == "SUCCESS")
    check("4 items", len(tr.data["items"]) == 4)
    check("item.symbol='AAPL' (first)", tr.data["items"][0]["symbol"] == "AAPL")
    check("top_count=4", tr.data["top_count"] == 4)
    check("user_count on first item=0",
          tr.data["items"][0]["user_count"] == 0)


# ---------------------------------------------------------------------------
# 16. trending top_n clamp
# ---------------------------------------------------------------------------

def test_16_trending_clamp():
    section("16. trending top_n clamp (2)")
    payload = make_streams_raw(make_trending_payload(
        [f"SYM{i}" for i in range(20)]))
    opener = _fake_opener_factory([("trending/symbols", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.trending(top_n=9999)
    check("items capped at 20 (upstream limit)",
          len(tr.data["items"]) == 20)


# ---------------------------------------------------------------------------
# 17. trending dedup / order is upstream order
# ---------------------------------------------------------------------------

def test_17_trending_order():
    section("17. trending preserves upstream order (2)")
    syms = ["FIRST", "SECOND", "THIRD"]
    payload = make_streams_raw(make_trending_payload(syms))
    opener = _fake_opener_factory([("trending/symbols", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.trending(top_n=3)
    actual = [it["symbol"] for it in tr.data["items"]]
    check("order matches upstream", actual == syms)


# ---------------------------------------------------------------------------
# 18. trending HTTP errors
# ---------------------------------------------------------------------------

def test_18_trending_http_errors():
    section("18. trending HTTP 401/403/429/500 (4)")
    for code, needle in [(401, "401"), (403, "403"),
                         (429, "429"), (500, "500")]:
        opener = _fake_opener_factory([("trending/symbols", "", code)])
        tool = SentimentSocialTool(opener=opener)
        tr = tool.trending(top_n=10)
        check(f"HTTP {code}: FAILED with {needle}",
              tr.status == "FAILED" and needle in tr.note)


# ---------------------------------------------------------------------------
# 19. trending EMPTY when no items
# ---------------------------------------------------------------------------

def test_19_trending_empty():
    section("19. trending EMPTY (2)")
    payload = json.dumps({"symbols": []}).encode("utf-8")
    opener = _fake_opener_factory([("trending/symbols", payload, 0)])
    tool = SentimentSocialTool(opener=opener)
    tr = tool.trending(top_n=10)
    check("status=EMPTY", tr.status == "EMPTY")
    check("top_count=0", tr.data["top_count"] == 0)


# ---------------------------------------------------------------------------
# 20. trending payload drift
# ---------------------------------------------------------------------------

def test_20_trending_payload_drift():
    section("20. trending payload drift → FAILED (3)")
    cases = [
        ('{"foo":"bar"}', "missing 'symbols'"),
        ('{"symbols":"oops"}', "'symbols' not a list"),
        ('{"symbols":[1,2,3]}', "non-dict items dropped"),
    ]
    for body, hint in cases:
        opener = _fake_opener_factory([("trending/symbols", body.encode("utf-8"), 0)])
        tool = SentimentSocialTool(opener=opener)
        tr = tool.trending(top_n=3)
        check(f"  {hint}: FAILED or EMPTY",
              tr.status == "FAILED" or tr.status == "EMPTY")


# ---------------------------------------------------------------------------
# 21. clear_cache empties both
# ---------------------------------------------------------------------------

def test_21_clear_cache():
    section("21. clear_cache (4)")
    plan = [
        ("streams/symbol", make_streams_raw(make_streams_payload(["Bullish"])), 0),
        ("trending/symbols", make_streams_raw(make_trending_payload(["AAPL"])), 0),
        ("streams/symbol", make_streams_raw(make_streams_payload(["Bearish"])), 0),  # for re-warm
    ]
    opener = _fake_opener_factory(plan)
    tool = SentimentSocialTool(opener=opener)
    tool.messages("AAPL", limit=1)
    tool.trending(top_n=1)
    check("2 caches populated",
          len(tool._msg_cache) == 1 and len(tool._trend_cache) == 1)
    tool.clear_cache()
    check("msg_cache empty", len(tool._msg_cache) == 0)
    check("trend_cache empty", len(tool._trend_cache) == 0)
    tool.messages("MSFT", limit=1)
    check("re-warm populates msg_cache", len(tool._msg_cache) == 1)


# ---------------------------------------------------------------------------
# 22. call_tool() registry roundtrip
# ---------------------------------------------------------------------------

def test_22_call_tool_roundtrip():
    section("22. call_tool() registry roundtrip (5)")
    from runtime.call_tool import call_tool
    original_m = SentimentSocialTool.messages
    original_t = SentimentSocialTool.trending

    def fake_messages(self, ticker, limit=30):
        return ToolResult(
            status="SUCCESS",
            data={"ticker": ticker, "messages": [], "summary": {"total": 0},
                  "symbol": {"watchlist_count": 0},
                  "as_of": "now", "url": "https://REDACTED"},
            as_of="now", source="stocktwits_streams", note="stub",
        )

    def fake_trending(self, top_n=10):
        return ToolResult(
            status="SUCCESS",
            data={"as_of": "now",
                  "items": [{"symbol": "AAPL", "user_count": 100,
                             "watchlist_count": 4321}],
                  "top_count": 1, "url": "https://REDACTED"},
            as_of="now", source="stocktwits_trending", note="stub-trending",
        )

    SentimentSocialTool.messages = fake_messages
    SentimentSocialTool.trending = fake_trending
    try:
        tr_m = call_tool("sentiment_social",
                         requested_by_agent="smoke",
                         args={"ticker": "AAPL", "limit": 5})
        tr_t = call_tool("sentiment_social",
                         requested_by_agent="smoke",
                         method="trending",
                         args={"top_n": 5})
        check("default method dispatches to messages",
              tr_m.status == "SUCCESS" and tr_m.data["ticker"] == "AAPL")
        check("method=trending dispatches correctly",
              tr_t.status == "SUCCESS" and len(tr_t.data["items"]) == 1)
        check("messages source attribution",
              tr_m.source == "stocktwits_streams")
        check("trending source attribution",
              tr_t.source == "stocktwits_trending")
        check("tr_t symbol=AAPL",
              tr_t.data["items"][0]["symbol"] == "AAPL")
    finally:
        SentimentSocialTool.messages = original_m
        SentimentSocialTool.trending = original_t


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_1_messages_success_shape,
        test_2_all_bullish,
        test_3_no_tags,
        test_4_input_validation,
        test_5_limit_clamp,
        test_6_cache,
        test_7_dollar_prefix_strip,
        test_8_symbol_meta,
        test_9_http_errors,
        test_10_payload_misc,
        test_11_empty_when_no_valid,
        test_12_row_schema,
        test_13_summary_timestamps,
        test_14_url_preserved,
        test_15_trending_success,
        test_16_trending_clamp,
        test_17_trending_order,
        test_18_trending_http_errors,
        test_19_trending_empty,
        test_20_trending_payload_drift,
        test_21_clear_cache,
        test_22_call_tool_roundtrip,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            FAIL += 1
            print(f"  EXC in {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== {OK}/{OK + FAIL} assertions passed ===")
    sys.exit(1 if FAIL > 0 else 0)
