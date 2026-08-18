"""
Tier-1 connector conn-5: 8-K material-event wire.

Public method surface:
- latest(ticker=None, cik=None, since_days=30, limit=50)
    Single call an agent lead makes. Returns wire-shape rows:
        [{ticker, cik, headline, material_kind, items: ["2.02", "7.01"],
          filing_date, accession, url, company, score_priorty}, ...]

- material_only(ticker=None, cik=None, since_days=30, limit=50)
    Same as `latest` but filters out LOW/noise items (5.07 annual-meeting
    vote count, 9.01 exhibit-only filings, etc).

- search(ticker=None, cik=None, query="", since_days=30, limit=50)
    Full EFTS-style search across 8-Ks — lets an agent lead combine a
    ticker filter with a free-text query like "guidance" or "covenant".

Design notes:
- Connects straight to EDGAR's free EFTS endpoint (`efts.sec.gov`). No
  key, no login, no paid API. The `sec_edgar_fulltext` tool already
  covers the bare HTTP+JSON, but `news_8k` is a thin *projector* on top
  with item-code classification + ticker resolution + wire shape.
- Material-event taxonomy follows the SEC 8-K item numbering. We rate
  each item HIGH/MEDIUM/LOW and surface a `material_kind` per row so an
  agent lead can filter without re-implementing the taxonomy.
- The ticker is pulled from `display_names` in the EFTS hit, which has
  the format  "NVIDIA CORP  (NVDA)  (CIK 0001045810)". If the EFTS row
  has no ticker (small-cap), the row still ships and `ticker` is None,
  but `cik` is always present.
- Cache TTL is 1 hour (DEFAULT_FRESHNESS_HOURS). 8-Ks get *re-classified*
  by EDGAR within the first 24h after filing (sometimes adding items,
  uploading exhibits), so it's not static like transcripts.
- Auth: keyless.

Freshness tier: tier-1 (24h).
"""

from __future__ import annotations

import json as _json
import re as _re
import sys as _sys
import time as _time
import urllib.parse as _up
from dataclasses import dataclass, field
from typing import Any

# Public re-export of project ToolResult.
if "runtime.tools" in _sys.modules:
    _rt = _sys.modules["runtime.tools"]
    ToolResult = getattr(_rt, "ToolResult", None)
else:
    ToolResult = None  # type: ignore[assignment]


def _now_iso() -> str:
    return _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())


if ToolResult is None:
    # Stand-alone fallback for piloting without runtime package.
    @dataclass
    class ToolResult:  # type: ignore[no-redef]
        status: str
        data: Any
        as_of: str = field(default_factory=_now_iso)
        source: str = ""
        note: str = ""


# --------------------------------------------------------------------------- #
# Item-code taxonomy
# --------------------------------------------------------------------------- #

# HIGH  — always material in equity research context
# MEDIUM — material with context (FD, vote-on-by-law)
# LOW   — typically noise (annual meeting vote counts, exhibit-only)

ITEM_TAXONOMY: dict[str, tuple[str, str]] = {
    # code -> (material_kind, priority)
    "1.01":  ("material_agreement",      "HIGH"),
    "1.03":  ("bankruptcy",              "HIGH"),
    "2.01":  ("acquisition",             "HIGH"),
    "2.02":  ("earnings",                "HIGH"),
    "2.03":  ("debt_obligation",         "MEDIUM"),
    "2.04":  ("debt_trigger",            "MEDIUM"),
    "2.05":  ("restructuring",           "HIGH"),
    "3.01":  ("delisting",               "MEDIUM"),
    "3.02":  ("unregistered_sale",       "LOW"),
    "4.01":  ("auditor_change",          "MEDIUM"),
    "4.02":  ("non_reliance",            "HIGH"),
    "5.01":  ("control_change",          "HIGH"),
    "5.02":  ("officer_change",          "HIGH"),
    "5.05":  ("bylaws_amendment",        "MEDIUM"),
    "5.07":  ("annual_meeting_vote",     "LOW"),
    "5.08":  ("shareholder_vote",        "MEDIUM"),
    "7.01":  ("reg_fd_disclosure",       "MEDIUM"),
    "8.01":  ("other_event",             "LOW"),
    "9.01":  ("exhibits_only",           "LOW"),
}

# Display labels for the human-readable `headline` we project per row.
ITEM_HEADLINE: dict[str, str] = {
    "1.01":  "Material agreement entered",
    "1.03":  "Bankruptcy / receivership filing",
    "2.01":  "Acquisition / disposition completed",
    "2.02":  "Earnings results / financial condition",
    "2.03":  "New direct financial obligation",
    "2.04":  "Triggering event on debt obligation",
    "2.05":  "Exit / disposal / restructuring costs",
    "3.01":  "Notice of delisting / failure to satisfy listing rule",
    "3.02":  "Unregistered sale of equity securities",
    "4.01":  "Changes in registrant's certifying accountant",
    "4.02":  "Non-reliance on prior financial statements",
    "5.01":  "Change in control",
    "5.02":  "Departure / appointment of principal officer",
    "5.05":  "Amendment to articles or bylaws; shareholder vote",
    "5.07":  "Annual meeting shareholder vote results",
    "5.08":  "Shareholder vote on未定 matter",
    "7.01":  "Reg FD disclosure (forward-looking guidance)",
    "8.01":  "Other event (free-text)",
    "9.01":  "Exhibits only (no body items)",
}

_HIGH_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "": 0}


# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

DEFAULT_USER_AGENT = "Labourious/0.1 (+https://labourious.local; research)"
EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"
EFTS_QUERY_URL = EFTS_BASE + "?q={query}&forms=8-K&dateRange=custom&startdt={start}&enddt={end}"

DEFAULT_FRESHNESS_HOURS = 24  # 8-Ks are re-classified within 24h of posting
MAX_LIMIT = 50


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #

# display_names shape:  "NVIDIA CORP  (NVDA)  (CIK 0001045810)"
_TICKER_RX = _re.compile(r"\(([A-Z]{1,5})\)")

# Material-classifier fror the public headline text — picks a single
# `material_kind` for the *whole* 8-K by taking the highest-priority
# item across all items in the row.
def _classify(items: list[str]) -> tuple[str, str]:
    """Given a list of item codes, return (material_kind, priority).

    Priority is HIGH > MEDIUM > LOW. If no items match the taxonomy,
    returns ("other_event", "LOW").
    """
    best_kind = ""
    best_prio = ""
    for code in items or []:
        kind, prio = ITEM_TAXONOMY.get(code, ("other_event", "LOW"))
        if _HIGH_RANK[prio] > _HIGH_RANK.get(best_prio, 0):
            best_kind = kind
            best_prio = prio
    if not best_kind:
        return ("other_event", "LOW")
    return (best_kind, best_prio)


def _parse_display_name(s: str) -> tuple[str | None, str | None]:
    """Pull (ticker, cik) out of one EFTS display_names string.

    Returns (ticker_uppercase_or_None, cik_with_leading_zeros_or_None).
    """
    if not s:
        return (None, None)
    tk = _TICKER_RX.search(s)
    # CIK appears at the very end as `(CIK NNNNNNNN)`.
    cik_m = _re.search(r"\(CIK\s+(\d+)\)\s*$", s)
    return (
        tk.group(1) if tk else None,
        cik_m.group(1) if cik_m else None,
    )


def _project_hit(hit: dict[str, Any]) -> dict[str, Any]:
    """Project one EFTS `_source` blob into a wire-shape row."""
    src = hit.get("_source", {}) or {}
    items = src.get("items") or []
    kind, prio = _classify(items)

    # Ticker + cik can live in either `display_names` or `ciks` arrays.
    display_names = src.get("display_names") or []
    ticker = None
    cik = (src.get("ciks") or [None])[0]
    company = display_names[0] if display_names else ""
    if display_names:
        tk, ck = _parse_display_name(display_names[0])
        ticker = tk
        # Prefer the cik that shows up in the display_name for accuracy.
        cik = ck or cik

    # Build the headline — the *highest-priority* item becomes the
    # caption. We list all items so the user can see what else is inside.
    primary_item = ""
    for code in items:
        if ITEM_TAXONOMY.get(code, ("", "LOW"))[1] == prio:
            primary_item = code
            break
    headline = ITEM_HEADLINE.get(primary_item, f"8-K filing ({', '.join(items) or 'no items'})")

    adsh = src.get("adsh", "") or ""
    file_id = hit.get("_id", "") or ""
    # _id format is "<adsh>:<primary_doc_filename>"
    primary_doc = file_id.split(":", 1)[1] if ":" in file_id else ""
    if cik and adsh:
        cik_no_zeros = str(int(cik))
        adsh_no_dash = adsh.replace("-", "")
        if primary_doc:
            url = (
                "https://www.sec.gov/Archives/edgar/data/"
                f"{cik_no_zeros}/{adsh_no_dash}/{primary_doc}"
            )
        else:
            url = (
                "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                f"&CIK={cik}&type=8-K&dateb=&owner=include&count=40"
            )
    else:
        url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=8-K"

    return {
        "ticker": ticker,
        "cik": cik,
        "company": company,
        "headline": headline,
        "material_kind": kind,
        "priority": prio,
        "items": items,
        "filing_date": src.get("file_date", "") or "",
        "period_ending": src.get("period_ending", "") or "",
        "accession": adsh,
        "file_description": src.get("file_description", "") or "",
        "url": url,
        "primary_doc": primary_doc,
    }


# --------------------------------------------------------------------------- #
# Default opener
# --------------------------------------------------------------------------- #


def _default_opener(url: str, headers: dict[str, str] | None = None) -> tuple[int, str]:
    import urllib.request as _ur

    req = _ur.Request(url, headers=headers or {})
    with _ur.urlopen(req, timeout=20) as resp:  # noqa: S310
        return resp.status, resp.read().decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- #
# Tool
# --------------------------------------------------------------------------- #


class News8KTool:
    """Tier-1 connector `news_8k` — material-event wire from EDGAR EFTS.

    All methods return ToolResult; never raise on HTTP error.
    """

    SOURCE = "news_8k"

    def __init__(
        self,
        opener=_default_opener,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._opener = opener
        self._ua = user_agent
        self._cache: dict[str, tuple[float, ToolResult]] = {}

    # -- cache ---------------------------------------------------------- #
    def _cache_key(self, **kw: Any) -> str:
        return "::".join(f"{k}={v}" for k, v in sorted(kw.items()))

    def _cache_get(self, key: str, ttl: float) -> ToolResult | None:
        hit = self._cache.get(key)
        if hit is None:
            return None
        ts, val = hit
        if ttl > 0 and (_time.time() - ts) > ttl:
            self._cache.pop(key, None)
            return None
        return val

    def _cache_put(self, key: str, val: ToolResult) -> None:
        self._cache[key] = (_time.time(), val)

    def clear_cache(self) -> None:
        self._cache.clear()

    # -- network -------------------------------------------------------- #
    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._ua,
            "Accept": "application/json,text/json",
        }

    def _fetch(self, url: str) -> tuple[int, str]:
        return self._opener(url, self._headers())

    # -- date range helpers -------------------------------------------- #
    @staticmethod
    def _end_today() -> str:
        return _time.strftime("%Y-%m-%d", _time.gmtime())

    @staticmethod
    def _start_n_days_ago(days: int) -> str:
        return _time.strftime(
            "%Y-%m-%d",
            _time.gmtime(_time.time() - int(days) * 86400),
        )

    # -- public API ---------------------------------------------------- #
    def latest(
        self,
        ticker: str | None = None,
        cik: str | None = None,
        since_days: int = 30,
        limit: int = 50,
    ) -> ToolResult:
        return self.search(
            ticker=ticker,
            cik=cik,
            query="",
            since_days=since_days,
            limit=limit,
            priority_filter=None,
        )

    def material_only(
        self,
        ticker: str | None = None,
        cik: str | None = None,
        since_days: int = 30,
        limit: int = 50,
    ) -> ToolResult:
        """Same as `latest` but filters LOW-priority items out."""
        return self.search(
            ticker=ticker,
            cik=cik,
            query="",
            since_days=since_days,
            limit=limit,
            priority_filter={"HIGH", "MEDIUM"},
        )

    def search(
        self,
        ticker: str | None = None,
        cik: str | None = None,
        query: str = "",
        since_days: int = 30,
        limit: int = 50,
        priority_filter: set[str] | None = None,
    ) -> ToolResult:
        ticker = (ticker or "").upper().strip() or None
        cik = (cik or "").strip() or None
        if not ticker and not cik and not query:
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note="at least one of ticker/cik/query required",
            )

        limit = min(int(limit), MAX_LIMIT) if int(limit) > 0 else MAX_LIMIT
        since_days = max(int(since_days), 1)

        cache_key = self._cache_key(
            t=ticker or "", c=cik or "", q=query, d=since_days,
            n=limit, p=",".join(sorted(priority_filter or set())),
        )
        ttl = DEFAULT_FRESHNESS_HOURS * 3600
        cached = self._cache_get(cache_key, ttl=ttl)
        if cached is not None:
            return cached

        # EFTS query: ticker/cik become site-filters via the standard
        # fields=ciks&fields=display_names syntax. We don't enforce
        # those here — we let EFTS do the broadest match + apply the
        # (ticker, cik) reject filter locally. Simpler + works.
        url = EFTS_QUERY_URL.format(
            query=_up.quote(query),
            start=self._start_n_days_ago(since_days),
            end=self._end_today(),
        )

        try:
            status_code, body = self._fetch(url)
        except Exception as exc:
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note=f"network error on {url}: {exc!r}",
            )

        if status_code >= 400:
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note=f"HTTP {status_code} on {url}",
            )

        try:
            parsed = _json.loads(body)
        except _json.JSONDecodeError as exc:
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note=f"EFTS JSON parse failed: {exc!r}",
            )

        hits = ((parsed or {}).get("hits") or {}).get("hits") or []
        rows: list[dict[str, Any]] = []
        for h in hits:
            row = _project_hit(h)
            rows.append(row)

        # Local filter pass: ticker/cik + priority
        if ticker or cik:
            def _keep(r: dict[str, Any]) -> bool:
                if ticker and r["ticker"] != ticker:
                    # Last-ditch: ticker resolution may put NVDA in the
                    # company name as "NVIDIA CORP" — accept if the
                    # ticker is a substring of the row's company too.
                    if r["ticker"] is None and ticker in (r["company"] or "").upper():
                        return True
                    return False
                if cik and r["cik"] != cik:
                    return False
                return True

            rows = [r for r in rows if _keep(r)]

        if priority_filter:
            rows = [r for r in rows if (r.get("priority") or "") in priority_filter]

        # Sort: filing_date desc → priority desc
        _prio_index = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        rows.sort(
            key=lambda r: (
                r.get("filing_date", ""),
                _prio_index.get(r.get("priority", ""), 0),
            ),
            reverse=True,
        )
        rows = rows[: int(limit)]

        # Note: include a per-kind tally so the ChatScreen can bubble up
        # counts into the citation footer without re-iterating.
        kind_counts: dict[str, int] = {}
        for r in rows:
            k = r.get("material_kind") or "other"
            kind_counts[k] = kind_counts.get(k, 0) + 1
        summary = ", ".join(f"{v} {k}" for k, v in sorted(kind_counts.items(), key=lambda kv: -kv[1])[:5])

        if not rows:
            result = ToolResult(
                as_of=_now_iso(),
                status="EMPTY",
                data={"rows": [], "kind_counts": {}},
                source=self.SOURCE,
                note=(
                    f"EDGAR EFTS returned 0 8-K rows for "
                    f"{ticker or (cik and ('CIK ' + cik)) or 'free query'} "
                    f"in last {since_days}d (limit {limit}). "
                    f"Source: {url}"
                ),
            )
        else:
            result = ToolResult(
                as_of=_now_iso(),
                status="SUCCESS",
                data={"rows": rows, "kind_counts": kind_counts},
                source=self.SOURCE,
                note=(
                    f"EDGAR EFTS: {len(rows)} 8-K rows "
                    f"{ticker or (cik and ('CIK ' + cik)) or 'free'} "
                    f"in last {since_days}d ({summary}). "
                    f"Source: {url}"
                ),
            )

        self._cache_put(cache_key, result)
        return result


# --------------------------------------------------------------------------- #
# Module exports
# --------------------------------------------------------------------------- #

__all__ = [
    "News8KTool",
    "ToolResult",
    "ITEM_TAXONOMY",
    "ITEM_HEADLINE",
    "EFTS_BASE",
    "EFTS_QUERY_URL",
    "DEFAULT_FRESHNESS_HOURS",
]
