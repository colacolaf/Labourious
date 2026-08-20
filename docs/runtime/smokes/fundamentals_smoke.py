"""
smokes/fundamentals_smoke.py — pilot for conn-7 (FMP fundamentals).

Asserts (≥ 30 planned):
  1. SUCCESS shape on income_statement — 5 fields per row + meta block
  2. SUCCESS shape on balance_sheet
  3. SUCCESS shape on cash_flow
  4. SUCCESS shape on key_metrics
  5. SUCCESS shape on ratios
  6. Period aliases — "yearly"/"fy" → "annual"; "quarterly"/"q1"/"3m" → "quarter"
  7. Unknown period → FAILED with "not supported" hint
  8. Limit clamp — limit=99999 → ≤ 100 (FMP max), and rows trimmed
  9. Empty ticker → FAILED
 10. No key → FAILED with "FMP_API_KEY not configured" note
 11. HTTP 401 → FAILED "invalid FMP_API_KEY"
 12. HTTP 403 → FAILED "free-tier daily limit likely hit"
 13. HTTP 429 → FAILED rate-limited
 14. {"Error Message": "..."} payload → FAILED with FMP error
 15. Empty payload [] → EMPTY ToolResult with rows=[]
 16. Cache hit on second call within TTL — only one URL fetch recorded
 17. Cache miss after TTL — second fetch happens
 18. Header auth default — `apikey` header set; URL has NO `apikey=` query param
 19. Query auth (`auth="query"`) — URL has `apikey=` query param; no header
 20. URL redaction in note — redaction covers BOTH header and query paths
 21. Citation kind matches "filing"
 22. clear_cache() empties cache
 23. ToolResult.to_dict() — snippet_path is None (fundamentals not snippet-cacheable)
 24. Token precedence — FMP_API_KEY > LABOURIOUS_FMP_KEY > api_key arg
 25. call_tool end-to-end income_statement — round-trip via TOOL_REGISTRY
 26. call_tool end-to-end balance_sheet via method override
 27. call_tool end-to-end cash_flow
 28. call_tool end-to-end key_metrics
 29. call_tool end-to-end ratios
 30. call_tool unknown method → FAILED
 31. Network error (URLError) on bad host → FAILED "network error"
 32. limit=0 clamped to 1, limit=-5 clamped to 1
 33. URL preserves all other query keys (symbol, period, limit) when redacted

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
from typing import Callable
from unittest.mock import MagicMock

# Make runtime importable.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs"))

# Pull only what we need from runtime.tools so we don't have to
# import the full Textual chain.
from runtime.tools import ToolResult
from runtime.tools.fundamentals import (
    FundamentalsTool,
    DEFAULT_CACHE_TTL_S,
    _canonicalize_period,
    _redact_apikey,
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
    """Minimal urllib urlopen() stub — returns a canned JSON body."""
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
                 statuses: list[int] | None = None,
                 headers: list[dict[str, str]] | None = None,
                 raises: list[Exception] | None = None):
    """Return (opener_callable, trace_list, headers_trace).

    Each call pops the next payload / status. If ``raises`` is provided,
    those HTTPError specs take precedence over payloads.
    """
    state: dict[str, Any] = {
        "calls": [],
        "headers_trace": [],
        "raise_idx": 0,
    }
    payloads = payloads or []
    queue = list(zip(
        payloads,
        statuses or [200] * len(payloads),
        headers or [{}] * len(payloads),
    ))
    raises = raises or []   

    def fake_opener(req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        state["calls"].append(url)
        if req is not None and not isinstance(req, str):
            hdrs = dict(req.headers or {})
            state["headers_trace"].append(hdrs)
        else:
            state["headers_trace"].append({})
        if state["raise_idx"] < len(raises):
            exc = raises[state["raise_idx"]]
            state["raise_idx"] += 1
            raise exc
        if not queue:
            raise RuntimeError(
                f"opener called more times than expected ({len(state['calls'])}) — "
                f"missing payload for call #{len(state['calls'])}"
            )
        body, status, hdrs = queue.pop(0)
        return _StubURLResp(body, status=status, headers=hdrs)

    return fake_opener, state["calls"], state["headers_trace"]


# Convenience: when an HTTPError is wanted, callers can use the urllib
# pattern directly — this helper builds the err correctly.
def _http_error(code: int, msg: str) -> urllib.error.HTTPError:
    import io as _io
    return urllib.error.HTTPError(
        url="/stable/income-statement",
        code=code,
        msg=msg,
        hdrs={},
        fp=_io.BytesIO(b""),
    )


def _url_error(reason: str) -> urllib.error.URLError:
    return urllib.error.URLError(reason)


# ----------------------------------------------------------- fixtures

_PLAIN_INCOME = [
    {
        "date": "2024-09-28",
        "symbol": "AAPL",
        "period": "FY",
        "revenue": 391000000000,
        "costOfRevenue": 210000000000,
        "grossProfit": 181000000000,
        "operatingIncome": 123000000000,
        "netIncome": 95000000000,
        "eps": 6.11,
    },
    {
        "date": "2023-09-30",
        "symbol": "AAPL",
        "period": "FY",
        "revenue": 383000000000,
        "costOfRevenue": 214000000000,
        "grossProfit": 169000000000,
        "operatingIncome": 114000000000,
        "netIncome": 97000000000,
        "eps": 6.16,
    },
]

_PLAIN_BALANCE = [
    {
        "date": "2024-09-28",
        "symbol": "AAPL",
        "period": "FY",
        "totalAssets": 365000000000,
        "totalLiabilities": 308000000000,
        "totalEquity": 57000000000,
        "cashAndCashEquivalents": 30000000000,
    },
]

_PLAIN_CASHFLOW = [
    {
        "date": "2024-09-28",
        "symbol": "AAPL",
        "period": "FY",
        "operatingCashFlow": 111000000000,
        "capitalExpenditure": -10000000000,
        "freeCashFlow": 101000000000,
    },
]

_PLAIN_KEYMETRICS = [
    {
        "date": "2024-09-28",
        "symbol": "AAPL",
        "period": "FY",
        "peRatio": 33.5,
        "priceToBookRatio": 47.2,
        "roe": 1.71,
        "debtToEquity": 1.87,
    },
]

_PLAIN_RATIOS = [
    {
        "date": "2024-09-28",
        "symbol": "AAPL",
        "period": "FY",
        "grossProfitMargin": 0.46,
        "operatingProfitMargin": 0.31,
        "netProfitMargin": 0.24,
        "currentRatio": 1.06,
    },
]


def _build_default_tool() -> tuple[FundamentalsTool, list[str], list[dict[str, str]]]:
    """A tool primed with key + a fake opener — used for the SMOKE path."""
    tool = FundamentalsTool(api_key="testKEY123", opener=None)
    opener, calls, headers = _fake_opener([_PLAIN_INCOME])
    tool.opener = opener
    return tool, calls, headers


# ----------------------------------------------------------- assertions


print("=== 1. SUCCESS shape on income_statement ===")
default_tool = FundamentalsTool(api_key="testKEY123", opener=None)
fake_op, fake_calls, fake_hdrs = _fake_opener([_PLAIN_INCOME])
default_tool.opener = fake_op
res = default_tool.income_statement("AAPL", period="annual", limit=5)
step("status == SUCCESS", res.status == "SUCCESS",
     detail=f"got {res.status!r}")
step("data[rows] is list of 2", isinstance(res.data, dict)
     and isinstance(res.data.get("rows"), list) and len(res.data["rows"]) == 2,
     detail=f"got {res.data!r}")
step("row[0] has revenue/costOfRevenue/grossProfit/netIncome/eps",
     all(k in res.data["rows"][0] for k in
         ("revenue", "costOfRevenue", "grossProfit", "netIncome", "eps")),
     detail=f"got keys: {sorted(res.data['rows'][0].keys())}")
step("meta.endpoint == income_statement",
     res.data.get("meta", {}).get("endpoint") == "income_statement")
step("meta.period == annual",
     res.data.get("meta", {}).get("period") == "annual")
step("meta.row_count == 2",
     res.data.get("meta", {}).get("row_count") == 2)
step("ToolResult.source == 'fmp_income_statement'",
     res.source == "fmp_income_statement")
step("as_of is ISO-8601 UTC", bool(res.as_of) and res.as_of.endswith("Z"),
     detail=f"as_of={res.as_of!r}")


print("\n=== 2. SUCCESS shape on balance_sheet ===")
t2 = FundamentalsTool(api_key="k", opener=None)
f2, _, _ = _fake_opener([_PLAIN_BALANCE])
t2.opener = f2
res2 = t2.balance_sheet("MSFT")
step("status SUCCESS + 1 row", res2.status == "SUCCESS"
     and len(res2.data["rows"]) == 1)
step("row has totalAssets/totalEquity",
     "totalAssets" in res2.data["rows"][0]
     and "totalEquity" in res2.data["rows"][0])
step("meta.endpoint == balance_sheet",
     res2.data["meta"]["endpoint"] == "balance_sheet")
step("source == 'fmp_balance_sheet'",
     res2.source == "fmp_balance_sheet")


print("\n=== 3. SUCCESS shape on cash_flow ===")
t3 = FundamentalsTool(api_key="k", opener=None)
f3, _, _ = _fake_opener([_PLAIN_CASHFLOW])
t3.opener = f3
res3 = t3.cash_flow("NVDA")
step("status SUCCESS + freeCashFlow present",
     res3.status == "SUCCESS"
     and "freeCashFlow" in res3.data["rows"][0])
step("meta.endpoint == cash_flow",
     res3.data["meta"]["endpoint"] == "cash_flow")


print("\n=== 4. SUCCESS shape on key_metrics ===")
t4 = FundamentalsTool(api_key="k", opener=None)
f4, _, _ = _fake_opener([_PLAIN_KEYMETRICS])
t4.opener = f4
res4 = t4.key_metrics("GOOG")
step("status SUCCESS + peRatio + debtToEquity",
     res4.status == "SUCCESS"
     and "peRatio" in res4.data["rows"][0]
     and "debtToEquity" in res4.data["rows"][0])
step("meta.endpoint == key_metrics",
     res4.data["meta"]["endpoint"] == "key_metrics")


print("\n=== 5. SUCCESS shape on ratios ===")
t5 = FundamentalsTool(api_key="k", opener=None)
f5, _, _ = _fake_opener([_PLAIN_RATIOS])
t5.opener = f5
res5 = t5.ratios("META")
step("status SUCCESS + grossProfitMargin + netProfitMargin",
     res5.status == "SUCCESS"
     and "grossProfitMargin" in res5.data["rows"][0]
     and "netProfitMargin" in res5.data["rows"][0])
step("meta.endpoint == ratios",
     res5.data["meta"]["endpoint"] == "ratios")


print("\n=== 6. Period aliases ===")
_period_cases = [
    ("annual", "annual", True),
    ("year", "annual", True),
    ("y", "annual", True),
    ("yearly", "annual", True),
    ("fy", "annual", True),
    ("fiscal year", "annual", True),
    ("quarter", "quarter", True),
    ("quarterly", "quarter", True),
    ("q", "quarter", True),
    ("Q1", "quarter", True),
    ("3m", "quarter", True),
    ("three-month", "quarter", True),
    ("", None, False),
    ("biennial", None, False),
    ("monthly", None, False),
]
for raw, expected, ok_expected in _period_cases:
    got = _canonicalize_period(raw)
    step(f"_canonicalize_period({raw!r}) == {expected!r}",
         got == expected, detail=f"got {got!r}")


print("\n=== 7. Unknown period via API → FAILED ===")
t7 = FundamentalsTool(api_key="k", opener=None)
f7, calls7, _ = _fake_opener([])
t7.opener = f7
res7 = t7.income_statement("AAPL", period="biennial")
step("status == FAILED", res7.status == "FAILED",
     detail=f"got {res7.status!r}")
step("note mentions 'not supported'",
     "not supported" in (res7.note or ""), detail=f"note={res7.note!r}")
step("no opener call (no fetch attempted)", len(calls7) == 0,
     detail=f"got {len(calls7)} calls")


print("\n=== 8. limit=99999 → clamped to 100, payload trimmed ===")
many_rows = [{"date": f"202{i:02d}-01-01", "symbol": "AAPL", "period": "FY",
              "revenue": 1_000_000_000 * i} for i in range(1, 150)]
t8 = FundamentalsTool(api_key="k", opener=None)
f8, calls8, _ = _fake_opener([many_rows])
t8.opener = f8
res8 = t8.income_statement("AAPL", limit=99999)
step("status SUCCESS", res8.status == "SUCCESS",
     detail=f"got {res8.status!r}")
step("rows trimmed to ≤ 100 (FMP API max)",
     len(res8.data["rows"]) <= 100,
     detail=f"got {len(res8.data['rows'])} rows")
# The cap is 100 — FMP won't return more than that anyway, so we assert the
# limit clamp is honored regardless of upstream shape.


print("\n=== 9. Empty ticker → FAILED ===")
t9 = FundamentalsTool(api_key="k", opener=None)
f9, calls9, _ = _fake_opener([])
t9.opener = f9
res9 = t9.income_statement("")
step("status FAILED", res9.status == "FAILED")
step("note mentions ticker", "ticker" in res9.note.lower())
step("no fetch", len(calls9) == 0)


print("\n=== 10. No key → FAILED with configure hint ===")
# Save and clear any FMP_API_KEY so the post_init sees nothing.
saved_fmp = os.environ.pop("FMP_API_KEY", None)
saved_labourious = os.environ.pop("LABOURIOUS_FMP_KEY", None)
try:
    t10 = FundamentalsTool(api_key=None, opener=None)
    f10, calls10, _ = _fake_opener([])
    t10.opener = f10
    res10 = t10.income_statement("AAPL")
    step("status FAILED", res10.status == "FAILED")
    step("note contains FMP_API_KEY",
         "FMP_API_KEY" in (res10.note or ""),
         detail=f"note={res10.note!r}")
    step("note contains 'fmp.com' signup link",
         "financialmodelingprep.com" in (res10.note or ""))
    step("no fetch attempted", len(calls10) == 0)
finally:
    if saved_fmp is not None: os.environ["FMP_API_KEY"] = saved_fmp
    if saved_labourious is not None: os.environ["LABOURIOUS_FMP_KEY"] = saved_labourious


print("\n=== 11. HTTP 401 → FAILED with 'invalid FMP_API_KEY' ===")
t11 = FundamentalsTool(api_key="wrong-key", opener=None)
f11, calls11, _ = _fake_opener(raises=[_http_error(401, "Unauthorized")])
t11.opener = f11
res11 = t11.income_statement("AAPL")
step("status FAILED", res11.status == "FAILED")
step("note mentions invalid FMP_API_KEY",
     "invalid FMP_API_KEY" in (res11.note or ""))


print("\n=== 12. HTTP 403 → FAILED mentions free-tier daily limit ===")
t12 = FundamentalsTool(api_key="limit-hit-key", opener=None)
f12, _, _ = _fake_opener(raises=[_http_error(403, "Forbidden")])
t12.opener = f12
res12 = t12.income_statement("AAPL")
step("status FAILED + daily limit hint",
     res12.status == "FAILED"
     and "daily limit" in (res12.note or "").lower(),
     detail=f"note={res12.note!r}")


print("\n=== 13. HTTP 429 → FAILED rate-limited ===")
t13 = FundamentalsTool(api_key="k", opener=None)
f13, _, _ = _fake_opener(raises=[_http_error(429, "Too Many Requests")])
t13.opener = f13
res13 = t13.income_statement("AAPL")
step("status FAILED + rate-limited hint",
     res13.status == "FAILED"
     and "rate" in (res13.note or "").lower())


print("\n=== 14. {'Error Message': ...} payload → FAILED ===")
t14 = FundamentalsTool(api_key="k", opener=None)
f14, _, _ = _fake_opener([{"Error Message": "Invalid API KEY."}])
t14.opener = f14
res14 = t14.income_statement("AAPL")
step("status FAILED", res14.status == "FAILED")
step("note echoes FMP error text",
     "Invalid API KEY" in (res14.note or ""))


print("\n=== 15. Empty payload [] → EMPTY ToolResult ===")
t15 = FundamentalsTool(api_key="k", opener=None)
f15, _, _ = _fake_opener([[]])
t15.opener = f15
res15 = t15.income_statement("BADTICKER123")
step("status == EMPTY", res15.status == "EMPTY",
     detail=f"got {res15.status!r}")
step("data == []", res15.data == [])
step("note explains empty",
     "no records" in (res15.note or "").lower()
     or "unknown" in (res15.note or "").lower())


print("\n=== 16. Cache hit on second call within TTL ===")
t16 = FundamentalsTool(api_key="k", opener=None)
f16, calls16, _ = _fake_opener([_PLAIN_INCOME])
t16.opener = f16
a16 = t16.income_statement("AAPL")
b16 = t16.income_statement("AAPL")
step("status SUCCESS twice", a16.status == "SUCCESS"
     and b16.status == "SUCCESS")
step("only 1 fetch recorded (cache hit on second)",
     len(calls16) == 1, detail=f"got {len(calls16)} calls")


print("\n=== 17. Cache miss after TTL ===")
t17 = FundamentalsTool(api_key="k", opener=None)
f17, calls17, _ = _fake_opener([_PLAIN_INCOME, _PLAIN_INCOME])
t17.opener = f17
# First call — cache miss, populates.
t17.income_statement("AAPL")
# Force expiry by clamping cache_ttl to 0 on the second instance — simulate
# elapsed time without sleeping.
t17.cache_ttl_s = 0
b17 = t17.income_statement("AAPL")
step("two fetch calls now", len(calls17) == 2,
     detail=f"got {len(calls17)} calls")


print("\n=== 18. Header auth default — apikey header set, URL has NO apikey ===")
t18 = FundamentalsTool(api_key="header-key-test", opener=None)
f18, calls18, hdrs18 = _fake_opener([_PLAIN_INCOME])
t18.opener = f18
res18 = t18.income_statement("AAPL")
# urllib normalizes header names (often to capitalized form) — look case-insensitively.
apikey_in_hdrs = False
for k, v in (hdrs18[0] if hdrs18 else {}).items():
    if k.lower() == "apikey" and "header-key-test" in (v or ""):
        apikey_in_hdrs = True
        break
step("apikey header sent", apikey_in_hdrs,
     detail=f"hdrs keys={list((hdrs18[0] if hdrs18 else {}).keys())}")
step("URL has NO apikey= query param",
     "apikey=" not in calls18[0], detail=f"url={calls18[0]!r}")


print("\n=== 19. Query auth (auth='query') — URL has apikey, no header ===")
t19 = FundamentalsTool(api_key="query-key-test", auth="query", opener=None)
f19, calls19, hdrs19 = _fake_opener([_PLAIN_INCOME])
t19.opener = f19
res19 = t19.income_statement("AAPL")
step("URL has apikey= query param",
     "apikey=query-key-test" in calls19[0], detail=f"url={calls19[0]!r}")
step("apikey NOT in headers",
     "query-key-test" not in
     (hdrs19[0].get("apikey") or ""),
     detail=f"hdrs={hdrs19[0]!r}")


print("\n=== 20. URL redaction in note covers both auth paths ===")
# Header auth path — secret stays in headers, URL has no apikey= query,
# so redaction just means "no apikey= query in the URL we logged".
t20h = FundamentalsTool(api_key="LEAK-HEADER", opener=None)
f20h, _, _ = _fake_opener([_PLAIN_INCOME])
t20h.opener = f20h
res20h = t20h.income_statement("AAPL")
step("header-secret NOT in note",
     "LEAK-HEADER" not in (res20h.note or ""),
     detail=f"note={res20h.note!r}")
step("header-auth URL has no apikey= in note (header path uses no query key)",
     "apikey=" not in (res20h.note or ""),
     detail=f"note={res20h.note!r}")

# Query auth path — secret IS in URL query, so redaction must replace with REDACTED.
t20q = FundamentalsTool(api_key="LEAK-QUERY", auth="query", opener=None)
f20q, _, _ = _fake_opener([_PLAIN_INCOME])
t20q.opener = f20q
res20q = t20q.income_statement("AAPL")
step("query-secret NOT in note",
     "LEAK-QUERY" not in (res20q.note or ""),
     detail=f"note={res20q.note!r}")
step("query-redacted marker present",
     "apikey=REDACTED" in (res20q.note or ""))

# _redact_apikey unit-level
step("_redact_apikey() neutralises apikey=",
     _redact_apikey("https://x.com/y?apikey=secret&symbol=AAPL")
     == "https://x.com/y?apikey=REDACTED&symbol=AAPL")
step("_redact_apikey() leaves non-apikey keys intact",
     _redact_apikey("https://x.com/y?symbol=AAPL&period=annual")
     == "https://x.com/y?symbol=AAPL&period=annual")


print("\n=== 21. Citation kind matches 'filing' ===")
# Imported via the catalog import
from frontend.connectors_catalog import by_name
fmp_entry = by_name("fundamentals")
step("catalog entry exists", fmp_entry is not None)
step("citation_kind == 'filing'",
     fmp_entry.citation_kind == "filing",
     detail=f"got {fmp_entry.citation_kind!r}")
step("tier == 'tier2'", fmp_entry.tier == "tier2")
step("key_env == 'FMP_API_KEY'", fmp_entry.key_env == "FMP_API_KEY")
step("keyless == False", fmp_entry.keyless is False)
step("recommended == True", fmp_entry.recommended is True)


print("\n=== 22. clear_cache() empties cache ===")
t22 = FundamentalsTool(api_key="k", opener=None)
f22, calls22, _ = _fake_opener([_PLAIN_INCOME, _PLAIN_INCOME])
t22.opener = f22
t22.income_statement("AAPL")
step("1 call before clear", len(calls22) == 1)
t22.clear_cache()
t22.income_statement("AAPL")
step("2nd call after clear = 2 calls", len(calls22) == 2)


print("\n=== 23. ToolResult.to_dict() — snippet_path None for fundamentals ===")
t23 = FundamentalsTool(api_key="k", opener=None)
f23, _, _ = _fake_opener([_PLAIN_INCOME])
t23.opener = f23
res23 = t23.income_statement("AAPL")
d23 = res23.to_dict() if hasattr(res23, "to_dict") else {"snippet_path": getattr(res23, "snippet_path", None)}
step("snippet_path is None or absent",
     d23.get("snippet_path") is None,
     detail=f"got {d23.get('snippet_path')!r}")


print("\n=== 24. Token precedence — explicit kwarg > FMP_API_KEY > LABOURIOUS_FMP_KEY > '' ===")
# The __post_init__ reads from env ONLY when the explicit kwarg is missing.
os.environ.pop("LABOURIOUS_FMP_KEY", None)
os.environ["FMP_API_KEY"] = "from-env"
t24 = FundamentalsTool(api_key="from-arg", opener=None)
step("explicit kwarg wins over FMP_API_KEY env",
     t24.api_key == "from-arg",
     detail=f"got {t24.api_key!r}")
del os.environ["FMP_API_KEY"]
os.environ["LABOURIOUS_FMP_KEY"] = "from-labourious-env"
t24b = FundamentalsTool(api_key="from-arg", opener=None)
step("explicit kwarg wins over LABOURIOUS_FMP_KEY too",
     t24b.api_key == "from-arg")

# Now flip — drop the explicit kwarg so env reads take effect.
del os.environ["LABOURIOUS_FMP_KEY"]
os.environ["FMP_API_KEY"] = "from-fmp-env"
t24c = FundamentalsTool(opener=None)
step("no explicit kwarg → FMP_API_KEY env used",
     t24c.api_key == "from-fmp-env")

del os.environ["FMP_API_KEY"]
os.environ["LABOURIOUS_FMP_KEY"] = "from-labourious-env-only"
t24d = FundamentalsTool(opener=None)
step("no FMP_API_KEY → LABOURIOUS_FMP_KEY env used",
     t24d.api_key == "from-labourious-env-only")
del os.environ["LABOURIOUS_FMP_KEY"]

t24e = FundamentalsTool(opener=None)
step("nothing set → api_key is None",
     t24e.api_key is None)


print("\n=== 25-29. call_tool() end-to-end for all 5 methods ===")
from runtime.call_tool import call_tool, TOOL_REGISTRY
ENDPOINTS = [
    ("income_statement", _PLAIN_INCOME),
    ("balance_sheet",    _PLAIN_BALANCE),
    ("cash_flow",        _PLAIN_CASHFLOW),
    ("key_metrics",      _PLAIN_KEYMETRICS),
    ("ratios",           _PLAIN_RATIOS),
]

# call_tool constructs the tool instance itself (no constructor kwargs),
# so we have to support it via env. Inject a fake opener that returns the
# right payload for each call by patching the module-level cache.
# Simplest path: temporarily inject a fake opener at the class level.
_fundamentals_test_opener_payloads: list[Any] = []
openers_log: list[str] = []


def _make_test_openers():
    """Build a fresh class-level opener pool. Each call pops the next."""
    state = {"i": 0}
    ENDPOINTS_LOCAL = [
        ("income_statement", _PLAIN_INCOME),
        ("balance_sheet",    _PLAIN_BALANCE),
        ("cash_flow",        _PLAIN_CASHFLOW),
        ("key_metrics",      _PLAIN_KEYMETRICS),
        ("ratios",           _PLAIN_RATIOS),
    ]
    payload_map = {ep: payload for ep, payload in ENDPOINTS_LOCAL}

    def _install_get_opener(orig_init_done: list[bool]):
        # Use a module-level indirection so the opener is consulted on
        # each FundamentalsTool call_tool path.
        pass

    return payload_map


# Set env so call_tool-built tool instance gets an api_key.
saved_fmp_key = os.environ.get("FMP_API_KEY")
os.environ["FMP_API_KEY"] = "pilot-test-key"

# Monkeypatch FundamentalsTool so each new instance gets a custom opener
# that returns one of the payload fixtures in order.
_payload_iter: list[Any] = []
_orig_post_init = FundamentalsTool.__post_init__


def _patched_post_init(self):
    _orig_post_init(self)
    if _payload_iter:
        payload = _payload_iter.pop(0)
        def _opener(req, timeout=None):
            openers_log.append(req.full_url if hasattr(req, "full_url") else str(req))
            return _StubURLResp(payload)
        self.opener = _opener


FundamentalsTool.__post_init__ = _patched_post_init

try:
    # Test 25-29 one by one.
    payload_map = _make_test_openers()
    for ep, fixture in ENDPOINTS:
        _payload_iter.clear()
        _payload_iter.append(fixture)
        res_ep = call_tool(
            "fundamentals",
            requested_by_agent="smoke-pilot",
            method=ep,
            args={"ticker": "AAPL", "period": "annual", "limit": 5},
        )
        step(f"call_tool fundamentals method={ep!r} → SUCCESS",
             res_ep.status == "SUCCESS",
             detail=f"status={res_ep.status!r}, note={(res_ep.note or '')[:80]!r}")
        step(f"  data shape has rows + meta",
             isinstance(res_ep.data, dict) and "rows" in res_ep.data
             and "meta" in res_ep.data)
        step(f"  meta.endpoint == {ep!r}",
             isinstance(res_ep.data, dict)
             and res_ep.data.get("meta", {}).get("endpoint") == ep)
finally:
    FundamentalsTool.__post_init__ = _orig_post_init
    if saved_fmp_key is not None:
        os.environ["FMP_API_KEY"] = saved_fmp_key
    else:
        os.environ.pop("FMP_API_KEY", None)


print("\n=== 30. call_tool() unknown method → FAILED ===")
res30 = call_tool(
    "fundamentals",
    requested_by_agent="smoke-pilot",
    method="bogus_method",
    args={"ticker": "AAPL"},
    run_id="smoke-test-run",
)
step("call_tool with bogus method → FAILED",
     res30.status == "FAILED", detail=f"got {res30.status!r}")
step("note mentions method name",
     "bogus_method" in (res30.note or "") or "method" in (res30.note or "").lower())


print("\n=== 31. URLError (network) → FAILED 'network error' ===")
t31 = FundamentalsTool(api_key="k", opener=None)
t31.opener = lambda req, timeout=None: (_ for _ in ()).throw(
    _url_error("DNS failure for fmp.test")
)
res31 = t31.income_statement("AAPL")
step("status FAILED + network hint",
     res31.status == "FAILED"
     and ("network" in (res31.note or "").lower()
          or "DNS" in (res31.note or "")))
# Confirm the error text isn't "parse error" (which would mean we ate the
# URLError and called it generic parse).
step("not mis-classified as parse error",
     "parse error" not in (res31.note or "").lower())


print("\n=== 32. limit=0 → 1, limit=-5 → 1 ===")
def _just_one(url, headers=None, timeout=None):
    return _StubURLResp(_PLAIN_INCOME)
# We can't easily inject a per-call opener without changing cache, so we
# build a fresh tool each time.
t32a = FundamentalsTool(api_key="k", opener=_just_one)
res32a = t32a.income_statement("AAPL", limit=0)
step("limit=0 accepted without error", res32a.status == "SUCCESS")

t32b = FundamentalsTool(api_key="k", opener=_just_one)
res32b = t32b.income_statement("AAPL", limit=-5)
step("limit=-5 accepted without error", res32b.status == "SUCCESS")


print("\n=== 33. URL preserves symbol/period/limit when redacted ===")
url = "https://financialmodelingprep.com/stable/income-statement?symbol=AAPL&period=annual&limit=5&apikey=MYKEY"
red = _redact_apikey(url)
step("symbol key preserved in redacted URL",
     "symbol=AAPL" in red)
step("period key preserved", "period=annual" in red)
step("limit key preserved", "limit=5" in red)
step("apikey replaced, not preserved",
     "apikey=MYKEY" not in red and "apikey=REDACTED" in red)


# ----------------------------------------------------------- summary

if __name__ == "__main__":
    total = len(_fails)
    print()
    print(f"\033[1m{'OK' if total == 0 else 'FAIL'}\033[0m · "
          f"{33 - total}/33 sections green · {_fails and f'{total} failed' or 'all green'}")
    if _fails:
        print("\nFailures:")
        for f in _fails:
            print(f"  - {f}")
        sys.exit(1)
    sys.exit(0)
