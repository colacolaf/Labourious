# AGENTS.md — The Complete Agent System

## The Portfolio Manager (Main Orchestrator)

**Personality:** Calm, collected, deliberate. Never rushed. Always thorough.

The Portfolio Manager is the ONLY agent the user directly chats with. It has a comprehensive system prompt (2-5 pages) with dedicated sections on every subagent and exactly when to call each one. When the user makes a request, the PM automatically decides which agents to wake up — no user confirmation needed.

**How the PM works:**
1. User sends a request ("Analyze my tech holdings," "Should I rotate into bonds?", "Find undervalued mid-cap healthcare with strong moats")
2. PM evaluates which rooms are needed based on its routing prompt
3. PM sends the request to the relevant **Room Leads** (not individual agents)
4. Each Room Lead triages — decides which sub-agents in their room to activate
5. Sub-agents do deep research (1-10 minutes depending on complexity), cite fresh sources
6. Room Lead synthesizes the room's sub-agent outputs into one clean response and sends it to the PM
7. PM synthesizes ALL room-level outputs into:
   - A detailed report with comprehensive analysis
   - A concise summary
   - Clear options for what to do next
8. If the user is time-sensitive, PM uses only lightweight agents and interns

**Hierarchy:** PM → Room Leads → Sub-agents → Interns. The PM only knows ~16 room leads, not 50+ individual agents.

**Rules & Mandates:** Users define persistent constraints the PM always follows. Examples:
- "Never invest in fossil fuels"
- "Keep 20% cash minimum"
- "Only trade during NYSE hours"
- "No single position over 5% of portfolio"
- "Prioritize dividend yield > 2%"

**Conflict Resolution:** When agents disagree (e.g., Quant says BUY, Critique says SELL), the Execution Room's dedicated conflict resolution agent makes the final call or presents both arguments to the user.

---

## Agent Characteristics

Every subagent has:
- **A multi-page system prompt** defining its personality, expertise boundaries, tool access, citation requirements, output formatting, and "unknown" handling
- **An attitude/personality** — each agent feels distinct
- **Tool access** as allowed by its system prompt (web search, file read/write, API calls, database queries, code execution)
- **Persistent memory** across calls — vector DB + knowledge graph
- **Source citation** — must cite fresh/recent data, no stale information
- **Research depth** — 1-10 minutes depending on the agent and request complexity

**Intern Agents:** Lighter-weight versions of main agents. Called when:
- The sophisticated subagent is overwhelmed
- The user has a time-sensitive request
- A task doesn't require the full agent's depth

**Agent Overlap:** Agents intentionally overlap. Quant and Risk might analyze the same data from different angles. Multiple perspectives produce better insights.

---

## Room Taxonomy (16 Rooms, 50+ Agents)

### Room 1: Research (3-5 agents)
Deep web research, SEC filings, news, academic papers, alternative data gathering.

| Agent | Role |
|-------|------|
| **Web Research Agent** | Searches the web, finds relevant articles, papers, data sources |
| **SEC/Regulatory Research Agent** | Reads filings (10-K, 10-Q, 8-K), extracts key data points<br>↳ *Intern: Hedge Fund & Political Filings Agent* — 13F filings, campaign finance, lobbying disclosures, PAC activity |
| **Academic Research Agent** | Searches academic databases, finds peer-reviewed research |
| **News Aggregation Agent** | Aggregates and filters news from multiple sources, removes noise |
| **Data Scout Agent** | Discovers new data sources, APIs, datasets the other agents might need |

### Room 2: Risk (4-6 agents)
Portfolio stress testing, VaR, drawdown analysis, correlation matrices, black swan detection, liquidity risk, factor exposure.

| Agent | Role |
|-------|------|
| **VaR & Stress Test Agent** | Calculates Value at Risk, runs Monte Carlo simulations, stress scenarios |
| **Correlation & Concentration Agent** | Analyzes portfolio correlation matrix, finds hidden concentration risks |
| **Black Swan Detection Agent** | Scans for tail-risk events, fat-tail distributions, systemic vulnerabilities |
| **Drawdown Monitor Agent** | Tracks drawdown, recovery time, sets alert thresholds |
| **Liquidity Risk Agent** | Measures ability to exit positions without moving markets; detects illiquid assets and slippage risk |
| **Factor Risk Agent** | Calculates exposure to market factors — Value, Growth, Momentum, Quality, Volatility, Size, Duration, Inflation |

### Room 3: Macro (4 agents)
Global macroeconomics — central bank policy, GDP, inflation, geopolitics, currency flows, sovereign debt.

| Agent | Role |
|-------|------|
| **Central Bank & Liquidity Analyst** | Fed, ECB, BoJ, PBOC — policy shifts, rate expectations, QE/QT, balance sheets, global liquidity conditions |
| **Geopolitical Risk Agent** | Wars, elections, sanctions, trade disputes, supply chain disruptions, political instability — market/sector/commodity impact |
| **Currency & Sovereign Debt Agent** | Currency flows, sovereign credit risk, yield spreads, capital flight |
| **Global Growth Tracker** | GDP trajectories, PMI data, employment trends across major economies |

### Room 4: Quant (5-7 agents)
Quantitative modeling, factor analysis, statistical arbitrage, momentum, mean reversion, options pricing, regime detection, risk budgeting.

| Agent | Role |
|-------|------|
| **Factor Analysis Agent** | Runs factor models (value, momentum, quality, size, vol), decomposes returns |
| **Statistical Arbitrage Agent** | Pair trading, cointegration, mean reversion strategies |
| **Options & Volatility Agent** | Options pricing models, implied vol surfaces, volatility arbitrage |
| **Momentum & Trend Agent** | Time-series momentum, cross-sectional momentum, trend following signals |
| **Machine Learning Agent** | ML models for pattern recognition, anomaly detection, predictive signals |
| **Regime Detection Agent** | Classifies market regimes (bull, bear, sideways, crisis, high-vol) using HMM, GARCH, volatility clustering — tells other agents what environment we're in so they weight signals accordingly |
| **Risk Budgeting & Allocation Agent** | Mean-variance optimization, Black-Litterman, Kelly criterion, risk parity — bridges the gap between factor signals and actual position sizing |

### Room 5: Fundamental (5-6 agents)
Company deep-dives, DCF models, competitive moat analysis, management quality, forensic accounting, catalysts, industry dynamics.

| Agent | Role |
|-------|------|
| **DCF & Valuation Agent** | Builds discounted cash flow models, intrinsic value estimates |
| **Moat & Competitive Analysis Agent** | Analyzes competitive advantages, barriers to entry, industry positioning |
| **Management Quality Agent** | Evaluates executive track records, capital allocation, insider behavior |
| **Forensic Accounting Agent** | Detects earnings manipulation, accounting red flags, aggressive practices |
| **Catalyst & Event Agent** | Finds the "why now" — earnings surprises, spin-offs, activist pressure, patent approvals, FDA decisions, contract wins, CEO changes — events that actually move the stock |
| **Industry Structure Agent** | Five Forces forward-looking — pricing power, disruption risk, competitive dynamics. Is the industry getting better or worse? Who's winning and losing share? |

### Room 6: Technical (3-4 agents)
Chart patterns, volume profile, market microstructure, order flow, composite technical signals.

| Agent | Role |
|-------|------|
| **Chart & Pattern Agent** | Identifies chart patterns, support/resistance, trendlines across timeframes |
| **Volume & Order Flow Agent** | Volume profile, VWAP, order book depth, large block trades, absorption |
| **Market Microstructure Agent** | Bid/ask dynamics, spread analysis, HFT activity, liquidity conditions |
| **Technical Signal Engine** | Combines indicators (RSI, MACD, moving averages, Bollinger Bands, ATR, ADX) into high-confidence composite signals, reducing false signals from relying on single indicators |

### Room 7: Sentiment (4-5 agents)
News sentiment, social media, analyst reports, insider trading, options flow, dark pool activity, earnings revisions.

| Agent | Role |
|-------|------|
| **News Sentiment Agent** | NLP sentiment analysis on news, earnings calls, press releases |
| **Social Media & Retail Agent** | Reddit, Twitter/X, StockTwits — retail sentiment, meme stock tracking |
| **Insider & Institutional Agent** | Tracks insider buying/selling, institutional 13F filings, activist investors |
| **Options Flow & Dark Pool Agent** | Unusual options activity, dark pool prints, smart money positioning |
| **Analyst & Earnings Revision Agent** | Tracks analyst upgrades/downgrades, price target changes, earnings estimate revisions, consensus vs dispersion — the most predictive sentiment signals on Wall Street |

### Room 8: Strategy (4 agents + 2 interns)
Portfolio construction, asset allocation, tactical overlays, hedging strategies, tax-loss harvesting.

| Agent | Role |
|-------|------|
| **Asset Allocation Agent** | Strategic and tactical allocation across asset classes, risk parity<br>↳ *Intern: Tactical Overlay Intern* — short-term shifts (overweight Europe for 2 weeks, underweight bonds until CPI) while main agent manages strategic allocation |
| **Hedging & Protection Agent** | Options collars, protective puts, tail hedges, VIX hedging |
| **Tax Optimization Agent** | Tax-loss harvesting, wash sale avoidance, lot selection, gain/loss management |
| **Portfolio Construction Agent** | Sector weighting, factor tilts, rebalancing schedules — the high-level architecture<br>↳ *Intern: Position Sizing Intern* — does the math: given constraints and conviction level, how much to actually buy |

### Room 9: Execution (3-4 agents)
Order routing, slippage analysis, execution algorithms, broker selection, timing optimization, pre-flight safety checks. Lean room — executes, doesn't debate.

| Agent | Role |
|-------|------|
| **Order Routing Agent** | Smart order routing across brokers, best execution, fee minimization |
| **Execution Algorithm Agent** | TWAP, VWAP, Iceberg, implementation shortfall — algorithm selection |
| **Timing & Slippage Agent** | Optimal execution timing, liquidity windows, slippage estimation |
| **Pre-Flight Check Agent** | Basic safety gate — violates user rules? Obvious error? Insane slippage? Within position limits? Final sanity check before money moves. Does NOT re-litigate the decision. |

### Room 10: Memory/Knowledge (1-2 agents)
Maintains orchestrator's long-term memory, learns from past decisions, builds knowledge graph.

| Agent | Role |
|-------|------|
| **Knowledge Graph Agent** | Builds and maintains the knowledge graph — entities, relationships, facts |
| **Learning & Reflection Agent** | Reviews past decisions, identifies patterns, improves future recommendations |

### Room 11: Critique/Devil's Advocate (4 agents + 2 interns)
Challenges every recommendation, finds blind spots, argues the opposite case. Also handles inter-room conflict resolution.

| Agent | Role |
|-------|------|
| **Devil's Advocate Agent** | Takes the opposite position on every recommendation, stress-tests logic<br>↳ *Intern: Bear Case Intern* — constructs the most convincing possible bear case with narrative, catalysts, worst-case scenarios, and precedent. Ensures the DA produces structured bull vs bear thinking, not reflexive contrarianism |
| **Blind Spot Detector Agent** | Scans for what's missing — overlooked risks, unconsidered factors<br>↳ *Intern: Historical Analog Intern* — finds historical parallels to the current setup, reports what happened next. Adds a "we've seen this movie before" time dimension that forward-looking agents miss |
| **Assumption Challenger Agent** | Identifies and questions all assumptions underlying any analysis |
| **Conflict Resolution Agent** | When agents across rooms disagree (e.g., Quant says BUY, Risk says SELL), resolves the conflict or presents both sides with analysis to the PM |

### Room 12: Compliance & Tax (2-3 agents)
Wash sale rules, PDT rules, cross-border tax, concentration limits, regulatory changes.

| Agent | Role |
|-------|------|
| **Regulatory Compliance Agent** | Tracks SEC/FINRA rules, pattern day trader rules, reporting requirements |
| **Cross-Border Tax Agent** | Withholding taxes, tax treaties, jurisdiction-specific rules |
| **Trading Restriction Agent** | Wash sale windows, short-sale restrictions, position limits, sector caps |

### Room 13: Alternative Data (4-5 agents)
Satellite imagery, credit card data, supply chain tracking, shipping data, weather/crop analysis, web & app traffic.

| Agent | Role |
|-------|------|
| **Satellite & Geospatial Agent** | Satellite imagery of retail parking lots, factory activity, crop yields |
| **Supply Chain Agent** | Shipping data, container rates, port congestion, supplier disruption |
| **Consumer Spending Agent** | Credit card transaction data, foot traffic, consumer behavior patterns |
| **Weather & Commodity Agent** | Weather forecasts, crop conditions, natural disaster impacts, commodity supply |
| **Web & App Traffic Agent** | App store rankings, website traffic, user engagement metrics, download trends — catches product-level shifts before they appear in earnings |

### Room 14: Crypto/Digital Assets (2-4 agents)
On-chain analytics, DeFi yields, tokenomics, protocol risk, custody options.

| Agent | Role |
|-------|------|
| **On-Chain Analytics Agent** | Wallet flows, exchange reserves, miner activity, network health metrics |
| **DeFi & Yield Agent** | DeFi protocol yields, liquidity pool analysis, impermanent loss, smart contract risk |
| **Tokenomics Agent** | Token supply schedules, vesting unlocks, inflation rates, governance analysis |
| **Protocol Risk Agent** | Smart contract audits, bridge security, custody risk, regulatory exposure |

### Room 15: Control (1-2 agents)
Meta-agents that manage other agents — quality control, agent health, output verification.

| Agent | Role |
|-------|------|
| **Quality Control Agent** | Reviews all agent outputs for accuracy, completeness, source quality |
| **Agent Health Monitor** | Tracks agent performance, response times, flags degraded agents |

### Room 16: Tasks/Automation (1-2 agents)
Idle-mode research, daily briefings, periodic insight surfacing. **Opt-in only** — the PM does NOT route to this room by default. The user must explicitly enable it. Once on, agents work autonomously even when the user isn't actively asking.

| Agent | Role |
|-------|------|
| **Daily Briefing Agent** | Generates daily market/portfolio briefings, flags urgent items |
| **Opportunity Scout Agent** | Continuously scans for opportunities, surfaces insights proactively |

---

## Room Lead Agents

Every room has a **Lead Agent** (except rooms with 1-2 agents: Memory, Control, Tasks). The lead acts as a mini-orchestrator for its room.

**What a Room Lead does:**

| Responsibility | Details |
|---------------|---------|
| **Triage** | Receives the PM's request, decides which sub-agents in the room to activate |
| **Synthesize** | Combines all sub-agent outputs into one clean room-level response for the PM |
| **Quality gate** | Catches low-quality or off-track output before it reaches the PM |
| **Flag disagreements** | When sub-agents disagree, surfaces both views with explanation |

**The lead doesn't do the research itself** — it's a domain expert that knows its agents intimately and routes work efficiently.

**Rooms that need a lead (13):** Research, Risk, Macro, Quant, Fundamental, Technical, Sentiment, Strategy, Execution, Critique, Compliance & Tax, Alternative Data, Crypto

**Rooms without a lead (3, agents report directly to PM):** Memory/Knowledge, Control, Tasks/Automation

---

## Agent Calling & Lifecycle

### Full Flow: PM → Leads → Sub-agents

```
User
  ↕
Portfolio Manager     ← talks only to Room Leads (+ small-room agents)
  ↕
Lead Research  Lead Risk  Lead Quant  ...  (13 room leads)
  ↕              ↕            ↕
Web Research  VaR Agent   Factor Agent  ...  (sub-agents)
SEC/Reg       Correlation Regime Agent
Academic      Liquidity    ML Agent
...           ...          ...
```

1. **PM evaluates request** → consults routing section of its system prompt, decides which rooms are relevant
2. **PM sends to Room Leads** → each lead receives the request + relevant context
3. **Room Lead triages** → decides which sub-agents in its room to activate, wakes them up
4. **Sub-agents execute** → each receives its system prompt + task context, does deep research in parallel
5. **Room Lead synthesizes** → collects sub-agent outputs, produces one clean room-level response, sends to PM
6. **Time awareness** → tight deadline → leads activate lightweight agents/interns only; deep dive → full agents
7. **PM final synthesis** → collects all room-level outputs and produces unified report for user

---

## Memory System

Each agent has persistent memory across calls via:
- **Vector database** — semantic search over past conversations, research, decisions
- **Knowledge graph** — structured relationships between entities (companies, sectors, macro factors, trades, decisions)

The PM uses both to learn from every interaction and improve over time.

---

## User Interaction

- **User ONLY talks to the Portfolio Manager.** No direct subagent chat.
- **User CAN inspect agents** — if curious about an agent's reasoning, the user can "walk over" and click the agent for information (frontend detail later).
- **User can edit agent system prompts** — full customization of any agent's personality and behavior.
- **User sets rules/mandates** — persistent constraints the PM always follows.

---

*This document defines the agent taxonomy for Labourious. Agent counts, names, and specific roles will be refined during implementation.*
