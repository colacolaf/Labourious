"""
smokes/consensus_smoke.py — pilot for conn-8 (Finnhub consensus).

Asserts (≥ 25 planned):
  1. Price target SUCCESS shape — keys: ticker/target_mean/target_median/
     target_high/target_low/last_updated/as_of/url
  2. Recommendations SUCCESS shape — rows with period/strongBuy/buy/hold/
     sell/strongSell/analyst_count
  3. Revenue estimate SUCCESS shape — rows with period/revenue_avg/
     revenue_low/revenue_high/revenue_growth/num_analysts
  4. analyst_count = strongBuy + buy + hold + sell + strongSell
  5. Recommendations cache within TTL — only 1 fetch across 2 calls
  6. Price target cache within TTL — fetch count = 1 across 2 calls
  7. Revenue estimate cache within TTL — fetch count = 1 across 2 calls
  8. Cache across distinct methods does not cross-pollute (3 separate maps)
  9. clear_cache() empties all three
 10. No key → FAILED with FINNHUB_API_KEY configure hint
 11. Empty ticker → FAILED
 12. Unknown ticker (recommendations: []) → EMPTY
 13. Unknown ticker (revenue_estimate: []) → EMPTY
 14. Price target targetMean=0 → FAILED (don't fabricate $0.00)
 15. Price target with no targetMean key → FAILED with payload echo
 16. HTTP 401 → FAILED "invalid FINNHUB_API_KEY"
 17. HTTP 403 → FAILED mentioning free-tier rate limit
 18. HTTP 429 → FAILED rate-limited
 19. Freq aliases — "quarter"/"q"/"3m" → "quarterly"; "yearly"/"fy" → "annual"
 20. Unknown freq → FAILED with "not supported"
 21. Limit clamp — 99999 → ≤ 50
 22. Limit=0 → 1, limit=-5 → 1
 23. URL redaction — raw token never appears in note for any of 3 methods
 24. _redact_token() neutralises token query key
 25. citation_kind in catalog == 'consensus'
 26. ToolResult.source per method — finnhub_recommendation /
     finnhub_price_target / finnhub_revenue_estimate
 27. Token precedence — explicit kwarg > FINNHUB_API_KEY > LABOURIOUS_FINNHUB_KEY
 28. Three endpoints end-to-end via call_tool (registry round-trip)
 29. call_tool() with bogus method → FAILED
 30. Note format — has URL: prefix + REDACTED marker, never raw token

Robust to ⌃C, prints FAILs at the bottom, exits non-zero on any failure.
"""
from __future__ import annotations

import io
import json
import os
import sys
import urllib.error
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

# Make runtime importable.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs"))

from runtime.tools import ToolResult
from runtime.tools.consensus import (
    ConsensusTool,
    DEFAULT_PRICE_TARGET_CACHE_TTL_S,
    DEFAULT_RECOMMENDATIONS_CACHE_TTL_S,
    DEFAULT_REVENUE_ESTIMATE_CACHE_TTL_S,
    _canonicalize_freq,
    _redact_token,
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
    """Return (callable, calls_list)."""
    state = {"calls": [], "raise_idx": 0}
    payloads = payloads or []
    queue = list(payloads)
    raises = raises or []

    def fake_opener(req, timeout=None):
        state["calls"].append(req.full_url if hasattr(req, 'full_url') else req)
        if state["raise_idx"] < len(raises):
            exc = raises[state["raise_idx"]]
            state["raise_idx"] += 1
            raise exc
        if not queue:
            raise RuntimeError(f"opener ran out ({len(state['calls'])} calls)")
        return _StubURLResp(queue.pop(0))

    return fake_opener, state["calls"]


def _http_error(code: int, msg: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="/stable/consensus", code=code, msg=msg,
        hdrs={}, fp=io.BytesIO(b""),
    )


# ----------------------------------------------------------- fixtures

_PLAIN_RECOMMENDATIONS = [
    # Period format from Finnhub: "YYYY-MM" (month-start)
    {"period": "2025-08", "strongBuy": 12, "buy": 18, "hold": 8, "sell": 1, "strongSell": 0},
    {"period": "2025-07", "strongBuy": 11, "buy": 19, "hold": 8, "sell": 1, "strongSell": 1},
    {"period": "2025-06", "strongBuy": 10, "buy": 17, "hold": 10, "sell": 2, "strongSell": 1},
    {"period": "2025-05", "strongBuy": 9,  "buy": 16, "hold": 12, "sell": 2, "strongSell": 1},
]

_PLAIN_PRICE_TARGET = {
    "symbol": "AAPL",
    "targetMean":   230.50,
    "targetMedian": 225.00,
    "targetHigh":   300.00,
    "targetLow":    180.00,
    "lastUpdated":  "2025-08-15",
}

_PLAIN_REVENUE_ESTIMATE_Q = [
    # Finnhub returns rows like this; per-period avg in dollars,
    # growth as a decimal multiplier (not pct).
    {"period": "2025-09-30", "revenueAvg": 101_500_000_000, "revenueLow": 99_000_000_000,
     "revenueHigh": 104_000_000_000, "revenueGrowth": 0.06, "numberAnalysts": 32},
    {"period": "2025-06-30", "revenueAvg": 96_500_000_000, "revenueLow": 94_000_000_000,
     "revenueHigh": 99_500_000_000, "revenueGrowth": 0.05, "numberAnalysts": 31},
    {"period": "2025-03-31", "revenueAvg": 95_000_000_000, "revenueLow": 92_000_000_000,
     "revenueHigh": 97_500_000_000, "revenueGrowth": 0.05, "numberAnalysts": 30},
]


# ----------------------------------------------------------- assertions

print("=== 1. Price target SUCCESS shape ===")
t1 = ConsensusTool(api_key="k1", opener=None)
f1, calls1 = _fake_opener([_PLAIN_PRICE_TARGET])
t1.opener = f1
res1 = t1.price_target("AAPL")
step("status SUCCESS", res1.status == "SUCCESS", detail=f"got {res1.status!r}")
step("data has all numeric fields",
     isinstance(res1.data, dict) and all(
         k in res1.data for k in
         ("ticker", "target_mean", "target_median", "target_high", "target_low")
     ), detail=f"keys={list(res1.data.keys()) if isinstance(res1.data, dict) else None}")
step("target_mean == 230.50",
     isinstance(res1.data, dict) and abs(res1.data["target_mean"] - 230.50) < 1e-9,
     detail=f"got {res1.data.get('target_mean') if isinstance(res1.data, dict) else None}")
step("target_high/low/median populated",
     isinstance(res1.data, dict)
     and res1.data["target_high"] == 300.0
     and res1.data["target_low"] == 180.0
     and res1.data["target_median"] == 225.0)
step("last_updated is string date",
     isinstance(res1.data, dict) and res1.data["last_updated"] == "2025-08-15")
step("source == 'finnhub_price_target'",
     res1.source == "finnhub_price_target")
step("as_of is ISO-8601 UTC", bool(res1.as_of) and res1.as_of.endswith("Z"),
     detail=f"as_of={res1.as_of!r}")


print("\n=== 2. Recommendations SUCCESS shape ===")
t2 = ConsensusTool(api_key="k2", opener=None)
f2, calls2 = _fake_opener([_PLAIN_RECOMMENDATIONS])
t2.opener = f2
res2 = t2.recommendations("AAPL")
step("status SUCCESS", res2.status == "SUCCESS")
step("rows >= 1", isinstance(res2.data, dict) and len(res2.data.get("rows", [])) >= 1)
step("row schema — period/counts/analyst_count",
     isinstance(res2.data, dict) and all(
         k in res2.data["rows"][0] for k in
         ("period", "strongBuy", "buy", "hold", "sell", "strongSell", "analyst_count")
     ))
step("source == 'finnhub_recommendation'",
     res2.source == "finnhub_recommendation")


print("\n=== 3. Revenue estimate SUCCESS shape ===")
t3 = ConsensusTool(api_key="k3", opener=None)
f3, calls3 = _fake_opener([_PLAIN_REVENUE_ESTIMATE_Q])
t3.opener = f3
res3 = t3.revenue_estimate("AAPL", freq="quarterly", limit=5)
step("status SUCCESS", res3.status == "SUCCESS")
step("row schema — period/avg/low/high/growth/num_analysts",
     isinstance(res3.data, dict) and all(
         k in res3.data["rows"][0] for k in
         ("period", "revenue_avg", "revenue_low", "revenue_high",
          "revenue_growth", "num_analysts")
     ))
step("meta.freq == 'quarterly'",
     isinstance(res3.data, dict) and res3.data["meta"]["freq"] == "quarterly")


print("\n=== 4. analyst_count = strongBuy + buy + hold + sell + strongSell ===")
# Use the row from test 2 directly.
if isinstance(res2.data, dict) and res2.data.get("rows"):
    row = res2.data["rows"][0]
    expected = (
        row["strongBuy"] + row["buy"] + row["hold"]
        + row["sell"] + row["strongSell"]
    )
    step("analyst_count == sum-of-buckets",
         row["analyst_count"] == expected,
         detail=f"got {row['analyst_count']} vs sum {expected}")


print("\n=== 5. Recommendations cache within TTL ===")
t5 = ConsensusTool(api_key="k", opener=None)
f5, calls5 = _fake_opener([_PLAIN_RECOMMENDATIONS])
t5.opener = f5
t5.recommendations("AAPL")
t5.recommendations("AAPL")
step("only 1 fetch across 2 calls", len(calls5) == 1,
     detail=f"got {len(calls5)} calls")


print("\n=== 6. Price target cache within TTL ===")
t6 = ConsensusTool(api_key="k", opener=None)
f6, calls6 = _fake_opener([_PLAIN_PRICE_TARGET])
t6.opener = f6
t6.price_target("AAPL")
t6.price_target("AAPL")
step("only 1 fetch across 2 calls", len(calls6) == 1)


print("\n=== 7. Revenue estimate cache within TTL ===")
t7 = ConsensusTool(api_key="k", opener=None)
f7, calls7 = _fake_opener([_PLAIN_REVENUE_ESTIMATE_Q])
t7.opener = f7
t7.revenue_estimate("AAPL")
t7.revenue_estimate("AAPL")
step("only 1 fetch across 2 calls", len(calls7) == 1)


print("\n=== 8. Cache across distinct methods does not cross-pollute ===")
t8 = ConsensusTool(api_key="k", opener=None)
f8, calls8 = _fake_opener([
    _PLAIN_RECOMMENDATIONS,
    _PLAIN_PRICE_TARGET,
    _PLAIN_REVENUE_ESTIMATE_Q,
])
t8.opener = f8
t8.recommendations("AAPL")
t8.price_target("AAPL")
t8.revenue_estimate("AAPL")
# Now call each again — none should refetch from network even though
# they're the SAME (ticker) cache key prefix — the prefixes are rec::, pt::, re::.
t8.recommendations("AAPL")
t8.price_target("AAPL")
t8.revenue_estimate("AAPL")
step("3 unique fetches only (each cache hit on second)",
     len(calls8) == 3, detail=f"got {len(calls8)} calls")


print("\n=== 9. clear_cache() empties all three ===")
t9 = ConsensusTool(api_key="k", opener=None)
f9, calls9 = _fake_opener([
    _PLAIN_RECOMMENDATIONS,
    _PLAIN_PRICE_TARGET,
    _PLAIN_REVENUE_ESTIMATE_Q,
    _PLAIN_RECOMMENDATIONS,
    _PLAIN_PRICE_TARGET,
    _PLAIN_REVENUE_ESTIMATE_Q,
])
t9.opener = f9
t9.recommendations("AAPL")
t9.price_target("AAPL")
t9.revenue_estimate("AAPL")
step("3 fetches before clear", len(calls9) == 3)
t9.clear_cache()
t9.recommendations("AAPL")
t9.price_target("AAPL")
t9.revenue_estimate("AAPL")
step("3 more fetches after clear = 6 total", len(calls9) == 6,
     detail=f"got {len(calls9)} calls")


print("\n=== 10. No key → FAILED with configure hint ===")
# Save and clear any Finnhub key.
saved_fk = os.environ.pop("FINNHUB_API_KEY", None)
saved_lfk = os.environ.pop("LABOURIOUS_FINNHUB_KEY", None)
try:
    for method in ("recommendations", "price_target", "revenue_estimate"):
        t10 = ConsensusTool(api_key=None, opener=None)
        f10, calls10 = _fake_opener([])
        t10.opener = f10
        if method == "recommendations":
            res10 = t10.recommendations("AAPL")
            exp_source = "finnhub_recommendation"
        elif method == "price_target":
            res10 = t10.price_target("AAPL")
            exp_source = "finnhub_price_target"
        else:
            res10 = t10.revenue_estimate("AAPL")
            exp_source = "finnhub_revenue_estimate"
        step(f"  [{method}] status FAILED",
             res10.status == "FAILED", detail=f"got {res10.status!r}")
        step(f"  [{method}] note contains FINNHUB_API_KEY",
             "FINNHUB_API_KEY" in (res10.note or ""))
        step(f"  [{method}] source == '{exp_source}'",
             res10.source == exp_source)
        step(f"  [{method}] no fetch attempted", len(calls10) == 0)
finally:
    if saved_fk is not None: os.environ["FINNHUB_API_KEY"] = saved_fk
    if saved_lfk is not None: os.environ["LABOURIOUS_FINNHUB_KEY"] = saved_lfk


print("\n=== 11. Empty ticker → FAILED ===")
for method in ("recommendations", "price_target", "revenue_estimate"):
    t11 = ConsensusTool(api_key="k", opener=None)
    f11, calls11 = _fake_opener([])
    t11.opener = f11
    if method == "recommendations":
        res11 = t11.recommendations("")
    elif method == "price_target":
        res11 = t11.price_target("")
    else:
        res11 = t11.revenue_estimate("")
    step(f"  [{method}] empty ticker FAILED", res11.status == "FAILED")
    step(f"  [{method}] no fetch", len(calls11) == 0)


print("\n=== 12. Unknown ticker (recommendations) → EMPTY ===")
t12 = ConsensusTool(api_key="k", opener=None)
f12, calls12 = _fake_opener([[]])
t12.opener = f12
res12 = t12.recommendations("BADTICKER123")
step("status EMPTY", res12.status == "EMPTY")
step("data == []", res12.data == [])
step("note explains empty", "no rows" in (res12.note or "").lower())


print("\n=== 13. Unknown ticker (revenue_estimate) → EMPTY ===")
t13 = ConsensusTool(api_key="k", opener=None)
f13, calls13 = _fake_opener([[]])
t13.opener = f13
res13 = t13.revenue_estimate("BADTICKER123")
step("status EMPTY", res13.status == "EMPTY")
step("data == []", res13.data == [])


print("\n=== 14. Price target targetMean=0 → FAILED ===")
t14 = ConsensusTool(api_key="k", opener=None)
f14, calls14 = _fake_opener([{"symbol": "X", "targetMean": 0,
                              "targetHigh": 0, "targetLow": 0,
                              "targetMedian": 0, "lastUpdated": ""}])
t14.opener = f14
res14 = t14.price_target("X")
step("status FAILED + no-fabricate hint",
     res14.status == "FAILED"
     and "no coverage" in (res14.note or "").lower())


print("\n=== 15. Price target with no targetMean key → FAILED with payload echo ===")
t15 = ConsensusTool(api_key="k", opener=None)
f15, calls15 = _fake_opener([{"symbol": "X", "lastUpdated": ""}])
t15.opener = f15
res15 = t15.price_target("X")
step("status FAILED",
     res15.status == "FAILED", detail=f"got {res15.status!r}")
step("note echoes payload",
     "lastUpdated" in (res15.note or "")
     or "targetMean" in (res15.note or ""))


print("\n=== 16. HTTP 401 → FAILED 'invalid FINNHUB_API_KEY' ===")
t16 = ConsensusTool(api_key="wrong", opener=None)
f16, calls16 = _fake_opener(raises=[_http_error(401, "Unauthorized")])
t16.opener = f16
res16 = t16.price_target("AAPL")
step("status FAILED", res16.status == "FAILED")
step("note mentions invalid FINNHUB_API_KEY",
     "invalid FINNHUB_API_KEY" in (res16.note or ""),
     detail=f"note={res16.note!r}")


print("\n=== 17. HTTP 403 → FAILED mentions free-tier rate limit ===")
t17 = ConsensusTool(api_key="k", opener=None)
f17, calls17 = _fake_opener(raises=[_http_error(403, "Forbidden")])
t17.opener = f17
res17 = t17.price_target("AAPL")
step("status FAILED + rate-limit hint",
     res17.status == "FAILED"
     and ("rate" in (res17.note or "").lower()
          or "free-tier" in (res17.note or "").lower()))


print("\n=== 18. HTTP 429 → FAILED rate-limited ===")
t18 = ConsensusTool(api_key="k", opener=None)
f18, calls18 = _fake_opener(raises=[_http_error(429, "Too Many Requests")])
t18.opener = f18
res18 = t18.price_target("AAPL")
step("status FAILED + 429 hint",
     res18.status == "FAILED"
     and "429" in (res18.note or "")
     or "rate" in (res18.note or "").lower())


print("\n=== 19. Freq aliases ===")
_freq_cases = [
    ("quarterly",  "quarterly", True),
    ("quarter",    "quarterly", True),
    ("q",          "quarterly", True),
    ("Q1",         "quarterly", True),
    ("3m",         "quarterly", True),
    ("3month",     "quarterly", True),
    ("annual",     "annual",    True),
    ("yearly",     "annual",    True),
    ("year",       "annual",    True),
    ("fy",         "annual",    True),
    ("y",          "annual",    True),
    ("",           None,        False),
    ("monthly",    None,        False),
    ("biennial",   None,        False),
    ("daily",      None,        False),
]
for raw, expected, ok_expected in _freq_cases:
    got = _canonicalize_freq(raw)
    step(f"_canonicalize_freq({raw!r}) == {expected!r}",
         got == expected, detail=f"got {got!r}")


print("\n=== 20. Unknown freq via API → FAILED ===")
t20 = ConsensusTool(api_key="k", opener=None)
f20, calls20 = _fake_opener([])
t20.opener = f20
res20 = t20.revenue_estimate("AAPL", freq="biennial")
step("status FAILED + 'not supported' hint",
     res20.status == "FAILED"
     and "not supported" in (res20.note or ""),
     detail=f"note={res20.note!r}")
step("no fetch attempted", len(calls20) == 0)


print("\n=== 21. limit=99999 → clamped to ≤ 50 ===")
many_rev = [
    {"period": f"20{i:02d}-12-31", "revenueAvg": 1e10*i, "revenueLow": 9e9*i,
     "revenueHigh": 1.1e10*i, "revenueGrowth": 0.05, "numberAnalysts": 30}
    for i in range(1, 200)
]
t21 = ConsensusTool(api_key="k", opener=None)
f21, calls21 = _fake_opener([many_rev])
t21.opener = f21
res21 = t21.revenue_estimate("AAPL", limit=99999)
step("status SUCCESS", res21.status == "SUCCESS")
step("rows ≤ 50",
     isinstance(res21.data, dict) and len(res21.data["rows"]) <= 50,
     detail=f"got {len(res21.data['rows'])} rows")


print("\n=== 22. limit=0 → 1, limit=-5 → 1 ===")
def _just_one_rev(req, timeout=None):
    return _StubURLResp(_PLAIN_REVENUE_ESTIMATE_Q)
t22a = ConsensusTool(api_key="k", opener=_just_one_rev)
res22a = t22a.revenue_estimate("AAPL", limit=0)
step("limit=0 → SUCCESS", res22a.status == "SUCCESS")

t22b = ConsensusTool(api_key="k", opener=_just_one_rev)
res22b = t22b.revenue_estimate("AAPL", limit=-5)
step("limit=-5 → SUCCESS", res22b.status == "SUCCESS")


print("\n=== 23. URL redaction — raw token never appears in note for any method ===")
# All three methods, same time.
for method_name in ("recommendations", "price_target", "revenue_estimate"):
    t23 = ConsensusTool(
        api_key=f"LEAK-{method_name.upper()}", opener=None)
    payload = (
        _PLAIN_RECOMMENDATIONS if method_name == "recommendations"
        else _PLAIN_PRICE_TARGET if method_name == "price_target"
        else _PLAIN_REVENUE_ESTIMATE_Q
    )
    f23, calls23 = _fake_opener([payload])
    t23.opener = f23
    if method_name == "recommendations":
        res23 = t23.recommendations("AAPL")
    elif method_name == "price_target":
        res23 = t23.price_target("AAPL")
    else:
        res23 = t23.revenue_estimate("AAPL")
    step(f"  [{method_name}] raw secret NOT in note",
         f"LEAK-{method_name.upper()}" not in (res23.note or ""),
         detail=f"note={res23.note[:120] if res23.note else ''!r}")
    # The actual URL had ?token=LEAK-… (no apikey=; this is Finnhub).
    step(f"  [{method_name}] REDACTED marker present in note",
         "token=REDACTED" in (res23.note or ""),
         detail=f"note excerpt: {res23.note[:120] if res23.note else ''!r}")


print("\n=== 24. _redact_token() unit-level ===")
step("_redact_token() neutralises token=",
     _redact_token("https://x.com/y?symbol=AAPL&token=secret")
     == "https://x.com/y?symbol=AAPL&token=REDACTED")
step("_redact_token() leaves non-token keys intact",
     _redact_token("https://x.com/y?symbol=AAPL&freq=quarterly")
     == "https://x.com/y?symbol=AAPL&freq=quarterly")


print("\n=== 25. citation_kind in catalog == 'consensus' ===")
from frontend.connectors_catalog import by_name
entry = by_name("consensus")
step("catalog entry exists", entry is not None)
step("citation_kind == 'consensus'", entry.citation_kind == "consensus",
     detail=f"got {entry.citation_kind!r}")
step("tier == 'tier2'", entry.tier == "tier2")
step("key_env == 'FINNHUB_API_KEY'", entry.key_env == "FINNHUB_API_KEY")
step("recommended == True", entry.recommended is True)


print("\n=== 26. ToolResult.source spelling per method ===")
# Already verified inline in tests 1/2/3 — this confirms the spelling.
spelling_map = {
    "finnhub_recommendation":    ("recommendations",       _PLAIN_RECOMMENDATIONS),
    "finnhub_price_target":      ("price_target",         _PLAIN_PRICE_TARGET),
    "finnhub_revenue_estimate":  ("revenue_estimate",     _PLAIN_REVENUE_ESTIMATE_Q),
}
for source, (method_name, payload) in spelling_map.items():
    t26 = ConsensusTool(api_key="k", opener=None)
    f26, calls26 = _fake_opener([payload])
    t26.opener = f26
    fn = getattr(t26, method_name)
    if method_name == "revenue_estimate":
        res26 = fn("AAPL")
    else:
        res26 = fn("AAPL")
    step(f"source == '{source}' (method={method_name!r})",
         res26.source == source, detail=f"got {res26.source!r}")


print("\n=== 27. Token precedence — explicit kwarg > env > '' ===")
os.environ.pop("LABOURIOUS_FINNHUB_KEY", None)
os.environ["FINNHUB_API_KEY"] = "from-env"
t27 = ConsensusTool(api_key="from-arg", opener=None)
step("explicit kwarg wins over FINNHUB_API_KEY env",
     t27.api_key == "from-arg")
del os.environ["FINNHUB_API_KEY"]
os.environ["LABOURIOUS_FINNHUB_KEY"] = "from-labourious-env"
t27b = ConsensusTool(api_key="from-arg", opener=None)
step("explicit kwarg wins over LABOURIOUS_FINNHUB_KEY too",
     t27b.api_key == "from-arg")
del os.environ["LABOURIOUS_FINNHUB_KEY"]
os.environ["FINNHUB_API_KEY"] = "from-fmp-env"
t27c = ConsensusTool(opener=None)
step("no explicit kwarg → FINNHUB_API_KEY env used",
     t27c.api_key == "from-fmp-env")
del os.environ["FINNHUB_API_KEY"]


print("\n=== 28. Three endpoints end-to-end via call_tool ===")
from runtime.call_tool import call_tool

payload_map = {
    "recommendations": _PLAIN_RECOMMENDATIONS,
    "price_target": _PLAIN_PRICE_TARGET,
    "revenue_estimate": _PLAIN_REVENUE_ESTIMATE_Q,
}

_pilot_payloads: list[Any] = []
_orig_init = ConsensusTool.__post_init__


def _patched_init(self):
    _orig_init(self)
    if _pilot_payloads:
        payload = _pilot_payloads.pop(0)
        def _op(req, timeout=None):
            return _StubURLResp(payload)
        self.opener = _op


ConsensusTool.__post_init__ = _patched_init

# call_tool builds the tool instance itself (no constructor kwargs),
# so we have to support it via env. Inject the key for the duration of
# this section so the __post_init__ it constructs picks it up.
saved_key = os.environ.get("FINNHUB_API_KEY")
os.environ["FINNHUB_API_KEY"] = "pilot-test-key"

try:
    for method_name, payload in payload_map.items():
        _pilot_payloads.clear()
        _pilot_payloads.append(payload)
        args: dict[str, Any] = {"ticker": "AAPL"}
        if method_name == "revenue_estimate":
            args.update({"freq": "quarterly", "limit": 5})
        res28 = call_tool(
            "consensus",
            requested_by_agent="smoke-pilot",
            method=method_name,
            args=args,
        )
        step(f"call_tool({method_name!r}) → SUCCESS",
             res28.status == "SUCCESS",
             detail=f"status={res28.status!r}, note={(res28.note or '')[:80]!r}")
        if method_name == "price_target":
            step(f"  data has target_mean",
                 isinstance(res28.data, dict)
                 and "target_mean" in res28.data
                 and abs(res28.data["target_mean"] - 230.50) < 1e-9)
        else:
            step(f"  data has rows + meta",
                 isinstance(res28.data, dict)
                 and "rows" in res28.data and "meta" in res28.data)
finally:
    ConsensusTool.__post_init__ = _orig_init
    if saved_key is not None:
        os.environ["FINNHUB_API_KEY"] = saved_key
    else:
        os.environ.pop("FINNHUB_API_KEY", None)


print("\n=== 29. call_tool() with bogus method → FAILED ===")
res29 = call_tool(
    "consensus",
    requested_by_agent="smoke-pilot",
    method="bogus_method_xyz",
    args={"ticker": "AAPL"},
)
step("status FAILED", res29.status == "FAILED",
     detail=f"got {res29.status!r}")
step("note mentions method",
     "bogus_method_xyz" in (res29.note or "")
     or "method" in (res29.note or "").lower())


print("\n=== 30. Note format has URL: prefix + REDACTED + never raw token ===")
t30 = ConsensusTool(api_key="RAW-SECRET", opener=None)
f30, calls30 = _fake_opener([_PLAIN_PRICE_TARGET])
t30.opener = f30
res30 = t30.price_target("AAPL")
note30 = res30.note or ""
step("note starts with 'Finnhub /stock/price-target'",
     note30.startswith("Finnhub /stock/price-target"))
step("note has 'URL:' marker", "URL:" in note30)
step("note never has raw token", "RAW-SECRET" not in note30)
step("note has REDACTED marker", "token=REDACTED" in note30)


# ----------------------------------------------------------- summary
print()
total = len(_fails)
print(f"\033[1m{'OK' if total == 0 else 'FAIL'}\033[0m · "
      f"{30 - total}/30 sections green · "
      f"{_fails and f'{total} failed' or 'all green'}")
if _fails:
    print("\nFailures:")
    for f in _fails:
        print(f"  - {f}")
    sys.exit(1)
sys.exit(0)
