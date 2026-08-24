# AGENT-LIBRARY — the curated catalog of installable agent nodes

> The agent-library is the app's catalog of agent nodes beyond the 5 built-ins. Each entry is a JSON file under `app/agent-library/`. The app loads the catalog at startup; users install a node by dragging it from the left panel onto the canvas. **No app rebuild to add a node** — drop a JSON file in the folder, restart, it appears.

This file documents:

1. The catalog's **design policy** (what earns a node a place).
2. The **v1 catalog** (5 entries: technical, quant, macro, flow-and-transcript, research-forcer).
3. The **JSON schema** for a catalog entry.
4. The **pluggable-agents policy** as it applies here (carried from `docs/DEFERRED.md`).

---

## 1. Design policy — what earns a node a place

A new agent-library node earns its existence only if it passes **one of two gates** (the same two gates from `docs/DEFERRED.md` §"Pluggable agents must pass one of two tests"):

1. **Distinct data/tool surface** — it reaches a data source the 5 core prompts cannot, or it interprets a tool's output in a way no built-in does (e.g. the Quant agent coaching the DCF/Comps/Comparator trio).
2. **Distinct control-flow role** — it gates, vets, or transforms the pipeline rather than producing analysis (e.g. the research-forcer, which re-runs an upstream agent with a directive).

Anything else — sector-specific knowledge, persona variants, asset-class variants — ships as a **knowledge pack** loaded into an existing agent's prompt (per `docs/runtime/packs.py`), not as a new agent node. **Sectors are knowledge packs, not agents.** This is unchanged from `docs/DEFERRED.md` §1.

The library is **curated by the maintainers**, not user-uploaded. User-forkability (creating a new agent node from a user-written prompt) is explicitly deferred to Phase 6+ per [`ROADMAP.md`](ROADMAP.md) — see `CANNOT-DO.md` §6.

---

## 2. The v1 catalog

Five entries ship in Phase 3 (technical, quant, macro, flow-and-transcript) and Phase 4 (research-forcer).

### 2.1 Technical agent

| Field | Value |
|---|---|
| `id` | `technical` |
| `display_name` | "Technical Analysis" |
| `description` | "Deep-dive on price action, support/resistance, volume profile, momentum. Consumes market_data output." |
| `node_type` | `agent` |
| `source` | `library` |
| `default_model` | `ollama/llama3.3:70b` |
| `system_prompt_ref` | `docs/prompts/library/technical/system-prompt.md` |
| `connectors_consumed` | `["market_data"]` |
| `inputs` | `["envelope"]` (the upstream agent's envelope) |
| `outputs` | `["envelope"]` (with `technical_analysis` section added) |
| `accent_color` | `#9b59b6` (purple) |

**What it does:** Reads the upstream agent's envelope (typically senior-analyst's thesis skeleton) + the `market_data` connector's OHLCV output, and produces a technical-analysis section: price action relative to 50/200-day moving averages, momentum (RSI, MACD), volume profile, key support/resistance levels, and a short-term directional bias. The section is added to the envelope under `technical_analysis` and flows to downstream agents.

**Gate passed:** Distinct data/tool surface — interprets `market_data`'s raw OHLCV in a way no built-in does. (One of the deferred leads from `docs/DEFERRED.md` — the `technical-lead` gate was "Re-hire if a user asks for entry-timing on a flow other than f4." The app's custom-graph canvas *is* that flow.)

### 2.2 Quant agent

| Field | Value |
|---|---|
| `id` | `quant` |
| `display_name` | "Quantitative / Valuation" |
| `description` | "LLM coach over the DCF/Comps/Comparator trio. Interprets the quant tools' output into a fair-value range." |
| `node_type` | `agent` |
| `source` | `library` |
| `default_model` | `anthropic/claude-sonnet-4-5` (paid — quant interpretation benefits from frontier reasoning) |
| `system_prompt_ref` | `docs/prompts/library/quant/system-prompt.md` |
| `connectors_consumed` | `["quant_dcf", "quant_comps", "quant_comparator"]` |
| `inputs` | `["envelope"]` |
| `outputs` | `["envelope"]` (with `valuation` section added) |
| `accent_color` | `#1abc9c` (teal-green) |

**What it does:** Calls the three quant connectors (DCF, Comps, Comparator — already in `docs/runtime/tools/`) on the ticker, receives their structured output, and produces a `valuation` section: a fair-value range with methodology notes, sensitivity to key assumptions, and a comparison of the three methods' outputs. The section flows to downstream agents.

**Gate passed:** Distinct data/tool surface — the three quant connectors exist as non-LLM tools, but interpreting their output into a defensible valuation range requires LLM coaching. (The `quant-lead` from `docs/DEFERRED.md` — gate was "Re-hire if f6 (thematic screen) materializes." The app's custom canvas subsumes f6.)

### 2.3 Macro agent

| Field | Value |
|---|---|
| `id` | `macro` |
| `display_name` | "Macro / Rates / Regime" |
| `description` | "Top-down view — interest-rate sensitivity, sector-vs-beta, regime classification. Consumes FRED + market_data." |
| `node_type` | `agent` |
| `source` | `library` |
| `default_model` | `ollama/llama3.3:70b` |
| `system_prompt_ref` | `docs/prompts/library/macro/system-prompt.md` |
| `connectors_consumed` | `["market_data"]` (FRED is keyed separately) |
| `inputs` | `["envelope"]` |
| `outputs` | `["envelope"]` (with `macro_context` section added) |
| `accent_color` | `#e67e22` (orange) |

**What it does:** Reads FRED macro data (rates, money supply, if a FRED key is configured) + `market_data` for the ticker, and produces a `macro_context` section: current rate regime, the ticker's beta to the sector and to the market, interest-rate sensitivity, and a regime classification (risk-on / risk-off / transition). The section flows to downstream agents.

**Gate passed:** Distinct data/tool surface — FRED macro data is a different source than what the 5 built-ins consume. (The `macro-lead` from `docs/DEFERRED.md` — gate was "Re-hire if f5 or f8 needs a dedicated macro voice." The app's custom canvas lets a user *add* a macro voice to any graph.)

### 2.4 Flow-and-transcript agent

| Field | Value |
|---|---|
| `id` | `flow_and_transcript` |
| `display_name` | "Insider Flow + Earnings Transcript" |
| `description` | "Insider buying/selling patterns + earnings-call tone/forward-guide shifts. Pairs the two non-LLM connectors with an LLM interpreter." |
| `node_type` | `agent` |
| `source` | `library` |
| `default_model` | `ollama/llama3.3:70b` |
| `system_prompt_ref` | `docs/prompts/library/flow-and-transcript/system-prompt.md` |
| `connectors_consumed` | `["insider", "transcripts"]` |
| `inputs` | `["envelope"]` |
| `outputs` | `["envelope"]` (with `flow_and_transcript` section added) |
| `accent_color` | `#3498db` (blue) |

**What it does:** Calls the `insider` connector (OpenInsider data — recent cluster trades, 10b5-1 plan changes) + the `transcripts` connector (recent earnings-call transcripts), and produces a `flow_and_transcript` section: insider sentiment (net buy/sell, cluster activity), transcript tone shift vs prior Q, forward-guide changes, and any contradictions between the two. The section flows to downstream agents.

**Gate passed:** Distinct data/tool surface — insider flow + transcript deep-read is a combined surface none of the 5 built-ins own. (A hybrid of the `options-flow-insider` and `sec-filings` deferred specialists from `docs/DEFERRED.md`.)

### 2.5 Research-forcer (directive injector)

| Field | Value |
|---|---|
| `id` | `research_forcer` |
| `display_name` | "Research Forcer" |
| `description` | "A directive-injector: when wired between an upstream and downstream agent, forces the upstream to dig deeper (find more primary sources, expand sub-claims) before passing the envelope downstream." |
| `node_type` | `research_forcer` (special — not an agent) |
| `source` | `library` |
| `default_model` | (none — doesn't run a model) |
| `system_prompt_ref` | (none — uses a `directive_template`) |
| `connectors_consumed` | `[]` |
| `inputs` | `["edge"]` (attached to an edge, not a node slot) |
| `outputs` | `["edge"]` |
| `accent_color` | `#f1c40f` (yellow) |
| `config` | `{ "depth_budget": 1, "directive_template": "Find {N} more primary sources for each sub-claim in section '{section}'." }` |

**What it does:** See [`PROTOCOL.md`](PROTOCOL.md) §1.2 and [`ROADMAP.md`](ROADMAP.md) Phase 4. On Run, when the upstream agent of the forcer's edge finishes, the forcer inspects its envelope, generates a "dig deeper" directive from its `directive_template`, and re-runs the upstream agent with the directive appended to its brief. The re-run's envelope is what flows downstream. Caps at `depth_budget` extra passes (max 3).

**Gate passed:** Distinct control-flow role — it gates and transforms the pipeline rather than producing analysis. A genuinely novel node type, not a deferred prompt.

---

## 3. The JSON schema for a catalog entry

Each catalog entry is a file `app/agent-library/<id>.json`:

```json
{
  "schema_version": 1,
  "id": "technical",
  "display_name": "Technical Analysis",
  "description": "Deep-dive on price action, support/resistance, volume profile, momentum. Consumes market_data output.",
  "node_type": "agent",
  "source": "library",
  "default_model": "ollama/llama3.3:70b",
  "system_prompt_ref": "docs/prompts/library/technical/system-prompt.md",
  "connectors_consumed": ["market_data"],
  "inputs": ["envelope"],
  "outputs": ["envelope"],
  "accent_color": "#9b59b6",
  "config_schema": {},
  "version": "0.1.0",
  "author": "labourious maintainers"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | integer | yes | Currently `1`. |
| `id` | string | yes | Unique. Used as the React Flow node `agent_id` when the node is on the canvas. |
| `display_name` | string | yes | Shown in the library panel + node header. |
| `description` | string | yes | One-line description. Shown in the library panel + idle node body. |
| `node_type` | `"agent"` \| `"research_forcer"` | yes | Discriminator. |
| `source` | `"library"` | yes | Always `library` for catalog entries (the 5 built-ins are `source: "builtin"` and not in this folder). |
| `default_model` | string \| null | yes for `agent` | The model the node uses by default. The user can override per-node. |
| `system_prompt_ref` | string | yes for `agent` | Path (relative to repo root) to the prompt file. Must be under `docs/prompts/library/`. |
| `connectors_consumed` | array of strings | yes | Tool ids the agent will call. Must exist in `docs/runtime/connectors_catalog.py`. |
| `inputs` / `outputs` | array of strings | yes | What the node accepts/produces. Currently always `["envelope"]` for agents, `["edge"]` for the forcer. |
| `accent_color` | string (hex) | yes | Node accent color. |
| `config_schema` | object | no | JSON schema for per-node config fields (Phase 4+). Empty for v1. |
| `version` | string | yes | Catalog entry version (semver). |
| `author` | string | yes | For attribution in shared flows. |

### 3.1 Validation rules for catalog entries

1. `id` must be unique across the catalog.
2. `system_prompt_ref` must point to a file that exists and conforms to `docs/prompts/V2-PROMPT-STANDARD.md` (the shared envelope schema).
3. Every `connectors_consumed` entry must exist in `docs/runtime/connectors_catalog.py` (the single source of truth for tools, drift-free).
4. `accent_color` must be a valid hex color (the app enforces a hex-only palette for platform parity, per `docs/frontend/keys.py`).
5. The catalog is loaded at app startup; a malformed entry is skipped with a console warning (not a crash).

---

## 4. The pluggable-agents policy (carried from `docs/DEFERRED.md`)

This catalog is the long-promised home for pluggable agents. The policy from `docs/DEFERRED.md` §"Pluggable agents must pass one of two tests" applies unchanged:

- **Sector-specific knowledge → knowledge pack, not a node.** A "semiconductor analyst" node is wrong; a semiconductor knowledge pack loaded into senior-analyst (via `docs/runtime/packs.py`, already shipped) is right. The library does **not** ship sector variants.
- **Persona variants → no.** No Burry/Buffett/Taleb personas (per `docs/RESTRUCTURING.md` — retired permanently).
- **Asset-class variants → no.** No "crypto analyst" node (per `docs/CANNOT-DO.md` §6 — crypto is out of scope).

What the library **does** ship: focused deep-dive agents that pass the distinct-data-or-control-flow gate (technical, quant, macro, flow-and-transcript, research-forcer). What the library **may** ship in future versions, if a gate opens:

- **Sentiment** (deferred `sentiment-lead`) — gate: news tool layer matures past keyword mentions to need NL tone-judgment.
- **Strategy / allocation** (deferred `strategy-lead`) — gate: a flow's output becomes allocation advice (requires revising `docs/CANNOT-DO.md` §2's RIA boundary — unlikely).
- **Critique / base-rate** (deferred `critique-lead`) — gate: a flow's disagreements grow past what devil's-advocate + senior-analyst can resolve.

Each of these would land as a new JSON file under `app/agent-library/` + a new prompt under `docs/prompts/library/<agent>/system-prompt.md` — the same pattern the v1 catalog establishes.

---

## 5. How the app loads the catalog

1. On startup, the app reads every `*.json` file under `app/agent-library/` (or, in a bundled build, from a bundled `agent-library/` resource directory).
2. Each file is parsed and validated per §3.1. Malformed entries are skipped with a console warning.
3. Valid entries are sorted by `display_name` and rendered in the left panel's "Agent Library" section below the 5 built-ins.
4. A "Refresh library" button re-reads the folder (useful during development — no app restart needed for catalog changes).
5. When a user drags a library entry onto the canvas, a new node is created with `source: "library"` and `library_ref: <id>`, per [`PROTOCOL.md`](PROTOCOL.md) §1.1.

---

## 6. What this doc doesn't say

- The visual rendering of library nodes (header, body, footer) — see [`SPEC.md`](SPEC.md) §4.1.
- The WS bridge contract for running a graph that contains library nodes — see [`PROTOCOL.md`](PROTOCOL.md).
- The build phase when the library ships — Phase 3 (technical, quant, macro, flow-and-transcript) and Phase 4 (research-forcer) per [`ROADMAP.md`](ROADMAP.md).
