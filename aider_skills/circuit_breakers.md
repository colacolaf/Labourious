# CIRCUIT BREAKERS — PANIC PROTOCOLS & LOOP GUARDS

## Purpose
Prevent runaway execution, infinite loops, cascading failures, and PnL disasters.
Break the circuit before damage compounds.

## Hard Stop Triggers (immediate halt, surface to user)
- PnL drop > configured threshold in single session → halt all trading agents
- Same error message repeated >3x in one task → stop, diagnose root cause
- Test suite fails same test >5x after fixes → stop, escalate
- File written >3x to same path in one task → likely loop, stop
- API call fails with 429/503 → stop, do not retry silently

## Trading-Specific Breakers
```python
# Before any order execution:
if abs(pnl_delta) > MAX_DRAWDOWN_PCT:
    raise CircuitBreakerError("PnL threshold breached — halt")
if order_count > MAX_ORDERS_PER_MINUTE:
    raise CircuitBreakerError("Order rate limit — halt")
```
Always implement in agent `run()` pre-check, not post-execution.

## Retry Policy
- Max retries: 3
- Backoff: exponential (1s, 2s, 4s)
- After 3 failures: log error, mark agent DEGRADED, stop retrying
- Never retry: auth errors (401/403), invalid input (400), not found (404)

## State on Break
On circuit open:
1. Log exact error + context (no secrets)
2. Set agent status → HALTED
3. Do NOT attempt auto-recovery
4. Await explicit human reset

## Recovery Gate
Before reset after circuit break:
- Root cause identified and documented
- Fix deployed and tested
- Human explicitly triggers restart

## Loop Detection
```python
# ponytail: simple counter guard
attempt = 0
while condition:
    if attempt > MAX_ATTEMPTS:
        break  # circuit open
    attempt += 1
```
