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

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "data": self.data,
            "as_of": self.as_of,
            "source": self.source,
            "note": self.note,
        }
