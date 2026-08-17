# DEFERRED — what we cut and why it's not gone

> Deferred ≠ deleted. Every entry below is parked with a reason it doesn't ship in v1 and a gate it must pass to come back.

What's in this file is a *thesis*: "this idea is valid; it just doesn't earn its place in the 5-prompt roster until such-and-such happens." When the gate is met, the entry graduates back into the codebase — into `docs/prompts/` or `docs/flows/` or under `docs/runtime/`, whichever fits.

What's **not** here: things we cut because they were *wrong* (those are gone, in [`RESTRUCTURING.md`](RESTRUCTURING.md)). What's here: things we cut because they were *premature*.

---

## The 23 deferred prompts from the 28-prompt v2 library

The following prompts were deleted from `docs/prompts/` in this restructure. They are not gone — they are *deferred*. The reasoning in each row is the gate they must pass to come back.

### 11 deferred Lead prompts

| ID | What it would do | Gate to re-hire |
|----|------------------|-----------------|
| `research-lead` | Coordination of web + filings + news data layer | **Re-hire if:** a flow other than f1 grows past 4 agents and needs explicit data coordination. Today, senior-analyst plays this role. |
| `macro-lead` | Top-down view — rates, growth, geopolitics | **Re-hire if:** f5 (sector deep-dive) or f8 (macro overlay) needs a dedicated macro voice. For now, senior-analyst loads macro as a rubric on demand. |
| `technical-lead` | Chart patterns, price action, momentum | **Re-hire if:** a user asks for entry-timing on a flow other than f4 (earnings review). Today, f1 + f4 surface technical context inline. |
| `sentiment-lead` | News tone, social mood, analyst revisions, options flow | **Re-hire if:** the news tool layer matures past keyword mentions and needs NL tone-judgment. For now, system is skeptical of sentiment by default. |
| `quant-lead` | Factor exposure, regime, momentum quant screens | **Re-hire if:** f6 (thematic screen) materializes — quant screens are its backbone. Today, senior-analyst does basic factor checks. |
| `risk-lead` | Diversification, drawdowns, tail exposure | **Re-hire if:** f1's reviewer role grows past what devil's-advocate can catch. For now, devil's-advocate surfaces the worst risks. |
| `strategy-lead` | Asset allocation, portfolio construction | **Re-hire if:** f7 (risk event) returns "rotate out of X" — allocation advice becomes the deliverable. For now, senior-analyst gives one-name theses. |
| `critique-lead` | Base-rate analysis, conflict resolution | **Re-hire if:** a flow's disagreements grow past what a single devil's-advocate + senior-analyst can resolve. For now, the orchestrator surfaces conflicts. |
| `compliance-lead` | Wash sales, PDT, tax basics, concentration caps | **Re-hire if:** a user explicitly asks for a compliance question AND the orchestrator's brief can route there. Today, the system politely declines such questions — see `CANNOT-DO.md`. |
| `altdata-lead` | Satellite, supply-chain, credit-card, web-traffic data | **Re-hire if:** a paid data source or scrape pipeline goes live. Today, all alt-data is out of budget for free models. |
| `execution-lead` | Order routing, slippage | **Permanently deferred.** Trading execution is out of scope; see `CANNOT-DO.md`. |

### 11 deferred Specialist prompts

| ID | What it would do | Gate to re-hire |
|----|------------------|-----------------|
| `dcf-valuation` | DCF models, multiples, fair-value | **Re-hire if:** f1's intrinsic-value section needs more than a senior-analyst paragraph. Today, senior-analyst computes a range inline. |
| `central-bank-liquidity` | Rates, money supply | **Re-hire if:** f8 (macro overlay) ships and a dedicated liquidity sub-routine earns its place. |
| `geopolitical-risk` | Political events + market impact | **Re-hire if:** a flow explicitly focuses on a country-level event (f7 risk-event triggering it). |
| `chart-pattern` | Support / resistance / patterns | **Re-hire if:** a user asks for technical analysis specifically. Today, senior-analyst does chart-aware commentary. |
| `options-flow-insider` | Options activity, dark pools, insider moves | **Re-hire if:** a user pays for an options-flow data source. Today, the data is out of the free tool layer. |
| `factor-momentum` | Factor exposure, momentum screens | **Re-hire if:** a flow grows that needs systematic screening (f6-thematic-screen, mostly). |
| `stress-concentration` | Portfolio stress, concentration checks | **Re-hire if:** a portfolio-aware flow ships. Today, the system is single-name focused. |
| `black-swan` | Tail-risk detection, scenario modelling | **Re-hire if:** a flow exposes multiple correlated names together (compare-tickers at scale). For now, devil's-advocate catches concentration. |
| `position-sizing-hedging` | Sizing + protective hedges | **Re-hire if:** the system learns the user's portfolio, position sizing, or hedge preferences. |
| `web-research` | Web search + page reading | **Re-hire if:** the news tool layer proves insufficient for a flow. Today, web-fetch + news-rss cover the same surface. |
| `sec-filings` | 10-K/10-Q deep reads, footnote forensics | **Re-hire if:** forensic-accounting's specificity proves insufficient — i.e. a flow needs a deeper primary-source digger. Today, forensic-accounting owns this. |

### 1 deferred Pluggable prompt

| ID | What it would do | Gate to re-hire |
|----|------------------|-----------------|
| `pluggable/sector-analyst` | One agent loading per-sector knowledge packs | **Re-hire if:** a Wharton team or sector user demands sector-specific framing. Today, sectors are knowledge packs loaded into senior-analyst's prompt, not separate agents. |

---

## The 89 deleted `frontend/` prompts

These are **not deferred**. They are **deleted**, gone, beyond retrieval. The reasoning is in [`RESTRUCTURING.md`](RESTRUCTURING.md): the v1 library is functionally — and structurally — a superset of the 89-prompt zoo, with celebrity personas removed. Anything of practical value from the 89 was already absorbed into the 28 v2 prompts, then trimmed into the 5 we kept. Anything *not* absorbed was, by definition, low-value. Resurrecting a prompt from the 89 would re-introduce a persona we explicitly removed.

**The list:** all of `docs/frontend/ground/`, `docs/frontend/floor-2/`, `docs/frontend/floor-3/`, `docs/frontend/floor-4/`, `docs/frontend/penthouse/`. That's 89 system prompts across categories crypto, fundamental, macro, quant, technical, risk, critique, compliance, execution, memory, strategy, alt-data, research, sentiment, storage, control, tasks, perimeter, penthouse. Each had a celebrity persona voice (Burry, Buffett, Taleb, Bremmer, Crawford, Thorp, Bharara, Whitney, Minervini, Fink, Simons, Rosenbloom, Buterin, Svanevik, Swensen, Sornette, Markopolos, Wood, Najarian, Hempton). No persona ships in v1 of the Analyst's Bench.

If a specific prompt is *uniquely* missed: write a deliberate `docs/prompts/<category>/<agent>/system-prompt.md` of your own with the contribution it would make. Each agent in the new library is a *function* the system needs, and the directories in `docs/prompts/` are the only "real estate" we'll re-add.

---

## Design conventions that drive what's deferred vs. cut

These are not arbitrary. They are research-grounded choices and they apply forever.

### 1. Specificity lives in knowledge packs, not agents

**Anthropic's multi-agent paper, June 2025:** "Multi-agent systems earn their ~15× token cost only for high-value, heavily-parallelizable, breadth-first tasks. Low-variance extra agents amplify each other's blind spots instead of diversifying them."

**LangChain architecture guide:** "Use subagents for distinct data/tool surfaces or distinct control-flow roles. Specificity in domain knowledge is better as loadable skills than as separate agents."

**Implication:** if two agents would differ only in what they *know* (not what they *do*), one agent with a knowledge pack per use case is the right shape. **Sectors, asset classes, ticker-specific information — all knowledge packs.** Not agents.

### 2. Pluggable agents must pass one of two tests

A new agent earns its existence only if it passes one of two gates:

1. **Distinct data/tool surface** — it reaches a data source the 5 core prompts cannot (e.g. on-chain/DeFi data, options flow, satellite imagery). If it differs only in *knowledge*, it's a knowledge pack on an existing agent, not a new agent.
2. **Distinct control-flow role** — it gates, vets, or watches the pipeline rather than producing analysis (e.g. request vetting, risk interrupt, memory). It sits outside the hub-and-spoke so it adds routing surface.

Anything else — sector-specific, asset-specific, persona variants — ships as a knowledge pack or a prompt variant on an existing agent.

### 3. Effort modes are a runtime knob, not a prompt-text knob

The v2 library had `SCAN / STANDARD / DEEP / COMPRESSED` baked into every prompt. That meant 28 prompts × 4 modes = 112 different output shapes, scattered across 28 files. The runtime now reads `DEPTH` from the brief and applies it uniformly. This **doubles the speed of prompt iteration** without losing any mode coverage. Prompts are simpler; the runtime is smarter.

### 4. Per-asset gates are runtime-enforced, not prompt-text

The same logic: every agent having its own "Per-asset gate" section was 28 duplications of the same rule. The runtime now enforces: "every ticker in the orchestration must appear in the final-report's coverage." Same enforcement, less duplication, less drift.

---

## The gate table (reference)

A feature doesn't come back without passing its gate. Three gate shapes, applied consistently:

| Gate shape | Example |
|------------|---------|
| "until X flow ships" | `technical-lead` re-hires when f3/f4 need chart-aware sections |
| "until X data source goes live" | `altdata-lead` re-hires when a pipeline is running with budget |
| "until X user demand" | `compliance-lead` re-hires when the orchestrator sees a real comp-question |

When the gate is met, the entry moves out of this doc and into either `docs/prompts/` (a new agent) or `docs/flows/` (a flow wrapper) or `docs/runtime/` (a tool), whichever is the right shape. **The plurality is deliberate**: a feature should land where the codebase expects it, not where it's easy to drop.

---

## What isn't in this file

Things that *look like deferred features but are actually wrong* move to `RESTRUCTURING.md` instead. Examples:

- "26-agent roster" — wrong, not deferred (cut: 5 prompts is the steady state).
- "Celebrity persona agents in the core roster" — wrong, not deferred (cut: those were nostalgia).
- "Per-agent freshness tiers as separate prompt sections" — wrong, not deferred (cut: a runtime concern, not a prompt-text concern).
- "The v2 validator as proof-of-correctness" — wrong, not deferred (cut: it lints structure; doesn't test behavior).

See [`RESTRUCTURING.md`](RESTRUCTURING.md) for the wrong-things-was cut list.
