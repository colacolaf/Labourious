# Changelog

All notable changes to Labourious.

## [Unreleased] — V1 roster decided (2026-08-15)

### Added
- **`docs/V1-ROSTER.md`** — the definitive first-product roster: **26 core agents** (12 leads, 13 specialists, Final Report Agent) + 1 pluggable example (Sector Analyst with per-sector knowledge packs), built for the Wharton Investment Competition workflow. Every agent specified with ID, job, source prompt (functionalized from the 89-prompt library), and connectors; includes the default delegation map for the flagship flows.

### Changed
- `docs/AGENTS.md` — superseded the 16-lead plan with a pointer to `V1-ROSTER.md`.
- `docs/CONTEXT.md` — recorded the roster interview decisions (15–22) and research basis (Anthropic multi-agent lessons, LangChain patterns).
- `README.md`, `docs/README.md`, `docs/FEATURES.md` — agent-count references synced to the 26-agent roster.

### Decided (product)
- Audience: Wharton Investment Comp; personas fully functionalized (persona agents become pluggable examples); US + global equities; read-only portfolio; single-user; effort scaling rules in the orchestrator prompt; no comp-rules context layer; Crypto/Tasks/Memory/Control deferred to v2.

---

## [Unreleased] — Pivot: from pixel-art HQ to agent skeleton (2026-08-15)

### Removed
- **Entire pixel-art frontend prototype** (`frontend/`): Phaser 3 lobby, floor catalog, 23 room/roster HTML pages, agent gallery, 94 pixel-art agent portraits, tilesets, floor swatches, and asset build scripts.
- **89 `look.md`** pixel-art look descriptions (obsolete without sprites).
- **5 `ui.md`** floor UI-showcase stubs and **`docs/frontend/ground-floor.svg`** building layout diagram.
- **5 floor-level READMEs** (`docs/frontend/{ground,floor-2,floor-3,floor-4,penthouse}/README.md`) — building concept docs.

### Fixed
- **11 orphaned system prompts un-nested**: named specialists (Hempton, Markopolos, Thorp, Bremmer, Swensen, Whitney, Sornette, Svanevik, Crawford, Najarian, Rosenbloom) had prompts stranded inside their lead's folder. Moved to canonical agent folders; nested dirs removed. 89 prompts / 89 agent folders verified.

### Changed
- **Root README rewritten** for the new direction: Electron app, neutral orchestrator, real agents with connectors, file-based config.
- **Docs rewritten** (`docs/README.md`, `LABOURIOUS_ARCHITECTURE.md`, `AGENTS.md`, `FEATURES.md`, `LABOURIOUS_SETUP.md`, `SECURITY.md`): rooms → flat categories; subagents → real agents; PM persona → neutral orchestrator; hub-and-spoke comms; configurable connector providers; file-based memory.
- **`docs/frontend/README.md` rewritten** as the agent prompt library index (categories, not floors).

### Added
- **`docs/CONTEXT.md`** — the pivot log: what was deleted/kept/fixed, the full decision list from the design interview, and next moves.
- **`CHANGELOG.md`** — this file.

### Kept
- **89 system prompts** (`docs/frontend/`) — the raw material for the app's agent roster.
- Agent-level READMEs, category READMEs, prompt framework/test docs, `validate-system-prompts.py`.

### Planned (not yet built)
- Electron app skeleton: chat UI, neutral orchestrator, agent runtime, connectors (web search / market data / SEC / news), file memory, config + keychain, in-app agent editor. See `docs/CONTEXT.md` and `docs/LABOURIOUS_ARCHITECTURE.md`.
