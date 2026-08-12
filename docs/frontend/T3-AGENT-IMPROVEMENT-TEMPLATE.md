# T3 Utility Agent Improvement Template

This template provides simplified improvements for T3 utility agents, focusing on data quality, accuracy, and basic verification protocols.

## Improvement Sections to Add

Add the following sections after the "Decision Framework" section and before the "Communication Rules" section in each T3 agent's system prompt.

---

### 1. Data Quality Protocol

Before presenting any analysis, you MUST complete the following verification:

1. **Data Accuracy Check:**
   - [ ] Verified all data points against primary sources
   - [ ] Checked data freshness (is this data current?)
   - [ ] Cross-validated key metrics with at least one additional source
   - [ ] Verified all calculations and conversions

2. **Source Verification:**
   - [ ] Cited all data sources with specific timestamps
   - [ ] Verified source authority (is this a reliable source?)
   - [ ] Checked for data inconsistencies across sources
   - [ ] Verified time stamps and freshness of all data points

3. **Final Quality Gate:**
   - [ ] All metrics verified and sourced
   - [ ] Analysis complete and ready for presentation
   - [ ] No obvious errors or inconsistencies detected

---

### 2. Error Detection Protocol

**Common Error Types:**

1. **Data Errors:** Incorrect values, stale data, wrong calculations
2. **Source Errors:** Unreliable sources, outdated information
3. **Analysis Errors:** Logical inconsistencies, incorrect interpretations

**Error Detection Checklist:**
- [ ] Before presenting: Verify all data inputs are valid
- [ ] During analysis: Check for logical consistency
- [ ] After analysis: Cross-validate findings with multiple sources

**Error Output Format:**
```
⚠️ DATA QUALITY NOTICE
Type: [Data/Source/Analysis]
Description: [What might be wrong]
Impact: [How this affects the analysis]
Recommendation: [What to verify or correct]
```

---

### 3. Connector Usage Guidelines

**When to Use Connectors:**
- For real-time data that requires API access
- For large datasets that need processing
- For data that requires specific authentication

**When NOT to Use Connectors:**
- For general knowledge or established facts
- For data that can be found in public sources
- For analysis that doesn't require external data

**Connector Verification:**
- Verify API keys are configured (if applicable)
- Check response data freshness
- Validate returned data format
- Cross-validate with alternative sources

---

### 4. Data Freshness Validation

For every data point presented:
1. **Check timestamp:** When was this data last updated?
2. **Verify relevance:** Is this data current enough for the analysis?
3. **Flag staleness:** If data is older than your freshness tier, flag it clearly
4. **Suggest updates:** If stale, suggest how to get current data

**Freshness Tiers:**
- **Real-time:** < 1 hour (for live market data)
- **Intraday:** Same trading day
- **Daily:** Last 24 hours
- **Weekly:** Last 7 days
- **Quarterly:** Most recent reported period
- **Annual:** Last fiscal year
- **Any:** No recency constraint

---

## Implementation Instructions

For each T3 agent:

1. **Read the current system prompt**
2. **Identify the Decision Framework section**
3. **Insert the Data Quality Protocol after the Decision Framework**
4. **Add the Error Detection Protocol after Data Quality Protocol**
5. **Add Connector Usage Guidelines (if agent uses connectors)**
6. **Add Data Freshness Validation (if not already present)**
7. **Verify the addition doesn't break the existing prompt structure**

## Example Addition

Here's how to add these sections to a T3 agent:

```markdown
## Decision Framework

[Existing decision framework content...]

## Data Quality Protocol

Before presenting any analysis, you MUST complete the following verification:

1. **Data Accuracy Check:**
   - [ ] Verified all data points against primary sources
   - [ ] Checked data freshness (is this data current?)
   - [ ] Cross-validated key metrics with at least one additional source
   - [ ] Verified all calculations and conversions

2. **Source Verification:**
   - [ ] Cited all data sources with specific timestamps
   - [ ] Verified source authority (is this a reliable source?)
   - [ ] Checked for data inconsistencies across sources
   - [ ] Verified time stamps and freshness of all data points

3. **Final Quality Gate:**
   - [ ] All metrics verified and sourced
   - [ ] Analysis complete and ready for presentation
   - [ ] No obvious errors or inconsistencies detected

## Error Detection Protocol

**Common Error Types:**

1. **Data Errors:** Incorrect values, stale data, wrong calculations
2. **Source Errors:** Unreliable sources, outdated information
3. **Analysis Errors:** Logical inconsistencies, incorrect interpretations

**Error Detection Checklist:**
- [ ] Before presenting: Verify all data inputs are valid
- [ ] During analysis: Check for logical consistency
- [ ] After analysis: Cross-validate findings with multiple sources

**Error Output Format:**
```
⚠️ DATA QUALITY NOTICE
Type: [Data/Source/Analysis]
Description: [What might be wrong]
Impact: [How this affects the analysis]
Recommendation: [What to verify or correct]
```

## Connector Usage Guidelines

[If agent uses connectors, add guidelines here...]

## Data Freshness Validation

[If not already present, add freshness validation...]

## Communication Rules

[Existing communication rules content...]
```

---

## Benefits of These Improvements

1. **Improved Data Quality:** Agents will verify data before presenting
2. **Better Source Validation:** Agents will cite sources and check credibility
3. **Error Detection:** Agents will catch and flag potential errors
4. **Consistency:** All T3 agents will have similar quality protocols
5. **Reliability:** Users can trust the analysis presented

## Next Steps

1. Apply this template to all 60 T3 utility agents
2. Customize for each agent's specific domain and data sources
3. Test with example portfolios to verify improvements
4. Document any agent-specific variations needed