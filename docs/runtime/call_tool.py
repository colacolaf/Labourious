"""
call_tool.py — Runtime-level wrapper around every tier-1 connector call.

The runtime's contract with the TUI is the typed event set in `events.py`.
Connectors themselves return a `ToolResult` (status + data + as_of + source +
note). This module is the bridge: any caller — `execute_flow_f1` after a
tool-feeding directive, a CLI `--call-tool` invocation, a TUI hotkey, a
manual pilot — invokes `call_tool(...)` once, and gets back a ToolResult
*plus* the 3 Connector* events fires that the TUI already routes
(`chat._apply_event`). This is what makes the connector strip light up
automatically when an agent uses a tool.

Adding a connector to the registry is a single dict entry. New tools don't
touch the TUI at all — adding the connector is enough.

The pilot path (`runtime.call_tool.call_tool`) is the canonical way to invoke
any tier-1 connector. Bypassing it (calling `tool.X(**kwargs)` directly)
skips the event emission and the connector strip will *not* update.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .events import ConnectorCompleted, ConnectorFailed, ConnectorRequested
from .tools import ToolResult
from .tools.comparator import ComparatorTool
from .tools.comps import CompsTool
from .tools.dcf import DCFTool
from .tools.news_8k import News8KTool
from .tools.insider import InsiderTool
from .tools.institutional import InstitutionalTool
from .tools.market_data import MarketDataTool
from .tools.news import NewsTool
from .tools.sec_edgar import SECEdgarTool
from .tools.sec_edgar_fulltext import SECEdgarFullTextTool
from .tools.transcripts import TranscriptsTool
from .tools.web_fetch import WebFetchTool


log = logging.getLogger("labourious.call_tool")


# --------------------------------------------------------------------------- #
# Tool registry
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ToolBinding:
    """A single bridge between a connector id and the actual Tool class method.

    `arg_keys` lists the kwarg keys the runtime expects when the caller
    pre-routes to the *default* method. Other methods (e.g. transcripts'
    `fetch_transcript`) accept the full kwargs dict verbatim and don't need
    a fixed key list.

    `passes_request` is True for tools whose default method accepts a
    single positional `request: dict` (rather than flat kwargs). When set,
    callers like the CLI (``--call-tool quant_dcf --request '{...}'``)
    navigate to ``fn(tool_instance, request=<args>)`` instead of
    ``fn(tool_instance, *<args>)``.
    """
    tool_id: str
    tool_class: type
    default_method: str
    arg_keys: tuple[str, ...]
    summary_field: str  # name of `ToolResult.data` to summarize; "" = generic
    passes_request: bool = False


TOOL_REGISTRY: dict[str, ToolBinding] = {
    # ── sec_edgar_fulltext: full-text search of the filing body ──
    "sec_edgar_fulltext": ToolBinding(
        tool_id="sec_edgar_fulltext",
        tool_class=SECEdgarFullTextTool,
        default_method="search",
        arg_keys=("query", "forms", "ciks", "start", "end", "limit"),
        summary_field="",
    ),
    # ── sec_edgar: structured filings index / cik lookup ──
    "sec_edgar": ToolBinding(
        tool_id="sec_edgar",
        tool_class=SECEdgarTool,
        default_method="cik_for_ticker",
        arg_keys=("ticker",),
        summary_field="",
    ),
    # ── news_8k: material-event 8-K wire ──
    "news_8k": ToolBinding(
        tool_id="news_8k",
        tool_class=News8KTool,
        default_method="latest",
        arg_keys=("ticker", "since_days", "items", "query", "limit"),
        summary_field="rows",
    ),
    # ── insider: openinsider + EDGAR Form 4 ──
    "insider": ToolBinding(
        tool_id="insider",
        tool_class=InsiderTool,
        default_method="cluster_buys",
        arg_keys=("ticker", "since_days", "kind", "min_value", "limit"),
        summary_field="",
    ),
    # ── institutional: EDGAR 13F (mega-filer variant) ──
    "institutional": ToolBinding(
        tool_id="institutional",
        tool_class=InstitutionalTool,
        default_method="major_holders",
        arg_keys=("ticker", "since_quarters", "limit"),
        summary_field="",
    ),
    # ── transcripts: SA index + body fetch ──
    "transcripts": ToolBinding(
        tool_id="transcripts",
        tool_class=TranscriptsTool,
        default_method="list_for_ticker",
        arg_keys=("ticker", "since_quarters", "limit"),
        summary_field="",
    ),
    # ── quant: DCF + comps + comparator ──
    "quant_dcf": ToolBinding(
        tool_id="quant_dcf",
        tool_class=DCFTool,
        default_method="run_model",
        arg_keys=("ticker",),
        summary_field="per_share",
        passes_request=True,
    ),
    "quant_comps": ToolBinding(
        tool_id="quant_comps",
        tool_class=CompsTool,
        default_method="run",
        arg_keys=("subject.ticker",),
        summary_field="",
        passes_request=True,
    ),
    "quant_comparator": ToolBinding(
        tool_id="quant_comparator",
        tool_class=ComparatorTool,
        default_method="run",
        arg_keys=("rubric",),
        summary_field="confidence",
    ),
    # ── news: Google News RSS (no key) or NewsAPI (free key) ──
    "news": ToolBinding(
        tool_id="news",
        tool_class=NewsTool,
        default_method="search_news",
        arg_keys=("query", "limit"),
        summary_field="",
    ),
    # ── market_data: yfinance (no key) + FRED (free key) ──
    "market_data": ToolBinding(
        tool_id="market_data",
        tool_class=MarketDataTool,
        default_method="price_history",
        arg_keys=("ticker", "period", "interval"),
        summary_field="",
    ),
    # ── web_fetch: any URL → text ──
    "web_fetch": ToolBinding(
        tool_id="web_fetch",
        tool_class=WebFetchTool,
        default_method="fetch",
        arg_keys=("url",),
        summary_field="",
    ),
}


def known_tool_ids() -> list[str]:
    """Sorted list of all registered tool ids — useful for validation/CLI help."""
    return sorted(TOOL_REGISTRY.keys())


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _summarize(result: ToolResult, summary_field: str) -> str:
    """Turn ToolResult.data into a single ≤ ~80-char line for the strip chip.

    This is a *display* summary — never used as content. The real data is in
    `ToolResult.data`; the agent's prompt may pull whatever it needs from
    there.
    """
    data = result.data
    if data is None:
        return "(no data)"
    if summary_field and isinstance(data, dict):
        rows = data.get(summary_field)
        if isinstance(rows, list):
            return f"{len(rows)} {summary_field}"
        if isinstance(rows, dict):
            return f"{summary_field}: {len(rows)} entries"
    if isinstance(data, list):
        return f"{len(data)} rows"
    if isinstance(data, dict):
        if "rows" in data and isinstance(data["rows"], list):
            return f"{len(data['rows'])} rows"
        return f"dict({len(data)} keys)"
    if isinstance(data, str):
        return f"{len(data)} chars"
    return type(data).__name__


def _query_args(b: ToolBinding, args: Mapping[str, Any]) -> str:
    """Build a sanitized 1-line `query` summary for ConnectorRequested.

    Args are scrubbed of any object that's not a plain str/int/float/bool/None
    (URLs and identifiers survive, lists serialize as comma-joined). Bounded
    at ~120 chars so the log line stays one row.
    """
    def _scrub(v: Any) -> str:
        if v is None or isinstance(v, (str, int, float, bool)):
            return str(v)
        if isinstance(v, (list, tuple)):
            return ",".join(_scrub(x) for x in v)
        return str(v)

    parts = []
    for k in b.arg_keys:
        if k in args and args[k] is not None:
            parts.append(f"{k}={_scrub(args[k])}")
    raw = " ".join(parts) or "(no args)"
    return raw[:120]


def _now_iso() -> str:
    return dt.datetime.utcnow().isoformat() + "Z"


# --------------------------------------------------------------------------- #
# The function
# --------------------------------------------------------------------------- #
def call_tool(
    tool_id: str,
    requested_by_agent: str,
    emit_event: Callable[[Any], None] | None = None,
    *,
    method: str | None = None,
    args: Mapping[str, Any] | None = None,
) -> ToolResult:
    """Run a tier-1 connector and emit 3 typed events around it.

    Parameters
    ----------
    tool_id : str
        Id from `TOOL_REGISTRY`. Unknown ids emit `ConnectorFailed` with a
        "unknown tool_id" error and return a FAILED ToolResult without
        raising.
    requested_by_agent : str
        Used to (a) populate `ConnectorRequested.requested_by_agent` and
        (b) populate `ConnectorCompleted/Failed.requested_by_agent` so the
        TUI's chat screen can route the strip chip to the right bubble.
    emit_event : callable, optional
        Hook from `execute_flow_f1` (or the TUI). When provided, the three
        events fire around the call. When None, the call runs silently
        (useful for unit tests / dry-runs).
    method : str, optional
        Override the registry's `default_method`. E.g. for transcripts,
        caller may want `fetch_transcript("4907730", ticker="NVDA")`.
    args : dict, optional
        Keyword arguments forwarded to the tool method. Only the keys listed
        in `binding.arg_keys` are validated for the default method — other
        methods accept arbitrary kwargs.

    Returns
    -------
    ToolResult
        Whatever the underlying tool returned. On an unknown tool_id, a
        synthetic FAILED ToolResult with `source=tool_id` is delivered so
        the caller never sees an exception.
    """
    binding = TOOL_REGISTRY.get(tool_id)
    args = dict(args or {})

    if binding is None:
        log.error("call_tool: unknown tool_id=%s requested_by=%s", tool_id, requested_by_agent)
        if emit_event is not None:
            emit_event(ConnectorRequested(
                tool=tool_id, query="(unknown tool_id)", requested_by_agent=requested_by_agent,
            ))
            emit_event(ConnectorFailed(
                tool=tool_id, error=f"unknown tool_id: {tool_id}",
                requested_by_agent=requested_by_agent,
            ))
        return ToolResult(
            status="FAILED", data=None, as_of=_now_iso(),
            source=tool_id, note=f"unknown tool_id: {tool_id}",
        )

    fn_name = method or binding.default_method
    fn = getattr(binding.tool_class, fn_name, None)
    if fn is None or not callable(fn):
        log.error("call_tool: tool=%s has no method %r", tool_id, fn_name)
        if emit_event is not None:
            emit_event(ConnectorRequested(
                tool=tool_id, query=_query_args(binding, args), requested_by_agent=requested_by_agent,
            ))
            emit_event(ConnectorFailed(
                tool=tool_id, error=f"unknown method: {fn_name}",
                requested_by_agent=requested_by_agent,
            ))
        return ToolResult(
            status="FAILED", data=None, as_of=_now_iso(),
            source=tool_id, note=f"unknown method: {fn_name}",
        )

    query = _query_args(binding, args)

    if emit_event is not None:
        emit_event(ConnectorRequested(
            tool=tool_id, query=query, requested_by_agent=requested_by_agent,
        ))

    # Instantiate per-call (each tool class is stateless; this keeps
    # call_tool safe under concurrent flows).
    tool_instance = binding.tool_class()

    try:
        # Tools whose default method takes a single `request` dict get the
        # whole args bag as a positional rather than spread as kwargs. This
        # handles the quant trio (DCF/Comps/Comparator) without breaking
        # tier-1 connectors that want flat kwargs.
        if binding.passes_request and not method:
            result = fn(tool_instance, request=args)
        else:
            result = fn(tool_instance, **args)
    except Exception as exc:  # surface the failure as an event, not a raise
        log.exception("call_tool: tool=%s method=%s crashed", tool_id, fn_name)
        err = f"{type(exc).__name__}: {exc}"
        if emit_event is not None:
            emit_event(ConnectorFailed(
                tool=tool_id, error=err, requested_by_agent=requested_by_agent,
            ))
        return ToolResult(
            status="FAILED", data=None, as_of=_now_iso(),
            source=tool_id, note=err,
        )

    # Defensive: ensure the tool returned a ToolResult. If a future tool
    # forgets, the strip will still update, just with a NOTE-only chip.
    if not isinstance(result, ToolResult):
        log.warning("call_tool: tool=%s method=%s did not return ToolResult",
                    tool_id, fn_name)
        result = ToolResult(
            status="EMPTY", data=result, as_of=_now_iso(),
            source=tool_id, note=f"{fn_name} returned non-ToolResult (auto-wrapped)",
        )

    summary = _summarize(result, binding.summary_field)

    if emit_event is not None:
        emit_event(ConnectorCompleted(
            tool=tool_id,
            status=result.status,
            note=result.note or "",
            as_of=result.as_of,
            data_summary=summary,
            requested_by_agent=requested_by_agent,
        ))

    return result
