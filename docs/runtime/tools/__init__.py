# tools/__init__.py — package init for runtime tool adapters.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    status: str  # SUCCESS | PARTIAL | FAILED | EMPTY
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "data": self.data,
            "as_of": self.as_of,
            "source": self.source,
            "note": self.note,
            "snippet_path": self.snippet_path,
        }
