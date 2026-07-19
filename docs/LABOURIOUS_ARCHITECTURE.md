# Labourious Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       USER                                       │
│            (Chats with the Portfolio Manager)                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                    Electron Desktop App
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                 PORTFOLIO MANAGER                                 │
│              (Main Orchestrator Agent)                            │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ System Prompt (2-5 pages)                                │    │
│  │  ├─ Agent routing sections (when to call each agent)    │    │
│  │  ├─ Rules & mandates (user-defined constraints)          │    │
│  │  ├─ Personality definition (calm, collected, thorough)  │    │
│  │  ├─ Synthesis & output format instructions              │    │
│  │  └─ Time-sensitivity handling                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  1. User sends request                                           │
│  2. PM evaluates → selects rooms/agents                          │
│  3. PM calls agents alive (parallel + sequential)                │
│  4. PM collects outputs                                          │
│  5. PM synthesizes → Detailed Report + Summary + Options         │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬──────────────┐
         ▼               ▼               ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Room 1  │    │ Room 2  │    │ Room 3  │    │ Room N  │
    │Research │    │  Risk   │    │  Macro  │    │  ...    │
    │ (3-5    │    │ (2-4    │    │ (2-4    │    │         │
    │ agents) │    │ agents) │    │ agents) │    │         │
    └─────────┘    └─────────┘    └─────────┘    └─────────┘
         │               │               │              │
         └───────────────┴───────────────┴──────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Vector  │    │Knowledge│    │  User   │
    │   DB    │    │  Graph  │    │  Rules  │
    │(memory) │    │(memory) │    │(mandates│
    └─────────┘    └─────────┘    └─────────┘
```

---

## Core Components

### 1. Portfolio Manager (Main Orchestrator)

The Portfolio Manager is the central agent — the only one the user interacts with directly. It is a single sophisticated LLM agent with a comprehensive system prompt.

**System Prompt Structure:**
- **Personality section:** Defines tone — calm, collected, thorough, never rushed
- **Agent routing section:** For each of the 30-40 subagents, defines:
  - What the agent specializes in
  - When to call it (trigger conditions)
  - What kind of output to expect
  - Whether it runs independently or needs input from other agents
  - Typical research time (1-10 minutes)
- **Rules & mandates section:** User-defined persistent constraints
- **Synthesis section:** How to combine agent outputs into the unified report
- **Time-sensitivity section:** How to handle urgent vs deep-dive requests
- **Output format:** Detailed report → Summary → Options for next steps

**Calling Logic:**
- PM evaluates user request against routing sections
- Selects relevant agents (can call 3-15 agents for a complex request)
- Runs independent agents in parallel, dependent ones sequentially
- Collects all outputs, resolves conflicts via Execution Room's conflict agent
- Synthesizes everything into one response

### 2. Subagent System (30-40 Agents across 16 Rooms)

Each subagent is a fully independent LLM agent with its own multi-page system prompt.

**Agent Architecture:**
```
Agent Lifecycle:
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  IDLE    │───▶│  CALLED  │───▶│RESEARCHING│───▶│ RETURN   │
│          │    │  ALIVE   │    │(1-10 min)│    │ RESULTS  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                      │                               │
                      ▼                               ▼
               Intern agents                   Memory saved
               (if overwhelmed)             (vector DB + KG)
```

**System Prompt Contents (per agent):**
- Personality/attitude definition
- Domain expertise boundaries
- Tool access (web search, APIs, file I/O, DB queries, code execution)
- Citation requirements (must use fresh/recent data)
- Output formatting rules
- "Unknown" handling protocol
- Fallback behavior (what to do if it can't complete research)

**Agent Types:**
- **Primary agents:** Full multi-page system prompts, deep research, 1-10 minutes
- **Intern agents:** Lighter-weight, used when primary is overwhelmed or for time-sensitive requests

**Memory:** Each agent has persistent state across calls via:
- Vector DB for semantic search over past research
- Knowledge graph for structured relationships between entities

### 3. Memory System

**Vector Database:**
- Stores conversation history, past research outputs, decisions
- Enables semantic search: "What did we conclude about TSLA last quarter?"
- PM and agents can query for context

**Knowledge Graph:**
- Stores entities and relationships: companies, sectors, macro factors, trades, decisions
- Tracks what worked/failed over time
- Enables pattern recognition across decisions

### 4. Rules & Mandates Engine

User defines persistent constraints:
- "Never invest in fossil fuels"
- "Keep 20% cash minimum"
- "No single position over 5%"
- "Only trade during NYSE hours"
- "Prioritize dividend yield > 2%"

These are embedded in the PM's system prompt and checked against every recommendation.

### 5. Conflict Resolution

When agents disagree (Quant says BUY, Critique says SELL), the Execution Room's dedicated conflict resolution agent:
- Analyzes both arguments
- Checks against user rules/mandates
- Makes a final recommendation OR presents both sides
- The resolution is logged in the memory system

---

## Room Architecture Details

### Research Room
- **Primary function:** Data gathering, web search, filing analysis
- **Typical call pattern:** Called FIRST in most requests — feeds raw data to other rooms
- **Tools:** Web search, SEC Edgar, academic databases, news APIs

### Risk Room
- **Primary function:** Portfolio risk analysis
- **Typical call pattern:** Called after Research and Quant/Fundamental rooms
- **Tools:** Statistical packages, Monte Carlo sims

### Macro Room
- **Primary function:** Global economic context
- **Typical call pattern:** Called for any portfolio-level or sector-level request
- **Tools:** FRED API, central bank data, economic calendars

### Quant Room
- **Primary function:** Statistical modeling, factor analysis
- **Typical call pattern:** Called for portfolio analysis, strategy evaluation
- **Tools:** Python/R for stats, ML libraries

### Fundamental Room
- **Primary function:** Company deep-dives, valuation
- **Typical call pattern:** Called for individual stock/asset analysis
- **Tools:** SEC filings, financial data APIs

### Technical Room
- **Primary function:** Price/volume/order flow analysis
- **Typical call pattern:** Called for entry/exit timing, trade execution context
- **Tools:** Market data APIs, charting libraries

### Sentiment Room
- **Primary function:** Market sentiment aggregation
- **Typical call pattern:** Called alongside Technical or Fundamental rooms
- **Tools:** NLP, social media APIs, news feeds

### Strategy Room
- **Primary function:** Portfolio construction recommendations
- **Typical call pattern:** Called for allocation decisions, rebalancing
- **Tools:** Optimization libraries, tax software APIs

### Execution Room
- **Primary function:** Trade execution + conflict resolution
- **Typical call pattern:** Called when trades need to be placed or agents disagree
- **Tools:** Broker APIs, order management systems

### Memory/Knowledge Room
- **Primary function:** Maintains persistent knowledge
- **Typical call pattern:** Runs in background, queried by PM as needed
- **Tools:** Vector DB, graph DB

### Critique Room
- **Primary function:** Devil's advocate analysis
- **Typical call pattern:** Called for every major recommendation before final output
- **Tools:** Same as the rooms it critiques

### Compliance & Tax Room
- **Primary function:** Regulatory and tax constraint checking
- **Typical call pattern:** Called for every trade recommendation
- **Tools:** Tax rule databases, regulatory APIs

### Alternative Data Room
- **Primary function:** Non-traditional data analysis
- **Typical call pattern:** Called for deep-dive or edge-seeking requests
- **Tools:** Satellite APIs, shipping data, credit card aggregators

### Crypto/Digital Assets Room
- **Primary function:** Crypto-specific analysis
- **Typical call pattern:** Called when crypto assets are in scope
- **Tools:** On-chain analytics APIs, DeFi protocol APIs

### Control Room
- **Primary function:** Quality control, agent health
- **Typical call pattern:** Runs continuously, monitors agent outputs
- **Tools:** Internal monitoring

### Tasks/Automation Room
- **Primary function:** Idle-mode research
- **Typical call pattern:** Runs on schedule (daily, weekly), even without user prompt
- **Tools:** Same as Research Room

---

## Data Flow: Example Request

**User:** "Should I rotate my tech holdings given the macro environment?"

```
1. PM evaluates request
   → Relevant rooms: Macro, Fundamental, Risk, Critique, Strategy
   
2. PM calls agents in parallel (first wave):
   ┌─ Macro Room: Central Bank Analyst, Geopolitical Risk Agent
   └─ Research Room: News Aggregation Agent, SEC Research Agent
   
3. PM calls agents in parallel (second wave, uses first wave outputs):
   ┌─ Fundamental Room: DCF & Valuation Agent, Moat Analysis Agent
   └─ Technical Room: Chart & Pattern Agent
   
4. PM calls agents (third wave):
   └─ Risk Room: VaR & Stress Test Agent, Correlation Agent
   
5. PM calls Critique Room:
   └─ Devil's Advocate Agent, Blind Spot Detector
   
6. PM calls Execution Room:
   └─ Conflict Resolution Agent (resolves any disagreements)
   
7. PM synthesizes:
   ┌─ Detailed Report: Full analysis from all rooms
   ├─ Summary: Key findings in 2-3 paragraphs
   └─ Options: "Option A: Rotate 30% out of tech into bonds.
               Option B: Hold but add protective hedges.
               Option C: Wait for upcoming Fed meeting before rotating."
```

---

## Tech Stack (Planned)

| Layer | Technology |
|-------|-----------|
| Desktop Shell | Electron |
| LLM Orchestration | User-provided API keys (Ollama, Claude, GPT, Gemini) |
| Memory / Vector DB | TBD (likely Chroma or LanceDB) |
| Knowledge Graph | TBD (likely in-app graph structure) |
| Agent Framework | Custom orchestration layer |
| Broker Integration | ccxt, broker-specific SDKs |
| Encryption | AES-256, PBKDF2 (local vault) |
| Database | SQLite (local-first) |

---

## Binding Constraints

- **Local-first:** Everything runs on user's machine. No cloud dependency.
- **User-provided LLM:** User brings their own API keys. App routes through them.
- **Offline-capable:** Core functionality works without internet (using local Ollama models).
- **Open source:** MIT license.

---

*This architecture document will be updated as implementation details are finalized.*
