# Runtime — The Skeleton

> The runtime is what makes the prompts into a system, not a library. Today: minimal CLI that loads prompts, calls models, parses JSON, chains the 5 prompts, writes the thesis register, logs cost.

This directory lives under `docs/` because the project doesn't yet have an `app/` (no Electron shell). When the Electron build ships, this directory will move to `app/runtime/` and the Electron renderer will call the same Python entrypoints.

## What's here

| File | Role |
|------|------|
| `runtime.py` | The CLI. `python runtime.py --flow f1 --ticker NVDA --model ollama/llama3.3:70b` |
| `adapters/` | Per-model-provider adapter layer (Anthropic, Ollama, Groq, OpenAI-compat) |
| `tools/` | Per-source tool adapter layer (SEC EDGAR, news, market data, web fetch) |
| `thesis_register/` | SQLite memory (theses + updates + catalysts) |
| `evals/` | 5-test eval suite for prompt discipline |
| `.runs/` | Per-run artifact directory (memo markdown, JSON envelopes, cost log) |
| `.cache/` | Per-tool response cache |

## What `runtime.py` does

```
python docs/runtime/runtime.py \
    --flow f1 \
    --ticker NVDA \
    --model ollama/llama3.3:70b \
    --paid-for final-report   # optional; hybrid mode
```

1. **Loads the flow** from `docs/flows/<flow_id>.md`.
2. **Reads thesis_register** for the relevant ticker(s) (RELEVANT HISTORY).
3. **Loads the orchestrator prompt** + coverage plan.
4. **Calls orchestrator** with the user query + RELEVANT HISTORY + flow context.
5. **Plans waves** per the flow's wave plan.
6. **Calls senior-analyst** with the orchestrator's brief.
7. **Calls specialists** per senior-analyst's delegation list (forensic-accounting, devils-advocate).
8. **Calls final-report** with the synthesized envelopes.
9. **Writes thesis_register row(s)** with the new thesis.
10. **Logs cost.json**.
11. **Renders the memo** to `docs/runtime/.runs/<run_id>/memo.md`.
12. **Returns markdown to stdout**.

## CLI flags

| Flag | Purpose | Default |
|------|---------|---------|
| `--flow` | One of f1–f8 | (required) |
| `--ticker` | Single ticker or comma-separated | (required for f1/f3/f4; not used by f6/f8) |
| `--model` | Adapter + model name | (required) |
| `--paid-for` | `orchestrator | senior-analyst | final-report` for hybrid mode | unset (all-free) |
| `--depth` | `SCAN | STANDARD | DEEP` | STANDARD |
| `--compressed` | bool | false |
| `--output-dir` | Per-run artifact directory | `docs/runtime/.runs/<run_id>/` |
| `--dry-run` | Print the wave plan + brief structure without making calls | false |

## What `_run_id` looks like

`<UTC timestamp>_<flow_id>_<ticker>_<8 char hash>`, e.g. `20260816T123456Z_f1_NVDA_a1b2c3d4`.

## Hybrid mode

When `--paid-for final-report` is set:
- Orchestrator + senior-analyst + forensic-accounting + devils-advocate → free model (`ollama/...` or `groq/...`).
- final-report only → Sonnet.

Adds `~0.5–1.5 seconds` per call for the adapter swap.

## Costs

`logs/cost.json` (or `.runs/<run_id>/cost.json`) records per-call:
- `agent_id`
- `model`
- `in_tokens`
- `out_tokens`
- `cache_hit_tokens` (if applicable)
- `cost_usd_estimate`
- `wallclock_s`

Total per f1 run: ~5–10k tokens; ~$0.05–$0.30 hybrid; ~$0 all-free.

## What relies on what

```
prompts/  ──┐
            ├──▶ runtime.py
adapters/ ──┤
tools/  ────┤
flows/  ────┤
register/ ──┤
```

Prompts are inert until the runtime loads them. Tools are inert until the model adapter's token output references them (the model *describes* what it wants; the runtime decides whether to call).

## Future work

- Electron renderer calling the same Python entrypoints via a thin Node shim.
- Multi-user: per-user `~/.labourious/<userid>/thesis_register/`.
- Concurrent runs: `runtime.py --flow f1 --ticker NVDA --flow f2 --tickers AAPL,AMD --parallel`.

See [`../ROADMAP.md`](../ROADMAP.md) for P0/P1/P2 ordering.
