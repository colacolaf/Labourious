# ROADMAP — what to build, in what order

> Roadmap, not backlog. These 6 things are **ordered by what unblocks what**. Skip a step and the next one is unprovable.

## The constraint that shapes the order

The system being built is **the Analyst's Bench** — a citation-grounded, abstention-honest short-form research tool. Three classes of failure guard its calibration:

1. **Premature scaling** — adding flows/agents before one flagship works on free models.
2. **Untested discipline** — shipping prompts without evals; *every claim on each prompt becomes a hypothesis nobody can confirm*.
3. **Amnesiac system** — no memory across runs; the system never gets smarter.

The order below is designed to make these failures impossible to miss, in that order. Read [`CONTEXT.md`](CONTEXT.md) for the framing, [`USER-JOBS.md`](USER-JOBS.md) for the jobs the roadmap serves, [`RESTRUCTURING.md`](RESTRUCTURING.md) for the audit trail that justifies each cut.

---

## P0 — Ship these to make the project work

### 1. Runtime skeleton — `docs/runtime/`

**Goal:** A CLI script that loads a prompt by `agent_id`, calls a model, parses the JSON envelope, writes `logs/cost.json`, and chains to the next agent. No app, no UI, no extra features.

**Deliverable:** `python docs/runtime/runtime.py --flow f1 --ticker NVDA --model ollama/llama3.3:70b` returns the final-report agent's JSON envelope to stdout and exits 0.

**Cost:** Wallclock + electricity. **Tokens:** ~5–10k per f1 run on a 70B model; ~$0.05–$0.30 on Anthropic.

**Acceptance:**
- Loads a prompt from `docs/prompts/<agent_id>/system-prompt.md` and calls any of the 5 prompts.
- Calls any of the 4 model adapters with a CLI flag.
- Parses the structured-output JSON envelope (validator in `adapters/_validate_envelope.py`).
- Logs `in_tokens`, `out_tokens`, `cache_hit`, `wallclock_s`, `model`, `agent_id` to `logs/cost.json`.
- Exits 0 on success, non-zero on missing model key / unparseable output / gate breach.

**Unblocks:** everything. Without this, every other claim in `docs/CONTEXT.md` is theatre.

---

### 2. The flagship flow f1 — `docs/flows/f1-analyze-ticker.md`

**Goal:** End-to-end recipe. Given a ticker, produce a memo with bottom line + bull + bear + next questions + citations, every claim traceable to a retrieved source.

**Deliverable:** A complete f1 run on NVDA against a credible analyst memo (Stratechery / Citrus / Concurrent Capital / sell-side report) read by a skeptical human who says "I'd send this to my PM with edits." Repeatable on AAPL, MSFT.

**Glue between prompts:** A 50-line `flow_f1.py` script per flow that orchestrates the 5 prompts in dependency order.

**Acceptance:**
- Three consecutive f1 runs on NVDA each produce a memo with: a 1-line bottom line; a 3–5 paragraph bull case; a 3–5 paragraph bear case (from devil's-advocate); a "What an attacker would say" section; a "Next three questions" section; ≥ 80% of claims cited to a primary source URL.
- Forensic-accounting output is on-record (not silently omitted) regardless of cleanliness, per the agent's prompt.
- Devil's-advocate surfaces at least one bear argument not present in the bull case (i.e. it does work).
- Wallclock under 10 minutes on Ollama + Llama 3.3 70B, under 2 minutes on Anthropic Sonnet.

**Unblocks:** trust (job 1), action (job 2), speed (job 3), defensibility (job 4).

---

### 3. Eval suite v1 — `docs/runtime/evals/`

**Goal:** A pytest suite that fails when the system's discipline breaks. After this exists, **no prompt change ships without running it**.

**Deliverable:** Five failing-on-discipline-break tests:

| Test | What it catches | Skeptical-input shape |
|------|-----------------|----------------------|
| `test_hallucination.py` | System cites a non-existent source | Inject a fabricated press release into the tool layer; assert cited URLs don't include it |
| `test_source_verification.py` | System averages over a real contradiction | Inject two contradicting 10-K footnotes for NVDA; assert the contradiction is surfaced in `gaps` or `tensions`, not averaged |
| `test_per_asset_coverage.py` | System skips an asset in a basket | Query a 5-ticker basket; assert every ticker appears in every relevant section of the final report |
| `test_freshness.py` | System uses a stale source | Inject a 3-year-old "as_of"; assert staleness is flagged |
| `test_abstention.py` | System invents rather than abstains | Ask a question the connector can't answer; assert a clean `NOT FOUND` in `gaps`, no fabrication |

**Cost:** A week of writing replayable test fixtures + inject patterns. Manual seeding of "known-fabricated" inputs from current news (so tests stay auditor-defensible).

**Acceptance:**
- Every test fails with a human-readable message naming which discipline broke.
- Tests run against any model that completes the flow (free or paid).
- tests pass on a known-clean run (Calibrated baseline memo); fail when the prompt is intentionally regressed.

**Unblocks:** legitimacy. No more "we think the prompts work." You have a CI gate.

---

### 4. Free-model adapter layer — `docs/runtime/adapters/`

**Goal:** One file per model provider so the slot in `--model` works across providers without rewriting prompts. Hybrid routing — free for 90% of work, paid for highest-stakes synthesis only.

**Deliverable:** Four adapters, each conforming to a common interface:

| Adapter file | Provider | Free-tier option |
|--------------|----------|------------------|
| `adapters/anthropic.py` | Anthropic Messages (Sonnet / Haiku) | None in v1, fallback for synthesis only |
| `adapters/ollama.py` | Local Ollama server | Yes — `llama3.3:70b`, `qwen2.5:72b`, `deepseek-r1:70b` |
| `adapters/groq.py` | Groq Inference API | Yes — Llama 3.3 70B Versatile, Qwen 2.5 72B |
| `adapters/openai_compat.py` | Anything OpenAI-compatible (Together, OpenRouter, etc.) | Some — OpenRouter zero-priced routes |

**Acceptance:**
- A single `--model` flag across all four adapters (`ollama/llama3.3:70b`, `groq/llama-3.3-70b-versatile`, `anthropic/claude-sonnet-4-5`, `openrouter/meta-llama/llama-3.3-70b:free`).
- Hybrid routing flag: `--paid-for final-report` — runs the orchestrator + lead + specialists on free, final-report on Sonnet.
- Prompt caching: adapters translate the orchestrator's plan + lead's coverage as a single prefix to subsequent agents.

**Unblocks:** cost. After this, every user can run a $0 flow.

---

### 5. Tool adapters — `docs/runtime/tools/`

**Goal:** Four real tool adapters that return structured data the agents can rely on.

**Deliverable:**

| Tool | Source | Free? |
|------|--------|-------|
| `tools/sec_edgar.py` | SEC EDGAR REST API | Yes, keyless, free. Rate-limit: max 10 req/sec; user-agent header required. |
| `tools/news.py` | Google News RSS + Reddit JSON API + (optional) NewsAPI | RSS endpoint free; NewsAPI requires key. |
| `tools/market_data.py` | Yahoo Finance via `yfinance` Python package, FRED API for macro | yfinance keyless; FRED requires key. |
| `tools/web_fetch.py` | Single-page-to-markdown helper (Beautiful Soup + markdownify) | Free, local. |

**Acceptance:**
- Each adapter exposes `def call(tool_input) -> tool_output` with structured failure semantics (`SUCCESS | PARTIAL | FAILED | EMPTY`, with reason).
- A 1MB response cache keyed on `(tool, input_hash, fetch_ts)` written to `runtime/.cache/`.
- Connectors degrade gracefully: if SEC EDGAR is down, the agent reports `connector_status: FAILED` and continues with what it has.

**Unblocks:** analyst work that is more than Wikipedia recap. SEC filings matter; recency matters; primary sources matter.

---

### 6. Thesis register — `docs/runtime/thesis_register/`

**Goal:** Persistent, versioned, queryable memory of past theses and updates. After this, every f1 run *gets better* by reading the last time the system thought about this ticker.

**Deliverable:** SQLite schema with 3 tables:

```sql
CREATE TABLE theses (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  date TEXT NOT NULL,
  thesis_text TEXT NOT NULL,
  conviction INTEGER NOT NULL,         -- 1..5
  bottom_line TEXT NOT NULL,
  evidence_urls TEXT NOT NULL,         -- JSON array
  flow_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE updates (
  id INTEGER PRIMARY KEY,
  thesis_id INTEGER NOT NULL REFERENCES theses(id),
  date TEXT NOT NULL,
  what_changed TEXT NOT NULL,
  new_thesis_text TEXT,
  deltas TEXT,                        -- JSON: the things that flipped
  reason TEXT
);

CREATE TABLE catalysts (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  event TEXT NOT NULL,
  expected_date TEXT,
  what_to_watch TEXT,
  resolved_date TEXT,
  resolved_outcome TEXT
);
```

Plus a `register.py` module exposing:
- `read_thesis(ticker) -> last_n_versions`
- `diff_thesis(ticker, new_thesis_text) -> changed_fields`
- `write_thesis(thesis_object)`
- `add_update(ticker, what_changed, reason)`
- `add_catalyst(ticker, event, expected_date, what_to_watch)`
- `resolve_catalyst(...)`

**Acceptance:**
- Every f1 run starts by calling `read_thesis(ticker)` and surfaces the prior thesis in its conclusion if one exists.
- Every f1 run ends by calling `write_thesis(...)`. The previous thesis is preserved; the new one is versioned.
- `diff_thesis(...)` against the previous version surfaces in the final report under "What changed since we last looked."
- Catalysts are queryable in CLI: `python register.py catalysts AAPL`.**Unblocks:** jobs 1, 4, and the missing trait #6 from the prior report (updating views when facts change). Without this, the system never compounds.

### 7. The TUI (`docs/frontend/`)

**Goal:** A Python TUI (Textual v4 + Rich) the user actually interacts with — chat bubbles streaming per agent, a left activity sidebar, inline diff when a prior thesis exists, modal screens for Settings + History. Research + decision in [`FRONTEND-DECISION.md`](FRONTEND-DECISION.md).

**Deliverable:** `python docs/frontend/app.py` launches the TUI. The user's first experience is identical to `python docs/runtime/runtime.py --flow f1 ...` but with progressive disclosure as agents complete.

**Cost:** ~1500 lines of Python + ~150 lines of CSS. No new dependencies beyond `textual>=4`, `rich>=13`, `keyring>=24`, `tomli>=2` (see [`IMPLEMENTATION.md`](IMPLEMENTATION.md)).

**Acceptance:**
- Each event type from [`PROTOCOL.md`](frontend/PROTOCOL.md) renders correctly in the TUI.
- `--dry-run` mode also works in the TUI (the wave plan is shown instead of running).
- Modal screens (Settings, History) round-trip through `~/.labourious/config.json` and `docs/runtime/thesis_register/theses.db`.
- Falls back gracefully to a no-key / unreachable-tool state without crashing.

**Unblocks:** the audit's missing trait #8 (anticipation — the TUI surfaces the next 3 questions inline so the user can pre-seed them), plus real adoption (a TUI on the user's laptop is what they actually use).

---

## P1 — Once P0 is green

### 8. Flow f2 — `docs/flows/f2-compare-tickers.md`

Same 5 prompts, different wrapper. Inputs: 2–5 tickers + optional sector. Output: side-by-side normalized comparison, ranked. Same evals apply; same thesis register usage. **The flow file is the only new artifact.**

### 9. Flow f3/f4 — earnings preview / review

Same prompts, scope narrowed to the next (or last) earnings event. **Reuses f1's wrapper with a different rubric.**

### 10. Eval suite v2

Add tests for: prompt-cache hit-rate, abstention rate by connector failure, citation coverage by section, devil's-advocate minimum coverage (the bear case must include at least one argument not in the bull case).

### 11. Agent prompt v2 cycles

With the eval suite green, the system now has a feedback loop. Agent prompts are versioned (`senior-analyst_v1.md`, ..., `_vN.md`); the eval harness runs both and diffs outputs. This is where the prompts *get better* over time. The Wharton target isn't the v1 — it's the steady improvement graph.

---

## P2 — Once P1 ships and a thesis register has ≥ 30 entries

### 12. Flows f5–f8 (sector deep-dive, thematic screen, risk event, macro overlay)

Flow-only artifacts. **No new agent prompts.** Each flow wires up its prompt sequence via `run_flow_stream` (post-TUI) or its own orchestrator function (pre-TUI).

### 13. The Wharton-comp deliverables as flows f9/f10

IPS drafting as `f9-ips-draft`. Final handed-in report as `f10-final-pitch`. The Wharton comp becomes **a config of f1 + f9 + f10**, not a different system.

### 14. Pluggable agents (knowledge packs only, not more analyst agents)

`docs/prompts/pluggable/<sector>-pack.md`, loaded as a `<system-prompt-fragment>` into the senior-analyst prompt at runtime. New agents earn existence only via the v1 pluggable policy in [`DEFERRED.md`](DEFERRED.md).

---

## What isn't on this roadmap (and why)

- **Real-time market data.** Deferred to P3+ and only if a user pays; delayed OHLCV is enough.
- **Trading execution.** Out of scope permanently; see [`CANNOT-DO.md`](CANNOT-DO.md).
- **Portfolio management UI.** The user has one; we provide analysis, not custody.
- **Per-sector agents as separate prompts.** Forbidden by the pluggable policy: sectors are knowledge packs, not agents (Anthropic multi-agent research + LangChain are unanimous on this — extra low-variance agents amplify each other's blind spots instead of diversifying them).
- **A 26-agent roster.** Permanently. The 5 prompts are the steady state.

---

## How to use this file

Pick the next item on this list. Each item has a goal, a deliverable, an acceptance criterion, and the item it unblocks. Build P0 in numerical order; do not skip. P1 and P2 are tested as P0 goes green.
