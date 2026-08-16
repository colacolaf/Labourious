# V1 Roster — The First Product's Agents

**26 core agents + 1 pluggable example**, built for the Wharton Investment Competition workflow (client case → IPS → sector/company research → portfolio → final report). Decided August 2026 — see [`CONTEXT.md`](CONTEXT.md) for the reasoning and the interview decisions.

## Design principles

1. **Functional, not persona.** No celebrity personas in the core roster. Every prompt is functionalized from the 89-prompt library; the persona versions remain available as pluggable examples for users who want them.
2. **Leads coordinate, specialists go deep.** 12 category leads + 13 specialists + 1 final-report agent. Leads receive orchestrator briefs and delegate within their category; specialists do the deep, tool-heavy work.
3. **Sectors are knowledge, not agents.** Sector coverage lives in a single pluggable Sector Analyst that loads per-sector knowledge packs (research: separate agents that differ only in prompt content duplicate work and burn tokens).
4. **Client alignment filters everything.** All 12 categories are prompted to frame analysis against the client's goals, horizon, and risk tolerance (the comp's #1 judging criterion).
5. **Effort scales with question.** The orchestrator follows Anthropic-style effort tiers: simple → 1–3 agents, medium → 3–6, deep → up to 12. No uncapped delegation (multi-agent systems burn ~15× chat tokens).
6. **No competition-rules layer in v1.** The app is a research tool; comp-specific context (stock list, rules, case study) is the user's responsibility for now.

## Core roster (26)

### Leads (12)

| # | ID | Agent | Job | Source prompt (functionalize) | Connectors |
|---|----|-------|-----|-------------------------------|------------|
| 1 | `research-lead` | Research Lead | Coordinates the data layer — web, filings, news; the first pass on any request | `ground/research/michael-burry/` | web_search, url_fetch, sec_edgar, news |
| 2 | `fundamental-lead` | Fundamental Lead | Company deep dives — moats, management, financials | `floor-2/fundamental/warren-buffett/` | market_data, sec_edgar, web_search |
| 3 | `macro-lead` | Macro Lead | Market environment — rates, growth, currencies, geopolitics at a glance | `floor-2/macro/larry-fink/` | web_search, news, market_data |
| 4 | `technical-lead` | Technical Lead | Price action, trend, timing for entries/exits | `floor-2/technical/mark-minervini/` | market_data |
| 5 | `sentiment-lead` | Sentiment Lead | News tone, social mood, analyst revisions | `ground/sentiment/cathie-wood/` | news, web_search |
| 6 | `quant-lead` | Quant Lead | Factor exposure, momentum, regime — the numbers layer | `floor-2/quant/jim-simons/` | market_data |
| 7 | `risk-lead` | Risk Lead | Diversification, drawdowns, tail exposure | `floor-3/risk/nassim-taleb/` | market_data, web_search |
| 8 | `strategy-lead` | Strategy Lead | Asset allocation, portfolio construction, sizing | `floor-4/strategy/asset-allocation/` | market_data |
| 9 | `critique-lead` | Critique Lead | Challenges every major recommendation before it reaches the user | `floor-3/critique/charlie-munger/` | (reads other agents' outputs) |
| 10 | `compliance-lead` | Compliance Lead | Rules, restrictions, tax basics, concentration limits | `floor-3/compliance/preet-bharara/` | web_search |
| 11 | `altdata-lead` | Alt Data Lead | Supply chain, consumer spending, web/app traffic signals | `ground/alt-data/matthew-granade/` | web_search, news |
| 12 | `execution-lead` | Execution Lead | Trade timing, order planning, slippage thinking — **no broker in v1** | `floor-4/execution/order-routing/` (new prompt) | market_data |

### Specialists (13)

| # | ID | Agent | Job | Source prompt (functionalize/merge) | Connectors |
|---|----|-------|-----|-------------------------------------|------------|
| 13 | `web-research` | Web Research Agent | Web search + page reading; the data workhorse | `ground/research/web-research/` | web_search, url_fetch |
| 14 | `sec-filings` | SEC Filings & Regulatory Agent | 10-K/10-Q/8-K deep reads, footnote forensics | `ground/research/sec-regulatory/` (Hempton) | sec_edgar |
| 15 | `dcf-valuation` | DCF & Valuation Agent | Valuation models, multiples, fair-value ranges | `floor-2/fundamental/dcf-valuation/` | market_data, sec_edgar |
| 16 | `forensic-accounting` | Forensic Accounting Agent | Earnings quality, red flags, aggressive accounting | `floor-2/fundamental/forensic-accounting/` (Markopolos) | sec_edgar, market_data |
| 17 | `central-bank-liquidity` | Central Bank & Liquidity Agent | Rates, money supply, liquidity conditions | `floor-2/macro/central-bank-liquidity/` | web_search, news |
| 18 | `geopolitical-risk` | Geopolitical Risk Agent | Political/geopolitical events and market impact | `floor-2/macro/geopolitical-risk/` (Bremmer) | web_search, news |
| 19 | `chart-pattern` | Chart & Pattern Agent | Price action, support/resistance, pattern reads | `floor-2/technical/chart-pattern/` | market_data |
| 20 | `options-flow-insider` | Options Flow & Insider Agent | Options activity + insider/institutional moves | `ground/sentiment/options-flow-dark-pool/` (Najarian) + `ground/sentiment/insider-institutional/` — merged | market_data, news |
| 21 | `factor-momentum` | Factor & Momentum Agent | Factor exposure, momentum screens | `floor-2/quant/factor-analysis/` + `floor-2/quant/momentum-trend/` — merged | market_data |
| 22 | `stress-concentration` | Stress & Concentration Agent | Portfolio stress tests, concentration checks | `floor-3/risk/var-stress-test/` + `floor-3/risk/correlation-concentration/` — merged | market_data |
| 23 | `black-swan` | Black Swan Agent | Tail risks, crash detection, what-if scenarios | `floor-3/risk/black-swan-detection/` (Sornette) | market_data, web_search |
| 24 | `devils-advocate` | Devil's Advocate Agent | The bear case on every big idea | `floor-3/critique/devils-advocate/` (Whitney) | (reads other agents' outputs) |
| 25 | `position-sizing-hedging` | Position Sizing & Hedging Agent | How much to allocate, protective hedges | `floor-4/strategy/position-sizing-intern/` + `floor-4/strategy/hedging-protection/` — merged | market_data |

### Cross-cutting (1)

| # | ID | Agent | Job | Source prompt |
|---|----|-------|-----|---------------|
| 26 | `final-report` | Final Report Agent | Turns the synthesized research into IPS + Final Report sections (investment policy, strategy narrative, sector breakdown, rationale) | **NEW** — style reference: `penthouse/agents/portfolio-manager/` synthesis format |

## Pluggable-agent policy (when to add an agent outside the core)

**Do not add more *analyst* agents. Specificity lives in knowledge packs, not agents.** This is the research-backed rule (Anthropic: multi-agent burns ~15× chat tokens and only pays off for genuinely parallelizable work; low-variance agents amplify each other's blind spots instead of diversifying them). A new agent earns its existence only if it passes one of two tests:

1. **Distinct data/tool surface** — it reaches a data source the core 26 cannot (e.g. on-chain/DeFi data). If it differs only in *knowledge*, it's a knowledge pack on an existing agent, not a new agent.
2. **Distinct control-flow role** — it gates or watches the pipeline rather than producing analysis (e.g. request vetting, risk interrupt, memory). These sit outside the hub-and-spoke, so they don't add routing surface.

Anything else — sector-specific, asset-specific, persona variants — ships as a **knowledge pack or a prompt variant** on an existing agent. See the Sector Analyst below as the canonical example of the "one agent, loadable packs" pattern.

## Pluggable example (ships disabled, one-click to add)

| ID | Agent | Job | Notes |
|----|-------|-----|-------|
| `sector-analyst` | Sector Analyst | One agent that loads per-sector knowledge packs — Tech, Healthcare, Energy, Financials, Consumer, Industrials, Materials, Utilities, Communication Services, Real Estate, ETFs | **NEW** — mirrors the comp's sector-team structure; per-sector knowledge as loadable packs, not separate agents |

Also available as pluggable examples from the library: the persona agents (Burry, Buffett, Taleb, etc.), Entrance Bodyguard (request vetting), PM Bodyguard (risk interrupt), crypto specialists (Buterin, Svanevik, DeFi, Tokenomics, Protocol Risk), and the storage/memory/control/tasks agents.

## Deferred to v2

| Category | Why deferred |
|----------|--------------|
| Crypto / Digital Assets | Not selected for v1; pluggable agents exist |
| Tasks / Automation | Daily briefings & scheduling — the user said "maybe v2" |
| Memory / Knowledge Graph | v1 memory is file-based notes + chat history only |
| Control (QC, health monitor) | Orchestrator-level quality rules cover v1; dedicated agents later |
| Team roles (sector owners) | Single-user v1; the data model leaves room for it |
| Competition context layer | Explicitly declined for v1 — app stays generic |

## The default delegation map

What the orchestrator wakes for the flagship flows:

**"Analyze NVDA"** → Research Lead (data pass) → Fundamental Lead (deep dive) + DCF & Valuation + Forensic Accounting + Technical Lead (chart read) + Sentiment Lead (tone) → Risk Lead (tail check) → Critique Lead + Devil's Advocate → synthesis.

**"Review my portfolio"** → Strategy Lead (allocation) + Risk Lead (stress & concentration) + Quant Lead (factor exposure) + Macro Lead (environment) → Critique Lead → synthesis.

**"Find undervalued mid-cap healthcare stocks"** → Research Lead (screen candidates) + Factor & Momentum (screens) → Fundamental Lead + DCF & Valuation (shortlist) → Sentiment Lead (check) → Risk Lead (vet) → synthesis.

**"Should I rotate out of tech?"** → Macro Lead + Research Lead (environment) → Quant Lead (regime/factors) + Technical Lead (trend) → Strategy Lead (allocation) → Risk Lead → Critique Lead → synthesis.

Each of these is exactly the shape of the comp's deliverables — every flow ends with material that feeds the IPS and the Final Report.
