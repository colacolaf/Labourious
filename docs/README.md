# Labourious Documentation

The product design, architecture, agent taxonomy, security model, and agent prompt library for Labourious. For the repository overview, start with the [root README](../README.md).

> **Status note:** the Electron app described here is **planned architecture**. The runnable asset today is the agent prompt library under [`frontend/`](frontend/) (89 system prompts) — formerly "docs/frontend", kept as-is pending reorganization.

**The AI portfolio manager designed to go deeper.**

Labourious is a local-first Electron desktop app. You connect your own API keys, chat with a neutral orchestrator agent, and it delegates to real specialist agents — each with its own system prompt, model, and connectors — to produce deeper investment research.

---

## What It Is

A single orchestrator agent that you talk to directly. When you ask something — "analyze my tech holdings," "should I rotate into bonds given the macro environment?", "find me undervalued mid-cap healthcare stocks with strong moats" — the orchestrator automatically wakes the right specialists. Each specialist runs as a genuine agent (its own LLM call, its own system prompt, its own tools) and returns findings with citations.

The orchestrator then synthesizes everything into one unified answer: the analysis, the key takeaways, and clear options for what to do next.

## How It's Different

| Typical AI | Labourious |
|---|---|
| One model, one response | One orchestrator, a team of specialist agents all contributing |
| Simulated subagents | Real agents with real connectors (web search, market data, SEC filings, news) |
| Fixed roster | Customizable — agents, prompts, models, and connectors editable in-app and saved to files |
| Cloud-dependent | Runs locally. Your keys, your data, your machine |

## The Agent Categories

There are no "rooms" and no building — agents are simply grouped into **categories** for organization. The v1 roster ships **26 core agents** (12 leads + 13 specialists + 1 final-report agent) plus pluggable examples — the definitive list is in **[V1-ROSTER.md](V1-ROSTER.md)**. The full category map:

| # | Category | Lead | Purpose |
|---|----------|------|---------|
| 1 | Research | Michael Burry | Deep web research, SEC filings, news, academic papers |
| 2 | Risk | Nassim Taleb | Stress testing, VaR, drawdown, black swan detection |
| 3 | Macro | Larry Fink | Central bank policy, GDP, inflation, geopolitics, currency |
| 4 | Quant | Jim Simons | Factor analysis, stat arb, momentum, options pricing |
| 5 | Fundamental | Warren Buffett | DCF, moats, management quality, forensic accounting |
| 6 | Technical | Mark Minervini | Chart patterns, volume profile, order flow, liquidity |
| 7 | Sentiment | Cathie Wood | News sentiment, social media, analysts, insider moves |
| 8 | Strategy | David Swensen | Asset allocation, tactical overlays, hedging, tax harvesting |
| 9 | Execution | — | Order routing, timing, slippage, conflict resolution |
| 10 | Memory | — | Long-term notes, learns from past decisions |
| 11 | Critique | Charlie Munger | Devil's advocate — challenges every recommendation |
| 12 | Compliance & Tax | Preet Bharara | Wash sales, PDT, cross-border tax, concentration limits |
| 13 | Alternative Data | Matthew Granade | Satellite, credit-card, supply chain, weather data |
| 14 | Crypto/Digital Assets | Vitalik Buterin | On-chain analytics, DeFi, tokenomics, protocol risk |
| 15 | Control | — | Quality control, agent health |
| 16 | Tasks/Automation | — | Daily briefings, periodic insight surfacing |

Categories marked with **—** are deferred from v1 (see the deferred table in [V1-ROSTER.md](V1-ROSTER.md)). The full taxonomy lives in [AGENTS.md](AGENTS.md).

## Tech Stack (Planned)

| Layer | Technology |
|-------|------------|
| Desktop Shell | Electron |
| Chat UI | Web-based renderer in Electron |
| LLM Orchestration | Provider-agnostic: OpenAI-compatible, Anthropic, Ollama (user-provided keys) |
| Agent Runtime | Custom lightweight runtime — one LLM call per agent, system prompt + connectors per agent |
| Connectors | Web search (Serper/Tavily/Brave), market data (yfinance-style/Polygon/FMP), SEC EDGAR (free), news — all configurable |
| Memory | Chat history + agent notes as plain files (JSON/markdown) |
| Secrets | Local config file, OS-keychain-backed (Electron `safeStorage`) where available |
| CLI | Later, after the app runtime is proven |

## Quick Links

- [Context — what changed and why](CONTEXT.md)
- [Architecture](LABOURIOUS_ARCHITECTURE.md) — orchestrator, agents, connectors, memory
- [Agents](AGENTS.md) — complete category taxonomy
- [Setup](LABOURIOUS_SETUP.md) — planned install and configuration
- [Features](FEATURES.md) — full feature set
- [Security](SECURITY.md) — local-first security model
- [Agent Prompt Library](frontend/README.md) — the 89 system prompts

## Status

**Phase: post-pivot, pre-build.** The pixel-art frontend prototype was deleted (Aug 2026). The agent prompt library (89 system prompts) was kept and cleaned up, and the architecture docs were rewritten for the skeleton app. The Electron app, agent runtime, connectors, and editor are planned work.

*Labourious. The AI portfolio manager that goes deeper.*
