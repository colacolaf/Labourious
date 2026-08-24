# CANNOT-DO — app-specific scope boundaries

> This file is the credibility boundary for the app. Every claim in the rest of `app/docs/` should be read against this list *and* against `docs/CANNOT-DO.md`. If a feature sounds impressive but conflicts with what's below, **this file wins**. If it conflicts with `docs/CANNOT-DO.md`, **that file wins**.

The app inherits every boundary in `docs/CANNOT-DO.md` (no trading, no RIA, no custody of user data on a Labourious server, no replacing human judgment, no ESG, no crypto, no real-time rebalancing, no prohibited-category recommendations). This file adds the boundaries specific to the desktop app surface. The split:

1. **Today cannot** — the app doesn't currently do this. Might later under named conditions.
2. **Will not in this app** — out of scope permanently for the app; a different surface serves it.
3. **Will always be lossy** — hard limits that don't go away with engineering.

---

## Today cannot (but might)

### 1. Cloud sync of graphs or theses

**Today:** graphs save as `.labourious-flow.json` to `~/.labourious/flows/`; theses live in `~/.labourious/theses.db` (shared with the TUI). Both are local-only.

**Why it can't:** Cloud sync implies a Labourious-hosted relay, which bumps against `docs/CANNOT-DO.md` §3 ("No Labourious backend, period"). Building a relay + auth + encryption is a different product.

**Milestone to unlock:** A user explicitly opts into an encrypted cloud sync AND `docs/CANNOT-DO.md` §3 is revised to permit a sync-relay (relay only, never the secrets or runtime). Until then, file-based sharing (export `.labourious-flow.json`, send via any channel) is the path.

### 2. Mobile app

**Today:** desktop only (macOS + Windows).

**Why it can't:** A mobile app is a different build target — different UI density, different interaction model, different distribution. The app v1 is a desktop studio; mobile would be a sibling to *this*, not a port.

**Milestone to unlock:** The desktop app ships, reaches real adoption, and a mobile use-case is articulated that the desktop app can't serve (e.g. "check my thesis register on the go"). Then a mobile app earns its own docs tree. Until then, mobile is `docs/USER-JOBS.md`'s no-build list, unchanged.

### 3. Real-time graph collaboration (multi-user editing)

**Today:** single-user. One user edits one canvas at a time.

**Why it can't:** Multi-user editing requires a backend with conflict resolution, presence, and permissions — the same surface area `docs/CANNOT-DO.md` §7 defers. The thesis register is per-user SQLite.

**Milestone to unlock:** Never in this app. Multi-user is a v3+ product surface, not a feature.

### 4. A Labourious-hosted agent marketplace

**Today:** sharing is file-based — export a `.labourious-flow.json`, send it via GitHub gist / Discord / email, the recipient imports it.

**Why it can't:** A hosted marketplace requires accounts, moderation, and a Labourious server — all of which `docs/CANNOT-DO.md` §3 forbids.

**Milestone to unlock:** A self-hosted registry (e.g. a GitHub repo of curated flows the app can browse) is plausible for v2. A Labourious-hosted one is not.

### 5. Auto-update of the app binary

**Today:** updates are manual — download a new `.dmg` / `.msi`.

**Why it can't:** Auto-update implies a Labourious-hosted update server (Tauri's updater plugin needs one). That's a backend. The app's runtime + prompts are shared with the TUI, so updates must be coordinated across both surfaces — an auto-updater that bumps the app without bumping the shared `docs/` would cause drift.

**Milestone to unlock:** v2+, once a coordinated-release process across TUI + app + prompts is in place.

### 6. Custom agent nodes from user-written prompts (forkability)

**Today:** the 5 built-in agents are fixed; the agent-library catalog (Phase 3) ships a curated set (technical, quant, macro, flow-and-transcript). Users cannot *create* a new agent node from scratch in the app.

**Why it can't:** Forkability requires a prompt editor UI + envelope-schema validator + a way to test the forked agent in isolation. That's real surface area and real risk (a user-written prompt that doesn't conform to the envelope schema breaks the graph compiler).

**Milestone to unlock:** Phase 3 ships the curated library first. Forkability is a Phase 6+ conversation if the curated library proves the agent-node pattern works and users want more. See [`ROADMAP.md`](ROADMAP.md) — forkability was explicitly deferred ("Start fixed, forkability later").

### 7. A polished marketing site / landing page

**Today:** this docs tree + the README.

**Why it can't:** A marketing site is downstream of a shipped, adopted app. Building one before adoption is putting the cart before the horse.

**Milestone to unlock:** The app ships, real users use it, and growth demands a public face. Then a site earns its existence.

---

## Will not (permanently)

These are decisions, not limitations. The cost of doing them is greater than the value.

### 1. Becoming a hosted SaaS

The app is local-first, period. The runtime runs on the user's machine (bundled sidecar). The thesis register, config, and graphs live in `~/.labourious/`. **No Labourious-hosted runtime, ever.** A hosted version is a different product, not a version of this one. See `docs/CANNOT-DO.md` §3.

### 2. Storing API keys on a Labourious server

Provider keys (Anthropic, OpenAI, etc.) live in the OS keychain on the user's machine (macOS Keychain / Windows Credential Manager), the same place the TUI stores them. **No Labourious server ever sees a key.** The bundled sidecar reads them via `keyring`, same as the TUI.

### 3. Replacing the TUI

The TUI is the v1 surface and stays maintained. The app is the v2 surface, a sibling. **The app does not deprecate the TUI.** Users who prefer terminals keep the TUI; users who prefer a visual surface use the app. Both consume the same runtime.

### 4. Shipping a different runtime

The runtime stays in `docs/runtime/runtime.py`. The app's bridge wraps `run_flow_stream()` (and, from Phase 2, `run_custom_flow_stream()`). **No app-forked runtime.** Any runtime improvement benefits both surfaces; any runtime regression breaks both. This is the single-source-of-truth guarantee.

### 5. Forking the prompts

The 5 built-in prompts stay in `docs/prompts/`. Agent-library variants (Phase 3) live in `app/agent-library/` as JSON catalogs that *reference* prompt files under `docs/prompts/library/<agent>/system-prompt.md` — new prompts, added to the shared tree, not duplicated into an app-private tree. **One prompt library.**

### 6. Trading execution, order placement, broker integration

Inherited from `docs/CANNOT-DO.md` §8. The app provides analysis, not custody. The "Action" job surfaces a bottom line + flip trigger, never a "Buy" button.

### 7. Becoming a registered investment advisor

Inherited from `docs/CANNOT-DO.md` §2. The app surfaces *analysis*, not *advice*. No "you should buy X" — only "the bull case is X, the bear case is Y, the bottom line is Z conviction."

### 8. Real-time portfolio rebalancing or portfolio management UI

Inherited from `docs/CANNOT-DO.md` §7. The user has a broker; we provide analysis.

---

## Will always be lossy

These limits are physics, not engineering decisions.

### 1. Webview rendering differences across platforms

Tauri uses the OS webview (WebKit on macOS, WebView2 on Windows). They are not bit-identical. CSS edge cases, JS API availability, and font rendering will differ slightly across platforms. Mitigation: target the intersection, test on both per release. **This doesn't go away.**

### 2. Bundled-Python binary size

A self-contained `.app` / `.exe` with bundled Python + all deps ships at ~40–80 MB (portable Python + site-packages) or ~15–25 MB (PyOxidizer-embedded). Either is larger than the TUI's `pip install` footprint. The trade-off is zero-Python-literacy install vs. binary size. **This doesn't go away** — Python runtimes don't shrink.

### 3. Sidecar startup latency

The bundled Python sidecar takes 1–3 seconds to start on first launch (Python interpreter init + imports + WS server bind). The app shows a "Starting runtime…" splash during this window. **This doesn't go away** — Python cold-start is real.

### 4. Long-context degradation (inherited)

Inherited from `docs/CANNOT-DO.md` "Will always be lossy" §1. Even frontier models lose accuracy on inputs over ~50k tokens. The app's graph compiler could theoretically produce very long briefs if the user wires many agents; the runtime's prompt-caching strategy mitigates but doesn't eliminate this.

### 5. Free-model quality gap on adversarial reasoning (inherited)

Inherited from `docs/CANNOT-DO.md` "Will always be lossy" §2. The 70B-class free models are 50–85% as good as Sonnet 4.5 on adversarial reasoning. The app's per-node model routing lets the user route the final-report (or any agent) to a paid model, but the gap on free-only runs is real.

### 6. Model hallucination on small numeric queries (inherited)

Inherited from `docs/CANNOT-DO.md` "Will always be lossy" §5. The eval suite (`docs/runtime/evals/test_hallucination.py`) is what keeps this honest. The app doesn't change this — it surfaces the same citations the TUI does.

---

## How to read the rest of the docs against this file

The "n8n-style flow builder", "agent library", "research-forcer" claims in [`CONTEXT.md`](CONTEXT.md) and the 5 jobs in [`USER-JOBS.md`](USER-JOBS.md) all assume this file exists. If a user asks "can the app do X?", the answer is:

- "yes, today" → check whether it conflicts with any *will not* line above or in `docs/CANNOT-DO.md`.
- "no, today" → check whether the milestone above is plausible.
- "no, ever" → direct them to the *will not* reasoning.

This file is the most important doc in `app/docs/` for credibility. Update it whenever a milestone is reached or a boundary is revised.
