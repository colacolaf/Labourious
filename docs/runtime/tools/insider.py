"""
tools/insider.py — Insider transactions (Form 4 cluster buys).

Free, keyless, polite. Primary source: openinsider.com, a single-host scraper
that aggregates SEC Form 4 filings within minutes of EDGAR publication.
Backup: scrape SEC EDGAR's recent Form 4 filings for the same CIK.

Why this connector is in MVP-5: the sentiment-agent's primary behavioural
signal. Cluster buys ("3+ insiders buy in the same week") and direct
CEO/CFO buys carry the most cited insider-signal weight in the literature
(FinGPT/WhaleWisdom/Crystal Capital 2024). Without Form 4 ingestion, the
sentiment agent can only see news headlines that quote the same filings.

Single dataclass — `runtime.tools.insider.InsiderTool`. Two public entry
points:
  - `cluster_buys(ticker, since_days=365, min_value=20000, limit=50)`
       Filters to "P - Purchase" rows where |Value| >= min_value, sorted by
       Filing Date desc. Captures the "meaningful" buys the literature cites;
       option buys and exercise-then-sell rows are still flagged in the
       scanner but not the cluster count.
  - `recent_filings(ticker, since_days=90, limit=50)`
       All Form 4 filings, both buys and sells, for the given window.

Caching: per (ticker, since_days, min_value, kind), 30-minute TTL. Form 4
filings land at EDGAR within minutes, but OpenInsider scrapes every 5-15
minutes, so caching more aggressively saves us from getting noticed.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from . import ToolResult


DEFAULT_OPENINSIDER_URL = "http://openinsider.com/screener"
DEFAULT_USER_AGENT = "Labourious Analyst [email protected]"
DEFAULT_CACHE_TTL_S = 1800  # 30 min
DEFAULT_REQUEST_TIMEOUT_S = 30


@dataclass
class InsiderTool:
    user_agent: str = ""
    openinsider_url: str = DEFAULT_OPENINSIDER_URL
    cache_ttl_s: int = DEFAULT_CACHE_TTL_S
    request_timeout_s: int = DEFAULT_REQUEST_TIMEOUT_S
    # Optional override for the underlying HTML opener — pilot tests inject
    # a stub here; production gets `urllib.request.urlopen`.
    opener: Any = field(default=None)
    _cache: dict[str, tuple[float, ToolResult]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.user_agent or not self.user_agent.strip():
            self.user_agent = (
                os.environ.get("OPENINSIDER_USER_AGENT")
                or os.environ.get("SEC_EDGAR_USER_AGENT")
                or DEFAULT_USER_AGENT
            )
        if self.opener is None:
            self.opener = urllib.request.urlopen

    # ----------------------------------------------------------- public API
    def cluster_buys(
        self,
        ticker: str,
        since_days: int = 365,
        min_value: int = 20_000,
        limit: int = 50,
    ) -> ToolResult:
        """Form 4 cluster buys — purchases only, |Value|>=min_value, last N days."""
        return self._fetch(
            ticker=ticker, since_days=since_days, kind="purchases",
            min_value=min_value, limit=limit,
        )

    def recent_filings(
        self,
        ticker: str,
        since_days: int = 90,
        limit: int = 50,
    ) -> ToolResult:
        """All Form 4 filings — buys and sells — within the window."""
        return self._fetch(
            ticker=ticker, since_days=since_days, kind="all",
            min_value=0, limit=limit,
        )

    def clear_cache(self) -> None:
        self._cache.clear()

    # ----------------------------------------------------------- internal
    def _fetch(
        self, *, ticker: str, since_days: int, kind: str,
        min_value: int, limit: int,
    ) -> ToolResult:
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return _failed(self, "ticker must be a non-empty string")

        cache_key = f"{ticker}:{kind}:{since_days}:{min_value}:{limit}"
        cached_hit = self._cache_hit(cache_key)
        if cached_hit is not None:
            return cached_hit

        url = _build_openinsider_url(self.openinsider_url, ticker, since_days, limit)
        as_of = _now_iso()
        try:
            html = self._fetch_html(url)
        except urllib.error.HTTPError as e:
            return _failed(self, f"OpenInsider HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            return _failed(self, f"OpenInsider network error: {e.reason}")
        except Exception as e:
            return _failed(self, f"OpenInsider parse error: {type(e).__name__}: {e}")

        rows = _parse_table_rows(html)
        # Filter + project into our dict shape.
        rows = [r for r in rows if r["ticker"] == ticker]
        rows = self._filter_rows(rows, kind=kind, min_value=min_value)
        rows = self._filter_rows(rows, kind=kind, min_value=min_value)
        rows = rows[:limit]

        # If OpenInsider returned nothing we can still mint an EMPTY — never
        # fabricate. Cross-check EDGAR for the same ticker before settling on
        # EMPTY so we don't produce false negatives on scraper outages.
        if not rows:
            tool_edgar = self._try_edgar_fallback(ticker, since_days, limit)
            if tool_edgar is not None:
                self._cache_put(cache_key, tool_edgar)
                return tool_edgar

        if not rows:
            result = ToolResult(
                status="EMPTY", data=[], as_of=as_of,
                source="insider",
                note=f"OpenInsider: no {kind} rows for {ticker} "
                     f"in last {since_days}d (|Value|>=${min_value:,}).",
            )
        else:
            # Compute cluster-buy signature on the same-day span.
            cluster_count = _count_clusters(rows)
            result = ToolResult(
                status="SUCCESS",
                data=rows,
                as_of=as_of,
                source="insider",
                note=(
                    f"OpenInsider: {len(rows)} {kind} filings for {ticker} "
                    f"in last {since_days}d; {cluster_count} cluster-buy span"
                    f"{'s' if cluster_count != 1 else ''} detected "
                    f"(3+ distinct insiders within a 7-day window among cluster buys). "
                    f"URL: {url}"
                ),
            )
        self._cache_put(cache_key, result)
        return result

    def _fetch_html(self, url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "gzip, deflate",
            },
        )
        with self.opener(req, timeout=self.request_timeout_s) as resp:
            raw = resp.read()
        try:
            return raw.decode("utf-8", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            return raw.decode("latin-1", errors="replace") if isinstance(raw, bytes) else raw

    def _filter_rows(
        self, rows: list[dict[str, Any]], *, kind: str, min_value: int,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for r in rows:
            # kind filter: "purchases" only retains "P - …" trades.
            if kind == "purchases":
                tt = r.get("trade_type", "")
                if not tt.startswith("P"):
                    continue
            # Value filter: keep |Value|>=min_value.
            if min_value and abs(r.get("value", 0) or 0) < min_value:
                continue
            out.append(r)
        return out

    def _cache_hit(self, key: str) -> ToolResult | None:
        stamped = self._cache.get(key)
        if not stamped:
            return None
        ts, tr = stamped
        if (time.time() - ts) > self.cache_ttl_s:
            self._cache.pop(key, None)
            return None
        return tr

    def _cache_put(self, key: str, tr: ToolResult) -> None:
        self._cache[key] = (time.time(), tr)

    def _try_edgar_fallback(
        self, ticker: str, since_days: int, limit: int,
    ) -> ToolResult | None:
        """If OpenInsider returned nothing, query EDGAR Form 4 directly as a
        health check before settling on EMPTY.

        We use SEC EDGAR's recent-filings index (the same shape the existing
        sec_edgar.py tool exposes) — pulls Form 4 filings within the window.
        Useful when OpenInsider's table is empty due to a scraper outage.
        """
        try:
            import json as _json
            from urllib.parse import urlencode
            # Step 1: resolve CIK
            url_ciks = "https://www.sec.gov/files/company_tickers.json"
            req = urllib.request.Request(
                url_ciks,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept-Encoding": "gzip, deflate",
                },
            )
            with self.opener(req, timeout=self.request_timeout_s) as r:
                payload = _json.loads(r.read().decode("utf-8"))
            cik = None
            for v in payload.values():
                if str(v.get("ticker", "")).upper() == ticker:
                    cik = str(v.get("cik_str", "")).zfill(10)
                    break
            if not cik:
                return None
            # Step 2: pull submissions
            url_sub = f"https://data.sec.gov/submissions/CIK{cik}.json"
            req = urllib.request.Request(
                url_sub,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept-Encoding": "gzip, deflate",
                },
            )
            with self.opener(req, timeout=self.request_timeout_s) as r:
                sub = _json.loads(r.read().decode("utf-8"))
            recent = sub.get("filings", {}).get("recent", {}) or {}
            forms = recent.get("form", []) or []
            dates = recent.get("filingDate", []) or []
            cutoff = (datetime.now(timezone.utc).date()
                      - timedelta(days=since_days)).isoformat()
            hits = []
            for i, frm in enumerate(forms):
                if frm != "4":
                    continue
                if dates[i] < cutoff:
                    continue
                adsh = (recent.get("accessionNumber") or [])[i]
                prim = (recent.get("primaryDocument") or [])[i]
                hits.append({
                    "filing_date": dates[i],
                    "adsh": adsh,
                    "cik": cik,
                    "form": "4",
                    "primary_document": prim,
                    "url": (
                        f"https://www.sec.gov/cgi-bin/browse-edgar?"
                        f"action=getcompany&CIK={int(cik)}&type=4"
                    ),
                })
                if len(hits) >= limit:
                    break
            if not hits:
                return None
            as_of = _now_iso()
            return ToolResult(
                status="SUCCESS",
                data=hits,
                as_of=as_of,
                source="insider",
                note=(
                    f"EDGAR fallback: {len(hits)} Form 4 filings for {ticker} "
                    f"in last {since_days}d (OpenInsider returned no rows)."
                ),
            )
        except Exception:
            return None  # we never raise out of the fallback path


# ----------------------------------------------------------- helpers
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _failed(tool: "InsiderTool", note: str) -> ToolResult:
    """Shorthand for FAILED ToolResult with current user_agent + source."""
    return ToolResult(
        status="FAILED", data=None,
        as_of=_now_iso(),
        source="insider",
        note=note,
    )


def _build_openinsider_url(base: str, ticker: str,
                            since_days: int, limit: int) -> str:
    """Match OpenInsider's screener URL convention."""
    # `fd` = filing date in N days, capped at 1460 on OpenInsider side.
    days = max(1, min(since_days, 1460))
    qs = {
        "s": ticker,
        "fd": str(days),
        "fdr": "00",      # days granularity
        "td": "0", "tdr": "00",
        "exect": "ALL",   # include all officer types
        "txo": "ALL",     # trade-type all
        "sfo": "ALL",     # direct/indirect all
        "sortcol": "0",   # sort by filing date desc
        "cnt": str(max(1, min(limit, 1000))),  # 50/100/200/...
        "page": "1",
    }
    return f"{base}?{urllib.parse.urlencode(qs)}"


def _parse_table_rows(html: str) -> list[dict[str, Any]]:
    """Lightweight OpenInsider table parser.

    The screener renders an HTML <table class="tinytable">; each row holds
    12 <td> cells (X link, filing date, trade date, ticker, name, title,
    trade type, price, qty, owned, ΔOwn, value). Numeric cells may carry
    thousand-separator commas (`-885,000`) and dollar signs (`$210.17`).

    The aim is "good enough" without BeautifulSoup — we tolerate whitespace,
    nested <a>, and odd tags the site adds. Real production sites drift; if
    this regex breaks, the FAILED ToolResult surfaces the issue rather than
    silently returning garbage.
    """
    rows: list[dict[str, Any]] = []
    # Find each top-level <tr> block on the reports table.
    # OpenInsider ships many tables (header, menus, etc); we only want the
    # main reports table which sits under <table class="tinytable">.
    table_match = re.search(
        r"<table[^>]*class=[\"']?tinytable[\"']?[^>]*>(.*?)</table>",
        html, flags=re.DOTALL | re.IGNORECASE,
    )
    table_html = table_match.group(1) if table_match else html
    # Capture every <tr> block.
    tr_blocks = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html,
                           flags=re.DOTALL | re.IGNORECASE)
    for tr in tr_blocks:
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr,
                         flags=re.DOTALL | re.IGNORECASE)
        # Strip HTML tags from each cell; collapse whitespace.
        clean = [_strip_tags(td) for td in tds]
        if not _looks_like_data_row(clean):
            continue
        row = _row_to_dict(clean)
        rows.append(row)
    return rows


def _strip_tags(cell: str) -> str:
    """Strip nested <a>, <b>, <span>. Collapse tabs/newlines."""
    text = re.sub(r"<[^>]+>", "", cell)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    return text.strip()


def _looks_like_data_row(cells: list[str]) -> bool:
    """Heuristic: a data row has a filing-date cell (YYYY-MM-DD HH:MM:SS)."""
    if len(cells) < 12:
        return False
    return bool(re.match(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", cells[1]))


def _row_to_dict(cells: list[str]) -> dict[str, Any]:
    """Map the 12 cleaned cells to our dict shape.

    OpenInsider column order (with leading X link):
      0  X                — link to Form 4 (we drop text)
      1  filing_date      — "YYYY-MM-DD HH:MM:SS"
      2  trade_date       — "YYYY-MM-DD"
      3  ticker           — "NVDA"
      4  insider_name     — "Stevens Mark A"
      5  title            — "Dir"
      6  trade_type       — "S - Sale" / "P - Purchase"
      7  price            — "$210.17"
      8  qty              — "-885,000"
      9  owned            — "31,768,422"
     10  delta_own        — "-3%"
     11  value            — "-$185,999,938"
    """
    return {
        "filing_date": cells[1],
        "trade_date": cells[2],
        "ticker": cells[3].upper(),
        "insider_name": cells[4],
        "title": cells[5],
        "trade_type": cells[6],
        "price": _parse_number(cells[7]) if _has_currency(cells[7]) else _parse_int(cells[7]),
        "raw_price": cells[7],
        "qty": _parse_int(cells[8]),
        "owned_after": _parse_int(cells[9]),
        "delta_own_pct": cells[10],
        "value": _parse_money(cells[11]),
        "raw_value": cells[11],
        # Pre-rendered URL to the SEC Form 4 page (OpenInsider breaks it down
        # to the underlying EDGAR accession; we link to the SEC search index
        # for the user to drill if they want).
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=4",
    }


def _has_currency(s: str) -> bool:
    return "$" in s


def _parse_number(s: str) -> float | None:
    if not s:
        return None
    cleaned = re.sub(r"[^\d.\-]", "", s)
    if not cleaned or cleaned in ("-", "."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_int(s: str) -> int | None:
    if not s:
        return None
    cleaned = re.sub(r"[^\d\-]", "", s)
    if not cleaned or cleaned == "-":
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return None


def _parse_money(s: str) -> int | None:
    """Money cells like '-$185,999,938' or '+$1,234'. Returns signed int dollars."""
    if not s:
        return None
    sign = -1 if s.strip().startswith("-") else 1
    cleaned = re.sub(r"[^\d]", "", s)
    if not cleaned:
        return None
    try:
        return sign * int(cleaned)
    except ValueError:
        return None


def _count_clusters(rows: list[dict[str, Any]]) -> int:
    """Count distinct filing-week clusters containing >=3 distinct insiders
    who ALL BOUGHT in the same 7-day window.

    A 'cluster' definition (per the cluster-buy literature): 3+ different
    insiders reporting Buy filings within a rolling 7-day window.
    """
    if len(rows) < 3:
        return 0
    # Sort by trade_date (ISO so string sort = chronological), desc considered.
    sorted_rows = sorted(rows, key=lambda r: r.get("trade_date") or "")
    clusters: list[tuple[str, set[str]]] = []  # (start_date, set(insider_names))
    for r in sorted_rows:
        ts = r["trade_date"]
        if not ts:
            continue
        name = r.get("insider_name", "")
        # Extend an existing cluster if the new filing is within 7 days of
        # any date in the cluster set; otherwise start a new one.
        merged = False
        for i, (start_date, members) in enumerate(clusters):
            if _within_window(start_date, ts, days=7):
                members.add(name)
                clusters[i] = (start_date, members)
                merged = True
                break
        if not merged:
            clusters.append((ts, {name}))
    return sum(1 for _start, members in clusters if len(members) >= 3)


def _within_window(start: str, current: str, days: int = 7) -> bool:
    """True if `current` is within `days` days of `start` (ISO YYYY-MM-DD)."""
    try:
        a = datetime.fromisoformat(start)
        b = datetime.fromisoformat(current)
    except (ValueError, TypeError):
        return False
    return abs((b - a).days) <= days
