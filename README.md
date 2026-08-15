# Labourious

**A local-first AI portfolio manager — one orchestrator agent, a team of specialist agents, real connectors, and your own API keys.**

Labourious is an Electron desktop app. You chat with a neutral orchestrator agent; it decides which specialist agents to wake, sends each one a task, collects their outputs, and synthesizes one answer. The specialists are **real agents** — each runs its own model call with its own system prompt and has access to **real connectors** (web search, market data, SEC filings, news). Everything is local-first: your keys, your data, your machine.

> **Current status:** the repository is mid-pivot. The pixel-art "building" frontend prototype was removed entirely (see [`docs/CONTEXT.md`](docs/CONTEXT.md) for the full story). What remains is the **agent prompt library** — 89 system prompts under [`docs/frontend/`](docs/frontend/) — plus a rewritten architecture. The Electron app skeleton itself is **planned, not yet built**.

## What exists today

- **Agent prompt library** — 89 system prompts across 18 categories (research, sentiment, alt-data, macro, quant, fundamental, technical, crypto, risk, critique, compliance, strategy, execution, memory, control, tasks, perimeter, penthouse). These are the raw material for the app's agent roster.
- **Prompt engineering framework** — validation scripts, audit frameworks, and test templates for upgrading prompts to v2 (tool protocols, routing rules, structured outputs).
- **Design docs** — architecture, taxonomy, features, setup, and security model for the planned app.

## The planned app (skeleton)

| Layer | Plan |
|---|---|
| Shell | Electron desktop app ("opens like Chrome") |
| Chat UI | One chat window with the orchestrator; activity panel showing which agents were called |
| Orchestrator | Neutral main agent — routes work to specialists (hub-and-spoke), synthesizes results |
| Agents | 16 base leads (one per category) + pluggable agents; each agent = its own system prompt + model + connectors |
| LLM layer | Provider-agnostic — OpenAI-compatible, Anthropic, Ollama (per-agent model choice) |
| Connectors | Configurable providers: web search (Serper / Tavily / Brave), market data (yfinance-style / Polygon / FMP), SEC EDGAR (free), news |
| Customization | In-app editor — system prompts, models, connectors, and roster, all saved to files on disk |
| Memory | Chat history + agent notes (plain files) |
| Keys | Local config file, OS-keychain-backed where available |
| CLI | Later (after the app runtime is proven) |

## Repository map

| Path | Purpose |
|---|---|
| [`docs/README.md`](docs/README.md) | Product overview and documentation index |
| [`docs/CONTEXT.md`](docs/CONTEXT.md) | **What changed and why** — the pivot log and decisions from the rework |
| [`docs/LABOURIOUS_ARCHITECTURE.md`](docs/LABOURIOUS_ARCHITECTURE.md) | App architecture: orchestrator, agents, connectors, memory |
| [`docs/AGENTS.md`](docs/AGENTS.md) | Agent taxonomy — categories, leads, and the calling model |
| [`docs/FEATURES.md`](docs/FEATURES.md) | Feature set for the skeleton and beyond |
| [`docs/LABOURIOUS_SETUP.md`](docs/LABOURIOUS_SETUP.md) | Planned setup: install, API keys, config file |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Local-first security model |
| [`docs/frontend/`](docs/frontend/) | The agent prompt library (89 system prompts + framework docs) |

## Design principles

- **Local-first:** keys, data, and memory stay on your machine; cloud models are opt-in through your own credentials.
- **Orchestration over one-shot answers:** the orchestrator routes work to domain specialists rather than relying on one generic response.
- **Real agents, real connectors:** every specialist is a genuine agent with tool access — not a simulated subagent.
- **Customizable:** agents, prompts, models, and connectors are user-editable, persisted as files.

## License

MIT (no `LICENSE` file yet).
