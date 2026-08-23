"""
diff_widget.py — collapsible prior-thesis vs new-thesis panel.

Renders a structured delta grouped by section:
  - **Added**  (green)  — sections present in the new envelope but not the prior
  - **Removed** (red)    — sections present in the prior but gone from the new
  - **Modified** (yellow) — sections whose text changed between prior and new

Only rendered when a prior thesis exists in the register. Collapsed by default.

v2: section-by-section structured diff instead of literal OLD→NEW lines.
"""

from __future__ import annotations

from difflib import unified_diff
from typing import Any

from textual.containers import Vertical
from textual.widgets import Collapsible, Static


_DIFF_SECTIONS: list[tuple[str, str]] = [
    # (envelope_key, display_label)
    ("thesis_text",    "Thesis"),
    ("bottom_line",    "Bottom Line"),
    ("bull_case",      "Bull Case"),
    ("bear_case",      "Bear Case"),
    ("what_an_attacker_would_say", "Attacker Says"),
    ("next_three_questions", "Next Questions"),
    ("conviction",     "Conviction"),
    ("confidence",     "Confidence"),
    ("verification",   "Verification"),
]


class DiffPanel(Vertical):
    """Side-by-side prior vs. new with structured section diffs."""

    def __init__(self, prior: dict, current: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.add_class("diff-panel")
        header = (
            f"▾  Changes since {prior.get('version', 'v?')} "
            f"· {prior.get('created_at', '')}"
        )
        body = self._render_body(prior, current)
        self._collapsible = Collapsible(
            Static(body, markup=True), title=header, collapsed=True
        )

    def compose(self):
        yield self._collapsible

    @staticmethod
    def _section_changed(old: str, new: str) -> bool:
        """Numeric sections compared as-is; text sections stripped of whitespace."""
        os = str(old).strip()
        ns = str(new).strip()
        return os != ns

    @staticmethod
    def _section_diff(old: str, new: str, max_lines: int = 6) -> str:
        """Mini inline diff showing changed lines (truncated to max_lines)."""
        old_lines = str(old).splitlines(keepends=True) if old else []
        new_lines = str(new).splitlines(keepends=True) if new else []
        diff_lines = list(unified_diff(
            old_lines, new_lines,
            fromfile="prior", tofile="new", lineterm=""
        ))
        if len(diff_lines) > max_lines + 3:
            diff_lines = diff_lines[:max_lines] + ["  … (truncated)"]
        return "\n".join(diff_lines)

    @classmethod
    def _render_body(cls, prior: dict, current: dict) -> str:
        """Markup-mode structured delta grouped by (added / removed / modified)."""
        lines: list[str] = []
        added: list[tuple[str, str]] = []
        removed: list[tuple[str, str]] = []
        modified: list[tuple[str, str, str]] = []  # (label, old, new)

        for key, label in _DIFF_SECTIONS:
            old_val = prior.get(key)
            new_val = current.get(key)

            # Coerce dicts into json-like strings for comparison
            if isinstance(old_val, dict):
                old_val = _compact_dict(old_val)
            if isinstance(new_val, dict):
                new_val = _compact_dict(new_val)

            old_present = old_val is not None and str(old_val).strip() != ""
            new_present = new_val is not None and str(new_val).strip() != ""

            if not old_present and new_present:
                added.append((label, str(new_val)[:300]))
            elif old_present and not new_present:
                removed.append((label, str(old_val)[:300]))
            elif old_present and new_present and cls._section_changed(str(old_val), str(new_val)):
                modified.append((label, str(old_val)[:200], str(new_val)[:200]))

        # ── Modified ──
        if modified:
            lines.append("[bold yellow]═══ Modified ═══[/]")
            for label, old_s, new_s in modified:
                lines.append(f"\n[b]{label}[/b]")
                lines.append(f"  [dim red]- {old_s}[/]")
                lines.append(f"  [dim green]+ {new_s}[/]")
            lines.append("")

        # ── Added ──
        if added:
            lines.append("[bold green]═══ Added ═══[/]")
            for label, val in added:
                lines.append(f"  + [b]{label}[/b]: {val}")
            lines.append("")

        # ── Removed ──
        if removed:
            lines.append("[bold red]═══ Removed ═══[/]")
            for label, val in removed:
                lines.append(f"  - [b]{label}[/b]: {val}")
            lines.append("")

        if not (modified or added or removed):
            lines.append("[dim]No significant changes detected.[/]")

        return "\n".join(lines)

    @classmethod
    def maybe_build(cls, prior_list: list[dict], current: dict) -> "DiffPanel | None":
        """Public factory: returns None if no prior thesis exists."""
        if not prior_list:
            return None
        prior = sorted(prior_list, key=lambda r: str(r.get("created_at", "")), reverse=True)[0]
        return cls(prior=prior, current=current)


def _compact_dict(d: dict, max_len: int = 200) -> str:
    """Flatten a dict to a compact one-line representation for diff display."""
    if not d:
        return "{}"
    pairs = []
    for k, v in d.items():
        s = str(v)
        if len(s) > 60:
            s = s[:57] + "..."
        pairs.append(f"{k}={s}")
    result = ", ".join(pairs)
    if len(result) > max_len:
        result = result[:max_len - 3] + "..."
    return result