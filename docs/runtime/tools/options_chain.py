"""
tools/options_chain.py — Finnhub options chain & expirations.

Free, single-source, single-key. Both endpoints reuse ``FINNHUB_API_KEY``:
  - ``/stock/option-chain?symbol=…&date=YYYY-MM-DD``  — full chain for one expiry
  - ``/stock/option-expiry-dates?symbol=…``         — list of available expiries

Why this connector ships: the options-strategy flow (f7, on deck) and the
risk-rubric axis of the Comparator both need the raw option-chain surface
(strike × side × OI × greeks). Without options data, the agent pipeline can
only derive "implied volatility is high" as a vibes-conclusion from news
language; with the chain, the LLM gets exact greeks + OI per strike.

Two public methods on ``OptionsChainTool``:
  - ``expirations(ticker)``           — list of available ``YYYY-MM-DD`` dates.
                                       Cached 24 h (expiries settle weekly).
  - ``chain(ticker, expiration)``    — full chain rows + summaries.
                                       Cached 15 min (greeks move with
                                       the underlying).

Hygiene: same call_tool contract as ``consensus.py`` (SUCCESS/EMPTY/FAILED,
ttl+key+redact, ToolResult dataclass, ``clear_cache``).
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


DEFAULT_API_BASE = "https://finnhub.io/api/v1"
DEFAULT_USER_AGENT = "Labourious Analyst [email protected]"
DEFAULT_TIMEOUT_S = 15

# Expirations are set by the exchange, change weekly; quote movers only on
# ~Friday afternoon. 24 h lets us dodge getting noticed without going stale
# on a Monday morning.
DEFAULT_EXPIRATIONS_CACHE_TTL_S = 24 * 3600
# Chains move with the underlying across the session. 15 min is just enough
# granularity to ride a price swing without rounding.
DEFAULT_CHAIN_CACHE_TTL_S = 15 * 60

_PATH_OPTION_CHAIN = "/stock/option-chain"
_PATH_OPTION_EXPIRIES = "/stock/option-expiry-dates"

# Defensive clamps on inputs the runtime tends to abuse.
EXPIRATIONS_MAX = 60
CHAIN_ROW_HARD_CAP = 5000

# Common natural-language aliases → YYYY-MM-DD canonical. We accept strings
# ("2024-01-19"), explicit dates ("January 19, 2024", omitted), but reject a
# iffy "next friday" because calendar math belongs upstream.
EXPECTED_FIELDS_CHAIN = (
    "strikePrice", "side", "symbol", "expiryDate",
    "openInterest", "volume", "lastPrice", "bidPrice", "askPrice",
    "impliedVolatility", "delta", "gamma", "theta", "vega", "rho",
)


# ------------------------------------------------------------------
# Tool
# ------------------------------------------------------------------


@dataclass
class OptionsChainTool:
    """Finnhub-backed options chain & expirations fetcher.

    Parameters
    ----------
    api_key : str | None
        Finnhub API key. ``__post_init__`` reads ``FINNHUB_API_KEY`` then
        ``LABOURIOUS_FINNHUB_KEY``.
    api_base : str
        Override for tests. Production never changes this.
    user_agent : str
        Polite UA.
    request_timeout_s : int
        Per-request timeout.
    expirations_cache_ttl_s : int
        Cache TTL for ``/stock/option-expiry-dates``. Defaults to 24 h.
    chain_cache_ttl_s : int
        Cache TTL for ``/stock/option-chain``. Defaults to 15 min.
    opener : Any
        Override for tests; default ``urllib.request.urlopen``.
    """

    api_key: str | None = None
    api_base: str = DEFAULT_API_BASE
    user_agent: str = ""
    request_timeout_s: int = DEFAULT_TIMEOUT_S
    expirations_cache_ttl_s: int = DEFAULT_EXPIRATIONS_CACHE_TTL_S
    chain_cache_ttl_s: int = DEFAULT_CHAIN_CACHE_TTL_S
    opener: Any = field(default=None)
    _exp_cache: dict[str, tuple[float, Any]] = field(default_factory=dict)
    _chain_cache: dict[str, tuple[float, Any]] = field(default_factory=dict)

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
    def expirations(self, ticker: str) -> Any:
        """List available option expiration dates for ``ticker``.

        Returns a SUCCESS ``ToolResult`` with ``data`` shaped:

        ```
        {
          "ticker": "AAPL",
          "expirations": ["2024-01-19", "2024-01-26", ..., "2026-12-18"],
          "exp_count": N,
          "as_of": "ISO"
        }
        ```

        Cached ``expirations_cache_ttl_s`` (default 24 h).
        """
        from . import ToolResult  # late import keeps the module importlib-clean

        ticker = (ticker or "").strip().upper()
        if not ticker:
            from .consensus import _failed  # reuse helper
            return _failed(None, "ticker must be a non-empty string",
                            source="finnhub_expirations")

        cache_key = f"exp::{ticker}"
        hit = _cache_hit(self._exp_cache, cache_key, self.expirations_cache_ttl_s)
        if hit is not None:
            return hit

        if not (self.api_key and self.api_key.strip()):
            return _failed_from(None, _no_key_msg(),
                                source="finnhub_expirations")

        url = (
            f"{self.api_base}{_PATH_OPTION_EXPIRIES}"
            f"?symbol={urllib.parse.quote(ticker)}"
            f"&token={urllib.parse.quote(self.api_key)}"
        )
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed_from(
                None, _http_note("option-expiry-dates", e.code, e.reason),
                source="finnhub_expirations",
            )
        except urllib.error.URLError as e:
            return _failed_from(
                None, f"Finnhub network error on /stock/option-expiry-dates: {e.reason}",
                source="finnhub_expirations",
            )
        except Exception as e:
            return _failed_from(
                None,
                f"Finnhub parse error on /stock/option-expiry-dates: "
                f"{type(e).__name__}: {e}",
                source="finnhub_expirations",
            )

        if isinstance(payload, dict) and ("error" in payload or "Error" in payload):
            return _failed_from(
                None, str(payload.get("error") or payload.get("Error")),
                source="finnhub_expirations",
            )
        if not isinstance(payload, list):
            return _failed_from(
                None,
                f"Finnhub returned non-list payload on /stock/option-expiry-dates: "
                f"{type(payload).__name__}",
                source="finnhub_expirations",
            )

        # Defensive row casting — Finnhub sends str dates; keep the ones that
        # parse as YYYY-MM-DD, drop rest. We do NOT raise on a partial cleanup.
        rows = []
        for x in payload[:EXPIRATIONS_MAX]:
            if isinstance(x, str) and len(x) == 10 and x[4] == "-" and x[7] == "-":
                rows.append(x)
        if not rows:
            return ToolResult(
                status="EMPTY",
                data={"ticker": ticker, "expirations": [], "exp_count": 0,
                      "as_of": as_of, "url": _redact_token(url)},
                as_of=as_of,
                source="finnhub_expirations",
                note=(
                    f"Finnhub /stock/option-expiry-dates for {ticker}: no "
                    f"YYYY-MM-DD entries."
                ),
            )

        tr = ToolResult(
            status="SUCCESS",
            data={
                "ticker": ticker,
                "expirations": sorted(rows),
                "exp_count": len(rows),
                "as_of": as_of,
                "url": _redact_token(url),
            },
            as_of=as_of,
            source="finnhub_expirations",
            note=(
                f"Finnhub /stock/option-expiry-dates for {ticker}: {len(rows)} "
                f"expirations. URL: {_redact_token(url)}"
            ),
        )
        _cache_put(self._exp_cache, cache_key, tr)
        return tr

    def chain(self, ticker: str, expiration: str) -> Any:
        """Full options chain for ``ticker`` at one ``expiration``.

        Returns a SUCCESS ``ToolResult`` with ``data`` shaped:

        ```
        {
          "ticker": "AAPL",
          "expiration": "2024-01-19",
          "rows": [{"strike": 100.0, "side": "call",
                    "open_interest": 1234, "volume": 567,
                    "last": 5.6, "bid": 5.5, "ask": 5.7,
                    "implied_volatility": 0.32,
                    "delta": 0.45, "gamma": 0.02,
                    "theta": -0.05, "vega": 0.18, "rho": 0.01,
                    "occ_symbol": "O:AAPL240119C00100000"},
                   ...],
          "summary": {"calls": N, "puts": M, "strikes": K,
                      "calls_oi": ...,
                      "puts_oi": ...,
                      "put_call_oi_ratio": ...,
                      "max_oi_call_strike": ...,
                      "max_oi_put_strike": ...,
                      "iv_mean_call": ...,
                      "iv_mean_put": ...},
          "row_count": R,
          "as_of": "ISO"
        }
        ```

        Cached ``chain_cache_ttl_s`` (default 15 min).
        """
        from . import ToolResult
        from .consensus import _failed

        ticker = (ticker or "").strip().upper()
        expiration = (expiration or "").strip()
        if not ticker:
            return _failed(None, "ticker must be a non-empty string",
                           source="finnhub_option_chain")
        if not _is_expiration(expiration):
            return _failed(
                None,
                f"expiration must be YYYY-MM-DD (got {expiration!r})",
                source="finnhub_option_chain",
            )

        cache_key = f"chain::{ticker}::{expiration}"
        hit = _cache_hit(self._chain_cache, cache_key, self.chain_cache_ttl_s)
        if hit is not None:
            return hit

        if not (self.api_key and self.api_key.strip()):
            return _failed_from(None, _no_key_msg(),
                                source="finnhub_option_chain")

        url = (
            f"{self.api_base}{_PATH_OPTION_CHAIN}"
            f"?symbol={urllib.parse.quote(ticker)}"
            f"&date={urllib.parse.quote(expiration)}"
            f"&token={urllib.parse.quote(self.api_key)}"
        )
        as_of = _now_iso()
        try:
            payload = self._fetch_json(url)
        except urllib.error.HTTPError as e:
            return _failed_from(
                None, _http_note("option-chain", e.code, e.reason),
                source="finnhub_option_chain",
            )
        except urllib.error.URLError as e:
            return _failed_from(
                None,
                f"Finnhub network error on /stock/option-chain: {e.reason}",
                source="finnhub_option_chain",
            )
        except Exception as e:
            return _failed_from(
                None,
                f"Finnhub parse error on /stock/option-chain: "
                f"{type(e).__name__}: {e}",
                source="finnhub_option_chain",
            )

        if isinstance(payload, dict) and ("error" in payload or "Error" in payload):
            return _failed_from(
                None, str(payload.get("error") or payload.get("Error")),
                source="finnhub_option_chain",
            )
        if not isinstance(payload, dict) or "data" not in payload:
            return _failed_from(
                None,
                f"Finnhub payload for /stock/option-chain missing 'data' "
                f"key (got {type(payload).__name__}).",
                source="finnhub_option_chain",
            )

        raw_rows = payload.get("data") or []
        if not isinstance(raw_rows, list):
            return _failed_from(
                None,
                f"Finnhub /stock/option-chain 'data' is not a list: "
                f"{type(raw_rows).__name__}",
                source="finnhub_option_chain",
            )

        rows: list[dict[str, Any]] = []
        for r in raw_rows[:CHAIN_ROW_HARD_CAP]:
            if not isinstance(r, dict):
                continue
            side_raw = (r.get("side") or "").lower()
            if side_raw not in ("call", "put"):
                continue
            try:
                strike = float(r.get("strikePrice") or 0)
            except (TypeError, ValueError):
                strike = 0.0
            rows.append({
                "strike": strike,
                "side": side_raw,
                "occ_symbol": r.get("symbol") or "",
                "expiry": r.get("expiryDate") or expiration,
                "open_interest": _safe_int(r.get("openInterest")),
                "volume": _safe_int(r.get("volume")),
                "last": _safe_float(r.get("lastPrice")),
                "bid": _safe_float(r.get("bidPrice")),
                "ask": _safe_float(r.get("askPrice")),
                "implied_volatility": _safe_float(r.get("impliedVolatility")),
                "delta": _safe_float(r.get("delta")),
                "gamma": _safe_float(r.get("gamma")),
                "theta": _safe_float(r.get("theta")),
                "vega": _safe_float(r.get("vega")),
                "rho": _safe_float(r.get("rho")),
            })

        if not rows:
            return ToolResult(
                status="EMPTY",
                data={
                    "ticker": ticker,
                    "expiration": expiration,
                    "rows": [],
                    "summary": {},
                    "row_count": 0,
                    "as_of": as_of,
                    "url": _redact_token(url),
                },
                as_of=as_of,
                source="finnhub_option_chain",
                note=(
                    f"Finnhub /stock/option-chain for {ticker} {expiration}: "
                    f"no call/put rows after defensive parsing."
                ),
            )

        summary = _summarize_chain(rows)
        tr = ToolResult(
            status="SUCCESS",
            data={
                "ticker": ticker,
                "expiration": expiration,
                "rows": rows,
                "summary": summary,
                "row_count": len(rows),
                "as_of": as_of,
                "url": _redact_token(url),
            },
            as_of=as_of,
            source="finnhub_option_chain",
            note=(
                f"Finnhub /stock/option-chain for {ticker} {expiration}: "
                f"{len(rows)} rows ({summary['calls']} calls, "
                f"{summary['puts']} puts, "
                f"put_call_oi_ratio={summary['put_call_oi_ratio']}). "
                f"URL: {_redact_token(url)}"
            ),
        )
        _cache_put(self._chain_cache, cache_key, tr)
        return tr

    def clear_cache(self) -> None:
        """Drop both caches."""
        self._exp_cache.clear()
        self._chain_cache.clear()

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
    """UTC wallclock as ISO-8601, second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_expiration(x: str) -> bool:
    """YYYY-MM-DD only. Anything else is FAILED."""
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


def _summarize_chain(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate OI / IV / strike counts. Pure function, easy to pilot."""
    calls, puts = [], []
    for r in rows:
        if r["side"] == "call":
            calls.append(r)
        else:
            puts.append(r)

    def oi(grp): return sum((r["open_interest"] or 0) for r in grp)
    def iv_mean(grp):
        ivs = [r["implied_volatility"] for r in grp
               if r["implied_volatility"] is not None]
        return round(sum(ivs) / len(ivs), 4) if ivs else None

    calls_oi, puts_oi = oi(calls), oi(puts)
    pc_ratio = (puts_oi / calls_oi) if calls_oi > 0 else None

    def max_oi(grp):
        if not grp:
            return None
        return max(grp, key=lambda r: r["open_interest"] or 0).get("strike")

    return {
        "calls": len(calls),
        "puts": len(puts),
        "strikes": len({r["strike"] for r in rows}),
        "calls_oi": calls_oi,
        "puts_oi": puts_oi,
        "put_call_oi_ratio": round(pc_ratio, 4) if pc_ratio is not None else None,
        "max_oi_call_strike": max_oi(calls),
        "max_oi_put_strike": max_oi(puts),
        "iv_mean_call": iv_mean(calls),
        "iv_mean_put": iv_mean(puts),
    }


def _no_key_msg() -> str:
    return (
        "FINNHUB_API_KEY not configured — set it in your shell or in "
        "~/.labourious/config.yaml to enable Finnhub options. "
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


def _failed_from(
    tool: Any,
    note: str,
    *,
    source: str = "finnhub_options",
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
    "OptionsChainTool",
    "DEFAULT_API_BASE",
    "DEFAULT_EXPIRATIONS_CACHE_TTL_S",
    "DEFAULT_CHAIN_CACHE_TTL_S",
]
