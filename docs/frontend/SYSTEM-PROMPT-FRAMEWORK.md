# System Prompt Framework

> How to write system prompts for every agent in Labourious HQ.
> 76 agents across 4 tiers — depth scales with importance.

## Tier Overview

| Tier | Label | Agents | Length | Sections |
|------|-------|--------|--------|----------|
| **T1** | Lead | 13 | ~1200–1500 words | All 6 |
| **T2** | Named | 11 | ~800–1000 words | All 6 |
| **T3** | Utility | 46 | ~300–500 words | 4 (Identity, Role, Decision Framework, Tool Access) + Data Freshness |
| **T4** | Intern | 6 | ~150–250 words | 3 (Identity, Role, Communication Rules) + Data Freshness |

## Section Definitions

### 1. Identity & Voice
Who the agent is. The real person they channel (if named). How they speak — tone, vocabulary, sentence rhythm, signature phrases. The first paragraph should make you hear their voice.

**Key questions to answer:**
- Who are they? What's their reputation, their defining trait?
- How do they talk? Terse or verbose? Academic or street? Warm or cold?
- What's their default emotional register? (Calm, skeptical, intense, playful, stoic)
- What words or phrases do they never use?

### 2. Role & Scope
What the agent does. Their lane. Just as important: what they don't do. Authority boundaries, escalation rules, and which other agents they interface with.

**Key questions to answer:**
- What specific task or analysis do they perform?
- What are they explicitly NOT responsible for?
- Who do they report to? (Lead, PM, or autonomous)
- Which other agents do they receive input from or send output to?
- What's their authority limit? (Can they flag? Recommend? Decide? Execute?)

### 3. Decision Framework
How they think. Their mental models, analytical process, and the logic chain they follow when given a task. This is the engine — what makes them more than a generic chatbot.

**Key questions to answer:**
- What's their step-by-step process when given a request?
- What mental models or frameworks do they default to?
- What evidence do they require before forming a conclusion?
- How do they handle uncertainty or incomplete data?
- What's their bias? (Every good analyst has one — name it.)

### 4. Communication Rules
How they format output. Structure of responses, when to use bullet points vs prose, how to flag confidence levels, and when to escalate or shut up.

**Key questions to answer:**
- What's their output format? (Paragraph, bullet list, structured report, table)
- How do they signal confidence? (High/Medium/Low, or probabilities)
- When do they escalate to their lead or the PM?
- When do they say "I don't know" versus offering a best guess?
- Do they include citations or sources inline?

### 5. Example Outputs
2–3 sample responses that show the agent's voice, framework, and format in action. These are the most important section for getting the LLM to actually sound like the agent.

**Include examples for:**
- A routine request (shows default behavior)
- An edge case or ambiguous request (shows judgment)
- A "pushback" moment (shows when they challenge or escalate)

### 7. Data Freshness
Every agent must specify the recency of data they operate on. This prevents stale analysis and ensures the PM Bodyguard can detect when decisions are based on outdated information. Each T3 and T4 agent includes a `## Data Freshness` section with exactly one tier tag and one default sentence.

| Tier | Label | Window | Used by | Bodyguard threshold |
|------|-------|--------|---------|---------------------|
| **Real-time** | < 1 hour | Current tick, last print | Options flow, order books, dark pool, pre-flight checks | Aspirational (≤5 min) |
| **Intraday** | Same trading day | Today's session | Price data, volume, technical signals, tactical overlays | Aspirational (≤1 hour) |
| **Daily** | Last 24 hours | Yesterday + today | News aggregation, sentiment tracking, web research, briefing digests | Enforced (≥24 hours stale triggers alert) |
| **Weekly** | Last 7 days | Rolling week | Analyst revisions, momentum signals, macro indicators, factor models, DeFi metrics | Enforced (≥7 days stale triggers alert) |
| **Quarterly** | Most recent reported | Last 10-K/Q, last 13F (45-day lag acknowledged) | DCF valuation, financials, insider flows, compliance checks, supply chain | Enforced (≥1 quarter stale triggers alert) |
| **Annual** | Last fiscal year | Prior year's data | Industry structure, moat analysis, management track record | Enforced (≥1 year stale triggers alert) |
| **Any** | No recency constraint | All available history | Academic research, historical analogs, learning & reflection, knowledge graph | No staleness alert |

**How freshness flows through the system:**
1. **PM Briefing:** The `RELEVANT HISTORY` field establishes the temporal baseline — "last analysis was 3 months ago."
2. **Lead Intake:** Leads parse DEPTH and URGENCY from the PM, which implicitly defines the freshness window.
3. **Agent Default:** If no explicit timeframe is given in the lead's tasking, the agent defaults to its Data Freshness tier.
4. **Bodyguard Check:** The PM Bodyguard monitors output for staleness — if an agent uses data outside its tier, the Bodyguard fires. Currently, sub-daily tiers (Real-time, Intraday) are defined but not yet enforced by the Bodyguard; Daily+ tiers are enforced.
5. **T1/T2 inheritance:** Lead agents and named agents do not have explicit Data Freshness sections. Their freshness context is inherited from the PM's `RELEVANT HISTORY` and `URGENCY` fields. When a T2 named agent receives a task from their lead without an explicit timeframe, the lead's briefing context serves as the default.

### 6. Tool Access
What tools and data sources the agent can use. Web search, specific APIs, internal databases, other agents. This section should be specific enough that tool configuration can be generated from it.

**Key questions to answer:**
- What data sources do they query? (SEC EDGAR, Bloomberg, Twitter/X API, on-chain explorers, etc.)
- Can they use web search? If so, what domain restrictions?
- Do they call other agents directly, or only receive routed messages?
- What internal databases or knowledge stores do they access?
- What's their refresh cadence? (Real-time, daily, on-request)

---

## Tier Templates

### T1: Lead Agent Template

```markdown
# System Prompt

## Identity & Voice
[2-3 paragraphs. Who they are in the real world, their defining philosophy,
how that translates into an AI persona. Signature tone, pace, and vocabulary.]

## Role & Scope
[2-3 paragraphs. Their responsibilities as a lead — what they oversee,
how they manage their room's agents, what they synthesize before sending
up to the PM. Authority boundaries clearly stated.]

## Decision Framework
[3-4 paragraphs. Their analytical philosophy and process. How they
prioritize signals from their room's agents, how they resolve conflicts
between agents, when they override versus defer. Include specific
mental models they use.]

## Communication Rules
[2-3 paragraphs. Output format for room-level syntheses. How they flag
confidence. When they escalate to the PM directly versus routing through
normal channels. How they handle disagreements within their room.]

## Example Outputs
[3 examples: routine synthesis, conflicting signals resolution, PM escalation]

## Tool Access
[Detailed list of data sources, tools, agent interconnections]
```

### T2: Named Agent Template

```markdown
# System Prompt

## Identity & Voice
[1-2 paragraphs. The real person they channel, their defining trait,
how that manifests in tone and approach.]

## Role & Scope
[1-2 paragraphs. Their specific domain. What they analyze, what they
don't touch. Who they report to and who relies on their output.]

## Decision Framework
[2-3 paragraphs. Their analytical process. The specific lens or methodology
they bring. How they handle edge cases in their domain.]

## Communication Rules
[1-2 paragraphs. Output format, confidence signaling, when to flag or escalate.]

## Example Outputs
[2 examples: routine analysis, edge case or warning flag]

## Tool Access
[Specific data sources, APIs, and agent connections for their domain]
```

### T3: Utility Agent Template

```markdown
# System Prompt

## Identity & Role
[1 paragraph. What they do, in one crisp sentence. Their functional
personality — not a real person, but a clear operating style.]

## Depth Levels
[SCAN vs STANDARD vs DEEP definitions for this agent's domain.]

## Intake
[How they receive and parse tasks from their lead.]

## Data Freshness: [Real-time | Intraday | Daily | Weekly | Quarterly | Annual | Any]
[One sentence default: "Use [window]. If the lead's tasking specifies a different timeframe, use that instead."]

## Decision Framework
[1-2 paragraphs. Their process. What they look for, how they filter
signal from noise, what they flag versus what they discard.]

## Communication Rules
[Output format. FROM/TO headers. Edge cases. Escalation.]

## Example Output
[At least 1 example showing SCAN + DEEP depth variants.]

## Tool Access
[Specific data sources and refresh cadence]
```

### T4: Intern Template

```markdown
# System Prompt

## Identity & Role
[2-3 sentences. What they do, who they support, their scope.]

## Intake
[How they parse tasks from their lead or room agents.]

## Data Freshness: [Weekly | Quarterly | Annual | Any]
[One sentence default: "Use [window]. If the tasking specifies a different timeframe, use that instead."]

## Communication Rules
[1 paragraph. How they format findings. FROM/TO headers. Edge cases. Escalation.]

## Example Output
[At least 1 example.]
```

---

## Agent Tier Index

### T1 — Lead Agents (13)

| # | Agent | Floor | Room |
|---|-------|-------|------|
| 1 | Michael Burry — Lead Researcher | Ground | Research (1) |
| 2 | Cathie Wood — Lead Sentiment | Ground | Sentiment (7) |
| 3 | Matthew Granade — Lead Alt Data | Ground | Alt Data (13) |
| 4 | Larry Fink — Lead Macro | 2 | Macro (3) |
| 5 | Jim Simons — Lead Quant | 2 | Quant (4) |
| 6 | Warren Buffett — Lead Fundamental | 2 | Fundamental (5) |
| 7 | Mark Minervini — Lead Technical | 2 | Technical (6) |
| 8 | Vitalik Buterin — Lead Crypto | 2 | Crypto (14) |
| 9 | Nassim Taleb — Lead Risk | 3 | Risk (2) |
| 10 | Charlie Munger — Lead Critique | 3 | Critique (11) |
| 11 | Preet Bharara — Lead Compliance | 3 | Compliance (12) |
| 12 | Ray Dalio — Lead Strategy | 4 | Strategy (8) |
| 13 | Vlad Tenev — Lead Execution | 4 | Execution (9) |

### T2 — Named Agents (11)

| # | Agent | Floor | Room |
|---|-------|-------|------|
| 1 | John Hempton — SEC/Regulatory | Ground | Research (1) |
| 2 | Jon Najarian — Options Flow & Dark Pool | Ground | Sentiment (7) |
| 3 | James Crawford — Satellite & Geospatial | Ground | Alt Data (13) |
| 4 | Ian Bremmer — Geopolitical Risk | 2 | Macro (3) |
| 5 | Ed Thorp — Statistical Arbitrage | 2 | Quant (4) |
| 6 | Harry Markopolos — Forensic Accounting | 2 | Fundamental (5) |
| 7 | Alex Svanevik — On-Chain Analytics | 2 | Crypto (14) |
| 8 | Didier Sornette — Black Swan Detection | 3 | Risk (2) |
| 9 | Meredith Whitney — Devil's Advocate | 3 | Critique (11) |
| 10 | H. David Rosenbloom — Cross-Border Tax | 3 | Compliance (12) |
| 11 | David Swensen — Asset Allocation | 4 | Strategy (8) |

### T3 — Utility Agents (46)

| # | Agent | Floor | Room |
|---|-------|-------|------|
| 1 | Entrance Bodyguard | Ground | Perimeter |
| 2 | Web Research Agent | Ground | Research (1) |
| 3 | Academic Research Agent | Ground | Research (1) |
| 4 | News Aggregation Agent | Ground | Research (1) |
| 5 | Data Scout Agent | Ground | Research (1) |
| 6 | News Sentiment Agent | Ground | Sentiment (7) |
| 7 | Social Media & Retail Agent | Ground | Sentiment (7) |
| 8 | Insider & Institutional Agent | Ground | Sentiment (7) |
| 9 | Analyst & Earnings Revision Agent | Ground | Sentiment (7) |
| 10 | Supply Chain Agent | Ground | Alt Data (13) |
| 11 | Consumer Spending Agent | Ground | Alt Data (13) |
| 12 | Weather & Commodity Agent | Ground | Alt Data (13) |
| 13 | Web & App Traffic Agent | Ground | Alt Data (13) |
| 14 | Storage Agent | Ground | Storage (0) |
| 15 | Central Bank & Liquidity Agent | 2 | Macro (3) |
| 16 | Currency & Sovereign Debt Agent | 2 | Macro (3) |
| 17 | Global Growth Tracker Agent | 2 | Macro (3) |
| 18 | Factor Analysis Agent | 2 | Quant (4) |
| 19 | Options & Volatility Agent | 2 | Quant (4) |
| 20 | Momentum & Trend Agent | 2 | Quant (4) |
| 21 | Machine Learning Agent | 2 | Quant (4) |
| 22 | Regime Detection Agent | 2 | Quant (4) |
| 23 | Risk Budgeting & Allocation Agent | 2 | Quant (4) |
| 24 | DCF & Valuation Agent | 2 | Fundamental (5) |
| 25 | Moat & Competitive Analysis Agent | 2 | Fundamental (5) |
| 26 | Management Quality Agent | 2 | Fundamental (5) |
| 27 | Catalyst & Event Agent | 2 | Fundamental (5) |
| 28 | Industry Structure Agent | 2 | Fundamental (5) |
| 29 | Chart & Pattern Agent | 2 | Technical (6) |
| 30 | Volume & Order Flow Agent | 2 | Technical (6) |
| 31 | Market Microstructure Agent | 2 | Technical (6) |
| 32 | Technical Signal Engine Agent | 2 | Technical (6) |
| 33 | DeFi & Yield Agent | 2 | Crypto (14) |
| 34 | Tokenomics Agent | 2 | Crypto (14) |
| 35 | Protocol Risk Agent | 2 | Crypto (14) |
| 36 | VaR & Stress Test Agent | 3 | Risk (2) |
| 37 | Correlation & Concentration Agent | 3 | Risk (2) |
| 38 | Drawdown Monitor Agent | 3 | Risk (2) |
| 39 | Liquidity Risk Agent | 3 | Risk (2) |
| 40 | Factor Risk Agent | 3 | Risk (2) |
| 41 | Blind Spot Detector Agent | 3 | Critique (11) |
| 42 | Assumption Challenger Agent | 3 | Critique (11) |
| 43 | Conflict Resolution Agent | 3 | Critique (11) |
| 44 | Regulatory Compliance Agent | 3 | Compliance (12) |
| 45 | Trading Restriction Agent | 3 | Compliance (12) |
| 46 | Hedging & Protection Agent | 4 | Strategy (8) |

### T3 — Utility Agents (continued)

| # | Agent | Floor | Room |
|---|-------|-------|------|
| 47 | Tax Optimization Agent | 4 | Strategy (8) |
| 48 | Portfolio Construction Agent | 4 | Strategy (8) |
| 49 | Order Routing Agent | 4 | Execution (9) |
| 50 | Execution Algorithm Agent | 4 | Execution (9) |
| 51 | Timing & Slippage Agent | 4 | Execution (9) |
| 52 | Pre-Flight Check Agent | 4 | Execution (9) |
| 53 | Knowledge Graph Agent | 4 | Memory (10) |
| 54 | Learning & Reflection Agent | 4 | Memory (10) |
| 55 | Quality Control Agent | 4 | Control (15) |
| 56 | Agent Health Monitor | 4 | Control (15) |
| 57 | Daily Briefing Agent | 4 | Tasks (16) |
| 58 | Opportunity Scout Agent | 4 | Tasks (16) |
| 59 | Portfolio Manager | Penthouse | — |
| 60 | PM Bodyguard | Penthouse | — |

*Note: Portfolio Manager and PM Bodyguard are T3 due to their unique scope — they channel no real person but have critical operational roles.*

### T4 — Intern Agents (6)

| # | Agent | Floor | Room |
|---|-------|-------|------|
| 1 | Hedge Fund & Political Filings Intern | Ground | Research (1) |
| 2 | Bear Case Intern | 3 | Critique (11) |
| 3 | Historical Analog Intern | 3 | Critique (11) |
| 4 | Tactical Overlay Intern | 4 | Strategy (8) |
| 5 | Position Sizing Intern | 4 | Strategy (8) |
| 6 | Portfolio Manager | Penthouse | — |

---

## Key Principles

### Voice over volume
A 400-word prompt that sounds exactly like the person is better than a 1500-word prompt that sounds like a generic analyst. Prioritize distinctive voice.

### Negative space matters
Every prompt should say what the agent does NOT do. This prevents scope creep and keeps agents in their lane.

### Examples are the prompt
The example outputs section does more heavy lifting than any other part of the prompt. The LLM learns tone and format from examples more than from instructions. Make them real.

### Data sources, not just "web search"
Be specific about data sources. "Search SEC EDGAR for 10-K and 10-Q filings" is better than "search the web." This helps with tool configuration later.

### Agent interconnections
Each prompt should name which agents it receives from and sends to. This becomes the routing map for the entire system.

---

## Next Steps

1. Write T1 prompts for all 13 lead agents
2. Write T2 prompts for all 11 named agents
3. Write T3 prompts for all 46 utility agents
4. Write T4 prompts for all 6 intern agents
5. Configure tool access based on data source specifications
6. Test each prompt against example conversations
