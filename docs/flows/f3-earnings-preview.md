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
