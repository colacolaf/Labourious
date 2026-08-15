# Labourious Agent Taxonomy

Agents are organized into **categories** (formerly "rooms"). Categories are a flat organizational tag — there is no building, no floors, and no hierarchy beyond lead → team.

## The Calling Model

```
User → Orchestrator → (task briefings, hub-and-spoke) → Specialist agents → Orchestrator → User
```

- The **orchestrator** is the only agent the user talks to.
- Specialists never call each other directly — all communication flows through the orchestrator.
- A task briefing carries: **TASK** (what to do), **CONTEXT** (relevant history/findings), **URGENCY** (routine/elevated/immediate), **DEPTH** (scan/standard/deep).
- Every specialist returns a **structured output** the orchestrator can consume.

## Categories & Base Leads

16 base leads ship with the skeleton — one per category. The full prompt library holds 89 agents; any of them can be a base agent, and users can add their own.

| # | Category | Lead | Lead prompt | Team (in library) |
|---|----------|------|-------------|-------------------|
| 1 | Research | Michael Burry | `ground/research/michael-burry/` | Web Research, SEC/Regulatory (John Hempton), Filings Intern, Academic Research, News Aggregation, Data Scout |
| 2 | Risk | Nassim Taleb | `floor-3/risk/nassim-taleb/` | VaR & Stress Test, Correlation & Concentration, Black Swan (Didier Sornette), Drawdown Monitor, Liquidity Risk, Factor Risk |
| 3 | Macro | Larry Fink | `floor-2/macro/larry-fink/` | Geopolitical Risk (Ian Bremmer), Central Bank & Liquidity, Currency & Sovereign Debt, Global Growth Tracker |
| 4 | Quant | Jim Simons | `floor-2/quant/jim-simons/` | Statistical Arbitrage (Ed Thorp), Options & Volatility, Momentum & Trend, Machine Learning, Regime Detection, Risk Budgeting |
| 5 | Fundamental | Warren Buffett | `floor-2/fundamental/warren-buffett/` | DCF & Valuation, Moat & Competitive Analysis, Management Quality, Forensic Accounting (Harry Markopolos), Catalyst & Event, Industry Structure |
| 6 | Technical | Mark Minervini | `floor-2/technical/mark-minervini/` | Chart & Pattern, Volume & Order Flow, Market Microstructure, Technical Signal Engine |
| 7 | Sentiment | Cathie Wood | `ground/sentiment/cathie-wood/` | Options Flow & Dark Pool (Jon Najarian), News Sentiment, Social Media & Retail, Insider & Institutional, Analyst & Earnings Revision |
| 8 | Strategy | David Swensen | `floor-4/strategy/asset-allocation/` | Tactical Overlay Intern, Hedging & Protection, Tax Optimization, Portfolio Construction, Position Sizing Intern |
| 9 | Execution | — (unassigned) | — | Order Routing, Execution Algorithm, Timing & Slippage, Pre-Flight Check |
| 10 | Memory | — (unassigned) | — | Knowledge Graph, Learning & Reflection |
| 11 | Critique | Charlie Munger | `floor-3/critique/charlie-munger/` | Devil's Advocate (Meredith Whitney), Bear Case Intern, Blind Spot Detector, Historical Analog Intern, Assumption Challenger, Conflict Resolution |
| 12 | Compliance & Tax | Preet Bharara | `floor-3/compliance/preet-bharara/` | Regulatory Compliance, Cross-Border Tax (H. David Rosenbloom), Trading Restriction |
| 13 | Alternative Data | Matthew Granade | `ground/alt-data/matthew-granade/` | Satellite & Geospatial (James Crawford), Supply Chain, Consumer Spending, Weather & Commodity, Web & App Traffic |
| 14 | Crypto/Digital Assets | Vitalik Buterin | `floor-2/crypto/vitalik-buterin/` | On-Chain Analytics (Alex Svanevik), DeFi & Yield, Tokenomics, Protocol Risk |
| 15 | Control | — (unassigned) | — | Quality Control, Agent Health Monitor |
| 16 | Tasks/Automation | — (unassigned) | — | Daily Briefing, Opportunity Scout |

**Unassigned leads** (Execution, Memory, Control, Tasks) will be filled during the skeleton build — either from the existing library (their team agents are already prompted) or new prompts.

## Non-Category Agents

| Agent | Category note |
|-------|---------------|
| Portfolio Manager | Former "penthouse" main agent — its routing/synthesis logic is the ancestor of the orchestrator prompt; the persona is retired (neutral orchestrator) |
| PM Bodyguard | `penthouse/agents/pm-bodyguard/` — its monitoring/interrupt protocol is a candidate for a Control-category agent or an orchestrator safety layer |
| Entrance Bodyguard | `ground/perimeter/entrance-bodyguard/` — perimeter agent; candidate for a request-vetting layer in front of the orchestrator |

## Agent Levels

The prompt library uses a tier system that carries over to the app:

| Level | Meaning | Example |
|-------|---------|---------|
| **T1 — Lead** | Category lead; receives orchestrator briefs and delegates within the category | Michael Burry, Nassim Taleb |
| **T2 — Named specialist** | A named expert persona with deep domain prompts | Harry Markopolos, Ed Thorp |
| **T3 — Utility agent** | Standard specialist with tool protocols and quality gates | Web Research Agent, DCF & Valuation Agent |
| **T4 — Intern** | Lightweight agents for overflow or time-sensitive work | Bear Case Intern, Position Sizing Intern |

## Custom Agents (Pluggable)

Users add agents by:
1. **In-app editor** — create/duplicate an agent, edit its prompt, pick its model and connectors; saved to the agents folder.
2. **File drop** — place a config file (JSON) + a system-prompt markdown file in the agents folder; the app picks it up.

Every agent needs: id, name, category, model, system prompt, connector list.

## System Prompt v2

The 89 prompts in the library are the base. The v2 upgrade adds (per agent):
- **Connector + tool-use protocols** — exact instructions per tool, when to call, output contracts, failure handling
- **Delegation + routing protocols** — how leads receive briefs and how they delegate
- **Structured output contracts** — every agent returns JSON with a defined schema the orchestrator consumes

The framework docs under `docs/frontend/` (SYSTEM-PROMPT-FRAMEWORK, audit frameworks, test templates) define how this upgrade is done and validated.
