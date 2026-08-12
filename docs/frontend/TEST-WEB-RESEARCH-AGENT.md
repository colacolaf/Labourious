# Test Scenario: Web Research Agent

## Test Portfolio
A sample portfolio with the following holdings:
- NVDA (NVIDIA Corporation) - 15% allocation
- TSLA (Tesla Inc.) - 10% allocation
- AAPL (Apple Inc.) - 20% allocation
- MSFT (Microsoft Corporation) - 15% allocation
- AMZN (Amazon.com Inc.) - 10% allocation
- GOOGL (Alphabet Inc.) - 10% allocation
- META (Meta Platforms Inc.) - 10% allocation
- Cash - 10%

## Test Query
"Research recent news and developments for NVDA (NVIDIA Corporation) that could impact the stock price in the next quarter. Focus on product launches, earnings reports, and competitive dynamics."

## Expected Improvements
With the new Data Quality Protocol and Error Detection Protocol, the Web Research Agent should:

### 1. Data Quality Verification
- [ ] Verify all news sources are credible (Reuters, Bloomberg, WSJ, etc.)
- [ ] Check that all data points are from the last 30 days (Daily freshness tier)
- [ ] Cross-validate key claims across multiple sources
- [ ] Verify all dates and timestamps are accurate

### 2. Source Citation
- [ ] Cite each source with specific publication date
- [ ] Include URLs where available
- [ ] Note the authority of each source
- [ ] Flag any sources that are less reliable

### 3. Error Detection
- [ ] Flag any conflicting information between sources
- [ ] Note if data is older than expected
- [ ] Identify any missing information that should be included
- [ ] Highlight any potential inaccuracies in reporting

### 4. Quality Output
- [ ] Present findings in the standard FROM/TO format
- [ ] Include all required fields (RESULTS section)
- [ ] Provide clear source attribution
- [ ] Note confidence level in findings

## Example Test Output

**Expected Improved Output:**

```
FROM: Web Research Agent
TO: Michael Burry — Lead Research (Room 1)

RESULTS:
- Reuters: "NVIDIA reports record Q4 2026 earnings, revenue up 122% YoY to $35.1B." Feb 20, 2026. [reuters.com]
- Bloomberg: "NVIDIA Blackwell B200 production ramp exceeded expectations, TSMC yields at 85%." Feb 18, 2026. [bloomberg.com]
- WSJ: "AMD announces new MI400 AI chip to compete with NVIDIA Blackwell, launching Q3 2026." Feb 15, 2026. [wsj.com]
- TechCrunch: "NVIDIA announces partnership with major automakers for autonomous driving platform." Feb 12, 2026. [techcrunch.com]

DATA QUALITY VERIFICATION:
- All sources are credible financial/news outlets
- All data from last 30 days (within Daily freshness tier)
- Key claims verified across multiple sources
- No conflicting information detected

CONFIDENCE: High
Findings are well-sourced and consistent across multiple credible outlets.
```

## Verification Checklist

After the agent responds, verify:

1. **Data Quality Protocol was followed:**
   - [ ] All sources cited with dates
   - [ ] Data freshness verified (last 30 days)
   - [ ] Multiple sources used for key claims
   - [ ] No obvious errors in data extraction

2. **Error Detection Protocol was followed:**
   - [ ] Conflicting information flagged (if any)
   - [ ] Data staleness noted (if any)
   - [ ] Missing information identified (if any)
   - [ ] Potential inaccuracies highlighted (if any)

3. **Output format is correct:**
   - [ ] FROM/TO headers present
   - [ ] RESULTS section with bullet points
   - [ ] Source citations included
   - [ ] Confidence level stated

## Test Results

**Date:** [Current Date]
**Tester:** [Name]
**Agent Version:** [With improvements]

### Results:
- [ ] Data Quality Protocol followed correctly
- [ ] Error Detection Protocol followed correctly
- [ ] Output format correct
- [ ] All sources cited properly
- [ ] Data freshness verified
- [ ] No errors detected in presentation

### Notes:
[Space for any observations or issues found during testing]

## Conclusion

The Web Research Agent improvements ensure that:
1. **Data is verified** before presentation
2. **Sources are properly cited** with timestamps
3. **Errors are detected** and flagged appropriately
4. **Output is consistent** and follows the standard format
5. **Users can trust** the information presented

These improvements will significantly enhance the reliability and accuracy of web research across the Labourious HQ system.