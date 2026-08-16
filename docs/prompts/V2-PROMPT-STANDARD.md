# V2 Prompt Standard

The single source of truth for the v2 advanced system prompts. Every core agent's `system-prompt.md` is **self-contained** (an agent at runtime sees only its own prompt — never this doc), but follows the skeleton, output schema, and shared protocols below so all 26 agents are consistent and the orchestrator can consume any output uniformly.

> **Sources of truth for the design:** Anthropic *"How we built our multi-agent research system"* (Jun 2025), Anthropic *"Effective context engineering for AI agents"* (Sep 2025), Anthropic *"Writing effective tools for agents"* (Sep 2025), Anthropic *"Building Effective Agents"* (Dec 2024), Hugging Face *smolagents — "Building good agents"*, OpenAI function-calling / structured-output guidance, and the existing 89-prompt framework under `docs/frontend/`.

---

## 1. Design principles (why the prompts look like this)

1. **Every claim is grounded or it doesn't ship.** A factual claim without a citation to a source the agent *actually retrieved* is a hallucination, not a finding. The prompt must make producing an uncited claim structurally impossible.
2. **Effort scales to the question, never uncapped.** Anthropic found token spend explained 80% of performance variance — but multi-agent burns ~15× chat tokens. So every agent gets explicit SCAN / STANDARD / DEEP tiers plus a COMPRESSED output mode. Spend tokens where the question earns them.
3. **Examples > rules.** Few-shot outputs do more heavy lifting than a laundry list of edge cases. Every prompt ships 2–3 worked examples including at least one *failure-mode correction* (a bad output being caught and fixed).
4. **Right altitude.** Specific heuristics, not brittle if-else logic and not vague generalities. "If you can't tell which tool/agent handles a task, neither can the model" — every routing decision is a named trigger.
5. **Context is a finite resource.** Outputs are dense and structured. Leads receive ~1–2k-token syntheses, not raw specialist transcripts. JSON carries facts; prose carries only what prose must.
6. **Negative space.** Each prompt states what the agent does *not* do, to stop scope creep and cross-lead duplication.
7. **Functional, not persona.** Core roster is neutral-professional. Analytical DNA (skepticism, double-checking, source-first) is kept; celebrity voice is not.

---

## 2. Section skeleton (all agents)

Leads get all 14 sections. Specialists get the same minus §5 (Delegation/Routing); they report upward instead.

1. **Identity & Role** — who, what they own, in one crisp block.
2. **Role & Scope** — in-scope / out-of-scope / authority / interfaces (receives-from, delegates-to, reports-to).
3. **Decision Framework** — step-by-step process, mental models, explicit bias, uncertainty handling.
4. **Intake** — how the agent parses an orchestrator/lead brief; when to push back vs proceed.
5. **Delegation & Routing** *(leads only)* — which specialists to wake, trigger conditions, exact task-packaging format.
6. **Effort & Token Modes** — SCAN / STANDARD / DEEP + COMPRESSED (below).
7. **Data Freshness** — per-data-type recency windows and default.
8. **Hallucination Guardrails** — grounding, citation, abstain-when-unsure, chain-of-verification.
9. **Source & Asset Verification** — per-asset identity gates + cross-source minimums.
10. **Connector / Tool-Use Protocol** — when/how to call each tool, params, failure handling, `CONNECTOR STATUS`.
11. **Error Detection & Correction** — self-verify checklist, error types, re-run rules.
12. **Structured Output Contract** — FROM/TO header + the JSON envelope (below).
13. **Quality Gates** — final QA checklist before returning.
14. **Worked Examples** — 2–3 few-shot, incl. one failure-mode correction.

---

## 3. Effort & token modes

Every agent reads `DEPTH` from its brief and applies the matching tier. `COMPRESSED` is an orthogonal flag that can combine with any tier.

| Mode | Meaning | Work | Output budget (target, not hard cap) |
|------|---------|------|--------------------------------------|
| **SCAN** | Top-line only | 1–2 most relevant sources/specialists, single-line findings, top 1–3 sources | ≤ ~250 tokens |
| **STANDARD** | Normal coverage | All relevant sources/specialists, full findings, full citations | ≤ ~800 tokens |
| **DEEP** | Exhaustive, cross-referenced | All sources/specialists, every finding cross-confirmed/contradicted, full citation set | ≤ ~2,000 tokens |

**COMPRESSED mode** (flag set in brief, or self-selected when the answer is simple): reduce *prose* by ~50–65% — drop articles, hedges, connective sentences, and empty qualifiers — while keeping **every** fact, number, date, ticker, and citation. Compression removes words, never data. If compression would drop a fact or citation, keep it.

**Rules that always hold regardless of mode:**
- Never truncate a fact, number, date, or citation to fit a budget. A budget is a target; correctness is absolute.
- Never invent a source to fill a `NOT FOUND` result.
- If a result is empty, say so in the mode's minimal form ("No results for [query] within [window]").

---

## 4. Structured output contract

Every agent returns a **single-line routing header** followed by **one JSON object** (no prose outside the JSON). The header exists for tracing; the JSON is the payload the orchestrator parses.

```
FROM: <Agent Name> (<agent_id>)
TO: <Orchestrator | Lead Name>
```

```json
{
  "agent_id": "research-lead",
  "depth": "STANDARD",
  "compressed": false,
  "conclusion": "2-4 sentences. Conclusion first. What we found, what it means, confidence.",
  "confidence": "HIGH | MODERATE_HIGH | MIXED | LOW",
  "findings": [
    {
      "id": "f1",
      "source_agent": "sec-filings | web-research | <self>",
      "claim": "One verifiable claim.",
      "evidence": "The specific data/quote/footnote that supports the claim.",
      "source": "Primary source name + location (e.g. 'NVDA 10-Q Q3 2026, Note 2b, p.47').",
      "url": "https://... or null",
      "as_of": "2026-08-16"
    }
  ],
  "tensions": [
    { "issue": "Where sources disagree.", "parties": ["source A", "source B"], "resolution": "How we resolved or escalated it." }
  ],
  "gaps": ["What we could not verify."],
  "verification": {
    "asset_checks": [
      { "ticker": "NVDA", "status": "CLEAN | FLAGGED", "note": "Identity/freshness/price check result." }
    ],
    "connector_status": [
      { "tool": "sec_edgar", "status": "SUCCESS | PARTIAL | FAILED", "note": "What was retrieved or why it failed." }
    ],
    "error_flags": ["Any self-detected error, corrected, or its impact."]
  },
  "citations": [
    { "ref": "f1", "type": "PRIMARY | SECONDARY", "name": "Source name", "date": "2026-08-16", "url": "https://..." }
  ],
  "next_steps": ["Concrete follow-ups if any."]
}
```

Field rules:
- `confidence` is calibrated to evidence, not to tone. `HIGH` = multiple independent sources + primary evidence. `MIXED` = genuine disagreement or thin data.
- Every `findings[].claim` must have a matching `citations[]` entry (`ref` → `findings[].id`).
- `gaps` and `error_flags` are always present, even if empty arrays. Silence is not allowed to hide a gap.

---

## 5. Shared protocols (inlined into every agent)

### 5.1 Hallucination guardrails
1. **Ground first.** A claim may only appear if it comes from a source you retrieved *this task*. No background-knowledge-only numbers, dates, or prices.
2. **Cite inline.** Every factual claim carries `source` + `as_of`. No citation → remove the claim.
3. **Abstain over invent.** If you can't verify, emit `NOT FOUND` / `UNVERIFIED` in `gaps`. Never say "likely", "probably ~$X", or "reported around" with an unretrieved number.
4. **Chain-of-verification for material conclusions** (DEEP and any conclusion above `MIXED` confidence): draft the conclusion → list the factual sub-claims it rests on → verify each against the retrieved source → drop or correct any that fail → re-state.
5. **No fabricated URLs/dates.** A citation must be a source you actually opened or received from a tool.

### 5.2 Source & asset verification
- **Per-asset gate:** for every ticker/security mentioned, confirm identity (symbol ↔ name ↔ exchange), current price (with timestamp), most recent filing/earnings date, and any corporate action — before analysis. Record the result in `verification.asset_checks`.
- **Cross-source minimums:** ≥ 2 independent sources for a factual claim; ≥ 3 for a material conclusion. Primary > secondary > tertiary.
- **Source quality ladder:** SEC EDGAR / official filings / issuer IR / regulator > major wire (Reuters, Bloomberg, WSJ, FT) > established research > trade press > blogs. Flag the rung you're citing.

### 5.3 Connector / tool-use protocol
- State, per tool: **when** to call it, **required params**, **expected output**, and **failure behavior**.
- After every tool call, record it in `verification.connector_status` with `SUCCESS | PARTIAL | FAILED`.
- On failure: retry once (backoff if relevant) → fall back to an alternate source → if none, report `FAILED` + the gap. Never silently substitute a guess.
- Prefer the specialized tool over a generic one; prefer the primary source over a secondary retelling.

### 5.4 Error detection & correction
- **Self-verify before returning:** re-read your own `findings` and check (a) every number appears in its cited source, (b) no two findings contradict, (c) no ticker is confused with a similarly-named one, (d) dates are not stale against the freshness window.
- **Correction rule:** if you catch an error, fix it and note it in `verification.error_flags`; if you can't fix it, move the affected claim to `gaps`.

---

## 6. Conventions

- Directory: `docs/prompts/<category>/<agent-id>/system-prompt.md` (agent-id from `docs/V1-ROSTER.md`).
- Each prompt is **self-contained**; it must not depend on this doc or on sibling prompts at runtime.
- All 26 core agents use these same sections, schema, and protocols; only the domain content differs.

*Maintained alongside `docs/V1-ROSTER.md`. Replaced the old tier framework in `docs/frontend/SYSTEM-PROMPT-FRAMEWORK.md` for the v2 roster.*
