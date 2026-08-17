# Changelog

All notable changes to Labourious.

## [Unreleased] — Restructure (2026-08-16)

### Summary
Three adversarial audits (the prompt in `docs/prompts/ANALYZE-THE-PROJECT.md`, archived) found that the 26-agent roster was overbuilt for the actual job and relied on claims no prompt text can support. The repository is restructured into **the Analyst's Bench**: **5 system prompts** powering **8 named flows** with a **runtime skeleton** that can run on free models, validated by a **5-test eval suite**, and made durable by a **thesis register** that gives the system memory across runs. See `docs/RESTRUCTURING.md` for the full audit trail and `docs/CONTEXT.md` for the framing.

### Removed
- **`docs/frontend/`** — entire 89-prompt pixel-art prototype library (89 system prompts + 89 `look.md` + 5 floor READMEs). Persona-driven; structurally absorbed into the v2 library, then trimmed to 5 prompts.
- **23 deferred v2 prompts** (12 lead prompts kept only the senior-analyst lead; 13 specialist prompts kept only forensic-accounting + devils-advocate; 1 pluggable prompt removed in favour of the knowledge-pack policy in `docs/DEFERRED.md`).
- **`docs/prompts/scripts/validate-v2-prompts.py`** — structural linter that lints against the shape it was written to enforce (tautology); replaced by behaviour-based evals at `docs/runtime/evals/`.
- **`docs/prompts/ANALYZE-THE-PROJECT.md`** — meta-prompt for the analysis that drove the restructure; the analysis is archived in `docs/RESTRUCTURING.md` and below.
- **6 obsolete top-level docs** — `AGENTS.md`, `V1-ROSTER.md`, `LABOURIOUS_ARCHITECTURE.md`, `LABOURIOUS_SETUP.md`, `FEATURES.md`, `SECURITY.md`. Replaced by the docs listed below.

### Added
- **7 framing docs** at `docs/` — `CONTEXT.md` (the framing), `ARCHITECTURE.md` (components/calling model), `ROADMAP.md` (build order), `USER-JOBS.md` (the 5 user jobs + no-build list), `CANNOT-DO.md` (honest boundary list), `DEFERRED.md` (what's parked vs. deleted), `RESTRUCTURING.md` (the audit trail).
- **`docs/prompts/leads/senior-analyst/system-prompt.md`** — NEW. Replaces 12 lead prompts. Single voice; owns the thesis; coordinates the 2 specialists.
- **`docs/prompts/specialists/forensic-accounting/system-prompt.md`** — MOVED from `docs/prompts/fundamental/forensic-accounting/`. Rewritten to report to senior-analyst.
- **`docs/prompts/specialists/devils-advocate/system-prompt.md`** — MOVED from `docs/prompts/critique/devils-advocate/`. Stricter: refuses if THESIS is too weak.
- **`docs/prompts/cross-cutting/final-report/system-prompt.md`** — Rewritten with a strict 6-section memo template (Bottom line + Bull + Bear + What an attacker would say + Next three questions + Citations). Replaces the prior IPS + Final Report structure.
- **`docs/flows/README.md`** + **8 flow files** (`f1-analyze-ticker.md` through `f8-macro-overlay.md`) — recipes that use the 5 prompts in different orders/rubrics. f1 is the flagship.
- **`docs/runtime/runtime.py`** + **`docs/runtime/README.md`** — runtime skeleton. CLI shape: `python docs/runtime/runtime.py --flow f1 --ticker NVDA --model ollama/llama3.3:70b [--paid-for final-report]`. f1 is fully wired; f2-f8 raise `NotImplementedError` (P1).
- **`docs/runtime/adapters/`** — `anthropic.py`, `ollama.py`, `groq.py`, `openai_compat.py`. Common `Response` interface.
- **`docs/runtime/tools/`** — `sec_edgar.py`, `news.py`, `market_data.py`, `web_fetch.py`.
- **`docs/runtime/thesis_register/`** — `schema.sql` + `register.py` + `README.md`. SQLite with 3 tables; CLI at `register.py` for ad-hoc inspection.
- **`docs/runtime/evals/`** — 5 pytest files (`test_hallucination.py`, `test_source_verification.py`, `test_per_asset_coverage.py`, `test_freshness.py`, `test_abstention.py`) + README. The 5-test eval suite is the only evidence the system works.

### Changed
- **`docs/prompts/orchestrator/system-prompt.md`** — slimmed. Now reports the 5-agent roster and points to `docs/flows/` for per-flow recipes. Per-agent gate enforcement moved to runtime.
- **`docs/prompts/V2-PROMPT-STANDARD.md`** — rewritten to scope to the 5-agent roster; per-agent-type schemas collapsed into a single shared envelope.
- **`docs/README.md`** + **`README.md`** (root) — rewritten. Now describe the Analyst's Bench framing; no more 89-prompt references.

### Net change
- **−112 prompts deleted** (89 frontend + 23 v2 deferred; 5 rewritten/kept).
- **−7 obsolete top-level docs** (replaced by 7 new framing docs + 1 README rewrite).
- **+8 flow files, +4 model adapters, +4 tool adapters, +1 thesis register schema, +1 thesis register module, +5 eval tests, +1 runtime, +1 runtime README.**
- **+~1500 lines of Python across the runtime (runtime.py + 4 adapters + 4 tools + register + 5 eval tests).**

### Planned (next, per `docs/ROADMAP.md`)
P0 items in order: runtime → f1 → evals → free-model adapter layer → tool adapters → thesis register. The first f1 end-to-end run on a calibrated baseline is the milestone that turns the restructure from "consistent paper analysis" into "verifiable system."

---

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
## [Unreleased] — Frontend decision: Python TUI (Textual v4 + Rich) (2026-08-16)

### Summary
Replacing the planned Electron desktop app with a Python TUI built on
Textual v4 + Rich. Decision rationale in
[`docs/FRONTEND-DECISION.md`](docs/FRONTEND-DECISION.md). Constraint
that drove it: "not in the browser" + "simplicity is best" + "advanced
chat feel." TUI ships the chat experience directly in the terminal,
consumes an event stream from the runtime (no Chromium, no Electron,
no Node build step).

### Added
- **`docs/FRONTEND-DECISION.md`** — research summary + decision matrix
  (TUI vs. web app vs. Tauri vs. plain CLI vs. Electron). TL;DR: TUI
  wins on every constraint.
- **`docs/frontend/README.md`** + **`docs/frontend/SPEC.md`** + **`docs/frontend/SCREENS.md`** + **`docs/frontend/PROTOCOL.md`** + **`docs/frontend/IMPLEMENTATION.md`** — the TUI's spec, screen state machine, runtime↔TUI event protocol, and file plan with line budgets (~1500 lines of Python + ~150 lines of CSS).
- Two stub subdirectories under `docs/frontend/`: `screens/` and `widgets/` (reserved for the future Python implementation; specs live in the parent files).

### Changed
- **`docs/ARCHITECTURE.md`** §Components — added § 6 "The user surface" describing the TUI; CLI/TUI parity. Runtime + TUI are in-process (one Python interpreter, one event iterator).
- **`docs/ROADMAP.md`** — added the TUI as P0 item 7 (`docs/frontend/`); reshuffled flow-f2/f3/f4 to P1, f5-f8 to P2, and Wharton deliverables (f9/f10) to P2.

---

EOF

