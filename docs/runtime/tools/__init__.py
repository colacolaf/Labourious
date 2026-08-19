# tools/__init__.py — package init for runtime tool adapters.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


# Status sentinels (string constants for ``ToolResult.status``).
STATUS_SUCCESS   = "SUCCESS"
STATUS_PARTIAL   = "PARTIAL"
STATUS_FAILED    = "FAILED"
STATUS_EMPTY     = "EMPTY"
# [domain-7] — UNCHANGED: the connector's signal that the upstream
# returned 304 Not Modified after a conditional GET. Tells the
# snippet cache the cached version is still current (no rewrite).
# Carries ``note`` like "ETag matched: 304 Not Modified".
STATUS_UNCHANGED = "UNCHANGED"


@dataclass
class ToolResult:
    status: str  # SUCCESS | PARTIAL | FAILED | EMPTY | UNCHANGED
    data: Any
    as_of: str
    source: str
    note: str = ""
    # Optional: absolute path to a cached snippet in `.runs/<run_id>/
    # snippets/<source>_<idx>.txt`. Populated by the runtime layer
    # (write_snippet_for) for SUCCESS results from text-heavy
    # connectors (sec_edgar_fulltext, news_8k, transcripts). The
    # chip's `v` action reads this and opens the file in `less`/`bat`.
    snippet_path: str | None = None
    # Optional: ETag header from the connector's last upstream response
    # (e.g. "W/\"abc123\"" or "abc123"). Carried so the snippet cache
    # can persist it in the sidecar (cached_etag) and feed it back to
    # the connector as If-None-Match on the next call.
    etag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "data": self.data,
            "as_of": self.as_of,
            "source": self.source,
            "note": self.note,
            "snippet_path": self.snippet_path,
            "etag": self.etag,
        }
