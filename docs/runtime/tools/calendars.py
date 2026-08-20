"""
tools/calendars.py — Earnings + IPO calendars via Finnhub.

Free-with-API-key. Same credentials as ``consensus`` and
``quotes_realtime``: sign up at https://finnhub.io/ (free tier:
60 req/min). All endpoints below are inclusive of the same 60/min
budget when called together with the other Finnish tools.

Two endpoints, two public methods on a single dataclass
(``runtime.tools.calendars.CalendarsTool``):

  1. ``earnings(ticker=None, start=None, end=None)``
        ``GET /calendar/earnings?from=YYYY-MM-DD&to=YYYY-MM-DD&symbol=AAPL``
        Returns the list of upcoming earnings announcements within the
        date window. ``ticker`` is OPTIONAL — when omitted, returns the
        whole market across the window. When set, filters to one
        ticker.

        Response shape from Finnhub:
        ```
        {"earningsCalendar": [
            {"date": "2025-08-21", "hour": "amc", "quarter": 2, "year": 2025,
             "epsActual": null, "epsEstimate": 1.34,
             "revenueActual": null, "revenueEstimate": 88400000000,
             "symbol": "NVDA"},
            ...
        ]}
        ```
        The wrapper key is ``earningsCalendar`` (yes, with capital C).
        ``hour`` is one of ``"bmo"`` (before market open), ``"dmh"``
        (during market hours), or ``"amc"`` (after market close).

        Default method of the tool — the single most-asked calendar
        question is "when is the next print?". Cached 6 h. Window is
        clamped to 90 days max (Finnhub's free-tier daily cap).

  2. ``ipo(start=None, end=None)``
        ``GET /calendar/ipo?from=YYYY-MM-DD&to=YYYY-MM-DD``
        Returns the list of upcoming IPOs within the date window.
        ``ticker`` not applicable. Response:
        ```
        {"ipoCalendar": [
            {"date": "2025-09-12", "exchange": "NASDAQ",
             "name": "Acme Co", "numberOfShares": 12000000,
             "price": "12.00-14.00", "status": "priced",
             "symbol": "ACME", "totalSharesValue": 156000000},
            ...
        ]}
        ```
        Cached 6 h. Same 90-day window cap.

Date defaults (when caller passes None):
  - ``start`` → today (UTC)
  - ``end``   → today + 30 days (UTC)

Date format: ISO ``YYYY-MM-DD``. Validation rejects:
  - non-ISO strings (raises FAILED, no silent passthrough)
  - ``end < start``
  - window > 90 days (failed with "window too wide; max 90 days")

Authentication: Finnhub's ``?token=...`` query-string protocol (same
as ``quotes_realtime``). Token is redacted from any note / log URL.

This connector is OPTIONAL — it's a "context anchor" for the chat
timeline rather than a primary input to the model. Default
``recommended=True`` because the brief almost always wants to know
when the next print is.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from . import ToolResult


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

DEFAULT_API_BASE = "https://finnhub.io/api/v1"
DEFAULT_USER_AGENT = "Labourious Analyst [email protected]"
DEFAULT_TIMEOUT_S = 15
DEFAULT_CACHE_TTL_S = 6 * 3600    # 6 h — calendars move on filings, not real-time
DEFAULT_WINDOW_DAYS_DEFAULT = 30  # when caller doesn't specify end
DEFAULT_WINDOW_DAYS_MAX = 90      # Finnhub free-tier cap

_PATH_EARNINGS = "/calendar/earnings"
_PATH_IPO = "/calendar/ipo"

# Wrapper keys Finnhub returns data under.
_KEY_EARNINGS_WRAPPER = "earningsCalendar"
_KEY_IPO_WRAPPER = "ipoCalendar"

HourT = Literal["bmo", "dmh", "amc", ""]   # empty string = unspecified


# ------------------------------------------------------------------
# Tool
# ------------------------------------------------------------------


@dataclass
class CalendarsTool:
    """Finnhub-backed earnings + IPO calendars.

    Parameters
    ----------
    api_key : str | None
        Finnhub API key. ``__post_init__`` reads from
        ``FINNHUB_API_KEY`` then ``LABOURIOUS_FINNHUB_KEY``.
    api_base : str
        Override for tests; production never changes this.
    user_agent : str
        Polite UA, same string across our providers.
    request_timeout_s : int
        Per-request timeout. 15 s is generous.
    cache_ttl_s : int
        Defaults to 6 h. Calendar rows only mutate when filings move.
    window_days_default : int
        When caller doesn't specify `end`, use ``today + this-many-days``.
        Defaults to 30.
    window_days_max : int
        Hard cap on the from/to span. Defaults to 90 (Finnhub free-tier).
    opener : Any
        Override for tests; default ``urllib.request.urlopen``.
    """

    api_key: str | None = None
    api_base: str = DEFAULT_API_BASE
    user_agent: str = ""
    request_timeout_s: int = DEFAULT_TIMEOUT_S
    cache_ttl_s: int = DEFAULT_CACHE_TTL_S
    window_days_default: int = DEFAULT_WINDOW_DAYS_DEFAULT
    window_days_max: int = DEFAULT_WINDOW_DAYS_MAX
    opener: Any = field(default=None)
    _earnings_cache: dict[str, tuple[float, ToolResult]] = \
        field(default_factory=dict)
    _ipo_cache: dict[str, tuple[float, ToolResult]] = \
        field(default_factory=dict)

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
    def earnings(
        self,
        ticker: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> ToolResult:
        """Earnings calendar within ``[start, end]`` date window.

        Parameters
        ----------
        ticker : str | None
            Optional filter — when set, returns only that ticker's
            prints. When None / empty, returns the whole market across
            the window.
        start : str | None
            ISO date string ``YYYY-MM-DD``. None → today (UTC).
        end : str | None
            ISO date string ``YYYY-MM-DD``. None → today + 30 days.

        Returns
        -------
        ToolResult
            ``data`` shaped ``{"rows": [...], "meta": {...}}``.
            ``rows`` is the list of `earningsCalendar` entries from
            Finnhub. Each entry has ``{date, hour, quarter, year,
            epsActual, epsEstimate, revenueActual, revenueEstimate,
            symbol}`` (the actuals are populated post-print — always
            null for upcoming prints).
        """
        ticker_norm = (ticker or "").strip().upper() if ticker else ""
        try:
            start_d, end_d = _resolve_window(
                start, end, self.window_days_default, self.window_days_max,
            )
        except ValueError as e:
            return _failed(
                None, str(e), source="finnhub_earnings_calendar",
            )

        cache_key = (
            f"earnings::{ticker_norm}::{start_d.isoformat()}::{end_d.isoformat()}"
        )
        cached = self._earnings_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            return _failed(None, _no_key_msg(),
                           source="finnhub_earnings_calendar")

        qs: dict[str, str] = {
            "from": start_d.isoformat(),
            "to": end_d.isoformat(),
            "token": self.api_key,
        }
        if ticker_norm:
            qs["symbol"] = ticker_norm

        url = f"{self.api_base}{_PATH_EARNINGS}?{urllib.parse.urlencode(qs)}"
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None,
                _http_note("calendar/earnings", e.code, e.reason),
                source="finnhub_earnings_calendar",
            )
        except urllib.error.URLError as e:
            return _failed(
                None,
                f"Finnhub network error on /calendar/earnings: {e.reason}",
                source="finnhub_earnings_calendar",
            )
        except Exception as e:
            return _failed(
                None,
                f"Finnhub parse error on /calendar/earnings: "
                f"{type(e).__name__}: {e}",
                source="finnhub_earnings_calendar",
            )

        if isinstance(payload, dict) and (
            "error" in payload or "Error" in payload
        ):
            return _failed(
                None,
                str(payload.get("error") or payload.get("Error")),
                source="finnhub_earnings_calendar",
            )

        if not isinstance(payload, dict):
            return _failed(
                None,
                f"Finnhub returned non-object payload on "
                f"/calendar/earnings: {type(payload).__name__}",
                source="finnhub_earnings_calendar",
            )

        rows_raw = payload.get(_KEY_EARNINGS_WRAPPER) or []
        if not isinstance(rows_raw, list):
            return _failed(
                None,
                f"Finnhub returned {type(rows_raw).__name__} in "
                f"'{_KEY_EARNINGS_WRAPPER}' (expected list)",
                source="finnhub_earnings_calendar",
            )

        if not rows_raw:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source="finnhub_earnings_calendar",
                note=(
                    f"Finnhub /calendar/earnings for "
                    f"{'all-mkt' if not ticker_norm else ticker_norm} "
                    f"[{start_d.isoformat()}..{end_d.isoformat()}]: "
                    f"no scheduled prints in window."
                ),
            )

        # Cast each row into a stable shape — Finnhub fields are mixed
        # str/number/null, no need to enforce more than that.
        rows = []
        for r in rows_raw:
            try:
                rows.append({
                    "date":             str(r.get("date") or ""),
                    "symbol":           str(r.get("symbol") or ""),
                    "hour":             str(r.get("hour") or ""),
                    "quarter":          r.get("quarter"),
                    "year":             r.get("year"),
                    "eps_estimate":     r.get("epsEstimate"),
                    "eps_actual":       r.get("epsActual"),
                    "revenue_estimate": r.get("revenueEstimate"),
                    "revenue_actual":   r.get("revenueActual"),
                })
            except Exception:
                # Defensive — never let one bad row crash the whole pull.
                continue

        meta = {
            "ticker": ticker_norm or None,
            "scope":  "ticker" if ticker_norm else "all",
            "start":  start_d.isoformat(),
            "end":    end_d.isoformat(),
            "window_days": (end_d - start_d).days,
            "row_count": len(rows),
            "as_of": as_of,
        }

        result = ToolResult(
            status="SUCCESS",
            data={"rows": rows, "meta": meta},
            as_of=as_of,
            source="finnhub_earnings_calendar",
            note=(
                f"Finnhub /calendar/earnings "
                f"{'(all-mkt' if not ticker_norm else f'for {ticker_norm}'}"
                f" [{start_d.isoformat()}..{end_d.isoformat()}]: "
                f"{len(rows)} scheduled prints. "
                f"URL: {_redact_token(url)}"
            ),
        )
        self._earnings_cache_put(cache_key, result)
        return result

    def ipo(
        self,
        start: str | None = None,
        end: str | None = None,
    ) -> ToolResult:
        """IPO calendar within ``[start, end]`` date window.

        Parameters
        ----------
        start : str | None
            ISO date string ``YYYY-MM-DD``. None → today (UTC).
        end : str | None
            ISO date string ``YYYY-MM-DD``. None → today + 30 days.

        Returns
        -------
        ToolResult
            ``data`` shaped ``{"rows": [...], "meta": {...}}``.
            Each row: ``{date, exchange, name, numberOfShares,
            price, status, symbol, totalSharesValue}``.
        """
        try:
            start_d, end_d = _resolve_window(
                start, end, self.window_days_default, self.window_days_max,
            )
        except ValueError as e:
            return _failed(
                None, str(e), source="finnhub_ipo_calendar",
            )

        cache_key = f"ipo::{start_d.isoformat()}::{end_d.isoformat()}"
        cached = self._ipo_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            return _failed(None, _no_key_msg(),
                           source="finnhub_ipo_calendar")

        qs: dict[str, str] = {
            "from": start_d.isoformat(),
            "to": end_d.isoformat(),
            "token": self.api_key,
        }
        url = f"{self.api_base}{_PATH_IPO}?{urllib.parse.urlencode(qs)}"
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None,
                _http_note("calendar/ipo", e.code, e.reason),
                source="finnhub_ipo_calendar",
            )
        except urllib.error.URLError as e:
            return _failed(
                None,
                f"Finnhub network error on /calendar/ipo: {e.reason}",
                source="finnhub_ipo_calendar",
            )
        except Exception as e:
            return _failed(
                None,
                f"Finnhub parse error on /calendar/ipo: "
                f"{type(e).__name__}: {e}",
                source="finnhub_ipo_calendar",
            )

        if isinstance(payload, dict) and (
            "error" in payload or "Error" in payload
        ):
            return _failed(
                None,
                str(payload.get("error") or payload.get("Error")),
                source="finnhub_ipo_calendar",
            )

        if not isinstance(payload, dict):
            return _failed(
                None,
                f"Finnhub returned non-object payload on "
                f"/calendar/ipo: {type(payload).__name__}",
                source="finnhub_ipo_calendar",
            )

        rows_raw = payload.get(_KEY_IPO_WRAPPER) or []
        if not isinstance(rows_raw, list):
            return _failed(
                None,
                f"Finnhub returned {type(rows_raw).__name__} in "
                f"'{_KEY_IPO_WRAPPER}' (expected list)",
                source="finnhub_ipo_calendar",
            )

        if not rows_raw:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source="finnhub_ipo_calendar",
                note=(
                    f"Finnhub /calendar/ipo [{start_d.isoformat()}.."
                    f"{end_d.isoformat()}]: no scheduled IPOs in window."
                ),
            )

        rows = []
        for r in rows_raw:
            try:
                rows.append({
                    "date":              str(r.get("date") or ""),
                    "symbol":            str(r.get("symbol") or ""),
                    "name":              str(r.get("name") or ""),
                    "exchange":          str(r.get("exchange") or ""),
                    "number_of_shares":  r.get("numberOfShares"),
                    "price":             str(r.get("price") or ""),
                    "status":            str(r.get("status") or ""),
                    "total_shares_value": r.get("totalSharesValue"),
                })
            except Exception:
                continue

        meta = {
            "start": start_d.isoformat(),
            "end":   end_d.isoformat(),
            "window_days": (end_d - start_d).days,
            "row_count": len(rows),
            "as_of": as_of,
        }

        result = ToolResult(
            status="SUCCESS",
            data={"rows": rows, "meta": meta},
            as_of=as_of,
            source="finnhub_ipo_calendar",
            note=(
                f"Finnhub /calendar/ipo "
                f"[{start_d.isoformat()}..{end_d.isoformat()}]: "
                f"{len(rows)} scheduled IPOs. "
                f"URL: {_redact_token(url)}"
            ),
        )
        self._ipo_cache_put(cache_key, result)
        return result

    def clear_cache(self) -> None:
        """Drop both caches. Useful for tests / ops."""
        self._earnings_cache.clear()
        self._ipo_cache.clear()

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

    def _earnings_cache_hit(self, key: str) -> ToolResult | None:
        return _cache_hit(self._earnings_cache, key, self.cache_ttl_s)
    def _earnings_cache_put(self, key: str, tr: ToolResult) -> None:
        _cache_put(self._earnings_cache, key, tr)

    def _ipo_cache_hit(self, key: str) -> ToolResult | None:
        return _cache_hit(self._ipo_cache, key, self.cache_ttl_s)
    def _ipo_cache_put(self, key: str, tr: ToolResult) -> None:
        _cache_put(self._ipo_cache, key, tr)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _now_iso() -> str:
    """UTC wallclock as ISO-8601, second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonicalize_arg_date(s: str) -> date | None:
    """Parse ``YYYY-MM-DD`` strictly. Returns None on any deviation."""
    if not s:
        return None
    s = s.strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _resolve_window(
    start: str | None,
    end: str | None,
    default_window_days: int,
    max_window_days: int,
) -> tuple[date, date]:
    """Resolve final (start, end) dates; raise ``ValueError`` if invalid."""
    today = _today_utc()
    start_d = _canonicalize_arg_date(start) if start else None
    if start_d is None and start:
        raise ValueError(
            f"start {start!r} is not a valid YYYY-MM-DD date."
        )
    end_d = _canonicalize_arg_date(end) if end else None
    if end_d is None and end:
        raise ValueError(
            f"end {end!r} is not a valid YYYY-MM-DD date."
        )

    if start_d is None:
        start_d = today
    if end_d is None:
        end_d = start_d + timedelta(days=default_window_days)

    if end_d < start_d:
        raise ValueError(
            f"end {end_d.isoformat()} is before start "
            f"{start_d.isoformat()} — window must span forward in time."
        )
    span = (end_d - start_d).days
    if span > max_window_days:
        raise ValueError(
            f"window too wide: {span} days (max {max_window_days} days, "
            f"Finnhub free-tier cap). Narrow the from/to range."
        )
    return start_d, end_d


def _no_key_msg() -> str:
    return (
        "FINNHUB_API_KEY not configured — set it in your shell or in "
        "~/.labourious/config.yaml to enable Finnhub calendars. "
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
            f"free-tier rate limit likely hit (60 req/min). Wait and retry."
        )
    if code == 429:
        return f"Finnhub HTTP 429 on /{endpoint_short}: rate-limited. Retry."
    return f"Finnhub HTTP {code} on /{endpoint_short}: {reason}"


def _failed(
    tool: "CalendarsTool | None",
    note: str,
    *,
    source: str,
) -> ToolResult:
    """Shorthand for FAILED ToolResult. ``tool`` is accepted positionally
    for signature parity with the rest of the runtime; unused here."""
    return ToolResult(
        status="FAILED", data=None,
        as_of=_now_iso(),
        source=source,
        note=note,
    )


def _cache_hit(
    cache: dict[str, tuple[float, ToolResult]],
    key: str, ttl_s: int,
) -> ToolResult | None:
    stamped = cache.get(key)
    if not stamped:
        return None
    ts, tr = stamped
    if (time.time() - ts) > ttl_s:
        cache.pop(key, None)
        return None
    return tr


def _cache_put(
    cache: dict[str, tuple[float, ToolResult]],
    key: str, tr: ToolResult,
) -> None:
    cache[key] = (time.time(), tr)


__all__ = [
    "CalendarsTool",
    "DEFAULT_API_BASE",
    "DEFAULT_CACHE_TTL_S",
    "DEFAULT_WINDOW_DAYS_DEFAULT",
    "DEFAULT_WINDOW_DAYS_MAX",
]
