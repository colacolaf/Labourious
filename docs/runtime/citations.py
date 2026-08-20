"""
citations.py — "lawyer-grade citation" layer.

When the agent emits a citation that points at a raw URL (a vendor
press release, an analyst-hosted PDF link, a Reuters/Bloomberg
article), the citation chip *would* show ◫ for snippet and the
reviewer's ``v`` key would surface the cached excerpt — but only if a
snippet is on disk. The connector-shaped citations (sec_edgar_fulltext,
news_8k, transcripts) populate snippets via ``snippets.write_snippet_for``
every run. Raw URLs *don't* — they were the citation modal's long tail:
visible, but unverifiable.

This module closes that tail. For each unique URL in a run we:

1. Hash the URL into a stable, filesystem-safe filename.
2. Check the snippet cache: ``<RUNS_DIR>/<run_id>/snippets/web_<key>.txt``.
3. If fresh under the per-source TTL → return existing path.
4. Else → fetch via ``web_fetch.fetch(url)`` and write the first
    4 KiB excerpt of the page (HTML stripped to plain text).

Reuse the same meta-sidecar shape as ``snippets.py`` so the chip's
existing freshness probe (``.is_stale``) and ETag detection work
identically — chips with `web_<key>` snippets light up `` ◫``
and the per-citation badge falls in line.

Two non-trivial bits:

- **In-memory dedupe**: ``ensure_snippet_for_url`` keeps a process-wide
  cache so the same URL clicked twice in one session never doubles the
  network round-trip. The lifetime is the process — across runs the
  disk-side TTL is the gate.
- **Background-thread friendly**: the helpers are sync. Chat/screens
  wrap with ``asyncio.to_thread``; tests wrap with a direct call.

Failure modes — all return ``(None, error)`` instead of raising:

- ``HTTPError`` / network down       → ``(None, "HTTP ..." )``
- empty body / decode failure        → ``(None, "empty decode" )``
- non-2xx response                   → ``(None, "HTTP ..." )``
- any other unhandled exception     → ``(None, "<type>: <msg>" )``

The pilot ``docs/runtime/smokes/citation_hard_smoke.py`` exercises
each path; chip integration is asserted with real CitationChip
``request_view()`` returning the populated snippet path.
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


# Reuse snippets.py primitives so the chip's freshness probe works
# without touching the per-URL files differently from per-connector
# files. ``MAX_SNIPPET_BYTES`` from snippets.py is 2 KiB; for the
# lawyer-grade layer we want a slightly larger cap so reviewers can
# ground multi-sentence claims. 4 KiB is the TODO default.
MAX_URL_SNIPPET_BYTES = 4096

# Default TTL for URL-snippet cache: shorter than connectors because
# we have no `as_of` from web_fetch to gate on. 6 h is the sweet spot
# for press releases + transcripts-host pages + analyst PDFs.
URL_TTL_S = 6 * 3600


# -----------------------------------------------------------------------
# Time provider — mirrors snippets.py so the same `SNIPPET_NOW_OVERRIDE_S`
# trick works for tests.
# -----------------------------------------------------------------------
def _now_s() -> float:
    override = os.environ.get("CITATION_NOW_OVERRIDE_S")
    if override is None and "CITATION_NOW_OVERRIDE_S" not in os.environ:
        override = os.environ.get("SNIPPET_NOW_OVERRIDE_S")
    if override is not None:
        try:
            return float(override)
        except ValueError:
            pass
    return time.time()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


RUNS_DIR = _project_root() / "docs" / "runtime" / ".runs"


# -----------------------------------------------------------------------
# Path helpers
# -----------------------------------------------------------------------
def _url_key(url: str) -> str:
    """Stable, collision-resistant filename-safe slug for *url*.

    Shape: ``<safe_host>__<sha1-12>``. ``<safe_host>`` so two articles
    on the same host share a prefix (UI sortable). ``<sha1-12>`` so
    URL variants (different slugs, query params, anchor fragments) that
    resolve to the same page share a snippet. Always returns a
    non-empty string.
    """
    try:
        host = (urlparse(url).hostname or "unknown").lower()
    except Exception:
        host = "unknown"
    if host.startswith("www."):
        host = host[4:]
    safe_host = re_slugify(host)[:48] or "unknown"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"{safe_host}__{digest}"


def re_slugify(s: str) -> str:
    """Inline slugifier: ``[a-z0-9_-]`` kept, rest replaced with ``_``."""
    import re
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s or "").strip("_").lower()


def _snippet_path_for(url: str, run_id: str, *, base_dir: Optional[Path] = None) -> Path:
    base = Path(base_dir) if base_dir else RUNS_DIR
    safe = _url_key(url)
    return base / run_id / "snippets" / f"web_{safe}.txt"


# -----------------------------------------------------------------------
# Process-wide dedupe (per-resolved-URL). Same URL clicked twice does
# not double-fetch. This dict is module-level so the chat screen and
# the modal screen share the dedupe window without explicit plumbing.
# -----------------------------------------------------------------------
_FETCH_CACHE: dict[str, tuple[float, Path | None, str | None]] = {}
_FETCH_LOCK = threading.Lock()


@dataclass(frozen=True)
class EnsureResult:
    """Outcome of ``ensure_snippet_for_url``.

    All fields populated regardless of success: a failed fetch has
    ``path=None`` and ``error=<reason>``. ``new_write`` is True if
    *this* call actually fetched + wrote. ``bytes_written`` is 0 on
    failure and the on-disk size on success.
    """
    url: str
    path: Optional[Path]
    new_write: bool
    bytes_written: int
    error: Optional[str]


# -----------------------------------------------------------------------
# Read paths
# -----------------------------------------------------------------------
def snippet_path_for_url(url: str, run_id: str, *,
                         base_dir: Optional[Path] = None) -> Optional[Path]:
    """Return the on-disk path for *url* if a snippet exists, else None.

    Read-only. Pure stat; does NOT fetch. Used by chat.py on remount
    so chips re-discover prior snippets across screen pushes.
    """
    p = _snippet_path_for(url, run_id, base_dir=base_dir)
    return p if p.exists() else None


def is_snippet_fresh(path: Path) -> bool:
    """True if the cached snippet is still under its TTL window.

    Mirrors snippets.is_stale but for the URL-shaped cache. We re-use
    the meta sidecar format so the same JSON shape works.
    """
    try:
        from runtime.snippets import snippet_metadata_for
    except Exception:
        return False
    meta = snippet_metadata_for(path)
    if meta is None:
        # No sidecar — be conservative; play fresh so the chip doesn't
        # flash ⚠ on a malformed meta file.
        return True
    return not meta.is_stale(_now_s())


# -----------------------------------------------------------------------
# Write path (the meat of the lawyer-grade cache)
# -----------------------------------------------------------------------
def ensure_snippet_for_url(
    url: str,
    run_id: str,
    *,
    requested_by_agent: str | None = None,
    base_dir: Optional[Path] = None,
    force: bool = False,
) -> EnsureResult:
    """Ensure a snippet for *url* exists in the run's cache.

    If the snippet is already on disk and still under its TTL window
    (or already-fetched-flagged in the in-memory dedupe), returns
    the existing path with ``new_write=False``. Otherwise fetches
    via ``runtime.tools.web_fetch.WebFetchTool.fetch`` and writes
    ``MAX_URL_SNIPPET_BYTES`` of plain text to the cache.

    Returns an ``EnsureResult`` with ``path`` populated on success
    and ``error`` populated on failure. Never raises.
    """
    if not url:
        return EnsureResult(url=url, path=None, new_write=False,
                            bytes_written=0, error="empty url")
    path = _snippet_path_for(url, run_id, base_dir=base_dir)

    # ----- Disk cache read (sync, no I/O) -----
    if not force and path.exists():
        try:
            from runtime.snippets import snippet_metadata_for
            meta = snippet_metadata_for(path)
        except Exception:
            meta = None
        if meta is None or not meta.is_stale(_now_s()):
            # Disk hit — record in the in-memory cache and return.
            with _FETCH_LOCK:
                _FETCH_CACHE[url] = (_now_s(), path, None)
            return EnsureResult(url=url, path=path, new_write=False,
                                bytes_written=path.stat().st_size, error=None)

    # ----- In-memory dedupe -----
    with _FETCH_LOCK:
        cached = _FETCH_CACHE.get(url)
        if cached is not None:
            ts, cached_path, err = cached
            # If the prior call's result is still on disk AND the row
            # hasn't been invalidated, return that pointer.
            if cached_path is not None and cached_path.exists():
                return EnsureResult(url=url, path=cached_path, new_write=False,
                                    bytes_written=cached_path.stat().st_size,
                                    error=None)
            # Prior call failed and the failure is still within a
            # short retry window (5 min) — don't hammer upstream.
            if cached_path is None and (err is not None) and (_now_s() - ts) < 300:
                return EnsureResult(url=url, path=None, new_write=False,
                                    bytes_written=0, error=err)

    # ----- Actual fetch -----
    yielded_path: Path | None = None
    yielded_error: str | None = None
    yielded_bytes = 0
    try:
        from runtime.tools.web_fetch import WebFetchTool
        tool = WebFetchTool(max_chars=MAX_URL_SNIPPET_BYTES)
        tr = tool.fetch(url)
    except Exception as e:
        yielded_error = f"{type(e).__name__}: {e}".strip()
    else:
        status = getattr(tr, "status", "FAILED")
        if status != "SUCCESS":
            note = getattr(tr, "note", "") or ""
            yielded_error = note or f"web_fetch returned {status}"
        else:
            data = getattr(tr, "data", None) or {}
            text = data.get("text", "") if isinstance(data, dict) else ""
            if not text:
                yielded_error = "empty decode"
            else:
                raw = text.encode("utf-8")[:MAX_URL_SNIPPET_BYTES]
                truncated = len(text.encode("utf-8")) > MAX_URL_SNIPPET_BYTES
                if truncated:
                    snippet = raw.decode("utf-8", errors="replace") + "\n[truncated @ 4096 bytes]"
                else:
                    snippet = raw.decode("utf-8", errors="replace")
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(snippet, encoding="utf-8")
                    # Write meta sidecar matching snippets.py shape so
                    # chip's freshness probe is identical to connector paths.
                    from runtime.snippets import SnippetMetadata
                    meta = SnippetMetadata(
                        written_at=_now_s(),
                        source="url_snippet",
                        bytes_written=len(raw),
                        ttl_seconds=URL_TTL_S,
                        truncated=truncated,
                        cached_as_of=getattr(tr, "as_of", "") or None,
                        cached_etag=getattr(tr, "etag", None),
                    )
                    meta_path = path.with_suffix(path.suffix + ".meta.json")
                    meta_path.write_text(meta.to_json(), encoding="utf-8")
                    yielded_path = path
                    yielded_bytes = len(raw)
                except Exception as e:
                    yielded_error = f"disk write failed: {type(e).__name__}: {e}"

    # ----- Update dedupe -----
    with _FETCH_LOCK:
        _FETCH_CACHE[url] = (_now_s(), yielded_path, yielded_error)

    return EnsureResult(url=url, path=yielded_path, new_write=(yielded_path is not None),
                        bytes_written=yielded_bytes, error=yielded_error)


def clear_dedupe() -> None:
    """Reset the in-memory fetch cache.

    Tests use this between scenarios so prior fetches do not bleed
    into a new scenario. Disk cache is untouched — the on-disk cache
    is governed by ``url_snippet`` TTL.
    """
    with _FETCH_LOCK:
        _FETCH_CACHE.clear()


__all__ = [
    "MAX_URL_SNIPPET_BYTES",
    "URL_TTL_S",
    "RUNS_DIR",
    "EnsureResult",
    "snippet_path_for_url",
    "is_snippet_fresh",
    "ensure_snippet_for_url",
    "clear_dedupe",
    "_url_key",
]
