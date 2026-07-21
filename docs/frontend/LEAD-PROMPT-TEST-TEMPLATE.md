# Lead Agent System Prompt — Test Template

> Paste this at the end of any lead agent system prompt to stress-test it.
> Replace `[LEAD]`, `[ROOM]`, `[TICKER]`, and agent names with the actual lead's details.

---

## TEST: Simulated PM Briefing

You receive the following briefing from the Portfolio Manager. Process it and route tasks to your room's agents.

```
FROM: Portfolio Manager
TO: [LEAD NAME] — [ROOM NAME]

SITUATION:
User wants a read on [TICKER]. Currently holding a 3% position at $[COST BASIS],
up [X]%. User is considering adding to the position. Asking: "Should I add to
my [TICKER] position or trim?" Decision: buy more, hold, or trim.

PORTFOLIO CONTEXT:
[TICKER] is 3% of portfolio. Sector exposure is at [X]% (target: [Y]%).
Adding would push sector to [Z]%. The position was initiated [N] months ago.
Portfolio is up [X]% YTD. Risk budget is at [X]% of max drawdown allocation.

WHAT I'M ASKING EVERYONE:
- [List other rooms being briefed — at least 3-4]
- Include what each room is tasked with

RELEVANT HISTORY:
Knowledge Graph shows last analysis was [N] weeks ago. At that time:
[DCF range / technical setup / macro context from last analysis].
Verdict was [BUY/HOLD/SELL]. Since then, price moved from $[X] to $[Y].
Key change: [what changed — earnings, macro, sentiment shift, etc.]

YOUR SPECIFIC TASK:
[Specific ask for THIS lead's room. 2-3 precise questions.
Example: "DCF with bear/base/bull cases. Competitive moat durability.
Management quality assessment. Valuation relative to growth rate.
Conviction: High/Moderate-High/Mixed."]

URGENCY: Routine
```

---

## TEST: Simulated Agent Outputs

Your room's agents have returned the following outputs. Some are clean, some have issues.

### Agent 1: [Agent Name] — ✅ Clean Output

```
[Write a clean, well-formatted output from one of your room's agents.
Include: clear conclusion, supporting evidence, conviction level.
This one is correct — the lead should accept it as-is.]
```

### Agent 2: [Agent Name] — ⚠️ Internally Contradictory

```
[Write an output that contradicts itself.
Example: says the moat is widening in one paragraph, then says
competitive pressure is intensifying in the next paragraph.
The lead should catch this and send it back.]
```

### Agent 3: [Agent Name] — ⚠️ Stale Data

```
[Write an output that uses obviously stale or outdated data.
Example: references Q1 earnings when Q2 was already reported,
or uses a price from 3 months ago.
The lead should catch this and flag it.]
```

### Agent 4: [Agent Name] — ⚠️ No Conviction / Vague

```
[Write an output that hedges excessively, uses "maybe" and "perhaps,"
and refuses to take a position. No clear conclusion.
The lead should push back — either demand conviction or note the ambiguity.]
```

### Agent 5: [Agent Name] — ✅ Clean Output

```
[Write a second clean output, with a different perspective.
This one might partially conflict with Agent 1's conclusion,
creating a minor tension the lead needs to resolve.]
```

---

## TEST: Expected Behaviors Checklist

After processing the PM briefing and agent outputs, verify:

- [ ] **Parse:** Lead correctly extracted the PM's question, portfolio context, and specific task
- [ ] **Route:** Lead routed the right sub-tasks to the right agents (correctly matched asks to agents)
- [ ] **Quality check — Contradiction:** Lead caught Agent 2's internal contradiction and flagged it
- [ ] **Quality check — Stale data:** Lead caught Agent 3's stale data and flagged it
- [ ] **Quality check — Vagueness:** Lead pushed back on Agent 4's hedging or noted the lack of conviction
- [ ] **Synthesis:** Lead wove Agent 1 and Agent 5's clean outputs into a coherent view
- [ ] **Minor tension:** Lead handled the partial disagreement between Agent 1 and Agent 5 (either resolved it or surfaced it honestly)
- [ ] **Persona:** Lead's output sounds like [LEAD NAME], not a generic analyst
- [ ] **Format:** Lead's output follows the expected room-level synthesis format (not raw agent dumps)
- [ ] **Conviction:** Lead assigned an overall conviction level (High / Moderate-High / Mixed)
- [ ] **No hedging:** Lead avoided "maybe," "perhaps," "I think" (unless the lead's persona explicitly uses those)

---

## TEST: Expected Output Format

The lead should produce a room-level synthesis in this format:

```
FROM: [LEAD NAME] — [ROOM NAME]
TO: Portfolio Manager

EXECUTIVE SUMMARY:
[2-3 sentence conclusion. What the room found. What it means.
The dominant signal. Conviction level.]

AGENT FINDINGS:
- [Agent 1]: [1-2 line summary of key finding. Status: CLEAN]
- [Agent 2]: [Finding + flag: "Internal contradiction — [detail]. Sent back for re-run."]
- [Agent 3]: [Finding + flag: "Stale data — references Q1 when Q2 is available."]
- [Agent 4]: [Finding + flag: "No conviction — unable to form a view. Proceeding without."]
- [Agent 5]: [1-2 line summary of key finding. Status: CLEAN]

TENSIONS & UNKNOWNS:
[If agents partially disagreed: what's the disagreement, how significant is it,
does it need Critique room escalation or can you resolve it at room level?]

OVERALL CONVICTION: [High / Moderate-High / Mixed]
[Rationale in 1 sentence.]
```

---

## TEST: Edge Cases

After the main test, verify these edge cases:

1. **What if the PM sends a briefing with almost no RELEVANT HISTORY?**
   - Lead should proceed without it, not stall. Don't demand history if there is none.

2. **What if ALL agent outputs come back contradictory or bad?**
   - Lead should tell the PM: "Room cannot form a view. [Specific reasons]. Re-briefing the agents now."

3. **What if the URGENCY is "Immediate"?**
   - Lead should skip quality-checking non-critical issues. Accept minor imperfections. Speed over perfection.

4. **What if the PM's briefing includes a question outside the room's domain?**
   - Lead should flag it: "This ask includes [X] which is outside our room's scope. [Other room] should handle that."

5. **What if one agent doesn't respond at all?**
   - Lead should note the gap and proceed without them. Don't wait for a straggler.

---

## Instructions for Using This Template

1. Copy this entire section
2. Replace all `[PLACEHOLDERS]` with real values for the lead you're testing
3. Paste it at the end of the lead's `system-prompt.md` file
4. Run the prompt through an LLM and check the output against the Expected Behaviors Checklist
5. If the lead passes all 11 checklist items and 5 edge cases, the prompt is solid
6. Remove the test section from the final prompt before deploying
