# CONTEXT — The Pivot (Aug 2026)

Everything you need to know about why this repository looks the way it does. Read this before reading anything else.

## TL;DR

Labourious was over-ambitious. The repo contained a full pixel-art "research building" frontend prototype (Phaser lobby, 5 floors, 23 room pages, 94 pixel-art agent portraits) plus a huge design-doc estate, and **nothing runnable**. 

The project is now: **a local-first Electron app** where you chat with a **neutral orchestrator agent** that delegates to **real specialist agents** (each with its own system prompt, model, and **real connectors**), fully **customizable** through an in-app editor. The pixel-art frontend is **deleted**. The 89 system prompts are **kept** as the raw material. The app is **planned, not yet built** — this session was cleanup + documentation only.

## What was deleted (this session)

| What | Why |
|------|-----|
| `frontend/` — the entire Phaser pixel-art HQ (lobby, floors.html, 23 room/roster HTML pages, agent-gallery, agent portraits, tilesets, floor catalogs, build scripts) | The "actual room" frontend was the ambition problem. The product is a chat interface, not a walkable building. |
| 89 `look.md` files (one per agent) | Pixel-art look descriptions — obsolete without the sprites. |
| 5 `ui.md` files + `docs/frontend/ground-floor.svg` | Floor/UI showcase stubs and the building layout diagram. |
| 5 floor-level READMEs (`ground/`, `floor-2/`, `floor-3/`, `floor-4/`, `penthouse/`) | Building-floor concept docs; their roster content is now in `docs/AGENTS.md`. |

## What was kept (and why)

| What | Why |
|------|-----|
| **89 `system-prompt.md` files** | The single most valuable asset — a full specialist-agent prompt library with freshness protocols, per-asset gates, connector protocols, and output formats. This is the base for v2 prompts. |
| ~89 agent-level `README.md` files | Persona, role, tools, and per-agent API-key tables — feeds the app's agent config in the build phase. |
| 18 room-level READMEs | Category rosters + per-category API-key tables. Still titled "Room N" — slated for rewrite into category docs during the build. |
| Prompt framework + test docs, `validate-system-prompts.py` | The prompt-engineering machinery that v2 prompt work reuses. |
| `penthouse/` prompts (Portfolio Manager, PM Bodyguard) | Their routing/monitoring content is the ancestor of the orchestrator prompt and a safety layer. |

## What was fixed

- **11 orphaned system prompts un-nested.** Named specialists (John Hempton, Harry Markopolos, Ed Thorp, Ian Bremmer, David Swensen, Meredith Whitney, Didier Sornette, Alex Svanevik, James Crawford, Jon Najarian, H. David Rosenbloom) had their prompts nested inside their lead's folder (e.g. `michael-burry/john-hempton/system-prompt.md`) while their own folders said "System Prompt: _TBD_". All 11 prompts moved into their canonical agent folders; the nested dirs were deleted. **89 prompts, 89 folders, one prompt each — verified.**

## The decisions (from the design interview, Aug 2026)

1. **Frontend:** no room, no building. A skeleton chat interface is the frontend.
2. **Form factor:** an **app** — Electron, opens like Chrome. A terminal/CLI version comes **later**.
3. **Agent model:** real agents — each agent takes the API key, actually calls the model, reads its system prompt, uses its connectors. Not simulated subagents.
4. **LLM providers:** **provider-agnostic** layer — OpenAI-compatible, Anthropic, Ollama; per-agent model choice.
5. **Roster:** **16 base leads** (one per category) + **pluggable agents** users can pop in.
6. **Customization:** **in-app editor** — system prompts, models, connectors, and the roster itself; everything **saved to files** so it's portable.
7. **Connectors:** all three first-class — **web search, market data, SEC filings + news** — with **configurable providers** (user picks provider + key in settings; not hard-coded to one vendor).
8. **Memory:** **chat history + agent notes as plain files.** No vector DB in the skeleton (designed so one can slot in later). No knowledge graph for now.
9. **Docs:** **keep the prompts, rewrite the rest** — done.
10. **Comms:** **hub-and-spoke** — orchestrator → specialists → orchestrator. No direct agent-to-agent calls in the skeleton.
11. **Rooms:** **gone as a concept** — replaced by **categories** (a flat tag; the category list may grow).
12. **Orchestrator:** **neutral** — not the "Portfolio Manager" persona. Routing + synthesis first; persona is user-configurable later.
13. **Keys storage:** local config file (`~/.labourious/config.json`), OS keychain (`safeStorage`) where available.
14. **Prompts v2:** connector/tool-use protocols + delegation/routing protocols + structured output contracts — per agent.

## What the app will look like (planned)

```
User chats → Neutral orchestrator agent
  → picks specialists (hub-and-spoke) → each: own model call + system prompt + connectors
  → collects → synthesizes → one answer
```

Skeleton scope: Electron app + chat UI + orchestrator + 16 base leads + connectors (Serper/Tavily/Brave, yfinance/Polygon/FMP, SEC EDGAR, news) + file memory + config + in-app editor.

## The V1 roster decision (second interview, same session)

The first product targets the **Wharton Investment Competition** (teams of 4–6 students, virtual portfolio on WInS, judged on strategy quality and research strength — not returns; deliverables are the IPS and the Final Report). Research performed before this interview:

- **Anthropic multi-agent research system** — multi-agent excels at breadth-first parallel research but burns ~15× chat tokens; each agent needs distinct tools/prompts or they duplicate work; effort must scale to query complexity (simple 1–3 agents, medium 3–6, deep up to 12).
- **LangChain architecture guide** — hub-and-spoke = the "subagents" pattern (+1 model call per interaction, context isolation); domain/sector knowledge is better as loadable skills on one agent than as separate agents.

Decisions (15–22):

15. **Audience:** the Wharton Investment Comp. The roster maps to the comp workflow: client case → IPS → research → portfolio → Final Report.
16. **Core jobs (all three):** deep company research, portfolio review, screening for ideas.
17. **Roster shape:** function leads only — no per-sector agents as separate agents.
18. **Markets:** US + global equities (matches WInS).
19. **Personas:** fully functional core roster; persona agents (Burry, Buffett, Taleb, …) ship as pluggable examples.
20. **Roster size:** 26 core agents (12 leads + 13 specialists + Final Report Agent) + 1 pluggable example (Sector Analyst with per-sector knowledge packs). **The definitive list is [`V1-ROSTER.md`](V1-ROSTER.md).**
21. **Categories in v1:** Research, Fundamental, Macro, Technical, Sentiment, Quant, Risk, Strategy, Critique, Compliance, Alt Data, Execution. Deferred: Crypto, Tasks/Automation, Memory, Control.
22. **Portfolio:** read-only portfolio awareness in v1. **Team roles:** single-user v1 (sector-owner features later). **Comp context layer:** declined — the app stays generic. **Effort:** scaling rules in the orchestrator prompt (not uncapped). **Automation (daily briefings):** v2.

## Known debt / next moves

1. **Build the skeleton** (`app/` — Electron shell, runtime, connectors, editor). Nothing is implemented yet.
2. **Write the 2 new prompts** — Final Report Agent (IPS + report drafting) and Sector Analyst (pluggable example), then functionalize the ~20 core prompts from the library (strip personas, add connector protocols + output contracts).
3. **Write the v2 orchestrator prompt** — routing protocol (effort tiers), synthesis rules, structured output.
4. **Reorganize the prompt tree** — `docs/frontend/floor-*` paths still say "floor"; move to `prompts/<category>/<agent>/` and rename room READMEs into category docs.
5. **v2 prompt upgrade** — add connector protocols, routing rules, and output contracts to all 89 prompts using the existing framework docs.
6. **Perimeter + penthouse prompts** — Entrance Bodyguard and PM Bodyguard become pluggable examples (already decided); no action needed beyond packaging.
