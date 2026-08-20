"""
tools/sentiment_social.py — Stocktwits sentiment stream.

Free-without-auth. Endpoints:
  - ``/api/2/streams/symbol/{TICKER}.json`` — per-symbol stream (≤30 msgs
    per page; we don't paginate, we just take what Stocktwits gives).
  - ``/api/2/trending/symbols/equities.json`` — top trending equities.

Why this connector ships: the agent pipeline has been thoroughly
skeptical-of-sentiment (see ``docs/USER-JOBS.md`` §"Social sentiment
scoring"). Yet the few signals that are real — bearish/bullish tags
self-applied by users — already live in the public Stocktwits stream.
This connector surfaces the *raw* row-level Bullish/Bearish/neutral
breakdown; the agent decides how much weight to give (it doesn't have
to use them at all).

Two public methods on ``SentimentSocialTool``:
  - ``messages(ticker, limit)`` — recent messages + bullish/bearish
    tally + average-watchlist-count (rough bumpiness proxy for retail
    reach).
  - ``trending(top_n)`` — top trending equities right now.

Auth: none required for read-only access. We send a polite UA — not
required, but it's the litmus test Stocktwits applies before considering
a bot a "respectful collaborator" rather than a scraper; behavioural
ripple on the TUI is small enough that we can opt-in.

Hygiene: same call_tool contract (ToolResult dataclass, ttl+key+redact,
defensive row casting, clear_cache).
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
from typing import Any


DEFAULT_API_BASE = "https://api.stocktwits.com/api/2"
DEFAULT_USER_AGENT = "Labourious Analyst [email protected]"
DEFAULT_TIMEOUT_S = 15

# Stocktwits data freshness: social chatter is *inherently* short-lived.
# 5-min cache lets a high-traffic ticker not hammer Stocktwits; we stay
# honest about the data being snapshot-at-read.
DEFAULT_MESSAGES_CACHE_TTL_S = 5 * 60
# Trending list moves every minute on the upstream side (their refresh).
DEFAULT_TRENDING_CACHE_TTL_S = 60

PATH_STREAMS_SYMBOL = "/streams/symbol/{ticker}.json"
PATH_TRENDING_EQUITIES = "/trending/symbols/equities.json"

# Stocktwits streams rate-limit is opaque-ish; their docs say "Please do
# not exceed 60 calls per minute on a single route". 60 r/m min means
# we sit well under it with our 5-minute cache.
MESSAGES_MAX = 30  # every page is 30
TRENDING_MAX = 30  # trending endpoint returns up to 30

VALID_SENTIMENTS = {"Bullish", "Bearish", None}  # None = untagged


# ------------------------------------------------------------------
# Tool
# ------------------------------------------------------------------


@dataclass
class SentimentSocialTool:
    """Stocktwits public stream & trending fetcher (no key).

    Parameters
    ----------
    api_base : str
        Override for tests.
    user_agent : str
        Polite UA. Stocktwits' behavioural firewall is happier with one.
    request_timeout_s : int
        Per-request timeout.
    messages_cache_ttl_s : int
        Default 5 min (Stocktwits chatter is short-lived).
    trending_cache_ttl_s : int
        Default 60 s (trending refreshes minute-by-minute).
    opener : Any
        Override for tests.
    """

    api_base: str = DEFAULT_API_BASE
    user_agent: str = ""
    request_timeout_s: int = DEFAULT_TIMEOUT_S
    messages_cache_ttl_s: int = DEFAULT_MESSAGES_CACHE_TTL_S
    trending_cache_ttl_s: int = DEFAULT_TRENDING_CACHE_TTL_S
    opener: Any = field(default=None)
    _msg_cache: dict[str, tuple[float, Any]] = field(default_factory=dict)
    _trend_cache: dict[str, tuple[float, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (self.user_agent and self.user_agent.strip()):
            self.user_agent = (
                os.environ.get("STOCKTWITS_USER_AGENT")
                or os.environ.get("LABOURIOUS_DEFAULT_USER_AGENT")
                or DEFAULT_USER_AGENT
            )
        if self.opener is None:
            self.opener = urllib.request.urlopen

    # ----------------------------------------------------------- public API
    def messages(self, ticker: str, limit: int = 30) -> Any:
        """Recent Stocktwits messages for ``ticker``.

        Returns a SUCCESS ``ToolResult`` with ``data`` shaped:

        ```
        {
          "ticker": "AAPL",
          "messages": [{"id": 1234567890,
                        "body": "$AAPL …",
                        "user": {"username": "...", "watchlist_count": 1234,
                                 "join_date": "..."},
                        "sentiment": "Bullish",  // or "Bearish" or null
                        "created_at": "ISO"},
                       …],
          "summary": {"total": N,
                      "bullish": X, "bearish": Y, "neutral": Z,
                      "bullish_pct": 0.X,
                      "total_watchlist_count": D,
                      "avg_watchlist_count_per_msg": E,
                      "earliest": "ISO",
                      "latest": "ISO"},
          "as_of": "ISO"
        }
        ```

        Stocktwits returns at most 30 messages per call; ``limit`` clamps
        that further. The upstream does not paginate — beyond ~30
        messages we're capturing the snapshot-of-now, not history.
        Cached ``messages_cache_ttl_s`` (default 5 min).
        """
        from . import ToolResult
        from .consensus import _failed

        ticker = (ticker or "").strip().upper().lstrip("$")  # "$AAPL" → "AAPL"
        if not ticker:
            return _failed(None, "ticker must be a non-empty string",
                           source="stocktwits_streams")

        if limit <= 0:
            return _failed(None,
                            f"limit must be ≥ 1 (got {limit!r})",
                            source="stocktwits_streams")
        if limit > MESSAGES_MAX:
            limit = MESSAGES_MAX  # Stocktwits hard cap

        cache_key = f"msg::{ticker}::{limit}"
        hit = _cache_hit(self._msg_cache, cache_key, self.messages_cache_ttl_s)
        if hit is not None:
            return hit

        url = (
            f"{self.api_base}"
            f"{PATH_STREAMS_SYMBOL.format(ticker=urllib.parse.quote(ticker))}"
        )
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None, _http_note("streams/symbol", e.code, e.reason),
                source="stocktwits_streams",
            )
        except urllib.error.URLError as e:
            return _failed(
                None,
                f"Stocktwits network error: {e.reason}",
                source="stocktwits_streams",
            )
        except Exception as e:
            return _failed(
                None,
                f"Stocktwits parse error: {type(e).__name__}: {e}",
                source="stocktwits_streams",
            )

        if not isinstance(payload, dict) or "messages" not in payload:
            return _failed(
                None,
                f"Stocktwits payload missing 'messages' key (got "
                f"{type(payload).__name__}).",
                source="stocktwits_streams",
            )

        raw_msgs = payload.get("messages") or []
        if not isinstance(raw_msgs, list):
            return _failed(
                None,
                f"Stocktwits 'messages' is not a list: "
                f"{type(raw_msgs).__name__}",
                source="stocktwits_streams",
            )

        msgs: list[dict[str, Any]] = []
        sentiment_count = {"Bullish": 0, "Bearish": 0, None: 0}
        watchlist_total = 0
        earliest = None
        latest = None
        for m in raw_msgs[:limit]:
            if not isinstance(m, dict):
                continue
            user = m.get("user") or {}
            if not isinstance(user, dict):
                user = {}
            entities = m.get("entities") or {}
            if not isinstance(entities, dict):
                entities = {}
            sent = entities.get("sentiment") or {}
            if not isinstance(sent, dict):
                sent = {}
            basic = sent.get("basic")
            if basic not in ("Bullish", "Bearish"):
                basic = None
            wl = _safe_int(user.get("watchlist_count")) or 0
            watchlist_total += wl
            created = str(m.get("created_at") or "")
            if created:
                if earliest is None or created < earliest:
                    earliest = created
                if latest is None or created > latest:
                    latest = created
            sentiment_count[basic] = sentiment_count.get(basic, 0) + 1
            msgs.append({
                "id": _safe_int(m.get("id")),
                "body": str(m.get("body") or ""),
                "user": {
                    "username": str(user.get("username") or ""),
                    "watchlist_count": wl,
                    "join_date": str(user.get("join_date") or ""),
                },
                "sentiment": basic,
                "created_at": created,
            })

        # Pull the symbol's overall watchlist count from upstream
        symbol_data = payload.get("symbol") or {}
        if not isinstance(symbol_data, dict):
            symbol_data = {}
        sym_watchlist = _safe_int(symbol_data.get("watchlist_count")) or 0

        total = len(msgs)
        if total == 0:
            return ToolResult(
                status="EMPTY",
                data={
                    "ticker": ticker,
                    "messages": [],
                    "symbol": {"watchlist_count": sym_watchlist},
                    "summary": {
                        "total": 0,
                        "bullish": 0, "bearish": 0, "neutral": 0,
                        "bullish_pct": None,
                        "total_watchlist_count": 0,
                        "avg_watchlist_count_per_msg": None,
                        "earliest": None,
                        "latest": None,
                    },
                    "as_of": as_of,
                    "url": url,
                },
                as_of=as_of,
                source="stocktwits_streams",
                note=(
                    f"Stocktwits /streams/symbol/{ticker}.json returned no "
                    f"messages in last 30 messages."
                ),
            )

        bullish = sentiment_count.get("Bullish", 0)
        bearish = sentiment_count.get("Bearish", 0)
        neutral = sentiment_count.get(None, 0)
        bull_pct = round(bullish / total, 4) if total else None
        avg_wl = round(watchlist_total / total, 2) if total else None

        summary = {
            "total": total,
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "bullish_pct": bull_pct,
            "total_watchlist_count": watchlist_total,
            "avg_watchlist_count_per_msg": avg_wl,
            "earliest": earliest,
            "latest": latest,
        }

        tr = ToolResult(
            status="SUCCESS",
            data={
                "ticker": ticker,
                "messages": msgs,
                "symbol": {"watchlist_count": sym_watchlist},
                "summary": summary,
                "as_of": as_of,
                "url": url,
            },
            as_of=as_of,
            source="stocktwits_streams",
            note=(
                f"Stocktwits /streams/symbol/{ticker}.json: {total} msgs — "
                f"bullish={bullish}, bearish={bearish}, neutral={neutral}, "
                f"bullish_pct={bull_pct}."
            ),
        )
        _cache_put(self._msg_cache, cache_key, tr)
        return tr

    def trending(self, top_n: int = 10) -> Any:
        """Top trending equities right now.

        Returns a SUCCESS ``ToolResult`` with ``data`` shaped:

        ```
        {
          "as_of": "ISO",
          "items": [{"symbol": "AAPL",
                     "user_count": 1234,  // users watching / in stream
                     "watchlist_count": 567890}, …],
          "top_count": N
        }
        ```

        ``top_n`` clamped to ``TRENDING_MAX`` (30). Cached
        ``trending_cache_ttl_s`` (default 60 s).
        """
        from . import ToolResult
        from .consensus import _failed

        if top_n <= 0:
            return _failed(None,
                            f"top_n must be ≥ 1 (got {top_n!r})",
                            source="stocktwits_trending")
        if top_n > TRENDING_MAX:
            top_n = TRENDING_MAX

        cache_key = f"trend::{top_n}"
        hit = _cache_hit(self._trend_cache, cache_key, self.trending_cache_ttl_s)
        if hit is not None:
            return hit

        url = f"{self.api_base}{PATH_TRENDING_EQUITIES}"
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None, _http_note("trending/equities", e.code, e.reason),
                source="stocktwits_trending",
            )
        except urllib.error.URLError as e:
            return _failed(
                None,
                f"Stocktwits network error: {e.reason}",
                source="stocktwits_trending",
            )
        except Exception as e:
            return _failed(
                None,
                f"Stocktwits parse error: {type(e).__name__}: {e}",
                source="stocktwits_trending",
            )

        if not isinstance(payload, dict) or "symbols" not in payload:
            return _failed(
                None,
                f"Stocktwits payload missing 'symbols' key (got "
                f"{type(payload).__name__}).",
                source="stocktwits_trending",
            )

        raw_items = payload.get("symbols") or []
        if not isinstance(raw_items, list):
            return _failed(
                None,
                f"Stocktwits 'symbols' is not a list: "
                f"{type(raw_items).__name__}",
                source="stocktwits_trending",
            )

        items: list[dict[str, Any]] = []
        for it in raw_items[:top_n]:
            if not isinstance(it, dict):
                continue
            items.append({
                "symbol": str(it.get("symbol") or "").upper(),
                "user_count": _safe_int(it.get("user_count")),
                "watchlist_count": _safe_int(it.get("watchlist_count")),
            })

        if not items:
            return ToolResult(
                status="EMPTY",
                data={"as_of": as_of, "items": [], "top_count": 0,
                      "url": url},
                as_of=as_of,
                source="stocktwits_trending",
                note="Stocktwits /trending/symbols/equities.json returned "
                     "no items after defensive parsing.",
            )

        tr = ToolResult(
            status="SUCCESS",
            data={
                "as_of": as_of,
                "items": items,
                "top_count": len(items),
                "url": url,
            },
            as_of=as_of,
            source="stocktwits_trending",
            note=(
                f"Stocktwits /trending/symbols/equities.json: {len(items)} "
                f"trending equities."
            ),
        )
        _cache_put(self._trend_cache, cache_key, tr)
        return tr

    def clear_cache(self) -> None:
        """Drop both caches."""
        self._msg_cache.clear()
        self._trend_cache.clear()

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


def _safe_int(x: Any) -> int | None:
    if x is None:
        return None
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def _http_note(endpoint_short: str, code: int | None, reason: Any) -> str:
    code = code or 0
    if code == 401:
        return (
            f"Stocktwits HTTP 401 on /{endpoint_short}: "
            f"{reason}. (Stocktwits streams are nominally public; in "
            f"practice a UA-less request sometimes 401s. We always send one.)"
        )
    if code == 403:
        return (
            f"Stocktwits HTTP 403 on /{endpoint_short}: forbidden — "
            "may be hitting rate limit (≤60 r/m). Wait and retry."
        )
    if code == 429:
        return f"Stocktwits HTTP 429 on /{endpoint_short}: rate-limited. Retry."
    return f"Stocktwits HTTP {code} on /{endpoint_short}: {reason}"


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
    "SentimentSocialTool",
    "DEFAULT_API_BASE",
    "DEFAULT_MESSAGES_CACHE_TTL_S",
    "DEFAULT_TRENDING_CACHE_TTL_S",
    "MESSAGES_MAX",
    "TRENDING_MAX",
]
