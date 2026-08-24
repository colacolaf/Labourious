# USER-JOBS — the 5 jobs, applied to the app

> Every feature in the app maps to one of the 5 user jobs from `docs/USER-JOBS.md` — or it doesn't ship. The app's reason to exist is that it serves these jobs *better* or *differently* than the TUI on a desktop surface. If a candidate app feature moves zero of these, cut it.

This file is the app-specific lens on the 5 jobs. The jobs themselves are unchanged — `docs/USER-JOBS.md` is canonical. This file says how each job shapes the app, what the app does for it that the TUI can't, and the no-build list specific to the app.

The 5 jobs, in priority order (same as `docs/USER-JOBS.md`):

1. **Trust** — can I cite this output? Is it real or machine-made-up?
2. **Action** — what do I do with this? Buy / hold / sell / wait for what?
3. **Speed** — how fast can I get a defensible view on a new name?
4. **Defensibility** — when my PM/team/client asks "why?", does the report hold up?
5. **Comparison** — how does ticker A compare to B and C?

---

## Job 1 — Trust

> *"Can I trust this output? What's the source? Where could it be wrong?"*

This is the hardest job to deliver on a visual surface, and it's the app's strongest differentiator. The TUI shows citations as chips in a terminal bubble; the app can show them as interactive cards with the source URL, retrieved-at timestamp, confidence label, and a one-click "open in browser" / "view cached snippet" affordance — the same affordances the TUI's `o` / `y` / `v` / `n` keys provide, but discoverable.

**What this means in app product terms:**
- Every claim in the final memo (right panel) has a clickable citation card showing URL + retrieved-at + confidence.
- Citation cards have inline actions: open URL in browser, copy URL, view the 2 KB cached snippet (the same snippet cache the TUI uses under `~/.labourious/`).
- Stale snippets (past TTL) show a `⚠ ◫` badge, same as the TUI's chip.
- Contradictions between sources surface as a "Tensions" section, not averaged away.
- The system declares what it cannot answer — abstention is visible as a "Gaps" section in the right panel.
- Every run produces a "What an attacker would say" section, expandable.

**What the app does that the TUI can't:**
- Citation cards can expand inline to show the snippet excerpt without a separate pager (`less`). The TUI had to shell out to `less`; the app renders the excerpt in a modal.
- The canvas itself is evidence of trust — the user can *see* which agents ran, in what order, with what connectors, and trace any claim back to the agent + connector that produced it. The TUI shows this in a sidebar; the app shows it as the graph the user built.

**What this job forbids in the app:**
- No "trust score" widget. Trust is shown via citations + abstention, never a number.
- No hiding the bear case. Job 1 requires the bear case be as visible as the bull.

---

## Job 2 — Action

> *"What do I do with this? Buy, hold, sell? Wait for what?"*

**What this means in app product terms:**
- Every run's right panel ends with a "Bottom line" card: direction, conviction (1–5), and the price/event that would flip the view.
- The next catalyst date surfaces as a card ("next earnings 2026-11-20 — what we're watching").
- The bear case is in the same run as the bull — not buried in a tab.
- The system never says "I'd need more research" without also saying *which research and where* (a "Next three questions" card).

**What the app does that the TUI can't:**
- The "flip trigger" (the price/event that would change the view) can be a card with a one-click "watch this" affordance that writes a row to the thesis register's `catalysts` table. The TUI required the user to know to look in History; the app surfaces it inline.

**What this job forbids:**
- No trade execution button. The boundary from `docs/CANNOT-DO.md` §8 holds — "describe, don't prescribe."
- No "AI confidence percentage" — conviction is 1–5, earned, not invented.

---

## Job 3 — Speed

> *"How fast can I get a defensible view on a new ticker?"*

**What this means in app product terms:**
- Single-ticker custom graph: 5–10 minutes on free 70B-class models, <2 minutes on Sonnet (same as the TUI's f1).
- The canvas shows live status per node (queued / running / done / failed) — the user knows the system is alive, not hung.
- The right panel streams agent output as it arrives, not when the whole run finishes.
- Curated flow templates (Phase 5) let a user one-click load a proven graph instead of wiring from scratch — the "first draft in under 10 minutes" promise, but with one click instead of a slash command.

**What the app does that the TUI can't:**
- A user can save a custom graph as a personal template and re-run it on a new ticker with one click — the TUI's flows are fixed; the app's are user-defined. A junior analyst who builds a "semiconductor deep-dive" graph once can re-run it on NVDA, AMD, INTC, AVGO in sequence without re-wiring.
- Parallel branches visibly run concurrently — the user sees the speedup, not just experiences it.

**What this job forbids:**
- No "fast mode" that skips the devil's-advocate. Speed comes from parallelism + free models, not from cutting discipline.

---

## Job 4 — Defensibility

> *"When my PM/team/client asks 'why?', can I cite the memo? Does it hold up?"*

**What this means in app product terms:**
- Every assertion in the right panel's memo has a primary source URL beside it (rendered as a citation card, per Job 1).
- Every quantitative claim has a date stamp and the figure source (10-Q line, transcript page).
- The memo names its assumptions ("we assumed 22% gross margin continues") — visible as an "Assumptions" card.
- A "What an attacker would say" section is mandatory, expandable.

**What the app does that the TUI can't:**
- The canvas is itself a defensibility artifact — the user can export the graph alongside the memo, so a reviewer can see *which agents in what arrangement* produced the memo. The TUI's flows are implicit recipes; the app's are explicit, user-built, and exportable.
- The research-forcer (Phase 4) makes defensibility *controllable* — a user can force an agent to dig deeper on a specific sub-claim before the final report, producing a more defensible memo on demand. The TUI has no equivalent.

**What this job forbids:**
- No hiding the forensic-accounting output if it's clean. It must be on-record regardless (same as the TUI).

---

## Job 5 — Comparison

> *"How does ticker A compare to B and C? Which one wins?"*

This is the job the TUI handles worst and the app handles best. A terminal can show side-by-side text columns; a desktop app can show side-by-side ticker cards, ranked, with swipe/sort to re-rank.

**What this means in app product terms:**
- A user can build a "compare" graph: one senior-analyst per ticker (fan-out), then a final-report that synthesizes across tickers. The canvas expresses this naturally as fan-out + converge.
- The right panel renders the comparison as side-by-side cards: bottom line, conviction, bull, bear, key metric per ticker.
- The system produces a ranked pick, with confidence — not a menu of maybes.

**What the app does that the TUI can't:**
- Visual comparison: the canvas itself shows the parallel branches per ticker; the user can see at a glance that NVDA / AMD / INTC were analyzed in parallel with the same agents.
- Re-ranking: the user can drag ticker cards in the right panel to re-rank, and the underlying graph re-runs the final-report with the new ordering as a hint.

**What this job forbids:**
- No "they're different companies so hard to compare" cop-out. The system normalizes across sectors (same as the TUI's f2 promise).

---

## The no-build list (app-specific)

These features sound good on a desktop surface and **never move the 5 jobs above.** They are deferred, not deleted, with a reason.

| Feature | Why it's deferred |
|---------|-------------------|
| **A chart library (price charts, candlestick, etc.)** | Memos > dashboards for trust. Markdown tables are sufficient. A charting library is v3+ if ever — same call as the TUI's `docs/USER-JOBS.md` no-build list. |
| **Real-time streaming market data** | Same as TUI — free sources lag; paid sources cost $. Daily OHLCV covers 95% of cases. |
| **Trading execution / order placement** | Regulatory surface area, not analytical. `docs/CANNOT-DO.md` §8 holds. |
| **Portfolio management UI** | The user already has one. We provide analysis, not custody. |
| **Social sentiment scoring** | Sentiment is mostly noise. The system is skeptical of itself by design. |
| **Backtesting engine** | Requires a 10-year clean dataset we don't have and won't get free. Out of scope. |
| **A "wizard" / guided tour** | The canvas + curated templates (Phase 5) are the onboarding. A separate wizard duplicates what the library panel already does. |
| **Open chat over the memo** | Sounds great, UX disaster. Every follow-up burns context; every answer invents detail. Same call as the TUI's `docs/USER-JOBS.md`. |
| **Per-sector agents as separate nodes by default** | Sectors are knowledge packs, not agents (per `docs/DEFERRED.md`). The agent-library may ship *focused deep-dive* agents (technical, quant, macro) — but not 11 sector variants. |
| **Auto-update of the app binary** | v2+ concern. Updates should be coordinated across the TUI + app + prompts, which means manual for v1. |

---

## The litmus test for any new app feature

Every new feature must pass **all three** questions below. If it fails any, cut.

1. **Which of the 5 jobs above does this move?** If "all 5 weakly" — cut.
2. **Is this measurable?** If the answer is "we'll know if users complain" — cut. Define the metric before shipping.
3. **Does the canvas + runtime actually produce it?** If the bridge or graph-compiler doesn't support it yet, the feature is a hope, not a feature. Build the substrate first; the feature second.

---

## Where this list might be wrong

Three assumptions are worth pressure-testing as the app ships:

1. **The mixed retail + analyst audience is right.** If real adoption skews heavily retail, Job 5 (Comparison) and Job 3 (Speed) rise in rank; Job 4 (Defensibility) might drop slightly. Revise this file then.
2. **The canvas-first surface is right.** If users overwhelmingly prefer loading a curated template and never editing the graph, the canvas might be overkill — a "template picker + run" surface might serve the same jobs with less complexity. The Phase 1 prototype against a mock stream is where this falsifies.
3. **The research-forcer is worth its complexity.** If users never wire it in, it's a novelty. The Phase 4 acceptance criteria (≥ 2× cited sources) is the falsification gate.

The list is a hypothesis. The evals (`docs/runtime/evals/`) and shipping behavior are what falsify it.
