# SCREENS — state machine of the TUI

> What the TUI looks like in each named state, and what triggers a transition between states.

The TUI is **a chat app with two modal screens**: Settings, History. The day-to-day experience is one screen — the chat screen — in three sub-states (idle, running, finished). Below: each named screen, in each sub-state, with a state-transition matrix.

## Screen 1 — Chat (default screen)

This is what the user lands in 99% of the time. Sub-states are keyed off the running flow.

### 1.a — Chat / Idle

**What it looks like:**
- Header: green dot · flow defaults shown
- Sidebar: activity panel says `Idle · awaiting input`
- Chat pane: empty (or last run's transcript, scrolled to bottom)
- Input: empty, focused, blinking cursor
- Footer: helper text "Type a prompt and press Enter"

**Transitions to:**
- 1.b (Running) — on `Enter` pressed in input + valid flow
- 2 (Settings) — on `s` or `/settings`
- 3 (History) — on `h` or `/history`

### 1.b — Chat / Running

**What it looks like:**
- Sidebar: rows tick from `queued` → `running` (with spinner) → `done` as agents complete; cost widget updates per-call
- Chat pane: streaming bubbles appear top-down as agents finish; the in-progress bubble shows the live agent's name and a `▌ waiting…` placeholder
- Input: disabled (greyed out)
- Footer: shows current flow + depth + hybrid routing summary

**Transitions to:**
- 1.c (Finished) — when `agent_finished` event for `final-report` arrives, OR a fatal error leaves the flow with no output
- 2 / 3 (modals) — modal screens overlay; underlying chat state stays at 1.b (Reactive: the runtime keeps running; modal comes off when user dismisses)

**On `q`/`Ctrl+C` while running:** show "Cancel current flow? `[Y/N]`" — kills the run by interrupting the underlying iterator; partial draft remains in the chat pane with red `[canceled]` marker on every bubble.

### 1.c — Chat / Finished

**What it looks like:**
- Sidebar: all 5 rows show `done` with wallclock + token counts
- Chat pane: complete memo rendered with the 6-section template (Bottom line / Bull / Bear / What an attacker would say / Next three questions / Citations). Citations are chips. If a prior thesis exists, a collapsible `Diff` widget sits just before the final memo.
- Input: enabled again, focused with a blinking cursor
- Footer: shows the cost total + "Press Ctrl+R to re-run."

**Transitions to:**
- 1.b (Running) — on `Ctrl+R` (re-run the last prompt) or `Enter` with a new prompt
- 1.a (Idle) — on `Ctrl+L` (clear chat)
- 2 / 3 (modals)

### 1.d — Chat / Error (sub-state of Finished)

A variation of 1.c. The flow ended on a fatal error (one agent failed irrecoverably; the orchestrator aborted).

**What it looks like:**
- Top of the chat pane: red error card `[Flow aborted: senior-analyst returned malformed envelope; not JSON — see logs/cost.json]`
- Sidebar: all rows show their actual state; the failing row shows red `✗`
- Input: enabled
- Footer: "Press `Ctrl+r` to retry."

## Screen 2 — Settings (modal)

**Trigger:** `s` key (when input not focused), or `/settings` typed in input.

**What it looks like:**
- A modal centered on the chat screen (Textual `ModalScreen` with a dim backdrop).
- Form layout: 6 sections (Providers / Default Model / Per-agent overrides / Connectors / Hybrid routing / Defaults).
- Per field, an `Input` or `Select` widget with the current value pre-filled from `~/.labourious/config.json`.
- Bottom row: `[Save]` `[Cancel]` `[Reset to defaults]`.
- `[Esc]` also closes (treated as Cancel).

**On Save:**
- Write the JSON file (the runtime re-reads it on next prompt).
- Show a toast `✓ Saved`.
- Close the modal; chat screen comes back unchanged.

**On Reset to defaults:**
- Pre-fill all fields with the defaults documented in [`PROTOCOL.md`](PROTOCOL.md) Appendix A. User still has to `Save` to commit.

## Screen 3 — History (modal)

**Trigger:** `h` key or `/history`.

**What it looks like:**
- Modal with two panes.
- Left pane: ticker list (sorted by recency), with a version-count badge.
- Right pane: the selected ticker's thesis register entries, newest first; updates below; catalysts below.
- Top of right pane: `f4 (earnings review)` style next-questions indicator (resolved questions crossed out, unresolved highlighted).
- Closing: `Esc` or click outside.

## Transitions matrix

| From | Event | To |
|------|-------|----|
| 1.a | Enter pressed | 1.b |
| 1.a | Ctrl+L | 1.a (clear) |
| 1.a | `s` / `/settings` | 2 (over) |
| 1.a | `h` / `/history` | 3 (over) |
| 1.a | `q` / Ctrl+C | quit |
| 1.b | agent_finished(final-report) | 1.c |
| 1.b | any fatal abort | 1.d |
| 1.b | Ctrl+C | 1.d (canceled) |
| 1.b | `s`/`h` | 2 or 3 over 1.b |
| 1.c | Enter with new prompt | 1.b |
| 1.c | Ctrl+R | 1.b |
| 1.c | Ctrl+L | 1.a |
| 1.c | `s`/`h` | 2 or 3 over 1.c |
| 1.c | `q` | quit |
| 1.d | Ctrl+R retry | 1.b |
| 1.d | Ctrl+L clear | 1.a |
| 2 | Save | 1.?.(saved) — return to whatever chat sub-state was active |
| 2 | Cancel / Esc | 1.?. — return to prior chat sub-state |
| 3 | Esc / click outside | 1.?. — return to prior chat sub-state |

## Welcome screen (transient)

On first launch (no `~/.labourious/config.json`), the chat screen opens with a one-line welcome card:

```
▌  Welcome to Labourious. Press [s] to set a provider key, then `analyze NVDA` to try the first preset.
```

This is not a separate screen — it's 1.a Idle + an extra widget. The card disappears once the user submits their first valid prompt.

## What this file doesn't say

- Why each sub-state exists (that's `SPEC.md`).
- What events cause transitions (`PROTOCOL.md`).
- Code structure (`IMPLEMENTATION.md`).
