# Labourious

**The ultimate AI portfolio manager. So detailed it won't miss.**

Labourious is a local-first, GitHub-installable Electron desktop app. You connect your own API model, chat with a calm, collected Portfolio Manager, and it orchestrates 30-40 highly sophisticated AI subagents across 16 specialized rooms to give you insights most AI misses entirely.

---

## What It Is

A single Portfolio Manager agent that you talk to directly. When you ask something — "analyze my tech holdings," "should I rotate into bonds given the macro environment?", "find me undervalued mid-cap healthcare stocks with strong moats" — the Portfolio Manager automatically calls the right subagents alive. Each subagent wakes up with its own multi-page system prompt, does deep research in its domain (1-10 minutes), cites fresh sources, and returns its findings.

The Portfolio Manager then synthesizes EVERYTHING into one unified report: a detailed deep-dive, a summary, and a set of clear options for what to do next.

---

## How It's Different

| Typical AI | Labourious |
|---|---|
| One model, one response | One orchestrator, 30-40 specialized agents all contributing |
| Surface-level analysis | Multi-room deep research — quant, fundamental, macro, sentiment, alternative data, and more |
| No memory between sessions | Vector DB + knowledge graph that learns from every decision |
| Generic | You write the rules, mandates, and constraints; PM always follows them |
| Cloud-dependent | Runs locally. Your keys, your data, your machine |

---

## The 16 Rooms

| # | Room | Purpose |
|---|------|---------|
| 1 | **Research** | Deep web research, SEC filings, news, academic papers, alternative data |
| 2 | **Risk** | Portfolio stress testing, VaR, drawdown, correlation matrices, black swan detection |
| 3 | **Macro** | Central bank policy, GDP, inflation, geopolitics, currency flows, sovereign debt |
| 4 | **Quant** | Factor analysis, statistical arbitrage, momentum models, mean reversion, options pricing |
| 5 | **Fundamental** | DCF models, competitive moat analysis, management quality, forensic accounting |
| 6 | **Technical** | Chart patterns, volume profile, market microstructure, order flow, liquidity |
| 7 | **Sentiment** | News sentiment, social media, analyst reports, insider trading, options flow, dark pool |
| 8 | **Strategy** | Portfolio construction, asset allocation, tactical overlays, hedging, tax-loss harvesting |
| 9 | **Execution** | Order routing, slippage, TWAP/VWAP, broker selection, timing optimization, conflict resolution |
| 10 | **Memory/Knowledge** | Long-term memory, learns from past decisions, builds knowledge graph |
| 11 | **Critique** | Devil's advocate — challenges every recommendation, finds blind spots |
| 12 | **Compliance & Tax** | Wash sale rules, PDT, cross-border tax, concentration limits, regulatory changes |
| 13 | **Alternative Data** | Satellite imagery, credit card data, supply chain tracking, shipping, weather/crop data |
| 14 | **Crypto/Digital Assets** | On-chain analytics, DeFi, tokenomics, protocol risk, custody |
| 15 | **Control** | Meta-agents that manage other agents, quality control, agent health |
| 16 | **Tasks/Automation** | Idle-mode research, daily briefings, periodic insight surfacing |

Each room has 1-5 agents. Agents can overlap — Quant and Risk might both analyze the same data from different angles. Some agents have lightweight "intern" sub-agents for when the main agent is overwhelmed.

---

## Tech Stack

- **Desktop shell:** Electron
- **LLM:** User's own API model — Ollama (local), Claude, GPT, Gemini (any or all)
- **Memory:** Vector DB + knowledge graph
- **License:** MIT — open source
- **Philosophy:** Local-first. Your keys, your machine, your data.

---

## Quick Links

- [Architecture](LABOURIOUS_ARCHITECTURE.md) — How the Portfolio Manager and subagent system works
- [Agents](AGENTS.md) — Complete 16-room agent taxonomy
- [Setup](LABOURIOUS_SETUP.md) — Install from GitHub and connect your API model
- [Features](FEATURES.md) — Full feature set
- [Security](SECURITY.md) — Local-first security model

---

## The Portfolio Manager

The Portfolio Manager is the only agent the user talks to. It is calm, collected, and deliberate. Its system prompt (2-5 pages) contains sections on every subagent and exactly when to call them. It automatically decides which agents to wake up based on the user's request, calls them in parallel or sequentially, and synthesizes their outputs.

Users can set persistent rules/mandates: "Never invest in fossil fuels," "Keep 20% cash minimum," "Only trade during NYSE hours." The PM always follows them.

If agents disagree, the Execution Room's conflict resolution agent makes the final call — or presents both arguments to the user.

---

## Status

**Phase: Documentation & Design** — architecture defined, agent taxonomy in progress. Implementation begins after frontend design is finalized.

---

*Labourious. The AI portfolio manager that goes deeper.*
