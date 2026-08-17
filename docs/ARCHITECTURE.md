# ARCHITECTURE

> Today: 5 prompts, 4 model adapters, 4 tool adapters, 1 thesis register, 5 evals, 8 flows, **a Python TUI (Textual v4 + Rich)**. Local-first. Free-model-friendly. Phase: post-restructure, pre-runtime-build.

The architecture is what *runs* — runtime — once it ships. Right now, it's the shape the codebase is committed to. The decisions are derived in [`RESTRUCTURING.md`](RESTRUCTURING.md) and constrained by [`CANNOT-DO.md`](CANNOT-DO.md). Build order is in [`ROADMAP.md`](ROADMAP.md). The user-facing surface is a **TUI**, not a browser or Electron app — see [`FRONTEND-DECISION.md`](FRONTEND-DECISION.md) for the research that picked it.

---

## System Overview

```
                              ┌──────────────────────────────────┐
                              │     USER (CLI / future UI)       │
                              │  --flow f1 --ticker NVDA ...     │
                              └──────────────────┬───────────────┘
                                                 │
                                                 ▼
                          ╭─────────────────────────────────────────╮
                          │     ORCHESTRATOR (1 prompt)             │
                          │  • routing (5 routing rules)            │
                          │  • wave planning                       │
                          │  • effort mode selection               │
                          │  • prompt-cache prefix assembly        │
                          ╰─────────────────┬───────────────────────╯
                                            │  hub-and-spoke (always)
              ┌─────────────────────────────┼─────────────────────────────┐
              │                             │                             │
              ▼                             ▼                             ▼
   ╭─────────────────────╮    ╭─────────────────────────╮    ╭────────────────────╮
   │  SENIOR ANALYST     │    │  FORENSIC ACCOUNTING   │    │  DEVIL'S ADVOCATE  │
   │  (lead prompt)      │───▶│  (specialist)          │    │  (specialist)      │
   │                     │    │  earnings quality,     │    │  mandatory counter │
   │  • frames question  │    │  accruals, M-Score,    │    │  case              │
   │  • owns thesis      │    │  red flags             │    │                    │
   │  • coordinates spec.│    │  → JSON envelope       │    │  → counter-case    │
   │  → thesis skeleton  │    │                        │    │                    │
   ╰─────────┬───────────╯    ╰─────────────────────────╯    ╰─────────┬──────────╯
             │                                                              │
             │                                                              │
             ▼                                                              ▼
   ╭────────────────────────────────────────────────────────────────────────────────╮
   │                          FINAL REPORT (1 prompt)                              │
   │  ─ bottom line (direction + conviction + flip-trigger)                        │
   │  ─ bull case (from senior-analyst)                                           │
   │  ─ bear case (from devil's-advocate)                                         │
   │  ─ what an attacker would say (from devil's-advocate + forensic)              │
   │  ─ next three questions (system-anticipation pattern)                        │
   │  ─ citations (every claim → primary URL + as_of)                              │
   ╰──────────────────────────────────────┬────────────────────────────────────────╯
                                          │
                                          ▼
                          ╭───────────────────────────────╮
                          │     THESIS REGISTER           │
                          │  SQLite: theses + updates     │
                          │       + catalysts             │
                          │  On every f1 run:             │
                          │  • read past theses           │
                          │  • diff vs. new thesis        │
                          │  • write new versioned row    │
                          ╰───────────────────────────────╯
```

Five prompts. Single hub-and-spoke. Each box is **one** system-prompt.md file. Each one is reusable across all 8 flows ([`docs/flows/`](flows/)).

---

## Components

### 1. The 5 prompts

| Prompt | Path | Function |
|--------|------|----------|
| Orchestrator | `docs/prompts/orchestrator/system-prompt.md` | Routing, wave planning, synthesis, conclusion-first presentation |
| Senior Analyst (lead) | `docs/prompts/leads/senior-analyst/system-prompt.md` | Frames the question, owns the thesis, coords specialists |
| Forensic Accounting (specialist) | `docs/prompts/specialists/forensic-accounting/system-prompt.md` | Earnings quality, accruals, M-Score, red flags |
| Devil's Advocate (specialist) | `docs/prompts/specialists/devils-advocate/system-prompt.md` | Mandatory counter-case, steelman-then-break |
| Final Report | `docs/prompts/cross-cutting/final-report/system-prompt.md` | Assembles bottom line + bear case + next questions + citations |

All 5 share the JSON envelope spec defined in [`prompts/V2-PROMPT-STANDARD.md`](prompts/V2-PROMPT-STANDARD.md). The runtime validates every envelope on receipt.

### 2. Model adapters — `docs/runtime/adapters/`

A single file per provider, conforming to a common interface (`class ModelAdapter.call(messages, system, options) -> Response`). Today's adapters:

| Adapter file | Provider | Free-friendly |
|--------------|----------|---------------|
| `adapters/anthropic.py` | Anthropic Messages (Sonnet 4.5 / Haiku 4) | No; paid only. Used for synthesis only under hybrid routing. |
| `adapters/ollama.py` | Local Ollama server | Yes — supports Llama 3.3 70B, Qwen 2.5 72B, DeepSeek-R1. |
| `adapters/groq.py` | Groq Inference API | Yes — Llama 3.3 70B Versatile (free tier very fast), Qwen 2.5 72B. |
| `adapters/openai_compat.py` | OpenRouter, Together, OpenAI itself, etc. | Variable — OpenRouter has zero-priced routes. |

**Hybrid routing default:** orchestrator + lead + specialists → free model (Ollama local or Groq free); final-report agent → Sonnet via the `--paid-for final-report` flag. **Estimated cost per f1 run: ~$0.05–$0.30 on hybrid; ~$0 on all-free.**

### 3. Tool adapters — `docs/runtime/tools/`

Four real tool adapters that return structured data:

| Tool | Source | Interface |
|------|--------|-----------|
| `tools/sec_edgar.py` | SEC EDGAR REST API (free, keyless, 10 req/sec cap) | `def get_filing(ticker, form, period)` |
| `tools/news.py` | Google News RSS + Reddit JSON + optional NewsAPI | `def search_news(query, since, until)` |
| `tools/market_data.py` | `yfinance` (free, keyless) + FRED (free, key) | `def price_history(ticker, period)` |
| `tools/web_fetch.py` | Single-page fetch → markdown (BS4 + markdownify) | `def fetch(url)` |

Each tool returns:

```json
{
  "status": "SUCCESS | PARTIAL | FAILED | EMPTY",
  "data": <tool_payload>,
  "as_of": "2026-08-16T12:34Z",
  "source": "sec_edgar",
  "note": "Retrieved 10-K FY2026 + FY2025 + 10-Q Q3"
}
```

The orchestrator surfaces `FAILED` to the user (no silent substitution).

### 4. Thesis register — `docs/runtime/thesis_register/`

SQLite with 3 tables:

- `theses` — versioned theses per ticker (one row per f1 run)
- `updates` — diff-against-prior records ("X flipped because Y")  
- `catalysts` — anticipated events ("next earnings 2026-11-20 — what we're watching")

Every f1 run starts by calling `read_thesis(ticker)` and ends by calling `write_thesis(...)`. This is the system's durable memory across runs — without it, every analysis is one-shot.

### 5. The 8 flows — `docs/flows/`

Flows are **recipes**, not agents. They're thin: which prompts in what order, what rubric, what gets written where. The 5 prompts above are reused across all 8 flows.

| Flow | File | Reuses | Adapts |
|------|------|--------|--------|
| f1 — Analyze ticker | `docs/flows/f1-analyze-ticker.md` | All 5 prompts | Standard rubric |
| f2 — Compare tickers | `docs/flows/f2-compare-tickers.md` | All 5 prompts | Comparison rubric |
| f3 — Earnings preview | `docs/flows/f3-earnings-preview.md` | All 5 prompts | "What we're watching" rubric |
| f4 — Earnings review | `docs/flows/f4-earnings-review.md` | All 5 prompts | "What changed" rubric |
| f5 — Sector deep-dive | `docs/flows/f5-sector-deep-dive.md` | All 5 prompts | Cross-name rubric |
| f6 — Thematic screen | `docs/flows/f6-thematic-screen.md` | Lead + devil's-advocate | Screening rubric |
| f7 — Risk event | `docs/flows/f7-risk-event.md` | All 5 prompts | Event-driven rubric |
| f8 — Macro overlay | `docs/flows/f8-macro-overlay.md` | Lead + forensic | Macro-frame rubric |

### 6. The user surface — `docs/frontend/`

The user interacts with the bench via a **Python TUI (Textual v4 + Rich)** — see [`FRONTEND-DECISION.md`](FRONTEND-DECISION.md) for the research that chose it (over Electron, local web app, or plain CLI). The TUI:

- **Consumes events** from `runtime.run_flow_stream()` per [`PROTOCOL.md`](frontend/PROTOCOL.md).
- **Renders** chat-style streaming markdown bubbles per agent ([`SPEC.md`](frontend/SPEC.md)).
- **Shows** a left activity sidebar with per-agent status + cost totals; a `Diff` collapsible when a prior thesis exists; an inline `What changed` line if `f4` is in flight.
- **Exposes modals** for Settings (edit `~/.labourious/config.json`) and History (browses the thesis register).

The TUI is built **in-process** with the runtime (one Python process, one event iterator). No HTTP/IPC bridge, no Node shim, no Electron. Local-first, period.

### 7. Eval suite — `docs/runtime/evals/`

Five tests that **fail when discipline breaks**:

| Test | Discipline it tests |
|------|---------------------|
| `test_hallucination.py` | The system never cites a source it didn't retrieve this run |
| `test_source_verification.py` | Contradictions surface in `gaps` or `tensions`, not averaged |
| `test_per_asset_coverage.py` | Every ticker in a basket appears in every relevant section |
| `test_freshness.py` | Stale sources are flagged |
| `test_abstention.py` | Out-of-scope queries return `NOT FOUND`, not invention |

Run this on every prompt change. A passing eval suite is the only evidence the system "works."

---

## Calling model

```
1. Runtime loads flow (e.g. f1).
2. Runtime loads orchestrator prompt.
3. Runtime calls orchestrator with: user_query + flow_id + thesis_register.read(ticker).
4. Orchestrator returns JSON envelope with: routing decisions, agent brief list, effort mode.
5. Runtime executes each brief in order:
   a. Lead prompt → JSON envelope.
   b. Each specialist called from lead → JSON envelope.
6. Final-report prompt called with the synthesized prior envelopes.
7. Final report JSON envelope returned to user + parsed to memo markdown.
8. Runtime writes thesis_register row(s) before exit.
9. Runtime logs cost.json + activity_panel.
```

Hub-and-spoke: **no agent calls another agent directly**. All communication flows through the orchestrator's synthesis step. The senior-analyst lead is special — it receives briefs from the orchestrator and is allowed to "request" a forensic-accounting call as part of its output, but the **runtime** decides whether to actually make that call (it almost always will). The runtime is the conduit, not the senior-analyst prompt.

---

## Prompt caching strategy

Anthropic's multi-agent paper June 2025 estimates the 15× token cost; the cache hit rate is the major savings. The runtime implements:

- Per-flow cache: keyed on `(flow_id, asset_universe_hash, run_id)`.
- Per-agent prefix: orchestrator's coverage plan + senior-analyst's thesis skeleton become a single prefix to every downstream agent call.
- Per-freshness cache: any tool layer call with a hash-equivalent input is served from cache for the freshness window (1 day for prices, 1 week for filings, 6 hours for news).

**Effect:** when the final-report agent is called with the orchestrator's routing + senior-analyst's thesis + forensic-accounting's output + devil's-advocate's output as a prefix, the model pays cheap input-token cost on the cached portion. **This is where the runtime wins, even on free models that don't auto-cache.**

---

## Memory model

| Storage | What | Lifetime | Locality |
|---------|------|----------|----------|
| `~/.labourious/config.json` | API keys, model choice, hybrid flag | Until the user deletes it | Local |
| OS keychain / `safeStorage` | API secret strings | Until the user removes them | Local |
| `~/.labourious/history/<conversation_id>.json` | Chat history per session | Until the user prunes | Local |
| `docs/runtime/thesis_register/theses.db` (or `~/.labourious/theses.db`) | Thesis register | Forever (grows linearly with runs) | Local |
| `docs/runtime/.cache/<tool>/<hash>.json` | Tool-call response cache | The freshness window | Local |
| `logs/cost.json` | Per-call token meter | Forever (append-only) | Local |

Nothing leaves the user's machine. **No Labourious backend exists.**

---

## What's NOT in this architecture

Three things explicitly omitted because they're wrong-shaped:

1. **A vector DB for "agent memory."** The thesis register covers long-term memory; tool caches cover short-term. A vector DB adds complexity without an observed need; the design leaves room to slot one in (`docs/runtime/thesis_register/`) but doesn't ship it.
2. **A web-search connector at the orchestrator level.** Web search is a *specialist tool*; the orchestrator routes requests to specialists, doesn't fetch itself.
3. **A broker integration.** Out of scope; see [`CANNOT-DO.md`](CANNOT-DO.md).

---

## Component dependencies

```
prompts/  ─────┐
               ├──▶  runtime/runtime.py
adapters/  ────┤
               ├──▶  runtime/tools/
flows/  ───────┤
               ├──▶  runtime/thesis_register/
evals/  ───────┘
```

Prompts are inert until the runtime loads them. The runtime is inert until a flow is requested. The evals call the runtime end-to-end. The thesis register is the only stateful component.

---

## How a developer reads this

1. Pick a feature question. [`USER-JOBS.md`](USER-JOBS.md) names which job it serves.
2. Decide if it's in scope. [`CANNOT-DO.md`](CANNOT-DO.md) answers.
3. Pick which prompt to extend. Click through the 5 [`docs/prompts/`](prompts/) files.
4. Pick which flow to adapt it for. Read the relevant flow in [`docs/flows/`](flows/).
5. Implement and test against the [`evals/`](runtime/evals/).
6. Update `CHANGELOG.md`.
