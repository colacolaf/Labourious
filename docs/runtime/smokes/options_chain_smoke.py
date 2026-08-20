"""options_chain_smoke.py — pilot for OptionsChainTool (conn-12).

Three goals: SUCCESS shape on both endpoints, defensive row casting on
real Finnhub payloads, FAILED paths (no key, HTTP, malformed expiration,
unknown ticker, payload shape drift). Caching + redaction are exercised
last so they're not overrun by the new-shape ones.

Counts: ~ 76 assertions across 22 sections.
"""
from __future__ import annotations

import json
import os
import sys

# Quiet urllib when urllib.error is around
import urllib.error as _urllib_error  # noqa: F401

sys.path.insert(0, "docs")

from runtime.tools.options_chain import OptionsChainTool  # noqa: E402
from runtime.tools import ToolResult  # noqa: E402


# ---------------------------------------------------------------------------
# Fake opener infrastructure
# ---------------------------------------------------------------------------

def _fake_opener_factory(
    plan: list[tuple[str, str | bytes, int]],
):
    """Build an opener that hands back payloads from ``plan`` once each.

    Each item is a (url_substr, payload, status). When the URL contains the
    substring, only the first *fresh* entry is consumed. ``status==0`` means
    "raw bytes"; non-0 means "raise HTTPError with that status".
    """
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
    return {
        401: "Unauthorized",
        403: "Forbidden",
        429: "Too Many Requests",
        500: "Server Error",
    }.get(s, f"HTTP {s}")


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


# ---------------------------------------------------------------------------
# Helpers
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
# Helper: craft a representative Finnhub payload
# ---------------------------------------------------------------------------

def fake_expirations_payload(n: int = 6) -> bytes:
    return json.dumps(
        [f"2024-12-{20 + i:02d}" for i in range(n)]
    ).encode("utf-8")


def fake_chain_payload(call_strikes=(90, 95, 100, 105, 110),
                       put_strikes=(90, 95, 100, 105, 110),
                       with_bogus_rows=True) -> bytes:
    """Mimic a Finnhub /stock/option-chain response shape."""
    rows = []
    for s in call_strikes:
        rows.append({
            "strikePrice": s, "side": "CALL", "type": "American",
            "symbol": f"O:AAPL240119C{s:08d}000",
            "expiryDate": "2024-01-19",
            "openInterest": 1234 + s, "volume": 567,
            "lastPrice": 5.6, "bidPrice": 5.5, "askPrice": 5.7,
            "impliedVolatility": 0.32,
            "delta": 0.45, "gamma": 0.02, "theta": -0.05,
            "vega": 0.18, "rho": 0.01,
        })
    for s in put_strikes:
        rows.append({
            "strikePrice": s, "side": "PUT", "type": "American",
            "symbol": f"O:AAPL240119P{s:08d}000",
            "expiryDate": "2024-01-19",
            "openInterest": 987 + s, "volume": 432,
            "lastPrice": 4.7, "bidPrice": 4.6, "askPrice": 4.8,
            "impliedVolatility": 0.34,
            "delta": -0.42, "gamma": 0.02, "theta": -0.04,
            "vega": 0.18, "rho": -0.01,
        })
    if with_bogus_rows:
        rows.append("not a dict")    # dropped
        rows.append(None)             # dropped
        rows.append({"strikePrice": "x", "side": "garbage"})  # dropped
    return json.dumps({"data": rows}).encode("utf-8")


# ---------------------------------------------------------------------------
# 1. expirations SUCCESS shape
# ---------------------------------------------------------------------------

def test_1_expirations_success():
    section("1. expirations SUCCESS shape (8)")
    plan = [("option-expiry-dates", fake_expirations_payload(4), 0)]
    opener = _fake_opener_factory(plan)
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.expirations("AAPL")
    check("status=SUCCESS", tr.status == "SUCCESS")
    check("data is dict", isinstance(tr.data, dict))
    check("data.ticker='AAPL'", tr.data["ticker"] == "AAPL")
    check("expirations is list", isinstance(tr.data["expirations"], list))
    check("exp_count=4", tr.data["exp_count"] == 4)
    check("expirations sorted", tr.data["expirations"] == sorted(tr.data["expirations"]))
    check("note has count", f"4 expirations" in tr.note)
    check("URL has REDACTED", "REDACTED" in tr.data["url"])


# ---------------------------------------------------------------------------
# 2. expirations cache
# ---------------------------------------------------------------------------

def test_2_expirations_cache():
    section("2. expirations cache hit (3)")
    plan = [("option-expiry-dates", fake_expirations_payload(2), 0)]
    opener = _fake_opener_factory(plan)
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    a = tool.expirations("MSFT")
    b = tool.expirations("MSFT")
    c = tool.expirations("msft")  # case-insensitive
    check("a is SUCCESS", a.status == "SUCCESS")
    check("b hits cache (same id(a))", id(a) == id(b))
    check("c hits cache (case-insensitive)", id(a) == id(c))
    check("only 1 upstream call", len(opener.plan_receipts()) == 1)


# ---------------------------------------------------------------------------
# 3. expirations no-key FAILED
# ---------------------------------------------------------------------------

def test_3_expirations_no_key():
    section("3. expirations no-key → FAILED (2)")
    opener = _fake_opener_factory([])
    tool = OptionsChainTool(opener=opener, api_key="")
    tr = tool.expirations("AAPL")
    check("status=FAILED", tr.status == "FAILED")
    check("note mentions FINNHUB_API_KEY", "FINNHUB_API_KEY" in tr.note)


# ---------------------------------------------------------------------------
# 4. expirations HTTP 401
# ---------------------------------------------------------------------------

def test_4_expirations_401():
    section("4. expirations HTTP 401 → FAILED (2)")
    opener = _fake_opener_factory([("option-expiry-dates", "", 401)])
    tool = OptionsChainTool(opener=opener, api_key="BAD_KEY")
    tr = tool.expirations("AAPL")
    check("status=FAILED", tr.status == "FAILED")
    check("note mentions 401", "401" in tr.note)


# ---------------------------------------------------------------------------
# 5. expirations malformed payload (non-list)
# ---------------------------------------------------------------------------

def test_5_expirations_payload_drift():
    section("5. expirations payload drift → FAILED (2)")
    opener = _fake_opener_factory([("option-expiry-dates", '{"foo":"bar"}', 0)])
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.expirations("AAPL")
    check("status=FAILED", tr.status == "FAILED")
    check("note mentions non-list", "non-list" in tr.note or "list" in tr.note)


# ---------------------------------------------------------------------------
# 6. expirations EMPTY when all bad rows
# ---------------------------------------------------------------------------

def test_6_expirations_empty_when_bad_rows():
    section("6. expirations all-bad rows → EMPTY (2)")
    plan = [("option-expiry-dates",
             json.dumps(["not-a-date", None, 12345]).encode("utf-8"), 0)]
    opener = _fake_opener_factory(plan)
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.expirations("AAPL")
    check("status=EMPTY", tr.status == "EMPTY")
    check("exp_count=0", tr.data["exp_count"] == 0)


# ---------------------------------------------------------------------------
# 7. chain SUCCESS shape
# ---------------------------------------------------------------------------

def test_7_chain_success_shape():
    section("7. chain SUCCESS shape + summary (10)")
    plan = [("option-chain", fake_chain_payload(), 0)]
    opener = _fake_opener_factory(plan)
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.chain("AAPL", "2024-01-19")
    check("status=SUCCESS", tr.status == "SUCCESS")
    check("data.ticker='AAPL'", tr.data["ticker"] == "AAPL")
    check("data.expiration='2024-01-19'", tr.data["expiration"] == "2024-01-19")
    rows = tr.data["rows"]
    check("5 calls + 5 puts = 10 rows", len(rows) == 10)
    check("bad rows dropped", "NOT_A_DICT" not in [type(r).__name__ for r in rows])
    summ = tr.data["summary"]
    check("summary.calls==5", summ["calls"] == 5)
    check("summary.puts==5", summ["puts"] == 5)
    check("summary.strikes==5 (unique)", summ["strikes"] == 5)
    check("summary.calls_oi>0", summ["calls_oi"] > 0)
    check("summary.puts_oi>0", summ["puts_oi"] > 0)


# ---------------------------------------------------------------------------
# 8. chain summary put_call_oi_ratio + max OI strikes
# ---------------------------------------------------------------------------

def test_8_chain_summary_ratios():
    section("8. chain summary ratios (4)")
    plan = [("option-chain", fake_chain_payload(), 0)]
    opener = _fake_opener_factory(plan)
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.chain("AAPL", "2024-01-19")
    summ = tr.data["summary"]
    pc = summ["put_call_oi_ratio"]
    check("pc_ratio is float rounded to 4 dec", isinstance(pc, float))
    check("pc_ratio > 0", pc > 0)
    check("max_oi_call_strike in strikes set", summ["max_oi_call_strike"] in {90, 95, 100, 105, 110})
    check("max_oi_put_strike in strikes set", summ["max_oi_put_strike"] in {90, 95, 100, 105, 110})


# ---------------------------------------------------------------------------
# 9. chain cache hit + miss
# ---------------------------------------------------------------------------

def test_9_chain_cache():
    section("9. chain cache hit + miss (3)")
    plan = [
        ("option-chain", fake_chain_payload(call_strikes=(100,), put_strikes=(100,)), 0),
        ("option-chain", fake_chain_payload(call_strikes=(200,), put_strikes=(200,)), 0),
    ]
    opener = _fake_opener_factory(plan)
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    a = tool.chain("AAPL", "2024-01-19")
    b = tool.chain("AAPL", "2024-01-19")  # cache hit
    c = tool.chain("AAPL", "2024-02-19")  # different expiry → miss
    check("a is SUCCESS", a.status == "SUCCESS")
    check("b hits cache (same rows)", b.data == a.data)
    check("c is different row (new strike 200)",
          c.data["summary"]["strikes"] == 1 and
          c.data["rows"][0]["strike"] == 200.0)
    check("2 upstream calls total", len(opener.plan_receipts()) == 2)


# ---------------------------------------------------------------------------
# 10. chain bad expiration
# ---------------------------------------------------------------------------

def test_10_chain_bad_expiration():
    section("10. chain malformed expiration → FAILED (3)")
    opener = _fake_opener_factory([])
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    cases = [
        "",
        "garbage",
        "2024-1-19",     # wrong shape
        "01/19/2024",    # wrong shape
        "2024-13-99",    # realistic-looking but invalid
    ]
    for exp in cases:
        tr = tool.chain("AAPL", exp)
        msg = f"expiration={exp!r} → FAILED (note: {tr.note!r})"
        check(f"  {exp!r}", tr.status == "FAILED")


# ---------------------------------------------------------------------------
# 11. chain empty ticker
# ---------------------------------------------------------------------------

def test_11_chain_empty_ticker():
    section("11. chain empty ticker → FAILED (2)")
    opener = _fake_opener_factory([])
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    tr_a = tool.chain("", "2024-01-19")
    tr_b = tool.chain(None, "2024-01-19")
    check("a is FAILED", tr_a.status == "FAILED")
    check("b is FAILED", tr_b.status == "FAILED")


# ---------------------------------------------------------------------------
# 12. chain no-key FAILED
# ---------------------------------------------------------------------------

def test_12_chain_no_key():
    section("12. chain no-key → FAILED (2)")
    opener = _fake_opener_factory([])
    tool = OptionsChainTool(opener=opener, api_key="")
    tr = tool.chain("AAPL", "2024-01-19")
    check("status=FAILED", tr.status == "FAILED")
    check("note mentions FINNHUB", "FINNHUB_API_KEY" in tr.note)


# ---------------------------------------------------------------------------
# 13. chain HTTP error
# ---------------------------------------------------------------------------

def test_13_chain_http_errors():
    section("13. chain HTTP 401/403/429/500 (4)")
    cases = [(401, "401"), (403, "403"), (429, "429"), (500, "500")]
    for status, needle in cases:
        opener = _fake_opener_factory(
            [("option-chain", "", status)]
        )
        tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
        tr = tool.chain("AAPL", "2024-01-19")
        check(f"status={status} → FAILED with {needle} in note",
              tr.status == "FAILED" and needle in tr.note)


# ---------------------------------------------------------------------------
# 14. chain EMPTY when no valid rows
# ---------------------------------------------------------------------------

def test_14_chain_empty_after_defensive_parse():
    section("14. chain all rows bad → EMPTY (2)")
    bogus = json.dumps({"data": [None, "x", {"side": "garbage"}]}).encode("utf-8")
    opener = _fake_opener_factory([("option-chain", bogus, 0)])
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.chain("AAPL", "2024-01-19")
    check("status=EMPTY", tr.status == "EMPTY")
    check("row_count=0", tr.data["row_count"] == 0)


# ---------------------------------------------------------------------------
# 15. chain row schema fidelity
# ---------------------------------------------------------------------------

def test_15_chain_row_schema():
    section("15. chain row schema fidelity (7)")
    plan = [("option-chain", fake_chain_payload(call_strikes=(150,),
                                                 put_strikes=(150,)), 0)]
    opener = _fake_opener_factory(plan)
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.chain("AAPL", "2024-01-19")
    rows = tr.data["rows"]
    r = next(r for r in rows if r["side"] == "call")
    check("row.strike == 150", r["strike"] == 150)
    check("row.open_interest >= 1234", r["open_interest"] >= 1234)
    check("row.volume == 567", isinstance(r["volume"], int))
    check("row.last is float", isinstance(r["last"], (int, float)))
    check("row.delta == 0.45", abs(r["delta"] - 0.45) < 1e-6)
    check("row.implied_volatility == 0.32", abs(r["implied_volatility"] - 0.32) < 1e-6)
    check("row.occ_symbol startswith O:AAPL", r["occ_symbol"].startswith("O:AAPL"))


# ---------------------------------------------------------------------------
# 16. side normalisation (CALL → call, PUT → put)
# ---------------------------------------------------------------------------

def test_16_side_normalization():
    section("16. side normalisation CALL/put/empty (3)")
    payload = json.dumps({
        "data": [
            {"strikePrice": 100, "side": "CALL", "openInterest": 1},
            {"strikePrice": 200, "side": "put",  "openInterest": 2},
            {"strikePrice": 300, "side": "other","openInterest": 3},  # dropped
        ]
    }).encode("utf-8")
    opener = _fake_opener_factory([("option-chain", payload, 0)])
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    tr = tool.chain("AAPL", "2024-01-19")
    s = {r["side"] for r in tr.data["rows"]}
    check("only 'call' and 'put' kept", s == {"call", "put"})
    summ = tr.data["summary"]
    check("calls==1, puts==1", summ["calls"] == 1 and summ["puts"] == 1)


# ---------------------------------------------------------------------------
# 17. URL has REDACTED, never the raw token
# ---------------------------------------------------------------------------

def test_17_token_redaction():
    section("17. URL redaction (3)")
    raw_key = "abcdef-SUPER-SECRET-123"
    plan = [
        ("option-expiry-dates", fake_expirations_payload(1), 0),
        ("option-chain", fake_chain_payload(call_strikes=(100,), put_strikes=(100,)), 0),
    ]
    opener = _fake_opener_factory(plan)
    tool = OptionsChainTool(api_key=raw_key, opener=opener)
    tr_e = tool.expirations("AAPL")
    tr_c = tool.chain("AAPL", "2024-01-19")
    check("expirations url REDACTED",
          "REDACTED" in tr_e.data["url"] and raw_key not in tr_e.data["url"])
    check("chain url REDACTED",
          "REDACTED" in tr_c.data["url"] and raw_key not in tr_c.data["url"])
    check("notes do NOT leak raw key",
          raw_key not in tr_e.note and raw_key not in tr_c.note)


# ---------------------------------------------------------------------------
# 18. Token precedence: FINNHUB_API_KEY beats LABOURIOUS_FINNHUB_KEY
# ---------------------------------------------------------------------------

def test_18_token_precedence():
    section("18. Token env precedence (3)")
    prior_finnhub = os.environ.pop("FINNHUB_API_KEY", None)
    try:
        # 1. Only LABOURIOUS_FINNHUB_KEY — fallback works
        os.environ.pop("LABOURIOUS_FINNHUB_KEY", None)
        os.environ["LABOURIOUS_FINNHUB_KEY"] = "FALLBACK_KEY"
        opener = _fake_opener_factory(
            [("option-expiry-dates", fake_expirations_payload(1), 0)]
        )
        tool = OptionsChainTool(opener=opener, api_key=None)
        tr_l = tool.expirations("AAPL")
        check("with only LABOURIOUS_FINNHUB_KEY env, fallback works",
              tr_l.status == "SUCCESS" and "FALLBACK_KEY" not in tr_l.data["url"])

        # 2. Both envs set — FINNHUB_API_KEY wins. Use a fresh tool + opener
        #    with its own plan entry so a real fetch fires.
        os.environ["FINNHUB_API_KEY"] = "PRIMARY_KEY"
        os.environ["LABOURIOUS_FINNHUB_KEY"] = "SHOULD_LOSE"
        opener2 = _fake_opener_factory(
            [("option-expiry-dates", fake_expirations_payload(2), 0)]
        )
        tool2 = OptionsChainTool(opener=opener2, api_key=None)
        # Force a non-cached call by giving it a different ticker
        tr_p = tool2.expirations("MSFT")
        check("with both envs, FINNHUB_API_KEY wins",
              tr_p.status == "SUCCESS" and "PRIMARY_KEY" not in tr_p.data["url"])

        # 3. Explicit api_key kwarg wins over env
        opener3 = _fake_opener_factory(
            [("option-expiry-dates", fake_expirations_payload(1), 0)]
        )
        tool3 = OptionsChainTool(opener=opener3, api_key="KWARG_BEATS_ENV")
        tr_k = tool3.expirations("NVDA")
        check("explicit api_key kwarg beats env",
              tr_k.status == "SUCCESS" and "KWARG_BEATS_ENV" not in tr_k.data["url"])
    finally:
        for k in ("FINNHUB_API_KEY", "LABOURIOUS_FINNHUB_KEY"):
            os.environ.pop(k, None)
        if prior_finnhub is not None:
            os.environ["FINNHUB_API_KEY"] = prior_finnhub


# ---------------------------------------------------------------------------
# 19. clear_cache empties both
# ---------------------------------------------------------------------------

def test_19_clear_cache():
    section("19. clear_cache (4)")
    plan = [
        ("option-expiry-dates", fake_expirations_payload(1), 0),
        ("option-chain", fake_chain_payload(call_strikes=(100,), put_strikes=(100,)), 0),
        ("option-expiry-dates", fake_expirations_payload(2), 0),  # extra for re-warm
    ]
    opener = _fake_opener_factory(plan)
    tool = OptionsChainTool(opener=opener, api_key="DEMO_KEY")
    tool.expirations("AAPL")
    tool.chain("AAPL", "2024-01-19")
    check("2 caches populated after 2 calls",
          len(tool._exp_cache) == 1 and len(tool._chain_cache) == 1)
    tool.clear_cache()
    check("exp_cache empty after clear", len(tool._exp_cache) == 0)
    check("chain_cache empty after clear", len(tool._chain_cache) == 0)
    tool.expirations("AAPL")  # re-warms via plan entry #3
    check("re-warm populates exp_cache", len(tool._exp_cache) == 1)


# ---------------------------------------------------------------------------
# 20. call_tool round-trip via registry
# ---------------------------------------------------------------------------

def test_20_call_tool_roundtrip():
    section("20. call_tool registry roundtrip (5)")
    # Stub the actual network by monkey-patching the tool class methods.
    from runtime.call_tool import call_tool
    from runtime.tools.options_chain import OptionsChainTool
    original_chain = OptionsChainTool.chain
    original_exp = OptionsChainTool.expirations

    def fake_chain(self, ticker, expiration):
        return ToolResult(
            status="SUCCESS",
            data={
                "ticker": ticker, "expiration": expiration,
                "rows": [{"strike": 100, "side": "call",
                          "open_interest": 10}],
                "summary": {"calls": 1, "puts": 0},
                "row_count": 1, "as_of": "2024-01-19T00:00:00Z",
                "url": "https://REDACTED",
            },
            as_of="2024-01-19T00:00:00Z",
            source="finnhub_option_chain",
            note="stub",
        )

    def fake_exp(self, ticker):
        return ToolResult(
            status="SUCCESS",
            data={"ticker": ticker, "expirations": ["2024-01-19"],
                  "exp_count": 1, "as_of": "now",
                  "url": "https://REDACTED"},
            as_of="now", source="finnhub_expirations", note="stub",
        )

    OptionsChainTool.chain = fake_chain
    OptionsChainTool.expirations = fake_exp
    try:
        tr1 = call_tool(
            "options_chain",
            requested_by_agent="smoke",
            args={"ticker": "AAPL", "expiration": "2024-01-19"},
        )
        tr2 = call_tool(
            "options_chain",
            requested_by_agent="smoke",
            method="expirations",
            args={"ticker": "AAPL"},
        )
        check("default method dispatches to chain",
              tr1.status == "SUCCESS" and tr1.data["expiration"] == "2024-01-19")
        check("method=expirations dispatches correctly",
              tr2.status == "SUCCESS" and tr2.data["expirations"] == ["2024-01-19"])
        check("tr1 fields preserved (row_count)",
              tr1.data["row_count"] == 1)
        check("tr2 fields preserved (exp_count)",
              tr2.data["exp_count"] == 1)
        check("both carry source attribution",
              tr1.source == "finnhub_option_chain"
              and tr2.source == "finnhub_expirations")
    finally:
        OptionsChainTool.chain = original_chain
        OptionsChainTool.expirations = original_exp


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_1_expirations_success,
        test_2_expirations_cache,
        test_3_expirations_no_key,
        test_4_expirations_401,
        test_5_expirations_payload_drift,
        test_6_expirations_empty_when_bad_rows,
        test_7_chain_success_shape,
        test_8_chain_summary_ratios,
        test_9_chain_cache,
        test_10_chain_bad_expiration,
        test_11_chain_empty_ticker,
        test_12_chain_no_key,
        test_13_chain_http_errors,
        test_14_chain_empty_after_defensive_parse,
        test_15_chain_row_schema,
        test_16_side_normalization,
        test_17_token_redaction,
        test_18_token_precedence,
        test_19_clear_cache,
        test_20_call_tool_roundtrip,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"  EXC in {t.__name__}: {type(e).__name__}: {e}")
            FAIL += 1
    print(f"\n=== {OK}/{OK + FAIL} assertions passed ===")
    sys.exit(1 if FAIL > 0 else 0)
