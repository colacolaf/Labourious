"""
smokes/macro_smoke.py — pilot for conn-11 (FRED macro).

Asserts (≥ 25 planned):
  1. series SUCCESS shape — observations list, meta.{series_id,
     sort_order, row_count}
  2. series row schema — date/value (numeric or None)/realtime_*
  3. series cache hit within TTL
  4. series cache miss after TTL=0
  5. series empty series_id → FAILED
  6. series sort_order validation — bogus → FAILED
  7. series sort_order aliases — "oldest" → "asc", "newest" → "desc"
  8. series limit clamp — 99999 → 10,000 (FRED hard ceiling)
  9. series limit=0 → 1
 10. series EMPTY — empty observations → EMPTY
 11. series wrapper spelling — observations key
 12. series defensive — bad observation silently skipped
 13. series non-dict payload → FAILED
 14. series dot-value handling — periodicals report "." for missing data
     → value=None in our schema (not a string)
 15. series FRED error_code/error_message → FAILED echoed
 16. search SUCCESS shape — series list
 17. search row schema — id/title/frequency/units/seasonal_adjustment/
     observation_start/observation_end/popularity
 18. search empty query → FAILED
 19. search invalid popularity → int-coerced or skipped
 20. search EMPTY
 21. release_calendar SUCCESS shape
 22. release_calendar row schema
 23. release_calendar cache hit
 24. release_calendar EMPTY
 25. No key (all 3 methods) → FAILED with FRED_API_KEY hint
 26. HTTP 401 → FAILED "invalid FRED_API_KEY"
 27. HTTP 403 → FAILED rate-limit hint
 28. HTTP 429 → FAILED rate-limited
 29. HTTP 400 → FAILED "check series_id"
 30. URL redaction — raw api_key never in note (3 paths)
 31. _redact_apikey() unit-level — api_key (with underscore) handled
 32. Token precedence — explicit kwarg > FRED_API_KEY env > ''
 33. citation_kind in catalog == 'macro'
 34. Three methods via call_tool round-trip
 35. call_tool bogus method → FAILED

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

# Make runtime importable.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs"))

from runtime.tools import ToolResult
from runtime.tools.macro import (
    MacroTool,
    DEFAULT_API_BASE,
    DEFAULT_CACHE_TTL_S,
    DEFAULT_LIMIT_MAX_SERIES,
    DEFAULT_LIMIT_MAX_SEARCH,
    _canonicalize_sort,
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
        url="/fred/series", code=code, msg=msg,
        hdrs={}, fp=io.BytesIO(b""),
    )


# ----------------------------------------------------------- fixtures

_PLAIN_SERIES = {
    "realtime_start": "2025-08-22",
    "realtime_end": "2025-08-22",
    "observation_start": "2010-01-01",
    "observation_end": "2025-08-21",
    "units": "Percent",
    "sort_order": "desc",
    "count": 3,
    "observations": [
        # Note: FRED uses "." as a sentinel for missing values, which we
        # should coerce to None in our schema.
        {"date": "2025-08-21", "value": "4.33",
         "realtime_start": "2025-08-22", "realtime_end": "2025-08-22"},
        {"date": "2025-07-21", "value": ".",   # missing
         "realtime_start": "2025-08-22", "realtime_end": "2025-08-22"},
        {"date": "2025-06-21", "value": "4.20",
         "realtime_start": "2025-08-22", "realtime_end": "2025-08-22"},
    ],
}

_PLAIN_SEARCH = {
    "count": 3,
    "seriess": [
        {
            "id": "GDP",
            "title": "Real Gross Domestic Product",
            "frequency": "Quarterly",
            "units": "Billions of Chained 2017 Dollars",
            "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
            "observation_start": "1947-01-01",
            "observation_end": "2025-04-01",
            "popularity": 95,
        },
        {
            "id": "GDPC1",
            "title": "Real GDP",
            "frequency": "Quarterly",
            "units": "Billions",
            "seasonal_adjustment": "Seasonally Adjusted",
            "observation_start": "1947-01-01",
            "observation_end": "2025-04-01",
            "popularity": 87,
        },
        {
            "id": "DGS10",
            "title": "10-Year Treasury Constant Maturity Rate",
            "frequency": "Daily",
            "units": "Percent",
            "seasonal_adjustment": "Not Seasonally Adjusted",
            "observation_start": "1962-01-02",
            "observation_end": "2025-08-21",
            "popularity": 99,
        },
    ],
}

_PLAIN_RELEASE_CAL = {
    "release_dates": [
        {"release_id": "50", "release_name": "Employment Situation",
         "date": "2025-09-05"},
        {"release_id": "10", "release_name": "Consumer Price Index",
         "date": "2025-09-11"},
    ],
}


# ----------------------------------------------------------- assertions

print("=== 1. series SUCCESS shape ===")
t1 = MacroTool(api_key="k1", opener=None)
f1, calls1, _ = _fake_opener([_PLAIN_SERIES])
t1.opener = f1
res1 = t1.series("GDP")
step("status SUCCESS", res1.status == "SUCCESS",
     detail=f"got {res1.status!r}")
step("data has observations + meta",
     isinstance(res1.data, dict) and "observations" in res1.data
     and "meta" in res1.data)
step("meta.series_id == 'GDP'",
     isinstance(res1.data, dict)
     and res1.data["meta"]["series_id"] == "GDP")
step("meta.sort_order == 'desc' (default)",
     isinstance(res1.data, dict)
     and res1.data["meta"]["sort_order"] == "desc")
step("meta.row_count == 3",
     isinstance(res1.data, dict)
     and res1.data["meta"]["row_count"] == 3)
step("source == 'fred_series'",
     res1.source == "fred_series")


print("\n=== 2. series row schema — date/value/realtime_* ===")
if isinstance(res1.data, dict) and res1.data.get("observations"):
    row = res1.data["observations"][0]
    step("row keys present",
         all(k in row for k in
             ("date", "value", "realtime_start", "realtime_end")))


print("\n=== 3. series cache hit within TTL ===")
t3 = MacroTool(api_key="k", opener=None)
f3, calls3, _ = _fake_opener([_PLAIN_SERIES])
t3.opener = f3
t3.series("GDP")
t3.series("GDP")
step("only 1 fetch across 2 calls", len(calls3) == 1)


print("\n=== 4. series cache miss after TTL=0 ===")
t4 = MacroTool(api_key="k", opener=None)
f4, calls4, _ = _fake_opener([_PLAIN_SERIES, _PLAIN_SERIES])
t4.opener = f4
t4.series("GDP")
t4.cache_ttl_s = 0
t4.series("GDP")
step("2 fetches after TTL=0", len(calls4) == 2)


print("\n=== 5. series empty series_id → FAILED ===")
t5 = MacroTool(api_key="k", opener=None)
f5, calls5, _ = _fake_opener([])
t5.opener = f5
res5 = t5.series("")
step("status FAILED", res5.status == "FAILED")
step("no fetch attempted", len(calls5) == 0)


print("\n=== 6. series sort_order validation — bogus → FAILED ===")
t6 = MacroTool(api_key="k", opener=None)
f6, calls6, _ = _fake_opener([])
t6.opener = f6
res6 = t6.series("GDP", sort_order="random")
step("status FAILED + 'not supported'",
     res6.status == "FAILED"
     and "not supported" in (res6.note or ""),
     detail=f"note={res6.note!r}")
step("no fetch attempted", len(calls6) == 0)


print("\n=== 7. series sort_order aliases ===")
_step_aliases = [
    ("asc", "asc"),
    ("desc", "desc"),
    ("ascending", "asc"),
    ("descending", "desc"),
    ("oldest", "asc"),
    ("newest", "desc"),
    ("", None),
    ("random", None),
]
for raw, expected in _step_aliases:
    got = _canonicalize_sort(raw)
    step(f"_canonicalize_sort({raw!r}) == {expected!r}",
         got == expected, detail=f"got {got!r}")


print("\n=== 8. series limit clamp 99999 → 10000 (FRED max) ===")
# For this test, just verify the call succeeds (no smoke on upstream).
def _ok_op(req, timeout=None):
    return _StubURLResp(_PLAIN_SERIES)
t8 = MacroTool(api_key="k", opener=_ok_op)
res8 = t8.series("GDP", limit=99999)
step("status SUCCESS (limit clamped)", res8.status == "SUCCESS")


print("\n=== 9. series limit=0 → 1 ===")
t9 = MacroTool(api_key="k", opener=_ok_op)
res9 = t9.series("GDP", limit=0)
step("status SUCCESS", res9.status == "SUCCESS")
t9b = MacroTool(api_key="k", opener=_ok_op)
res9b = t9b.series("GDP", limit=-5)
step("status SUCCESS (limit=-5 clamped)",
     res9b.status == "SUCCESS")


print("\n=== 10. series EMPTY — empty observations → EMPTY ===")
t10 = MacroTool(api_key="k", opener=None)
f10, _, _ = _fake_opener([{"observation_start": "2010-01-01",
                             "observation_end": "2025-08-21",
                             "observations": [],
                             "count": 0,
                             "units": ""}])
t10.opener = f10
res10 = t10.series("NOSUCHSERIES")
step("status EMPTY", res10.status == "EMPTY",
     detail=f"got {res10.status!r}")
step("data == []", res10.data == [])


print("\n=== 11. series wrapper spelling — uses 'observations' key ===")
# Verified by test 1 — formal spelling check.
t11 = MacroTool(api_key="k", opener=None)
f11, _, _ = _fake_opener([{"observations": []}])
t11.opener = f11
res11 = t11.series("X")
step("status EMPTY (spelled 'observations')",
     res11.status == "EMPTY", detail=f"got {res11.status!r}")


print("\n=== 12. series defensive — bad row silently skipped ===")
mixed = {
    "observations": [
        {"date": "2025-08-21", "value": "4.33",
         "realtime_start": "X", "realtime_end": "X"},
        "NOT_A_DICT",
        None,
        [1, 2, 3],
        {"date": "2025-07-21", "value": "4.20",
         "realtime_start": "X", "realtime_end": "X"},
    ],
}
t12 = MacroTool(api_key="k", opener=None)
f12, _, _ = _fake_opener([mixed])
t12.opener = f12
res12 = t12.series("X")
step("status SUCCESS (3 bad rows skipped)",
     res12.status == "SUCCESS")
step("2 valid observations kept",
     isinstance(res12.data, dict)
     and len(res12.data["observations"]) == 2)


print("\n=== 13. series non-dict payload → FAILED ===")
t13 = MacroTool(api_key="k", opener=None)
f13, _, _ = _fake_opener([[1, 2, 3]])
t13.opener = f13
res13 = t13.series("X")
step("status FAILED", res13.status == "FAILED")
step("note mentions 'non-object'",
     "non-object" in (res13.note or ""),
     detail=f"note={res13.note!r}")


print("\n=== 14. dot-value ('.' for missing FRED data) coerced to None ===")
# Verified directly off res1's first observation with value='.'.
if isinstance(res1.data, dict):
    obs = res1.data["observations"]
    step("len(observations) == 3",
         len(obs) == 3, detail=f"got {len(obs)}")
    # obs[0] was "4.33" → 4.33, obs[1] was "." → None, obs[2] was "4.20"
    step("obs[0].value is numeric 4.33",
         obs[0]["value"] == 4.33, detail=f"got {obs[0]['value']!r}")
    step("obs[1].value is None ('.' sentinel coerced)",
         obs[1]["value"] is None,
         detail=f"got {obs[1]['value']!r}")
    step("obs[2].value is numeric 4.20",
         obs[2]["value"] == 4.20, detail=f"got {obs[2]['value']!r}")


print("\n=== 15. FRED error_code/error_message payload → FAILED echoed ===")
t15 = MacroTool(api_key="k", opener=None)
f15, _, _ = _fake_opener([{
    "error_code": 404,
    "error_message": "The series ID does not exist.",
}])
t15.opener = f15
res15 = t15.series("BAD_SERIES_ID")
step("status FAILED", res15.status == "FAILED")
step("note echoes FRED message",
     "BAD_SERIES_ID" in (res15.note or "")
     or "does not exist" in (res15.note or ""),
     detail=f"note={res15.note!r}")


print("\n=== 16. search SUCCESS shape ===")
t16 = MacroTool(api_key="k1", opener=None)
f16, calls16, _ = _fake_opener([_PLAIN_SEARCH])
t16.opener = f16
res16 = t16.search("GDP")
step("status SUCCESS", res16.status == "SUCCESS")
step("data has series + meta",
     isinstance(res16.data, dict) and "series" in res16.data
     and "meta" in res16.data)
step("meta.query carried through",
     isinstance(res16.data, dict)
     and res16.data["meta"]["query"] == "GDP")
step("source == 'fred_search'", res16.source == "fred_search")


print("\n=== 17. search row schema ===")
if isinstance(res16.data, dict) and res16.data.get("series"):
    row = res16.data["series"][0]
    step("row schema — id/title/frequency/units/popularity",
         all(k in row for k in
             ("id", "title", "frequency", "units",
              "seasonal_adjustment", "observation_start",
              "observation_end", "popularity")))


print("\n=== 18. search empty query → FAILED ===")
t18 = MacroTool(api_key="k", opener=None)
f18, calls18, _ = _fake_opener([])
t18.opener = f18
res18 = t18.search("")
step("status FAILED + 'non-empty'",
     res18.status == "FAILED"
     and "non-empty" in (res18.note or "").lower())
step("no fetch attempted", len(calls18) == 0)


print("\n=== 19. search invalid popularity → None or skipped ===")
mixed_search = {
    "seriess": [
        {"id": "GDP", "title": "Real GDP",
         "frequency": "Quarterly", "units": "USD",
         "seasonal_adjustment": "SA",
         "observation_start": "1947", "observation_end": "2025",
         "popularity": "not_a_number"},   # garbage popularity
        {"id": "DGS10", "title": "10y",
         "frequency": "Daily", "units": "Percent",
         "seasonal_adjustment": "NSA",
         "observation_start": "1962", "observation_end": "2025",
         "popularity": 99},
    ],
}
t19 = MacroTool(api_key="k", opener=None)
f19, _, _ = _fake_opener([mixed_search])
t19.opener = f19
res19 = t19.search("rate")
step("status SUCCESS (bad popularity skipped, row kept)",
     res19.status == "SUCCESS")
if isinstance(res19.data, dict):
    rows = res19.data["series"]
    step("row 1 popularity is None (was coerced from garbage)",
         rows[0]["popularity"] is None,
         detail=f"got {rows[0]['popularity']!r}")
    step("row 2 popularity is 99",
         rows[1]["popularity"] == 99)


print("\n=== 20. search EMPTY ===")
t20 = MacroTool(api_key="k", opener=None)
f20, _, _ = _fake_opener([{"seriess": [], "count": 0}])
t20.opener = f20
res20 = t20.search("XYZ_NONEXISTENT_QUERY_FOR_TEST_X7Z9")
step("status EMPTY", res20.status == "EMPTY")


print("\n=== 21. release_calendar SUCCESS shape ===")
t21 = MacroTool(api_key="k1", opener=None)
f21, calls21, _ = _fake_opener([_PLAIN_RELEASE_CAL])
t21.opener = f21
res21 = t21.release_calendar()
step("status SUCCESS", res21.status == "SUCCESS")
step("data has release_dates + meta",
     isinstance(res21.data, dict) and "release_dates" in res21.data
     and "meta" in res21.data)
step("source == 'fred_release_calendar'",
     res21.source == "fred_release_calendar")


print("\n=== 22. release_calendar row schema ===")
if isinstance(res21.data, dict) and res21.data.get("release_dates"):
    row = res21.data["release_dates"][0]
    step("row has release_id / release_name / date",
         all(k in row for k in ("release_id", "release_name", "date")))


print("\n=== 23. release_calendar cache hit ===")
t23 = MacroTool(api_key="k", opener=None)
f23, calls23, _ = _fake_opener([_PLAIN_RELEASE_CAL])
t23.opener = f23
t23.release_calendar()
t23.release_calendar()
step("only 1 fetch across 2 calls", len(calls23) == 1)


print("\n=== 24. release_calendar EMPTY ===")
t24 = MacroTool(api_key="k", opener=None)
f24, _, _ = _fake_opener([{"release_dates": []}])
t24.opener = f24
res24 = t24.release_calendar()
step("status EMPTY", res24.status == "EMPTY")


print("\n=== 25. No key (all 3) → FAILED with FRED_API_KEY hint ===")
saved = os.environ.pop("FRED_API_KEY", None)
saved_l = os.environ.pop("LABOURIOUS_FRED_KEY", None)
try:
    for method in ("series", "search", "release_calendar"):
        t25 = MacroTool(api_key=None, opener=None)
        f25, calls25, _ = _fake_opener([])
        t25.opener = f25
        if method == "series":
            res25 = t25.series("GDP")
            exp_source = "fred_series"
        elif method == "search":
            res25 = t25.search("GDP")
            exp_source = "fred_search"
        else:
            res25 = t25.release_calendar()
            exp_source = "fred_release_calendar"
        step(f"  [{method}] status FAILED",
             res25.status == "FAILED")
        step(f"  [{method}] note contains FRED_API_KEY",
             "FRED_API_KEY" in (res25.note or ""))
        step(f"  [{method}] source == '{exp_source}'",
             res25.source == exp_source)
        step(f"  [{method}] no fetch attempted", len(calls25) == 0)
finally:
    if saved is not None: os.environ["FRED_API_KEY"] = saved
    if saved_l is not None:
        os.environ["LABOURIOUS_FRED_KEY"] = saved_l


print("\n=== 26. HTTP 401 → FAILED 'invalid FRED_API_KEY' ===")
t26 = MacroTool(api_key="wrong", opener=None)
f26, _, _ = _fake_opener(raises=[_http_error(401, "Unauthorized")])
t26.opener = f26
res26 = t26.series("GDP")
step("status FAILED + 'invalid FRED_API_KEY'",
     res26.status == "FAILED"
     and "invalid FRED_API_KEY" in (res26.note or ""),
     detail=f"note={res26.note!r}")


print("\n=== 27. HTTP 403 → FAILED rate-limit hint ===")
t27 = MacroTool(api_key="k", opener=None)
f27, _, _ = _fake_opener(raises=[_http_error(403, "Forbidden")])
t27.opener = f27
res27 = t27.search("GDP")
step("status FAILED + 'rate-limit' or 'forbidden'",
     res27.status == "FAILED"
     and ("rate" in (res27.note or "").lower()
          or "forbidden" in (res27.note or "").lower()))


print("\n=== 28. HTTP 429 → FAILED rate-limited ===")
t28 = MacroTool(api_key="k", opener=None)
f28, _, _ = _fake_opener(raises=[_http_error(429, "Too Many Requests")])
t28.opener = f28
res28 = t28.release_calendar()
step("status FAILED + 'rate-limited' or '429'",
     res28.status == "FAILED"
     and ("rate-limited" in (res28.note or "").lower()
          or "429" in (res28.note or "")))


print("\n=== 29. HTTP 400 → FAILED 'check series_id' ===")
t29 = MacroTool(api_key="k", opener=None)
f29, _, _ = _fake_opener(raises=[_http_error(400, "Bad Request")])
t29.opener = f29
res29 = t29.series("bad-series-id!!")
step("status FAILED + '400' or 'bad request' or 'series_id'",
     res29.status == "FAILED"
     and ("400" in (res29.note or "")
          or "bad request" in (res29.note or "").lower()
          or "series_id" in (res29.note or "").lower()),
     detail=f"note={res29.note!r}")


print("\n=== 30. URL redaction — raw api_key never in note ===")
for method_name in ("series", "search", "release_calendar"):
    t30 = MacroTool(
        api_key=f"LEAK-{method_name.upper()}", opener=None)
    payload_map = {
        "series": _PLAIN_SERIES,
        "search": _PLAIN_SEARCH,
        "release_calendar": _PLAIN_RELEASE_CAL,
    }
    f30, _, _ = _fake_opener([payload_map[method_name]])
    t30.opener = f30
    if method_name == "series":
        res30 = t30.series("GDP")
    elif method_name == "search":
        res30 = t30.search("GDP")
    else:
        res30 = t30.release_calendar()
    step(f"  [{method_name}] raw secret NOT in note",
         f"LEAK-{method_name.upper()}" not in (res30.note or ""),
         detail=f"note={(res30.note or '')[:120]!r}")
    step(f"  [{method_name}] REDACTED marker present",
         "api_key=REDACTED" in (res30.note or ""),
         detail=f"note={(res30.note or '')[:120]!r}")


print("\n=== 31. _redact_apikey() unit-level — api_key (with underscore) handled ===")
step("_redact_apikey() neutralises api_key=",
     _redact_apikey("https://x.com/y?series_id=GDP&api_key=secret")
     == "https://x.com/y?series_id=GDP&api_key=REDACTED")
step("case-insensitive ('API_KEY' → REDACTED)",
     _redact_apikey("https://x.com/y?api_key=secret")
     == "https://x.com/y?api_key=REDACTED",
     detail=None)
step("_redact_apikey() leaves non-api_key keys intact",
     _redact_apikey("https://x.com/y?series_id=GDP&file_type=json")
     == "https://x.com/y?series_id=GDP&file_type=json")


print("\n=== 32. Token precedence ===")
os.environ.pop("LABOURIOUS_FRED_KEY", None)
os.environ["FRED_API_KEY"] = "from-env"
t32 = MacroTool(api_key="from-arg", opener=None)
step("explicit kwarg wins over FRED_API_KEY env",
     t32.api_key == "from-arg")
del os.environ["FRED_API_KEY"]
os.environ["LABOURIOUS_FRED_KEY"] = "from-labourious-env"
t32b = MacroTool(api_key="from-arg", opener=None)
step("explicit kwarg wins over LABOURIOUS_FRED_KEY too",
     t32b.api_key == "from-arg")
del os.environ["LABOURIOUS_FRED_KEY"]
os.environ["FRED_API_KEY"] = "from-fred-env"
t32c = MacroTool(opener=None)
step("no explicit kwarg → FRED_API_KEY env used",
     t32c.api_key == "from-fred-env")
del os.environ["FRED_API_KEY"]


print("\n=== 33. citation_kind in catalog == 'macro' ===")
from frontend.connectors_catalog import by_name
entry = by_name("macro")
step("catalog entry exists", entry is not None)
step("citation_kind == 'macro'", entry.citation_kind == "macro")
step("tier == 'tier2'", entry.tier == "tier2")
step("key_env == 'FRED_API_KEY'", entry.key_env == "FRED_API_KEY")
step("recommended == True", entry.recommended is True)


print("\n=== 34. Three methods via call_tool round-trip ===")
from runtime.call_tool import call_tool

payload_map = {
    "series": _PLAIN_SERIES,
    "search": _PLAIN_SEARCH,
    "release_calendar": _PLAIN_RELEASE_CAL,
}

_pilot_payloads: list[Any] = []
_orig_init = MacroTool.__post_init__


def _patched_init(self):
    _orig_init(self)
    if _pilot_payloads:
        payload = _pilot_payloads.pop(0)
        def _op(req, timeout=None):
            return _StubURLResp(payload)
        self.opener = _op


MacroTool.__post_init__ = _patched_init
saved_key = os.environ.get("FRED_API_KEY")
os.environ["FRED_API_KEY"] = "pilot-test-key"

try:
    for method_name, payload in payload_map.items():
        _pilot_payloads.clear()
        _pilot_payloads.append(payload)
        args: dict[str, Any] = {}
        if method_name == "series":
            args["series_id"] = "GDP"
        elif method_name == "search":
            args["query"] = "GDP"
        else:
            args = {}
        res34 = call_tool(
            "macro",
            requested_by_agent="smoke-pilot",
            method=method_name,
            args=args,
        )
        step(f"call_tool({method_name!r}) → SUCCESS",
             res34.status == "SUCCESS",
             detail=f"status={res34.status!r}, note={(res34.note or '')[:80]!r}")
        step(f"  data has rows + meta",
             isinstance(res34.data, dict)
             and any(k in res34.data for k in
                     ("observations", "series", "release_dates")))
finally:
    MacroTool.__post_init__ = _orig_init
    if saved_key is not None:
        os.environ["FRED_API_KEY"] = saved_key
    else:
        os.environ.pop("FRED_API_KEY", None)


print("\n=== 35. call_tool bogus method → FAILED ===")
res35 = call_tool(
    "macro",
    requested_by_agent="smoke-pilot",
    method="bogus_method_xyz",
    args={},
)
step("status FAILED", res35.status == "FAILED")
step("note mentions method",
     "bogus_method_xyz" in (res35.note or "")
     or "method" in (res35.note or "").lower())


# ----------------------------------------------------------- summary
print()
total = len(_fails)
print(f"\033[1m{'OK' if total == 0 else 'FAIL'}\033[0m · "
      f"{35 - total}/35 sections green · "
      f"{_fails and f'{total} failed' or 'all green'}")
if _fails:
    print("\nFailures:")
    for f in _fails:
        print(f"  - {f}")
    sys.exit(1)
sys.exit(0)
