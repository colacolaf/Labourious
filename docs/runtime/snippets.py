"""
snippets.py — first-2 KB snippet cache for citation chips. Now TTL-aware.

When a connector returns text-heavy data (SEC full-text filings,
8-K rows, transcripts) we want to write a small excerpt to disk so
the chip's ``v`` key handler can pop the snippet into ``less``/``bat``
without re-fetching the network. This module owns that write path.

The function is deliberately side-effect-isolated and TTL-aware:

    write_snippet_for(tr, run_id, idx) -> SnippetPath | None

Behaviour:
- Returns ``None`` if ``tr.status != SUCCESS`` (failure/empty skips the
  write — chips ``v`` key will report no snippet).
- Returns the read/written ``SnippetPath`` if a snippet was written
  (or already existed AND is fresh under the TTL).
- If a cached snippet exists and is **still within its TTL window**,
  the rewrite is skipped (``new_write=False``, ``refreshed=False``).
  Per-source freshness needs:
      * news_8k     — 1 h   (filings are time-sensitive)
      * sec_edgar_fulltext — 24 h (filing amendments settle within a day)
      * transcripts — 7 d   (call transcripts only change Q-on-Q)
      * default     — 24 h
- If a cached snippet is **stale** (TTL elapsed), the next call
  rewrites it. The caller always gets the fresh snippet.
- ``force=True`` or ``force_refresh(path)`` override the TTL entirely.

The on-disk shape:
    `<RUNS_DIR>/<run_id>/snippets/<safe_source>_<idx>.txt` — content
    `<RUNS_DIR>/<run_id>/snippets/<safe_source>_<idx>.meta.json` — metadata
        {
          "written_at": 1234567890.0,            (epoch seconds, local cache time)
          "source": "sec_edgar_fulltext",
          "bytes_written": 1620,
          "ttl_seconds": 86400,
          "truncated": false,
          "cached_as_of": "2026-08-19T17:59:55Z" (upstream's as_of at last write)
        }

As-of-equals freshness ([domain-6]): in addition to the wallclock
TTL gate, ``write_snippet_for`` will refresh a cached snippet when
the upstream ``ToolResult.as_of`` is strictly *later* than what
the cache recorded (sidecar's ``cached_as_of`` field). This handles
the case where the same ticker publishes a successor 8-K later in
the same day — the cache should pick up the new filing on the
next connector call, even if the wallclock TTL hasn't elapsed.

ISO-8601 timestamps (``...Z`` or ``+00:00``) compare correctly
lexicographically when both use the same offset. The gate uses a
strict ``>`` so an equal ``as_of`` falls back to the TTL check.
We deliberately do NOT downgrade the cache when ``as_of`` regresses
(a stale response with an older timestamp doesn't lose what we have).

Two responsibilities kept here, none elsewhere:

1. Excerpt construction from arbitrary ToolResult.data shapes (capped).
2. Path derivation + filesystem write + TTL metadata sidecar.

The chip action layer (CitationChip, ChatScreen, frontend.utils.
platform) reads the snippet_path but never writes the file. The chip's
``v`` action pops the file into ``less``/``bat``. The chip's label
shows `` ◫`` (fresh) or ``⚠ ◫`` (stale) so reviewers notice when a
snippet is past its freshness window.

Tests in ``docs/runtime/smokes/snippet_cache_smoke.py`` (write path)
and ``docs/runtime/smokes/snippet_ttl_smoke.py`` (TTL/refreshing).
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# 2 KB cap — the chip's `v` action pops this into `less`/`bat` and
# we want it readable in one screen. Bigger excerpts would scroll;
# smaller doesn't give the reviewer enough to ground the citation.
MAX_SNIPPET_BYTES = 2048

# Default TTL if no per-source rule matches. 24 h is the sweet spot:
# long enough to dedupe same-day re-runs, short enough to catch
# filings on the next day.
DEFAULT_TTL_S = 86_400

# Per-source TTL overrides (in seconds). Edit conservatively:
# shortening means more network traffic on re-runs; lengthening means
# older snippets persist between real runs and reviewers might believe
# stale data. The connectors page-load with the network anyway.
SOURCE_TTL: dict[str, int] = {
    "news_8k":              3_600,    # 1 hour — 8-Ks are timing-critical
    "sec_edgar_fulltext":  86_400,    # 24 hours — amendments settle within a day
    "transcripts":        604_800,    # 7 days — earnings calls only refresh Q-on-Q
}


# ---------------------------------------------------------------------------
# Time provider — exposed so tests can fast-forward without sleeping.
# ``time.monotonic`` would be wrong (skips backwards on clock changes);
# ``os.environ.get(...)`` injection lets us simulate elapsed time in
# pilots. Default is wallclock seconds since epoch.
# ---------------------------------------------------------------------------
def _now_s() -> float:
    """Return current wallclock seconds since epoch (UTC).

    Override via ``SNIPPET_NOW_OVERRIDE_S=<float>`` for tests so we can
    assert after-TTL behaviour without sleeping.
    """
    override = os.environ.get("SNIPPET_NOW_OVERRIDE_S")
    if override is not None:
        try:
            return float(override)
        except ValueError:
            pass
    return time.time()


def _resolve_ttl(source: str) -> int:
    """Resolve the effective TTL for *source* honoring env overrides.

    Precedence (highest first):
      1. ``SNIPPET_TTL_<UPPER_SOURCE>_S`` env var for the specific source
      2. ``SOURCE_TTL[source]`` (per-source table)
      3. ``SNIPPET_DEFAULT_TTL_S`` (global env override)
      4. ``DEFAULT_TTL_S`` (hard-coded fallback)
    """
    # 1. Per-source env override.
    env_key = f"SNIPPET_TTL_{source.upper().replace('-', '_')}_S"
    override = os.environ.get(env_key)
    if override is not None:
        try:
            return int(override)
        except ValueError:
            pass
    # 2. Per-source table.
    if source in SOURCE_TTL:
        return SOURCE_TTL[source]
    # 3. Global env override.
    global_override = os.environ.get("SNIPPET_DEFAULT_TTL_S")
    if global_override is not None:
        try:
            return int(global_override)
        except ValueError:
            pass
    # 4. Hard-coded fallback.
    return DEFAULT_TTL_S


def _project_root() -> Path:
    """Repo root. snippets.py lives at docs/runtime/snippets.py — so
    parent.parents[2] is the repo root."""
    return Path(__file__).resolve().parents[2]


RUNS_DIR = _project_root() / "docs" / "runtime" / ".runs"


def _safe_source(source: str) -> str:
    """Slugify ``sec_edgar_fulltext`` etc. to a filename-safe form.

    Strict: only [a-z0-9_-] pass. Empty after filter → 'unknown'.
    """
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", source or "").strip("_")
    return (s.lower() or "unknown")[:48]


def _meta_path_for(content_path: Path) -> Path:
    """Sidecar metadata file path: <path>.meta.json."""
    return content_path.with_suffix(content_path.suffix + ".meta.json")


def _excerpt_from_data(data: Any, cap_bytes: int = MAX_SNIPPET_BYTES) -> tuple[str, bool]:
    """Render ``ToolResult.data`` into a capped text excerpt.

    Returns ``(text, truncated)`` — text is plain UTF-8, no JSON for
    the common case. We pick:

    - ``dict``         → JSON-printed, capped
    - ``list[dict]``   → tab-separated key/value rows, capped
    - ``list[str]``    → newline-joined strings, capped
    - ``str``          → slice to cap_bytes
    - ``None``         → "" (no excerpt)

    Truncation sets the trailing ``\n[truncated @ N bytes]`` marker so
    reviewers can see in `less` they're not seeing the whole thing.
    """
    if data is None:
        return "", False
    if isinstance(data, dict):
        try:
            text = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            text = str(data)
        if len(text.encode("utf-8")) > cap_bytes:
            text = text.encode("utf-8")[:cap_bytes].decode("utf-8", errors="replace")
            return text + "\n[truncated @ 2048 bytes]", True
        return text, False
    if isinstance(data, list):
        if not data:
            return "(empty list)", False
        lines: list[str] = []
        running = 0
        truncated = False
        for i, item in enumerate(data):
            if isinstance(item, dict):
                parts: list[str] = []
                for k in ("adsh", "form", "filing_date", "company",
                          "headline", "ticker", "cik", "url", "summary"):
                    if k in item and item[k]:
                        parts.append(f"{k}={item[k]}")
                if parts:
                    line = "\t".join(parts)
                else:
                    line = json.dumps(item, default=str, ensure_ascii=False)
            else:
                line = str(item)
            line_bytes = len(line.encode("utf-8")) + 1
            if running + line_bytes > cap_bytes and i > 0:
                truncated = True
                lines.append(f"[{len(data) - i} more rows truncated]")
                break
            lines.append(line)
            running += line_bytes
        text = "\n".join(lines)
        if truncated:
            text += "\n[truncated @ 2048 bytes]"
        return text, truncated
    if isinstance(data, str):
        if len(data.encode("utf-8")) > cap_bytes:
            truncated = True
            return data.encode("utf-8")[:cap_bytes].decode("utf-8", errors="replace") + \
                "\n[truncated @ 2048 bytes]", True
        return data, False
    text = str(data)
    if len(text.encode("utf-8")) > cap_bytes:
        return text.encode("utf-8")[:cap_bytes].decode("utf-8", errors="replace") + \
            "\n[truncated @ 2048 bytes]", True
    return text, False


# ---------------------------------------------------------------------------
# Result dataclasses — frozen, both feed the chip's UI layer
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SnippetMetadata:
    """Sidecar metadata for a single cached snippet."""
    written_at: float                          # epoch seconds, local cache time
    source: str
    bytes_written: int
    ttl_seconds: int
    truncated: bool = False
    cached_as_of: str | None = None            # upstream's as_of at last write

    def age_seconds(self, now_s: float | None = None) -> float:
        return (now_s if now_s is not None else _now_s()) - self.written_at

    def is_stale(self, now_s: float | None = None) -> bool:
        return self.age_seconds(now_s) >= self.ttl_seconds

    def ttl_remaining_s(self, now_s: float | None = None) -> float:
        return max(0, self.ttl_seconds - self.age_seconds(now_s))

    def to_json(self) -> str:
        return json.dumps({
            "written_at": self.written_at,
            "source": self.source,
            "bytes_written": self.bytes_written,
            "ttl_seconds": self.ttl_seconds,
            "truncated": self.truncated,
            "cached_as_of": self.cached_as_of,
        }, indent=2)

    @staticmethod
    def from_json(s: str) -> "SnippetMetadata":
        d = json.loads(s)
        return SnippetMetadata(
            written_at=float(d["written_at"]),
            source=str(d["source"]),
            bytes_written=int(d["bytes_written"]),
            ttl_seconds=int(d["ttl_seconds"]),
            truncated=bool(d.get("truncated", False)),
            cached_as_of=d.get("cached_as_of"),
        )


@dataclass(frozen=True)
class SnippetPath:
    """Resolved location of a snippet on disk + cap/size metadata.

    Fields:
        path            : on-disk content path (.txt)
        bytes_written   : byte count on disk
        truncated       : True if the excerpt was capped at 2 KB
        new_write       : True if THIS call wrote the content (False
                          if it was already there and is fresh under
                          the source-TTL window)
        metadata        : SnippetMetadata or None if missing sidecar
    """
    path: Path
    bytes_written: int
    truncated: bool
    new_write: bool
    metadata: SnippetMetadata | None = None

    @property
    def is_stale(self) -> bool:
        """True if the cached snippet's TTL has elapsed.

        Returns True when there is no metadata sidecar or when
        ``now - written_at >= ttl_seconds``. ``SnippetPath`` is the
        union of "content exists" + "metadata tells me how fresh".
        The chip uses this to flip `` ◫`` → ``⚠ ◫`` in its label.
        """
        if self.metadata is None:
            return False     # unknown freshness; show fresh badge
        return self.metadata.is_stale()

    def ttl_remaining_s(self) -> float:
        if self.metadata is None:
            return 0.0
        return self.metadata.ttl_remaining_s()

    def __str__(self) -> str:        # pragma: no cover
        return str(self.path)


# ---------------------------------------------------------------------------
# Read paths (no I/O beyond stat)
# ---------------------------------------------------------------------------
def snippet_metadata_for(content_path: Path | str) -> SnippetMetadata | None:
    """Read the metadata sidecar for *content_path* (or `None` if absent/corrupt)."""
    p = Path(content_path)
    meta = _meta_path_for(p)
    if not meta.exists():
        return None
    try:
        return SnippetMetadata.from_json(meta.read_text(encoding="utf-8"))
    except Exception:
        return None


def snippet_for(tr: Any, run_id: str, idx: int,
                *, base_dir: Path | None = None) -> SnippetPath | None:
    """Return a cached snippet for *tr* or ``None`` if not succeeded.

    Read-only — does NOT write a snippet if missing. Returns a
    SnippetPath whose ``metadata`` is filled in if the sidecar exists
    so callers can check ``is_stale``.
    """
    if tr is None:
        return None
    status = getattr(tr, "status", "")
    if status != "SUCCESS":
        return None
    source = getattr(tr, "source", "") or "unknown"
    safe = _safe_source(source)
    base = Path(base_dir) if base_dir else RUNS_DIR
    path = base / run_id / "snippets" / f"{safe}_{idx}.txt"
    if not path.exists():
        return None
    size = path.stat().st_size
    metadata = snippet_metadata_for(path)
    truncated = metadata.truncated if metadata else (size >= MAX_SNIPPET_BYTES)
    return SnippetPath(
        path=path,
        bytes_written=size,
        truncated=truncated,
        new_write=False,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Write paths (TTL-gated)
# ---------------------------------------------------------------------------
def _iso_compare(a: str | None, b: str | None) -> int:
    """Compare two ISO-8601 strings, normalizing 'Z' to '+00:00'.

    Returns -1 / 0 / +1 like a strcmp, with ``None`` sorted last
    (``None`` is "unknown" so never wins). Compares on the same
    UTC offset when both are convertible; otherwise falls back to
    string compare (works for Z-suffixed timestamps which sort
    correctly in lexicographic order).
    """
    def norm(v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return s
    na, nb = norm(a), norm(b)
    if na is None and nb is None:
        return 0
    if na is None:
        return 1   # unknown is "less than"
    if nb is None:
        return -1
    if na < nb:
        return -1
    if na > nb:
        return 1
    return 0


def write_snippet_for(tr: Any, run_id: str, idx: int,
                      *, base_dir: Path | None = None,
                      force: bool = False) -> SnippetPath | None:
    """Write a snippet for ``tr`` if eligible AND not still fresh.

    Returns the resolved SnippetPath on success, ``None`` if the
    result wasn't eligible (FAILED / EMPTY / None).

    TWO refresh gates, in order:
      1. **TTL gate**: cached snippet's ``age >= ttl_seconds``?
         Yes → refresh.
      2. **as-of gate** ([domain-6]): ``ToolResult.as_of`` strictly
         later than cached snippet's ``cached_as_of``? Yes → refresh.
         Catches the case where a successor filing appears within
         the wallclock TTL window.

    Either gate firing → refresh. Neither firing → return cached
    SnippetPath with ``new_write=False``. ``force=True`` skips both
    gates entirely (used by tests + ops).
    """
    if tr is None:
        return None
    status = getattr(tr, "status", "")
    if status != "SUCCESS":
        return None
    source = getattr(tr, "source", "") or "unknown"
    safe = _safe_source(source)
    base = Path(base_dir) if base_dir else RUNS_DIR
    path = base / run_id / "snippets" / f"{safe}_{idx}.txt"
    meta_path = _meta_path_for(path)
    ttl = _resolve_ttl(source)
    now_s = _now_s()

    # === Both gates ===
    if not force and path.exists() and meta_path.exists():
        try:
            meta = SnippetMetadata.from_json(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = None
        if meta is not None:
            ttl_fresh = not meta.is_stale(now_s)
            # as-of gate: skip refresh if cached_as_of is missing,
            # equal, or *later* than the new ToolResult.as_of.
            tr_as_of = getattr(tr, "as_of", "") or ""
            asof_fresh = (_iso_compare(tr_as_of, meta.cached_as_of) <= 0)
            if ttl_fresh and asof_fresh:
                size = path.stat().st_size
                return SnippetPath(
                    path=path,
                    bytes_written=size,
                    truncated=meta.truncated,
                    new_write=False,
                    metadata=meta,
                )
            # else: at least one gate wants a refresh — fall through.

    # === Write path ===
    path.parent.mkdir(parents=True, exist_ok=True)
    excerpt, truncated = _excerpt_from_data(getattr(tr, "data", None))
    raw = excerpt.encode("utf-8")
    if len(raw) > MAX_SNIPPET_BYTES:
        raw = raw[:MAX_SNIPPET_BYTES]
    path.write_bytes(raw)
    metadata = SnippetMetadata(
        written_at=now_s,
        source=source,
        bytes_written=len(raw),
        ttl_seconds=ttl,
        truncated=truncated,
        cached_as_of=getattr(tr, "as_of", "") or None,
    )
    meta_path.write_text(metadata.to_json(), encoding="utf-8")
    return SnippetPath(
        path=path,
        bytes_written=len(raw),
        truncated=truncated,
        new_write=True,
        metadata=metadata,
    )


def force_refresh(path: Path | str, *,
                  new_excerpt_text: str | None = None,
                  new_metadata_overrides: dict[str, Any] | None = None,
                  base_dir: Path | None = None) -> SnippetPath:
    """Force-refresh a snippet, bypassing any TTL gate.

    If ``new_excerpt_text`` is given, it's written to the content
    file. If omitted, the existing content is kept (only metadata's
    ``written_at`` is bumped). Useful when the caller wants to bump
    freshness without a real fetch (or after a manual edit).

    Returns a SnippetPath with ``new_write=True`` always.
    """
    p = Path(path)
    meta_p = _meta_path_for(p)
    if not p.exists():
        raise FileNotFoundError(f"snippet not found: {p}")
    if new_excerpt_text is not None:
        raw = new_excerpt_text.encode("utf-8")
        if len(raw) > MAX_SNIPPET_BYTES:
            raw = raw[:MAX_SNIPPET_BYTES]
        p.write_bytes(raw)
    size = p.stat().st_size
    existing_meta = snippet_metadata_for(p)
    if existing_meta is None:
        # Synthesize a meta if missing — best-effort recovery.
        existing_meta = SnippetMetadata(
            written_at=_now_s(),
            source=p.stem.split("_")[0] if "_" in p.stem else "unknown",
            bytes_written=size,
            ttl_seconds=DEFAULT_TTL_S,
            truncated=size >= MAX_SNIPPET_BYTES,
        )
    overrides = new_metadata_overrides or {}
    new_meta = SnippetMetadata(
        written_at=overrides.get("written_at", _now_s()),
        source=overrides.get("source", existing_meta.source),
        bytes_written=overrides.get("bytes_written", size),
        ttl_seconds=overrides.get("ttl_seconds", existing_meta.ttl_seconds),
        truncated=overrides.get("truncated", existing_meta.truncated),
        cached_as_of=overrides.get("cached_as_of", existing_meta.cached_as_of),
    )
    meta_p.write_text(new_meta.to_json(), encoding="utf-8")
    return SnippetPath(
        path=p,
        bytes_written=size,
        truncated=new_meta.truncated,
        new_write=True,
        metadata=new_meta,
    )


# Re-export for tests / call sites that want to manage the base dir.
__all__ = [
    "DEFAULT_TTL_S",
    "MAX_SNIPPET_BYTES",
    "RUNS_DIR",
    "SOURCE_TTL",
    "SnippetMetadata",
    "SnippetPath",
    "_now_s",
    "_resolve_ttl",
    "_safe_source",
    "_excerpt_from_data",
    "force_refresh",
    "snippet_for",
    "snippet_metadata_for",
    "write_snippet_for",
]
