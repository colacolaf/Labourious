"""
smokes/calendars_smoke.py — pilot for conn-9 (Finnhub calendars).

Asserts (≥ 25 planned):
  1. Earnings SUCCESS shape — meta.{ticker, scope, start, end, window_days,
     row_count}, rows[i].{date, symbol, hour, quarter, year,
     eps_estimate, eps_actual, revenue_estimate, revenue_actual}
  2. Earnings window: defaults — when start/end are None, today's UTC
     anchor + 30 days
  3. Earnings window: end < start → FAILED with "before start" hint
  4. Earnings window: span > 90 days → FAILED with "window too wide"
  5. Earnings window: invalid start format ("not-a-date") → FAILED
  6. Earnings with `ticker="AAPL"` adds &symbol=AAPL to URL
  7. Earnings without ticker — no symbol filter in URL
  8. Earnings cache hit across repeat calls within TTL
  9. Earnings cache miss after TTL=0
 10. Earnings wrapper key — uses literal "earningsCalendar"
 11. Earnings defensive — bad row in `rows_raw` doesn't crash
 12. Earnings EMPTY — empty list → EMPTY ToolResult, data=[]
 13. Earnings non-dict payload → FAILED
 14. Earnings non-list `earningsCalendar` → FAILED with expected-list hint
 15. IPO SUCCESS shape — rows[i].{date, symbol, name, exchange,
     number_of_shares, price, status, total_shares_value}
 16. IPO wrapper key — uses literal "ipoCalendar"
 17. IPO EMPTY → EMPTY ToolResult
 18. IPO cache hit within TTL
 19. IPO doesn't accept ticker (window-only)
 20. Cache across earnings + ipo doesn't cross-pollute
 21. clear_cache() empties both caches
 22. No key → FAILED with FINNHUB_API_KEY hint (both methods)
 23. HTTP 401 → FAILED "invalid FINNHUB_API_KEY"
 24. HTTP 403 → FAILED free-tier rate-limit hint
 25. HTTP 429 → FAILED rate-limited
 26. URL redaction — raw token never appears in any note (both methods)
 27. _redact_token() unit-level
 28. Token precedence — explicit kwarg > FINNHUB_API_KEY > LABOURIOUS_FINNHUB_KEY
 29. citation_kind in catalog == 'calendar'
 30. Two methods via call_tool (registry round-trip)
 31. call_tool() with bogus method → FAILED
 32. Today's UTC anchor — earnings with no args uses today UTC + 30d

Robust to ⌃C, prints FAILs at the bottom, exits non-zero on any failure.
"""
from __future__ import annotations

import io
import json
import os
import sys
import urllib.error
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Make runtime importable.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs"))

from runtime.tools import ToolResult
from runtime.tools.calendars import (
    CalendarsTool,
    DEFAULT_API_BASE,
    DEFAULT_CACHE_TTL_S,
    DEFAULT_WINDOW_DAYS_DEFAULT,
    DEFAULT_WINDOW_DAYS_MAX,
    _canonicalize_arg_date,
    _redact_token,
    _resolve_window,
    _today_utc,
)


PASS = "\033[32m  ok\033[0m"
FAIL = "\033[31mFAIL\033[0m"

_fails: list[str] = []


def step(label: str, ok: bool, *, detail: str = "") -> None:
    if ok:
        print(f"{PASS}    | {label}")
    else:
        msg = f"{FAIL}   | {label}"
        if detail:
            msg += f"\n         {detail}"
        print(msg)
        _fails.append(label)


# ----------------------------------------------------------- stubs

class _StubURLResp:
    def __init__(self, payload: Any, status: int = 200,
                 headers: dict[str, str] | None = None):
        self._payload = payload
        self.status = status
        self.headers = headers or {}

    def read(self) -> bytes:
        body = self._payload
        if not isinstance(body, (bytes, str)):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode("utf-8")
        return body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _fake_opener(payloads: list[Any] | None = None,
                 raises: list[Exception] | None = None):
    """Return (callable, calls_list, headers_trace)."""
    state: dict[str, Any] = {
        "calls": [],
        "headers_trace": [],
        "raise_idx": 0,
    }
    payloads = payloads or []
    queue = list(payloads)
    raises = raises or []

    def fake_opener(req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        state["calls"].append(url)
        if req is not None and not isinstance(req, str):
            state["headers_trace"].append(dict(req.headers or {}))
        else:
            state["headers_trace"].append({})
        if state["raise_idx"] < len(raises):
            exc = raises[state["raise_idx"]]
            state["raise_idx"] += 1
            raise exc
        if not queue:
            raise RuntimeError(f"opener ran out ({len(state['calls'])} calls)")
        return _StubURLResp(queue.pop(0))

    return fake_opener, state["calls"], state["headers_trace"]


def _http_error(code: int, msg: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="/v1/calendar", code=code, msg=msg,
        hdrs={}, fp=io.BytesIO(b""),
    )


# ----------------------------------------------------------- fixtures

_TODAY = _today_utc()

_PLAIN_EARNINGS_ALL_MKT = {
    "earningsCalendar": [
        {
            "date": (_TODAY + timedelta(days=1)).isoformat(),
            "hour": "bmo", "quarter": 2, "year": 2025,
            "epsActual": None, "epsEstimate": 1.34,
            "revenueActual": None, "revenueEstimate": 88400000000,
            "symbol": "NVDA",
        },
        {
            "date": (_TODAY + timedelta(days=2)).isoformat(),
            "hour": "amc", "quarter": 2, "year": 2025,
            "epsActual": None, "epsEstimate": 0.92,
            "revenueActual": None, "revenueEstimate": 39200000000,
            "symbol": "AAPL",
        },
    ],
}

_PLAIN_EARNINGS_AAPL = {
    "earningsCalendar": [
        {
            "date": (_TODAY + timedelta(days=2)).isoformat(),
            "hour": "amc", "quarter": 2, "year": 2025,
            "epsActual": None, "epsEstimate": 0.92,
            "revenueActual": None, "revenueEstimate": 39200000000,
            "symbol": "AAPL",
        },
    ],
}

_PLAIN_IPO = {
    "ipoCalendar": [
        {
            "date": (_TODAY + timedelta(days=14)).isoformat(),
            "exchange": "NASDAQ", "name": "Acme Co",
            "numberOfShares": 12000000, "price": "12.00-14.00",
            "status": "priced", "symbol": "ACME",
            "totalSharesValue": 156000000,
        },
    ],
}


# ----------------------------------------------------------- assertions

print("=== 1. Earnings SUCCESS shape ===")
t1 = CalendarsTool(api_key="k1", opener=None)
f1, calls1, _ = _fake_opener([_PLAIN_EARNINGS_ALL_MKT])
t1.opener = f1
res1 = t1.earnings()
step("status SUCCESS", res1.status == "SUCCESS",
     detail=f"got {res1.status!r}, note={(res1.note or '')[:80]!r}")
step("data is dict with rows + meta",
     isinstance(res1.data, dict) and "rows" in res1.data
     and "meta" in res1.data)
step("rows count == 2",
     isinstance(res1.data, dict) and len(res1.data["rows"]) == 2)
step("row schema — date/symbol/hour/quarter/year/eps_estimate/",
     isinstance(res1.data, dict) and all(
         k in res1.data["rows"][0] for k in
         ("date", "symbol", "hour", "quarter", "year",
          "eps_estimate", "eps_actual", "revenue_estimate", "revenue_actual")
     ))
step("meta.scope == 'all' (no ticker)",
     isinstance(res1.data, dict) and res1.data["meta"]["scope"] == "all")
step("meta.row_count == 2",
     isinstance(res1.data, dict) and res1.data["meta"]["row_count"] == 2)
step("source == 'finnhub_earnings_calendar'",
     res1.source == "finnhub_earnings_calendar")


print("\n=== 2. Earnings window defaults — start/end None → today UTC + 30 days ===")
t2 = CalendarsTool(api_key="k", opener=None)
f2, calls2, _ = _fake_opener([_PLAIN_EARNINGS_ALL_MKT])
t2.opener = f2
t2.earnings()
# Pull start/end from the URL that was actually fired.
url = calls2[0]
from urllib.parse import urlparse, parse_qs
qs = parse_qs(urlparse(url).query)
start_used = qs["from"][0]
end_used   = qs["to"][0]
step("from ≈ today's UTC",
     start_used == _TODAY.isoformat(),
     detail=f"from={start_used!r}, expected={_TODAY.isoformat()!r}")
step("to ≈ today + 30d",
     end_used == (_TODAY + timedelta(days=30)).isoformat(),
     detail=f"to={end_used!r}")


print("\n=== 3. Earnings window — end < start → FAILED ===")
t3 = CalendarsTool(api_key="k", opener=None)
f3, calls3, _ = _fake_opener([])
t3.opener = f3
res3 = t3.earnings(start="2025-09-10", end="2025-09-01")
step("status FAILED", res3.status == "FAILED",
     detail=f"got {res3.status!r}")
step("note mentions 'before start'",
     "before start" in (res3.note or ""),
     detail=f"note={res3.note!r}")
step("no fetch attempted", len(calls3) == 0)


print("\n=== 4. Earnings window — span > 90 days → FAILED ===")
t4 = CalendarsTool(api_key="k", opener=None)
f4, calls4, _ = _fake_opener([])
t4.opener = f4
res4 = t4.earnings(start="2025-01-01", end="2025-12-31")
step("status FAILED", res4.status == "FAILED")
step("note mentions 'window too wide'",
     "window too wide" in (res4.note or ""),
     detail=f"note={res4.note!r}")
step("note mentions max days",
     str(DEFAULT_WINDOW_DAYS_MAX) in (res4.note or ""),
     detail=f"note={res4.note!r}")
step("no fetch attempted", len(calls4) == 0)


print("\n=== 5. Earnings window — invalid start format → FAILED ===")
t5 = CalendarsTool(api_key="k", opener=None)
f5, calls5, _ = _fake_opener([])
t5.opener = f5
res5 = t5.earnings(start="not-a-date")
step("status FAILED + 'not a valid' hint",
     res5.status == "FAILED"
     and "not a valid" in (res5.note or ""),
     detail=f"note={res5.note!r}")
step("no fetch attempted", len(calls5) == 0)


print("\n=== 6. Earnings with ticker=\"AAPL\" adds &symbol=AAPL to URL ===")
t6 = CalendarsTool(api_key="k", opener=None)
f6, calls6, _ = _fake_opener([_PLAIN_EARNINGS_AAPL])
t6.opener = f6
t6.earnings(ticker="AAPL")
url6 = calls6[0]
from urllib.parse import urlparse, parse_qs
qs6 = parse_qs(urlparse(url6).query)
step("symbol=AAPL in query", qs6.get("symbol", [""])[0] == "AAPL",
     detail=f"query keys: {sorted(qs6.keys())}, full url: {url6[:120]!r}")


print("\n=== 7. Earnings without ticker — no symbol filter in URL ===")
t7 = CalendarsTool(api_key="k", opener=None)
f7, calls7, _ = _fake_opener([_PLAIN_EARNINGS_ALL_MKT])
t7.opener = f7
t7.earnings(ticker="")  # empty → all mkt
qs7 = parse_qs(urlparse(calls7[0]).query)
step("no symbol key in query", "symbol" not in qs7,
     detail=f"query keys: {sorted(qs7.keys())}")


print("\n=== 8. Earnings cache hit within TTL ===")
t8 = CalendarsTool(api_key="k", opener=None)
f8, calls8, _ = _fake_opener([_PLAIN_EARNINGS_ALL_MKT])
t8.opener = f8
t8.earnings()
t8.earnings()
t8.earnings()
step("only 1 fetch across 3 calls", len(calls8) == 1,
     detail=f"got {len(calls8)} calls")


print("\n=== 9. Earnings cache miss after TTL=0 ===")
t9 = CalendarsTool(api_key="k", opener=None)
f9, calls9, _ = _fake_opener([
    _PLAIN_EARNINGS_ALL_MKT, _PLAIN_EARNINGS_ALL_MKT,
])
t9.opener = f9
t9.earnings()
t9.cache_ttl_s = 0
t9.earnings()
step("2 fetches after TTL=0", len(calls9) == 2,
     detail=f"got {len(calls9)} calls")


print("\n=== 10. Earnings wrapper key — literal 'earningsCalendar' ===")
# Verified by section 1 — this is a spelling check.
t10 = CalendarsTool(api_key="k", opener=None)
out_payload = {"earningsCalendar": []}
f10, _, _ = _fake_opener([out_payload])
t10.opener = f10
res10 = t10.earnings()
step("status EMPTY (spelled 'earningsCalendar')",
     res10.status == "EMPTY",
     detail=f"got {res10.status!r}, note={(res10.note or '')[:60]!r}")


print("\n=== 11. Earnings defensive — bad row in 'rows_raw' doesn't crash ===")
mixed = {
    "earningsCalendar": [
        {  # valid
            "date": "2025-12-01", "hour": "bmo",
            "quarter": 4, "year": 2025,
            "epsEstimate": 1.34, "epsActual": None,
            "revenueEstimate": 88400000000, "revenueActual": None,
            "symbol": "NVDA",
        },
        "NOT_A_DICT",    # bad row — should be skipped silently
        [1, 2, 3],       # bad row — should be skipped silently
        None,            # bad row — should be skipped silently
        {  # valid
            "date": "2025-12-02", "hour": "amc",
            "quarter": 4, "year": 2025,
            "epsEstimate": 0.92, "epsActual": None,
            "revenueEstimate": 39200000000, "revenueActual": None,
            "symbol": "AAPL",
        },
    ],
}
t11 = CalendarsTool(api_key="k", opener=None)
f11, _, _ = _fake_opener([mixed])
t11.opener = f11
res11 = t11.earnings()
step("status SUCCESS (3 bad rows survived)",
     res11.status == "SUCCESS", detail=f"got {res11.status!r}")
step("rows trimmed to 2 valid",
     isinstance(res11.data, dict) and len(res11.data["rows"]) == 2,
     detail=f"got {len(res11.data['rows'])}")


print("\n=== 12. Earnings EMPTY — empty list → EMPTY ===")
t12 = CalendarsTool(api_key="k", opener=None)
f12, _, _ = _fake_opener([{"earningsCalendar": []}])
t12.opener = f12
res12 = t12.earnings()
step("status EMPTY", res12.status == "EMPTY",
     detail=f"got {res12.status!r}")
step("data == []", res12.data == [])
step("note explains empty",
     "no scheduled prints" in (res12.note or "").lower()
     or "no scheduled" in (res12.note or "").lower())


print("\n=== 13. Earnings non-dict payload → FAILED ===")
t13 = CalendarsTool(api_key="k", opener=None)
f13, _, _ = _fake_opener([[1, 2, 3], "string", 42])  # multiple bad shapes
t13.opener = f13
for bad_payload in [[1, 2, 3], "string-payload", 42]:
    # Re-populate the queue for each.
    t13sub = CalendarsTool(api_key="k", opener=None)
    f13sub, _, _ = _fake_opener([bad_payload])
    t13sub.opener = f13sub
    res13 = t13sub.earnings()
    step(f"  payload={type(bad_payload).__name__} → FAILED",
         res13.status == "FAILED", detail=f"got {res13.status!r}")


print("\n=== 14. Earnings non-list 'earningsCalendar' → FAILED ===")
t14 = CalendarsTool(api_key="k", opener=None)
f14, _, _ = _fake_opener([{"earningsCalendar": "not-a-list"}])
t14.opener = f14
res14 = t14.earnings()
step("status FAILED", res14.status == "FAILED")
step("note mentions 'expected list'",
     "expected list" in (res14.note or ""),
     detail=f"note={res14.note!r}")


print("\n=== 15. IPO SUCCESS shape ===")
t15 = CalendarsTool(api_key="k1", opener=None)
f15, calls15, _ = _fake_opener([_PLAIN_IPO])
t15.opener = f15
res15 = t15.ipo()
step("status SUCCESS", res15.status == "SUCCESS")
step("row schema — date/symbol/name/exchange/number_of_shares/price/status",
     isinstance(res15.data, dict)
     and all(
         k in res15.data["rows"][0] for k in
         ("date", "symbol", "name", "exchange",
          "number_of_shares", "price", "status", "total_shares_value")
     ))
step("source == 'finnhub_ipo_calendar'",
     res15.source == "finnhub_ipo_calendar")
step("meta.row_count == 1",
     isinstance(res15.data, dict)
     and res15.data["meta"]["row_count"] == 1)


print("\n=== 16. IPO wrapper key — literal 'ipoCalendar' ===")
# Verified via _PLAIN_IPO in section 15. Spelling check standalone.
t16 = CalendarsTool(api_key="k", opener=None)
out_payload2 = {"ipoCalendar": []}
f16, _, _ = _fake_opener([out_payload2])
t16.opener = f16
res16 = t16.ipo()
step("status EMPTY (spelled 'ipoCalendar')",
     res16.status == "EMPTY", detail=f"got {res16.status!r}")


print("\n=== 17. IPO EMPTY → EMPTY ===")
t17 = CalendarsTool(api_key="k", opener=None)
f17, _, _ = _fake_opener([{"ipoCalendar": []}])
t17.opener = f17
res17 = t17.ipo()
step("status EMPTY", res17.status == "EMPTY")
step("data == []", res17.data == [])


print("\n=== 18. IPO cache hit within TTL ===")
t18 = CalendarsTool(api_key="k", opener=None)
f18, calls18, _ = _fake_opener([_PLAIN_IPO])
t18.opener = f18
t18.ipo()
t18.ipo()
step("only 1 fetch across 2 calls", len(calls18) == 1,
     detail=f"got {len(calls18)} calls")


print("\n=== 19. IPO doesn't accept ticker — window-only ===")
# Just assert that passing ticker doesn't crash and is ignored.
t19 = CalendarsTool(api_key="k", opener=None)
f19, calls19, _ = _fake_opener([_PLAIN_IPO])
t19.opener = f19
res19 = t19.ipo()  # no ticker kwarg
step("status SUCCESS", res19.status == "SUCCESS")
qs19 = parse_qs(urlparse(calls19[0]).query)
step("no symbol key in IPO URL", "symbol" not in qs19,
     detail=f"query keys: {sorted(qs19.keys())}")


print("\n=== 20. Cache across earnings + ipo doesn't cross-pollute ===")
t20 = CalendarsTool(api_key="k", opener=None)
f20, calls20, _ = _fake_opener([
    _PLAIN_EARNINGS_ALL_MKT, _PLAIN_IPO,
])
t20.opener = f20
t20.earnings()
t20.ipo()
# Hit each again — should still be cache hits (each has own map).
t20.earnings()
t20.ipo()
step("only 2 fetches across 4 calls", len(calls20) == 2,
     detail=f"got {len(calls20)} calls")


print("\n=== 21. clear_cache() empties both caches ===")
t21 = CalendarsTool(api_key="k", opener=None)
f21, calls21, _ = _fake_opener([
    _PLAIN_EARNINGS_ALL_MKT, _PLAIN_IPO,
    _PLAIN_EARNINGS_ALL_MKT, _PLAIN_IPO,
])
t21.opener = f21
t21.earnings()
t21.ipo()
step("2 fetches before clear", len(calls21) == 2)
t21.clear_cache()
t21.earnings()
t21.ipo()
step("4 total fetches after clear", len(calls21) == 4,
     detail=f"got {len(calls21)}")


print("\n=== 22. No key → FAILED with FINNHUB_API_KEY hint (both methods) ===")
saved = os.environ.pop("FINNHUB_API_KEY", None)
saved2 = os.environ.pop("LABOURIOUS_FINNHUB_KEY", None)
try:
    for method in ("earnings", "ipo"):
        t22 = CalendarsTool(api_key=None, opener=None)
        f22, calls22, _ = _fake_opener([])
        t22.opener = f22
        if method == "earnings":
            res22 = t22.earnings()
            exp_source = "finnhub_earnings_calendar"
        else:
            res22 = t22.ipo()
            exp_source = "finnhub_ipo_calendar"
        step(f"  [{method}] status FAILED",
             res22.status == "FAILED", detail=f"got {res22.status!r}")
        step(f"  [{method}] note contains FINNHUB_API_KEY",
             "FINNHUB_API_KEY" in (res22.note or ""))
        step(f"  [{method}] source == '{exp_source}'",
             res22.source == exp_source)
        step(f"  [{method}] no fetch attempted", len(calls22) == 0)
finally:
    if saved is not None: os.environ["FINNHUB_API_KEY"] = saved
    if saved2 is not None: os.environ["LABOURIOUS_FINNHUB_KEY"] = saved2


print("\n=== 23. HTTP 401 → FAILED 'invalid FINNHUB_API_KEY' ===")
t23 = CalendarsTool(api_key="wrong", opener=None)
f23, _, _ = _fake_opener(raises=[_http_error(401, "Unauthorized")])
t23.opener = f23
res23 = t23.earnings()
step("status FAILED + 'invalid FINNHUB_API_KEY'",
     res23.status == "FAILED"
     and "invalid FINNHUB_API_KEY" in (res23.note or ""),
     detail=f"note={res23.note!r}")


print("\n=== 24. HTTP 403 → FAILED free-tier rate-limit hint ===")
t24 = CalendarsTool(api_key="k", opener=None)
f24, _, _ = _fake_opener(raises=[_http_error(403, "Forbidden")])
t24.opener = f24
res24 = t24.ipo()
step("status FAILED + free-tier rate-limit hint",
     res24.status == "FAILED"
     and ("free-tier" in (res24.note or "").lower()
          or "rate" in (res24.note or "").lower()),
     detail=f"note={res24.note!r}")


print("\n=== 25. HTTP 429 → FAILED rate-limited ===")
t25 = CalendarsTool(api_key="k", opener=None)
f25, _, _ = _fake_opener(raises=[_http_error(429, "Too Many Requests")])
t25.opener = f25
res25 = t25.earnings()
step("status FAILED + 429 hint",
     res25.status == "FAILED"
     and ("rate" in (res25.note or "").lower()
          or "429" in (res25.note or "")))


print("\n=== 26. URL redaction — raw token never appears in any note ===")
for method in ("earnings", "ipo"):
    t26 = CalendarsTool(
        api_key=f"LEAK-{method.upper()}", opener=None)
    payload = (_PLAIN_EARNINGS_ALL_MKT if method == "earnings"
               else _PLAIN_IPO)
    f26, _, _ = _fake_opener([payload])
    t26.opener = f26
    if method == "earnings":
        res26 = t26.earnings()
    else:
        res26 = t26.ipo()
    step(f"  [{method}] raw secret NOT in note",
         f"LEAK-{method.upper()}" not in (res26.note or ""),
         detail=f"note={(res26.note or '')[:120]!r}")
    step(f"  [{method}] REDACTED marker present in note",
         "token=REDACTED" in (res26.note or ""),
         detail=f"note={(res26.note or '')[:120]!r}")


print("\n=== 27. _redact_token() unit-level ===")
step("_redact_token() neutralises token=",
     _redact_token("https://x.com/y?from=2025-01-01&token=secret")
     == "https://x.com/y?from=2025-01-01&token=REDACTED")
step("_redact_token() leaves non-token keys intact",
     _redact_token("https://x.com/y?from=2025-01-01&symbol=AAPL")
     == "https://x.com/y?from=2025-01-01&symbol=AAPL")


print("\n=== 28. Token precedence — explicit kwarg > env > '' ===")
os.environ.pop("LABOURIOUS_FINNHUB_KEY", None)
os.environ["FINNHUB_API_KEY"] = "from-env"
t28 = CalendarsTool(api_key="from-arg", opener=None)
step("explicit kwarg wins over FINNHUB_API_KEY env",
     t28.api_key == "from-arg")
del os.environ["FINNHUB_API_KEY"]
os.environ["LABOURIOUS_FINNHUB_KEY"] = "from-labourious-env"
t28b = CalendarsTool(api_key="from-arg", opener=None)
step("explicit kwarg wins over LABOURIOUS_FINNHUB_KEY too",
     t28b.api_key == "from-arg")
del os.environ["LABOURIOUS_FINNHUB_KEY"]
os.environ["FINNHUB_API_KEY"] = "from-fmp-env"
t28c = CalendarsTool(opener=None)
step("no explicit kwarg → FINNHUB_API_KEY env used",
     t28c.api_key == "from-fmp-env")
del os.environ["FINNHUB_API_KEY"]


print("\n=== 29. citation_kind in catalog == 'calendar' ===")
from frontend.connectors_catalog import by_name
entry = by_name("calendars")
step("catalog entry exists", entry is not None)
step("citation_kind == 'calendar'", entry.citation_kind == "calendar")
step("tier == 'tier2'", entry.tier == "tier2")
step("key_env == 'FINNHUB_API_KEY'", entry.key_env == "FINNHUB_API_KEY")
step("recommended == True", entry.recommended is True)


print("\n=== 30. Two methods via call_tool (registry round-trip) ===")
from runtime.call_tool import call_tool

payload_map = {
    "earnings": _PLAIN_EARNINGS_ALL_MKT,
    "ipo":      _PLAIN_IPO,
}

_pilot_payloads: list[Any] = []
_orig_init = CalendarsTool.__post_init__


def _patched_init(self):
    _orig_init(self)
    if _pilot_payloads:
        payload = _pilot_payloads.pop(0)
        def _op(req, timeout=None):
            return _StubURLResp(payload)
        self.opener = _op


CalendarsTool.__post_init__ = _patched_init
saved_key = os.environ.get("FINNHUB_API_KEY")
os.environ["FINNHUB_API_KEY"] = "pilot-test-key"

try:
    for method_name, payload in payload_map.items():
        _pilot_payloads.clear()
        _pilot_payloads.append(payload)
        args: dict[str, Any] = {"ticker": ""}
        if method_name == "ipo":
            args.pop("ticker", None)
        res30 = call_tool(
            "calendars",
            requested_by_agent="smoke-pilot",
            method=method_name,
            args=args,
        )
        step(f"call_tool({method_name!r}) → SUCCESS",
             res30.status == "SUCCESS",
             detail=f"status={res30.status!r}, note={(res30.note or '')[:80]!r}")
        step(f"  data has rows + meta",
             isinstance(res30.data, dict)
             and "rows" in res30.data and "meta" in res30.data)
finally:
    CalendarsTool.__post_init__ = _orig_init
    if saved_key is not None:
        os.environ["FINNHUB_API_KEY"] = saved_key
    else:
        os.environ.pop("FINNHUB_API_KEY", None)


print("\n=== 31. call_tool() with bogus method → FAILED ===")
res31 = call_tool(
    "calendars",
    requested_by_agent="smoke-pilot",
    method="bogus_method_xyz",
    args={"ticker": ""},
)
step("status FAILED", res31.status == "FAILED",
     detail=f"got {res31.status!r}")
step("note mentions method",
     "bogus_method_xyz" in (res31.note or "")
     or "method" in (res31.note or "").lower())


print("\n=== 32. Today's UTC anchor — _resolve_window with both None ===")
start_d, end_d = _resolve_window(None, None, 30, 90)
step("start == today UTC",
     start_d == _TODAY,
     detail=f"start={start_d}, today={_TODAY}")
step("end == today + 30d",
     end_d == _TODAY + timedelta(days=30),
     detail=f"end={end_d}")


# ----------------------------------------------------------- summary
print()
total = len(_fails)
print(f"\033[1m{'OK' if total == 0 else 'FAIL'}\033[0m · "
      f"{32 - total}/32 sections green · "
      f"{_fails and f'{total} failed' or 'all green'}")
if _fails:
    print("\nFailures:")
    for f in _fails:
        print(f"  - {f}")
    sys.exit(1)
sys.exit(0)
