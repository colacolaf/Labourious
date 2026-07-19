# AGENTS.md — The Complete Agent System

## The Portfolio Manager (Main Orchestrator)

**Personality:** Calm, collected, deliberate. Never rushed. Always thorough.

The Portfolio Manager is the ONLY agent the user directly chats with. It has a comprehensive system prompt (2-5 pages) with dedicated sections on every subagent and exactly when to call each one. When the user makes a request, the PM automatically decides which agents to wake up — no user confirmation needed.

**How the PM works:**
1. User sends a request ("Analyze my tech holdings," "Should I rotate into bonds?", "Find undervalued mid-cap healthcare with strong moats")
2. PM evaluates which rooms/agents are needed based on its routing prompt
3. PM calls those agents alive — each receives its own multi-page system prompt and the relevant context
4. Agents do deep research (1-10 minutes depending on complexity), cite fresh sources
5. PM synthesizes ALL outputs into:
   - A detailed report with comprehensive analysis
   - A concise summary
   - Clear options for what to do next
6. If the user is time-sensitive, PM uses only lightweight agents and interns

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
| **SEC/Regulatory Research Agent** | Reads filings (10-K, 10-Q, 8-K), extracts key data points |
| **Academic Research Agent** | Searches academic databases, finds peer-reviewed research |
| **News Aggregation Agent** | Aggregates and filters news from multiple sources, removes noise |
| **Data Scout Agent** | Discovers new data sources, APIs, datasets the other agents might need |

### Room 2: Risk (2-4 agents)
Portfolio stress testing, VaR, drawdown analysis, correlation matrices, black swan detection.

| Agent | Role |
|-------|------|
| **VaR & Stress Test Agent** | Calculates Value at Risk, runs Monte Carlo simulations, stress scenarios |
| **Correlation & Concentration Agent** | Analyzes portfolio correlation matrix, finds hidden concentration risks |
| **Black Swan Detection Agent** | Scans for tail-risk events, fat-tail distributions, systemic vulnerabilities |
| **Drawdown Monitor Agent** | Tracks drawdown, recovery time, sets alert thresholds |

### Room 3: Macro (2-4 agents)
Global macroeconomics — central bank policy, GDP, inflation, geopolitics, currency flows, sovereign debt.

| Agent | Role |
|-------|------|
| **Central Bank Analyst** | Tracks Fed, ECB, BoJ, PBOC — policy shifts, rate expectations, minutes |
| **Geopolitical Risk Agent** | Monitors global conflicts, trade wars, sanctions, political instability |
| **Currency & Sovereign Debt Agent** | Currency flows, sovereign credit risk, yield spreads, capital flight |
| **Global Growth Tracker** | GDP trajectories, PMI data, employment trends across major economies |

### Room 4: Quant (3-5 agents)
Quantitative modeling, factor analysis, statistical arbitrage, momentum, mean reversion, options pricing.

| Agent | Role |
|-------|------|
| **Factor Analysis Agent** | Runs factor models (value, momentum, quality, size, vol), decomposes returns |
| **Statistical Arbitrage Agent** | Pair trading, cointegration, mean reversion strategies |
| **Options & Volatility Agent** | Options pricing models, implied vol surfaces, volatility arbitrage |
| **Momentum & Trend Agent** | Time-series momentum, cross-sectional momentum, trend following signals |
| **Machine Learning Agent** | ML models for pattern recognition, anomaly detection, predictive signals |

### Room 5: Fundamental (3-4 agents)
Company deep-dives, DCF models, competitive moat analysis, management quality, forensic accounting.

| Agent | Role |
|-------|------|
| **DCF & Valuation Agent** | Builds discounted cash flow models, intrinsic value estimates |
| **Moat & Competitive Analysis Agent** | Analyzes competitive advantages, barriers to entry, industry positioning |
| **Management Quality Agent** | Evaluates executive track records, capital allocation, insider behavior |
| **Forensic Accounting Agent** | Detects earnings manipulation, accounting red flags, aggressive practices |

### Room 6: Technical (2-4 agents)
Chart patterns, volume profile, market microstructure, order flow, liquidity analysis.

| Agent | Role |
|-------|------|
| **Chart & Pattern Agent** | Identifies chart patterns, support/resistance, trendlines across timeframes |
| **Volume & Order Flow Agent** | Volume profile, VWAP, order book depth, large block trades, absorption |
| **Market Microstructure Agent** | Bid/ask dynamics, spread analysis, HFT activity, liquidity conditions |
| **Indicator Systems Agent** | RSI, MACD, moving averages, Bollinger Bands, custom indicator suites |

### Room 7: Sentiment (2-4 agents)
News sentiment, social media, analyst reports, insider trading, options flow, dark pool activity.

| Agent | Role |
|-------|------|
| **News Sentiment Agent** | NLP sentiment analysis on news, earnings calls, press releases |
| **Social Media & Retail Agent** | Reddit, Twitter/X, StockTwits — retail sentiment, meme stock tracking |
| **Insider & Institutional Agent** | Tracks insider buying/selling, institutional 13F filings, activist investors |
| **Options Flow & Dark Pool Agent** | Unusual options activity, dark pool prints, smart money positioning |

### Room 8: Strategy (2-4 agents)
Portfolio construction, asset allocation, tactical overlays, hedging strategies, tax-loss harvesting.

| Agent | Role |
|-------|------|
| **Asset Allocation Agent** | Strategic and tactical allocation across asset classes, risk parity |
| **Hedging & Protection Agent** | Options collars, protective puts, tail hedges, VIX hedging |
| **Tax Optimization Agent** | Tax-loss harvesting, wash sale avoidance, lot selection, gain/loss management |
| **Portfolio Construction Agent** | Position sizing, sector weighting, factor tilts, rebalancing schedules |

### Room 9: Execution (2-4 agents)
Order routing, slippage analysis, execution algorithms, broker selection, timing optimization. Also houses the conflict resolution agent.

| Agent | Role |
|-------|------|
| **Order Routing Agent** | Smart order routing across brokers, best execution, fee minimization |
| **Execution Algorithm Agent** | TWAP, VWAP, Iceberg, implementation shortfall — algorithm selection |
| **Timing & Slippage Agent** | Optimal execution timing, liquidity windows, slippage estimation |
| **Conflict Resolution Agent** | When agents disagree, this agent resolves — or presents both sides to PM |

### Room 10: Memory/Knowledge (1-2 agents)
Maintains orchestrator's long-term memory, learns from past decisions, builds knowledge graph.

| Agent | Role |
|-------|------|
| **Knowledge Graph Agent** | Builds and maintains the knowledge graph — entities, relationships, facts |
| **Learning & Reflection Agent** | Reviews past decisions, identifies patterns, improves future recommendations |

### Room 11: Critique/Devil's Advocate (2-3 agents)
Challenges every recommendation, finds blind spots, argues the opposite case.

| Agent | Role |
|-------|------|
| **Devil's Advocate Agent** | Takes the opposite position on every recommendation, stress-tests logic |
| **Blind Spot Detector Agent** | Scans for what's missing — overlooked risks, unconsidered factors |
| **Assumption Challenger Agent** | Identifies and questions all assumptions underlying any analysis |

### Room 12: Compliance & Tax (2-3 agents)
Wash sale rules, PDT rules, cross-border tax, concentration limits, regulatory changes.

| Agent | Role |
|-------|------|
| **Regulatory Compliance Agent** | Tracks SEC/FINRA rules, pattern day trader rules, reporting requirements |
| **Cross-Border Tax Agent** | Withholding taxes, tax treaties, jurisdiction-specific rules |
| **Trading Restriction Agent** | Wash sale windows, short-sale restrictions, position limits, sector caps |

### Room 13: Alternative Data (2-4 agents)
Satellite imagery, credit card data, supply chain tracking, shipping data, weather/crop analysis.

| Agent | Role |
|-------|------|
| **Satellite & Geospatial Agent** | Satellite imagery of retail parking lots, factory activity, crop yields |
| **Supply Chain Agent** | Shipping data, container rates, port congestion, supplier disruption |
| **Consumer Spending Agent** | Credit card transaction data, foot traffic, consumer behavior patterns |
| **Weather & Commodity Agent** | Weather forecasts, crop conditions, natural disaster impacts, commodity supply |

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
Idle-mode research, daily briefings, periodic insight surfacing — works even when user isn't actively asking.

| Agent | Role |
|-------|------|
| **Daily Briefing Agent** | Generates daily market/portfolio briefings, flags urgent items |
| **Opportunity Scout Agent** | Continuously scans for opportunities, surfaces insights proactively |

---

## Agent Calling & Lifecycle

1. **PM evaluates request** → consults routing section of its system prompt
2. **PM selects agents** → decides which rooms/agents are relevant
3. **Agents wake up** → each receives its system prompt + task context
4. **Parallel + sequential execution** → PM can run agents in parallel (independent analysis) or sequentially (one agent's output feeds another)
5. **Intern escalation** → if an agent is overwhelmed, PM spawns interns to assist
6. **Time awareness** → tight deadline → lightweight agents only; deep dive → full agents
7. **Synthesis** → PM collects all outputs and produces unified report

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
