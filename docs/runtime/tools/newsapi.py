"""
tools/newsapi.py — News articles via NewsAPI.org.

Free-with-API-key tier: 100 requests/day, articles up to 1 month
old on ``/v2/everything`` (the dev-tier lookback cap). Sign up at
https://newsapi.org/register. Auth: ``apiKey=...`` query string.

This connector is the proper Tier-2 alternative to the
``news.google_rss`` fallback in ``tools/news.py``. It gives us:

  - Structured JSON responses (vs RSS XML)
  - Source metadata (publication name, ID, country, language)
  - Date filtering (since, until, ISO-8601)
  - Domain-filtered sources (Bloomberg, Reuters, FT)
  - Top headlines endpoint for current events

Three endpoints, three public methods on a single dataclass
(``runtime.tools.newsapi.NewsAPITool``):

  1. ``everything(query, since=None, until=None, sources=None,
                  language="en", sort_by="publishedAt", limit=20)``
        ``GET /v2/everything?q={query}&...&apiKey=...``
        Full-text search across all indexed articles.
        Default method because it's the most general "find me
        articles about X" answer.

  2. ``top_headlines(query=None, country="us", category=None,
                     limit=20)``
        ``GET /v2/top-headlines?country=us&...&apiKey=...``
        Current top headlines with optional category filter
        (business / technology / general / etc).

  3. ``sources(category=None, language=None, country=None)``
        ``GET /v2/sources?...&apiKey=...``
        List of available source publications. Used by the UI
        settings panel for "pick which sources to filter on".

Auth goes via query string (``apiKey=...``) — we redact it from
the URL echoed in ``ToolResult.note``. Caching is 15 min for
articles, 5 min for top headlines (news moves fast), 1 h for
sources (rarely change).
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

DEFAULT_API_BASE = "https://newsapi.org/v2"
DEFAULT_USER_AGENT = "Labourious Analyst [email protected]"
DEFAULT_TIMEOUT_S = 15

DEFAULT_EVERYTHING_CACHE_TTL_S = 15 * 60           # 15 min — articles slow
DEFAULT_TOP_HEADLINES_CACHE_TTL_S = 5 * 60          # 5 min — news moves fast
DEFAULT_SOURCES_CACHE_TTL_S = 60 * 60              # 1 h — sources static

DEFAULT_LIMIT = 20
DEFAULT_LIMIT_MAX = 100                              # NewsAPI free-tier max

DEFAULT_LOOKBACK_MAX_DAYS = 30                       # NewsAPI free-tier cap

# Valid sort_by values for /v2/everything.
SortByT = Literal["publishedAt", "relevancy", "popularity"]

# Valid category values for /v2/top-headlines (subset of what NewsAPI lists).
CATEGORY_VALUES = (
    "business", "entertainment", "general", "health",
    "science", "sports", "technology",
)

_PATH_EVERYTHING = "/everything"
_PATH_TOP_HEADLINES = "/top-headlines"
_PATH_SOURCES = "/sources"


# ------------------------------------------------------------------
# Tool
# ------------------------------------------------------------------


@dataclass
class NewsAPITool:
    """NewsAPI.org article + headline fetcher.

    Parameters
    ----------
    api_key : str | None
        NewsAPI key. ``__post_init__`` reads from ``NEWSAPI_KEY``
        then ``LABOURIOUS_NEWSAPI_KEY``.
    api_base : str
        Override for tests; production never changes this.
    user_agent : str
        Polite UA, same string across our providers.
    request_timeout_s : int
        Per-request timeout.
    everything_cache_ttl_s : int
        Defaults to 15 min. Articles are slow-moving once published.
    top_headlines_cache_ttl_s : int
        Defaults to 5 min. Headlines cycle fast.
    sources_cache_ttl_s : int
        Defaults to 1 h. Source list is mostly static.
    lookback_max_days : int
        Defaults to 30. NewsAPI free-tier forbids deeper history on
        ``/v2/everything`` — we surface this in the note rather
        than silently truncating results.
    opener : Any
        Override for tests; default ``urllib.request.urlopen``.
    """

    api_key: str | None = None
    api_base: str = DEFAULT_API_BASE
    user_agent: str = ""
    request_timeout_s: int = DEFAULT_TIMEOUT_S
    everything_cache_ttl_s: int = DEFAULT_EVERYTHING_CACHE_TTL_S
    top_headlines_cache_ttl_s: int = DEFAULT_TOP_HEADLINES_CACHE_TTL_S
    sources_cache_ttl_s: int = DEFAULT_SOURCES_CACHE_TTL_S
    lookback_max_days: int = DEFAULT_LOOKBACK_MAX_DAYS
    opener: Any = field(default=None)
    _everything_cache: dict[str, tuple[float, ToolResult]] = \
        field(default_factory=dict)
    _top_headlines_cache: dict[str, tuple[float, ToolResult]] = \
        field(default_factory=dict)
    _sources_cache: dict[str, tuple[float, ToolResult]] = \
        field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (self.api_key and self.api_key.strip()):
            self.api_key = (
                os.environ.get("NEWSAPI_KEY")
                or os.environ.get("LABOURIOUS_NEWSAPI_KEY")
            )
        if not (self.user_agent and self.user_agent.strip()):
            self.user_agent = (
                os.environ.get("NEWSAPI_USER_AGENT")
                or os.environ.get("LABOURIOUS_DEFAULT_USER_AGENT")
                or DEFAULT_USER_AGENT
            )
        if self.opener is None:
            self.opener = urllib.request.urlopen

    # ----------------------------------------------------------- public API
    def everything(
        self,
        query: str,
        since: str | None = None,
        until: str | None = None,
        sources: str | None = None,
        language: str = "en",
        sort_by: str = "publishedAt",
        limit: int = DEFAULT_LIMIT,
    ) -> ToolResult:
        """Full-text search across all indexed NewsAPI articles.

        Parameters
        ----------
        query : str
            Keyword or phrase (e.g. ``"NVDA AI capex"``).
        since : str | None
            ISO date ``YYYY-MM-DD`` (default: today − 7d).
        until : str | None
            ISO date ``YYYY-MM-DD`` (default: today).
        sources : str | None
            Comma-separated source IDs (e.g. ``"bloomberg,reuters"``).
            Free-tier allows up to 20 sources per call.
        language : str
            2-letter ISO language code, default ``"en"``.
        sort_by : str
            One of ``"publishedAt"`` (default), ``"relevancy"``,
            ``"popularity"``.
        limit : int
            Max results, clamped to ``DEFAULT_LIMIT_MAX``.

        Returns
        -------
        ToolResult
            ``data`` shaped ``{"articles": [...], "meta": {...}}``.
            Each article: ``{title, url, published_at, source_name,
            source_id, description}``.
        """
        query = (query or "").strip()
        if not query:
            return _failed(
                None, "query must be a non-empty string",
                source="newsapi_everything",
            )

        limit = max(1, min(int(limit), DEFAULT_LIMIT_MAX))

        canonical_sort = _canonicalize_sort_by(sort_by)
        if canonical_sort is None:
            return _failed(
                None,
                f"sort_by {sort_by!r} not supported "
                f"(use one of: publishedAt, relevancy, popularity).",
                source="newsapi_everything",
            )

        # Validate and date-default the since/until window.
        try:
            since_d, until_d = _resolve_window(
                since, until,
                default_days=self.lookback_max_days - 7,  # 23d
                max_days=self.lookback_max_days,
            )
        except ValueError as e:
            return _failed(
                None, str(e), source="newsapi_everything",
            )

        cache_key = (
            f"everything::{query}::{since_d.isoformat()}::{until_d.isoformat()}"
            f"::{sources or ''}::{language}::{canonical_sort}::{limit}"
        )
        cached = self._everything_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            return _failed(None, _no_key_msg(),
                           source="newsapi_everything")

        qs: dict[str, str] = {
            "q": query,
            "pageSize": str(limit),
            "language": language.strip().lower(),
            "sortBy": canonical_sort,
            "apiKey": self.api_key,
        }
        if since_d:
            qs["from"] = since_d.isoformat()
        if until_d:
            qs["to"] = until_d.isoformat()
        if sources:
            qs["sources"] = sources

        url = f"{self.api_base}{_PATH_EVERYTHING}?{urllib.parse.urlencode(qs)}"
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None,
                _http_note("/v2/everything", e.code, e.reason),
                source="newsapi_everything",
            )
        except urllib.error.URLError as e:
            return _failed(
                None,
                f"NewsAPI network error on /v2/everything: {e.reason}",
                source="newsapi_everything",
            )
        except Exception as e:
            return _failed(
                None,
                f"NewsAPI parse error on /v2/everything: "
                f"{type(e).__name__}: {e}",
                source="newsapi_everything",
            )

        if not isinstance(payload, dict):
            return _failed(
                None,
                f"NewsAPI returned non-object payload on "
                f"/v2/everything: {type(payload).__name__}",
                source="newsapi_everything",
            )

        if payload.get("status") == "error":
            return _failed(
                None,
                f"NewsAPI error: {payload.get('message') or payload.get('code') or payload!r}",
                source="newsapi_everything",
            )

        articles_raw = payload.get("articles") or []
        if not isinstance(articles_raw, list):
            return _failed(
                None,
                f"NewsAPI returned {type(articles_raw).__name__} in "
                f"'articles' (expected list)",
                source="newsapi_everything",
            )

        if not articles_raw:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source="newsapi_everything",
                note=(
                    f"NewsAPI /v2/everything for query={query!r}: 0 articles "
                    f"in [{since_d.isoformat()}..{until_d.isoformat()}]"
                ),
            )

        articles = []
        for a in articles_raw:
            try:
                src = a.get("source") or {}
                if isinstance(src, dict):
                    src_name = src.get("name") or ""
                    src_id = src.get("id") or ""
                else:
                    src_name = str(src)
                    src_id = ""
                articles.append({
                    "title":        str(a.get("title") or ""),
                    "url":          str(a.get("url") or ""),
                    "published_at": str(a.get("publishedAt") or ""),
                    "source_name":  src_name,
                    "source_id":    src_id,
                    "description":  str(a.get("description") or ""),
                    "author":       str(a.get("author") or ""),
                })
            except Exception:
                continue

        meta = {
            "query": query,
            "since": since_d.isoformat(),
            "until": until_d.isoformat(),
            "language": language,
            "sort_by": canonical_sort,
            "row_count": len(articles),
            "total_results": payload.get("totalResults"),
            "as_of": as_of,
        }

        result = ToolResult(
            status="SUCCESS",
            data={"articles": articles, "meta": meta},
            as_of=as_of,
            source="newsapi_everything",
            note=(
                f"NewsAPI /v2/everything for query={query!r}: "
                f"{len(articles)} articles "
                f"[{since_d.isoformat()}..{until_d.isoformat()}]. "
                f"URL: {_redact_apikey(url)}"
            ),
        )
        self._everything_cache_put(cache_key, result)
        return result

    def top_headlines(
        self,
        query: str | None = None,
        country: str = "us",
        category: str | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> ToolResult:
        """Current top headlines, optionally filtered by category.

        Parameters
        ----------
        query : str | None
            Optional keyword filter.
        country : str
            2-letter ISO country code, default ``"us"``.
        category : str | None
            One of ``"business"``, ``"technology"``, etc. None = all.
        limit : int
            Max results, clamped to ``DEFAULT_LIMIT_MAX``.

        Returns
        -------
        ToolResult
            ``data`` shaped ``{"articles": [...], "meta": {...}}``.
        """
        limit = max(1, min(int(limit), DEFAULT_LIMIT_MAX))

        canonical_category: str | None = None
        if category:
            canonical_category = category.strip().lower()
            if canonical_category not in CATEGORY_VALUES:
                return _failed(
                    None,
                    f"category {category!r} not supported "
                    f"(use one of: {', '.join(CATEGORY_VALUES)}).",
                    source="newsapi_top_headlines",
                )

        country_norm = (country or "us").strip().lower()

        cache_key = (
            f"top::{query or ''}::{country_norm}::{canonical_category or ''}"
            f"::{limit}"
        )
        cached = self._top_headlines_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            return _failed(None, _no_key_msg(),
                           source="newsapi_top_headlines")

        qs: dict[str, str] = {
            "pageSize": str(limit),
            "apiKey": self.api_key,
            "country": country_norm,
        }
        if query:
            qs["q"] = query
        if canonical_category:
            qs["category"] = canonical_category

        url = f"{self.api_base}{_PATH_TOP_HEADLINES}?{urllib.parse.urlencode(qs)}"
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None,
                _http_note("/v2/top-headlines", e.code, e.reason),
                source="newsapi_top_headlines",
            )
        except urllib.error.URLError as e:
            return _failed(
                None,
                f"NewsAPI network error on /v2/top-headlines: {e.reason}",
                source="newsapi_top_headlines",
            )
        except Exception as e:
            return _failed(
                None,
                f"NewsAPI parse error on /v2/top-headlines: "
                f"{type(e).__name__}: {e}",
                source="newsapi_top_headlines",
            )

        if not isinstance(payload, dict):
            return _failed(
                None,
                f"NewsAPI returned non-object payload on "
                f"/v2/top-headlines: {type(payload).__name__}",
                source="newsapi_top_headlines",
            )

        if payload.get("status") == "error":
            return _failed(
                None,
                f"NewsAPI error: {payload.get('message') or payload.get('code') or payload!r}",
                source="newsapi_top_headlines",
            )

        articles_raw = payload.get("articles") or []
        if not isinstance(articles_raw, list):
            return _failed(
                None,
                f"NewsAPI returned {type(articles_raw).__name__} in "
                f"'articles' (expected list)",
                source="newsapi_top_headlines",
            )

        if not articles_raw:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source="newsapi_top_headlines",
                note=(
                    f"NewsAPI /v2/top-headlines for "
                    f"country={country_norm}, category={canonical_category or 'all'}: "
                    f"0 articles"
                ),
            )

        articles = []
        for a in articles_raw:
            try:
                src = a.get("source") or {}
                if isinstance(src, dict):
                    src_name = src.get("name") or ""
                    src_id = src.get("id") or ""
                else:
                    src_name = str(src)
                    src_id = ""
                articles.append({
                    "title":        str(a.get("title") or ""),
                    "url":          str(a.get("url") or ""),
                    "published_at": str(a.get("publishedAt") or ""),
                    "source_name":  src_name,
                    "source_id":    src_id,
                    "description":  str(a.get("description") or ""),
                })
            except Exception:
                continue

        meta = {
            "country": country_norm,
            "category": canonical_category or None,
            "query": query,
            "row_count": len(articles),
            "total_results": payload.get("totalResults"),
            "as_of": as_of,
        }

        result = ToolResult(
            status="SUCCESS",
            data={"articles": articles, "meta": meta},
            as_of=as_of,
            source="newsapi_top_headlines",
            note=(
                f"NewsAPI /v2/top-headlines for country={country_norm}, "
                f"category={canonical_category or 'all'}: "
                f"{len(articles)} articles. "
                f"URL: {_redact_apikey(url)}"
            ),
        )
        self._top_headlines_cache_put(cache_key, result)
        return result

    def sources(
        self,
        category: str | None = None,
        language: str | None = None,
        country: str | None = None,
    ) -> ToolResult:
        """List of available NewsAPI source publications.

        Parameters
        ----------
        category, language, country : optional filters.

        Returns
        -------
        ToolResult
            ``data`` shaped ``{"sources": [...], "meta": {...}}``.
            Each source: ``{id, name, description, url, category,
            language, country}``.
        """
        canonical_category: str | None = None
        if category:
            canonical_category = category.strip().lower()
            if canonical_category not in CATEGORY_VALUES:
                return _failed(
                    None,
                    f"category {category!r} not supported "
                    f"(use one of: {', '.join(CATEGORY_VALUES)}).",
                    source="newsapi_sources",
                )

        language_norm = (language or "").strip().lower() or ""
        country_norm = (country or "").strip().lower() or ""

        cache_key = (
            f"sources::{canonical_category or ''}::{language_norm}"
            f"::{country_norm}"
        )
        cached = self._sources_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            return _failed(None, _no_key_msg(),
                           source="newsapi_sources")

        qs: dict[str, str] = {"apiKey": self.api_key}
        if canonical_category:
            qs["category"] = canonical_category
        if language_norm:
            qs["language"] = language_norm
        if country_norm:
            qs["country"] = country_norm

        url = f"{self.api_base}{_PATH_SOURCES}?{urllib.parse.urlencode(qs)}"
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None,
                _http_note("/v2/sources", e.code, e.reason),
                source="newsapi_sources",
            )
        except urllib.error.URLError as e:
            return _failed(
                None,
                f"NewsAPI network error on /v2/sources: {e.reason}",
                source="newsapi_sources",
            )
        except Exception as e:
            return _failed(
                None,
                f"NewsAPI parse error on /v2/sources: "
                f"{type(e).__name__}: {e}",
                source="newsapi_sources",
            )

        if not isinstance(payload, dict):
            return _failed(
                None,
                f"NewsAPI returned non-object payload on "
                f"/v2/sources: {type(payload).__name__}",
                source="newsapi_sources",
            )

        if payload.get("status") == "error":
            return _failed(
                None,
                f"NewsAPI error: {payload.get('message') or payload.get('code') or payload!r}",
                source="newsapi_sources",
            )

        sources_raw = payload.get("sources") or []
        if not isinstance(sources_raw, list):
            return _failed(
                None,
                f"NewsAPI returned {type(sources_raw).__name__} in "
                f"'sources' (expected list)",
                source="newsapi_sources",
            )

        if not sources_raw:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source="newsapi_sources",
                note=(
                    f"NewsAPI /v2/sources: no sources matching filters"
                ),
            )

        sources_norm = []
        for s in sources_raw:
            try:
                sources_norm.append({
                    "id":          str(s.get("id") or ""),
                    "name":        str(s.get("name") or ""),
                    "description": str(s.get("description") or ""),
                    "url":         str(s.get("url") or ""),
                    "category":    str(s.get("category") or ""),
                    "language":    str(s.get("language") or ""),
                    "country":     str(s.get("country") or ""),
                })
            except Exception:
                continue

        meta = {
            "category": canonical_category or None,
            "language": language_norm or None,
            "country": country_norm or None,
            "row_count": len(sources_norm),
            "as_of": as_of,
        }

        result = ToolResult(
            status="SUCCESS",
            data={"sources": sources_norm, "meta": meta},
            as_of=as_of,
            source="newsapi_sources",
            note=(
                f"NewsAPI /v2/sources: {len(sources_norm)} sources "
                f"(category={canonical_category or 'all'}, "
                f"language={language_norm or 'all'}, "
                f"country={country_norm or 'all'}). "
                f"URL: {_redact_apikey(url)}"
            ),
        )
        self._sources_cache_put(cache_key, result)
        return result

    def clear_cache(self) -> None:
        """Drop all three caches."""
        self._everything_cache.clear()
        self._top_headlines_cache.clear()
        self._sources_cache.clear()

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

    def _everything_cache_hit(self, key: str) -> ToolResult | None:
        return _cache_hit(self._everything_cache, key, self.everything_cache_ttl_s)
    def _everything_cache_put(self, key: str, tr: ToolResult) -> None:
        _cache_put(self._everything_cache, key, tr)

    def _top_headlines_cache_hit(self, key: str) -> ToolResult | None:
        return _cache_hit(self._top_headlines_cache, key, self.top_headlines_cache_ttl_s)
    def _top_headlines_cache_put(self, key: str, tr: ToolResult) -> None:
        _cache_put(self._top_headlines_cache, key, tr)

    def _sources_cache_hit(self, key: str) -> ToolResult | None:
        return _cache_hit(self._sources_cache, key, self.sources_cache_ttl_s)
    def _sources_cache_put(self, key: str, tr: ToolResult) -> None:
        _cache_put(self._sources_cache, key, tr)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonicalize_sort_by(s: str) -> str | None:
    if not s:
        return None
    s = s.strip().lower()
    valid = {"publishedat", "relevancy", "popularity"}
    return s if s in valid else None


def _canonicalize_arg_date(s: str | None) -> Any:
    """Parse ``YYYY-MM-DD`` strictly. Returns ``datetime.date`` or None."""
    if not s:
        return None
    s = s.strip()
    try:
        from datetime import datetime as _dt
        return _dt.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _today_utc() -> Any:
    from datetime import datetime as _dt, timezone as _tz
    return _dt.now(_tz.utc).date()


def _resolve_window(
    since: str | None,
    until: str | None,
    default_days: int,
    max_days: int,
) -> tuple[Any, Any]:
    """Resolve final (since, until) dates.

    ``since`` defaults to today − (max_days − 7). ``until`` defaults to today.
    Both strictly validated.
    """
    today = _today_utc()
    since_d = _canonicalize_arg_date(since) if since else None
    if since_d is None and since:
        raise ValueError(
            f"since {since!r} is not a valid YYYY-MM-DD date."
        )
    until_d = _canonicalize_arg_date(until) if until else None
    if until_d is None and until:
        raise ValueError(
            f"until {until!r} is not a valid YYYY-MM-DD date."
        )

    if since_d is None:
        from datetime import timedelta as _td
        since_d = today - _td(days=default_days)
    if until_d is None:
        until_d = today

    if until_d < since_d:
        raise ValueError(
            f"until {until_d.isoformat()} is before since "
            f"{since_d.isoformat()} — window must span forward in time."
        )
    span = (until_d - since_d).days
    if span > max_days:
        raise ValueError(
            f"window too wide: {span} days (max {max_days} days, "
            f"NewsAPI free-tier cap on /v2/everything). Narrow the "
            f"since/until range."
        )
    return since_d, until_d


def _no_key_msg() -> str:
    return (
        "NEWSAPI_KEY not configured — set it in your shell or in "
        "~/.labourious/config.yaml to enable NewsAPI article search. "
        "Sign up free at https://newsapi.org/register "
        "(100 req/day free tier)."
    )


def _redact_apikey(url: str) -> str:
    """Replace ``&apiKey=…`` or ``?apiKey=…`` with ``apikey=REDACTED``."""
    parts = urllib.parse.urlparse(url)
    if not parts.query:
        return url
    qsl = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    redacted = [
        (k, "REDACTED" if k.lower() == "apikey" else v)
        for k, v in qsl
    ]
    return urllib.parse.urlunparse(parts._replace(
        query=urllib.parse.urlencode(redacted)
    ))


def _http_note(endpoint_short: str, code: int | None, reason: Any) -> str:
    code = code or 0
    if code == 401:
        return (
            f"NewsAPI HTTP 401 on {endpoint_short}: invalid NEWSAPI_KEY.\n"
            "Re-check the key in shell or ~/.labourious/config.yaml."
        )
    if code == 403:
        return (
            f"NewsAPI HTTP 403 on {endpoint_short}: forbidden. "
            f"Free-tier daily cap likely hit (100 req/day). Wait 24 h."
        )
    if code == 429:
        return f"NewsAPI HTTP 429 on {endpoint_short}: rate-limited. Retry."
    return f"NewsAPI HTTP {code} on {endpoint_short}: {reason}"


def _failed(
    tool: "NewsAPITool | None",
    note: str,
    *,
    source: str,
) -> ToolResult:
    """Shorthand for FAILED ToolResult. ``tool`` accepted for
    signature parity with the rest of the runtime; unused here."""
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
    "NewsAPITool",
    "DEFAULT_API_BASE",
    "DEFAULT_EVERYTHING_CACHE_TTL_S",
    "DEFAULT_TOP_HEADLINES_CACHE_TTL_S",
    "DEFAULT_SOURCES_CACHE_TTL_S",
    "DEFAULT_LIMIT",
    "DEFAULT_LIMIT_MAX",
    "DEFAULT_LOOKBACK_MAX_DAYS",
    "CATEGORY_VALUES",
]
