"""
diff_widget.py — collapsible prior-thesis vs new-thesis panel.

Only rendered when a prior thesis exists in the register. Shows the most recent
prior version side-by-side with the current run's thesis one-liner and
conviction. Collapsed by default — the user opens it when curious.

For v1 we use a plain Textual Collapsible + Static with markup=True; full
markdown tables are a v2 polish.
"""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Collapsible, Static


class DiffPanel(Vertical):
    """Side-by-side prior vs. new. Shown above the final-report bubble."""

    def __init__(self, prior: dict, current: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.add_class("diff-panel")
        header = (
            f"▾  What changed since {prior.get('version', 'v?')} "
            f"· {prior.get('created_at', '')}"
        )
        body = self._render_body(prior, current)
        self._collapsible = Collapsible(
            Static(body, markup=True), title=header, collapsed=True
        )

    def compose(self):
        yield self._collapsible

    @staticmethod
    def _render_body(prior: dict, current: dict) -> str:
        """Markup-mode text table. Cheap diff of thesis_text + conviction."""
        prev_t = prior.get("thesis_text") or "_(none)_"
        new_t = current.get("thesis_text") or "_(none)_"
        prev_c = prior.get("conviction", "?")
        new_c = current.get("conviction", "?")
        return (
            f"        [b]prior[/b]                    [b]new[/b]\n"
            f"thesis  {prev_t}\n"
            f"        [b]{new_t}[/b]\n"
            f"\n"
            f"conv.   {prev_c}/5   →   [b]{new_c}[/b]/5"
        )

    @classmethod
    def maybe_build(cls, prior_list: list[dict], current: dict) -> "DiffPanel | None":
        """Public factory: returns None if no prior thesis exists."""
        if not prior_list:
            return None
        prior = sorted(prior_list, key=lambda r: r.get("created_at", ""), reverse=True)[0]
        return cls(prior=prior, current=current)
