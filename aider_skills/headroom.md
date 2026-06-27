# HEADROOM — COMPUTE ALLOCATION & TOKEN BALANCING

## Purpose
Manage context window budget. Prevent token exhaustion from verbose context.
Local-first: data stays in environment, never sent unnecessarily.

## Token Balancing Rules
- Track cumulative token spend per session (approximate)
- If context is >60% full: start compressing read files (summaries > full content)
- If context is >80% full: drop lowest-priority context (logs, verbose output)
- If context is >90% full: caveman ultra mode mandatory, drop all non-essential context

## Context Priority (highest → lowest)
1. Active task spec / plan
2. Files being edited
3. Error messages / test output
4. Schema / model definitions
5. Skill files (this file and peers)
6. Historical chat / logs

## Compression Rules (CCR — Context Compression Reduction)
When compressing context:
- Summarize file contents → one-line description + key symbols
- Cache originals mentally; retrieve on demand only
- Strip docs/comments from read-only context files
- Never compress: active diffs, error messages, test output

## Dynamic Allocation
- Simple task (typo fix, rename): minimal context, no skill preload
- Medium task (new function, test): load relevant skill + active file
- Complex task (new feature, refactor): full skill matrix + plan

## TLS / Network
- `HEADROOM_TLS_STRICT=true` equivalent: never disable SSL verification in generated code
- All external HTTP calls: explicit timeout (30s default)
