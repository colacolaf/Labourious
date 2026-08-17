# CONTEXT — The Restructure (Aug 2026)

> Read this first. Why this repo looks the way it does today.

## TL;DR

The original build target was a 26-agent Electron app for the Wharton Investment Competition, anchored in a 89-prompt pixel-art prototype library. Three adversarial audit passes (`docs/prompts/ANALYZE-THE-PROJECT.md`, archived) found that the design was overbuilt for the actual job and relied on claims no prompt text can support. The repository is now restructured into **the Analyst's Bench**: **5 system prompts** powering **one flagship flow** with a **runtime skeleton** that can run on free models, validated by a **5-test eval suite**, and made durable by a **thesis register** that gives the system memory across runs.

This file is the short tour. The full audit trail — what was deleted, what was kept, what was rewritten and why — is in **[`docs/RESTRUCTURING.md`](RESTRUCTURING.md)**. The build sequence is in **[`docs/ROADMAP.md`](ROADMAP.md)**. The user jobs the project serves are in **[`docs/USER-JOBS.md`](USER-JOBS.md)**.

## What Labourious is, in one paragraph

Labourious is a free-model-friendly, citation-grounded, abstention-honest research bench for analyst-quality short-form memos on public companies. You give it a ticker and a question; it gives you a memo with a bottom line, a bear case, and citations to primary sources — disassembled into evidence you can defend and gaps it couldn't fill. It is **the team you'd hire if you could afford one**, written into a 5-prompt library that any provider-agnostic runtime can execute.

## What changed in this restructure

| Axis | Before | After |
|------|--------|-------|
| **Roster** | 26 agents (12 leads + 13 specialists + final-report + pluggable) | **5 prompts** (orchestrator + senior-analyst lead + forensic-accounting + devil's-advocate + final-report) |
| **Per-agent protocols** | 14-section prompts, 5 effort modes, per-asset gates in every prompt | Same skeleton — protocols no longer duplicated, runtime enforces gates |
| **Flows** | Implicit in the orchestrator's routing map | Explicit **8 named flows** (`docs/flows/f1`–`f8`), each using 4–5 of the 5 prompts |
| **Runtime** | Planned, not built | Skeleton at `docs/runtime/runtime.py` — load prompt → call model → parse output → chain |
| **Model layer** | Provider-agnostic, per-agent | **`docs/runtime/adapters/`** — one file per provider (Anthropic, Ollama, Groq, OpenAI-compat) |
| **Tool layer** | 4 connectors specified in docs | **`docs/runtime/tools/`** — `sec_edgar` (free), `news`, `market_data`, `web_fetch` |
| **Memory** | Plain files, no model | **`docs/runtime/thesis_register/`** — SQLite (theses, updates, catalysts), every flow reads/writes |
| **Validation** | `validate-v2-prompts.py` — lints prompts against a shape they were written to match (proves structure, not behavior) | **`docs/runtime/evals/`** — 5 tests that **fail when discipline breaks** (hallucination, source-verification, per-asset, freshness, abstention) |
| **User jobs** | Implicit | **5 user jobs**, ranked, in [`USER-JOBS.md`](USER-JOBS.md). Every feature maps to one or is cut. |
| **Honest limits** | None | [`CANNOT-DO.md`](CANNOT-DO.md) — what the system will never do |

## The decisions behind the cut

Driven by three findings from the prior audit (`docs/prompts/ANALYZE-THE-PROJECT.md`, archived; full text in [`RESTRUCTURING.md`](RESTRUCTURING.md)):

1. **A 26-agent roster is overbuilt for the actual first job.** The Wharton comp asks for **2–3 positions in depth**, which is the opposite of the breadth-first shape multi-agent systems pay off on (Anthropic's own finding). The flagship flow needs **one primary analyst voice, one forensic specialist, one adversarial check, one synthesizer**. That's four prompts of substance plus the orchestrator. Five total.
2. **The "decision-ready" / "prevents hallucination" claims were structural, not behavioral.** Saying a prompt enforces per-asset gates is not evidence it works — the v2 validator proved structure, not outcome. The new eval suite is what makes that claim falsifiable.
3. **Free models can carry most of this work, but only if the runtime has shared context.** Anthropic's 15× cost figure from their own multi-agent paper is largely a **prompt-cache** figure — lots of shared prefix across agents. Free local models (Llama 3.3 70B, Qwen 2.5 72B) don't auto-cache but accept long context cheaply. We get 80%+ of the Anthropic-on-Claude quality on free models, with one paid escape hatch for synthesis.

## Five user jobs (the litmus test for every feature)

From [`USER-JOBS.md`](USER-JOBS.md), in priority order:

1. **Trust** — can I cite this output? Is it real or machine-made-up?
2. **Action** — what do I do with this? Buy / hold / sell / wait for what?
3. **Speed** — how fast can I get a defensible view on a new name?
4. **Defensibility** — when my PM/team/client asks "why?", does the report hold up?
5. **Comparison** — how does ticker A compare to B and C?

Every shipped feature touches one of these jobs. Everything that doesn't is in [`DEFERRED.md`](DEFERRED.md) with a one-line reason it doesn't ship yet.

## The 6 things that make the project work

Order matters. Skip a step and the next one is unprovable.

1. **Runtime skeleton** (`docs/runtime/runtime.py`) — load prompts, call models, parse JSON envelopes, chain the 5 prompts together.
2. **Tool adapters** (`docs/runtime/tools/`) — `sec_edgar`, `news`, `market_data`, `web_fetch` with caching.
3. **Eval suite** (`docs/runtime/evals/`) — 5 tests that fail when protocols break.
4. **Flagship flow f1** (`docs/flows/f1-analyze-ticker.md`) — end-to-end on a known ticker (NVDA / AAPL), validated against a trusted analyst memos.
5. **Free-model adapter layer** (`docs/runtime/adapters/`) — Anthropic + Ollama + Groq + OpenAI-compat, single-file translation, hybrid routing (free for the bulk, paid for synthesis only).
6. **Thesis register** (`docs/runtime/thesis_register/`) — the durable memory. Every f1 run reads past theses and writes a new versioned thesis at the end. Without this, the system is one-shot.

## Architecture shape (the 30-second view)

```
                 ┌──────────────────────────────┐
                 │   USER (chat / CLI / API)    │
                 └───────────────┬──────────────┘
                                 │
                       upload flow_id + ticker
                                 │
                 ┌───────────────▼──────────────┐
                 │     ORCHESTRATOR (1 prompt)  │
                 │  routing • wave planning    │
                 │  conflict surfacing         │
                 └───────────────┬──────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
        ┌─────▼─────┐    ┌───────▼──────┐    ┌──────▼────────────┐
        │ SENIOR    │    │ FORENSIC     │    │ DEVIL'S ADVOCATE  │
        │ ANALYST   │───▶│ ACCOUNTING   │    │ (mandatory)       │
        │ (lead)    │    │ (specialist) │    │ (specialist)      │
        └─────┬─────┘    └───────┬──────┘    └──────┬────────────┘
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     FINAL REPORT        │
                    │ (bottom line + bear +   │
                    │  next questions +       │
                    │  citations)             │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    Thesis Register (SQLite)
                    ─ updated on every run
```

Each box is one prompt file. Each prompt is ≤ 2,000 tokens output budget per call. Each box is reusable across all 8 flows. The flows are recipes, not new agents — see [`docs/flows/README.md`](flows/README.md).

## What is *not* in this restructure

Explicit non-goals, in one line each:

- No per-sector agent (sectors are **knowledge packs**, not agents — Anthropic/LangChain research is unanimous on this).
- No real-time market prices (delayed OHLCV is enough for 95% of decisions).
- No trading execution (regulatory surface area, not an analytical one).
- No portfolio management UI (the user has one; we provide analysis, not custody).
- No mobile-first UI (analysts work on laptops; retail phone users aren't the v1 audience).
- No celebrity personas in the v1 roster (memory hook vs. function; defer to pluggable examples).
- No 89-prompt zoo — gone.

## What the developer does today

```
$ python docs/runtime/runtime.py --flow f1 --ticker NVDA --model ollama/llama3.3:70b
→  5–10 minutes, one memo with bottom line + bear case + citations
→  thesis_register/theses.db updated with the new thesis
→  logs/cost.json shows tokens spent per agent per run
→  evals/test_*.py can re-run the same flow and check discipline
```

Ship that command working against `flow f1` on free local models and the project stops being "prompt poetry" and becomes a real tool.

## Where the user comes in

You read [`ROADMAP.md`](ROADMAP.md) and decide which of the 6 things to build first. Recommendation: **runtime skeleton, then f1 flow, then one of the 5 evals** (whichever you'd most hate to be wrong about — usually hallucination or source-verification). The other 4 things follow.

---

*The next file down the rabbit hole is [`RESTRUCTURING.md`](RESTRUCTURING.md) — the full audit trail of what was cut, kept, rewritten, and why. If you only read three files, read this one, ROADMAP, and USER-JOBS. The prompt library at [`prompts/`](prompts/) and the runtime at [`runtime/`](runtime/) are read-as-needed.*
