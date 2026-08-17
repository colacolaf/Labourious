# Labourious — Documentation Index

> The project today: **the Analyst's Bench**. A 5-prompt library, an 8-flow recipe set, a runtime skeleton, and an eval suite. Phase: post-restructure, pre-runtime-build.

If you read three files, read these in this order:

1. **[`CONTEXT.md`](CONTEXT.md)** — what the project is and why the restructure happened.
2. **[`ROADMAP.md`](ROADMAP.md)** — what to build, in what order, with acceptance criteria.
3. **[`USER-JOBS.md`](USER-JOBS.md)** — what the project is for; the litmus test for any feature.

Then the rest, by role:

---

## Framing decisions

| File | Purpose |
|------|---------|
| [`CONTEXT.md`](CONTEXT.md) | The restructure log: what was cut, why, and what shape we ended up in |
| [`ROADMAP.md`](ROADMAP.md) | Build order for the 6 P0 items, P1 follow-ups, P2 deferred-but-targeted |
| [`USER-JOBS.md`](USER-JOBS.md) | The 5 user jobs the project serves; the litmus test for new features |
| [`CANNOT-DO.md`](CANNOT-DO.md) | Honest boundary list — what the project will never do and why |
| [`DEFERRED.md`](DEFERRED.md) | What was *parked* (not deleted) from the old 26-agent roster |
| [`RESTRUCTURING.md`](RESTRUCTURING.md) | The full audit trail of the restructure |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Components, calling model, memory model, what's *not* here |

---

## Code & artifacts

| Path | Purpose |
|------|---------|
| [`prompts/`](prompts/) | The **5 system prompts** — orchestrator, senior-analyst, forensic-accounting, devil's-advocate, final-report. Plus the V2-PROMPT-STANDARD template. |
| [`flows/`](flows/) | **8 named flows** — recipes that reuse the 5 prompts in different order/rubric. f1 (Analyze ticker) is the flagship. |
| [`runtime/runtime.py`](runtime/runtime.py) | The **runtime skeleton** — load prompt, call model, parse output, chain. |
| [`runtime/adapters/`](runtime/adapters/) | Free-model + paid-model adapter layer (Anthropic, Ollama, Groq, OpenAI-compat). |
| [`runtime/tools/`](runtime/tools/) | Free-tier tool adapters: SEC EDGAR, news, market data, web fetch. |
| [`runtime/thesis_register/`](runtime/thesis_register/) | SQLite memory: theses + updates + catalysts. |
| [`runtime/evals/`](runtime/evals/) | 5 tests that fail when discipline breaks (no prompt change ships without them passing). |

---

## What's NOT here (by design)

- **No `frontend/`** — the 89-prompt pixel-art prototype library was deleted; the v1 library is a structurally-and-functionally-superset of it.
- **No 26-agent roster documents** — `V1-ROSTER.md` and `AGENTS.md` were superseded and removed. The 5-prompt roster is in `prompts/`.
- **No celebrity persona agents** — Burry / Buffett / Taleb / Bremmer / Fink / Simons / Minervini / etc. were V1's Plug examples; the project has now retired the roster-membership for personas.
- **No "Senior PM" / "PM Bodyguard" prompts** — folded into orchestrator (synthesis discipline + critic).
- **No per-agent freshness tiers / per-asset gates in prompt text** — runtime-enforced via the eval suite.
- **No `validate-v2-prompts.py`** — the old linter checked the structure it was written to enforce (a structural tautology). The new eval suite replaces its role.

---

## Quick start (planned)

```
$ pip install -r docs/runtime/requirements.txt    # when the runtime ships
$ python docs/runtime/runtime.py --flow f1 --ticker NVDA --model ollama/llama3.3:70b
```

Expected output: a memo with bottom line, bull case, bear case, "what an attacker would say," "next three questions," and citations to primary sources. Returned to stdout, written to `docs/runtime/.runs/<run_id>/`, and logged to `docs/.runs/cost.json`.

---

## The directory tree

```
docs/
├── CONTEXT.md              ← read first
├── ROADMAP.md              ← read second
├── USER-JOBS.md            ← read third
├── CANNOT-DO.md
├── DEFERRED.md
├── RESTRUCTURING.md
├── ARCHITECTURE.md
├── README.md               ← you are here
├── LICENSE
├── prompts/
│   ├── V2-PROMPT-STANDARD.md
│   ├── orchestrator/system-prompt.md
│   ├── leads/senior-analyst/system-prompt.md
│   ├── specialists/
│   │   ├── forensic-accounting/system-prompt.md
│   │   └── devils-advocate/system-prompt.md
│   └── cross-cutting/final-report/system-prompt.md
├── flows/
│   ├── README.md
│   ├── f1-analyze-ticker.md      ← flagship
│   ├── f2-compare-tickers.md
│   ├── f3-earnings-preview.md
│   ├── f4-earnings-review.md
│   ├── f5-sector-deep-dive.md
│   ├── f6-thematic-screen.md
│   ├── f7-risk-event.md
│   └── f8-macro-overlay.md
└── runtime/
    ├── README.md
    ├── runtime.py                 ← the skeleton
    ├── adapters/
    │   ├── anthropic.py
    │   ├── ollama.py
    │   ├── groq.py
    │   └── openai_compat.py
    ├── tools/
    │   ├── sec_edgar.py
    │   ├── news.py
    │   ├── market_data.py
    │   └── web_fetch.py
    ├── thesis_register/
    │   ├── schema.sql
    │   ├── register.py
    │   └── README.md
    └── evals/
        ├── README.md
        ├── test_hallucination.py
        ├── test_source_verification.py
        ├── test_per_asset_coverage.py
        ├── test_freshness.py
        └── test_abstention.py
```
