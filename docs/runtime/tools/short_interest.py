"""
tools/short_interest.py — Finnhub FINRA-style short interest.

Free, single-source, single-key. Endpoint:
  - ``/stock/short-interest?symbol=…&from=YYYY-MM-DD&to=YYYY-MM-DD`` — biweekly
    FINRA short interest rows.

Why this connector ships: the Contrarian strategy (f3) and Forensic agent
both need a quantitative "is the street shorting this name?" signal.
Without short-interest data, the LLM can only approximate by insider
sells + negative news tone; with this connector, it gets the canonical
FINRA biweekly figure (settlementDate, shortInterest, avgDailyVolume,
daysToCover, shortPercentOfFloat).

Two public methods on ``ShortInterestTool``:
  - ``history(ticker, from_date, to_date)`` — raw rows + a derived
    ``is_squeeze_candidate`` flag (shortInterest > 20 % float AND
    days_to_cover > 3.0 d) plus a 4-week delta.
  - ``latest(ticker)`` — single-row convenience used by the PM bodyguard
    and the Comparator rubric.

Hygiene: same call_tool contract as ``consensus.py`` (ToolResult dataclass,
ttl+key+redact, defensive row casting, clear_cache, Three-Sentinel pattern
SUCCESS/EMPTY/FAILED).
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
from datetime import datetime, timezone
from typing import Any


DEFAULT_API_BASE = "https://finnhub.io/api/v1"
DEFAULT_USER_AGENT = "Labourious Analyst [email protected]"
DEFAULT_TIMEOUT_S = 15

# FINRA reports biweekly (settlement Friday). Window > 365 d is rarely
# needed and Finhub will return the same rows regardless.
DEFAULT_HISTORY_CACHE_TTL_S = 24 * 3600
DEFAULT_LATEST_CACHE_TTL_S = 6 * 3600

PATH_SHORT_INTEREST = "/stock/short-interest"

# Squeeze-candidate rule. Industry rule of thumb ≈ 20 % of float shorted
# AND > 3 days to cover. We bake the rule into the connector so the LLM
# doesn't have to invent it. Tighten later if backtest shows > 50 % false
# positives on 2021 meme cohort.
SHORT_PCT_SQUEEZE_THRESHOLD = 20.0  # %
DAYS_TO_COVER_SQUEEZE_THRESHOLD = 3.0  # days

# When ``from/to`` is not specified we default to a 9-month rolling window
# (≈ 18 biweekly prints) — enough to draw a trend line.
DEFAULT_HISTORY_MONTHS_BACK = 9
HISTORY_MONTHS_CAP = 25


# ------------------------------------------------------------------
# Tool
# ------------------------------------------------------------------


@dataclass
class ShortInterestTool:
    """Finnhub-backed short interest history fetcher.

    Parameters
    ----------
    api_key : str | None
        Finnhub API key. ``__post_init__`` reads from
        ``FINNHUB_API_KEY`` then ``LABOURIOUS_FINNHUB_KEY``.
    api_base : str
        Override for tests.
    user_agent : str
        Polite UA.
    request_timeout_s : int
        Per-request timeout.
    history_cache_ttl_s : int
        Default 24 h (FINRA prints settle biweekly; intra-day staleness
        doesn't matter here).
    latest_cache_ttl_s : int
        Default 6 h.
    opener : Any
        Override for tests.
    """

    api_key: str | None = None
    api_base: str = DEFAULT_API_BASE
    user_agent: str = ""
    request_timeout_s: int = DEFAULT_TIMEOUT_S
    history_cache_ttl_s: int = DEFAULT_HISTORY_CACHE_TTL_S
    latest_cache_ttl_s: int = DEFAULT_LATEST_CACHE_TTL_S
    opener: Any = field(default=None)
    _hist_cache: dict[str, tuple[float, Any]] = field(default_factory=dict)
    _latest_cache: dict[str, tuple[float, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (self.api_key and self.api_key.strip()):
            self.api_key = (
                os.environ.get("FINNHUB_API_KEY")
                or os.environ.get("LABOURIOUS_FINNHUB_KEY")
            )
        if not (self.user_agent and self.user_agent.strip()):
            self.user_agent = (
                os.environ.get("FINNHUB_USER_AGENT")
                or os.environ.get("LABOURIOUS_DEFAULT_USER_AGENT")
                or DEFAULT_USER_AGENT
            )
        if self.opener is None:
            self.opener = urllib.request.urlopen

    # ----------------------------------------------------------- public API
    def history(
        self, ticker: str,
        from_date: str = "", to_date: str = "",
    ) -> Any:
        """Raw biweekly short-interest rows for ``ticker``.

        Returns a SUCCESS ``ToolResult`` with ``data`` shaped:

        ```
        {
          "ticker": "AAPL",
          "rows": [{"settlement_date": "2024-01-15",
                    "short_interest": 105300000,
                    "avg_daily_volume": 56789012,
                    "days_to_cover": 1.85,
                    "short_pct_float": 0.71}, …],
          "summary": {"latest_pct_float": 0.71,
                      "latest_days_to_cover": 1.85,
                      "trend_4w_delta_pct_float": -0.04,
                      "is_squeeze_candidate": false},
          "row_count": N,
          "as_of": "ISO"
        }
        ```

        ``from_date`` / ``to_date`` accept ``YYYY-MM-DD``. If left blank,
        defaults to the trailing ``DEFAULT_HISTORY_MONTHS_BACK`` months
        window (which we expand from 9 to whichever end-of-months needed).
        Cached ``history_cache_ttl_s``.
        """
        from . import ToolResult
        from .consensus import _failed

        ticker = (ticker or "").strip().upper()
        if not ticker:
            return _failed(None, "ticker must be a non-empty string",
                           source="finnhub_short_interest")

        # =====================================================================
        # NEW resolve: if `from_date` and `to_date` are NOT supplied, default
        # to a sensible rolling window. If they're supplied, validate format.
        # =====================================================================
        if not from_date and not to_date:
            today = datetime.now(timezone.utc).date()
            # go back N months
            months_back = DEFAULT_HISTORY_MONTHS_BACK
            if months_back > HISTORY_MONTHS_CAP:
                months_back = HISTORY_MONTHS_CAP
            # rough month rollover (28-day approximation; calendar math is OK
            # since we round to month boundary)
            start = today.replace(day=1)
            for _ in range(months_back):
                if start.month == 1:
                    start = start.replace(year=start.year - 1, month=12)
                else:
                    start = start.replace(month=start.month - 1)
            from_date = start.strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")
        else:
            if not _is_yyyy_mm_dd(from_date):
                return _failed(
                    None,
                    f"from_date must be YYYY-MM-DD (got {from_date!r})",
                    source="finnhub_short_interest",
                )
            if not _is_yyyy_mm_dd(to_date):
                return _failed(
                    None,
                    f"to_date must be YYYY-MM-DD (got {to_date!r})",
                    source="finnhub_short_interest",
                )

        cache_key = f"hist::{ticker}::{from_date}::{to_date}"
        hit = _cache_hit(self._hist_cache, cache_key, self.history_cache_ttl_s)
        if hit is not None:
            return hit

        if not (self.api_key and self.api_key.strip()):
            return _failed(None, _no_key_msg(),
                            source="finnhub_short_interest")

        url = (
            f"{self.api_base}{PATH_SHORT_INTEREST}"
            f"?symbol={urllib.parse.quote(ticker)}"
            f"&from={urllib.parse.quote(from_date)}"
            f"&to={urllib.parse.quote(to_date)}"
            f"&token={urllib.parse.quote(self.api_key)}"
        )
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None, _http_note("short-interest", e.code, e.reason),
                source="finnhub_short_interest",
            )
        except urllib.error.URLError as e:
            return _failed(
                None,
                f"Finnhub network error on /stock/short-interest: {e.reason}",
                source="finnhub_short_interest",
            )
        except Exception as e:
            return _failed(
                None,
                f"Finnhub parse error on /stock/short-interest: "
                f"{type(e).__name__}: {e}",
                source="finnhub_short_interest",
            )

        if isinstance(payload, dict) and ("error" in payload or "Error" in payload):
            return _failed(
                None,
                str(payload.get("error") or payload.get("Error")),
                source="finnhub_short_interest",
            )
        if not isinstance(payload, dict) or "data" not in payload:
            return _failed(
                None,
                f"Finnhub payload for /stock/short-interest missing 'data' "
                f"key (got {type(payload).__name__})",
                source="finnhub_short_interest",
            )

        raw_rows = payload.get("data")
        if not isinstance(raw_rows, list):
            return _failed(
                None,
                f"Finnhub /stock/short-interest 'data' is not a list: "
                f"{type(raw_rows).__name__}",
                source="finnhub_short_interest",
            )

        rows: list[dict[str, Any]] = []
        for r in raw_rows:
            if not isinstance(r, dict):
                continue
            rows.append({
                "settlement_date": str(r.get("settlementDate") or ""),
                "short_interest": _safe_int(r.get("shortInterest")),
                "avg_daily_volume": _safe_int(r.get("avgDailyVolume")),
                "days_to_cover": _safe_float(r.get("daysToCover")),
                "short_pct_float": _safe_float(r.get("shortPercentOfFloat")),
            })

        if not rows:
            return ToolResult(
                status="EMPTY",
                data={
                    "ticker": ticker,
                    "rows": [],
                    "summary": {},
                    "row_count": 0,
                    "as_of": as_of,
                    "url": _redact_token(url),
                },
                as_of=as_of,
                source="finnhub_short_interest",
                note=(
                    f"Finnhub /stock/short-interest for {ticker} "
                    f"{from_date}→{to_date}: no rows."
                ),
            )

        summary = _summarize_short(rows)
        tr = ToolResult(
            status="SUCCESS",
            data={
                "ticker": ticker,
                "rows": rows,
                "summary": summary,
                "row_count": len(rows),
                "from_date": from_date,
                "to_date": to_date,
                "as_of": as_of,
                "url": _redact_token(url),
            },
            as_of=as_of,
            source="finnhub_short_interest",
            note=(
                f"Finnhub /stock/short-interest for {ticker} "
                f"{from_date}→{to_date}: {len(rows)} prints. "
                f"is_squeeze_candidate={summary['is_squeeze_candidate']}. "
                f"URL: {_redact_token(url)}"
            ),
        )
        _cache_put(self._hist_cache, cache_key, tr)
        return tr

    def latest(self, ticker: str) -> Any:
        """One-row convenience: the most recent FINRA biweekly print."""
        # Re-use history so we share the same cache + redacting.
        ticker = (ticker or "").strip().upper()
        if not ticker:
            from .consensus import _failed
            return _failed(None, "ticker must be a non-empty string",
                           source="finnhub_short_interest")

        cache_key = f"latest::{ticker}"
        hit = _cache_hit(self._latest_cache, cache_key, self.latest_cache_ttl_s)
        if hit is not None:
            return hit

        tr = self.history(ticker)  # trunk-managed default window
        if tr.status != "SUCCESS":
            return tr  # propagate FAILED/EMPTY
        # Pick the most recent settlement_date, not just upstream's last row
        rows = tr.data["rows"]
        dated = [r for r in rows if r.get("settlement_date")]
        latest_row = (sorted(dated, key=lambda r: r["settlement_date"])[-1]
                      if dated else None)
        out_data = {
            "ticker": ticker,
            "row": latest_row,
            "summary": tr.data.get("summary", {}),
            "row_count": 1 if latest_row else 0,
            "as_of": tr.data["as_of"],
            "url": tr.data["url"],
        }
        latest_tr = tr.__class__(
            status="SUCCESS",
            data=out_data,
            as_of=tr.as_of,
            source=tr.source,
            note=(
                f"Finnhub latest short-interest for {ticker}: "
                f"settlement={latest_row['settlement_date']}, "
                f"pct_float={latest_row['short_pct_float']}, "
                f"days_to_cover={latest_row['days_to_cover']}."
            ),
        )
        _cache_put(self._latest_cache, cache_key, latest_tr)
        return latest_tr

    def clear_cache(self) -> None:
        """Drop both caches."""
        self._hist_cache.clear()
        self._latest_cache.clear()

    # ----------------------------------------------------------- internal
    def _fetch_json(self, url: str) -> Any:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            },
        )
        with self.opener(req, timeout=self.request_timeout_s) as resp:
            raw = resp.read()
        if isinstance(raw, bytes):
            try:
                return json.loads(raw.decode("utf-8"))
            except UnicodeDecodeError:
                return json.loads(raw.decode("latin-1"))
        return json.loads(raw)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_yyyy_mm_dd(x: str) -> bool:
    return (
        isinstance(x, str)
        and len(x) == 10
        and x[4] == "-"
        and x[7] == "-"
        and x[:4].isdigit()
        and x[5:7].isdigit()
        and x[8:].isdigit()
    )


def _safe_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v


def _safe_int(x: Any) -> int | None:
    if x is None:
        return None
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def _summarize_short(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Latest row + 4-week delta + squeeze-candidate flag.

    All derivations baked into the connector so the LLM doesn't invent them.
    """
    rows_sorted = sorted(
        [r for r in rows
         if r.get("settlement_date") and r["short_pct_float"] is not None],
        key=lambda r: r["settlement_date"],
    )
    if not rows_sorted:
        return {
            "latest_pct_float": None,
            "latest_days_to_cover": None,
            "trend_4w_delta_pct_float": None,
            "is_squeeze_candidate": False,
        }

    latest = rows_sorted[-1]
    pct = latest["short_pct_float"]
    dtc = latest["days_to_cover"]
    # 4w ago = 2 biweekly prints back (FINRA prints are 14d apart)
    back_idx = max(0, len(rows_sorted) - 3)
    back = rows_sorted[back_idx]
    delta = None
    if pct is not None and back["short_pct_float"] is not None:
        delta = round(pct - back["short_pct_float"], 4)

    is_sq = False
    if pct is not None and dtc is not None:
        is_sq = (pct * 100.0 >= SHORT_PCT_SQUEEZE_THRESHOLD
                 and dtc >= DAYS_TO_COVER_SQUEEZE_THRESHOLD)

    return {
        "latest_pct_float": pct,
        "latest_days_to_cover": dtc,
        "trend_4w_delta_pct_float": delta,
        "is_squeeze_candidate": is_sq,
    }


def _no_key_msg() -> str:
    return (
        "FINNHUB_API_KEY not configured — set it in your shell or in "
        "~/.labourious/config.yaml to enable Finnhub short interest. "
        "Sign up free at https://finnhub.io/."
    )


def _redact_token(url: str) -> str:
    """Replace ``&token=…`` or ``?token=…`` with ``REDACTED``."""
    parts = urllib.parse.urlparse(url)
    if not parts.query:
        return url
    qsl = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    redacted = [(k, "REDACTED" if k.lower() == "token" else v) for k, v in qsl]
    return urllib.parse.urlunparse(parts._replace(
        query=urllib.parse.urlencode(redacted)
    ))


def _http_note(endpoint_short: str, code: int | None, reason: Any) -> str:
    code = code or 0
    if code == 401:
        return (
            f"Finnhub HTTP 401 on /{endpoint_short}: invalid FINNHUB_API_KEY.\n"
            "Re-check the key in shell or ~/.labourious/config.yaml."
        )
    if code == 403:
        return (
            f"Finnhub HTTP 403 on /{endpoint_short}: forbidden — "
            "free-tier rate limit likely hit (60 req/min). Wait and retry."
        )
    if code == 429:
        return f"Finnhub HTTP 429 on /{endpoint_short}: rate-limited. Retry."
    return f"Finnhub HTTP {code} on /{endpoint_short}: {reason}"


def _failed(
    tool: Any,
    note: str,
    *,
    source: str = "finnhub_short_interest",
) -> Any:
    """Shorthand for FAILED ToolResult. Mirrors ``consensus._failed``."""
    from . import ToolResult
    return ToolResult(
        status="FAILED", data=None,
        as_of=_now_iso(),
        source=source,
        note=note,
    )


def _cache_hit(
    cache: dict[str, tuple[float, Any]], key: str, ttl_s: int,
) -> Any | None:
    stamped = cache.get(key)
    if not stamped:
        return None
    ts, tr = stamped
    if (time.time() - ts) > ttl_s:
        cache.pop(key, None)
        return None
    return tr


def _cache_put(
    cache: dict[str, tuple[float, Any]], key: str, tr: Any,
) -> None:
    cache[key] = (time.time(), tr)


__all__ = [
    "ShortInterestTool",
    "DEFAULT_API_BASE",
    "DEFAULT_HISTORY_CACHE_TTL_S",
    "DEFAULT_LATEST_CACHE_TTL_S",
    "SHORT_PCT_SQUEEZE_THRESHOLD",
    "DAYS_TO_COVER_SQUEEZE_THRESHOLD",
]
