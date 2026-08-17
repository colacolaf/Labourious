# Labourious

**The Analyst's Bench — a citation-grounded, abstention-honest short-form research tool.**

Labourious is a CLI-and-future-app research tool that runs analyst-quality short-form memos on public companies. You give it a ticker and a question; it gives you a memo with a bottom line, a bear case, and citations to primary sources — disassembled into evidence you can defend and gaps it couldn't fill.

It is **the team you'd hire if you could afford one**, written into a 5-prompt library that any provider-agnostic runtime can execute.

> **Current status:** the repository is **post-restructure, pre-runtime-build**. The 26-agent roster and the 89-prompt prototype library have been replaced by a 5-prompt Analyst's Bench + an 8-flow recipe set + a runtime skeleton + an eval suite. See [`docs/CONTEXT.md`](docs/CONTEXT.md) for the framing and [`docs/RESTRUCTURING.md`](docs/RESTRUCTURING.md) for the audit trail.

## What's here

- **5 system prompts** (`docs/prompts/`) — orchestrator + senior-analyst + forensic-accounting + devil's-advocate + final-report.
- **8 named flows** (`docs/flows/`) — recipes that use the 5 prompts in different orders/rubrics. f1 (Analyze ticker) is the flagship.
- **Runtime skeleton** (`docs/runtime/runtime.py`) — load prompts, call models, parse JSON envelopes, chain the 5 prompts, write thesis register, log cost.
- **4 model adapters** (`docs/runtime/adapters/`) — Anthropic + Ollama + Groq + OpenAI-compat. Free-models supported; hybrid routing via `--paid-for`.
- **4 tool adapters** (`docs/runtime/tools/`) — SEC EDGAR (free) + News RSS + yfinance market data + web fetch.
- **Thesis register** (`docs/runtime/thesis_register/`) — SQLite memory across runs: theses + updates + catalysts.
- **5-test eval suite** (`docs/runtime/evals/`) — fails when discipline breaks. A passing suite is the only evidence the system works.
- **7 framing docs** (`docs/CONTEXT.md`, `ROADMAP.md`, `USER-JOBS.md`, `CANNOT-DO.md`, `DEFERRED.md`, `RESTRUCTURING.md`, `ARCHITECTURE.md`) — the why/what/how/where.

## How a user runs it (planned)

```
$ python docs/runtime/runtime.py --flow f1 --ticker NVDA --model ollama/llama3.3:70b
# 5–10 minutes, free local model, one memo with bottom line + bear case + next questions + citations
# thesis_register row written; cost.json updated
```

Hybrid mode with synthesis on Sonnet:

```
$ python docs/runtime/runtime.py --flow f1 --ticker NVDA \
    --model ollama/llama3.3:70b --paid-for final-report
```

Compare 3 tickers:

```
$ python docs/runtime/runtime.py --flow f2 \
    --tickers "NVDA,AMD,AVGO" --model groq/llama-3.3-70b-versatile
```

Dry-run (prints the wave plan, no model call):

```
$ python docs/runtime/runtime.py --dry-run --flow f1 --ticker NVDA \
    --model ollama/llama3.3:70b
```

## Repository map

| Path | Purpose |
|------|---------|
| [`docs/README.md`](docs/README.md) | Documentation index |
| [`docs/CONTEXT.md`](docs/CONTEXT.md) | The Analyst's Bench — what the project is |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Build order — what to ship first |
| [`docs/USER-JOBS.md`](docs/USER-JOBS.md) | What the project is for; the 5 user jobs + no-build list |
| [`docs/CANNOT-DO.md`](docs/CANNOT-DO.md) | Honest boundary list |
| [`docs/DEFERRED.md`](docs/DEFERRED.md) | What we cut and why (deferred ≠ deleted) |
| [`docs/RESTRUCTURING.md`](docs/RESTRUCTURING.md) | The audit trail |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Components, calling model, memory model |
| [`docs/prompts/`](docs/prompts/) | The 5 system prompts |
| [`docs/flows/`](docs/flows/) | The 8 named flows |
| [`docs/runtime/`](docs/runtime/) | The runtime skeleton + adapters + tools + thesis register + evals |

## Design principles

- **Citation-grounded.** Every claim in a memo has a primary-source URL. No citation, no claim.
- **Abstention-honest.** When the system can't verify, it says so. Never invents with "likely ~$X".
- **Discipline-first.** Steelman-then-break in the bear case. Source-verification in every claim. Per-asset gate in every run.
- **Free-models-first.** Qwen 2.5 72B and Llama 3.3 70B carry ~80% of the work. Hybrid routing closes the gap on synthesis.
- **Evidence over text.** A passing eval suite, not "we wrote the prompt carefully," is what proves the system works.

## Status

**Phase: post-restructure, pre-runtime-build.** The audit-driven restructure is complete. Calibration (passing evals on actual f1 runs) is the next milestone.

### What changed in the restructure
- 89 frontend prompts → 0 (deleted, not deferred)
- 28 v2 prompts → 5 (kept, edited)
- 6 obsolete top-level docs → 7 framing docs (rewritten)
- New: 8 flow recipes, runtime skeleton, 4 model adapters, 4 tool adapters, thesis register, 5-eval suite

See [`docs/RESTRUCTURING.md`](docs/RESTRUCTURING.md) for the full audit trail.

## License

MIT (no `LICENSE` file yet).
