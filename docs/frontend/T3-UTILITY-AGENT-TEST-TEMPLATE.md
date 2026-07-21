# T3 Utility Agent — Test Template

> Paste this at the end of any T3 utility agent system prompt to stress-test it.
> T3 agents have a functional personality, not a real person. They do ONE specific job.
> Replace `[AGENT]`, `[FUNCTION]`, and `[TOOL]` with actual values.

---

## TEST: Simulated Tasking

You receive the following task. Execute it and return your output.

```
TASK: [Specific task for this utility agent — one clear ask.
Example: "Pull all SEC 10-K filings for AAPL from the last 3 years and
extract the revenue, operating income, and free cash flow figures."
or "Scan Twitter/X for sentiment on NVDA over the last 24 hours.
Categorize as bullish, bearish, or neutral with volume metrics."]

CONTEXT (if any):
[Brief context about why this is needed. Optional — utility agents
should work with or without context.]

FORMAT: [Expected output format — table, list, structured report, etc.]
```

---

## TEST: Simulated Raw Data

You have access to the following raw data/sources. Process it into your output.

```
[Insert raw or semi-structured data relevant to this agent's domain.
Make it intentionally messy — some relevant, some noise, some ambiguous.
Example for a news aggregator: 5 headlines, 2 of which are noise.
Example for a data scout: a mix of relevant and irrelevant data points.]

Include at least:
- 1 clearly relevant signal
- 1 piece of noise that could be mistaken for signal
- 1 ambiguous data point that requires judgment
```

---

## TEST: Expected Behaviors Checklist

- [ ] **Focused execution:** Agent performed EXACTLY the task requested — no more, no less
- [ ] **Signal/noise filtering:** Agent correctly separated relevant signal from noise in the raw data
- [ ] **Ambiguity handled:** Agent flagged the ambiguous data point rather than forcing a false conclusion
- [ ] **Format compliance:** Output matches the requested format exactly
- [ ] **No scope creep:** Agent did not add commentary or recommendations beyond their functional scope. Interpretation within their domain is expected (e.g., sentiment scoring, regime classification). Portfolio advice or trade recommendations are not.
- [ ] **Tool usage:** Agent used the tools/data sources specified in their Tool Access section
- [ ] **Completeness:** Agent didn't skip any part of the task
- [ ] **No hedging:** Utility agents deliver results, not opinions. The output is factual and direct.

---

## TEST: Edge Cases

### Edge Case 1: Task is Unclear or Incomplete
The tasking is vague. The agent doesn't have enough info to execute precisely.
- Expected: Agent asks 1 specific clarifying question and waits. Doesn't guess.
- Wrong: Agent makes assumptions and executes anyway.

### Edge Case 2: No Relevant Data Found
The agent searches and finds nothing relevant.
- Expected: "No relevant results for [query]. Searched [sources]. Suggest expanding search to [alternative sources] or adjusting parameters."
- Wrong: Agent fabricates data or returns irrelevant results to fill space.

### Edge Case 3: Data Overload
The agent finds way too much data — hundreds of results.
- Expected: Agent returns a prioritized/ranked subset with a note: "Top [N] results by [relevance criterion]. Full dataset available on request."
- Wrong: Agent dumps everything unfiltered or silently truncates.

### Edge Case 4: Conflicting Data
Two sources give contradictory information.
- Expected: Agent presents both with source attribution. "Source A reports [X]. Source B reports [Y]. Discrepancy noted — recommend verification."
- Wrong: Agent picks one and ignores the other.

### Edge Case 5: Tool Failure
The agent's primary data source is unavailable.
- Expected: Agent reports the failure and offers a fallback if one exists. "Primary source [X] unavailable. Attempted fallback [Y] — results below (caveat: lower confidence)."
- Wrong: Agent silently fails or fabricates results.

---

## TEST: Expected Output Format

```
TASK: [Restate the task — shows you understood it]

RESULTS:
[Clean, formatted output. Table, list, or structured data as requested.
No narrative. No analysis. Just the data.]

DATA QUALITY NOTES (if applicable):
- [Source availability, confidence in data, discrepancies found]

EXECUTION SUMMARY:
Sources queried: [list]
Results found: [count]
Time to execute: [if relevant]
```
