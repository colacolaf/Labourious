"""
tools/fundamentals.py — Financial statements & ratios via Financial Modeling Prep.

Free-with-API-key. Sign up at https://financialmodelingprep.com/developer/docs
(free tier: 250 requests/day; per-key rate limits documented per plan).

Auth: FMP supports BOTH header (``apikey: YOUR_KEY``) and query
(``?apikey=YOUR_KEY``) auth. We default to the **header** path because it keeps
the token out of URL logs — only call_tool's note echoes a redacted version of
the URL, never the raw secret. The query-string form is still supported for
callers who pass ``auth="query"`` (useful when debugging through a proxy that
strips custom headers).

Why this connector exists: yfinance gives you 4 years of income statement /
balance sheet / cash flow and a thin set of ratios, but it pulls live from
Yahoo's servers on every call (rate-limited, occasionally blocked) and offers
no quarterly granularity past 4-5 quarters. FMP's free tier covers ~30 years
of annual data plus 30 quarters of quarterly data, and pre-computes ~60 ratios
so DCF/Comps/Comparator can run without the LLM hand-rolling math. Net effect:
much higher confidence on historical growth rate, margin trajectory, and
leverage metrics used by every Wharton-sheet line item.

Single dataclass — ``runtime.tools.fundamentals.FundamentalsTool``. Five
public endpoints (each maps 1:1 to FMP's stable router):

  - ``income_statement(ticker, period="annual", limit=5)``
        ``GET /stable/income-statement``
  - ``balance_sheet(ticker, period="annual", limit=5)``
        ``GET /stable/balance-sheet-statement``
  - ``cash_flow(ticker, period="annual", limit=5)``
        ``GET /stable/cash-flow-statement``
  - ``key_metrics(ticker, period="annual", limit=5)``
        ``GET /stable/key-metrics``
  - ``ratios(ticker, period="annual", limit=5)``
        ``GET /stable/ratios``

All methods return ``ToolResult`` — never raise on HTTP error.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from . import ToolResult


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

DEFAULT_API_BASE = "https://financialmodelingprep.com"
DEFAULT_USER_AGENT = "Labourious Analyst [email protected]"
DEFAULT_TIMEOUT_S = 15
DEFAULT_CACHE_TTL_S = 3600             # 1 h — fundamentals are quarterly/annual
DEFAULT_LIMIT = 5                       # default for annual pull
DEFAULT_LIMIT_QUARTERLY = 20            # more quarters fit in 250/day budget

# Endpoint → path. Stable router is the 2024+ path FMP standardised on; the
# ``v3`` legacy paths still work but ``stable`` is what their main docs index.
_ENDPOINT_PATHS: dict[str, str] = {
    "income_statement":  "/stable/income-statement",
    "balance_sheet":      "/stable/balance-sheet-statement",
    "cash_flow":          "/stable/cash-flow-statement",
    "key_metrics":        "/stable/key-metrics",
    "ratios":             "/stable/ratios",
}

PeriodT = Literal["annual", "quarter"]


# ------------------------------------------------------------------
# Tool
# ------------------------------------------------------------------


@dataclass
class FundamentalsTool:
    """FMP-backed financial statements & ratios fetcher.

    Parameters
    ----------
    api_key : str | None
        FMP API key. ``__post_init__`` reads from ``FMP_API_KEY`` then
        ``LABOURIOUS_FMP_KEY`` if not provided.
    api_base : str
        Override for tests. Production never changes this.
    auth : str
        ``"header"`` (default) or ``"query"``. We strongly prefer the
        header since it keeps the secret out of URL logs.
    user_agent : str
        Polite UA. Same string across all our providers.
    request_timeout_s : int
        Per-request timeout. 15 s is generous against FMP's p99 latency.
    cache_ttl_s : int
        Fundamentals barely change intra-day once a quarter closes;
        default 1 h is conservative against the 250 req/day free cap.
    opener : Any
        Override for tests; default ``urllib.request.urlopen``.
    """

    api_key: str | None = None
    api_base: str = DEFAULT_API_BASE
    auth: str = "header"
    user_agent: str = ""
    request_timeout_s: int = DEFAULT_TIMEOUT_S
    cache_ttl_s: int = DEFAULT_CACHE_TTL_S
    opener: Any = field(default=None)
    _cache: dict[str, tuple[float, ToolResult]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (self.api_key and self.api_key.strip()):
            self.api_key = (
                os.environ.get("FMP_API_KEY")
                or os.environ.get("LABOURIOUS_FMP_KEY")
            )
        if not (self.user_agent and self.user_agent.strip()):
            self.user_agent = (
                os.environ.get("FMP_USER_AGENT")
                or os.environ.get("LABOURIOUS_DEFAULT_USER_AGENT")
                or DEFAULT_USER_AGENT
            )
        if self.auth not in ("header", "query"):
            raise ValueError(
                f"auth must be 'header' or 'query' (got {self.auth!r})"
            )
        if self.opener is None:
            self.opener = urllib.request.urlopen

    # ----------------------------------------------------------- public API
    def income_statement(
        self,
        ticker: str,
        period: str = "annual",
        limit: int = DEFAULT_LIMIT,
    ) -> ToolResult:
        return self._fetch_statement("income_statement", ticker, period, limit)

    def balance_sheet(
        self,
        ticker: str,
        period: str = "annual",
        limit: int = DEFAULT_LIMIT,
    ) -> ToolResult:
        return self._fetch_statement("balance_sheet", ticker, period, limit)

    def cash_flow(
        self,
        ticker: str,
        period: str = "annual",
        limit: int = DEFAULT_LIMIT,
    ) -> ToolResult:
        return self._fetch_statement("cash_flow", ticker, period, limit)

    def key_metrics(
        self,
        ticker: str,
        period: str = "annual",
        limit: int = DEFAULT_LIMIT,
    ) -> ToolResult:
        return self._fetch_statement("key_metrics", ticker, period, limit)

    def ratios(
        self,
        ticker: str,
        period: str = "annual",
        limit: int = DEFAULT_LIMIT,
    ) -> ToolResult:
        return self._fetch_statement("ratios", ticker, period, limit)

    def clear_cache(self) -> None:
        """Drop the in-process cache. Useful for tests / ops."""
        self._cache.clear()

    # ----------------------------------------------------------- internal
    def _fetch_statement(
        self,
        endpoint: str,
        ticker: str,
        period: str,
        limit: int,
    ) -> ToolResult:
        """Shared implementation for all five endpoints."""
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return _failed(
                self, "ticker must be a non-empty string",
                source=f"fmp_{endpoint}",
            )

        canonical_period = _canonicalize_period(period)
        if canonical_period is None:
            return _failed(
                self,
                f"period {period!r} not supported (use 'annual' or 'quarter').",
                source=f"fmp_{endpoint}",
            )

        limit = max(1, min(int(limit), 100))

        path = _ENDPOINT_PATHS[endpoint]
        cache_key = f"{endpoint}::{ticker}::{canonical_period}::{limit}"
        cached = self._cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            return _failed(
                self,
                "FMP_API_KEY not configured — set it in your shell or in "
                "~/.labourious/config.yaml to enable Financial Modeling Prep "
                "fundamentals. Sign up free at "
                "https://financialmodelingprep.com/developer/docs "
                "(250 requests/day free tier).",
                source=f"fmp_{endpoint}",
            )

        qs: dict[str, str] = {
            "symbol": ticker,
            "period": canonical_period,
            "limit": str(limit),
        }

        if self.auth == "header":
            query_string = urllib.parse.urlencode(qs)
            url = f"{self.api_base}{path}?{query_string}"
            request_headers = {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "apikey": self.api_key,                          # FMP header auth
                "Accept-Encoding": "gzip, deflate",
            }
        else:
            qs["apikey"] = self.api_key                        # FMP query auth
            url = f"{self.api_base}{path}?{urllib.parse.urlencode(qs)}"
            request_headers = {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }

        as_of = _now_iso()
        try:
            payload = self._fetch_json(url, request_headers)
        except urllib.error.HTTPError as e:
            code = e.code
            if code == 401:
                note = (
                    f"FMP HTTP 401 on {path}: invalid FMP_API_KEY "
                    f"(check the key in your shell or "
                    f"~/.labourious/config.yaml)."
                )
            elif code == 403:
                note = (
                    f"FMP HTTP 403 on {path}: forbidden — free-tier daily "
                    f"limit likely hit (250 req/day). Wait 24 h or upgrade."
                )
            elif code == 429:
                note = (
                    f"FMP HTTP 429 on {path}: rate-limited. Wait and retry."
                )
            else:
                note = f"FMP HTTP {code} on {path}: {e.reason}"
            return _failed(self, note, source=f"fmp_{endpoint}", status_code=code)
        except urllib.error.URLError as e:
            return _failed(
                self,
                f"FMP network error on {path}: {e.reason}",
                source=f"fmp_{endpoint}",
            )
        except Exception as e:
            return _failed(
                self,
                f"FMP parse error on {path}: {type(e).__name__}: {e}",
                source=f"fmp_{endpoint}",
            )

        # FMP returns { "Error Message": "..." } on bad keys,
        # an empty list on truly unknown symbols, and a list of dicts on success.
        if isinstance(payload, dict):
            err_msg = payload.get("Error Message") or payload.get("error")
            if err_msg:
                return _failed(
                    self,
                    f"FMP error on {path}: {err_msg}",
                    source=f"fmp_{endpoint}",
                )
            # Some FMP errors come back as a dict-of-lists we didn't expect.
            return _failed(
                self,
                f"FMP returned unexpected JSON shape on {path}: {type(payload).__name__}",
                source=f"fmp_{endpoint}",
            )

        if not isinstance(payload, list):
            return _failed(
                self,
                f"FMP returned non-list payload on {path}: {type(payload).__name__}",
                source=f"fmp_{endpoint}",
            )

        if not payload:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source=f"fmp_{endpoint}",
                note=(
                    f"FMP {endpoint} for {ticker}: no records returned "
                    f"(unknown ticker or no {canonical_period} filings on file)."
                ),
            )

        # Trim to the requested limit defensively (FMP sometimes returns more).
        rows = payload[:limit]
        meta = {
            "endpoint": endpoint,
            "ticker": ticker,
            "period": canonical_period,
            "row_count": len(rows),
            "as_of": as_of,
        }

        # Build a redacted URL for the note. Strip the apikey from the live
        # request URL so the secret never lands in logs.
        redacted_url = _redact_apikey(url)

        result = ToolResult(
            status="SUCCESS",
            data={"rows": rows, "meta": meta},
            as_of=as_of,
            source=f"fmp_{endpoint}",
            note=(
                f"FMP {path} for {ticker}: {len(rows)} {canonical_period} "
                f"records (limit={limit}). URL: {redacted_url}"
            ),
        )
        self._cache_put(cache_key, result)
        return result

    def _fetch_json(self, url: str, headers: dict[str, str]) -> Any:
        req = urllib.request.Request(url, headers=headers)
        with self.opener(req, timeout=self.request_timeout_s) as resp:
            raw = resp.read()
        if isinstance(raw, bytes):
            try:
                return json.loads(raw.decode("utf-8"))
            except UnicodeDecodeError:
                return json.loads(raw.decode("latin-1"))
        return json.loads(raw)

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


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _now_iso() -> str:
    """UTC wallclock as ISO-8601, second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonicalize_period(period: str) -> str | None:
    """Map user input → FMP's ``period`` query value. None for unknown."""
    if not period:
        return None
    s = period.strip().lower()
    if s in ("annual", "year", "y", "yearly", "fy", "fiscal year"):
        return "annual"
    if s in (
        "quarter", "quarterly", "q", "q1", "q2", "q3", "q4",
        "3m", "3month", "three-month",
    ):
        return "quarter"
    return None


def _redact_apikey(url: str) -> str:
    """Return URL with any ``apikey=`` param replaced by ``apikey=REDACTED``."""
    parts = urllib.parse.urlparse(url)
    if not parts.query:
        return url
    qsl = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    redacted = [(k, "REDACTED" if k.lower() == "apikey" else v) for k, v in qsl]
    return urllib.parse.urlunparse(parts._replace(
        query=urllib.parse.urlencode(redacted)
    ))


def _failed(
    tool: "FundamentalsTool",
    note: str,
    *,
    source: str = "fmp_income_statement",
    status_code: int | None = None,
) -> ToolResult:
    """Shorthand for FAILED ToolResult with an FMP-shaped source."""
    return ToolResult(
        status="FAILED", data=None,
        as_of=_now_iso(),
        source=source,
        note=note,
    )


__all__ = [
    "FundamentalsTool",
    "DEFAULT_API_BASE",
    "DEFAULT_CACHE_TTL_S",
    "DEFAULT_LIMIT",
    "DEFAULT_LIMIT_QUARTERLY",
]
