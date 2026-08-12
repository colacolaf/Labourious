# System Prompt Audit Framework

## Executive Summary

This document outlines the systematic audit and improvement of all 89 subagent system prompts in the Labourious HQ system. The goal is to ensure each agent:
1. Acts as a high-level analyst with correct information
2. Double-checks its work before presenting findings
3. Takes information from the right authoritative sources
4. Uses connectors/APIs when needed
5. Validates each stock/fund every time
6. Provides accurate, actionable intelligence

## Key Findings from Initial Audit

### T1 Lead Agents (13 agents) - EXCELLENT QUALITY
- **Strengths:** Comprehensive decision frameworks, detailed examples, clear routing
- **Weaknesses:** Missing explicit "double-check" instructions, missing source verification protocols

### T2 Named Agents (11 agents) - GOOD QUALITY  
- **Strengths:** Strong domain expertise, good examples
- **Weaknesses:** Missing validation steps, inconsistent connector usage instructions

### T3 Utility Agents (60 agents) - NEEDS IMPROVEMENT
- **Strengths:** Clear role definitions, basic decision frameworks
- **Weaknesses:** Missing self-validation, missing source verification, inconsistent quality control

### T4 Intern Agents (6 agents) - BASIC BUT FUNCTIONAL
- **Strengths:** Clear scope, good examples
- **Weaknesses:** Missing validation, missing error correction protocols

## Critical Missing Elements Across All Tiers

### 1. Double-Check Protocol
**Current State:** Most prompts don't explicitly instruct agents to verify their own work
**Improvement:** Add explicit "Quality Assurance" section with verification steps

### 2. Source Verification
**Current State:** Prompts mention data sources but don't specify how to verify accuracy
**Improvement:** Add "Source Verification Protocol" section

### 3. Stock/Fund Validation
**Current State:** No explicit instruction to check each stock/fund every time
**Improvement:** Add "Asset Validation Protocol" section

### 4. Connector Usage
**Current State:** Some prompts mention API keys but don't instruct when to use them
**Improvement:** Add "Connector Usage Protocol" section

### 5. Error Correction
**Current State:** No explicit instructions for catching and correcting errors
**Improvement:** Add "Error Detection & Correction" section

## Improvement Framework by Tier

### T1 Lead Agent Improvements

#### Portfolio Manager
**Additions Needed:**
- Explicit instruction to verify all lead syntheses before presenting to user
- Protocol for cross-validating conflicting signals
- Requirement to check Knowledge Graph before EVERY analysis
- Validation that all stocks/funds mentioned are properly researched

#### Michael Burry (Lead Research)
**Additions Needed:**
- Explicit instruction to verify SEC filings are current (not stale)
- Protocol for cross-referencing multiple data sources
- Requirement to validate each ticker before analysis
- Quality check: "Does this analysis hold up under scrutiny?"

#### Warren Buffett (Lead Fundamental)
**Additions Needed:**
- Explicit instruction to verify DCF assumptions are current
- Protocol for validating moat assessments against recent data
- Requirement to check each stock's fundamentals EVERY time
- Quality check: "Are we paying a margin of safety?"

### T3 Utility Agent Improvements

#### Web Research Agent
**Additions Needed:**
- Explicit instruction to verify source credibility
- Protocol for cross-referencing information
- Requirement to validate each data point
- Quality check: "Is this information current and accurate?"

#### DCF & Valuation Agent
**Addions Needed:**
- Explicit instruction to verify all financial inputs
- Protocol for validating assumptions
- Requirement to check each company's financials EVERY time
- Quality check: "Are these assumptions defensible?"

#### VaR & Stress Test Agent
**Additions Needed:**
- Explicit instruction to verify portfolio composition
- Protocol for validating risk metrics
- Requirement to check each position EVERY time
- Quality check: "Does this risk profile make sense?"

### T4 Intern Agent Improvements

#### Hedge Fund & Political Filings Intern
**Additions Needed:**
- Explicit instruction to verify filing dates
- Protocol for validating data extraction
- Requirement to check each entity EVERY time
- Quality check: "Is this data complete and accurate?"

#### Bear Case Intern
**Additions Needed:**
- Explicit instruction to verify bear case assumptions
- Protocol for validating probability estimates
- Requirement to check each thesis EVERY time
- Quality check: "Is this bear case plausible?"

## Implementation Strategy

### Phase 1: Create Improvement Templates
1. Create "Quality Assurance" section template
2. Create "Source Verification Protocol" template
3. Create "Asset Validation Protocol" template
4. Create "Connector Usage Protocol" template
5. Create "Error Detection & Correction" template

### Phase 2: Implement for Each Tier
1. Start with T1 Lead Agents (highest impact)
2. Move to T2 Named Agents
3. Implement for T3 Utility Agents (largest group)
4. Finalize with T4 Intern Agents

### Phase 3: Testing & Validation
1. Test each agent with example portfolios
2. Verify improvements are consistent
3. Validate that agents now properly:
   - Double-check their work
   - Use correct sources
   - Validate each stock/fund
   - Use connectors when needed
   - Provide accurate information

## Quality Metrics

### Before Improvements
- Double-check rate: ~20% of prompts
- Source verification: ~30% of prompts
- Stock validation: ~10% of prompts
- Connector usage: ~50% of prompts
- Error correction: ~15% of prompts

### After Improvements (Target)
- Double-check rate: 100% of prompts
- Source verification: 100% of prompts
- Stock validation: 100% of prompts
- Connector usage: 100% of prompts
- Error correction: 100% of prompts

## Next Steps

1. Create improvement templates
2. Start implementing for T1 Lead Agents
3. Document specific improvements for each agent
4. Test with example scenarios
5. Iterate and refine

---

*This framework ensures every agent in the Labourious HQ system operates at the highest level of analytical rigor, providing accurate, actionable intelligence to the Portfolio Manager and ultimately the user.*