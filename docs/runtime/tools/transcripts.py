"""
Tier-1 connector conn-4: earnings-call transcripts.

Public method surface:
- list_for_ticker(ticker, since_quarters=8, limit=50)
    Scrape SeekingAlpha's per-ticker transcript index
    (https://seekingalpha.com/symbol/{TICKER}/earnings/transcripts) and
    return [{"quarter", "call_date", "article_id", "url", "title"}, ...].

- fetch_transcript(article_id, ticker=None)
    Given a SeekingAlpha article id, fetch the article URL and pull the
    visible transcript body (Prepared Remarks + Q&A). SeekingAlpha gates
    the body behind a free login for *some* tickers; the tool returns
    status="PARTIAL" in that case instead of failing.

- recent_transcripts(ticker, since_quarters=8, limit=50)
    Convenience: list_for_ticker + drop entries older than the requested
    quarter-window. This is the call an agent lead will actually make.

- edgar_fallback(ticker, cik=None, since_quarters=8)
    Search EDGAR full-text for that ticker's 8-K filings (Item 2.02 is the
    "Results of Operations" item that announces earnings calls and attaches
    the press release). We use 100% of the existing sec_edgar_fulltext tool
    under the hood, so this is a probe-only fallback. Useful when SA
    misclassifies a small-cap, or for filings within ~30d that SA hasn't
    indexed yet.

Design notes:
- We never call a paid transcript API.
- All quotes must include the source URL in the ToolResult note so the
  ChatScreen citation chip can light up.
- The SeekingAlpha index page is consistent enough to scrape with stdlib
  HTMLParser; the article body is a much messier <div data-test-id="...">
  soup — also stdlib. The thinness of our parse keeps the connector cheap.
- Cache TTL is hour-scale (90d default). Transcripts don't change once
  posted, so cache them forever by default — TTL of 0 = never expire.
- Freshness tiers (CONNECTORS.md): transcripts are *static* — tier-3
  (90d). Caller can override.

Auth: keyless.
"""

from __future__ import annotations

import json as _json
import re as _re
import sys as _sys
import time as _time
import urllib.parse as _up
from dataclasses import dataclass, field
from html.parser import HTMLParser as _HTMLParser
from typing import Any

# Public re-export of project ToolResult so the rest of the runtime can
# import "from runtime.tools.transcripts import TranscriptResult" without
# pulling runtime internals.
if "runtime.tools" in _sys.modules:
    _rt = _sys.modules["runtime.tools"]
    ToolResult = getattr(_rt, "ToolResult", None)
else:
    ToolResult = None  # type: ignore[assignment]


def _now_iso() -> str:
    return _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())


if ToolResult is None:
    # Stand-alone fallback so this module can be piloted without loading
    # the rest of the runtime package.
    @dataclass
    class ToolResult:  # type: ignore[no-redef]
        status: str
        data: Any
        as_of: str = field(default_factory=_now_iso)
        source: str = ""
        note: str = ""


# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

DEFAULT_USER_AGENT = "Labourious/0.1 (+https://labourious.local; research)"
SA_BASE = "https://seekingalpha.com"
SA_TICKER_INDEX = SA_BASE + "/symbol/{ticker}/earnings/transcripts"
SA_ARTICLE = SA_BASE + "/article/{article_id}"

# Quarter label inside SA index titles is "Q1 2025", "Q4 2024", etc.
_QUARTER_RX = _re.compile(r"\bQ([1-4])\s+(20\d{2})\b")
_ARTICLE_ID_RX = _re.compile(r"/article/(\d+)-")
_DATE_FROM_ID_RX = _re.compile(
    r"-(\d{4})(?:-(?:Q[1-4]|earnings|results))?-(?:earnings-call|earnings|results)-transcript$"
)

# Maximum characters we return from one article body. Earnings-call
# transcripts are 8k-25k words; the agent lead only needs the prepared
# remarks + first 4-5 Q&A exchanges, so we clip loudly.
TRANSCRIPT_BODY_MAX_CHARS = 14_000


# --------------------------------------------------------------------------- #
# Parsers
# --------------------------------------------------------------------------- #


class _IndexLinkParser(_HTMLParser):
    """Pull `<a href="/article/{id}-...">` blocks out of a SeekingAlpha
    transcript index page, pairing them with the visible anchor text.

    The index page is a server-rendered HTML document; we don't need a
    full DOM. The article links all live under `/article/{numeric}-{slug}`
    and the anchor text gives us the quarter label.
    """

    def __init__(self) -> None:
        super().__init__()
        self._buf: list[str] = []
        self._in_a = False
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if "/article/" in href:
                self._in_a = True
                self._current_href = href
                self._current_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_a:
            text = "".join(self._current_text).strip()
            if self._current_href:
                self.links.append({"href": self._current_href, "text": text})
            self._in_a = False
            self._current_href = None
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._current_text.append(data)


class _ArticleBodyParser(_HTMLParser):
    """Extract the visible text from a SeekingAlpha article page.

    We strip every tag and return one big string. Anything inside
    <script>/<style>/<noscript> is dropped so we don't get JS bundle
    fragments as comments.
    """

    _DROP = {"script", "style", "noscript", "svg", "header", "nav", "footer"}

    def __init__(self) -> None:
        super().__init__()
        self._buf: list[str] = []
        self._depth_drop = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: ARG002
        if tag in self._DROP:
            self._depth_drop += 1
        elif tag in ("br", "p", "div", "h1", "h2", "h3", "li"):
            # Insert a newline so paragraph structure survives.
            if self._buf and not self._buf[-1].endswith("\n"):
                self._buf.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._DROP:
            self._depth_drop = max(0, self._depth_drop - 1)
        elif tag in ("p", "div", "h1", "h2", "h3", "li"):
            if self._buf and not self._buf[-1].endswith("\n"):
                self._buf.append("\n")

    def handle_data(self, data: str) -> None:
        if self._depth_drop:
            return
        self._buf.append(data)

    @property
    def text(self) -> str:
        return "".join(self._buf)


def _parse_index(html: str, ticker: str) -> list[dict[str, str]]:
    """Parse the transcript index page into a list of normalized rows.

    Returns: [{"quarter": "Q1 2025", "article_id": "...", "url": "...",
               "call_date": "2025-04-29" (best-effort), "title": "..."}]
    """
    p = _IndexLinkParser()
    p.feed(html)

    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for link in p.links:
        href = link["href"]
        m = _ARTICLE_ID_RX.search(href)
        if not m:
            continue
        article_id = m.group(1)
        if article_id in seen_ids:
            continue
        seen_ids.add(article_id)

        text = link["text"]
        # Strip "(TICKER)" parenthetical from text labels.
        text = _re.sub(r"\([A-Z]{1,5}\)", "", text).strip()

        # Quarter label pulled from the visible link text, e.g.
        # "Q1 2026 Earnings Call Transcript".
        qm = _QUARTER_RX.search(text)
        quarter_label = f"Q{qm.group(1)} {qm.group(2)}" if qm else ""

        # Build the full URL — SA links can be relative.
        url = href if href.startswith("http") else (SA_BASE + href)

        # Best-effort call date fallback (SA hides the date inside the URL
        # slug for some quarters). Search for " April 29, 2025"-style
        # dates inside the surrounding text near the link.
        call_date = ""  # caller can populate from EDGAR if needed.

        rows.append({
            "quarter": quarter_label,
            "article_id": article_id,
            "url": url,
            "call_date": call_date,
            "title": text,
        })

    return rows


def _parse_article(html: str) -> dict[str, Any]:
    """Parse one transcript article page.

    Returns {"body": str, "speaker_chips": [{"speaker": .., "section": ..}],
             "is_paywalled": bool}.
    """
    body_parser = _ArticleBodyParser()
    body_parser.feed(html)
    body = body_parser.text.strip()

    # SA gates the body behind a free login for some articles. Detect by
    # looking for the login-related CTA strings.
    gated_markers = [
        "Sign in to your account",
        "Already a member?",
        "We see you're a free user",
        "This content is exclusively for members",
    ]
    is_paywalled = any(m in body for m in gated_markers) and len(body) < 600

    # Clip text to keep agent prompts cheap.
    if len(body) > TRANSCRIPT_BODY_MAX_CHARS:
        body = body[:TRANSCRIPT_BODY_MAX_CHARS] + "\n...[truncated]..."

    # Speakers chip extraction — heuristic: lines starting with
    # "Operator:", "Prepared Remarks:", "Question-and-Answer Session:".
    chips: list[dict[str, str]] = []
    for marker in (
        "Operator:",
        "Prepared Remarks:",
        "Question-and-Answer Session:",
        "Company Participants",
        "Conference Call Participants",
    ):
        if marker in body:
            chips.append({"section": marker.rstrip(":")})
    return {"body": body, "speaker_chips": chips, "is_paywalled": is_paywalled}


def _quarter_label_to_number(label: str) -> int:
    """Convert 'Q1 2025' to a sortable year * 4 + quarter integer."""
    m = _QUARTER_RX.search(label or "")
    if not m:
        return 0
    q, y = int(m.group(1)), int(m.group(2))
    return y * 4 + q


def _now_quarter() -> int:
    """Return the current quarter as a (year*4 + quarter) int."""
    gm = _time.gmtime()
    return gm.tm_year * 4 + ((gm.tm_mon - 1) // 3 + 1)


# --------------------------------------------------------------------------- #
# Default opener (so the tool works without httpx installed)
# --------------------------------------------------------------------------- #


def _default_opener(url: str, headers: dict[str, str] | None = None) -> tuple[int, str, str]:
    """Plain urllib opener used when tests don't inject an `opener=` shim.

    Returns ``(status, body, etag)``. ``etag`` is whatever the upstream set
    in the ``ETag`` (or ``Last-Modified``) response header, hashable to a
    conditional GET. Empty string when upstream omits ETag (which is the
    common case for free-data providers like SeekingAlpha).
    """
    import urllib.request as _ur

    etag = ""
    req = _ur.Request(url, headers=headers or {})
    try:
        with _ur.urlopen(req, timeout=15) as resp:  # noqa: S310
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
            etag = resp.headers.get("ETag", "") or ""
    except _ur.HTTPError as exc:  # 304 / 404 / 5xx
        status = exc.code
        body = exc.read().decode("utf-8", errors="replace")
        etag = (exc.headers.get("ETag", "") if exc.headers else "") or ""
    except Exception:
        return 0, "", ""
    return status, body, etag


# --------------------------------------------------------------------------- #
# Tool
# --------------------------------------------------------------------------- #


class TranscriptsTool:
    """Tier-1 connector `transcripts`.

    Connects to SeekingAlpha's free transcript index for lists and to
    SEC EDGAR 8-K Item 2.02 for fallback call dates. Returns ToolResult
    in all cases — never raises on HTTP error.
    """

    SOURCE = "transcripts"
    DEFAULT_FRESHNESS_DAYS = 90  # transcripts are static; tier-3 freshness

    def __init__(
        self,
        opener=_default_opener,
        user_agent: str = DEFAULT_USER_AGENT,
        sec_edgar_fulltext_tool: Any | None = None,
    ) -> None:
        self._opener = opener
        self._ua = user_agent
        self._sec = sec_edgar_fulltext_tool
        self._cache: dict[str, tuple[float, ToolResult]] = {}

    # -- cache ---------------------------------------------------------- #
    def _cache_get(self, key: str, ttl: float) -> ToolResult | None:
        hit = self._cache.get(key)
        if hit is None:
            return None
        ts, val = hit
        if ttl > 0 and (_time.time() - ts) > ttl:
            self._cache.pop(key, None)
            return None
        return val

    def _cache_put(self, key: str, val: ToolResult) -> None:
        self._cache[key] = (_time.time(), val)

    def clear_cache(self) -> None:
        self._cache.clear()

    # -- network -------------------------------------------------------- #
    def _headers(self, if_none_match: str | None = None) -> dict[str, str]:
        h = {
            "User-Agent": self._ua,
            "Accept": "text/html,application/xhtml+xml",
        }
        if if_none_match:
            h["If-None-Match"] = if_none_match
        return h

    def _fetch(
        self,
        url: str,
        *,
        if_none_match: str | None = None,
    ) -> tuple[int, str, str]:
        """Fetch a URL via the tool's opener.

        Returns ``(status, body, etag)``. ``self._last_etag`` carries
        the ETag that *came back from* the fetch (i.e. what the next
        conditional GET should send). Connectors that return UNCHANGED
        use this with the prior etag so the snippet cache stays in sync.
        """
        result = self._opener(url, self._headers(if_none_match=if_none_match))
        # Back-compat: 2-tuple openers (older test mocks) get normalized.
        if isinstance(result, tuple) and len(result) == 2:
            status, body = result
            etag = ""
        else:
            status, body, etag = result
        self._last_etag = etag or ""
        return status, body, etag

    # -- public API ---------------------------------------------------- #
    def list_for_ticker(
        self,
        ticker: str,
        since_quarters: int = 8,
        limit: int = 50,
        if_none_match: str | None = None,
    ) -> ToolResult:
        if_none_match = if_none_match or getattr(
            self, "_labourious_if_none_match", None
        )
        ticker = (ticker or "").upper().strip()
        if not ticker:
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note="empty ticker",
            )

        cache_key = f"list::{ticker}::{since_quarters}::{limit}"
        cached = self._cache_get(cache_key, ttl=0)  # 0 = never expire
        if cached is not None:
            return cached

        url = SA_TICKER_INDEX.format(ticker=_up.quote(ticker))
        try:
            status_code, html = self._fetch(url, if_none_match=if_none_match)
        except Exception as exc:
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note=f"network error on {url}: {exc!r}",
            )

        # [domain-8] 304 Not Modified: upstream confirms cached index is
        # current. We don't re-parse the body. Return UNCHANGED with the
        # same ETag so the snippet cache can keep its state.
        if status_code == 304:
            etag_response = self._last_etag
            return ToolResult(
                as_of=_now_iso(),
                status="UNCHANGED",
                data=None,
                source=self.SOURCE,
                note="ETag matched: 304 Not Modified",
                etag=(etag_response or if_none_match),
            )

        if status_code >= 400:
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note=f"HTTP {status_code} on {url}",
            )

        rows = _parse_index(html, ticker)
        current_q = _now_quarter()
        cutoff_q = current_q - int(since_quarters) + 1  # inclusive window
        # Filter to roughly the requested quarter window — keep rows we
        # *can* classify, drop them otherwise (we just don't know).
        def _row_quarter_int(r: dict[str, str]) -> int:
            return _quarter_label_to_number(r.get("quarter", ""))

        kept: list[dict[str, str]] = []
        for r in rows:
            qn = _row_quarter_int(r)
            if qn == 0 or qn >= cutoff_q:
                kept.append(r)
        kept = kept[: int(limit)]

        if not kept:
            result = ToolResult(
                as_of=_now_iso(),
                status="EMPTY",
                data=[],
                source=self.SOURCE,
                note=(
                    f"SeekingAlpha returned 0 transcript rows for "
                    f"{ticker} in last {since_quarters} quarter(s). "
                    f"Source: {url}"
                ),
            )
        else:
            result = ToolResult(
                as_of=_now_iso(),
                status="SUCCESS",
                data=kept,
                source=self.SOURCE,
                note=(
                    f"SeekingAlpha: {len(kept)} transcript entries for "
                    f"{ticker} in last {since_quarters} quarter(s). "
                    f"Source: {url}"
                ),
            )

        self._cache_put(cache_key, result)
        return result

    def fetch_transcript(self, article_id: str, ticker: str | None = None) -> ToolResult:
        article_id = (article_id or "").strip()
        if not article_id.isdigit():
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note=f"article_id must be numeric; got {article_id!r}",
            )

        cache_key = f"article::{article_id}"
        cached = self._cache_get(cache_key, ttl=0)
        if cached is not None:
            return cached

        url = SA_ARTICLE.format(article_id=_up.quote(article_id))
        try:
            status_code, html = self._fetch(url)
        except Exception as exc:
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note=f"network error on {url}: {exc!r}",
            )

        if status_code >= 400:
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note=f"HTTP {status_code} on {url}",
            )
        parsed = _parse_article(html)
        body = parsed["body"]
        is_paywalled = parsed["is_paywalled"]

        if is_paywalled:
            result = ToolResult(
                as_of=_now_iso(),
                status="PARTIAL",
                data={"article_id": article_id, "url": url, "preview": body[:600]},
                source=self.SOURCE,
                note=(
                    f"Article {article_id} is login-gated; "
                    f"returning preview only. Source: {url}"
                ),
            )
        else:
            # Header picks up the first 2 non-empty lines as a stand-in
            # for the article metadata strip (date, ticker, quarter).
            head_lines = [
                ln.strip() for ln in body.splitlines() if ln.strip()
            ][:8]
            quarter_match = _QUARTER_RX.search(" ".join(head_lines))
            quarter = (
                f"Q{quarter_match.group(1)} {quarter_match.group(2)}"
                if quarter_match
                else ""
            )
            call_date_m = _re.search(
                r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},\s+(20\d{2})\b",
                " ".join(head_lines),
            )
            call_date = (
                call_date_m.group(0) if call_date_m else ""
            )
            result = ToolResult(
                as_of=_now_iso(),
                status="SUCCESS",
                data={
                    "article_id": article_id,
                    "ticker": (ticker or "").upper(),
                    "quarter": quarter,
                    "call_date_text": call_date,
                    "body": body,
                    "speaker_chips": parsed["speaker_chips"],
                    "url": url,
                },
                source=self.SOURCE,
                note=(
                    f"Article {article_id} parsed "
                    f"({len(body)} chars). Source: {url}"
                ),
            )

        self._cache_put(cache_key, result)
        return result

    def recent_transcripts(
        self,
        ticker: str,
        since_quarters: int = 8,
        limit: int = 50,
    ) -> ToolResult:
        """Convenience — same as list_for_ticker but the *agent's* call."""
        return self.list_for_ticker(ticker, since_quarters=since_quarters, limit=limit)

    def edgar_fallback(
        self,
        ticker: str,
        cik: str | None = None,
        since_quarters: int = 8,
    ) -> ToolResult:
        """Search EDGAR 8-K filings for the ticker — alternative path
        when SeekingAlpha is gated or has not yet indexed a small-cap.

        Requires the runtime's sec_edgar_fulltext tool to be wired in.
        Returns status="EMPTY"/"FAILED" gracefully if not wired.
        """
        ticker = (ticker or "").upper().strip()
        if not ticker:
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note="empty ticker",
            )

        if self._sec is None:
            return ToolResult(
                as_of=_now_iso(),
                status="EMPTY",
                data=None,
                source=self.SOURCE,
                note=(
                    "EDGAR fallback not configured "
                    "(sec_edgar_fulltext_tool not wired)"
                ),
            )

        try:
            res = self._sec.search(
                query=ticker,
                forms="8-K",
                ciks=[cik] if cik else None,
                since_days=since_quarters * 90,
                limit=20,
            )
        except Exception as exc:
            return ToolResult(
                as_of=_now_iso(),
                status="FAILED",
                data=None,
                source=self.SOURCE,
                note=f"sec_edgar_fulltext raised: {exc!r}",
            )

        # Re-wrap: the sec tool returns ToolResult-like; we re-emit under
        # our own `source` so the citation chip names "transcripts".
        if getattr(res, "status", "") == "SUCCESS":
            return ToolResult(
                as_of=_now_iso(),
                status="SUCCESS",
                data=getattr(res, "data", None),
                source=self.SOURCE,
                note=(
                    f"EDGAR 8-K probe for {ticker} "
                    f"(Item 2.02 = earnings-call announcement). "
                    f"Source: https://www.sec.gov/cgi-bin/browse-edgar"
                    f"?action=getcompany&CIK={cik or ticker}&type=8-K"
                ),
            )

        return ToolResult(
            as_of=_now_iso(),
            status=getattr(res, "status", "EMPTY"),
            data=getattr(res, "data", None),
            source=self.SOURCE,
            note=(
                f"EDGAR 8-K probe for {ticker}: "
                f"{getattr(res, 'note', '') or 'no filings'}"
            ),
        )


# --------------------------------------------------------------------------- #
# Module exports
# --------------------------------------------------------------------------- #

__all__ = [
    "TranscriptsTool",
    "ToolResult",
    "TRANSCRIPT_BODY_MAX_CHARS",
    "SA_BASE",
    "SA_TICKER_INDEX",
]
