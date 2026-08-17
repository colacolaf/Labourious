# Flow f1 — Analyze Ticker (Flagship)

> The flagship. **"Analyze [TICKER]"** produces a memo a Wharton team could send to a PM with edits, an analyst could read before a thesis conversation, or a retail user could rely on for a defensible first view. Every other flow is a variation of this recipe.

## What it answers

> *"What's the thesis on [TICKER] at the current price? Should I own it / hold it / sell it / wait?"*

The deliverable is a memo addressing the user's decision frame. The output's `bottom_line` carries the directional verdict, conviction (1-5), and the flip trigger — a concrete price or event that would change the view.

## Inputs

| Field | Required? | What it carries |
|-------|-----------|------------------|
| `ticker` | yes | The ticker to analyze (e.g. `NVDA`). |
| `as_of` | optional | Override the current date for re-running historical analysis. |
| `flow_context` | optional | User's portfolio (sector exposure, cost basis) — informs RELEVANT HISTORY. |
| `depth` | optional | `SCAN | STANDARD | DEEP`. Default STANDARD. |
| `compressed` | optional | bool. Default false. |
| `model` | required | `--model ollama/llama3.3:70b | groq/... | anthropic/claude-sonnet-4-5` |
| `paid_for` | optional | `--paid-for final-report` — hybrid routing. |

The runtime pre-loads:
- `thesis_register.read_thesis(ticker, since=14d)` for RELEVANT HISTORY.
- LLM adapter and tool layer per the user config.

## Wave plan

```
Wave 1 (sequential):
   ➤ senior-analyst
     - frame the question
     - build thesis skeleton
     - decide specialists

Wave 2 (parallel):
   ➤ forensic-accounting   (DEPTH matches brief, default STANDARD)
   ➤ devils-advocate       (DEPTH matches brief, default STANDARD)

Wave 3 (sequential):
   ➤ final-report (assemble; default DEPTH = senior-analyst's DEPTH)

Post-flow:
   ➤ thesis_register.write_thesis(...)
   ➤ cost.json updated
```

## Rubric

> **The single-ticker thesis memo.**
> Goal: deliver a defensible first view on a public company to a busy reader. The reader skims the bottom line + bull + bear + next questions + citations in 30 seconds and decides whether to trust the memo further.
>
> Reading order: Bottom line → Bull case → Bear case → What an attacker would say → Next three questions → Citations.

Sections the memo will contain (in this order, no others):

1. **Bottom line** — direction + conviction + flip trigger + ≤140-char one-liner.
2. **Bull case** — 3–5 paragraphs.
3. **Bear case** — 3–5 paragraphs, **verbatim or near-verbatim from devils-advocate**.
4. **What an attacker would say** — 1 paragraph from devils-advocate.
5. **Next three questions** — 3 bullets, optimizing for "questions the busy reader will ask next."
6. **Citations** — list of every claim's source.

## Output

```jsonc
{
  "agent_id": "final-report",
  "flow_id": "f1",
  "memo": { ... },                  // 6-section template as above
  "confidence": "HIGH | ... | LOW",
  "gaps": ["..."],
  "verification": { ... }
}
```

The runtime:
1. Parses the envelope.
2. Renders markdown via `templates/memo.md.j2` into `docs/runtime/.runs/<run_id>/memo.md`.
3. Writes the thesis_register row.
4. Logs `cost.json`.
5. Returns markdown to stdout (CLI) or to the UI.

## Acceptance

A run of f1 is "ship-ready" when:

- All 5 standard evals pass on the same flow + model + ticker — see `docs/runtime/evals/`.
- A skeptical human (not the author) reads the memo and says: *"I'd send this to my PM with edits."*
- The Dalton test (Skim: bottom line alone must convey direction + conviction + flip trigger).
- The Bear test (the memo's bear case must include at least one specific argument not in the bull case).
- The Citation test (≥80% of numerical claims cited to a primary-source URL).

## Skipped calls (allowed)

- `forensic-accounting` may be SKIPPED only if the user's flow_context excludes financial deep-dive (rare f1 case — e.g. sentiment-only questions routed here by mistake; should go to f6 or a different flow).
- `devils-advocate` is **never** SKIPPED on f1. The bear case is the whole point of the deliverable.

## Failure modes + recovery

| Failure | Recovery |
|---------|----------|
| Senior-analyst output sparse (no fragile_assumption) | Re-brief with explicit ask. |
| Forensic-accounting tool call FAILED | Mark `connector_status: FAILED`; surface in `gaps`; proceed. |
| Devils-advocate refuses (THESIS too weak) | Re-brief senior-analyst; do not fabricate. |
| Final-report `confidence: MIXED` | Surface in memo's bottom line; never suppress. |

## Re-running

A re-run of f1 on the same ticker within 14 days:
- Loads the prior thesis from `thesis_register`.
- Surfaces the prior conclusion as RELEVANT HISTORY.
- Computes and surfaces a "what changed" delta in the memo's bottom line's `flip_trigger`.

## Wallclock target

- All-free (Ollama Llama 3.3 70B): **5–10 minutes**.
- Hybrid (free + Sonnet for final-report): **3–5 minutes**.
- All-paid (Sonnet): **2–3 minutes**.

## Cost target

| Mode | Cost / run |
|------|------------|
| All-free | $0 |
| Hybrid | $0.05–$0.30 |
| All-paid | $0.30–$1.00 |

## Out of scope (f1)

- Portfolio-level allocation. Use f5 (sector deep-dive) or a future portfolio flow.
- Real-time prices. f1 uses daily OHLCV.
- Options strategy. Out of scope permanently.
- Cross-ticker comparison. Use f2.
- Earnings-specific rubrics. Use f3/f4.

F1 is **the canonical "do one thing well"**. The other 7 flows are deliberate variants — they exist because the user has a slightly different question, not because f1 is broken.
