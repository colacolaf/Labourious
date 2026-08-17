# tools/sec_edgar.py — Free, keyless, polite. SEC EDGAR REST API.
#
# Compliance: SEC EDGAR asks for a User-Agent header identifying you.
# Rate limit: ≤ 10 req/sec.
# Docs: https://www.sec.gov/os/accessing-edgar-data
from __future__ import annotations
import os
import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any

from . import ToolResult


@dataclass
class SECEdgarTool:
    user_agent: str = ""

    def __post_init__(self):
        if not self.user_agent:
            self.user_agent = (
                os.environ.get("SEC_EDGAR_USER_AGENT")
                or "Labourious Analyst [email protected]"
            )

    # ---------------------------------------------------------------- #
    # CIK lookup: ticker → CIK
    # ---------------------------------------------------------------- #
    def cik_for_ticker(self, ticker: str) -> str | None:
        url = "https://www.sec.gov/files/company_tickers.json"
        req = urllib.request.Request(
            url, headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return None
        t = ticker.upper()
        for v in payload.values():
            if str(v.get("ticker", "")).upper() == t:
                return str(v.get("cik_str", "")).zfill(10)
        return None

    # ---------------------------------------------------------------- #
    # Get filings index for a CIK
    # ---------------------------------------------------------------- #
    def recent_filings(self, ticker: str, form: str = "10-K", limit: int = 5) -> ToolResult:
        cik = self.cik_for_ticker(ticker)
        as_of = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if not cik:
            return ToolResult(
                status="FAILED", data=None, as_of=as_of, source="sec_edgar",
                note=f"CIK not found for {ticker}",
            )
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        req = urllib.request.Request(
            url, headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return ToolResult(
                status="FAILED", data=None, as_of=as_of, source="sec_edgar",
                note=f"SEC submissions {e.code}: {e.reason}",
            )
        recent = payload.get("filings", {}).get("recent", {}) or {}
        forms = recent.get("form", []) or []
        dates = recent.get("filingDate", []) or []
        accs = recent.get("accessionNumber", []) or []
        prims = recent.get("primaryDocument", []) or []
        hits: list[dict] = []
        for i, f in enumerate(forms):
            if f == form and len(hits) < limit:
                acc_clean = accs[i].replace("-", "")
                hits.append({
                    "form": f,
                    "filed_date": dates[i],
                    "accession_number": accs[i],
                    "primary_document": prims[i],
                    "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{prims[i]}",
                })
        return ToolResult(
            status="SUCCESS" if hits else "EMPTY",
            data=hits,
            as_of=as_of,
            source="sec_edgar",
            note=f"Latest {limit} {form} filings for {ticker} (CIK {cik}).",
        )

    # ---------------------------------------------------------------- #
    # Fetch the contents of a primary document as text (light preprocessing)
    # ---------------------------------------------------------------- #
    def fetch_filing_text(self, ticker: str, accession_number: str,
                          primary_document: str) -> ToolResult:
        cik = self.cik_for_ticker(ticker)
        as_of = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if not cik:
            return ToolResult(status="FAILED", data=None, as_of=as_of, source="sec_edgar",
                              note=f"CIK not found for {ticker}")
        acc_clean = accession_number.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{primary_document}"
        req = urllib.request.Request(
            url, headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            return ToolResult(status="FAILED", data=None, as_of=as_of, source="sec_edgar",
                              note=f"{e.code}: {e.reason}")
        # Best-effort decode; filings are often HTML; the agent layer will look up the relevant note.
        text = raw.decode("utf-8", errors="replace")
        return ToolResult(
            status="SUCCESS", data={"text": text[:200000]},  # truncate to 200k chars
            as_of=as_of, source="sec_edgar",
            note=f"Fetched (truncated to 200k chars): {primary_document}",
        )
