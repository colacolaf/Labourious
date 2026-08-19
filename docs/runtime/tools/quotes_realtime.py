"""
tools/quotes_realtime.py — Realtime US equity quotes via Finnhub.

Free with API key. Sign up at https://finnhub.io/ (free tier: 60 req/min).
Auth: ``?token=...`` query string. We never log the token. The key is read
from ``FINNHUB_API_KEY`` first, then ``LABOURIOUS_FINNHUB_KEY`` as a
fallback, then ``self.api_key`` if the caller passed one in (used by
tests/pilots that mock the auth header).

Why this connector exists: yfinance is good for daily/weekly OHLCV but
its intraday and pre-market coverage is rate-limited / spotty on
free-deploy environments. Finnhub's free tier covers tickers globally
with sub-second latency on the ``/quote`` endpoint and D / 60 / 30 / 15 / 5 / 1
minute candles on ``/stock/candle``. We treat the two as complementary:
yfinance is the default for daily backtests; Finnhub anchors the
realtime-display path and intraday validation.

Single dataclass — ``runtime.tools.quotes_realtime.QuotesRealtimeTool``.
Two public entry points:
  - ``quote(ticker)``
        Single ticker snapshot (current/high/low/open/prev_close + ts).
        Cached 60 s (Finnhub's free-tier rate limit + 1 poll minimum).
  - ``candles(ticker, resolution="D", days_back=365, limit=1000)``
        OHLCV candles. ``resolution`` maps ``1d``→``D``, ``1h``→``60``,
        ``30m``→``30``, ``15m``→``15``, ``5m``→``5``, ``1m``→``1``.
        Returns a list of dicts ``{t, o, h, l, c, v}`` plus a
        ``meta`` block ({``resolution``, ``from_ts``, ``to_ts``, ``status``}).

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
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from . import ToolResult


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

DEFAULT_API_BASE = "https://finnhub.io/api/v1"
DEFAULT_USER_AGENT = "Labourious Analyst [email protected]"
DEFAULT_TIMEOUT_S = 15
DEFAULT_QUOTE_CACHE_TTL_S = 60            # Free-tier: 60 req/min, 1 s margin
DEFAULT_CANDLE_CACHE_TTL_S = 300          # Daily bars don't change intraday

# Resolution map: short alias → Finnhub's resolution code.
_RESOLUTION_ALIASES: dict[str, str] = {
    "1d": "D",
    "d":  "D",
    "day":"D",
    "1h": "60",
    "h":  "60",
    "hour": "60",
    "60m":"60",
    "30m":"30",
    "30": "30",
    "15m":"15",
    "15": "15",
    "5m": "5",
    "5":  "5",
    "1m": "1",
    "1":  "1",
}

ResolutionT = Literal["1", "5", "15", "30", "60", "D"]


# ------------------------------------------------------------------
# Tool
# ------------------------------------------------------------------


@dataclass
class QuotesRealtimeTool:
    """Finnhub-backed realtime quote + candle fetcher.

    Parameters
    ----------
    api_key : str | None
        Finnhub API key. If omitted, ``__post_init__`` reads from
        ``FINNHUB_API_KEY`` then ``LABOURIOUS_FINNHUB_KEY``.
    api_base : str
        Override for tests. Production never changes this.
    user_agent : str
        Polite UA. SEC also wants one; we use the same string so
        one identity across providers.
    request_timeout_s : int
        Per-request timeout. Free tier is fast; 15 s is generous.
    quote_cache_ttl_s : int
        Quote snapshots are cheap but bounded; default 60 s leaves
        1 s of slack against the 60 req/min rate limit.
    candle_cache_ttl_s : int
        Daily bars don't move once the day closes; default 300 s.
    opener : Any
        Override for tests; default ``urllib.request.urlopen``.
    """

    api_key: str | None = None
    api_base: str = DEFAULT_API_BASE
    user_agent: str = ""
    request_timeout_s: int = DEFAULT_TIMEOUT_S
    quote_cache_ttl_s: int = DEFAULT_QUOTE_CACHE_TTL_S
    candle_cache_ttl_s: int = DEFAULT_CANDLE_CACHE_TTL_S
    opener: Any = field(default=None)
    _quote_cache: dict[str, tuple[float, ToolResult]] = field(default_factory=dict)
    _candle_cache: dict[str, tuple[float, ToolResult]] = field(default_factory=dict)

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
    def quote(self, ticker: str) -> ToolResult:
        """Single ticker snapshot via ``GET /quote``.

        Returns a SUCCESS ``ToolResult`` with ``data`` shaped:

        ```
        {
          "ticker": "AAPL",
          "current": 192.34,
          "high": 193.10,
          "low":  190.50,
          "open": 191.20,
          "prev_close": 191.05,
          "change":  1.29,            # current - prev_close
          "change_pct": 0.675,        # (change / prev_close) * 100, %
          "as_of_unix": 1692451200,
          "as_of": "2025-08-19T16:00:00Z",
          "url": "https://finnhub.io/quote?symbol=AAPL"
        }
        ```

        Cached `quote_cache_ttl_s`. No key → FAILED with a clear
        "FINNHUB_API_KEY not configured" note (no silent fallback).
        """
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return _failed(self, "ticker must be a non-empty string", source="finnhub_quote")

        cache_key = f"quote::{ticker}"
        cached = self._quote_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            return _failed(
                self,
                "FINNHUB_API_KEY not configured — set it in your shell or in "
                "~/.labourious/config.yaml to enable Finnhub realtime quotes. "
                "Sign up free at https://finnhub.io/.",
                source="finnhub_quote",
            )

        url = (
            f"{self.api_base}/quote?symbol={urllib.parse.quote(ticker)}"
            f"&token={urllib.parse.quote(self.api_key)}"
        )
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                self,
                f"Finnhub HTTP {e.code} on /quote: {e.reason}",
                source="finnhub_quote", status_code=e.code,
            )
        except urllib.error.URLError as e:
            return _failed(
                self,
                f"Finnhub network error on /quote: {e.reason}",
                source="finnhub_quote",
            )
        except Exception as e:
            return _failed(
                self,
                f"Finnhub parse error on /quote: {type(e).__name__}: {e}",
                source="finnhub_quote",
            )

        # Validate shape. Finnhub returns c=0 when the symbol is invalid;
        # we treat that as FAILED so we don't fabricate "current=0.00".
        current = payload.get("c")
        high = payload.get("h")
        low = payload.get("l")
        opn = payload.get("o")
        prev_close = payload.get("pc")
        ts_unix = payload.get("t")
        if (
            current is None
            or high is None
            or low is None
            or opn is None
            or prev_close is None
            or float(current or 0) <= 0
            or float(prev_close or 0) <= 0
        ):
            return _failed(
                self,
                f"Finnhub returned no live quote for {ticker} "
                "(response outside market hours or unknown symbol).",
                source="finnhub_quote",
            )

        change = float(current) - float(prev_close)
        change_pct = (change / float(prev_close)) * 100.0
        iso_ts = (
            datetime.fromtimestamp(int(ts_unix), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if ts_unix else as_of
        )

        result = ToolResult(
            status="SUCCESS",
            data={
                "ticker": ticker,
                "current": float(current),
                "high": float(high),
                "low": float(low),
                "open": float(opn),
                "prev_close": float(prev_close),
                "change": round(change, 4),
                "change_pct": round(change_pct, 4),
                "as_of_unix": int(ts_unix) if ts_unix else None,
                "as_of": iso_ts,
                "url": f"https://finnhub.io/quote?symbol={urllib.parse.quote(ticker)}",
            },
            as_of=as_of,
            source="finnhub_quote",
            note=(
                f"Finnhub /quote for {ticker}: ${float(current):.2f} "
                f"({change:+.2f}, {change_pct:+.2f}%) as of {iso_ts}. "
                f"URL: {url.split('&token=')[0]}&token=REDACTED"
            ),
        )
        self._quote_cache_put(cache_key, result)
        return result

    def candles(
        self,
        ticker: str,
        resolution: str = "D",
        days_back: int = 365,
        limit: int = 1000,
    ) -> ToolResult:
        """OHLCV candles via ``GET /stock/candle``.

        Parameters
        ----------
        ticker : str
            Symbol, normalised to upper-case.
        resolution : str
            One of ``"1"`` (1m) · ``"5"`` (5m) · ``"15"`` (15m) ·
            ``"30"`` (30m) · ``"60"`` (1h) · ``"D"`` (1d). Short
            aliases accepted (``"1d"``→``"D"``, ``"1h"``→``"60"``).
        days_back : int
            Lookback window in calendar days. Translated to a
            ``from``/``to`` unix pair around ``now_utc``.
        limit : int
            Hard ceiling on returned rows (FCE ~ FMP).

        Returns
        -------
        ToolResult
            ``status="SUCCESS"`` with rows keyed by unix timestamp.
        """
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return _failed(self, "ticker must be a non-empty string", source="finnhub_candle")

        canonical_res = _canonicalize_resolution(resolution)
        if canonical_res is None:
            return _failed(
                self,
                f"resolution {resolution!r} not supported "
                f"(use one of: {sorted(_RESOLUTION_ALIASES.values())}).",
                source="finnhub_candle",
            )

        days_back = max(1, min(int(days_back), 365 * 25))   # 25 y ceiling
        limit = max(1, min(int(limit), 5000))

        cache_key = f"candle::{ticker}::{canonical_res}::{days_back}::{limit}"
        cached = self._candle_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            return _failed(
                self,
                "FINNHUB_API_KEY not configured — set it in your shell or in "
                "~/.labourious/config.yaml to enable Finnhub candles.",
                source="finnhub_candle",
            )

        to_dt = datetime.now(timezone.utc)
        from_dt = to_dt - timedelta(days=days_back)
        from_unix = int(from_dt.timestamp())
        to_unix = int(to_dt.timestamp())

        qs = {
            "symbol": ticker,
            "resolution": canonical_res,
            "from": from_unix,
            "to": to_unix,
            "token": self.api_key,
        }
        url = f"{self.api_base}/stock/candle?{urllib.parse.urlencode(qs)}"
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                self,
                f"Finnhub HTTP {e.code} on /stock/candle: {e.reason}",
                source="finnhub_candle", status_code=e.code,
            )
        except urllib.error.URLError as e:
            return _failed(
                self,
                f"Finnhub network error on /stock/candle: {e.reason}",
                source="finnhub_candle",
            )
        except Exception as e:
            return _failed(
                self,
                f"Finnhub parse error on /stock/candle: {type(e).__name__}: {e}",
                source="finnhub_candle",
            )

        status = payload.get("s") or ""
        ts_list = payload.get("t") or []
        opn_list = payload.get("o") or []
        hi_list = payload.get("h") or []
        lo_list = payload.get("l") or []
        cl_list = payload.get("c") or []
        vol_list = payload.get("v") or []

        if status != "ok" or not ts_list:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source="finnhub_candle",
                note=(
                    f"Finnhub returned no candles for {ticker} "
                    f"(resolution={canonical_res}, "
                    f"{from_dt.date()}→{to_dt.date()}). "
                    f"status='{status}'."
                ),
            )

        rows: list[dict[str, Any]] = []
        for i, ts in enumerate(ts_list):
            try:
                _iso = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except (ValueError, OSError):
                _iso = ""
            rows.append({
                "t": int(ts),
                "ts_iso": _iso,
                "o": float(opn_list[i]) if i < len(opn_list) else None,
                "h": float(hi_list[i]) if i < len(hi_list) else None,
                "l": float(lo_list[i]) if i < len(lo_list) else None,
                "c": float(cl_list[i]) if i < len(cl_list) else None,
                "v": int(vol_list[i]) if i < len(vol_list) and vol_list[i] is not None else None,
            })
        rows = rows[:limit]

        meta = {
            "resolution": canonical_res,
            "from_ts": from_unix,
            "to_ts": to_unix,
            "from_iso": from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to_iso": to_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": status,
            "row_count": len(rows),
        }

        result = ToolResult(
            status="SUCCESS",
            data={"rows": rows, "meta": meta},
            as_of=as_of,
            source="finnhub_candle",
            note=(
                f"Finnhub /stock/candle for {ticker}: {len(rows)} candles "
                f"@ resolution {canonical_res} "
                f"({meta['from_iso']} → {meta['to_iso']}). "
                f"URL: {url.split('&token=')[0]}&token=REDACTED"
            ),
        )
        self._candle_cache_put(cache_key, result)
        return result

    def clear_cache(self) -> None:
        """Drop both caches. Useful for tests / ops."""
        self._quote_cache.clear()
        self._candle_cache.clear()

    # ----------------------------------------------------------- internal
    def _fetch_json(self, url: str) -> dict[str, Any]:
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
        # Finnhub gzips some responses; ``Accept-Encoding`` was sent,
        # urllib's urlopen decompresses transparently — so raw is plain text.
        if isinstance(raw, bytes):
            try:
                return json.loads(raw.decode("utf-8"))
            except UnicodeDecodeError:
                return json.loads(raw.decode("latin-1"))
        return json.loads(raw)

    def _quote_cache_hit(self, key: str) -> ToolResult | None:
        stamped = self._quote_cache.get(key)
        if not stamped:
            return None
        ts, tr = stamped
        if (time.time() - ts) > self.quote_cache_ttl_s:
            self._quote_cache.pop(key, None)
            return None
        return tr

    def _quote_cache_put(self, key: str, tr: ToolResult) -> None:
        self._quote_cache[key] = (time.time(), tr)

    def _candle_cache_hit(self, key: str) -> ToolResult | None:
        stamped = self._candle_cache.get(key)
        if not stamped:
            return None
        ts, tr = stamped
        if (time.time() - ts) > self.candle_cache_ttl_s:
            self._candle_cache.pop(key, None)
            return None
        return tr

    def _candle_cache_put(self, key: str, tr: ToolResult) -> None:
        self._candle_cache[key] = (time.time(), tr)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _now_iso() -> str:
    """UTC wallclock as ISO-8601, second precision (Finnhub-friendly)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonicalize_resolution(res: str) -> str | None:
    """Return Finnhub's canonical resolution code or None for unknown."""
    if not res:
        return None
    s = res.strip().lower()
    if s in _RESOLUTION_ALIASES:
        return _RESOLUTION_ALIASES[s]
    if s in _RESOLUTION_ALIASES.values():
        return s
    return None


def _failed(
    tool: "QuotesRealtimeTool",
    note: str,
    *,
    source: str = "finnhub_quote",
    status_code: int | None = None,
) -> ToolResult:
    """Shorthand for FAILED ToolResult with a Finnhub-shaped source."""
    return ToolResult(
        status="FAILED", data=None,
        as_of=_now_iso(),
        source=source,
        note=note,
    )


__all__ = [
    "QuotesRealtimeTool",
    "DEFAULT_API_BASE",
    "DEFAULT_QUOTE_CACHE_TTL_S",
    "DEFAULT_CANDLE_CACHE_TTL_S",
]
