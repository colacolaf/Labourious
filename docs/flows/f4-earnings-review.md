# Flow f4 — Earnings Review

> *"What changed after [TICKER]'s print?"* — the post-mortem that updates the thesis.

## What it answers

> *"Now that [ticker] has printed, what does the prior thesis say differently? Did the print confirm, shift, or break it?"*

This is the flow that exercises the **thesis register** most precisely. Every f4 run writes an `updates` row and a new versioned `theses` row, so the system *remembers* that its prior view was either right or wrong.

## Inputs

| Field | Required? | What it carries |
|-------|-----------|------------------|
| `ticker` | yes | |
| `earnings_date` | yes | The print date (the runtime can fetch, but providing it pins). |
| `thesis_id` | optional | A specific thesis_register row to update. Default: latest 30 days. |
| `depth` | optional | Default STANDARD. |
| `model` | required | Per-adapter flag. |

## Wave plan

```
Wave 1 (sequential):
  ➤ senior-analyst (DEPTH=STANDARD, the heaviest at f4)
       - load prior thesis from thesis_register.read(ticker, since=30d)
       - re-read current thesis skeleton
       - construct the diff: which of the thesis's fragile_assumption / bull / bear / next_questions flipped?

Wave 2 (parallel):
  ➤ forensic-accounting (DEPTH=STANDARD)
       - what did the print actually show vs the prior number? (compare to last quarter; track the 3 watchpoints from f3)
  ➤ devils-advocate (DEPTH=STANDARD)
       - did the bear case get materially better or worse? what's the new fragile assumption?

Wave 3 (sequential):
  ➤ final-report (DEPTH=STANDARD or DEEP for major prints)
       - the diff memo (this is the deliverable's defining feature)
```

## Rubric

> **The diff memo.**
> Goal: produce a clear "we said X, now we say Y, here's why" with concrete attribution. The user wants to know **whether their position thesis is right or wrong** — the print is the test.
>
> Structure:
> 1. **Bottom line** — direction + conviction + flip_trigger (now what is the flip trigger, if different from before?).
> 2. **What changed** — explicit diff against prior thesis (`thesis_register.read(ticker, since=30d)`):
>    - prior thesis one-sentence vs new one-sentence
>    - prior fragile_assumption vs new fragile_assumption
>    - prior bottom_line vs new bottom_line
>    - prior next_three_questions vs new next_three_questions (some resolved? new ones?)
> 3. **Bull case** (revised).
> 4. **Bear case** (revised; especially — did the bear case improve or worsen?).
> 5. **What an attacker would say** (revised).
> 6. **New next questions** — calibration of unresolved watchpoints.
> 7. **Citations**.

## Output

```jsonc
{
  "agent_id": "final-report",
  "flow_id": "f4",
  "memo": {
    "bottom_line": {...},
    "diff": {
      "prior_thesis_one_sentence": "...",
      "new_thesis_one_sentence": "...",
      "prior_fragile_assumption": "...",
      "new_fragile_assumption": "...",
      "prior_conviction": 4,
      "new_conviction": 3,
      "prior_flip_trigger": "...",
      "new_flip_trigger": "...",
      "next_questions_resolved": ["Q1 resolved by print"],
      "next_questions_new": ["Q4 = new watchpoint"]
    },
    "bull_case_revised": "...",
    "bear_case_revised": "...",
    "what_an_attacker_would_say_revised": "...",
    "new_next_questions": [...],
    "citations": [...]
  }
}
```

## Acceptance

- All 5 standard evals pass.
- **The Diff test** (added to evals): every f4 run produces a `diff` object with all required fields populated. **No exception.**
- **The Resolve test**: at least 1 of the prior `next_three_questions` is marked resolved by the print.
- **The Update test**: a new `theses` row + an `updates` row are written to the thesis_register on completion.

## Skipped calls

- None normally. f4's value is in the diff; specialists are essential.

## Wallclock target

- All-free: **6–10 minutes**.
- Hybrid: **4–6 minutes**.

## Cost target

Roughly **1.2× f1** (slightly heavier due to prior-thesis fetching + diff computation).

## Out of scope (f4)

- Pre-print setup. Use f3.
- Multi-ticker print review. Use f2 with `rubric = "earnings print post-mortem"`.
- Original coverage initiation. Use f1.
