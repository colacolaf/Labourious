"""
tools/consensus.py — Sell-side analyst consensus via Finnhub.

Free-with-API-key. Same credentials as ``quotes_realtime``: sign up at
https://finnhub.io/ (free tier: 60 req/min, all endpoints below inclusive).

Three endpoints, three public methods on a single dataclass
(``runtime.tools.consensus.ConsensusTool``):

  1. ``recommendations(ticker)``
        ``GET /stock/recommendation?symbol=AAPL``
        Returns the last 4 months of analyst recommendation distributions.
        Each row: ``{period, strongBuy, buy, hold, sell, strongSell}``.
        This is the "consensus has been moving toward Buy for the last
        90 days" signal every Wharton memo cites.
  2. ``price_target(ticker)``
        ``GET /stock/price-target?symbol=AAPL``
        Returns ``{targetMean, targetHigh, targetLow, targetMedian,
        lastUpdated}`` — the sell-side 12-month price target.
        Default method of this tool because it's the single most-asked
        consensus question ("where does the street think it goes?").
  3. ``revenue_estimate(ticker, freq="quarterly", limit=8)``
        ``GET /stock/revenue-estimate?symbol=AAPL&freq=quarterly``
        Returns analyst revenue forecasts per period
        ``{period, revenueAvg, revenueLow, revenueHigh, revenueGrowth, numAnalysts}``.
        ``freq`` can be "quarterly" (default) or "annual".
        Limit clamped to 50.

All three endpoints return a list (recommendations, revenue_estimate)
or a single object (price_target). Strict shape validation: empty list
→ EMPTY ToolResult (no fabricated "$0.00"); bad ticker and out-of-
hours are treated identically — there's no quote number to fabricate.

Authentication: Finnhub's ?token=... query-string protocol, same as
``quotes_realtime``. Token is never echoed in ``ToolResult.note`` — we
redact ``?token=…`` before the URL hits the chip or the log.
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

DEFAULT_API_BASE = "https://finnhub.io/api/v1"
DEFAULT_USER_AGENT = "Labourious Analyst [email protected]"
DEFAULT_TIMEOUT_S = 15

# TTLs: recommendation distribution moves on broker upgrades/downgrades
# which settle weekly; price target can move intraday following earnings
# prints; revenue estimates settle quarterly when analysts update models.
DEFAULT_RECOMMENDATIONS_CACHE_TTL_S = 6 * 3600   # 6 h
DEFAULT_PRICE_TARGET_CACHE_TTL_S = 60 * 60       # 1 h
DEFAULT_REVENUE_ESTIMATE_CACHE_TTL_S = 6 * 3600 # 6 h

DEFAULT_LIMIT = 8                                # 2 years of quarters
DEFAULT_LIMIT_MAX = 50

# Endpoint paths.
_PATH_RECOMMENDATIONS = "/stock/recommendation"
_PATH_PRICE_TARGET = "/stock/price-target"
_PATH_REVENUE_ESTIMATE = "/stock/revenue-estimate"

FreqT = Literal["quarterly", "annual"]


# ------------------------------------------------------------------
# Tool
# ------------------------------------------------------------------


@dataclass
class ConsensusTool:
    """Finnhub-backed sell-side analyst consensus fetcher.

    Parameters
    ----------
    api_key : str | None
        Finnhub API key. ``__post_init__`` reads from
        ``FINNHUB_API_KEY`` then ``LABOURIOUS_FINNHUB_KEY``.
    api_base : str
        Override for tests. Production never changes this.
    user_agent : str
        Polite UA. Same string across all our providers.
    request_timeout_s : int
        Per-request timeout. 15 s is generous against Finnhub's p99.
    recommendations_cache_ttl_s : int
        Defaults to 6 h. Recommendation distribution moves weekly.
    price_target_cache_ttl_s : int
        Defaults to 1 h. Earnings prints can shift the target intraday.
    revenue_estimate_cache_ttl_s : int
        Defaults to 6 h. Estimates settle quarterly.
    opener : Any
        Override for tests; default ``urllib.request.urlopen``.
    """

    api_key: str | None = None
    api_base: str = DEFAULT_API_BASE
    user_agent: str = ""
    request_timeout_s: int = DEFAULT_TIMEOUT_S
    recommendations_cache_ttl_s: int = DEFAULT_RECOMMENDATIONS_CACHE_TTL_S
    price_target_cache_ttl_s: int = DEFAULT_PRICE_TARGET_CACHE_TTL_S
    revenue_estimate_cache_ttl_s: int = DEFAULT_REVENUE_ESTIMATE_CACHE_TTL_S
    opener: Any = field(default=None)
    _rec_cache: dict[str, tuple[float, ToolResult]] = field(default_factory=dict)
    _pt_cache: dict[str, tuple[float, ToolResult]] = field(default_factory=dict)
    _re_cache: dict[str, tuple[float, ToolResult]] = field(default_factory=dict)

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
    def recommendations(self, ticker: str) -> ToolResult:
        """Analyst recommendation distribution for the last 4 months.

        Returns a SUCCESS ``ToolResult`` with ``data`` shaped:

        ```
        {
          "rows": [
            {"period": "2024-12", "strongBuy": 12, "buy": 18,
             "hold": 8, "sell": 1, "strongSell": 0, "analyst_count": 39},
            ...
          ],
          "meta": {"ticker": "AAPL", "row_count": N, "as_of": "2025-08-19T17:59:55Z"}
        }
        ```

        Cached for ``recommendations_cache_ttl_s`` (default 6 h).
        Unknown ticker → EMPTY (the upstream returns ``[]``).
        """
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return _failed(self, "ticker must be a non-empty string",
                           source="finnhub_recommendation")

        cache_key = f"rec::{ticker}"
        cached = self._rec_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            miss_msg = _no_key_msg()
            return _failed(None, miss_msg, source="finnhub_recommendation")

        url = (
            f"{self.api_base}{_PATH_RECOMMENDATIONS}"
            f"?symbol={urllib.parse.quote(ticker)}"
            f"&token={urllib.parse.quote(self.api_key)}"
        )
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None,
                _http_note("recommendation", e.code, e.reason),
                source="finnhub_recommendation",
            )
        except urllib.error.URLError as e:
            return _failed(
                None, f"Finnhub network error on /stock/recommendation: {e.reason}",
                source="finnhub_recommendation",
            )
        except Exception as e:
            return _failed(
                None, f"Finnhub parse error on /stock/recommendation: "
                f"{type(e).__name__}: {e}",
                source="finnhub_recommendation",
            )

        if isinstance(payload, dict) and (
            "error" in payload or "Error" in payload
        ):
            return _failed(
                None, str(payload.get("error") or payload.get("Error")),
                source="finnhub_recommendation",
            )

        if not isinstance(payload, list):
            return _failed(
                None, f"Finnhub returned non-list payload on /stock/recommendation: "
                f"{type(payload).__name__}",
                source="finnhub_recommendation",
            )

        if not payload:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source="finnhub_recommendation",
                note=(
                    f"Finnhub /stock/recommendation for {ticker}: no rows "
                    "(unknown ticker or no analyst coverage)."
                ),
            )

        rows = [
            {
                "period":        str(r.get("period") or ""),
                "strongBuy":     int(r.get("strongBuy") or 0),
                "buy":           int(r.get("buy") or 0),
                "hold":          int(r.get("hold") or 0),
                "sell":          int(r.get("sell") or 0),
                "strongSell":    int(r.get("strongSell") or 0),
                "analyst_count": int(r.get("strongBuy") or 0)
                                + int(r.get("buy") or 0)
                                + int(r.get("hold") or 0)
                                + int(r.get("sell") or 0)
                                + int(r.get("strongSell") or 0),
            }
            for r in payload
        ]
        meta = {
            "ticker": ticker,
            "row_count": len(rows),
            "as_of": as_of,
        }
        result = ToolResult(
            status="SUCCESS",
            data={"rows": rows, "meta": meta},
            as_of=as_of,
            source="finnhub_recommendation",
            note=(
                f"Finnhub /stock/recommendation for {ticker}: "
                f"{len(rows)} periods of analyst counts "
                f"(latest period {rows[0]['period']}, "
                f"{rows[0]['analyst_count']} analysts). "
                f"URL: {_redact_token(url)}"
            ),
        )
        self._rec_cache_put(cache_key, result)
        return result

    def price_target(self, ticker: str) -> ToolResult:
        """Current sell-side consensus 12-month price target.

        Returns a SUCCESS ``ToolResult`` with ``data`` shaped:

        ```
        {
          "ticker": "AAPL",
          "target_mean":   230.50,
          "target_median": 225.00,
          "target_high":   300.00,
          "target_low":    180.00,
          "last_updated":  "2025-08-15",
          "as_of":         "2025-08-19T17:59:55Z",
          "url":           "https://finnhub.io/price-target?symbol=AAPL"
        }
        ```

        Cached for ``price_target_cache_ttl_s`` (default 1 h).
        """
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return _failed(self, "ticker must be a non-empty string",
                           source="finnhub_price_target")

        cache_key = f"pt::{ticker}"
        cached = self._pt_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            miss_msg = _no_key_msg()
            return _failed(None, miss_msg, source="finnhub_price_target")

        url = (
            f"{self.api_base}{_PATH_PRICE_TARGET}"
            f"?symbol={urllib.parse.quote(ticker)}"
            f"&token={urllib.parse.quote(self.api_key)}"
        )
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None,
                _http_note("price-target", e.code, e.reason),
                source="finnhub_price_target",
            )
        except urllib.error.URLError as e:
            return _failed(
                None, f"Finnhub network error on /stock/price-target: {e.reason}",
                source="finnhub_price_target",
            )
        except Exception as e:
            return _failed(
                None, f"Finnhub parse error on /stock/price-target: "
                f"{type(e).__name__}: {e}",
                source="finnhub_price_target",
            )

        if not isinstance(payload, dict):
            return _failed(
                None, f"Finnhub returned non-object payload on /stock/price-target: "
                f"{type(payload).__name__}",
                source="finnhub_price_target",
            )

        target_mean = payload.get("targetMean")
        target_high = payload.get("targetHigh")
        target_low = payload.get("targetLow")
        target_median = payload.get("targetMedian")
        last_updated = payload.get("lastUpdated")  # "YYYY-MM-DD" or ""

        # Strict validation: at minimum we need a numeric targetMean.
        # If the API returns a payload with no targets (unknown ticker),
        # the response is typically an empty dict or one with targetMean=0.
        try:
            target_mean_f = float(target_mean)
        except (TypeError, ValueError):
            return _failed(
                None, f"Finnhub returned no price target for {ticker} "
                f"(response: {payload!r}).",
                source="finnhub_price_target",
            )

        if target_mean_f <= 0:
            return _failed(
                None, f"Finnhub returned no coverage for {ticker} "
                f"(targetMean=0 implies no analyst coverage).",
                source="finnhub_price_target",
            )

        # Coerce optional numerics — they may be absent for thinly-covered
        # tickers.
        def _opt_float(v: Any) -> float | None:
            try:
                f = float(v)
                return f if f > 0 else None
            except (TypeError, ValueError):
                return None

        result = ToolResult(
            status="SUCCESS",
            data={
                "ticker": ticker,
                "target_mean":   target_mean_f,
                "target_median": _opt_float(target_median),
                "target_high":   _opt_float(target_high),
                "target_low":    _opt_float(target_low),
                "last_updated":  str(last_updated) if last_updated else None,
                "as_of":         as_of,
                "url":           f"https://finnhub.io/price-target?symbol={urllib.parse.quote(ticker)}",
            },
            as_of=as_of,
            source="finnhub_price_target",
            note=(
                f"Finnhub /stock/price-target for {ticker}: "
                f"${target_mean_f:.2f} (median="
                f"{_opt_float(target_median)}, high="
                f"{_opt_float(target_high)}, low="
                f"{_opt_float(target_low)}, last_updated="
                f"{last_updated or 'n/a'}). "
                f"URL: {_redact_token(url)}"
            ),
        )
        self._pt_cache_put(cache_key, result)
        return result

    def revenue_estimate(
        self,
        ticker: str,
        freq: str = "quarterly",
        limit: int = DEFAULT_LIMIT,
    ) -> ToolResult:
        """Analyst revenue estimates per period.

        Parameters
        ----------
        ticker : str
            Symbol, normalised to upper-case.
        freq : str
            ``"quarterly"`` (default) or ``"annual"``.
        limit : int
            Max rows returned (clamped to 50).

        Returns
        -------
        ToolResult
            ``status="SUCCESS"`` with rows
            ``{period, revenueAvg, revenueLow, revenueHigh,
            revenueGrowth, numAnalysts}`` keyed by ``period``.
        """
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return _failed(self, "ticker must be a non-empty string",
                           source="finnhub_revenue_estimate")

        canonical_freq = _canonicalize_freq(freq)
        if canonical_freq is None:
            return _failed(
                self,
                f"freq {freq!r} not supported "
                f"(use 'quarterly' or 'annual').",
                source="finnhub_revenue_estimate",
            )

        limit = max(1, min(int(limit), DEFAULT_LIMIT_MAX))

        cache_key = f"re::{ticker}::{canonical_freq}::{limit}"
        cached = self._re_cache_hit(cache_key)
        if cached is not None:
            return cached

        if not (self.api_key and self.api_key.strip()):
            miss_msg = _no_key_msg()
            return _failed(None, miss_msg, source="finnhub_revenue_estimate")

        url = (
            f"{self.api_base}{_PATH_REVENUE_ESTIMATE}"
            f"?symbol={urllib.parse.quote(ticker)}"
            f"&freq={canonical_freq}"
            f"&token={urllib.parse.quote(self.api_key)}"
        )
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed(
                None,
                _http_note("revenue-estimate", e.code, e.reason),
                source="finnhub_revenue_estimate",
            )
        except urllib.error.URLError as e:
            return _failed(
                None, f"Finnhub network error on /stock/revenue-estimate: {e.reason}",
                source="finnhub_revenue_estimate",
            )
        except Exception as e:
            return _failed(
                None, f"Finnhub parse error on /stock/revenue-estimate: "
                f"{type(e).__name__}: {e}",
                source="finnhub_revenue_estimate",
            )

        if isinstance(payload, dict) and (
            "error" in payload or "Error" in payload
        ):
            return _failed(
                None, str(payload.get("error") or payload.get("Error")),
                source="finnhub_revenue_estimate",
            )

        if not isinstance(payload, list):
            return _failed(
                None, f"Finnhub returned non-list payload on "
                f"/stock/revenue-estimate: {type(payload).__name__}",
                source="finnhub_revenue_estimate",
            )

        if not payload:
            return ToolResult(
                status="EMPTY",
                data=[],
                as_of=as_of,
                source="finnhub_revenue_estimate",
                note=(
                    f"Finnhub /stock/revenue-estimate for {ticker}: no rows "
                    f"(unknown ticker or no analyst coverage)."
                ),
            )

        rows_raw = payload[:limit]
        rows = []
        for r in rows_raw:
            period = r.get("period") or ""
            try:
                avg = float(r.get("revenueAvg") or 0)
            except (TypeError, ValueError):
                avg = 0.0
            try:
                low = float(r.get("revenueLow") or 0)
            except (TypeError, ValueError):
                low = 0.0
            try:
                high = float(r.get("revenueHigh") or 0)
            except (TypeError, ValueError):
                high = 0.0
            try:
                growth = r.get("revenueGrowth")
                growth = float(growth) if growth is not None else None
            except (TypeError, ValueError):
                growth = None
            try:
                num = r.get("numberAnalysts")
                num = int(num) if num is not None else None
            except (TypeError, ValueError):
                num = None

            rows.append({
                "period":          str(period),
                "revenue_avg":     avg,
                "revenue_low":     low,
                "revenue_high":    high,
                "revenue_growth":  growth,
                "num_analysts":    num,
            })

        meta = {
            "ticker": ticker,
            "freq": canonical_freq,
            "row_count": len(rows),
            "as_of": as_of,
        }

        result = ToolResult(
            status="SUCCESS",
            data={"rows": rows, "meta": meta},
            as_of=as_of,
            source="finnhub_revenue_estimate",
            note=(
                f"Finnhub /stock/revenue-estimate for {ticker}: "
                f"{len(rows)} {canonical_freq} periods (limit={limit}, "
                f"latest period {rows[0]['period']}, "
                f"{rows[0]['num_analysts'] or '?'} analysts). "
                f"URL: {_redact_token(url)}"
            ),
        )
        self._re_cache_put(cache_key, result)
        return result

    def clear_cache(self) -> None:
        """Drop all three caches. Useful for tests / ops."""
        self._rec_cache.clear()
        self._pt_cache.clear()
        self._re_cache.clear()

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

    # cache helpers — three independent TTLs so we never cross-pollute them
    def _rec_cache_hit(self, key: str) -> ToolResult | None:
        return _cache_hit(self._rec_cache, key, self.recommendations_cache_ttl_s)
    def _rec_cache_put(self, key: str, tr: ToolResult) -> None:
        _cache_put(self._rec_cache, key, tr)

    def _pt_cache_hit(self, key: str) -> ToolResult | None:
        return _cache_hit(self._pt_cache, key, self.price_target_cache_ttl_s)
    def _pt_cache_put(self, key: str, tr: ToolResult) -> None:
        _cache_put(self._pt_cache, key, tr)

    def _re_cache_hit(self, key: str) -> ToolResult | None:
        return _cache_hit(self._re_cache, key, self.revenue_estimate_cache_ttl_s)
    def _re_cache_put(self, key: str, tr: ToolResult) -> None:
        _cache_put(self._re_cache, key, tr)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _now_iso() -> str:
    """UTC wallclock as ISO-8601, second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonicalize_freq(freq: str) -> str | None:
    if not freq:
        return None
    s = freq.strip().lower()
    if s in (
        "quarterly", "quarter", "q", "q1", "q2", "q3", "q4",
        "3m", "3month",
    ):
        return "quarterly"
    if s in ("annual", "yearly", "year", "fy", "y"):
        return "annual"
    return None


def _no_key_msg() -> str:
    return (
        "FINNHUB_API_KEY not configured — set it in your shell or in "
        "~/.labourious/config.yaml to enable Finnhub consensus. "
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
    tool: "ConsensusTool | None",
    note: str,
    *,
    source: str = "finnhub_consensus",
) -> ToolResult:
    """Shorthand for FAILED ToolResult. ``tool`` is accepted positionally for
    signature parity with ``quotes_realtime._failed`` but is unused."""
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
    "ConsensusTool",
    "DEFAULT_API_BASE",
    "DEFAULT_RECOMMENDATIONS_CACHE_TTL_S",
    "DEFAULT_PRICE_TARGET_CACHE_TTL_S",
    "DEFAULT_REVENUE_ESTIMATE_CACHE_TTL_S",
    "DEFAULT_LIMIT",
    "DEFAULT_LIMIT_MAX",
]
