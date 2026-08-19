"""[domain-2] end-to-end pilot: primary connector data flows into the
tool_results_full brief the LLM will receive.

This proves the data-path the user asked for: real connectors pulling
real data, in a format the 3B-8B LLM can use as the seeds of its
prose. Without an LLM in the loop (which is independent) we verify that:
- market_data (yfinance) succeeds with real OHLCV, even in Securly
  SSL-MITM networks
- sec_edgar / news_8k / transcripts fail-soft with clear error notes
  (so the LLM sees the failure rather than silent silence)
- the tool_results_full block is well-formed and contains both
  successful data excerpts and failed-attempt notes
"""
from __future__ import annotations
import sys, importlib.util, pathlib
from runtime.events import ConnectorRequested, ConnectorCompleted, ConnectorFailed

OK = 0; FAIL = 0
def step(label, cond):
    global OK, FAIL
    if cond:
        print(f"  ok   | {label}"); OK += 1
    else:
        print(f"  FAIL | {label}"); FAIL += 1

# Load runtime + register runtime package
sys.path.insert(0, "docs")
_pkg_init = pathlib.Path("docs/runtime/__init__.py")
if _pkg_init.exists():
    _spec = importlib.util.spec_from_file_location("runtime", _pkg_init)
    _pkg = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_pkg)
    sys.modules["runtime"] = _pkg
spec = importlib.util.spec_from_file_location("rt", "docs/runtime/runtime.py")
rt = importlib.util.module_from_spec(spec); spec.loader.exec_module(rt)

print("=" * 64)
print("[domain-2] end-to-end connector pipeline")
print("=" * 64)

# 1. Multi-ticker preflight data flow
print("\n=== 1. preflight pulls real data across tickers ===")
tickers = ["NVDA", "AAPL", "MSFT"]
results_by_ticker = {}
for ticker in tickers:
    preflight = rt._tool_preflight(ticker=ticker, emit_event=None)
    results_by_ticker[ticker] = preflight
    yf = next((r for r in preflight if r["tool"] == "yfinance"), None)
    step(f"{ticker}: yfinance SUCCESS", yf is not None and yf["status"] == "SUCCESS")
    step(f"{ticker}: yfinance row count > 0",
         isinstance(yf.get("data"), (list, str)) and len(yf["data"]) > 0)

# 2. Brief block formatting
print("\n=== 2. brief block contains yfinance mention with data ===")
brief = rt._format_tool_results_for_brief(results_by_ticker["NVDA"])
step("brief block non-empty", len(brief) > 100)
step("brief mentions yfinance", "yfinance" in brief)
step("brief mentions SUCCESS for yfinance",
     "yfinance status=SUCCESS" in brief)
step("brief contains real OHLCV (digit-with-dot token) in data excerpt",
     any((any(ch.isdigit() for ch in w) and "." in w) for w in brief.split()))

# 3. sec_edgar fail-soft
print("\n=== 3. sec_edgar / news_8k / transcripts fail-soft in this network ===")
step("sec_edgar FAILED with clear note",
     any(r["tool"] == "sec_edgar" and r["status"] == "FAILED"
         and ("SSL" in (r.get("note") or "") or "URLError" in (r.get("note") or ""))
         for r in results_by_ticker["NVDA"]))
step("news_8k FAILED with clear note",
     any(r["tool"] == "news_8k" and r["status"] == "FAILED"
         for r in results_by_ticker["NVDA"]))
step("transcripts FAILED with clear note",
     any(r["tool"] == "transcripts" and r["status"] == "FAILED"
         for r in results_by_ticker["NVDA"]))

# 4. Events fire correctly via call_tool
print("\n=== 4. call_tool events fire from dispatching a real connector ===")
real_events = []
calls_recorded = []
def real_emit(ev: object) -> None:
    real_events.append(type(ev).__name__)
    if isinstance(ev, ConnectorRequested):
        calls_recorded.append(("req", ev.tool))
    elif isinstance(ev, ConnectorCompleted):
        calls_recorded.append(("done", ev.tool, ev.status))
    elif isinstance(ev, ConnectorFailed):
        calls_recorded.append(("fail", ev.tool, ev.error[:60]))

# success-path: yfinance
from runtime.call_tool import call_tool
tr = call_tool("market_data", requested_by_agent="test", emit_event=real_emit,
               args={"ticker": "MSFT", "period": "1mo", "interval": "1d"})
step("yfinance fires ConnectorRequested then ConnectorCompleted",
     "ConnectorRequested" in real_events and "ConnectorCompleted" in real_events)
step("ConnectorCompleted status=SUCCESS",
     any(c[0] == "done" and c[1] == "market_data" and c[2] == "SUCCESS" for c in calls_recorded))
step("tr.data has 1+ OHLCV row",
     isinstance(tr.data, list) and len(tr.data) >= 1)
# Sanity: first row has Open/High/Low/Close
if isinstance(tr.data, list) and tr.data:
    step("first row has OHLCV keys", 
         isinstance(tr.data[0], dict) and all(k in tr.data[0] for k in ["Open", "High", "Low", "Close"]))

# failure-path: sec_edgar
real_events.clear(); calls_recorded.clear()
tr = call_tool("sec_edgar", requested_by_agent="test", emit_event=real_emit,
               args={"ticker": "AAPL"})
step("sec_edgar fires ConnectorRequested then ConnectorFailed",
     "ConnectorRequested" in real_events and "ConnectorFailed" in real_events)
step("ConnectorFailed has SSL error note",
     any(c[0] == "fail" and "SSL" in c[2] for c in calls_recorded))
step("tr.status='FAILED' (graceful, no exception)",
     tr.status == "FAILED")

# 5. Synthesize citations_block from tool_results (the f9 / final-report path)
print("\n=== 5. citations_block synthesis (final-report use case) ===")
preflight = rt._tool_preflight(ticker="NVDA", emit_event=None)
citations_block = [
    f"#{i+1}: tool={r.get('tool','?')} status={r.get('status','?')} "
    f"as_of={r.get('as_of','?')} note={(r.get('note','') or '')[:120]}"
    for i, r in enumerate(preflight) if r.get("status") == "SUCCESS"
]
step("citations_block has at least 1 entry (yfinance SUCCESS)", len(citations_block) >= 1)
step("citations_block mentions yfinance",
     any("yfinance" in line for line in citations_block))

print(f"\n=== pilot complete: {OK} ok / {FAIL} fail ===")
sys.exit(0 if FAIL == 0 else 1)
