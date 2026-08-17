"""frontend — the TUI layer of Labourious (Analyst's Bench).

Subpackages:
    widgets — MessageBubble, ActivityPanel, CostWidget, banners, chips, diff.
    screens — ChatScreen (default), Settings, History.
    events  — re-export of the runtime event dataclasses.
    app     — the Textual App entrypoint.

The runtime lives in `docs/runtime/` (sibling); the TUI talks to it only through
the typed Event dataclasses defined in `runtime/events.py`.
"""
