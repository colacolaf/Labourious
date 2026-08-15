# Labourious Features

Planned feature set for the skeleton app, ordered by build priority.

## Skeleton (v0.1) — the minimal runnable app

- **Electron desktop app** with a chat interface
- **Neutral orchestrator agent** — routes work to specialists (hub-and-spoke), synthesizes answers
- **Real agent runtime** — each agent is a genuine LLM call with its own system prompt and connectors
- **Provider-agnostic LLM layer** — OpenAI-compatible APIs, Anthropic, Ollama; per-agent model choice
- **26 core agents** — 12 category leads + 13 specialists + final-report agent, functionalized from the existing 89-prompt library (see [`V1-ROSTER.md`](V1-ROSTER.md))
- **Connectors (configurable providers):**
  - Web search: Serper / Tavily / Brave
  - Market data: yfinance-style (keyless) / Polygon / FMP
  - SEC EDGAR (free)
  - News feeds
- **Chat history** — per-conversation persistence (JSON files)
- **Agent notes** — agents persist notes across sessions (markdown/JSON files)
- **Config file** — `~/.labourious/config.json`; API keys in the OS keychain via `safeStorage` with file fallback
- **In-app agent editor** — edit system prompts, models, connectors; add/duplicate/remove agents; all changes saved to files

## Post-skeleton (v0.2+)

- **User mandates & rules** — persistent constraints the orchestrator always checks ("never invest in fossil fuels", "keep 20% cash minimum")
- **Per-agent usage dashboards** — tokens, calls, cost per agent
- **Vector memory** — semantic search over past research (LanceDB/Chroma), designed-in interface from v0.1
- **CLI version** — terminal chat reusing the same runtime
- **Task automation** — daily briefings, scheduled research (Tasks category)
- **Broker integration** — order routing, execution (Execution category)

## Deferred / Removed

- ~~Pixel-art building HQ (Phaser lobby, floors, agent portraits)~~ — removed entirely, Aug 2026
- ~~Portfolio Manager persona~~ — replaced by a neutral orchestrator (persona is user-configurable later)
- ~~Rooms / floors as a spatial concept~~ — replaced by flat categories
