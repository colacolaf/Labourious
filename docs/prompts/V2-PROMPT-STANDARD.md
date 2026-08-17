# V2 Prompt Standard — The Analyst's Bench

> The single source of truth for the 5 system prompts in `docs/prompts/`. **Every prompt is self-contained** — an agent at runtime sees only its own prompt. They share a JSON envelope, share protocols (hallucination / source / asset / connector / error-detection), and follow the same section skeleton so the runtime can parse outputs uniformly.

> **Sources of truth for the design:** Anthropic *"How we built our multi-agent research system"* (Jun 2025), Anthropic *"Effective context engineering for AI agents"* (Sep 2025), Anthropic *"Writing effective tools for agents"* (Sep 2025), Anthropic *"Building Effective Agents"* (Dec 2024), Hugging Face *"smolagents — Building good agents"*, OpenAI function-calling guidance.

## Scope

**The 5 prompts in the v2 roster:**
- `orchestrator` — routing, wave planning, synthesis.
- `senior-analyst` — lead; frames questions, owns the thesis, coordinates specialists.
- `forensic-accounting` — specialist; earnings quality, M-Score, red flags.
- `devils-advocate` — specialist; mandatory counter-case.
- `final-report` — deliverable writer; bottom line + bear + next questions + citations.

**Per-agent variations belong in the prompt itself, not the standard.** Routing details, brief formats, and per-flow recipes live in the prompt text or in `docs/flows/`.

## 1. Design principles

1. **Every claim is grounded or it doesn't ship.** A factual claim without a citation to a source the agent *actually retrieved this task* is a hallucination, not a finding. The prompt must make producing an uncited claim structurally impossible.
2. **Effort scales to the question, never uncapped.** Anthropic found token spend explained 80% of performance variance — but multi-agent burns ~15× chat tokens. So every agent reads `DEPTH` from its brief and applies a matching tier. Spend tokens where the question earns them.
3. **Examples > rules.** Few-shot outputs do more heavy lifting than a laundry list of edge cases. Every prompt ships 2–3 worked examples including at least one *failure-mode correction* (a bad output being caught and fixed).
4. **Right altitude.** Specific heuristics, not brittle if-else logic and not vague generalities. Every routing decision is a named trigger.
5. **Context is a finite resource.** Outputs are dense and structured. Specialists never pass raw tool dumps to leads; leads never pass raw specialist transcripts to the orchestrator. JSON carries facts; prose carries only what prose must.
6. **Negative space.** Each prompt states what the agent does *not* do, to stop scope creep.
7. **Functional, not persona.** The lead is neutral — no celebrity voice, no fund name. The system's edge is *discipline*, not character.

## 2. Section skeleton (all 5 prompts)

The agent's prompt is structured into 14 sections. All five prompts use the same skeleton; only the domain content differs.

| # | Section | Purpose |
|---|---------|---------|
| 1 | **Identity & Role** | who, what they own, in one block |
| 2 | **Role & Scope** | in-scope / out-of-scope / authority / interfaces |
| 3 | **Decision Framework** | step-by-step process, mental models, named biases |
| 4 | **Intake** | how the prompt parses its brief; when to push back vs proceed |
| 5 | **Delegation & Routing** *(leads only)* | which specialists to wake, triggers, brief format |
| 6 | **Effort & Token Modes** | `SCAN / STANDARD / DEEP` + `COMPRESSED` flag |
| 7 | **Data Freshness** | per-data-type windows; default |
| 8 | **Hallucination Guardrails** | grounding, citation, abstain, chain-of-verification |
| 9 | **Source & Asset Verification** | per-asset identity gates + cross-source minimums |
| 10 | **Tool-Use Protocol** | what tools the agent needs, when, failure handling |
| 11 | **Error Detection & Correction** | self-verify checklist, error types, correction rules |
| 12 | **Structured Output Contract** | `FROM / TO` header + JSON envelope (below) |
| 13 | **Quality Gates** | final QA checklist before returning |
| 14 | **Worked Examples** | 2–3 few-shot incl. one failure-mode correction |

## 3. Common JSON envelope

The orchestrator, senior-analyst, and final-report share a near-uniform envelope:

```json
{
  "agent_id": "<matches directory name>",
  "flow_id": "f1 | f2 | ... | null for Lane A",
  "depth": "SCAN | STANDARD | DEEP",
  "compressed": false,
  "conclusion": "Bottom-line conclusion, conclusion-first.",
  "confidence": "HIGH | MODERATE_HIGH | MIXED | LOW",
  "findings": [
    {
      "id": "f1",
      "source_agent": "<self name> | <upstream name>",
      "claim": "One verifiable claim.",
      "evidence": "The specific data/quote/footnote that supports the claim.",
      "source": "Primary source name + location (e.g. 'NVDA 10-Q Q3 2026, Note 2b, p.47').",
      "url": "https://... or null",
      "as_of": "2026-08-16"
    }
  ],
  "tensions": [
    { "issue": "Where sources disagree.", "parties": ["source A", "source B"], "resolution": "How resolved." }
  ],
  "gaps": ["What we could not verify."],
  "verification": {
    "asset_checks": [
      { "ticker": "NVDA", "status": "CLEAN | FLAGGED", "note": "Identity/freshness/price check result." }
    ],
    "connector_status": [
      { "tool": "sec_edgar | market_data | news | web_fetch",
        "status": "SUCCESS | PARTIAL | FAILED",
        "note": "What was retrieved or why it failed." }
    ],
    "error_flags": ["Any self-detected error, corrected, or its impact."]
  },
  "citations": [
    { "ref": "f1", "type": "PRIMARY | SECONDARY | TERTIARY", "name": "...", "date": "2026-08-16", "url": "https://..." }
  ],
  "next_steps": ["Concrete follow-ups if any."]
}
```

**Per-agent extensions:**

- **Orchestrator envelope** adds `flow_id`, `bottom_line`, `key_takeaways`, `options`, `evidence[]` (routing), `disagreements[]`, `activity[]`.
- **Senior-Analyst envelope** adds `question_framed`, `thesis`, `bear_case_from_devils_advocate`, `what_an_attacker_would_say`, `bottom_line` (direction+conviction+flip_trigger), `next_three_questions`, `activity[]`.
- **Forensic Accounting envelope** adds `verdict: "CLEAN | FLAGGED | SEVERELY_FLAGGED"`.
- **Devil's Advocate envelope** adds `steelmanned_bull`, `bear_case`, `fragile_assumption`, `what_an_attacker_would_say`, `base_rates[]`.
- **Final Report envelope** adds `memo` (the deliverable) with `bottom_line`, `bull_case`, `bear_case`, `what_an_attacker_would_say`, `next_three_questions`, `citations_used`.

Field rules (all envelopes):
- `agent_id` MUST match the directory name.
- `confidence` is calibrated to evidence, not tone. `HIGH` = multiple independent sources + primary evidence. `MIXED` = genuine disagreement or thin data.
- Every `findings[].claim` MUST have a matching `citations[]` entry via `ref → id`.
- `gaps` and `error_flags` are always present, even if empty arrays. Silence is not allowed to hide a gap.

## 4. Effort & Token Modes

Every agent reads `DEPTH` from its brief and applies the matching tier. `COMPRESSED` is orthogonal.

| Mode | Meaning | Output budget (target, not hard cap) |
|------|---------|--------------------------------------|
| **SCAN** | Top-line only — 1–2 most relevant sources/specialists, single-line findings | ≤ ~250 tokens |
| **STANDARD** | Normal coverage — full findings, full citations | ≤ ~800 tokens |
| **DEEP** | Exhaustive — every finding cross-confirmed/contradicted, full citation set | ≤ ~2,500 tokens |

**COMPRESSED** mode (flag set in brief, or self-selected when the answer is simple): reduce prose by ~50–65% — drop articles, hedges, connective sentences, empty qualifiers — while keeping **every** fact, number, date, ticker, and citation. Compression removes words, never data.

**Rules that always hold:**
- Never truncate a fact/number/date/citation to fit a budget.
- Never invent a source to fill a `NOT FOUND` result.
- If a result is empty, say so in the mode's minimal form: *"No results for [query] within [window]."*

## 5. Shared protocols (inlined into every prompt)

### 5.1 Hallucination guardrails
1. **Ground first.** A claim may only appear if it comes from a source the runtime retrieved *this task*. No memory-only numbers, dates, or prices.
2. **Cite inline.** Every factual claim carries `source` + `as_of`. **No citation ⇒ remove the claim.**
3. **Abstain over invent.** If you can't verify, emit `NOT FOUND` / `UNVERIFIED` in `gaps`. Never say "likely", "probably ~$X", or "reported around" with an unretrieved number.
4. **Chain-of-verification** for material conclusions: draft → list sub-claims → verify each against the retrieved source → drop or correct → re-state.
5. **No fabricated URLs/dates.** A citation must be a source the runtime actually opened.

### 5.2 Source & asset verification
- **Per-asset gate:** for every ticker/security, confirm identity (symbol ↔ name ↔ exchange), current price (with timestamp), most recent filing/earnings date, and any corporate action — *before* analysis. Record in `verification.asset_checks`.
- **Cross-source minimums:** ≥ 2 independent sources for a factual claim; ≥ 3 for a material conclusion.
- **Source quality ladder:** SEC EDGAR / official filings / issuer IR / regulator > major wire > established research > trade press > blogs. Flag the rung.

### 5.3 Tool-use protocol (coordinated with runtime)
- Every prompt section §10 lists tools the agent needs and the failure handling.
- The runtime enforces the actual call; the prompt describes the *step the agent wants the tools to do*, not the API call itself.
- After every tool call, the runtime records `SUCCESS | PARTIAL | FAILED` in the envelope's `verification.connector_status`.

### 5.4 Error detection & correction
- **Self-verify before returning:** re-read your own `findings` and check (a) every number appears in its cited source, (b) no two findings contradict, (c) no ticker is confused with a similarly-named one, (d) dates are not stale against the freshness window.
- **Correction rule:** if you catch an error, fix it and note it in `verification.error_flags`; if you can't fix it, move the affected claim to `gaps`.

## 6. Conventions

- **Directory:** `docs/prompts/<category>/<agent-id>/system-prompt.md`. Agent-id from the JSON envelope's `agent_id`.
- **Self-contained prompts:** must not depend on this doc or on sibling prompts at runtime — every prompt includes the full V2 standard inline.
- **Consistency:** all 5 prompts use the same sections, JSON envelope, and shared protocols.
- **Maintenance:** when the JSON envelope changes here, update every prompt's §12 to match. When a shared protocol changes here, update every prompt's §8/§9/§11 to match.

## 7. What isn't here (and where it lives)

| Concern | Lives in |
|---------|----------|
| Per-flow recipes, rubrics, wave plans | `docs/flows/f1..f8.md` |
| Routing decisions between the 5 prompts | The orchestrator prompt's §3–§5 |
| Tool adapters and their APIs | `docs/runtime/tools/` |
| Model adapters and their APIs | `docs/runtime/adapters/` |
| Per-flow quick commentary | `docs/flows/f1..f8.md` |

---

*Maintained alongside `docs/prompts/`. Single source of truth for the v2 design. If you change this, change every prompt.*
