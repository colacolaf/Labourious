# CANNOT-DO — what this project will not do

> This file is the credibility boundary. Every claim in the rest of `docs/` should be read against this list. If a feature sounds impressive elsewhere but conflicts with what's below, **this file wins**.

The Analyst's Bench is a *force multiplier*, not a finance professional. It runs analyst-quality short-form memos on public companies with citation grounding, abstention honesty, and primary-source priorities. It does that well. It does *not* do many other things that adjacent projects often pretend to.

This file is honest about which is which. The split is in three categories:

1. **Today cannot** — the system does not currently produce this. May produce it later under named conditions.
2. **Will not in this project** — out of scope permanently; a different product solves it.
3. **Will always be lossy** — even with infinite engineering, there are hard physical limits (model capacity, data access) that don't go away.

---

## Today cannot (but might)

These are real limitations. They will go away in named ways once specific milestones are met. Each row names the milestone.

### 1. Real-time market data

**Today:** delayed OHLCV (Yahoo Finance via `yfinance`, FRED for macro). Typical lag: 15 minutes for prices; daily for fundamentals.

**Why it can't:** Free data sources are delayed by vendor contract. Real-time prices cost ~$100–500/month per provider (Polygon, IEX, NLS).

**Milestone to unlock:** A user pays for a paid data source *and* the system remains defensible on free sources for f1/f2/f4. Until then, f1 is fine with delayed prices — current price isn't usually what determines a thesis.

### 2. Options flow / dark pool data

**Today:** no options-flow layer. The system understands that options flow can be a signal but cannot retrieve it.

**Why it can't:** Paid data (Cboe, OPRA, Unusual Whales, BlackBox) is expensive and requires specific per-provider agreements.

**Milestone to unlock:** A dedicated options-flow tool adapter (paid) integrated into a flow that *needs* it (probably f7 risk-event, eventually f4 earnings review).

### 3. Real backtesting

**Today:** the system does not run a backtest. A user query of "did your thesis on NVDA beat the S&P since last quarter" returns *"I don't track returns of past theses — but my thesis register has the dated theses; you can compute that externally."*

**Why it can't:** A proper backtest engine needs 10+ years of clean price/fundamental data, corporate-action adjustments, and a survivorship-bias-audited universe. Free sources lack this.

**Milestone to unlock:** A paid data source (e.g. Norgate, Polygon paid tier) integrated with the thesis register. **Even then, "track returns of past theses" is the most useful next artifact** — not a full backtest framework.

### 4. Live news within the past 5 minutes

**Today:** Google News RSS is typically 5–30 minutes behind breaking news; major outlets may vary. For Wharton comp and analysis-purposes, this is plenty.

**Why it can't:** Free RSS doesn't atomize; paid news APIs (Bloomberg Terminal, NewsAPI premium) are costly.

**Milestone to unlock:** A subscription news source or live wire integration. Until then, no real-time alerts; analysis is "as of the run time."

### 5. International-language sources (CN/JP/KR filings & news)

**Today:** English-only primary sources. Hong Kong / Tokyo / Shanghai filings are not in scope. Korean KRX / Chinese SSE filings aren't reachable from the free tool layer.

**Why it can't:** Free SEC EDGAR is US-only. International equivalents (HKEX, JPX, SSE) require per-jurisdiction adapters, often paid.

**Milestone to unlock:** None named. International coverage is a *v3+* conversation.

### 6. Private companies

**Today:** the system is built for public equity. There is no private-company data layer (no Pitchbook integration, no manual entry path).

**Why it can't:** Pitchbook, Crunchbase Pro, CB Insights pay $30k+/year; without them, private-company research is mostly coffee-and-emails.

**Milestone to unlock:** Either an alternative-data purchase or a "user supplies the deck" mode. **Out of scope for v1.**

### 7. Multi-user / team workflows

**Today:** single-user. The thesis register is per-user (one local SQLite). Comments, shareability, role permissions don't exist.

**Why it can't:** A multi-user product has authentication, sharing, conflict-of-thesis reconciliation, and versioning concerns far past the runtime skeleton. Not a good first build.

**Milestone to unlock:** A v3+ build with an explicit multi-user mode; the runtime skeleton supports the data model already.

### 8. Broker integration / order placement

**Today:** no broker. Even if a flow asks "How do I buy NVDA?", the answer is *"use your broker"* — the system provides the thesis, not the execution.

**Why it can't:** Regulatory. Order placement requires broker-dealer registration, KYC/AML, and capital-reserve infrastructure. None of which an analytical product should carry.

**Milestone to unlock:** Never. **Permanently out of scope.** See [`ROADMAP.md`](ROADMAP.md) non-feature list.

### 9. A polished UI

**Today:** CLI. `python docs/runtime/runtime.py --flow f1 --ticker NVDA --model ollama/llama3.3:70b` returns a memo JSON envelope and a `markdown/` render.

**Why it can't:** A polished UI is post-runtime. The runtime ships first; the UI is downstream of which user nails which flow first.

**Milestone to unlock:** A user commits to a UI direction (web/Electron/CLI-notebook-augmentation). Until then, CLI is the entire surface.

### 10. Multi-day alerts ("tell me when X happens")

**Today:** there's no scheduler, no WebSocket pull, no email/SMS ping. The system answers *when called*, not *when relevant*.

**Why it can't:** A scheduler is a different product (cron + webhooks + delivery). Out of scope for v1.

**Milestone to unlock:** A daily-briefing flow (`f11-daily-briefing`, deferred). Until then, the user re-runs flows.

---

## Will not (permanently)

These are decisions, not limitations. The cost of doing them is greater than the value. A different product serves them.

### 1. Trading execution, order placement

See above. Regulatory surface area, not an analytical one.

### 2. Becoming a registered investment advisor (RIA)

The system surfaces *analysis*, not *advice*. It does not say "you should buy X." It says "the bull case is X, the bear case is Y, the bottom line is Z conviction." The user makes the decision. **This boundary is what keeps Labourious out of FINRA / SEC RIA scope.**

### 3. Custody of user data on a Labourious server

Local-first is a design principle, not a slogan. The thesis register, chat history, and config live on the user's machine. **No Labourious backend, period.** A `~/.labourious/` directory and that's it.

### 4. Replacing human analyst judgment

A 70B model is not a Goldman analyst. Even a frontier model is not a Goldman analyst — it's an *amplifier*. The Analyst's Bench gives a human analyst (or a Wharton team, or a retail user) a defensible first draft, not a verdict. **The thesis is "the team you'd hire if you could afford one"** — which is not the team you'd trust with custody.

### 5. ESG scoring

Data is contested (ratings disagree by 30–100 points). Methodology is unsettled. The most-honest answer the system can give is *"different methodologies disagree by 30+ points; pick one and we'll surface its signal"*. That's not a feature, it's a footnote.

### 6. Crypto / DeFi research

Crypto research has unique data, regulatory, and disclosure challenges. **The system works on equities, where the SEC EDGAR free API exists.** Crypto is structurally different (no primary source equivalent), and a separate product line serves it.

### 7. Real-time portfolio rebalancing

Out of scope. The system provides analysis; the user's broker and tax-aware rebalancer do back-office work.

### 8. Investment recommendations for prohibited categories

The system can describe a sector but will not say, e.g., *"buy cannabis names"*. There's a thin line between producing analysis and dispensing legal advice. **Describe, don't prescribe.**

---

## Will always be lossy

These limits are physics, not engineering decisions.

### 1. Long-context degradation

Even Claude Sonnet 4.5 loses accuracy on inputs over ~50k tokens. Models today (free or paid) degrade on long context. The system mitigates this via prompt caching and shared prefixes, but a 50k-token input will always cost accuracy vs. a 5k-token input on the same task.

### 2. Free 70B-class models ≠ frontier quality on adversarial reasoning

The `Qwen 2.5 72B` / `Llama 3.3 70B` models used for hybrid-routing the bulk of work are 70–85% as good as Claude Sonnet 4.5 on instruction-following jobs (per the prior audit). On adversarial reasoning (devil's-advocate, geopolitical-risk, geopolitical synthesis), the gap is wider — closer to 50–70%. **The hybrid plan routes the final-report agent to Sonnet to close that gap; this remains a meaningful bound.**

### 3. Data source contamination

The free tier of any data source has occasional outages, rate-limit surprises, schema changes, or — for financials — survivorship-bias issues. The system reports `connector_status: FAILED | PARTIAL` honestly. It does not silently substitute a guess. **But it cannot conjure data that doesn't exist.** A name with no SEC filings is a name the system can't analyze.

### 4. Unknown unknowns in market events

A liquidation event, a sudden regulatory change, a major counter-party failure — all of these can break a thesis in hours. The system produces theses as of the run time. It is not a real-time monitoring system. **No analysis product compensates for this — the user has a brain for a reason.**

### 5. Model hallucination on small queries

For small numeric queries (prices, dates, exact percentages), even frontier models hallucinate occasionally. The system mitigates via citation discipline (`f1` produces ≥ 80% of claims cited to a primary URL). **But no prompt can be "100% hallucination-free"**. The eval suite (`docs/runtime/evals/test_hallucination.py`) is what keeps this honest.

---

## How to read the rest of the docs against this file

The "decision-ready" / "analyst quality" / "high-leverage" claims in [`CONTEXT.md`](CONTEXT.md) and the "trust / action / speed / defensibility / comparison" jobs in [`USER-JOBS.md`](USER-JOBS.md) all assume this file exists. The 5 user jobs are what the project serves; this file is the boundary of what serving them looks like.

If a user asks "can the system do X?" the answer is:
- "yes, today" → check whether the answer conflicts with any *will not* line above.
- "no, today" → check whether the answer's milestone above is plausible.
- "no, ever" → direct them to the *will not* reasoning.

This file is the most important doc in the codebase for credibility. Update it whenever a milestone is reached.
