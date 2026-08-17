# RESTRUCTURING — the audit trail

> The full story of what was cut, what was kept, what was rewritten, and why. Read alongside [`CONTEXT.md`](CONTEXT.md) (the short tour) and [`ROADMAP.md`](ROADMAP.md) (the build order).

## What was found (the input to the restructure)

Three adversarial audits were conducted against the v2 prompt library + design docs. Their findings drove every cut below. The audits are sourced from `docs/prompts/ANALYZE-THE-PROJECT.md` (now archived in [`docs/CHANGELOG.md`](../CHANGELOG.md)). Key findings:

1. **The 26-agent roster was overbuilt.** Multi-agent pays off only for breadth-first, parallelizable, high-value tasks. The Wharton comp is *the opposite* — 2–3 names in depth.
2. **"Decision-ready" / "prevents hallucination" claims were structural, not behavioral.** A prompt that *says* it enforces a gate is not evidence the gate works.
3. **Free models can carry most work, but only with the right routing.** Anthropic's 15× cost figure is largely a prompt-cache figure; free 70B-class models can hit ~80% of Sonnet's quality for instruction-following jobs.
4. **The runtime was sketched, not built.** Claims like "the system does synthesis" and "the system calls SEC EDGAR" required evidence the codebase didn't contain.
5. **No memory across runs.** Every analysis was one-shot; the system never got smarter.

## The cut: what was deleted

**89 prompts in `docs/frontend/`** — the entire pixel-art prototype library.
- Reason: v1 already absorbed (functionally and structurally) everything of value from this library. Celebrity personas (Burry, Buffett, Taleb, etc.) are not part of v1's functional core. Without sprites, the `look.md` files are noise.
- Re-derivable from any new v2 prompt + a `pluggable/sector-pack.md` if needed.

**23 prompts in `docs/prompts/`** — the deferred v2 leads + specialists + pluggable.
- Reason: every one is captured by the 5 prompts we kept, either by absorbing into the senior-analyst prompt's rubric or by becoming a "future flow" rubric. See [`DEFERRED.md`](DEFERRED.md) for what would unlock each one's return.

**6 obsolete top-level docs** — `AGENTS.md`, `V1-ROSTER.md`, `LABOURIOUS_ARCHITECTURE.md`, `LABOURIOUS_SETUP.md`, `FEATURES.md`, `SECURITY.md`.
- Reason: each was a paper exercise describing a system that doesn't run. The replacement docs (CONTEXT, ARCHITECTURE, USER-JOBS, ROADMAP, CANNOT-DO, DEFERRED, RESTRUCTURING) are concrete and reference the *runtime* that's now under construction.

**1 obsolete validator script** — `docs/prompts/scripts/validate-v2-prompts.py`.
- Reason: it lints structure against a shape it was written to enforce. By definition, it can only pass prompts written to its spec. It is not a behavioural test; calling it a validator was a category error. The eval suite under `docs/runtime/evals/` takes the same role but tests *behaviour* not *structure*.

**1 meta-prompt** — `docs/prompts/ANALYZE-THE-PROJECT.md` (the prompt that ran the original analysis).
- Reason: the analysis it produced drove the restructure; now the analysis is in this RESTRUCTURING doc. Keeping the meta-prompt around was redundant.

## The keep: what was edited

The **5 system prompts** kept and rewritten:

| Prompt | Before | After | Why the change |
|--------|--------|-------|----------------|
| `orchestrator` | Routed 26 agents × N flow patterns; exhaustive routing map; effort-mode-hardcoded rope | Routes 5 agents; explicit per-flow recipe in `docs/flows/`; per-agent gate enforced by runtime (not prompt-text); one "5-agent roster" table | **Smaller**. Anthropic multi-agent research says fewer agents = better reasoning. Plus the prompt becomes a routing reference, not a coordination brain. |
| `senior-analyst` (NEW) | — | Frames question; owns thesis; coordinates 2 specialists | **New**: replaces 12 leads. One lead, one voice, one rubric. The 12-lead plan was a coordination load that the audit found was not earned. |
| `forensic-accounting` | Reports to fundamental-lead via 5-step protocol; broad scope | Reports to senior-analyst; same protocol; boundaries more sharply drawn | **Slimmer routing**. Specialist's *content* is unchanged (still the same Beneish M-Score + accruals + revenue-rec checks). The hard cost of the change is "the lead is one prompt, not twelve." |
| `devils-advocate` | Reports to critique-lead with optional steelman-then-break | Reports to senior-analyst; mandatory steelman-then-break; refuses if THESIS too weak | **Stricter**. The audit found the bear case was being under-called in some flows. A refusal when THESIS is weak surfaces the discipline to the *user*. |
| `final-report` | IPS + Final Report sections, optional joint deliverable | Strict 6-section memo template: Bottom line + Bull + Bear + What an attacker would say + Next three questions + Citations | **Lighter**. The Wharton IPS is a flow (`f9-ips-draft`) on top of f1's memo — not a separate agent output. The new template is skim-testable: ~30 seconds. |

Plus the meta-doc `docs/prompts/V2-PROMPT-STANDARD.md` rewritten: defined against 5 agents, no per-agent-type schemas needed.

## The add: what was created

**The runtime skeleton**, `docs/runtime/runtime.py`:
- ~300 lines of Python (~150 of dispatch and orchestration; ~150 of artifact writing).
- CLI shape: `python docs/runtime/runtime.py --flow f1 --ticker NVDA --model ollama/llama3.3:70b [--paid-for final-report]`.
- Phase: skeleton. The dispatch works; many of the per-flow orchestrators beyond f1 raise `NotImplementedError` — implementations are P1.

**The model-adapter layer**, `docs/runtime/adapters/`:
- `anthropic.py`, `ollama.py`, `groq.py`, `openai_compat.py`. Each conforms to a common interface (`Response` dataclass with text/in_tokens/out_tokens/cost).
- Adapter selection by `--model` prefix.
- Hybrid routing: `--paid-for final-report` swaps to Sonnet only on the final-report prompt.

**The tool-adapter layer**, `docs/runtime/tools/`:
- `sec_edgar.py` — free, keyless, SEC EDGAR REST API (10-K / 10-Q / 8-K / transcript lookup).
- `news.py` — Google News RSS (free, no key) + optional NewsAPI backend.
- `market_data.py` — yfinance (no key) + FRED (free key) for macro.
- `web_fetch.py` — single-page → markdown with script/style stripping.
- Each returns a unified `ToolResult(status, data, as_of, source, note)` envelope.

**The thesis register**, `docs/runtime/thesis_register/`:
- SQLite with 3 tables (`theses`, `updates`, `catalysts`).
- Schema in `schema.sql`; Python wrapper in `register.py`; CLI for ad-hoc inspection.
- Every flow writes; f4 (earnings review) and f8 (macro overlay) write `updates` rows; f3/f4 add catalysts.

**The eval suite**, `docs/runtime/evals/`:
- 5 pytest files: hallucination, source-verification, per-asset-coverage, freshness, abstention.
- Each test asserts a behavioural invariant against the produced envelope under a known-bad injected input.
- A passing suite is **the only evidence the system works**.

**Eight flow files**, `docs/flows/f1-f8.md`:
- Each flow: what it answers, inputs, wave plan, rubric, output shape, acceptance criteria, skipped-call rules, wallclock target, cost target.
- All use the same 5 prompts in different orders — no new agents.

**Six framing docs**, `docs/`:
- `CONTEXT.md` — short tour.
- `ROADMAP.md` — P0/P1/P2 build order.
- `USER-JOBS.md` — 5 user jobs + no-build list.
- `CANNOT-DO.md` — honest boundary list.
- `DEFERRED.md` — what was parked vs. deleted.
- `RESTRUCTURING.md` (this file) — the audit trail.

## Why the cuts at the prompt-text level (not just runtime-rewrite) matter

The audit found that *"every lead and specialist having their own per-asset gate and freshness tier section"* was the same rule duplicated 28 times. Even within the streamlined 5, `senior-analyst` has explicit per-asset and freshness sections in §7–§9. **But the runtime's enforcement layer (eval suite + thesis register + adapters with caching) is what actually catches the failures.** The prompt's job is to *instruct* the model; the runtime's job is to *verify* the model did it. **Evidence comes from verifiability, not from text.**

This is the discipline: prompts *say* what to do. Runtime *catches* when it's not done.

## The validator question: should we re-ship a structure linter?

The old `validate-v2-prompts.py` was a structural linter. The audit found it lints against the shape it was written to enforce (a tautology). **The eval suite replaces its role with behaviour-based tests**, which is a strict superset.

If a structure-linter still has value (e.g., to catch a missing section in a freshly-written prompt before merging), it can be added back as a pre-commit hook, scoped to the 5 prompts. Decision: deprioritised in favour of the behaviour tests. The 5 prompts share one skeleton; drift on that skeleton is caught quickly by reading. **Adding the linter back is a P3 item.**

## What remains unproven (the open questions)

These are the things this restructure **does not** solve and that future work must:

1. **The evaluation battery is not yet calibrated to a baseline.** A passing suite is the only evidence the system works. To *have* a passing suite, an actual f1 run must succeed first. **The first f1 end-to-end run is the next milestone.**
2. **The Qwen 2.5 72B / Llama 3.3 70B performance gap on adversarial reasoning is real.** Hybrid routing puts final-report on Sonnet for prose + adversarial quality. **The thesis register's diff is what surfaces when the free model did weak work** — but the user has to trust the diff is real.
3. **The 5-prompt discipline assumes the senior-analyst lead can do everything the 12-lead plan said it could.** This is the audit's biggest bet. If it fails — e.g. senior-analyst proves too thin for a specific flow — a deferred lead returns via [`DEFERRED.md`](DEFERRED.md)'s gate mechanic, *not* via the prompt text being re-edited. **The 5 prompts are the steady state.**
4. **SEC EDGAR coverage is single-jurisdiction.** International coverage (HKEX, JPX, SSE) is structurally a paid-data-layer problem; the project lives with US-only for v1.

## Reading order for someone who wants to evaluate the restructure

1. [`CONTEXT.md`](CONTEXT.md) — the framing.
2. [`USER-JOBS.md`](USER-JOBS.md) — what the project is for.
3. [`ROADMAP.md`](ROADMAP.md) — what to build next.
4. The 5 prompts in `docs/prompts/` — the actual artifact.
5. The 8 flows in `docs/flows/` — how the prompts become a system.
6. The runtime in `docs/runtime/` — what makes the system runnable.
7. The eval suite in `docs/runtime/evals/` — what makes the system verifiable.
8. [`DEFERRED.md`](DEFERRED.md) and [`CANNOT-DO.md`](CANNOT-DO.md) — the boundaries.
9. **This file** — the audit trail.

## What was renamed, indexed, or re-keyed

Mapping from the prior commit to the restructure:

| Before | After |
|--------|-------|
| `docs/frontend/...` | DELETED (89 prompts) |
| `docs/prompts/altdata/...` | DELETED (1 lead) |
| `docs/prompts/compliance/...` | DELETED (1 lead) |
| `docs/prompts/critique/critique-lead/...` | DELETED (1 lead) |
| `docs/prompts/critique/devils-advocate/...` | MOVED to `docs/prompts/specialists/devils-advocate/system-prompt.md` (rewritten; reports to senior-analyst) |
| `docs/prompts/execution/...` | DELETED (1 lead) |
| `docs/prompts/fundamental/fundamental-lead/...` | DELETED (replaced by senior-analyst) |
| `docs/prompts/fundamental/forensic-accounting/...` | MOVED to `docs/prompts/specialists/forensic-accounting/system-prompt.md` (rewritten; reports to senior-analyst) |
| `docs/prompts/fundamental/dcf-valuation/...` | DELETED (specialist; senior-analyst covers intrinsic-value inline) |
| `docs/prompts/orchestrator/...` | KEPT and EDITED (now 5-agent bound; per-flow recipes live in `docs/flows/`) |
| `docs/prompts/cross-cutting/final-report/...` | KEPT and EDITED (new 6-section memo template; Bottom line + Bear + Next questions enforced) |
| `docs/prompts/macro/...` | DELETED (3 prompts: lead, central-bank-liquidity, geopolitical-risk) |
| `docs/prompts/pluggable/...` | DELETED (1 specialist; policy moved to DEFERRED.md as knowledge-pack, not agent) |
| `docs/prompts/quant/...` | DELETED (2 prompts: lead, factor-momentum) |
| `docs/prompts/research/...` | DELETED (3 prompts: lead, sec-filings, web-research) |
| `docs/prompts/risk/...` | DELETED (3 prompts: lead, black-swan, stress-concentration) |
| `docs/prompts/sentiment/...` | DELETED (2 prompts: lead, options-flow-insider) |
| `docs/prompts/strategy/...` | DELETED (2 prompts: lead, position-sizing-hedging) |
| `docs/prompts/technical/...` | DELETED (2 prompts: lead, chart-pattern) |
| `docs/prompts/scripts/validate-v2-prompts.py` | DELETED (replaced by `docs/runtime/evals/`) |
| `docs/prompts/ANALYZE-THE-PROJECT.md` | DELETED (analysis archived in this file + CHANGELOG) |
| `docs/AGENTS.md` | DELETED (superseded by senior-analyst + 5-prompt roster) |
| `docs/V1-ROSTER.md` | DELETED (superseded by 5-prompt roster in `docs/prompts/`) |
| `docs/LABOURIOUS_ARCHITECTURE.md` | DELETED (superseded by `docs/ARCHITECTURE.md`) |
| `docs/LABOURIOUS_SETUP.md` | DELETED (superseded by `docs/ROADMAP.md`) |
| `docs/FEATURES.md` | DELETED (superseded by `docs/USER-JOBS.md`) |
| `docs/SECURITY.md` | DELETED (folded into `docs/ROADMAP.md` + `docs/CANNOT-DO.md`) |

Net change: −103 prompts (89 frontend + 14 v2 deferred), −1 obsolete validator script, −1 obsolete meta-prompt, −6 obsolete top-level docs. **+5 rewritten prompts, +6 framing docs, +8 flow files, +1 README, +1 V2-PROMPT-STANDARD rewrite, +~1500 lines of runtime code.**

## What this audit didn't try to do

- **Run the system.** Audit is *paper analysis* — no app is built yet, so we trace what each prompt would do, not what the system does. See [`CONTEXT.md`](CONTEXT.md) for the framing fact that *prompt-level promises are hypotheses* — verifiable only against the eventual behaviour.
- **Pick a specific free-model winner.** The audit identifies Qwen 2.5 72B and Llama 3.3 70B as plausible. Picking one is a runtime-tuning question, not an audit question.
- **Pick a specific data source.** The audit identifies SEC EDGAR free + Google News RSS + yfinance + FRED as the v1 free toolset. Picking paid sources later when the milestone justifies it.
- **Solve the international-coverage gap.** Out of scope for v1; see [`CANNOT-DO.md`](CANNOT-DO.md).

## What you should not say about the project after this restructure

Three overclaimings to avoid:

- ❌ "Labourious is a high-level analyst." It's *the team you'd hire if you could afford one.* That's the distinction; don't' over-promise.
- ❌ "The prompts are proven to work." They are written to a strong discipline skeleton. Verifiable behaviour comes from the eval suite, not from text. **A passing eval suite is the only evidence.**
- ❌ "It can run on free models." **It *can* run on free models**, but hybrid routing (free for 90% of work, paid for synthesis only) is the path that closes the free-model adversarial-reasoning gap. All-free mode works for fast iterative dev.

Three claims you *can* make after this restructure:

- ✅ "The prompt library is structured: every prompt shares a skeleton, has worked examples, and obeys the abstain-over-invent discipline."
- ✅ "The architecture is buildable: there is one orchestrator, one lead, two specialists, one cross-cutting agent, and eight named flows."
- ✅ "The audit trail is honest: see this file for what was cut and why."

---

*The restructure is a foundation. Calibration (passing evals on actual f1 runs) is the next milestone; that work is described in [`ROADMAP.md`](ROADMAP.md).*
