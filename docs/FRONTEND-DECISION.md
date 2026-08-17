# FRONTEND-DECISION — what the user actually chats with

> The decision: **a Python TUI (Textual v4 + Rich)** — not a browser, not Electron, not a CLI stdout. Local-first, single dependency (`pip install textual rich`), streaming Markdown output, and a Claude-Code-style chat feel.

## The constraint set (from prior docs)

The work done before this decision constrained the choice materially.

| Constraint | Source | Implication |
|------------|--------|-------------|
| Local-first, no Labourious backend | [`CANNOT-DO.md`](CANNOT-DO.md) | Hosted web app = strictly out. BYOK, on the user's machine, period. |
| 5 user jobs ranked: trust, action, speed, defensibility, comparison | [`USER-JOBS.md`](USER-JOBS.md) | The chat surface must show *evidence* (citations, sources, activity) — not just answers. |
| Runtime is already Python | [`runtime/runtime.py`](../runtime/runtime.py) | A Python-native frontend eliminates an inter-language bridge. |
| 17 free-model-adapter lines of code is the entire LLM layer | [`runtime/adapters/`](../runtime/adapters/) | Adding a Node/Electron client would duplicate state and force IPC. |
| "Simplicity is best" | user instruction | Minimum surface area that hits the jobs. |
| "Not in the browser" | user instruction | Tauri (which wraps HTML in a webview) satisfies the letter but not the spirit. |
| "Advanced chat feel" | user instruction | Bubbles + streaming + sidebar — not one finished dump. |

## Options considered

| Option | Stack | Pros | Cons | Verdict |
|--------|-------|------|------|---------|
| **A. Local web app** | Vite/React or SvelteKit + a Python backend | Easy to make pretty; hot-reload; familiar DevX | Renders in a Chromium tab — *that* is what the user said no to. Plus a Node-build step. | **Rejected** |
| **B. Desktop wrapper (Tauri)** | Rust shell wrapping HTML/JS | Install-able, real .app/.exe; lighter than Electron (~5MB not ~150MB) | Still wraps a webview under the hood; adds Rust build step; two-language codebase. | **Rejected** |
| **C. Rich CLI to stdout** | Just `python runtime.py ... > memo.md` | Trivial; nothing extra to build | No "chat feel" — the memo just appears all at once. | **Rejected** |
| **D. Rich CLI / TUI (Textual + Rich)** | Python TUI with widgets | Single dependency (Python); Claude-Code-style chat with bubbles + sidebar; v4 (Jul 2025) has streaming Markdown natively; no browser; no build step | Terminal aesthetic — looks like a developer tool by design | **Chosen** |
| E. Native desktop (Electron) | Electron + Node + React | Polished, install-able | Heavy; Chromium runtime; contradicts user "not in the browser" | **Rejected (was original plan)** |

The original CONTEXT.md framing was an "Electron desktop app, opens like Chrome." That is **superseded** by this decision; see [`ARCHITECTURE.md`](ARCHITECTURE.md) §Components for the updated framing. Electron is *not* the path.

## Why Textual specifically

Textual (the Python TUI framework by Will McGugan / Textualize) is the right fit because:

1. **v4 (Jul 2025) ships streaming Markdown as the signature feature** — the user sees the agent's output as it's generated, not when it's done. ([Simon Willison's notes](https://simonwillison.net/2025/Jul/22/textual-v4/) · [Textual blog](https://textual.textualize.io/blog/2024/09/15/anatomy-of-a-textual-user-interface/)).
2. **It's a single Python framework** — same language as the runtime. The chat app imports `runtime.py` directly. No subprocess bridge, no JSON-over-HTTP bridge, no duplicated state.
3. **Widgets map cleanly to our surface**: `MarkdownViewer` for the memo body, `Container` for the activity sidebar, `Input` for the prompt line, `ModalScreen` for the settings editor.
4. **CSS-based styling** for visual hierarchy (citation chips, sidebar grouping, streaming animation).
5. **Already used in serious dev tools** — uv, ruff, etc. Confidence in the project's longevity.
6. **Cost**: `~5 MB` of dependency. The runtime is already Python; adding `textual` and `rich` is two `pip install` commands. Compared to Electron (~150 MB Chromium + Node + native build), the savings are an order of magnitude.

Alternative I considered seriously: **prompt_toolkit**, which is older and lighter, but lacks the layout model and the streaming-Markdown widgets that Textual v4 ships. Textual wins on chat-app ergonomics even with the larger dependency footprint.

## What the TUI does (and does not) do

### Does

- Render a chat-style conversation: user prompt on the right, agent output on the left.
- Stream each of the 5 agent calls live as they complete.
- Show a left sidebar with per-agent status (queued / running / done / wallclock) and the connectivity state of each adapter.
- Inline-render the final memo's `bull_case`, `bear_case`, `what_an_attacker_would_say`, `next_three_questions`, and `citations_used`.
- Reveal a citation chip on hover/click → show the underlying URL + retrieved snippet.
- Show "what changed" if there's a prior thesis in the register for the ticker — side-by-side diff.
- Open a Settings modal screen for editing `~/.labourious/config.json`.
- Open a History modal for browsing prior theses from `docs/runtime/thesis_register/theses.db`.

### Does not

- Render charts. We deliver text memos per [`USER-JOBS.md`](USER-JOBS.md) — no chart library.
- Take actions on the user's behalf (no trade execution, no notifications).
- Run on a phone. Local-first, on a laptop.
- Multi-user. Single-user by design.

## Cost-of-add vs. cost-of-leave

| Choice | What you give up | What you gain |
|--------|------------------|---------------|
| **TUI now** | "Polished consumer-grade" aesthetic. No real logo / marketing site. | Ship in days, not weeks. No Chromium. Powers users, the Wharton teams, and junior analysts all fit a TUI aesthetic. |
| Local web app later | — | Polished UI; mobile; charts. |
| Reject TUI entirely | — | Same as TUI but loses streaming + sidebar advantages. |

The decision is **TUI for v1**, with a Tauri/local-web-app migration as a v2+ option **if shipped adoption justifies it.** Migration cost: moderate — the runtime stays; only the chat surface changes.

## What remains open

Three small open questions:

1. **Cost / connection display** — the sidebar currently shows per-agent wallclock. Do we surface cost per agent too? Recommendation: **yes** — even all-free runs benefit from "this used 4k tokens, 0 dollars" visible feedback.
2. **Whether `devils-advocate`'s output is visible by default** — arguments both ways. My recommendation: **collapsed by default**, expandable. The bull case is what the user asks for; the bear case is what they need to verify but doesn't have to live in their face.
3. **Whether the thesis-register `diff` view is a separate screen or inline** — my recommendation: **inline when there's a prior**, surfaces as a collapsible section between the agent's output and the final memo. Less screen churn.

These three are small. They go to the spec doc, not back here.

## File plan (preview)

Six docs total: this decision, plus five in `docs/frontend/`:

- `docs/frontend/README.md` — directory's role.
- `docs/frontend/SPEC.md` — the TUI components, layout, screen behavior.
- `docs/frontend/SCREENS.md` — state machine + screen shapes.
- `docs/frontend/PROTOCOL.md` — runtime → TUI event protocol.
- `docs/frontend/IMPLEMENTATION.md` — file plan with line budgets and runtime.py changes.

Update as a result of this decision:
- [`ARCHITECTURE.md`](ARCHITECTURE.md) §Components — replace "Electron app" framing with "TUI over the runtime."
- [`ROADMAP.md`](ROADMAP.md) — add "TUI v1" between tool adapters and thesis register.
- [`CHANGELOG.md`](../CHANGELOG.md) — note the decision.
