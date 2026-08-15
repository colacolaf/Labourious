# Labourious Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       USER                                       │
│            (Chats with the orchestrator in the app)              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                    Electron Desktop App
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                  ORCHESTRATOR (main agent)                       │
│              Neutral — routes work, synthesizes answers          │
│                                                                  │
│  1. User sends request                                           │
│  2. Orchestrator evaluates → selects specialist agents           │
│  3. Orchestrator sends each agent a task (briefing format)       │
│  4. Agents run: own LLM call + own system prompt + connectors    │
│  5. Orchestrator collects outputs, resolves conflicts            │
│  6. Orchestrator synthesizes → one answer                        │
└────────────────────────┬────────────────────────────────────────┘
                         │  hub-and-spoke — no direct agent-to-agent calls
         ┌───────────────┼───────────────┬──────────────┐
         ▼               ▼               ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Agent 1 │    │ Agent 2 │    │ Agent 3 │    │ Agent N │
    │Research │    │  Risk   │    │  Macro  │    │  ...    │
    │ lead    │    │  lead   │    │  lead   │    │         │
    └─────────┘    └─────────┘    └─────────┘    └─────────┘
         │               │               │              │
    ┌────▼────┐     ┌────▼────┐     ┌────▼────┐   ┌─────▼────┐
    │Connector│     │Connector│     │Connector│   │Connector │
    │ web     │     │ market  │     │  SEC    │   │ news     │
    │ search  │     │  data   │     │ EDGAR   │   │          │
    └─────────┘     └─────────┘     └─────────┘   └──────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Chat    │    │ Agent   │    │ Config  │
    │ History │    │ Notes   │    │ Files   │
    │ (files) │    │ (files) │    │ (files) │
    └─────────┘    └─────────┘    └─────────┘
```

---

## Core Components

### 1. Orchestrator (Main Agent)

The orchestrator is the only agent the user interacts with. It is deliberately **neutral** — a routing and synthesis layer, not a persona (the persona is user-configurable later).

**System prompt structure (v2, advanced):**
- **Routing protocol:** for each category/agent — what it specializes in, trigger conditions, what context to send, expected output contract
- **Delegation rules:** how tasks are packaged (briefing format: TASK / CONTEXT / URGENCY / DEPTH), when to run agents in parallel vs sequentially
- **Synthesis rules:** how to combine agent outputs into one answer, how to surface disagreement
- **Structured output:** the orchestrator returns a defined schema the app renders

**Calling logic (hub-and-spoke):**
1. Orchestrator evaluates the user request against routing rules
2. Selects relevant agents (1–15 for a complex request)
3. Sends each agent a task briefing (independent agents in parallel, dependent ones sequentially)
4. Collects outputs; resolves conflicts (e.g., via the Critique category's conflict-resolution agent)
5. Synthesizes into one response

### 2. Specialist Agents (Real Agents, Not Subagents)

Each specialist is a **genuine agent**: its own LLM call with its own system prompt, its own configured model, and access to connectors.

**Agent definition (config file):**

```json
{
  "id": "web-research",
  "name": "Web Research Agent",
  "category": "research",
  "model": "openai/gpt-4o",              // or anthropic/... , ollama/...
  "systemPrompt": "docs/frontend/ground/research/web-research/system-prompt.md",
  "connectors": ["web_search", "url_fetch"],
  "maxSteps": 8,
  "notesDir": "data/notes/web-research"
}
```

**System prompt contents (per agent):**
- Identity, role, and domain boundaries
- Connector usage protocols (when to call each tool, output contracts, failure handling)
- Data freshness & source verification rules
- Structured output format the orchestrator consumes
- "Unknown" handling and fallback behavior

**Agent types:**
- **Base leads (16):** one per category, shipped with the app
- **Pluggable agents:** added by the user (via the in-app editor or by dropping a config file + prompt into the agents folder)

### 3. Connectors

Connectors are real tool implementations the agents can call. Providers are **configurable** — the user picks the provider and enters a key in settings.

| Connector | Providers | Notes |
|---|---|---|
| `web_search` | Serper, Tavily, Brave (configurable) | Search results + snippets |
| `url_fetch` | — | Read a page as text |
| `market_data` | yfinance-style (keyless), Polygon, FMP (configurable) | Prices, fundamentals |
| `sec_edgar` | SEC EDGAR (free, official) | 10-K, 10-Q, 8-K, 13F |
| `news` | NewsAPI / provider feeds (configurable) | Article aggregation |

Every connector call is logged; agents are prompted to report `CONNECTOR STATUS: SUCCESS/PARTIAL/FAILED` and fall back gracefully.

### 4. Memory (Minimal, File-Based)

- **Chat history:** per-conversation JSON files
- **Agent notes:** each agent can write notes to its own markdown/JSON file (persistent across sessions)
- No vector DB in the skeleton — the interface is designed so a vector store can slot in later

### 5. Config & Secrets

- **Config file:** `~/.labourious/config.json` — providers, models, agent overrides, user mandates
- **Secrets:** stored via Electron `safeStorage` (OS keychain) where available, with plain-file fallback; never logged

### 6. Customization (In-App Editor)

The app includes an agent editor:
- Edit system prompts (rich text / markdown)
- Change per-agent model & provider
- Add/remove connectors
- Add/duplicate/delete agents
- All changes **persist to files** on disk so the roster is portable and git-able

---

## Data Flow: Example Request

**User:** "Should I rotate my tech holdings given the macro environment?"

```
1. Orchestrator evaluates request
   → Relevant categories: Macro, Fundamental, Risk, Critique, Strategy

2. Orchestrator calls agents in parallel (first wave):
   ┌─ Macro lead: Central-bank & liquidity brief
   └─ Research lead: News + filings brief

3. Orchestrator calls agents in parallel (second wave, uses first-wave outputs):
   ┌─ Fundamental lead: DCF & moat brief
   └─ Technical lead: chart & pattern brief

4. Orchestrator calls Risk lead: stress-test brief

5. Orchestrator calls Critique lead (devil's advocate) on the assembled case

6. Orchestrator resolves conflicts and synthesizes:
   ┌─ The analysis (with citations from each agent)
   ├─ Key takeaways
   └─ Options: "A: rotate 30% out of tech into bonds.
                B: hold but add protective hedges.
                C: wait for the upcoming Fed meeting."
```

---

## Binding Constraints

- **Local-first:** everything runs on the user's machine. No cloud dependency.
- **User-provided LLM:** user brings their own API keys; the app routes through them (provider-agnostic).
- **Offline-capable:** works with local Ollama models.
- **Open source:** MIT license.

---

*This architecture document will be updated as the skeleton is implemented.*
