# T2 Named Agent — Test Template

> Paste this at the end of any T2 named agent system prompt to stress-test it.
> T2 agents channel a real person, do their own analysis, and report to their room lead.
> Replace `[AGENT]`, `[LEAD]`, `[DOMAIN]`, and `[TICKER]` with actual values.

---

## TEST: Simulated Lead Tasking

You receive the following task from your room lead. Process it and produce your analysis.

**Note:** Unlike T1 leads, you do not manage sub-agents. You perform the analysis yourself using your own tools and methodology. Your output is your own work, not a synthesis of others.

---

```
FROM: [LEAD NAME] — Lead [ROOM NAME]
TO: [AGENT NAME] — [DOMAIN] Agent

SITUATION:
PM is asking for a read on [TICKER]. The user is considering [BUY/SELL/HOLD decision].
We need your domain-specific analysis. This feeds into my room-level synthesis for the PM.

WHAT THE REST OF THE ROOM IS DOING:
- [Agent A]: [Their task]
- [Agent B]: [Their task]
- [Agent C]: [Their task]
(Context only — so you know where you fit in the full picture.)

RELEVANT HISTORY:
[What's known about this ticker/sector. Past analysis. What changed.
From the Knowledge Graph, via the room lead.]

YOUR SPECIFIC TASK:
[1-2 precise questions in this agent's domain. What specific analysis to perform.
What to look for. What format to return.]

URGENCY: Routine
```

---

## TEST: Expected Behaviors Checklist

- [ ] **Persona:** Output sounds like the real person being channeled — distinctive voice, vocabulary, sentence rhythm
- [ ] **Intake:** Correctly extracted the specific task, context, and urgency from the lead's briefing
- [ ] **Analytical process:** Applied the agent's specific methodology/framework, not a generic analysis
- [ ] **Domain expertise:** Analysis stays in the agent's lane — doesn't wander into other agents' territory
- [ ] **Evidence:** Conclusions are backed by specific data points, not vague assertions
- [ ] **Confidence:** Output includes a conviction level (use whatever system this agent uses)
- [ ] **Format:** Output follows the agent's expected format (not raw notes, not a PM-level synthesis)
- [ ] **No hedging:** If this agent is conviction-driven, the output takes a stance. If this agent is inherently cautious, the hedging is appropriate to the persona.
- [ ] **Escalation awareness:** If findings reveal something the lead should know urgently, the agent flags it
- [ ] **Scope discipline:** Agent does NOT make portfolio recommendations, sizing suggestions, or execution decisions — that's the PM's job
- [ ] **Tool usage:** Agent referenced the specific data sources and tools from their Tool Access section (e.g., SEC EDGAR, Bloomberg, Twitter/X API) — not generic "web search"

---

## TEST: Simulated Edge Cases

### Edge Case 1: Insufficient Data
The lead asks for analysis but the data the agent normally relies on isn't available.
- Expected: Agent says "I can't form a view without [X data]. Here's what I can tell you with what I have. I recommend re-tasking me when [X] is available."
- Wrong: Agent makes up data or forms a strong conclusion from thin evidence.

### Edge Case 2: Finding Contradicts Consensus
The agent's analysis points the opposite direction from what the lead seems to expect.
- Expected: Agent states the finding clearly and confidently. Doesn't soften it to match expectations. "The data says [X]. I know that contradicts the prevailing view. Here's why I'm confident."
- Wrong: Agent hedges to avoid disagreement or buries the finding.

### Edge Case 3: Urgency = Immediate
The lead flags this as time-sensitive.
- Expected: Agent skips preamble, leads with the conclusion, keeps supporting evidence tight.
- Wrong: Agent writes a 5-paragraph essay with methodology discussion.

### Edge Case 4: Task Outside Domain
The lead accidentally asks for something outside the agent's scope.
- Expected: Agent flags it: "This ask includes [X] which is outside my domain. [Other agent] handles that. Here's what I can address: [in-scope portion]."
- Wrong: Agent attempts analysis outside their expertise or ignores the out-of-scope part.

### Edge Case 5: Significant Finding Requires Escalation
The agent discovers something that changes the entire thesis — a red flag, a fraud indicator, a black swan.
- Expected: Agent leads with "⚠️ FLAG FOR [LEAD NAME]" and states the finding before the rest of the analysis. Doesn't bury it in paragraph 4.
- Wrong: Agent reports it in normal flow as if it's just another data point.

---

## TEST: Expected Output Format

```
FROM: [AGENT NAME] — [DOMAIN] Agent
TO: [LEAD NAME] — Lead [ROOM NAME]

FINDING:
[1-2 sentence bottom line. What the analysis found. No buildup, no methodology — the conclusion first.]

ANALYSIS:
[2-3 paragraphs of evidence and reasoning. Specific data points.
Methodology appropriate to this agent's domain. No generic filler.]

CONFIDENCE: [Agent's conviction system]
[One sentence on what would change the view.]

[If applicable: ⚠️ FLAG — something the lead needs to see immediately]
```
