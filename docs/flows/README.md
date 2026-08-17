# Flows — Recipes that use the 5 prompts as ingredients

> **The 5 prompts in `docs/prompts/` are ingredients.** The 8 flows in this directory are the menu. Pick a flow; the runtime orchestrates the 5 prompts in the order the flow says.

## What a flow defines

A **flow** is a thin recipe. Each flow file says six things:

1. **What it answers** (the user question this flow serves).
2. **Inputs** (what the user provides; what the runtime must pre-load).
3. **Wave plan** (which of the 5 prompts run, in what order, with what DEPTH).
4. **Rubric** (the analytic lens — what's the deliverable's shape?).
5. **Output** (the deliverable format and where it lives).
6. **Acceptance** (the eval criteria specific to this flow).

Every flow reuses the 5 prompts. **No flow adds new prompts.** Sectors, asset classes, deliverable variations — all are rubric or knowledge-pack adjustments within a flow, not new flows.

## The 8 flows

| # | Flow | User question it serves | Reuses |
|---|------|-------------------------|--------|
| **f1** | Analyze ticker | "What's the thesis on [TICKER]?" | All 5 — flagship |
| **f2** | Compare tickers | "A vs B vs C — which wins?" | All 5 — comparison rubric |
| **f3** | Earnings preview | "What should I watch on [TICKER]'s next print?" | 4 (no devils-advocate at SCAN/STD) |
| **f4** | Earnings review | "What changed after [TICKER]'s print?" | All 5 — what-flipped rubric |
| **f5** | Sector deep-dive | "Map out [sector] — who's exposed, who wins?" | All 5 — cross-name rubric |
| **f6** | Thematic screen | "Find names that match [thesis]" | Lead + review-pass — screen rubric |
| **f7** | Risk event | "[News event] just hit — what's the read?" | All 5 — event-driven rubric |
| **f8** | Macro overlay | "How does [macro shock] hit my thesis?" | Lead + forensic — macro-frame rubric |

## Wave-plan defaults

The 5 prompts always follow a 3-wave pattern unless explicitly noted:

| Wave | Agents | Order |
|------|--------|-------|
| **1** | senior-analyst | sequential, alone |
| **2** | forensic-accounting + devils-advocate | parallel to each other, sequential to wave 1 |
| **3** | final-report | sequential, after wave 2 |

Variations:
- **f6 (thematic screen)** runs in batch over many tickers — orchestrator loops over senior-analyst with DEPTH=SCAN, then re-runs the survivors at DEPTH=STANDARD with full specialists.
- **f3 (earnings preview)** SCAN pas may drop devils-advocate (`next_three_questions` covers the "what could go wrong" beat at low cost).
- **f8 (macro overlay)** may drop forensic-accounting on already-vetted names.

## Hybrid model routing (default)

When the runtime is in hybrid mode (`--paid-for final-report`):
- Orchestrator + senior-analyst + specialists → free model (`ollama/llama3.3:70b` or `groq/llama-3.3-70b-versatile`).
- **final-report only → Sonnet 4.5** (paid) — to close the prose / adversarial-reasoning gap on free models.

When in all-free mode: every prompt goes through the same free adapter.

A typical f1 run costs **~$0.10–$0.30 in hybrid mode** and **$0 in all-free mode**.

## Thesis register integration

Every flow:
1. **Reads** the prior thesis from `thesis_register` at flow start (if one exists for the ticker or theme). `RELEVANT HISTORY` in the senior-analyst's brief carries it.
2. **Writes** a new versioned thesis (or update row) on successful completion. The previous thesis is preserved.

Without this step, the system has no durable memory. With it, every run *gets better* by reading the last time the system thought about this name.

## Eval-suite integration

Each flow file names the 5 standard evals (`docs/runtime/evals/`) and any flow-specific ones. A flow ships when:
- All 5 standard evals pass against a calibrated baseline.
- The human-readable deliverable pastes through the litmus test in [`docs/USER-JOBS.md`](../USER-JOBS.md) — Trust, Action, Speed, Defensibility, Comparison.

## Index of flows

| File | Purpose |
|------|---------|
| [`f1-analyze-ticker.md`](f1-analyze-ticker.md) | Flagship: single-ticker memo |
| [`f2-compare-tickers.md`](f2-compare-tickers.md) | Side-by-side, ranked |
| [`f3-earnings-preview.md`](f3-earnings-preview.md) | Pre-print: what to watch |
| [`f4-earnings-review.md`](f4-earnings-review.md) | Post-print: what flipped |
| [`f5-sector-deep-dive.md`](f5-sector-deep-dive.md) | Cross-name landscape |
| [`f6-thematic-screen.md`](f6-thematic-screen.md) | Filter for thesis-fit |
| [`f7-risk-event.md`](f7-risk-event.md) | Single news event → exposure map |
| [`f8-macro-overlay.md`](f8-macro-overlay.md) | Macro shock → portfolio impact |

## How to add a new flow (without adding agents)

1. Define the user question clearly (which of the 5 user jobs does it serve?).
2. Pick the wave plan from the defaults; deviate with justification.
3. Write the rubric: 1 paragraph that defines the analytic lens.
4. Define the output shape.
5. Name the eval acceptance criteria (start from the 5 standard evals; add flow-specific test cases).
6. Run the existing evals + the new ones; ship when green.

If you ever feel the urge to add a new prompt — *stop*. The 5 prompts are the steady state. **A new flow is a recipe, not a new chef.**
