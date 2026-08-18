"""
tools/institutional.py — Institutional holdings (Form 13F-HR).

Free, keyless, polite. Primary source: SEC EDGAR submissions index +
infotable.xml attachments on each 13F-HR accession. Backup: EDGAR full-text
search via sec_edgar_fulltext (already in the runtime).

Why this connector is in MVP-5: the second-most-cited smart-money signal.
Quarterly 13F filings are the only public window into how Renaissance,
Bridgewater, Berkshire, Citadel, etc. have shifted their books. Without
13F ingestion, the strategy + sentiment agents can only see news quotes
of the same filings, not the raw position data.

Single dataclass — `runtime.tools.institutional.InstitutionalTool`.

Three public entry points:

  - `recent_filings(since_quarters=4, limit=50)`
       Last N 13F-HR filings from the curated mega-filer set (Berkshire,
       Bridgewater, Renaissance, Citadel, Tiger Global, BlackRock, Vanguard,
       State Street, Baupost, Pershing Square, Soroban, Lone Pine, Coatue,
       Appaloosa, Greenlight, Soros Fund Mgmt).

  - `info_table(accession_number, *, cik=None)`
       Pulls the infotable.xml for a single 13F-HR accession. The official
       SEC XML schema lives at:
       https://www.sec.gov/edgar/thirteenf/informationtable

  - `major_holders(ticker, since_quarters=4, limit=100)`
       USER QUESTION — 'who holds ticker X?' Iterates the mega-filer set,
       pulls their most-recent 13F-HR's info tables, filters rows where the
       issuer name matches the requested ticker, aggregates shares + value
       per filer, returns a ranked list.

Caching: per (cik, accession, ticker, since_quarters) — 1 hour TTL for
filings list (they don't change once filed); 6 hour TTL for parsed info
tables (immutable). Same in-process dict pattern as the other tools.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Iterable

from . import ToolResult


# ----------------------------------------------------------- mega-filers
# Curated set of ~15 high-signal institutional managers. CIKs verified
# against EDGAR. We pull from this list for `recent_filings` and
# `major_holders`. Catalogue is intentionally small — 100s of filers would
# produce unreliable signal. Add more here only with empirical justification.
MAJOR_FILER_CIKS: tuple[tuple[str, str], ...] = (
    ("0001067983", "Berkshire Hathaway"),
    ("0001350694", "Bridgewater Associates"),
    ("0001037389", "Renaissance Technologies"),
    ("0001423053", "Citadel Advisors"),
    ("0001415686", "Tiger Global Management"),
    ("0001364742", "BlackRock"),
    ("0001029183", "Vanguard"),
    ("0000934047", "State Street"),
    ("0001061768", "Baupost Group"),
    ("0001336528", "Pershing Square"),
    ("0001496556", "Soroban Capital"),
    ("0001444079", "Lone Pine Capital"),
    ("0001418819", "Coatue Management"),
    ("0001112520", "Appaloosa Management"),
    ("0001075394", "Greenlight Capital"),
    ("0001029160", "Soros Fund Management"),
)

# SEC rate limit (10 req/sec blanket) — easy to forget when iterating
# a list of mega-filers + their info tables.
INTER_REQUEST_SLEEP_S = 0.15


@dataclass
class InstitutionalTool:
    user_agent: str = ""
    cache_ttl_filings_s: int = 3600           # 1 h
    cache_ttl_infotable_s: int = 6 * 3600    # 6 h
    request_timeout_s: int = 30
    # The SEC will complain about UnverifiedHTTPSContext on some Python 3
    # installs — we set a strict UA and accept whatever it returns. SSL
    # verification is left on; users should add efts.sec.gov to their
    # trust store if it ever bites.
    opener: Any = field(default=None)
    _cache: dict[str, tuple[float, ToolResult]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.user_agent or not self.user_agent.strip():
            self.user_agent = (
                os.environ.get("SEC_EDGAR_USER_AGENT")
                or "Labourious Analyst [email protected]"
            )
        if self.opener is None:
            self.opener = urllib.request.urlopen

    # ----------------------------------------------------------- public API
    def recent_filings(
        self,
        since_quarters: int = 4,
        limit: int = 50,
    ) -> ToolResult:
        """Recent 13F-HR filings from the curated mega-filer set."""
        if since_quarters < 1:
            since_quarters = 1
        if limit < 1:
            return _failed(self, "limit must be >= 1")

        cache_key = f"recent_filings:{since_quarters}:{limit}"
        cached = self._cache_hit(cache_key, self.cache_ttl_filings_s)
        if cached is not None:
            return cached

        rows: list[dict[str, Any]] = []
        # Quarter cutoff = now minus (since_quarters * 91 days). 13F filings
        # have a 45-day post-quarter deadline, so a 4-quarter lookback covers
        # ~16 months — generous enough that a filer's last quarterly 13F-HR
        # is always within range.
        cutoff = (
            datetime.now(timezone.utc).date()
            - timedelta(days=int(since_quarters * 91))
        ).isoformat()

        for cik, name in MAJOR_FILER_CIKS:
            sub = self._fetch_submissions(cik)
            if sub is None:
                continue
            recent = sub.get("filings", {}).get("recent", {}) or {}
            forms = recent.get("form", []) or []
            dates = recent.get("filingDate", []) or []
            accs = recent.get("accessionNumber", []) or []
            prims = recent.get("primaryDocument", []) or []
            for i, frm in enumerate(forms):
                if frm != "13F-HR":
                    continue
                if dates[i] < cutoff:
                    continue
                adsh = accs[i]
                adsh_clean = adsh.replace("-", "")
                rows.append({
                    "filer_cik": cik.lstrip("0").zfill(10),
                    "filer_name": name,
                    "form": frm,
                    "filing_date": dates[i],
                    "report_date": (recent.get("reportDate", [None] * len(forms)) or [None] * len(forms))[i],
                    "accession_number": adsh,
                    "primary_document": prims[i],
                    "url": (
                        f"https://www.sec.gov/Archives/edgar/data/"
                        f"{int(cik)}/{adsh_clean}/{prims[i]}"
                    ),
                })
                if len(rows) >= limit:
                    break
            time.sleep(INTER_REQUEST_SLEEP_S)
            if len(rows) >= limit:
                break

        # Sort by filing_date desc.
        rows.sort(key=lambda r: r["filing_date"], reverse=True)
        rows = rows[:limit]
        as_of = _now_iso()
        if not rows:
            result = ToolResult(
                status="EMPTY", data=[], as_of=as_of,
                source="institutional",
                note=(
                    f"EDGAR: no 13F-HR filings from {len(MAJOR_FILER_CIKS)} mega "
                    f"filers in the last {since_quarters} quarter(s)."
                ),
            )
        else:
            result = ToolResult(
                status="SUCCESS",
                data=rows,
                as_of=as_of,
                source="institutional",
                note=(
                    f"EDGAR: {len(rows)} 13F-HR filings from "
                    f"{min(len(MAJOR_FILER_CIKS), len(rows))}/{len(MAJOR_FILER_CIKS)} mega-filers "
                    f"in last {since_quarters} quarter(s). "
                    f"Source: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=13F-HR"
                ),
            )
        self._cache_put(cache_key, result)
        return result

    def info_table(
        self,
        accession_number: str,
        *,
        cik: str | None = None,
    ) -> ToolResult:
        """Pull and parse the infotable.xml for one 13F-HR accession.

        Returns list of dicts with: name_of_issuer, title_of_class, cusip,
        value_thousands, shares, put_call, investment_discretion,
        voting_authority{sole,shared,none}.
        """
        if not accession_number:
            return _failed(self, "accession_number is required")
        if not cik:
            return _failed(
                self,
                "cik required for info_table — pass it from recent_filings() "
                "results (entry['filer_cik'] or via accession-to-CIK lookup)."
            )
        adsh_clean = accession_number.replace("-", "")
        url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{adsh_clean}/"
        )
        cache_key = f"info_table:{cik}:{adsh_clean}:index"
        # The accession index page lists every file in the filing — we cache it
        # separately because each filename in the index needs a network round.
        idx_cache = self._cache_hit(cache_key, self.cache_ttl_filings_s)
        if idx_cache is None:
            try:
                idx_html = self._fetch_text(url)
            except urllib.error.HTTPError as e:
                return _failed(self, f"EDGAR index HTTP {e.code}: {e.reason}")
            except Exception as e:
                return _failed(self, f"EDGAR index error: {type(e).__name__}: {e}")
            # Save the raw index HTML in cache via a synthetic ToolResult so we
            # don't need a separate cache map.
            idx_cache = ToolResult(
                status="SUCCESS", data={"html": idx_html},
                as_of=_now_iso(),
                source="institutional",
                note="raw accession index",
            )
            self._cache_put(cache_key, idx_cache)
        if idx_cache.status != "SUCCESS":
            return _failed(self, f"could not load accession index: {idx_cache.note}")
        idx_html = idx_cache.data["html"]

        # Find infotable file in the index — typical filename:
        #   Form13FInfoTable.xml
        # Frontier large filers use it; older filers may use a different name.
        info_table_name = None
        for href in re.findall(r'href="([^"]+)"', idx_html):
            base = href.rsplit("/", 1)[-1]
            if re.match(r"(Form13F)?InfoTable.*\.xml$", base, re.IGNORECASE):
                info_table_name = base
                break
        if not info_table_name:
            return _failed(
                self,
                f"no infotable.xml in accession index at {url}",
            )

        xml_url = f"{url}{urllib.parse.quote(info_table_name, safe='/()')}"
        tbl_cache_key = f"info_table_xml:{cik}:{adsh_clean}:{info_table_name}"
        tbl_cache = self._cache_hit(tbl_cache_key, self.cache_ttl_infotable_s)
        if tbl_cache is None:
            try:
                xml_text = self._fetch_text(xml_url)
            except urllib.error.HTTPError as e:
                return _failed(self, f"infotable XML HTTP {e.code}: {e.reason}")
            rows = _parse_infotable_xml(xml_text)
            tbl_cache = ToolResult(
                status="SUCCESS", data=rows,
                as_of=_now_iso(),
                source="institutional",
                note=f"infotable.xml parsed: {len(rows)} holdings ({info_table_name})",
            )
            self._cache_put(tbl_cache_key, tbl_cache)
        return tbl_cache

    def major_holders(
        self,
        ticker: str,
        since_quarters: int = 4,
        limit: int = 100,
    ) -> ToolResult:
        """For ticker X, list the mega-filers that hold it (most recent Q).

        This is the user-question path — 'who owns ticker X?' We pull each
        mega-filer's most recent 13F-HR and the matching info table, filter
        rows where the issuer name matches the ticker (or whose company
        name matches a curated mapping), sum shares + value per filer.
        """
        if not ticker or not ticker.strip():
            return _failed(self, "ticker must be a non-empty string")
        ticker_clean = ticker.strip().upper()

        cache_key = f"major_holders:{ticker_clean}:{since_quarters}:{limit}"
        cached = self._cache_hit(cache_key, self.cache_ttl_filings_s)
        if cached is not None:
            return cached

        # Step 1: get one 13F-HR per mega filer (most recent).
        per_filer: list[dict[str, Any]] = []
        as_of = _now_iso()
        for cik, name in MAJOR_FILER_CIKS:
            sub = self._fetch_submissions(cik)
            if sub is None:
                continue
            recent = sub.get("filings", {}).get("recent", {}) or {}
            forms = recent.get("form", []) or []
            dates = recent.get("filingDate", []) or []
            accs = recent.get("accessionNumber", []) or []
            prims = recent.get("primaryDocument", []) or []
            rpt_dates = recent.get("reportDate", []) or []
            latest = None
            cutoff = (
                datetime.now(timezone.utc).date()
                - timedelta(days=int(since_quarters * 91))
            ).isoformat()
            for i, frm in enumerate(forms):
                if frm != "13F-HR":
                    continue
                if dates[i] < cutoff:
                    break  # sorted desc, no need to look further
                latest = {
                    "filer_cik": cik.lstrip("0").zfill(10),
                    "filer_name": name,
                    "filing_date": dates[i],
                    "report_date": rpt_dates[i] if i < len(rpt_dates) else None,
                    "accession_number": accs[i],
                }
                break
            if latest is None:
                continue
            # Step 2: pull the filing's info table.
            tbl = self.info_table(latest["accession_number"], cik=latest["filer_cik"])
            if tbl.status != "SUCCESS":
                continue
            # Step 3: filter rows for this ticker.
            matched_rows = [
                row for row in tbl.data
                if _row_matches_ticker(row, ticker_clean)
            ]
            if not matched_rows:
                time.sleep(INTER_REQUEST_SLEEP_S)
                continue
            total_shares = sum(int(r.get("shares") or 0) for r in matched_rows)
            total_value_thousands = sum(int(r.get("value_thousands") or 0) for r in matched_rows)
            # Combine duplicate cusips (CALL+SH often splits a position).
            per_filer.append({
                "filer_cik": latest["filer_cik"],
                "filer_name": latest["filer_name"],
                "filing_date": latest["filing_date"],
                "report_date": latest["report_date"],
                "accession_number": latest["accession_number"],
                "shares": total_shares,
                "value_thousands": total_value_thousands,
                "value_usd": total_value_thousands * 1000,
                "rows": matched_rows,
            })
            time.sleep(INTER_REQUEST_SLEEP_S)
            if len(per_filer) >= limit:
                break

        # Sort by value desc.
        per_filer.sort(key=lambda r: -r["value_usd"])
        per_filer = per_filer[:limit]
        if not per_filer:
            result = ToolResult(
                status="EMPTY", data=[], as_of=as_of,
                source="institutional",
                note=(
                    f"EDGAR: no mega-filer holds {ticker_clean} in their most "
                    f"recent 13F-HR (last {since_quarters} quarter(s), "
                    f"{len(MAJOR_FILER_CIKS)} mega-filers scanned)."
                ),
            )
        else:
            total_rows = sum(len(e["rows"]) for e in per_filer)
            result = ToolResult(
                status="SUCCESS",
                data=per_filer,
                as_of=as_of,
                source="institutional",
                note=(
                    f"EDGAR: {len(per_filer)} mega-filers hold {ticker_clean} "
                    f"across {total_rows} aggregated rows (last "
                    f"{since_quarters} quarter(s), scan over "
                    f"{len(MAJOR_FILER_CIKS)} mega-filers)."
                ),
            )
        self._cache_put(cache_key, result)
        return result

    def clear_cache(self) -> None:
        self._cache.clear()

    # ----------------------------------------------------------- internal
    def _fetch_submissions(self, cik: str) -> dict[str, Any] | None:
        """Caches submissions JSON per CIK with a long TTL — submissions
        always lag the present, so cache aggressively."""
        cache_key = f"submissions:{cik}"
        cached = self._cache_hit(cache_key, self.cache_ttl_filings_s)
        if cached is not None:
            return cached.data if isinstance(cached.data, dict) else None
        url = f"https://data.sec.gov/submissions/CIK{cik.lstrip('0').zfill(10)}.json"
        try:
            text = self._fetch_text(url)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        self._cache_put(
            cache_key,
            ToolResult(status="SUCCESS", data=payload,
                       as_of=_now_iso(), source="institutional",
                       note=f"submissions for CIK {cik}"),
        )
        return payload

    def _fetch_text(self, url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json, application/xml, text/xml, text/html",
            },
        )
        with self.opener(req, timeout=self.request_timeout_s) as resp:
            raw = resp.read()
        try:
            return raw.decode("utf-8", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            return raw.decode("latin-1", errors="replace") if isinstance(raw, bytes) else raw

    def _cache_hit(self, key: str, ttl_s: int) -> ToolResult | None:
        stamped = self._cache.get(key)
        if not stamped:
            return None
        ts, tr = stamped
        if (time.time() - ts) > ttl_s:
            self._cache.pop(key, None)
            return None
        return tr

    def _cache_put(self, key: str, tr: ToolResult) -> None:
        self._cache[key] = (time.time(), tr)


# ----------------------------------------------------------- helpers
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _failed(tool: "InstitutionalTool", note: str) -> ToolResult:
    return ToolResult(
        status="FAILED", data=None, as_of=_now_iso(),
        source="institutional", note=note,
    )


def _parse_infotable_xml(xml_text: str) -> list[dict[str, Any]]:
    """Parse SEC's <informationTable> XML into a flat list of holdings.

    Schema: https://www.sec.gov/edgar/thirteenf/informationtable
    Each <infoTable> holds a single holding. The fields are children of
    <infoTable>, except <shrsOrPrnAmt> and <votingAuthority> which have
    nested <sshPrnamt>/<sshPrnamtType> and <sole>/<shared>/<none> children.
    """
    rows: list[dict[str, Any]] = []
    try:
        tree = ET.fromstring(xml_text)
    except ET.ParseError:
        return rows
    # The XML namespace is registered on the root.
    ns = {"t": tree.tag.split("}")[0].lstrip("{")} if "}" in tree.tag else {}
    info_tables = tree.findall(".//t:infoTable", ns) if ns else tree.findall(".//infoTable")
    for it in info_tables:
        rows.append({
            "name_of_issuer": _el_text(it, "t:nameOfIssuer", ns),
            "title_of_class": _el_text(it, "t:titleOfClass", ns),
            "cusip": _el_text(it, "t:cusip", ns),
            "value_thousands": _safe_int(_el_text(it, "t:value", ns)),
            "shares": _safe_int(_el_text(it, "t:shrsOrPrnAmt/t:sshPrnamt", ns)),
            "share_type": _el_text(it, "t:shrsOrPrnAmt/t:sshPrnamtType", ns),
            "put_call": _el_text(it, "t:putCall", ns),
            "investment_discretion": _el_text(it, "t:investmentDiscretion", ns),
            "voting_authority_sole": _safe_int(
                _el_text(it, "t:votingAuthority/t:sole", ns)
            ),
            "voting_authority_shared": _safe_int(
                _el_text(it, "t:votingAuthority/t:shared", ns)
            ),
            "voting_authority_none": _safe_int(
                _el_text(it, "t:votingAuthority/t:none", ns)
            ),
        })
    return rows


def _el_text(parent: ET.Element, path: str, ns: dict[str, str]) -> str:
    """Return text of the first matching descendant; '' if missing."""
    el = parent.find(path, ns) if ns else parent.find(path.replace("t:", ""))
    if el is None:
        return ""
    return (el.text or "").strip()


def _safe_int(s: str) -> int:
    if not s:
        return 0
    cleaned = re.sub(r"[^\d\-]", "", s)
    try:
        return int(cleaned) if cleaned else 0
    except ValueError:
        return 0


# Curated mapping for tickers whose issuer name on the 13F doesn't match.
# 13F filings list issuer names verbatim from EDGAR; some filers abbreviate.
_TICKER_TO_ISSUER_HINTS: dict[str, tuple[str, ...]] = {
    "AAPL": ("APPLE",),
    "MSFT": ("MICROSOFT",),
    "NVDA": ("NVIDIA",),
    "GOOGL": ("ALPHABET", "GOOGLE"),
    "AMZN": ("AMAZON",),
    "META": ("META PLATFORMS", "FACEBOOK"),
    "TSLA": ("TESLA",),
    "BRK.B": ("BERKSHIRE HATHAWAY",),
    "JPM": ("JPMORGAN",),
    "BAC": ("BANK OF AMERICA",),
    "WFC": ("WELLS FARGO",),
    "V": ("VISA",),
    "MA": ("MASTERCARD",),
}


def _row_matches_ticker(row: dict[str, Any], ticker: str) -> bool:
    """Match a 13F row to a user ticker. Tries two paths:
       1. Issuer name starts with the CUSIP-mapped hint.
       2. Issuer name starts with a curated alias.
       CUSIP-level matching will be added when we pull a ticker↔CUSIP
       mapping (deferred to v2 — too brittle without a paid source).
    """
    issuer = (row.get("name_of_issuer") or "").upper().strip()
    hints = _TICKER_TO_ISSUER_HINTS.get(ticker, (ticker,))
    for hint in hints:
        if issuer.startswith(hint):
            return True
    return False
