"""
frontend/widgets — shared widget exports.
"""
from __future__ import annotations

from .activity_panel import ActivityPanel                  # type: ignore
from .citation_chip import CitationChip                    # type: ignore
from .connection_banner import ConnectionBanner            # type: ignore
from .cost_widget import CostWidget                        # type: ignore
from .diff_widget import DiffPanel                         # type: ignore
from .inline_editor import (                               # type: ignore
    InlineTextEditor, InlineToggleEditor,
    TextEditCommitted, TextEditReverted, ToggleEditCommitted, ToggleEditDone,
)
from .message_bubble import MessageBubble                  # type: ignore
from .omniroute_setup import OmniRouteSetup                # type: ignore
from .picker_overlay import PickerItem, PickerOverlay      # type: ignore
from .section_card import SectionCard                      # type: ignore
from .setting_row import render_row                        # type: ignore
from .status_strip import (                                # type: ignore
    StatusStrip, StatusStripLeft, StatusStripRight,
    render_pairs_line, render_help_tag,
)
from .ticker_shortcuts import (                            # type: ignore
    TickerShortcuts, DEFAULT_TICKERS,
)

__all__ = [
    "ActivityPanel",
    "CitationChip",
    "ConnectionBanner",
    "CostWidget",
    "DEFAULT_TICKERS",
    "DiffPanel",
    "InlineTextEditor",
    "InlineToggleEditor",
    "MessageBubble",
    "OmniRouteSetup",
    "PickerItem",
    "PickerOverlay",
    "SectionCard",
    "StatusStrip",
    "StatusStripLeft",
    "StatusStripRight",
    "TextEditCommitted",
    "TextEditReverted",
    "TickerShortcuts",
    "ToggleEditCommitted",
    "ToggleEditDone",
    "render_pairs_line",
    "render_help_tag",
    "render_row",
]
