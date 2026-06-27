# DRY RUN SAFETY — SIMULATED ORDERS & PRODUCTION GUARDS

## Core Rule
All order execution code must be testable in simulation before touching production endpoints.
Never write code that defaults to live execution. Simulation must be the default.

## Dry Run Flag Pattern
```python
# Always add dry_run param, default True
async def execute_order(symbol: str, side: str, amount: float, dry_run: bool = True):
    if dry_run:
        logger.info("DRY RUN order", extra={"symbol": symbol, "side": side, "amount": amount})
        return {"status": "simulated", "symbol": symbol, "side": side, "amount": amount}
    # real execution below — only reached when dry_run=False explicitly
    return await broker.create_order(symbol, side, amount)
```

## Environment Gates
```python
# In config/settings:
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"  # safe default
```
Production env must explicitly set `DRY_RUN=false`. Never default to false.

## Agent Configuration
All Agent DB records must carry `dry_run: bool` field.
Agent scheduler checks this before dispatching any trade action.
`.env.example` must contain `DRY_RUN=true`.

## Broker API Safety
- Paper trading endpoints preferred for all dev/test work
- ccxt: use `sandbox` mode: `exchange.set_sandbox_mode(True)`
- IB: use paper trading port 7497 (not live 7496) in dev
- Never use production API keys in test suite

## Test Suite Rule
`tests/test_sandbox.py` must verify:
1. `dry_run=True` → no real order created
2. `dry_run=False` → requires explicit env flag (skip in CI unless `LIVE_TEST=true`)
3. Order schema validates before any execution (real or simulated)

## Code Review Checklist
Before any trade-execution PR:
- [ ] `dry_run=True` is default in all new functions
- [ ] Production path requires explicit opt-in
- [ ] No hardcoded production endpoints
- [ ] Paper/sandbox broker config exists for dev
- [ ] `DRY_RUN=true` in `.env.example`
