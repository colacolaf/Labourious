# RUFLO — MULTI-AGENT ORCHESTRATION BRIDGE

## Purpose
Safe coordination rules when Aider operates as part of a larger agent system.
Single-agent in Aider context — these rules apply when outputs feed downstream agents.

## Orchestration Rules
- One task → one agent → one output. No fan-out without explicit plan.
- Output format: structured (JSON/YAML) when feeding downstream agents, prose for human.
- Task routing: include task type tag in output header when in pipeline mode.
- No implicit side effects. All file writes explicit and listed.

## Token Balancing (Cost Tracking)
- Prefer `pytest -q` / `--tb=short` over verbose output
- Prefer `grep -n pattern file` over reading whole file when target is known
- Prefer `git diff --stat` before `git diff` for scope check
- Log token-heavy operations: large file reads, full test suite runs

## Trust Scoring (for pipeline outputs)
Output quality gates before passing to next agent:
- success: tests pass + no new errors
- uptime: no partial/incomplete implementation
- integrity: no secrets in output, no hardcoded values
If any gate fails → mark output as DEGRADED, stop pipeline.

## Provider Failover
Primary: deepseek/deepseek-v4-pro
Fallback trigger: timeout >30s, HTTP 5xx, empty response
Fallback: surface error to user, do not silently retry with different model

## Behavioral Anomaly Detection
Stop and report if:
- Same file edited >3x in one task (likely loop)
- Test suite run >5x without green (likely broken loop)
- Output size >10x input size (likely hallucination/padding)
