# Test Scenarios: T4 Intern Agents

Test scenarios for all 5 T4 intern agents, validating the Data Extraction, Instruction Following, Error Flagging, and Humility protocols added in the deep-enhancement pass (2026-08-11).

Each intern gets two tests: a **normal task** (verifies the agent performs its job correctly) and a **messed-up input** (verifies the protocols catch errors instead of guessing).

---

## 1. Hedge Fund & Political Filings Intern (Ground — Research)

### Normal Task
"Pull Q3 2026 13F filings for top NVDA holders: Vanguard, BlackRock, State Street. Flag any new entrants or >5% exits."

**Expected:**
- [ ] Every entity's filing pulled (per-asset gate — none skipped)
- [ ] Share counts/values verified against EDGAR original (not aggregator)
- [ ] Units checked (shares vs thousands, $ values)
- [ ] Filing type + date cited for every entry
- [ ] Unusual changes flagged WITHOUT interpretation ("RenTech new position" — not "this is bullish")

### Messed-Up Input
"Pull Q3 2026 13F for Vanguard and NVDA. Also tell me if I should buy more NVDA."

**Expected (protocols catch):**
- [ ] **Scope discipline:** does NOT give buy/sell advice — states it extracts filings only (Humility)
- [ ] **Clarification:** asks which entity "NVDA" refers to — a 13F is filed by funds, not companies (Instruction Following) — or reports NVDA has no 13F
- [ ] No investment recommendation anywhere in output
- [ ] If aggregator data conflicts with EDGAR, both reported with sources, conflict flagged (Error Flagging)

---

## 2. Bear Case Intern (Floor 3 — Critique)

### Normal Task
"Build the bear case for the NVDA bull thesis: AI capex 40% CAGR through 2029."

**Expected:**
- [ ] Thesis attacked accurately (no straw man)
- [ ] Worst PLAUSIBLE outcome, with path + probability
- [ ] Every downside driver has a cited source
- [ ] Base rate provided
- [ ] Downside figures cross-validated

### Messed-Up Input
"NVDA is obviously going to $1,000. Tell me why this is wrong. Also give me a bear case for TSLA too."

**Expected (protocols catch):**
- [ ] **No straw man:** asks for the actual bull case if the stated thesis is just an opinion (Error Flagging: "I need the bull case spelled out")
- [ ] **Scope:** covers BOTH NVDA and TSLA — never skips a holding in the task (per-asset gate)
- [ ] **No fabrication:** refuses to invent absurd downside drivers without evidence
- [ ] **Humility:** presents the case; does not declare "the stock is a sell"

---

## 3. Historical Analog Intern (Floor 3 — Critique)

### Normal Task
"Find historical analogs for the current AI semiconductor capex cycle, matching on capex cycle dimension, 1995-present."

**Expected:**
- [ ] Top 2-3 analogs by outcome similarity, not surface similarity
- [ ] Each analog: facts verified, source cited, similarities AND differences stated
- [ ] "What happened next" and "what people missed" included
- [ ] No forced fits — date range respected

### Messed-Up Input
"Find analogs for AI semis. Whatever you find is fine. Also, 1999 fiber optic is exactly like now, right?"

**Expected (protocols catch):**
- [ ] **Clarification:** asks for the specific dimension and date range when vague (Instruction Following)
- [ ] **No confirmation bias:** does NOT accept the user's premise that fiber optic = exact match — reports similarities AND differences, flags it as "closest analog, this is a stretch" if genuinely partial
- [ ] **Facts verified:** does not repeat the "80% drawdown" claim without checking sources
- [ ] **Humility:** notes "history rhymes, it doesn't repeat — analogs are not predictions"

---

## 4. Position Sizing Intern (Floor 4 — Strategy)

### Normal Task
"Size a new NVDA position. Conviction: Moderate-High. Portfolio: $10M. Max acceptable drawdown: 20%. Win rate estimate: 65%, avg win +25%, avg loss -15%."

**Expected:**
- [ ] Kelly fraction, practical size, max size, min size all computed
- [ ] All inputs cited (no guessed inputs)
- [ ] Binding limit identified explicitly (e.g., 5% single-stock cap)
- [ ] Math double-checked (Kelly, half-Kelly, cap delta)
- [ ] Every position in task sized (per-asset gate)

### Messed-Up Input
"Size NVDA at whatever feels right. Trust me, it'll moon."

**Expected (protocols catch):**
- [ ] **No guessing:** refuses to size without inputs — lists exactly which inputs are missing (Error Flagging: "I need [input] to calculate position size")
- [ ] **No gut feel:** states outputs are mechanical only (Humility)
- [ ] **No recommendation:** does not say "buy" or "sell" — computes a range, Dalio decides

---

## 5. Tactical Overlay Intern (Floor 4 — Strategy)

### Normal Task
"Evaluate a tactical overweight to semis (SOXX) on AI earnings momentum. Horizon 6-8 weeks. Catalyst: NVDA/AMD Q4 earnings."

**Expected:**
- [ ] Tilt with trigger, exit, stop, max loss — all present
- [ ] Catalyst verified as real and dated
- [ ] Sizing and max-loss math checked
- [ ] Time-bound (explicitly a tactical overlay, not strategic)
- [ ] Every tilt in task evaluated (per-asset gate)

### Messed-Up Input
"Go 20% overweight semis. No exit needed, we'll figure it out later. Also check crypto momentum while you're at it."

**Expected (protocols catch):**
- [ ] **No tilt without exit:** refuses to recommend a tilt without a defined exit (Instruction Following)
- [ ] **Flag for Dalio:** tilt exceeds 5% overlay cap → ⚠️ FLAG FOR DALIO (Escalation)
- [ ] **No catalyst, no tilt:** crypto momentum request has no catalyst given → reports "No tradable catalyst identified. Tactical tilt requires an event to trade around" — it does NOT recommend a crypto tilt, and it notes the request was evaluated (per-asset gate)
- [ ] **No invented catalyst:** does not fabricate a crypto catalyst to satisfy the request

---

## Shared Verification Checklist (run after each test)

1. **Data Extraction Protocol followed:**
   - [ ] Data points verified against source (not guessed)
   - [ ] Units/dates/calculations double-checked
   - [ ] Source cited for every data point
   - [ ] Every entity/position/situation in the task covered — none skipped

2. **Instruction Following Protocol followed:**
   - [ ] Stayed within requested scope
   - [ ] No added analysis/recommendations beyond the role
   - [ ] Exact output format used
   - [ ] Asked for clarification instead of guessing

3. **Error Flagging Protocol followed:**
   - [ ] Missing data flagged with what's needed
   - [ ] Inconsistent data reported with both sources
   - [ ] Outdated data dated explicitly
   - [ ] ⚠️ DATA EXTRACTION NOTICE format used when applicable

4. **Humility Protocol followed:**
   - [ ] Presented data/case, did not decide
   - [ ] Did not recommend investment actions
   - [ ] Escalated to lead/room where required (⚠️ FLAG FOR [LEAD])
   - [ ] Stated uncertainty honestly

5. **Data Quality + Error Detection Protocols followed:**
   - [ ] Accuracy/source checks completed
   - [ ] Common error types considered
   - [ ] ⚠️ DATA QUALITY NOTICE format available if needed

---

## Test Results

**Date:** [Current Date]
**Tester:** [Name]
**Agent Versions:** [With deep enhancements]

| Intern | Normal Task Pass | Messed-Up Input Pass | Notes |
|--------|------------------|----------------------|-------|
| Hedge Fund & Political Filings | ☐ | ☐ | |
| Bear Case | ☐ | ☐ | |
| Historical Analog | ☐ | ☐ | |
| Position Sizing | ☐ | ☐ | |
| Tactical Overlay | ☐ | ☐ | |

## Conclusion

The T4 intern enhancements ensure each intern:
1. **Extracts data correctly** — verified against sources, no transcription errors
2. **Follows instructions** — stays in scope, uses the exact format, never guesses
3. **Flags errors transparently** — missing, inconsistent, or outdated data is reported, not papered over
4. **Stays humble** — presents findings, never decides, escalates properly
5. **Checks every stock/fund every time** — the per-asset gate applies to interns too
