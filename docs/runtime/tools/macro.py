"""
tools/macro.py — Macroeconomic data via the Federal Reserve (FRED).

Free-with-API-key. Sign up at https://fred.stlouisfed.org/docs/api/api_key.html
(no quota on the dev tier — just rate-limited at 120 req/min).

This connector is the proper macro suite that complements the
lightweight ``market_data.fred_series`` shim. While ``fred_series``
just gets the last N observations of one series, ``macro.py``
exposes:

  1. ``series(series_id, limit, sort_order)`` — direct series ID
     lookup, default method of the tool
  2. ``search(query, limit)`` — search FRED's series catalog by
     name/keyword (e.g. "real GDP", "10-year treasury")
  3. ``release_calendar(limit)`` — upcoming macro release dates

Three endpoints on a single dataclass
(``runtime.tools.macro.MacroTool``):

  - ``GET /fred/series/observations?series_id={id}&api_key=…&limit=N&sort_order=desc|asc``
  - ``GET /fred/series/search?search_text={q}&api_key=…``
  - ``GET /fred/releases/dates?api_key=…``

Auth goes via query string (``api_key=...``) — we redact it from
any note / log URL. Caching is 24 h (FRED data updates on
calendar — weekly cadence, not real-time).
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

DEFAULT_API_BASE = "https://api.stlouisfed.org/fred"
DEFAULT_USER_AGENT = "Labourious Analyst [email protected]"
DEFAULT_TIMEOUT_S = 15
DEFAULT_CACHE_TTL_S = 24 * 3600       # 24 h — FRED weekly cadence

DEFAULT_LIMIT = 100                    # series observations backcount
DEFAULT_LIMIT_MAX_SERIES = 10_000      # FRED max
DEFAULT_LIMIT_DEFAULT_SEARCH = 20
DEFAULT_LIMIT_MAX_SEARCH = 1000       # FRED max
DEFAULT_LIMIT_DEFAULT_RELEASE_CAL = 30
DEFAULT_LIMIT_MAX_RELEASE_CAL = 200

SortOrderT = Literal["asc", "desc"]


# ------------------------------------------------------------------
# Tool
# ------------------------------------------------------------------


@dataclass
class MacroTool:
    """FRED-backed macro series + search + release calendar.

    Parameters
    ----------
    api_key : str | None
        FRED API key. ``__post_init__`` reads from ``FRED_API_KEY``
        then ``LABOURIOUS_FRED_KEY``.
    api_base : str
        Override for tests; production never changes this.
    user_agent : str
        Polite UA, same string across all providers.
    request_timeout_s : int
        Per-request timeout.
    cache_ttl_s : int
        Defaults to 24 h. FRED data updates weekly.
    opener : Any
        Override for tests; default ``urllib.request.urlopen``.
    """

    api_key: str | None = None
    api_base: str = DEFAULT_API_BASE
    user_agent: str = ""
    request_timeout_s: int = DEFAULT_TIMEOUT_S
    cache_ttl_s: int = DEFAULT_CACHE_TTL_S
    opener: Any = field(default=None)
    _series_cache: dict[str, tuple[float, ToolResult]] = \
        field(default_factory=dict)
    _search_cache: dict[str, tuple[float, ToolResult]] = \
        field(default_factory=dict)
    _release_cache: dict[str, tuple[float, ToolResult]] = \
        field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (self.api_key and self.api_key.strip()):
            self.api_key = (
                os.environ.get("FRED_API_KEY")
                or os.environ.get("LABOURIOUS_FRED_KEY")
            )
        if not (self.user_agent and self.user_agent.strip()):
            self.user_agent = (
                os.environ.get("FRED_USER_AGENT")
                or os.environ.get("LABOURIOUS_DEFAULT_USER_AGENT")
                or DEFAULT_USER_AGENT
            )
        if self.opener is None:
            self.opener = urllib.request.urlopen

    # ----------------------------------------------------------- public API
    def series(
        self,
        series_id: str,
        limit: int = DEFAULT_LIMIT,
        sort_order: str = "desc",
    ) -> ToolResult:
        """FRED series observations — the primary macro lookup.

        Parameters
        ----------
        series_id : str
            FRED series id (e.g. ``"GDP"``, ``"DGS10"``,
            ``"UNRATE"``). Strict-validated as non-empty.
        limit : int
            Max observations returned. Clamped to 10,000
            (FRED's hard ceiling).
        sort_order : str
            ``"desc"`` (default, newest first) or ``"asc"``.

        Returns
        -------
        ToolResult
            ``data`` shaped ``{"observations": [...], "meta": {...}}``.
            Each observation: ``{date, value, realtime_start,
            realtime_end}``.
        """
        series_id = (series_id or "").strip().upper()
        if not series_id:
            return _failed(
                None, "series_id must be a non-empty string",
                source="fred_series",
            )

        canonical_sort = _canonicalize_sort(sort_order)
        if canonical_sort is None:
            return _failed(
                None,
                f"sort_order {sort_order!r} not supported "
                f"(use 'asc' or 'desc').",
                source="fred_series",
            )

        limit = max(1, min(int(limit), DEFAULT_LIMIT_MAX_SERIES))

        cache_key = f"series::{series_id}::{canonical_sort}::{limit}"
        cached = self._series_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            return _failed(None, _no_key_msg(), source="fred_series")

        # Note: FRED's endpoint is `/fred/series/observations` under the
        # base, so the path has a `/fred/` prefix despite being on
        # `api.stlouisfed.org/fred`. We keep the base short and append
        # the literal endpoint path.
        qs: dict[str, str] = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": canonical_sort,
            "limit": str(limit),
        }
        url = (
            f"{self.api_base}/series/observations"
            f"?{urllib.parse.urlencode(qs)}"
        )
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None,
                _http_note("/series/observations", e.code, e.reason),
                source="fred_series",
            )
        except urllib.error.URLError as e:
            return _failed(
                None,
                f"FRED network error on /series/observations: {e.reason}",
                source="fred_series",
            )
        except Exception as e:
            return _failed(
                None,
                f"FRED parse error on /series/observations: "
                f"{type(e).__name__}: {e}",
                source="fred_series",
            )

        if not isinstance(payload, dict):
            return _failed(
                None,
                f"FRED returned non-object payload on "
                f"/series/observations: {type(payload).__name__}",
                source="fred_series",
            )

        if "error_code" in payload or "error_message" in payload:
            return _failed(
                None,
                f"FRED error: {payload.get('error_message') or payload.get('error_code') or payload!r}",
                source="fred_series",
            )

        obs_raw = payload.get("observations") or []
        if not isinstance(obs_raw, list):
            return _failed(
                None,
                f"FRED returned {type(obs_raw).__name__} in "
                f"'observations' (expected list)",
                source="fred_series",
            )

        if not obs_raw:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source="fred_series",
                note=(
                    f"FRED series {series_id}: no observations returned "
                    f"(unknown series id or empty dataset)."
                ),
            )

        observations = []
        for r in obs_raw:
            try:
                v = r.get("value")
                v_norm = float(v) if v is not None and v != "." else None
                observations.append({
                    "date":            str(r.get("date") or ""),
                    "value":           v_norm,
                    "realtime_start":  str(r.get("realtime_start") or ""),
                    "realtime_end":    str(r.get("realtime_end") or ""),
                })
            except Exception:
                continue

        meta = {
            "series_id": series_id,
            "sort_order": canonical_sort,
            "row_count": len(observations),
            "as_of": as_of,
        }

        result = ToolResult(
            status="SUCCESS",
            data={"observations": observations, "meta": meta},
            as_of=as_of,
            source="fred_series",
            note=(
                f"FRED series {series_id}: {len(observations)} observations "
                f"(sort={canonical_sort}, limit={limit}). "
                f"URL: {_redact_apikey(url)}"
            ),
        )
        self._series_cache_put(cache_key, result)
        return result

    def search(
        self,
        query: str,
        limit: int = DEFAULT_LIMIT_DEFAULT_SEARCH,
    ) -> ToolResult:
        """Search the FRED series catalog by keyword.

        Parameters
        ----------
        query : str
            Search keyword (e.g. ``"real GDP"``).
        limit : int
            Max series returned, clamped to 1000.

        Returns
        -------
        ToolResult
            ``data`` shaped ``{"series": [...], "meta": {...}}``.
            Each series: ``{id, title, frequency, units, seasonal_adjustment,
            observation_start, observation_end, popularity}``.
        """
        query = (query or "").strip()
        if not query:
            return _failed(
                None, "query must be a non-empty string",
                source="fred_search",
            )

        limit = max(1, min(int(limit), DEFAULT_LIMIT_MAX_SEARCH))

        cache_key = f"search::{query}::{limit}"
        cached = self._search_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            return _failed(None, _no_key_msg(), source="fred_search")

        qs: dict[str, str] = {
            "search_text": query,
            "api_key": self.api_key,
            "file_type": "json",
            "limit": str(limit),
        }
        url = f"{self.api_base}/series/search?{urllib.parse.urlencode(qs)}"
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None,
                _http_note("/series/search", e.code, e.reason),
                source="fred_search",
            )
        except urllib.error.URLError as e:
            return _failed(
                None,
                f"FRED network error on /series/search: {e.reason}",
                source="fred_search",
            )
        except Exception as e:
            return _failed(
                None,
                f"FRED parse error on /series/search: "
                f"{type(e).__name__}: {e}",
                source="fred_search",
            )

        if not isinstance(payload, dict):
            return _failed(
                None,
                f"FRED returned non-object payload on "
                f"/series/search: {type(payload).__name__}",
                source="fred_search",
            )

        if "error_code" in payload or "error_message" in payload:
            return _failed(
                None,
                f"FRED error: {payload.get('error_message') or payload.get('error_code') or payload!r}",
                source="fred_search",
            )

        series_raw = payload.get("seriess") or []
        if not isinstance(series_raw, list):
            return _failed(
                None,
                f"FRED returned {type(series_raw).__name__} in "
                f"'seriess' (expected list — note FRED spelling)",
                source="fred_search",
            )

        if not series_raw:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source="fred_search",
                note=f"FRED search for query={query!r}: no matching series",
            )

        series_norm = []
        for s in series_raw:
            try:
                # FRED returns popularity as int 0-100.
                pop = s.get("popularity")
                try:
                    pop = int(pop) if pop is not None else None
                except (ValueError, TypeError):
                    pop = None
                series_norm.append({
                    "id":                  str(s.get("id") or ""),
                    "title":               str(s.get("title") or ""),
                    "frequency":           str(s.get("frequency") or ""),
                    "units":               str(s.get("units") or ""),
                    "seasonal_adjustment": str(s.get("seasonal_adjustment") or ""),
                    "observation_start":   str(s.get("observation_start") or ""),
                    "observation_end":     str(s.get("observation_end") or ""),
                    "popularity":          pop,
                })
            except Exception:
                continue

        meta = {
            "query": query,
            "row_count": len(series_norm),
            "as_of": as_of,
        }

        result = ToolResult(
            status="SUCCESS",
            data={"series": series_norm, "meta": meta},
            as_of=as_of,
            source="fred_search",
            note=(
                f"FRED search for query={query!r}: {len(series_norm)} series "
                f"(limit={limit}). URL: {_redact_apikey(url)}"
            ),
        )
        self._search_cache_put(cache_key, result)
        return result

    def release_calendar(
        self,
        limit: int = DEFAULT_LIMIT_DEFAULT_RELEASE_CAL,
    ) -> ToolResult:
        """Upcoming FRED release dates.

        Parameters
        ----------
        limit : int
            Max records returned. Clamped to 200.

        Returns
        -------
        ToolResult
            ``data`` shaped ``{"release_dates": [...], "meta": {...}}``.
            Each release: ``{release_id, release_name, date}``.
        """
        limit = max(1, min(int(limit), DEFAULT_LIMIT_MAX_RELEASE_CAL))

        cache_key = f"release::{limit}"
        cached = self._release_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            return _failed(None, _no_key_msg(), source="fred_release_calendar")

        qs: dict[str, str] = {
            "api_key": self.api_key,
            "file_type": "json",
            "limit": str(limit),
        }
        url = f"{self.api_base}/releases/dates?{urllib.parse.urlencode(qs)}"
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None,
                _http_note("/releases/dates", e.code, e.reason),
                source="fred_release_calendar",
            )
        except urllib.error.URLError as e:
            return _failed(
                None,
                f"FRED network error on /releases/dates: {e.reason}",
                source="fred_release_calendar",
            )
        except Exception as e:
            return _failed(
                None,
                f"FRED parse error on /releases/dates: "
                f"{type(e).__name__}: {e}",
                source="fred_release_calendar",
            )

        if not isinstance(payload, dict):
            return _failed(
                None,
                f"FRED returned non-object payload on "
                f"/releases/dates: {type(payload).__name__}",
                source="fred_release_calendar",
            )

        if "error_code" in payload or "error_message" in payload:
            return _failed(
                None,
                f"FRED error: {payload.get('error_message') or payload.get('error_code') or payload!r}",
                source="fred_release_calendar",
            )

        # FRED /releases/dates returns keys: release_dates (list of
        # objects) and, optionally, a flat array if the request asks
        # for older data. We accept both shapes.
        if isinstance(payload.get("release_dates"), list):
            releases_raw = payload["release_dates"]
        elif isinstance(payload.get("release_date"), list):
            # alternate naming seen across FRED versions
            releases_raw = payload["release_date"]
        else:
            releases_raw = []

        if not releases_raw:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source="fred_release_calendar",
                note=f"FRED /releases/dates: no upcoming releases",
            )

        releases_norm = []
        for r in releases_raw:
            try:
                releases_norm.append({
                    "release_id":   str(r.get("release_id") or ""),
                    "release_name": str(r.get("release_name") or ""),
                    "date":         str(r.get("date") or ""),
                })
            except Exception:
                continue

        meta = {
            "row_count": len(releases_norm),
            "as_of": as_of,
        }

        result = ToolResult(
            status="SUCCESS",
            data={"release_dates": releases_norm, "meta": meta},
            as_of=as_of,
            source="fred_release_calendar",
            note=(
                f"FRED /releases/dates: {len(releases_norm)} upcoming "
                f"releases (limit={limit}). "
                f"URL: {_redact_apikey(url)}"
            ),
        )
        self._release_cache_put(cache_key, result)
        return result

    def clear_cache(self) -> None:
        """Drop all three caches."""
        self._series_cache.clear()
        self._search_cache.clear()
        self._release_cache.clear()

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

    def _series_cache_hit(self, key: str) -> ToolResult | None:
        return _cache_hit(self._series_cache, key, self.cache_ttl_s)
    def _series_cache_put(self, key: str, tr: ToolResult) -> None:
        _cache_put(self._series_cache, key, tr)

    def _search_cache_hit(self, key: str) -> ToolResult | None:
        return _cache_hit(self._search_cache, key, self.cache_ttl_s)
    def _search_cache_put(self, key: str, tr: ToolResult) -> None:
        _cache_put(self._search_cache, key, tr)

    def _release_cache_hit(self, key: str) -> ToolResult | None:
        return _cache_hit(self._release_cache, key, self.cache_ttl_s)
    def _release_cache_put(self, key: str, tr: ToolResult) -> None:
        _cache_put(self._release_cache, key, tr)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonicalize_sort(s: str) -> str | None:
    if not s:
        return None
    s = s.strip().lower()
    if s in ("asc", "ascending", "oldest"):
        return "asc"
    if s in ("desc", "descending", "newest"):
        return "desc"
    return None


def _no_key_msg() -> str:
    return (
        "FRED_API_KEY not configured — set it in your shell or in "
        "~/.labourious/config.yaml to enable FRED macro series. "
        "Sign up free at https://fred.stlouisfed.org/docs/api/api_key.html "
        "(120 req/min no-quota dev tier)."
    )


def _redact_apikey(url: str) -> str:
    """Replace ``&api_key=…`` or ``?api_key=…`` with ``api_key=REDACTED``."""
    parts = urllib.parse.urlparse(url)
    if not parts.query:
        return url
    qsl = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    redacted = [
        (k, "REDACTED" if k.lower() == "api_key" else v)
        for k, v in qsl
    ]
    return urllib.parse.urlunparse(parts._replace(
        query=urllib.parse.urlencode(redacted)
    ))


def _http_note(endpoint_short: str, code: int | None, reason: Any) -> str:
    code = code or 0
    if code == 400:
        return (
            f"FRED HTTP 400 on {endpoint_short}: bad request. "
            f"Check series_id spelling and parameter values."
        )
    if code == 401:
        return (
            f"FRED HTTP 401 on {endpoint_short}: invalid FRED_API_KEY.\n"
            "Re-check the key in shell or ~/.labourious/config.yaml."
        )
    if code == 403:
        return (
            f"FRED HTTP 403 on {endpoint_short}: forbidden. "
            f"Rate-limit or undeliverable address; wait and retry."
        )
    if code == 429:
        return f"FRED HTTP 429 on {endpoint_short}: rate-limited. Retry."
    return f"FRED HTTP {code} on {endpoint_short}: {reason}"


def _failed(
    tool: "MacroTool | None",
    note: str,
    *,
    source: str,
) -> ToolResult:
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
    "MacroTool",
    "DEFAULT_API_BASE",
    "DEFAULT_CACHE_TTL_S",
    "DEFAULT_LIMIT",
    "DEFAULT_LIMIT_MAX_SERIES",
    "DEFAULT_LIMIT_DEFAULT_SEARCH",
    "DEFAULT_LIMIT_MAX_SEARCH",
    "DEFAULT_LIMIT_DEFAULT_RELEASE_CAL",
    "DEFAULT_LIMIT_MAX_RELEASE_CAL",
]
