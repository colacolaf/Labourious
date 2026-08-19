"""
tools/sec_edgar_fulltext.py — SEC EDGAR Full-Text Search (efts.sec.gov).

Free, keyless, polite. Rate limit: ≤ 10 req/sec (SEC's blanket rate for all
EDGAR endpoints). User-Agent header identifies the requester (SEC requires).

Endpoints:
  - https://efts.sec.gov/LATEST/search-index?q=<query>&forms=<form>&ciks=<cik>
    &dateRange=custom&startdt=YYYY-MM-DD&enddt=YYYY-MM-DD
  Hits return a JSON envelope; `_id` is `<accession>:<primary_doc>` and is
  the canonical filing locator.

Usage (analyst-facing):
    tool = SECEdgarFullTextTool()
    r = tool.search(query="guidance", forms="8-K", ciks=["0001045810"],
                    start="2024-01-01", end="2024-03-31", limit=10)
    # r.status == "SUCCESS", r.data = [{...}, ...]

Caching: per-(query, forms, ciks, date_range) `since` hours. The catalog
lists it under tier=free, default_on=True. Freshness tier is 90 days (the
13F/EDGAR/EFTS family gets the wider window — filings don't change after
they land).

Why this connector matters: Ant Group RLFKV (2026) shows that without
full-text + form-filter, filers can't answer questions like "show me every
8-K mentioning 'guidance'" or "all DEF 14A golden-parachute disputes since
2023." The recent-filings index returns only the filings list per CIK; the
EFTS API searches across every public filing since 2001.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from . import ToolResult


# Default EFTS page size — SEC returns up to 50 per page.
MAX_LIMIT = 50
# Default lookback when the caller doesn't supply start/end.
DEFAULT_LOOKBACK_DAYS = 90
# Cache TTL — EFTS responses are stable once filings are indexed.
DEFAULT_CACHE_TTL_S = 3600  # 1 hour


@dataclass
class SECEdgarFullTextTool:
    user_agent: str = ""
    cache_ttl_s: int = DEFAULT_CACHE_TTL_S
    _cache: dict[str, tuple[float, ToolResult]] = field(default_factory=dict)

    def __post_init__(self):
        # Treat empty AND whitespace-only as 'unset' — falls back to the labourious default.
        if not self.user_agent or not self.user_agent.strip():
            self.user_agent = (
                os.environ.get("SEC_EDGAR_USER_AGENT")
                or "Labourious Analyst [email protected]"
            )

    # ----------------------------------------------------------- public API
    def search(
        self,
        *,
        query: str,
        forms: str | tuple[str, ...] | None = None,
        ciks: str | tuple[str, ...] | None = None,
        start: str | None = None,
        end: str | None = None,
        limit: int = 10,
        use_cache: bool = True,
        if_none_match: str | None = None,
    ) -> ToolResult:
        """Free-text search across SEC filings.

        query:    required, multiple words are AND-match in EFTS.
        forms:    one form, or comma-separated list (e.g. "8-K", "10-K,10-Q")
        ciks:     optional CIK (10-digit zero-padded) or comma-separated list.
                  None = search every CIK (slower).
        start:    ISO date YYYY-MM-DD. None = today - DEFAULT_LOOKBACK_DAYS.
        end:      ISO date YYYY-MM-DD. None = today.
        limit:    max hits returned (≤ MAX_LIMIT).
        use_cache: read/write in-process cache, key=hash of (params).
        """
        if not query or not query.strip():
            return ToolResult(
                status="FAILED", data=None, as_of=_now_iso(),
                source="sec_edgar_fulltext",
                note="query must be a non-empty string",
            )
        if limit < 1 or limit > MAX_LIMIT:
            limit = min(max(limit, 1), MAX_LIMIT)

        # Default the date range if caller didn't supply.
        start, end = _resolve_date_range(start, end)

        # Coerce multi-value params to comma-separated strings.
        forms_str = _csv(forms) if forms else ""
        ciks_str = _csv(ciks) if ciks else ""

        # Cache key uses the query AS-SENT (case-preserving) — EFTS treats
        # 'Apple' and 'apple' as different searches with different scoring.
        # Lowercasing here would over-collide.
        cache_key = ":".join((
            query.strip(),
            forms_str, ciks_str,
            start, end, str(limit),
        ))
        if use_cache and cache_key in self._cache:
            stamped, cached = self._cache[cache_key]
            if (time.time() - stamped) < self.cache_ttl_s:
                # Refresh the as_of in the note so the user sees the cache hit.
                return cached

        as_of = _now_iso()
        url = _build_url(query, forms_str, ciks_str, start, end, limit)
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        }
        if if_none_match or getattr(self, "_labourious_if_none_match", None):
            headers["If-None-Match"] = (
                if_none_match or self._labourious_if_none_match
            )
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.loads(r.read().decode("utf-8"))
                response_etag = (r.headers.get("ETag", "") if r.headers else "") or ""
        except urllib.error.HTTPError as e:
            # [domain-8] 304 Not Modified: pass through AS UNCHANGED
            # so the snippet cache can preserve content + sidecar.
            if e.code == 304:
                etag_val = (e.headers.get("ETag", "") if e.headers else "") or (
                    headers.get("If-None-Match", "")
                )
                return ToolResult(
                    status="UNCHANGED", data=None, as_of=as_of,
                    source="sec_edgar_fulltext",
                    note="ETag matched: 304 Not Modified",
                    etag=etag_val or None,
                )
            return ToolResult(
                status="FAILED", data=None, as_of=as_of,
                source="sec_edgar_fulltext",
                note=f"EFTS HTTP {e.code}: {e.reason}",
            )
        except urllib.error.URLError as e:
            return ToolResult(
                status="FAILED", data=None, as_of=as_of,
                source="sec_edgar_fulltext",
                note=f"EFTS network error: {e.reason}",
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                status="FAILED", data=None, as_of=as_of,
                source="sec_edgar_fulltext",
                note=f"EFTS returned non-JSON: {e}",
            )

        hits = _coerce_hits(payload, limit)
        if not hits:
            result = ToolResult(
                status="EMPTY", data=[], as_of=as_of,
                source="sec_edgar_fulltext",
                note=f"No hits in EFTS for '{query}' "
                     f"(forms={forms_str!r}, ciks={ciks_str!r}, "
                     f"{start}\u2192{end}).",
                etag=response_etag or None,
            )
        else:
            result = ToolResult(
                status="SUCCESS",
                data=hits,
                as_of=as_of,
                source="sec_edgar_fulltext",
                note=(
                    f"EFTS: {len(hits)} of "
                    f"{payload.get('hits', {}).get('total', {}).get('value', '?')} "
                    f"hits for '{query}' (forms={forms_str!r}, "
                    f"{start}\u2192{end}). URL: {url}"
                ),
                etag=response_etag or None,
            )
        if use_cache:
            self._cache[cache_key] = (time.time(), result)
        return result

    def clear_cache(self) -> None:
        """Drop the in-process cache. Useful for tests."""
        self._cache.clear()


# ----------------------------------------------------------- helpers
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_date_range(start: str | None, end: str | None) -> tuple[str, str]:
    """Default to [today-90d, today] when either bound is missing."""
    today = datetime.now(timezone.utc).date()
    if end is None:
        end = today.isoformat()
    if start is None:
        start = (today - timedelta(days=DEFAULT_LOOKBACK_DAYS)).isoformat()
    return start, end


def _csv(value) -> str:
    """Coerce 'foo' / ('foo', 'bar') / ['foo', 'bar'] / 'foo,bar' to a CSV."""
    if isinstance(value, str):
        return value
    return ",".join(str(v) for v in value)


def _build_url(query: str, forms: str, ciks: str,
               start: str, end: str, limit: int) -> str:
    q = urllib.parse.quote_plus(query)
    parts = [f"q={q}", f"dateRange=custom", f"startdt={start}", f"enddt={end}"]
    if forms:
        parts.append(f"forms={urllib.parse.quote_plus(forms)}")
    if ciks:
        parts.append(f"ciks={urllib.parse.quote_plus(ciks)}")
    return "https://efts.sec.gov/LATEST/search-index?" + "&".join(parts)


def _coerce_hits(payload: dict, limit: int) -> list[dict[str, Any]]:
    """Map EFTS hits → citation-friendly dicts with stable URL + as_of."""
    out: list[dict[str, Any]] = []
    raw = payload.get("hits", {}).get("hits", []) or []
    for h in raw[:limit]:
        src = h.get("_source") or {}
        adsh = src.get("adsh") or ""
        ciks = src.get("ciks") or []
        cik = ciks[0] if ciks else ""
        # _id is "<adsh>:<primary_doc>" — both URL components.
        primary = h.get("_id", "").split(":", 1)[-1] if "_id" in h else ""
        if adsh and cik and primary:
            # Build the canonical EDGAR URL (no domain required to fetch).
            acc_no_dash = adsh.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}/{primary}"
        else:
            url = ""
        display_names = src.get("display_names") or []
        # display_names shape: "Apple Inc.  (AAPL)  (CIK 0000320193)"
        # The (TICKER) parenthetical is always 1\u20135 chars of alphanumeric; the
        # (CIK ...) parenthetical is longer. Pick the first one matching the
        # ticker shape — NOT iterating past it (the second match would be the
        # CIK, overwriting ticker with digits).
        ticker = ""
        company = ""
        if display_names:
            first = display_names[0]
            company = first.split(" (")[0].strip()
            import re as _re
            m = _re.search(r"\(([A-Z][A-Z0-9.\-]{0,5})\)", first)
            if m:
                ticker = m.group(1)
        out.append({
            "adsh": adsh,
            "cik": cik,
            "form": src.get("form", ""),
            "file_date": src.get("file_date", ""),     # YYYY-MM-DD
            "period_ending": src.get("period_ending", ""),
            "file_description": src.get("file_description", ""),
            "items": src.get("items", []) or [],
            "company": company,
            "ticker": ticker,
            "url": url,
            "efts_id": h.get("_id", ""),  # raw artifact id for re-fetch
        })
    return out
