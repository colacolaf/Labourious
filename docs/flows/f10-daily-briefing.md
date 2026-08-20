# Flow f10 — Daily Briefing

> *"What changed in my watchlist since yesterday?"* — for users who run f1 memos and want a single morning re-check on every tracked name.

## What it answers

> *"Across my watchlist of N names, which theses still hold (REITERATE), which need a tweak (UPDATE), and which flipped today (FLIP)?"*

This is f1 batched at watchlist scale: instead of one deep memo, you get a **page of one-paragraph re-checks** ranked by what changed most.

## Inputs

| Field | Required? | What it carries |
|-------|-----------|------------------|
| `watchlist` | required | The tickers to re-check. 1–20 names typical. CSV in the CLI; list of strings programmatically. |
| `since_days` | optional | Look-back window in days (default **1** = "since yesterday"; can be 7 for weekly review). Used to scope the prior-thesis + latest-news query. |
| `depth` | optional | Per-ticker depth. Default **SCAN** (one-paragraph re-check). `STANDARD` allowed but rarely useful at scale. |
| `model` | required | Same as f1. Free Ollama works fine for daily SCAN. |
| `paid_for` | optional | Hybrid routing. |

The runtime pre-loads:
- `thesis_register.read_thesis(ticker, since=since_days * 7)` per ticker (gives a 1-7 week lookback window for context).
- The snippet cache for any prior citations (8-Ks, news, transcripts) — feeds the senior-analyst's "what changed" prompt.

## Wave plan

```
Pre-wave (sequential, IO-bound):
  ➤ for each ticker in watchlist:
       load prior thesis from register (since_days * 7d)
       if no prior thesis → mark as "no prior" (still emit a placeholder entry)
       collect into per-ticker brief context

Wave 1 (parallel fan-out via ThreadPoolExecutor):
  ➤ for each ticker with a prior thesis:
       senior-analyst (DEPTH=SCAN) — "what changed in <TICKER> since <last_update>?"
       brief includes:
         - prior thesis summary (text + bottom_line + version)
         - last_update_date + days_since
         - today's market context (snippet from yfinance via market_data tool)
         - tag instruction: classify as REITERATE | UPDATE | FLIP

Wave 2 (sequential):
  ➤ final-report — assemble the daily memo:
       - top section: counts (REITERATE / UPDATE / FLIP)
       - per-ticker section: 1-paragraph read + tag + watchpoint
       - "no prior" section: list of tickers without a thesis (hint: run f1 to onboard)

Post-flow:
  ➤ for any ticker tagged FLIP:
       thesis_register.add_update(ticker, what_changed, reason="auto: f10 daily flip")
  ➤ cost.json updated
```

## Rubric

> **The watchlist one-pager.** Goal: let a user skim their tracked names in 60 seconds and know which ones need attention today. The reader looks at the FLIP section first, UPDATE second, REITERATE last (the REITERATE block is just to confirm "still on track").

Sections the memo will contain (in this order, no others):

1. **Header** — date + watchlist size + tag counts.
2. **FLIP block** — one paragraph per ticker where the thesis changed materially. Sorted by impact (severity × surprise).
3. **UPDATE block** — one paragraph per ticker with a meaningful but non-flipping change. Sorted by materiality.
4. **REITERATE block** — one sentence per ticker that hasn't changed materially. The smallest section by intent — the user wants their day to confirm stability.
5. **No-prior section** — list of tickers with no prior thesis. Hint: run `analyze <TICKER>` to onboard.
6. **Watchpoints** — list of upcoming catalysts (from `thesis_register.list_open_catalysts(ticker)`).
7. **Citations** — URLs cited in any of the per-ticker paragraphs (deduplicated).

## Output shape

```json
{
  "flow_id": "f10",
  "watchlist": ["NVDA", "AAPL", "MSFT"],
  "since_days": 1,
  "memo": {
    "bottom_line": {
      "direction": "STABLE",
      "conviction": 4,
      "one_liner": "1 FLIP, 1 UPDATE, 1 REITERATE — AAPL guidance cut the most material",
      "flip_trigger": "any FLIP'd ticker re-reverts, or >2 tickers UPDATE in the same direction"
    },
    "flips": [
      {
        "ticker": "AAPL",
        "one_paragraph": "...",
        "prior_thesis_id": 42,
        "auto_update_written": true
      }
    ],
    "updates": [{"ticker": "NVDA", "one_paragraph": "..."}],
    "reiterates": [{"ticker": "MSFT", "one_sentence": "..."}],
    "no_prior": [],
    "watchpoints": [
      {"ticker": "NVDA", "event": "Q4 earnings", "expected_date": "2026-11-20"}
    ],
    "citations_used": [
      {"name": "Apple Q4 2026 8-K", "type": "filing", "date": "2026-10-30", "url": "..."}
    ]
  },
  "confidence": "HIGH",
  "costs": [...]
}
```

## CLI usage

```bash
# Default: today's watchlist (from Config.watchlist), since yesterday
python docs/runtime/runtime.py --flow f10 --model ollama/llama3.3:70b

# Explicit watchlist
python docs/runtime/runtime.py --flow f10 --watchlist NVDA,AAPL,MSFT,GOOG,AMZN \
  --model ollama/llama3.3:70b --export daily.md

# Weekly review
python docs/runtime/runtime.py --flow f10 --watchlist NVDA,AAPL,MSFT \
  --since-days 7 --model ollama/llama3.3:70b
```

## Cost (per run, STANDARD watchlist of 5)

| Model | Per run |
|---|---|
| Ollama (free) | free · 7 agents (1 orchestrator + 5× senior-analyst + 1 final-report) |
| Claude Haiku 4 | ≈ $0.06 |
| Claude Sonnet 4 | ≈ $0.16 |
| Claude Opus 4 | ≈ $0.83 |

Watchlist of 10: roughly doubles the per-ticker agent count; final-report is constant.

## What this flow does NOT do

- Generate a fresh thesis for tickers without a prior. Run `analyze <TICKER>` (f1) first to onboard.
- Predict catalysts beyond what `thesis_register.list_open_catalysts()` already has. Use f3 (earnings preview) to add new ones.
- Trade. The auto-write to `updates` is an annotation, not a portfolio action.

## See also

- `docs/flows/f1-analyze-ticker.md` — the on-ramp for a single name (run this first before f10 sees anything)
- `docs/flows/f3-earnings-preview.md` — adds upcoming catalysts (so f10's watchpoints block isn't empty)
- `docs/runtime/thesis_register/README.md` — the underlying DB schema