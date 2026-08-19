# Flow f3 — Earnings Preview

> *"What should I watch on [TICKER]'s next print?"* — the recurring event-driven analyst task.

## What it answers

> *"On [ticker]'s next earnings release, what are the 3–5 things that will move the stock most, and what's our base-case reaction function for each?"*

The deliverable is shorter than f1: it's a **pre-mortem**, not a full thesis. Used by a trader or PM the morning of the print.

## Inputs

| Field | Required? | What it carries |
|-------|-----------|------------------|
| `ticker` | yes | e.g. `NVDA`. |
| `earnings_date` | yes | e.g. `2026-11-20`. |
| `thesis_id` | optional | Reference to existing thesis_register row (=> RELEVANT HISTORY). |
| `depth` | optional | Default SCAN to STANDARD. |
| `model` | required | Per-adapter flag. |

## Wave plan

```
Wave 1 (sequential):
  ➤ senior-analyst (DEPTH=SCAN or STANDARD)
       - frame as "what to watch"
       - use thesis_register to surface the prior thesis; identify what this print would change

Wave 2 (parallel):
  ➤ forensic-accounting (DEPTH=SCAN)
       - 3 key metrics to watch (rev growth adj/GAAP, gross margin, FCF gen)
  ➤ devils-advocate (DEPTH=SCAN, optional at f3)
       - worst-case plausibility check: "if X is bad, what happens to thesis Y?"

Wave 3 (sequential):
  ➤ final-report (DEPTH = max(senior-analyst, specialists))
       - assemble the pre-mortem memo
```

**Devils-advocate at f3 is the cheapest "what an attacker would say" beat.** If it's SKIPPED, the memo's `confidence` should reflect that. **Standard behaviour: include it on a SCAN DEPTH.**

## Rubric

> **The pre-mortem.**
> Goal: produce a 3-section memo focused on the upcoming print.
>
> Structure:
> 1. **What to watch** — 3–5 bullets ranked by likely impact on the stock.
> 2. **Reaction function** — for each bullet, "if [X]: stock goes [way] by [magnitude]" with reasoning.
> 3. **What the print says about the prior thesis** — explicit YES/NO/MIXED framework: "if [print result], then the prior thesis [stands/shifts/breaks]".
> 4. **Citations** — list.

## Output

```jsonc
{
  "agent_id": "final-report",
  "flow_id": "f3",
  "memo": {
    "what_to_watch": [{ "metric": "...", "importance": "HIGH | MEDIUM | LOW", "rationale": "..." }],
    "reaction_function": [
      { "metric": "...", "if_x": "...", "then_stock": "..." , "magnitude_reasoning": "..." }
    ],
    "thesis_implication": {
      "if_print_a": "thesis stands",
      "if_print_b": "thesis shifts",
      "if_print_c": "thesis breaks"
    },
    "citations": [...]
  }
}
```

## Acceptance

- All 5 standard evals pass.
- **The Coverage test** (added to evals): exactly 3–5 metrics in `what_to_watch`; no more, no fewer (less is risky; more dilutes attention).
- **The Reaction test**: every metric has a reaction function (no orphan bullets).
- **The Thesis-link test**: the `thesis_implication` is present and explicit.

## Skipped calls

- `devils-advocate` is *optional* at f3 (unlike f1/f2). SKIP if the user explicitly says "just the consensus check, no bear case".

## Wallclock target

- All-free: **3–6 minutes** (SCAN-heavy).
- Hybrid / all-paid: **2–4 minutes**.

Cost: roughly **half of f1**.

## Out of scope (f3)

- Full thesis re-derivation. Use f1.
- Comparison prints across peer set. Use f2 with `rubric = "earnings print at [date]"`.
- Post-mortem. Use f4.

---

## Implementation notes (post-build)

This section covers the running implementation in `execute_flow_f3`.

### Wave plan (light, deliberately not parallel)

```
pre-wave (sequential):
  ➤ load prior thesis from register → RELEVANT HISTORY
wave 1 (sequential):
  ➤ senior-analyst at DEPTH=SCAN — frame "what to watch"
      with prior thesis context
wave 2 (sequential):
  ➤ forensic-accounting SCAN — 3 measurable metrics
      (rev growth, gross margin, FCF gen by default)
wave 2b (optional — `--skip-devil` to drop):
  ➤ devils-advocate SCAN — bear-case plausibility check
wave 3 (sequential):
  ➤ final-report — assembles the pre-mortem memo
post-wave (sequential):
  ➤ register.add_catalyst(ticker, event='earnings_print:YYYY-MM-DD',
                              expected_date, what_to_watch)
  → produces catalyst_id so f4 can resolve it after the print
```

### Memo shape

```json
{
  "flow_id": "f3",
  "memo": {
    "what_to_watch": [
      { "metric": "revenue growth", "importance": "HIGH", "rationale": "..." },
      { "metric": "gross margin",    "importance": "MEDIUM", "rationale": "..." },
      { "metric": "FCF gen",         "importance": "MEDIUM", "rationale": "..." }
    ],
    "reaction_function": [
      { "metric": "revenue growth", "if_x": "<8% YoY",
        "then_stock": "-8%", "magnitude_reasoning": "..." }
    ],
    "thesis_implication": {
      "if_print_a": "thesis stands",
      "if_print_b": "thesis shifts",
      "if_print_c": "thesis breaks"
    },
    "citations": [...]
  },
  "confidence": "MEDIUM"
}
```

The memo MUST have 3-5 watch metrics — fewer is risky (no signal filtered), more dilutes attention.

### Disciplines applied

- **Pre-mortem methodology (Gary Klein, HBR 2007)** — "imagine 6 months from now this print was a disaster; what went wrong?" — used as the explicit framing for the devils-advocate beat
- **Sell-side pre-mortem practice** — 3-5 watchpoints ranked by likely impact, each with a reaction function; no orphan bullets
- **Anthropic finance agents pattern** — even with the lighter scope, we keep the citation-first discipline (every metric's rationale traces to a primary source)
- **Thesis_register coherence** — f3 writes a catalyst row so f4 can resolve it post-print; this closes the loop on "what we said we'd watch vs what we did"

### Boundaries

| Behavior | Default |
|---|---|
| Devils-advocate fires? | Yes; `--skip-devil` to drop |
| Default depth | `SCAN` (cheap; pre-mortems work better with fewer hot takes) |
| 3+ agents always fire | senior-analyst, forensic-accounting, final-report (skip-devil drops the 3rd) |
| Catalyst persisted | Always (ticker, event, expected_date, what_to_watch JSON) |

### CLI

```bash
python docs/runtime/runtime.py --flow f3 \
    --ticker NVDA --model ollama/llama3.3:70b \
    --earnings-date 2026-11-20 [--skip-devil]
```

### What's NOT in scope

- Multi-ticker earnings preview (use f2 with `rubric="earnings preview"` if needed)
- Original coverage / thesis derivation (use f1)
- DCF triggered by print reaction (use f9)
