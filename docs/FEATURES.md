# Labourious Features

## Feature Overview

Labourious is the ultimate AI portfolio manager — a single orchestrator (the Portfolio Manager) that coordinates 30-40 specialized subagents across 16 rooms to produce insights most AI misses.

---

## Core Features

### Portfolio Manager (Main Orchestrator)
- **Single chat interface** — user talks only to the PM
- **Calm, collected personality** — thorough, never rushed
- **Automatic agent selection** — PM decides which agents to call, no user confirmation needed
- **Comprehensive system prompt** — 2-5 pages with sections on every subagent and when to call them
- **Synthesis engine** — combines all agent outputs into:
  - Detailed report with full analysis
  - Concise summary
  - Clear options for next steps
- **Time-aware** — respects urgency (lightweight agents for fast responses, full agents for deep dives)

### Rules & Mandates
- User-defined persistent constraints the PM always follows
- Examples: "Never invest in fossil fuels," "Keep 20% cash minimum," "No single position over 5%"
- Checked against every recommendation

### Subagent System
- **30-40 highly sophisticated agents** across 16 specialized rooms
- **Multi-page system prompts** per agent — personality, expertise, tools, citation rules, formatting
- **1-10 minute research cycles** depending on agent and complexity
- **Fresh source citation** — must use recent data, no stale information
- **Intern agents** — lightweight versions for when main agents are overwhelmed or time is tight
- **Intentional overlap** — Quant and Risk may analyze same data from different angles
- **Hierarchy** — primary agents + intern sub-agents

### 16 Specialized Rooms
| Room | Domain |
|------|--------|
| Research | Web search, SEC filings, news, academic papers |
| Risk | VaR, stress testing, correlation, black swan detection |
| Macro | Central bank policy, GDP, geopolitics, currency |
| Quant | Factor analysis, statistical arbitrage, ML signals |
| Fundamental | DCF models, moat analysis, forensic accounting |
| Technical | Chart patterns, volume profile, order flow |
| Sentiment | News sentiment, insider tracking, options flow |
| Strategy | Asset allocation, hedging, tax optimization |
| Execution | Order routing, slippage, TWAP/VWAP, conflict resolution |
| Memory/Knowledge | Vector DB, knowledge graph, learning from past decisions |
| Critique | Devil's advocate, blind spot detection |
| Compliance & Tax | Wash sale rules, PDT, cross-border tax |
| Alternative Data | Satellite imagery, supply chain, credit card data |
| Crypto/Digital Assets | On-chain analytics, DeFi, tokenomics |
| Control | Quality control, agent health monitoring |
| Tasks/Automation | Idle-mode research, daily briefings |

### Memory System
- **Vector database** — semantic search across past conversations and research
- **Knowledge graph** — structured entity relationships, learns from every decision
- **Persistent agent memory** — agents remember across calls
- **User can query memory** — "What did we conclude about TSLA last quarter?"

### Agent Interaction
- **User talks ONLY to PM** — no direct subagent chat
- **Agent inspection** — user can "walk over" and click any agent to see its reasoning and data
- **Editable system prompts** — full customization of any agent's personality and behavior

### Conflict Resolution
- Dedicated agent in Execution Room handles agent disagreements
- Presents both arguments or makes the final call
- All resolutions logged to memory

### Idle Mode
- Tasks/Automation Room runs even when user isn't asking
- Daily market briefings
- Periodic insight surfacing
- Proactive opportunity detection

---

## LLM Flexibility
- User brings own API keys — Ollama, Claude, GPT, Gemini
- Any combination supported
- Same model for all agents, or per-agent model assignment
- Local-only mode (Ollama) works fully offline

---

## Trading Features
- Broker integration via encrypted vault (IB, Kraken, Coinbase, more)
- Paper trading mode
- Real-time market data
- Trade execution through Execution Room
- Position sizing, stop losses, take profits
- Portfolio tracking and P&L

---

## Platform
- **Electron desktop app** — native window, not in-browser
- **GitHub-installable** — clone, install, run
- **Local-first** — all data on user's machine
- **Open source** — MIT license

---

## Future Phase Features (TBD)
- Agent marketplace for community-created agents
- Backtesting engine
- Mobile companion app
- Multi-user support
- Email/SMS notifications
- Advanced charting and visualization

---

*Feature set will be refined during implementation. Frontend features defined separately per-page.*
