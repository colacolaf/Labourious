"""
snippets.py — first-2 KB snippet cache for citation chips.

When a connector returns text-heavy data (SEC full-text filings,
8-K rows, transcripts) we want to write a small excerpt to disk so
the chip's ``v`` key handler can pop the snippet into ``less``/``bat``
without re-fetching the network. This module owns that write path.

The function is deliberately side-effect-isolated and idempotent:

    write_snippet_for(tr: ToolResult, run_id: str, idx: int) -> Path | None

- Returns ``None`` if ``tr.status != SUCCESS`` (failure/empty skips the
  write — chips ``v`` key will report no snippet).
- Returns the written/read ``Path`` if a snippet was written (or
  already existed).
- Always uses the same on-disk shape: ``<RUNS_DIR>/<run_id>/
  snippets/<safe_source>_<idx>.txt`` — ``safe_source`` slashes-filter
  the source name so SEC + ticker + form reads cleanly.
- 2 KB cap is enforced on the excerpt. The path is in scope even if
  ``RUNS_DIR`` does not yet exist; we ``mkdir(parents=True)`` on demand.
- Idempotent: a second call with the same ``(run_id, source, idx)``
  does not rewrite the file. Useful so re-running a flow doesn't
  thrash the snippet cache.

Three responsibilities kept here, none elsewhere:

1. Excerpt construction from arbitrary ToolResult.data shapes.
2. Path derivation + filesystem write.
3. The "safe_source" slug that adapts ``sec_edgar_fulltext`` etc.
   to a filename-safe form.

The chip action layer (CitationChip, ChatScreen, frontend.utils.
platform) reads the ``snippet_path`` field but never writes the file.

Tests in ``docs/runtime/smokes/snippet_cache_smoke.py`` exercise
all three responsibilities end-to-end against a tokened temp dir.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 2 KB cap — the chip's `v` action pops this into `less`/`bat` and
# we want it readable in one screen. Bigger excerpts would scroll;
# smaller doesn't give the reviewer enough to ground the citation.
MAX_SNIPPET_BYTES = 2048


@dataclass(frozen=True)
class SnippetPath:
    """Resolved location of a snippet on disk + cap/size metadata."""
    path: Path
    bytes_written: int
    truncated: bool
    new_write: bool  # True if THIS call wrote the file; False if pre-existing

    def __str__(self) -> str:        # pragma: no cover
        return str(self.path)


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


def _excerpt_from_data(data: Any, cap_bytes: int = MAX_SNIPPET_BYTES) -> tuple[str, bool]:
    """Render ``ToolResult.data`` into a capped text excerpt.

    Returns ``(text, truncated)`` — text is plain UTF-8, no JSON for
    the common case. We pick:

    - ``dict``         → ``str(data)`` (dataclass-ish), or join key/val pairs
    - ``list[dict]``   → tab-separated key/value rows, capped
    - ``list[str]``    → newline-joined strings, capped
    - ``str``          → slice to cap_bytes
    - ``None``         → "" (no excerpt)

    Truncation sets the trailing ``\n[truncated @ N bytes]`` marker so
    reviewers can see in `less` they're not seeing the whole thing.
    """
    if data is None:
        return "", False

    # Render dict-style shapes via pretty-printed JSON so it stays
    # parseable in less — but cap aggressively since JSON is verbose.
    if isinstance(data, dict):
        try:
            text = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            text = str(data)
        if len(text.encode("utf-8")) > cap_bytes:
            text = text.encode("utf-8")[:cap_bytes].decode("utf-8", errors="replace")
            return text + "\n[truncated @ 2048 bytes]", True
        return text, False

    # List-shaped data — the most common case for sec_edgar/news8k/transcripts.
    if isinstance(data, list):
        if not data:
            return "(empty list)", False
        lines: list[str] = []
        running = 0
        truncated = False
        for i, item in enumerate(data):
            if isinstance(item, dict):
                # One compact line per item: prefer a few stable fields
                # if present (typical EFTS shape), fall back to hash-map.
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

    # Fallback: stringify (numbers, dataclasses, etc.)
    text = str(data)
    if len(text.encode("utf-8")) > cap_bytes:
        return text.encode("utf-8")[:cap_bytes].decode("utf-8", errors="replace") + \
            "\n[truncated @ 2048 bytes]", True
    return text, False


def snippet_for(tr: Any, run_id: str, idx: int,
                *, base_dir: Path | None = None) -> SnippetPath | None:
    """Return a cached snippet for *tr* or ``None`` if not succeeded.

    This is the read-only shape callers should use when they want the
    resolved ``Path``. If the file doesn't already exist we do NOT
    write it here — see ``write_snippet_for`` for the write path that
    matches your connector flow.
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
    return SnippetPath(
        path=path,
        bytes_written=size,
        truncated=size >= MAX_SNIPPET_BYTES,
        new_write=False,
    )


def write_snippet_for(tr: Any, run_id: str, idx: int,
                      *, base_dir: Path | None = None,
                      force: bool = False) -> SnippetPath | None:
    """Write a snippet for ``tr`` if it's a SUCCESS-shaped result.

    Returns the resolved SnippetPath on success, ``None`` if the
    result wasn't eligible (FAILED / EMPTY / None). Idempotent:
    default behaviour doesn't rewrite an existing file. Pass
    ``force=True`` to overwrite.
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
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        size = path.stat().st_size
        return SnippetPath(
            path=path,
            bytes_written=size,
            truncated=size >= MAX_SNIPPET_BYTES,
            new_write=False,
        )
    excerpt, truncated = _excerpt_from_data(getattr(tr, "data", None))
    raw = excerpt.encode("utf-8")
    if len(raw) > MAX_SNIPPET_BYTES:
        raw = raw[:MAX_SNIPPET_BYTES]
    path.write_bytes(raw)
    return SnippetPath(
        path=path,
        bytes_written=len(raw),
        truncated=truncated,
        new_write=True,
    )


# Re-export for tests / call sites that want to manage the base dir.
__all__ = [
    "MAX_SNIPPET_BYTES",
    "RUNS_DIR",
    "SnippetPath",
    "_safe_source",
    "_excerpt_from_data",
    "snippet_for",
    "write_snippet_for",
]
