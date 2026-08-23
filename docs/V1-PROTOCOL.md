# V1 Protocol — Agent Schemas & Runtime Contract

> **Single source of truth for every agent's input brief and output envelope.**
> This document defines the JSON schemas that the runtime validates (`validate_envelope`
> in `docs/runtime/runtime.py`) and that the 5 system prompts expect.
>
> Companion docs:
> - `V2-PROMPT-STANDARD.md` — shared design principles (effort tiers, hallucination guardrails, etc.)
> - `docs/frontend/PROTOCOL.md` — event protocol (FlowStarted → AgentStarted → ... → FlowFinished)
> - `docs/runtime/runtime.py` — the actual `validate_envelope()` function (authoritative)

---

## 1. Agent Input Briefs

Every agent receives a **brief** (the `input` dict passed to `call_agent`) before it
generates its envelope. The brief is constructed by the runtime based on the flow,
prior envelopes, tool results, and per-run flags.

### 1.1 Shared fields (all agents)

| Field | Type | Source | Notes |
|---|---|---|---|
| `role` | `str` | `agent_id` | e.g. `"senior-analyst"`, `"orchestrator"` |
| `ticker` | `str` | Flow input | The primary ticker under analysis |
| `tickers` | `list[str]` | Flow input | All tickers in scope (basket flows) |
| `depth` | `"SCAN" \| "STANDARD" \| "DEEP"` | `--depth` flag or `"STANDARD"` default |
| `compressed` | `bool` | `--compressed` flag, defaults `false` |
| `flow_id` | `str` | Auto-generated (`f1-<timestamp>-<hash>`) |
| `run_id` | `str` | Auto-generated (`make_run_id(flow_id, ticker)`) |
| `prior_thesis` | `str` | Thesis register | Rendered by `_summarize_prior_thesis()` — a flat string, never a nested dict |
| `_tool_results_full` | `str` | `_tool_preflight()` | Pre-flight connector results stitched into a block for the LLM |

### 1.2 Orchestrator

Additional fields beyond shared:

| Field | Type | Source |
|---|---|---|
| `question` | `str` | User's prompt |
| `available_agents` | `list[str]` | `["senior-analyst", "forensic-accounting", "devils-advocate", "final-report"]` |
| `flow` | `str` | Flow identifier (e.g. `"f1"`, `"f10"`) |

### 1.3 Senior-Analyst

Additional fields beyond shared:

| Field | Type | Source |
|---|---|---|
| `question` | `str` | User's prompt |
| `sector_pack` | `str` | Injected from `runtime/packs.py` when a sector match fires |
| `orchestrator_envelope` | `dict` | The orchestrator's full envelope (routing decisions) |
| `citations_block` | `str` | Rendered list of pre-flight tool result citations |

### 1.4 Forensic-Accounting

Additional fields beyond shared:

| Field | Type | Source |
|---|---|---|
| `senior_analyst_envelope` | `dict` | Senior-analyst's output (thesis + findings) |
| `_tool_results_full` | `str` | May contain results from senior-analyst's `tool_directives` in addition to pre-flight |

### 1.5 Devil's Advocate

Additional fields beyond shared:

| Field | Type | Source |
|---|---|---|
| `senior_analyst_envelope` | `dict` | Senior-analyst's thesis to attack |
| `_tool_results_full` | `str` | Same as forensic — pre-flight + senior-extended results |

### 1.6 Final-Report

Additional fields beyond shared:

| Field | Type | Source |
|---|---|---|
| `senior_analyst_envelope` | `dict` | The thesis + bottom_line + bull/bear/attacker |
| `forensic_envelope` | `dict` | Forensic's verdict + red flags |
| `devils_advocate_envelope` | `dict` | The counter-case |
| `orchestrator_envelope` | `dict` | The orchestrator's routing decisions |
| `_tool_results_full` | `str` | All accumulated tool results from the entire flow |

---

## 2. Agent Output Envelopes

Every agent's response is parsed as JSON. The runtime validates the envelope against
required fields using `validate_envelope(envelope, agent_id)` in `runtime.py:93`.

### 2.1 Shared fields (all agents)

| Field | Type | Required | Notes |
|---|---|---|---|
| `agent_id` | `str` | ✅ | Must match the directory name |
| `depth` | `"SCAN" \| "STANDARD" \| "DEEP"` | ✅ | Echoes the depth flag |
| `compressed` | `bool` | ✅ | Echoes the compressed flag, or self-selected |
| `conclusion` | `str` | ✅ | Bottom-line conclusion, conclusion-first |
| `confidence` | `"HIGH" \| "MODERATE_HIGH" \| "MIXED" \| "LOW"` | ✅ | Calibrated to evidence, not tone |
| `findings` | `list[Finding]` | ✅ | Each finding references a `citations[]` entry |
| `gaps` | `list[str]` | ✅ | Always present, even if empty |
| `verification` | `VerificationBlock` | ✅ | `asset_checks`, `connector_status`, `error_flags` |
| `citations` | `list[Citation]` | ✅ | Every claim → a citation ref |
| `next_steps` | `list[str]` | ✅ | Follow-ups, even if empty |

#### Finding shape

```json
{
  "id": "f1",
  "source_agent": "<self | upstream agent>",
  "claim": "One verifiable claim.",
  "evidence": "Specific data/quote/footnote.",
  "source": "Primary source name + location.",
  "url": "https://... | null",
  "as_of": "2026-08-16"
}
```

#### Citation shape

```json
{
  "ref": "f1",
  "type": "PRIMARY | SECONDARY | TERTIARY",
  "name": "Source name",
  "date": "2026-08-16",
  "url": "https://..."
}
```

#### VerificationBlock shape

```json
{
  "asset_checks": [
    { "ticker": "NVDA", "status": "CLEAN | FLAGGED", "note": "..." }
  ],
  "connector_status": [
    { "tool": "sec_edgar", "status": "SUCCESS | PARTIAL | FAILED", "note": "..." }
  ],
  "error_flags": ["any self-detected and corrected error"]
}
```

### 2.2 Orchestrator

**Required fields** (beyond shared): `agent_id`, `answer`, `key_takeaways`, `options`, `evidence`,
`activity`, `confidence`, `verification`, `next_steps`, `compressed`.

| Per-agent field | Type | Notes |
|---|---|---|
| `flow_id` | `str` | The flow identifier |
| `answer` | `str` | The direct answer to the user's question |
| `key_takeaways` | `list[str]` | 3–5 bullet points |
| `options` | `list[dict]` | Actionable options with pros/cons |
| `evidence` | `list[EvidenceRef]` | Routing evidence — which agent to wake for which sub-question |
| `bottom_line` | `BottomLine` | Direction + conviction + flip trigger |
| `disagreements` | `list[dict]` | Where agents disagreed and how resolved |
| `activity` | `list[str]` | Log of routing decisions made |
| `next_steps` | `list[str]` | Which agents to wake and what to brief them with |

#### EvidenceRef shape

```json
{
  "claim": "sub-question to investigate",
  "route_to": "senior-analyst | forensic-accounting | devils-advocate",
  "rationale": "why this agent"
}
```

#### BottomLine shape

```json
{
  "direction": "BUY | HOLD | SELL | ABSTAIN",
  "conviction": 4,
  "flip_trigger": "price ≤ $720 or M-Score < -1.0"
}
```

### 2.3 Senior-Analyst

**Required fields** (beyond shared): `agent_id`, `depth`, `compressed`, `conclusion`, `confidence`,
`thesis`, `bottom_line`, `findings`, `gaps`, `verification`, `citations`, `next_steps`.

| Per-agent field | Type | Notes |
|---|---|---|
| `question_framed` | `str` | The question restated in analytical terms |
| `thesis` | `ThesisBlock` | One_sentence thesis + bull_case + fragile_assumption |
| `bear_case_from_devils_advocate` | `str` | 3–5 paragraphs of the counter-case, attributed to DA |
| `what_an_attacker_would_say` | `str` | The short-seller framing |
| `bottom_line` | `BottomLine` | Direction + conviction + flip trigger |
| `next_three_questions` | `list[str]` | 3 concrete follow-ups |
| `activity` | `list[str]` | Research steps taken |

#### ThesisBlock shape

```json
{
  "one_sentence": "Single-line thesis statement.",
  "bull_case": "3-5 paragraphs of prose with inline citations.",
  "fragile_assumption": "The one assumption this thesis lives or dies by.",
  "primary_source_priorities": ["priority 1", "priority 2"]
}
```

### 2.4 Forensic-Accounting

**Required fields** (beyond shared): `agent_id`, `depth`, `compressed`, `conclusion`, `confidence`,
`verdict`, `findings`, `gaps`, `verification`, `citations`, `next_steps`.

| Per-agent field | Type | Notes |
|---|---|---|
| `verdict` | `"CLEAN" \| "FLAGGED" \| "SEVERELY_FLAGGED"` | The earnings-quality verdict |
| `m_score` | `float \| null` | Beneish M-Score (if calculable) |
| `red_flags` | `list[dict]` | Each flag: `{ "flag": "...", "severity": "HIGH \| MEDIUM \| LOW", "source": "..." }` |

### 2.5 Devil's Advocate

**Required fields** (beyond shared): `agent_id`, `depth`, `compressed`, `conclusion`, `confidence`,
`steelmanned_bull`, `bear_case`, `fragile_assumption`, `what_an_attacker_would_say`,
`findings`, `gaps`, `verification`, `citations`, `next_steps`.

| Per-agent field | Type | Notes |
|---|---|---|
| `steelmanned_bull` | `str` | The strongest version of the bull case (not a straw-man) |
| `bear_case` | `str` | 3–5 paragraphs of the counter-case |
| `fragile_assumption` | `str` | The assumption whose failure kills the bull case |
| `what_an_attacker_would_say` | `str` | The shortest bear framing — a single paragraph |
| `base_rates` | `list[dict]` | Historical analogs: `{ "analog": "...", "n": 14, "outcome": "...", "rate": "62%" }` |

### 2.6 Final-Report

**Required fields** (beyond shared): `agent_id`, `flow_id`, `depth`, `compressed`, `memo`, `confidence`,
`gaps`, `verification`.

| Per-agent field | Type | Notes |
|---|---|---|
| `flow_id` | `str` | Echoed from the flow |
| `memo` | `MemoBlock` | The deliverable — 6 sections |
| `_prior_thesis` | `list[dict] \| null` | Runtime-injected, not generated by the LLM |

#### MemoBlock shape

```json
{
  "bottom_line": {
    "direction": "BUY | HOLD | SELL | ABSTAIN",
    "conviction": 4,
    "flip_trigger": "price ≤ $720 or ...",
    "one_liner": "Single-line verdict."
  },
  "bull_case": "3-5 paragraphs, citation-inlined.",
  "bear_case": "3-5 paragraphs, citation-inlined. DO NOT SOFTEN.",
  "what_an_attacker_would_say": "Single paragraph, short-seller framing.",
  "next_three_questions": ["Q1", "Q2", "Q3"],
  "citations_used": [
    { "ref": "f1", "url": "https://...", "label": "NVDA 10-Q Q3 2026" }
  ]
}
```

---

## 3. Validation Rules

Implemented in `validate_envelope()` at `docs/runtime/runtime.py:93`.

### 3.1 Agent ID check

- `envelope["agent_id"]` must equal the `agent_id` parameter.
- Mismatch is a hard validation failure.

### 3.2 Required field check (per agent)

| Agent | Required fields (13 fields for most) |
|---|---|
| `orchestrator` | `agent_id`, `answer`, `key_takeaways`, `options`, `evidence`, `activity`, `confidence`, `verification`, `next_steps`, `compressed` |
| `senior-analyst` | `agent_id`, `depth`, `compressed`, `conclusion`, `confidence`, `thesis`, `bottom_line`, `findings`, `gaps`, `verification`, `citations`, `next_steps` |
| `forensic-accounting` | `agent_id`, `depth`, `compressed`, `conclusion`, `confidence`, `verdict`, `findings`, `gaps`, `verification`, `citations`, `next_steps` |
| `devils-advocate` | `agent_id`, `depth`, `compressed`, `conclusion`, `confidence`, `steelmanned_bull`, `bear_case`, `fragile_assumption`, `what_an_attacker_would_say`, `findings`, `gaps`, `verification`, `citations`, `next_steps` |
| `final-report` | `agent_id`, `flow_id`, `depth`, `compressed`, `memo`, `confidence`, `gaps`, `verification` |

### 3.3 Validation outcome

- Returns `(ok: bool, failures: list[str])`.
- `ok=True` → envelope is accepted, flow continues.
- `ok=False` → `failures` contains a human-readable list of missing/mismatched fields.
- The runtime may retry the model call if envelope validation fails (currently: 1 retry with a `VALIDATION ERROR` note appended to the brief).

---

## 4. Event Protocol

The runtime yields events that the TUI consumes. Full spec at `docs/frontend/PROTOCOL.md`.
This section lists the event types most relevant to agent schema understanding.

### 4.1 Flow lifecycle

```
FlowStarted → (AgentStarted → AgentChunk* → AgentFinished)* → FlowFinished
```

| Event | Key fields | When |
|---|---|---|
| `FlowStarted` | `flow_id`, `tickers`, `ticker_join`, `thesis_register_snapshot`, `depth`, `compressed` | Start of run |
| `FlowFinished` | `flow_id`, `final_envelope`, `total_cost_usd_estimate` | Successful completion |
| `FlowFailed` | `flow_id`, `reason`, `failed_agent_id`, `partial_envelopes` | Unrecoverable error |

### 4.2 Agent lifecycle

| Event | Key fields | When |
|---|---|---|
| `AgentStarted` | `agent_id`, `model` | Before model call |
| `AgentChunk` | `agent_id`, `delta` | During streaming (future: N per agent; current: 0–1) |
| `AgentFinished` | `agent_id`, `envelope`, `wallclock_s`, `in_tokens`, `out_tokens`, `cost_usd_estimate` | After model call |
| `AgentFailed` | `agent_id`, `reason` | Model call or validation failure |

### 4.3 Thesis register

| Event | Key fields | When |
|---|---|---|
| `ThesisPriorRead` | `ticker`, `prior_theses` (list of dicts) | At flow start |
| `ThesisWritten` | `ticker`, `thesis_id`, `version`, `thesis_text`, `conviction`, `bottom_line`, `evidence_urls` | When f1 finishes successfully |

### 4.4 Cost tracking

| Event | Key fields | When |
|---|---|---|
| `CostDelta` | `agent_id`, `in_tokens`, `out_tokens`, `cost_usd_estimate`, `cumulative_in`, `cumulative_out`, `cumulative_cost` | After each `AgentFinished` |

### 4.5 Connector tool events

| Event | Key fields | When |
|---|---|---|
| `ConnectorRequested` | `tool`, `query`, `requested_by_agent` | Before a tool call |
| `ConnectorCompleted` | `tool`, `status` (`SUCCESS \| PARTIAL \| FAILED \| EMPTY \| UNCHANGED`), `note`, `as_of`, `data_summary` | After a tool call |
| `ConnectorFailed` | `tool`, `error` | When a tool is unreachable |

---

## 5. Tool-Feeding Protocol

The runtime auto-invokes connectors before the senior-analyst runs (pre-flight)
and can invoke additional tools based on `tool_directives` in the senior-analyst's envelope.

### 5.1 Pre-flight

Executed by `_tool_preflight(ticker)` in `runtime.py`. Fires 3 connectors:

| Tool | What it pulls |
|---|---|
| `sec_edgar_fulltext` | CIK lookup + most recent 10-K/10-Q |
| `news_8k` | Recent 8-K filings (7 days) |
| `transcripts` | Recent earnings-call transcripts |

Results are stitched into `_tool_results_full` in every downstream agent's brief.
Failures are soft: a Securly SSL intercept on sec_edgar doesn't stop the flow.

### 5.2 Post-agent directives

When the senior-analyst emits `tool_directives` in its envelope:

```json
[
  {
    "tool": "news_8k",
    "args": { "ticker": "NVDA", "since_days": 30 },
    "reason": "Check for recent material events beyond pre-flight window"
  }
]
```

The runtime dispatches each via `call_tool`, stitches results into `_tool_results_full`,
and the next agent (forensic / devils-advocate / final-report) sees the expanded block.
Cap: 3 directives per envelope. Fail-soft on unknown `tool_id`.

---

## 6. Depth & Compression Modes

### 6.1 Depth tiers

| Mode | Budget (target) | Source minimums |
|---|---|---|
| `SCAN` | ~250 tokens | 1–2 sources, single-line findings |
| `STANDARD` | ~800 tokens | Full findings, full citations |
| `DEEP` | ~2,500 tokens | Every finding cross-confirmed, exhaustive citations |

### 6.2 Compressed flag

When `compressed: true`:
- Reduce prose by ~50–65% — drop articles, hedges, connective sentences.
- Keep **every** fact, number, date, ticker, and citation.
- Compression removes words, never data.

---

## 7. Citation & Grounding Rules

1. **Ground first.** Every claim must come from a source the runtime retrieved *this task*. No memory-only numbers.
2. **Cite inline.** Every factual claim carries `source` + `as_of`. No citation → remove the claim.
3. **Abstain over invent.** If unverifiable, emit in `gaps`. Never "likely ~$X" without a retrieved number.
4. **Chain-of-verification** for material conclusions: draft → list sub-claims → verify each → drop or correct → re-state.
5. **No fabricated URLs/dates.** A citation must reference a source the runtime actually opened.
6. **Cross-source minimums:** ≥ 2 independent sources for a claim; ≥ 3 for a material conclusion.

---

## 8. Model Routing

Models are resolved per-agent using this precedence (implemented in `call_agent`):

1. **`per_agent_model[agent_id]`** — user-configured per-agent override (Settings → Per-agent rail)
2. **`paid_for`** — the `--paid-for <agent_id>` flag routes only that agent to a paid model
3. **`default_model`** — the user's default model selection (Settings → Default rail)

When `per_agent_model` is `None` or not set, fall through to the next tier.
When using OmniRoute or Ollama, cost estimates reflect the actual model pricing
(from `docs/runtime/rates.py`).

---

## 9. Cross-Reference Index

| Concern | Document |
|---|---|
| Event protocol (full spec) | `docs/frontend/PROTOCOL.md` |
| Shared design principles | `docs/prompts/V2-PROMPT-STANDARD.md` |
| Agent system prompts | `docs/prompts/<category>/<agent-id>/system-prompt.md` |
| Envelope validation (source code) | `docs/runtime/runtime.py` → `validate_envelope()` |
| Flow recipes | `docs/flows/f*.md` |
| Connector catalog | `docs/frontend/connectors_catalog.py` |
| Cost tables | `docs/runtime/rates.py` |
| Thesis register schema | `docs/runtime/thesis_register/register.py` |

---

*Maintained alongside the 5 system prompts. Update this document when you change an agent's required fields or add a new agent.*