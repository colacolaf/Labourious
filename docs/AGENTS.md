# Labourious Agent Taxonomy

Agents are organized into **categories** (formerly "rooms"). Categories are a flat organizational tag — there is no building, no floors, and no hierarchy beyond lead → team.

## The Calling Model

```
User → Orchestrator → (task briefings, hub-and-spoke) → Specialist agents → Orchestrator → User
```

- The **orchestrator** is the only agent the user talks to.
- Specialists never call each other directly — all communication flows through the orchestrator.
- A task briefing carries: **TASK** (what to do), **CONTEXT** (relevant history/findings), **URGENCY** (routine/elevated/immediate), **DEPTH** (scan/standard/deep).
- Every specialist returns a **structured output** the orchestrator can consume.

## V1 Roster (the first product)

**26 core agents + 1 pluggable example** ship with v1, built for the Wharton Investment Competition workflow. The definitive list — every agent, its ID, job, source prompt, and connectors — lives in **[`V1-ROSTER.md`](V1-ROSTER.md)**.

At a glance:

- **12 leads** — Research, Fundamental, Macro, Technical, Sentiment, Quant, Risk, Strategy, Critique, Compliance, Alt Data, Execution
- **13 specialists** — Web Research, SEC Filings & Regulatory, DCF & Valuation, Forensic Accounting, Central Bank & Liquidity, Geopolitical Risk, Chart & Pattern, Options Flow & Insider, Factor & Momentum, Stress & Concentration, Black Swan, Devil's Advocate, Position Sizing & Hedging
- **1 cross-cutting** — Final Report Agent (IPS + report drafting)
- **1 pluggable example** — Sector Analyst (per-sector knowledge packs; ships disabled)

All core prompts are **functionalized** from the 89-prompt library (no celebrity personas); the persona agents ship as pluggable examples.

Categories not in v1: Crypto, Memory, Control, Tasks/Automation (see the deferred table in [`V1-ROSTER.md`](V1-ROSTER.md)).

## Non-Category Agents

| Agent | Status in v1 |
|-------|--------------|
| Portfolio Manager | Former "penthouse" main agent — its routing/synthesis logic is the ancestor of the orchestrator prompt; the persona is retired (neutral orchestrator) |
| PM Bodyguard | Pluggable example — its monitoring/interrupt protocol is a candidate for a Control-category agent or an orchestrator safety layer |
| Entrance Bodyguard | Pluggable example — perimeter agent; candidate for a request-vetting layer in front of the orchestrator |

## Agent Levels

The prompt library uses a tier system that carries over to the app:

| Level | Meaning | Example |
|-------|---------|---------|
| **T1 — Lead** | Category lead; receives orchestrator briefs and delegates within the category | Michael Burry, Nassim Taleb |
| **T2 — Named specialist** | A named expert persona with deep domain prompts | Harry Markopolos, Ed Thorp |
| **T3 — Utility agent** | Standard specialist with tool protocols and quality gates | Web Research Agent, DCF & Valuation Agent |
| **T4 — Intern** | Lightweight agents for overflow or time-sensitive work | Bear Case Intern, Position Sizing Intern |

## Custom Agents (Pluggable)

Users add agents by:
1. **In-app editor** — create/duplicate an agent, edit its prompt, pick its model and connectors; saved to the agents folder.
2. **File drop** — place a config file (JSON) + a system-prompt markdown file in the agents folder; the app picks it up.

Every agent needs: id, name, category, model, system prompt, connector list.

## System Prompt v2

The 89 prompts in the library are the base. The v2 upgrade adds (per agent):
- **Connector + tool-use protocols** — exact instructions per tool, when to call, output contracts, failure handling
- **Delegation + routing protocols** — how leads receive briefs and how they delegate
- **Structured output contracts** — every agent returns JSON with a defined schema the orchestrator consumes

The framework docs under `docs/frontend/` (SYSTEM-PROMPT-FRAMEWORK, audit frameworks, test templates) define how this upgrade is done and validated.
