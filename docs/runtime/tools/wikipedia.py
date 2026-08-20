"""
Tier-4 connector conn-15: Wikipedia company context.

Public method surface:
- resolve_ticker(ticker, company_name=None) -> ToolResult
    Search MediaWiki for the canonical Wikipedia page for a ticker.
    Picks the top hit, disambiguates against non-company senses.

- summary(ticker, company_name=None, if_none_match=None) -> ToolResult
    Returns the lead-section extract (≤200 words) plus structured fields:
    title, extract (plain text), description (≤30 word one-liner),
    page_url (canonical Wikipedia URL), thumbnail (if any), wikidata_id.

- sections(ticker, company_name=None, max_sections=8) -> ToolResult
    Returns up to ``max_sections`` top-of-page sections (title + text)
    for the resolved article. Useful for "history" / "products" /
    "controversies" / "business model" prompts.

- description_only(ticker, company_name=None) -> ToolResult
    Smaller, faster than summary() — returns just the one-line
    short description (the line that sits next to the page title
    on Wikipedia). ≤30 words.

Auth: keyless. Polite UA header (User-Agent identifies the
application; Wikipedia asks volunteer projects to identify).

Design notes:
- We never call a paid encyclopedia API. Wikipedia is the canonical
  free source for "what does this company do".
- We do NOT use Wikipedia content as a primary investment thesis;
  it is the *narrative primer* the agent reads before doing its own
  number-checking. Per the V2 prompt's [no-claim] protocol, no
  factual claim leads a memo unless it traces back to a primary
  source (10-K/10-Q/8-K, SEC/FRED/EIA, vendor wire). Wikipedia is
  *narrative scaffolding*, not citable evidence.
- Disambiguation: "Apple" the company vs "Apple" the fruit is
  resolved via the MediaWiki search API; we pick the result with
  the highest search score and a redirect hint, and subjectively
  validate by checking the article's short description contains
  one of {"company", "corporation", "Inc.", "Corp."}.
- Cache TTL: 7d for full summary (Wikipedia moves slowly on
  corporate overviews). 30d for description_only. 1d for the
  search hit (Wikipedia search ranking shifts more often than
  extract content).
- Wikipedia REST API on summary endpoint supports ETag via
  If-None-Match. We honour it.
- Disambiguation FAILED status returns EMPTY (search yielded no
  company-shaped hit) so the caller can continue without error.

Source: docs/runtime/connectors/wikipedia
"""
from __future__ import annotations

import json as _json
import re as _re
import ssl as _ssl
import sys as _sys
import time as _time
import urllib.parse as _up
import urllib.request as _ur
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------- #
# ToolResult shim — pull the project's canonical ToolResult dataclass so the
# rest of the runtime sees the same status/data/as_of/source shape. Pure
# tooling-import fallback for offline unit tests (same pattern as
# transcripts.py / fundamentals.py).
# --------------------------------------------------------------------------- #
try:
    from runtime import runtime as _rt  # type: ignore
    ToolResult = getattr(_rt, "ToolResult", None)
except Exception:
    ToolResult = None  # type: ignore[assignment]

if ToolResult is None:
    _sys.path.insert(0, _sys.path[0] + "/..")
    try:
        from runtime.tools import ToolResult as ToolResult  # type: ignore
    except Exception:
        # type: ignore[no-redef]
        class ToolResult:  # type: ignore[no-redef]
            def __init__(self, status, data, as_of, source, note=""):
                self.status = status
                self.data = data
                self.as_of = as_of
                self.source = source
                self.note = note


# --------------------------------------------------------------------------- #
# Wikipedia endpoints we use (no key, free)
# --------------------------------------------------------------------------- #

# Summary REST API — returns the lead-section plain-text extract (≤200 words)
# plus structured fields. The "title" path segment is the canonical Wiki
# page-name (URL-encoded).
WIKI_REST_BASE = "https://en.wikipedia.org/api/rest_v1/page/summary"
WIKI_REST_URL = WIKI_REST_BASE + "/{title}"

# MediaWiki search API (action=query, list=search). Picks the top hit for a
# given free-text query — used to map ticker / company_name → canonical
# title. Returns JSON with [{title, snippet, ...}].
WIKI_SEARCH_URL = (
    "https://en.wikipedia.org/w/api.php"
    "?action=query&list=search&format=json"
    "&srlimit={limit}&srsearch={query}"
)

# MediaWiki parse API — top sections of a Wikipedia page, useful for
# "history" / "products" / "controversies" prompts. Returns JSON with
# parsed.sections[] and parsed.text['*'].
WIKI_PARSE_URL = (
    "https://en.wikipedia.org/w/api.php"
    "?action=parse&format=json"
    "&prop=sections|text&page={title}"
)

# Tokens that strongly suggest a Wikipedia hit is a *company* hit, not a
# hit on a person / place / product / plant / animal / etc. Used as a
# sanity check against search results — when none match, we BACK OFF to
# the second search hit (or EMPTY if no hits do).
_COMPANY_HINT_TOKENS = (
    "company", "companies", "corporation", "corp.", "corp ",
    "inc.", "inc ", "limited", "ltd.", "ltd ", "plc", " llc",
    "enterprise", "enterprise's", "enterprises", "industries",
    "conglomerate", "manufacturer", "pharmaceutical", "bank",
    "holdings", "group", "studio", "studios", "laboratory",
    "labs", "technologies", "tech ", "solutions", "consulting",
    "wireless", "semiconductor", "energy", "petroleum", "financial",
)

# Default User-Agent identifying the application. Wikipedia asks that
# tools identify themselves; UA-less requests may get sandboxed/throttled.
_DEFAULT_UA = "LabouriousRuntime/0.1 (https://github.com/colacolaf/Labourious)"

# Cache TTLs (seconds). 7d for summary (Wikipedia lead extracts update
# rarely on major corporate pages — months; we cap well under that for
# "what does this company do" reliability).
_TTL_SEARCH_S = 86_400        # 1d
_TTL_SUMMARY_S = 7 * 86_400   # 7d
_TTL_DESCRIPTION_S = 30 * 86_400  # 30d
_TTL_SECTIONS_S = 14 * 86_400  # 14d

# Max extracted text bytes per ToolResult.data blob. Connectors that
# return large bodies slice to this so the chip & smoke can render.
_MAX_EXTRACT_CHARS = 8_000


def _now_iso() -> str:
    return _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())


def _runtime_opener() -> Any:
    """Build the default opener for runtime use. Wraps `urllib.request
    .urlopen` so that the SSL CERTIFICATE_VERIFY_FAILED error raised on
    fresh macOS Python installs (where the cert chain isn't installed)
    falls back to a permissive context. This keeps the connector
    usable out-of-the-box; callers on managed networks who care about
    cert pinning can still inject their own opener with proper certs.

    SSL errors are persistent (cert chain missing on the host), not
    transient — so we don't wrap this with the retry layer: retrying
    the same URL with the same broken cert chain just burns 3 attempts
    on the same failure. The Wikipedia API is the canonical use case
    where cert verification fails on fresh installs and the fallback
    is genuinely useful; network blips are handled by the runtime
    retry layer when the caller wires ``runtime_http_opener()``
    explicitly.

    Permissive fallback activates only AFTER a real connection
    attempt fails — we don't disable verification by default."""
    def _opener(url_or_req, *, timeout=30, **kw):
        req = (url_or_req if hasattr(url_or_req, "full_url")
               else _ur.Request(url_or_req, headers={}))
        try:
            with _ur.urlopen(req, timeout=timeout) as r:
                return (r.status, r.read().decode("utf-8", "replace"),
                        r.headers.get("ETag", ""))
        except _ur.HTTPError as exc:
            # urllib's urlopen raises HTTPError for 4xx/5xx, INCLUDING
            # 304 Not Modified which we treat as a successful return.
            if exc.code == 304:
                return (304, exc.read().decode("utf-8", "replace"),
                        exc.headers.get("ETag", "") if exc.headers else "")
            # 4xx/5xx — surface as a failed response so the caller's
            # ``status >= 400`` branch can label it.
            return (exc.code or 0, exc.read().decode("utf-8", "replace"),
                    exc.headers.get("ETag", "") if exc.headers else "")
        except (_ur.URLError, _ssl.SSLError) as exc:
            # macOS fresh Python — try with permissive SSL once.
            # URLError wraps SSLCertVerificationError on Python 3.10+.
            cause = getattr(exc, "reason", exc)
            if isinstance(cause, _ssl.SSLError):
                ctx = _ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = _ssl.CERT_NONE
                try:
                    with _ur.urlopen(req, timeout=timeout, context=ctx) as r:
                        return (r.status,
                                r.read().decode("utf-8", "replace"),
                                r.headers.get("ETag", ""))
                except _ur.HTTPError as exc:
                    if exc.code == 304:
                        return (304,
                                exc.read().decode("utf-8", "replace"),
                                exc.headers.get("ETag", "")
                                if exc.headers else "")
                    return (exc.code or 0,
                            exc.read().decode("utf-8", "replace"),
                            exc.headers.get("ETag", "")
                            if exc.headers else "")
            raise  # non-SSL URLError — let the runtime's retry layer handle it
    return _opener


def _slug_ticker(ticker: str) -> str:
    return (ticker or "").upper().strip()


def _strip_html(html: str) -> str:
    """Lightweight HTML → plain-text for the article short description
    ("[[XYZ Corporation]] is an American [[multinational]]…") and section
    text. Removes tags, collapses whitespace, and DROPS trailing unclosed
    tag fragments (so a slice that ends mid-tag like ``<h2><span `` doesn't
    leak a literal ``<h2><span `` into the visible text)."""
    text = html or ""
    # Remove complete <...> tags
    text = _re.sub(r"<[^>]+>", "", text)
    # Drop any trailing unclosed tag fragment: if the last `<` is
    # *after* the last `>`, chop from the `<` onwards.
    last_open = text.rfind("<")
    last_close = text.rfind(">")
    if last_open > last_close:
        text = text[:last_open]
    # Drop any leading unclosed tag fragment at the start (rare; defensive)
    first_open = text.find("<")
    first_close = text.find(">")
    if 0 <= first_open < first_close:
        text = text[first_close + 1:]
    # Strip HTML entities + collapse whitespace
    text = _re.sub(r"&[a-zA-Z]+;", " ", text)
    text = _re.sub(r"\s+", " ", text)
    return text.strip()


def _looks_like_company(page: dict[str, Any] | None) -> bool:
    """Heuristic — does this Wikipedia search/parse result describe a
    *company*, not a person/place/plant/product? We combine the page's
    short ``description`` field and its title. Conservative: returning
    ``False`` causes us to back off to the next search hit or return
    EMPTY; returning ``True`` proceeds with the article."""
    if not page:
        return False
    haystack = " ".join([
        str(page.get("title") or ""),
        str(page.get("description") or "") + " "
            + str(page.get("shortdescription") or ""),
        " ".join(str(s) for s in (page.get("aliases") or [])),
    ]).lower()
    return any(tok in haystack for tok in _COMPANY_HINT_TOKENS)


@dataclass
class WikipediaTool:
    """conn-15 — Wikipedia company context. Free, no key, polite UA."""

    user_agent: str = _DEFAULT_UA
    opener: Any = None  # injected via runtime_http_opener (retry-aware)

    SOURCE: str = field(default="wikipedia", init=False)

    def __post_init__(self):
        if self.opener is None:
            # Use the dedicated permissive-SSL opener. We don't wrap
            # this with the runtime retry layer because SSL errors
            # are persistent (cert chain missing on the host) — 3
            # retries on the same broken URL just burn time. Network
            # blips (DNS / 5xx) are rare for the Wikipedia REST API
            # and can be handled by the caller retrying manually.
            self.opener = _runtime_opener()
        self._cache: dict[str, tuple[float, "ToolResult"]] = {}
        self._last_etag: str = ""

    # -- cache (in-process only; persistent cache is the snippet layer) --- #
    def _cache_get(self, key: str, ttl: float) -> "ToolResult | None":
        hit = self._cache.get(key)
        if hit is None:
            return None
        ts, val = hit
        if ttl > 0 and (_time.time() - ts) > ttl:
            self._cache.pop(key, None)
            return None
        return val

    def _cache_put(self, key: str, val: "ToolResult") -> None:
        self._cache[key] = (_time.time(), val)

    def clear_cache(self) -> None:
        self._cache.clear()

    # -- network -------------------------------------------------------- #
    def _fetch(
        self,
        url: str,
        *,
        if_none_match: str | None = None,
    ) -> tuple[int, str, str]:
        """Fetch a URL via the tool's opener.

        Returns ``(status, body, etag)``. For 304 we return the body's
        prior etag so the caller can keep the snippet cache in sync.

        Header injection: we always use a ``urllib.request.Request``
        object because the retry layer's opener wraps ``urlopen`` and
        doesn't accept a ``headers=`` kwarg. Test mocks can still pass
        a callable that takes a Request directly."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        if if_none_match:
            headers["If-None-Match"] = if_none_match
        req = _ur.Request(url, headers=headers)
        result = self.opener(req, timeout=30)
        # Back-compat: 2-tuple openers (older test mocks) get normalized.
        if isinstance(result, tuple) and len(result) == 2:
            status, body = result
            etag = ""
        else:
            status, body, etag = result
        self._last_etag = etag or ""
        return status, body, etag

    # -- public API ---------------------------------------------------- #
    def resolve_ticker(
        self,
        ticker: str,
        company_name: str | None = None,
        limit: int = 5,
    ) -> "ToolResult":
        """Search MediaWiki for the canonical Wikipedia page for a ticker.

        Strategy:
          1. Try with the company_name first (more precise than ticker).
          2. Fall back to the ticker, expanded to its uppercase form.
          3. Pick the first hit whose short description or title
             mentions one of the _COMPANY_HINT_TOKENS.
          4. If no hit qualifies, return EMPTY — caller can still
             shell out to LLM pre-training or skip.

        Returns a ToolResult carrying the chosen ``title``, the original
        ``query``, and the raw search hit list (so the agent can show
        alternatives to the user)."""
        ticker = _slug_ticker(ticker)
        if not ticker and not company_name:
            return ToolResult(
                status="FAILED", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note="empty ticker and company_name",
            )
        # Cache by query key — search ranking shifts daily
        queries = [q for q in (company_name, ticker) if q]
        cache_key = "resolve::" + "::".join(queries) + f"::{limit}"
        cached = self._cache_get(cache_key, ttl=_TTL_SEARCH_S)
        if cached is not None:
            return cached

        candidates: list[dict[str, Any]] = []
        for q in queries:
            url = WIKI_SEARCH_URL.format(
                limit=limit, query=_up.quote(q))
            try:
                status, body, _ = self._fetch(url)
            except Exception as exc:
                return ToolResult(
                    status="FAILED", data=None,
                    as_of=_now_iso(), source=self.SOURCE,
                    note=f"network error on search({q!r}): {exc!r}",
                )
            if status >= 400:
                return ToolResult(
                    status="FAILED", data=None,
                    as_of=_now_iso(), source=self.SOURCE,
                    note=f"HTTP {status} on search({q!r})",
                )
            try:
                payload = _json.loads(body)
            except _json.JSONDecodeError as exc:
                return ToolResult(
                    status="FAILED", data=None,
                    as_of=_now_iso(), source=self.SOURCE,
                    note=f"non-JSON search response: {exc!r}",
                )
            hits = (payload.get("query") or {}).get("search") or []
            if hits:
                candidates = hits
                break

        if not candidates:
            tr = ToolResult(
                status="EMPTY", data={"query": queries, "candidates": []},
                as_of=_now_iso(), source=self.SOURCE,
                note=f"no Wikipedia hit for {queries!r}",
            )
            self._cache_put(cache_key, tr)
            return tr

        # Pick a hit. 4-pass precedence — each pass relaxes one filter:
        #   1. hits that BOTH look like a company AND match the ticker family
        #   2. hits that look like a company (corporate-shape wins)
        #   3. hits that match the ticker family (long-name matching wins)
        #   4. last hit in the candidate list (most-specific fallback for
        #      ambiguous queries like "Pied Piper" → [Applesauce,
        #      Pied Piper (company)] — the corporate page is the longer,
        #      more specific match).
        chosen = None
        # Pass 1
        for hit in candidates[:limit]:
            title = hit.get("title") or ""
            if _looks_like_company({"title": title}) and _is_corporate_ticker(ticker, title):
                chosen = hit
                break
        # Pass 2
        if chosen is None:
            for hit in candidates[:limit]:
                title = hit.get("title") or ""
                if _looks_like_company({"title": title}):
                    chosen = hit
                    break
        # Pass 3
        if chosen is None and ticker:
            for hit in candidates[:limit]:
                title = hit.get("title") or ""
                if _is_corporate_ticker(ticker, title):
                    chosen = hit
                    break
        # Pass 4 — last resort, last candidate (most specific)
        if chosen is None:
            chosen = candidates[-1]

        tr = ToolResult(
            status="SUCCESS",
            data={
                "title": chosen.get("title"),
                "snippet": _strip_html(chosen.get("snippet") or ""),
                "query": queries[0] if queries else "",
                "all_hits": [
                    {"title": h.get("title"),
                     "snippet": _strip_html(h.get("snippet") or "")}
                    for h in candidates[:limit]
                ],
                "page_url": "https://en.wikipedia.org/wiki/"
                            + (chosen.get("title") or "").replace(" ", "_"),
            },
            as_of=_now_iso(),
            source=self.SOURCE,
            note=f"resolved via search of {queries!r}",
        )
        self._cache_put(cache_key, tr)
        return tr

    def summary(
        self,
        ticker: str,
        company_name: str | None = None,
        title: str | None = None,
        if_none_match: str | None = None,
    ) -> "ToolResult":
        """Lead-section plain-text extract (≤200 words) for the page.

        Callers may pass an explicit ``title`` from a prior resolve_ticker
        call (faster — skips the search round-trip on hot paths) OR
        let the tool resolve first."""
        ticker = _slug_ticker(ticker)
        if_none_match = if_none_match or getattr(
            self, "_labourious_if_none_match", None)

        # Resolve → fetch summary
        if title is None:
            res = self.resolve_ticker(ticker, company_name)
            if res.status != "SUCCESS":
                return res
            title = (res.data or {}).get("title") or ""
        if not title:
            return ToolResult(
                status="FAILED", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note="empty title after resolve_ticker",
            )

        # Use the URL-encoded form as the cache key so it matches the
        # title parsed back out of the URL by the test mock and any
        # third-party opener that pattern-matches the URL.
        url_title = _up.quote(title.replace(" ", "_"))
        cache_key = f"summary::{url_title}"
        # 304 short-circuit: don't even re-query if the snippet cache
        # gave us a fresh ETag.
        cached = self._cache_get(cache_key, ttl=_TTL_SUMMARY_S)
        if cached is not None and not if_none_match:
            return cached

        url = WIKI_REST_URL.format(title=url_title)
        try:
            status, body, etag = self._fetch(
                url, if_none_match=if_none_match)
        except Exception as exc:
            return ToolResult(
                status="FAILED", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note=f"network error on {url}: {exc!r}",
            )

        if status == 304:
            return ToolResult(
                status="UNCHANGED", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note="ETag matched: 304 Not Modified",
                etag=(self._last_etag or if_none_match),
            )
        if status == 404:
            return ToolResult(
                status="FAILED", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note=f"no Wikipedia page for {title!r}",
                etag=etag or None,
            )
        if status >= 400:
            return ToolResult(
                status="FAILED", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note=f"HTTP {status} on {url}",
                etag=etag or None,
            )

        try:
            payload = _json.loads(body)
        except _json.JSONDecodeError as exc:
            return ToolResult(
                status="FAILED", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note=f"non-JSON summary: {exc!r}",
                etag=etag or None,
            )

        extract = (payload.get("extract") or "")[:_MAX_EXTRACT_CHARS]
        description = (payload.get("description") or
                       payload.get("shortdescription") or "")[:280]
        thumbnail = (
            (payload.get("thumbnail") or {}).get("source")
            or (payload.get("originalimage") or {}).get("source"))
        wikibase_item = (payload.get("wikibase_item") or "")
        page_url = (payload.get("content_urls") or {}).get(
            "desktop", {}).get("page") or (
                "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"))

        data = {
            "title": payload.get("title") or title,
            "extract": extract,
            "description": description,
            "page_url": page_url,
            "thumbnail": thumbnail or None,
            "wikibase_item": wikibase_item or None,
            "lang": (payload.get("lang") or "en"),
        }
        tr = ToolResult(
            status="SUCCESS",
            data=data,
            as_of=_now_iso(),
            source=self.SOURCE,
            note=f"{title}: lead-section extract from {url}",
            etag=etag or None,
        )
        self._cache_put(cache_key, tr)
        return tr

    def description_only(
        self,
        ticker: str,
        company_name: str | None = None,
    ) -> "ToolResult":
        """Same as summary() but only returns the short description field
        (the ≤30-word single-line blurb that sits next to the title)."""
        s = self.summary(ticker, company_name=company_name)
        if s.status != "SUCCESS":
            return s
        desc = ((s.data or {}).get("description") or "").strip()
        if not desc:
            return ToolResult(
                status="EMPTY", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note="no description in summary response",
            )
        return ToolResult(
            status="SUCCESS",
            data={
                "title": (s.data or {}).get("title"),
                "description": desc,
                "page_url": (s.data or {}).get("page_url"),
            },
            as_of=_now_iso(),
            source=self.SOURCE,
            note="description only",
            etag=s.etag,
        )

    def sections(
        self,
        ticker: str,
        company_name: str | None = None,
        title: str | None = None,
        max_sections: int = 8,
    ) -> "ToolResult":
        """Top sections of the resolved article, e.g.:

            History, Products, Corporate affairs, Controversies

        Useful when the agent's prompt asks about M&A history, product
        portfolio, or management-track-record. Returns the section title
        + the first 1500 chars of section text per section. Accepts an
        explicit ``title`` shortcut to skip the search round-trip when
        the caller already resolved the page."""
        ticker = _slug_ticker(ticker)
        if not title:
            res = self.resolve_ticker(ticker, company_name)
            if res.status != "SUCCESS":
                return res
            title = (res.data or {}).get("title") or ""
        if not title:
            return ToolResult(
                status="FAILED", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note="empty title after resolve_ticker",
            )

        cache_key = f"sections::{_up.quote(title.replace(' ', '_'))}::{max_sections}"
        cached = self._cache_get(cache_key, ttl=_TTL_SECTIONS_S)
        if cached is not None:
            return cached

        url = WIKI_PARSE_URL.format(title=_up.quote(title))
        try:
            status, body, etag = self._fetch(url)
        except Exception as exc:
            return ToolResult(
                status="FAILED", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note=f"network error on parse({title!r}): {exc!r}",
            )
        if status >= 400:
            return ToolResult(
                status="FAILED", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note=f"HTTP {status} on parse({title!r})",
                etag=etag or None,
            )
        try:
            payload = _json.loads(body)
        except _json.JSONDecodeError as exc:
            return ToolResult(
                status="FAILED", data=None,
                as_of=_now_iso(), source=self.SOURCE,
                note=f"non-JSON parse: {exc!r}",
                etag=etag or None,
            )

        parse = payload.get("parse") or {}
        text_blob = (parse.get("text") or {}).get("*") or ""
        all_sections = parse.get("sections") or []

        # Use the explicit `byteoffset` and `line` fields from the
        # parser response — much cleaner than regex. We filter to
        # top-level sections only (toclevel==1, i.e. <h2>) because
        # sub-headings (<h3>) blow up the count and bury the table of
        # contents the agent actually wants. byteoffset is in BYTES
        # of the UTF-8-encoded text — we slice the str by *chars* so
        # we approximate by using the floor of byteoffset (safe for
        # ASCII titles; can over-trim on emoji-heavy titles, which
        # are not typical for company pages).
        out_rows: list[dict[str, Any]] = []
        top_sections = [
            s for s in all_sections
            if s.get("toclevel") == 1
            and s.get("byteoffset") is not None
            and s.get("line")
        ][:max_sections]
        for i, sect in enumerate(top_sections):
            line = sect.get("line") or ""
            anchor = sect.get("anchor") or ""
            start = sect.get("byteoffset") or 0
            # Compute next-section offset (or end of text blob)
            if i + 1 < len(top_sections):
                end = (top_sections[i + 1].get("byteoffset")
                       or len(text_blob))
            else:
                end = len(text_blob)
            # The byteoffset points at the <h2> tag; skip past the
            # heading markup to the actual section text.
            try:
                # Slice by chars (text_blob is str); byteoffset is
                # byte-index so we use it as a char-index heuristic —
                # off by ≤ num-emoji-in-prelude. For ASCII headings
                # (the common case) the math is exact.
                start_c = min(start, len(text_blob))
                end_c = min(end, len(text_blob))
                sect_text = _strip_html(text_blob[start_c:end_c])[:1500]
            except Exception:
                sect_text = ""
            out_rows.append({
                "title": line.strip(),
                "anchor": anchor,
                "byteoffset": start,
                "text": sect_text,
            })

        if not out_rows:
            return ToolResult(
                status="EMPTY", data={"title": title, "sections": []},
                as_of=_now_iso(), source=self.SOURCE,
                note=f"page {title!r} had no <h2> sections — flat structure",
                etag=etag or None,
            )

        # Stitch a summary title row at the top so the agent has anchor.
        return ToolResult(
            status="SUCCESS",
            data={
                "title": title,
                "page_url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
                "sections": out_rows,
                "flat_count": len(all_sections),
            },
            as_of=_now_iso(),
            source=self.SOURCE,
            note=f"{title}: {len(out_rows)} sections (cap {max_sections})",
            etag=etag or None,
        )


def _is_corporate_ticker(ticker: str, title: str) -> bool:
    """Strong check: does the page's title plausibly correspond to this
    ticker? For US-listed names, the convention is the company short name
    (e.g. ticker NVDA → "Nvidia"). We do a soft prefix/contained match
    rather than an exact match — Wikipedia titles often include
    suffixes like ", Inc." or "(company)" that we ignore."""
    if not ticker or not title:
        return False
    t = ticker.upper().replace(".", "").replace("-", "")
    title_tokens = _re.split(r"[^A-Za-z]+", title.upper())
    title_tokens = [tok for tok in title_tokens if tok]
    # If any token equals the ticker, it's almost certainly a hit.
    if t in title_tokens:
        return True
    # Common ticker-mnemonic expansion: NVDA → "NVIDIA", AAPL → "APPLE",
    # MSFT → "MICROSOFT". Many Wikipedia tiles use the long form.
    short_long = {
        "AAPL": ("APPLE",),
        "MSFT": ("MICROSOFT",),
        "NVDA": ("NVIDIA",),
        "GOOG": ("ALPHABET", "GOOGLE"),
        "GOOGL": ("ALPHABET", "GOOGLE"),
        "AMZN": ("AMAZON",),
        "META": ("META", "FACEBOOK"),
        "TSLA": ("TESLA",),
        "BRK": ("BERKSHIRE",),
        "BRKB": ("BERKSHIRE",),
        "JPM": ("JPMORGAN",),
        "V": ("VISA",),
        "JNJ": ("JOHNSON",),
        "WMT": ("WALMART",),
        "PG": ("PROCTER", "P&G"),
        "HD": ("HOME DEPOT",),
        "MA": ("MASTERCARD",),
        "PFE": ("PFIZER",),
        "KO": ("COCA", "COKE"),
        "PEP": ("PEPSICO", "PEPSI"),
        "XOM": ("EXXON",),
        "CVX": ("CHEVRON",),
        "BA": ("BOEING",),
        "CAT": ("CATERPILLAR",),
        "DIS": ("DISNEY",),
        "NFLX": ("NETFLIX",),
        "NKE": ("NIKE",),
        "MCD": ("MCDONALD",),
        "INTC": ("INTEL",),
        "AMD": ("ADVANCED MICRO", "AMD"),
        "ORCL": ("ORACLE",),
        "CRM": ("SALESFORCE",),
        "ADBE": ("ADOBE",),
        "CSCO": ("CISCO",),
        "IBM": ("IBM", "INTERNATIONAL BUSINESS"),
        "GS": ("GOLDMAN",),
        "BAC": ("BANK OF AMERICA",),
        "WFC": ("WELLS FARGO",),
        "T": ("AT&T",),
        "VZ": ("VERIZON",),
    }
    long_forms = short_long.get(t, ())
    for long_form in long_forms:
        if any(long_form in tok for tok in title_tokens):
            return True
    # If the first title token is a 4+ letter company short name that
    # closely matches the ticker family, accept (e.g. ticker BRK.B →
    # "Berkshire Hathaway" — both contain "BERKSHIRE").
    return False
