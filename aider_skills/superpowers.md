# SUPERPOWERS — PERMISSION BOUNDARIES & ORCHESTRATION

## Permission Boundaries
- Operate within approved spec/plan only. No arbitrary directives.
- Human checkpoint required before: merging, deploying, destructive ops.
- Scope: tasks must be bounded (2-5 min each). No unbounded execution.
- Never escalate privileges. If action requires root/admin → stop, report.

## Mandatory Workflow Sequence
Before ANY implementation task, check for relevant skill/convention:
1. Brainstorm (design phase) — clarify intent before touching code
2. Worktree/isolation setup — keep main branch clean
3. Plan writing — break into discrete steps
4. Implementation — one step at a time
5. Tests (RED-GREEN-REFACTOR)
6. Code review — spec compliance then code quality
7. Branch finish/cleanup

Workflows are mandatory, not suggestions.

## State Synchronization
- All design decisions → written plan before code
- Git worktree isolation for parallel work
- Task completion markers must be explicit (not assumed)
- No implicit state. If state is unclear → ask, don't guess.

## Rollback Behavior
- On test failure: revert last change, re-run RED phase
- On broken plan: stop, surface issue, wait for human decision
- Worktree cleanup: delete branch if no net-new value
- Never force-push. Never `--no-verify`.

## Orchestration Rules
- One agent, one task. No parallel mutations to same file.
- Dispatch subagent per task with two-stage review: spec compliance → code quality.
- Skills load before action. If skill missing → surface gap, don't improvise.

## Scope Guard
If request scope creeps beyond plan: stop, list what's in scope vs out, get approval.
