# Eval Suite — the 5 tests that fail when discipline breaks

> **Why an eval suite?** A prompt that *says* it prevents hallucination is not evidence it does. A test that runs the system against a known-bad input and checks the output is. The 5 tests below make prompt changes verifiable.

The eval suite is **the team's feedback loop**. Ship a run-time change? Run the suite. Edit a prompt? Run the suite. Drift detected? Run the suite.

## The 5 tests

| Test | Discipline | What it injects | What passes |
|------|------------|-----------------|-------------|
| `test_hallucination.py` | The system never cites a source it didn't retrieve this run | A fabricated press release (with a URL the runtime can resolve, but content that doesn't match anything real) | The memo's `citations_used` does not include the fabricated source |
| `test_source_verification.py` | The system surfaces contradictions in `gaps` / `tensions`, not averages | Two contradicting 10-K footnotes for the same line item (e.g. revenue recognition policies that changed back-and-forth) | The memo's `tensions` or `gaps` contains one named contradiction |
| `test_per_asset_coverage.py` | Every ticker in a basket appears in every relevant section of the memo | f1 run on a 5-ticker basket | Final envelope contains ≥ 1 reference to each ticker in `bottom_line.flip_trigger`, `bear_case`, `next_three_questions` |
| `test_freshness.py` | Stale sources are flagged | A 3-year-old "as_of" injected via the tool layer's manual override | A `verification.error_flags` entry or a `gaps` entry names the staleness |
| `test_abstention.py` | Out-of-scope queries return `NOT FOUND`, not invention | "What's Tesla's projected 2030 delivery?" (out of scope for f1) | The memo's `gaps` contains `NOT FOUND` for the question; the memo does not invent a number |

## How they work

Each test:
1. Constructs a fixture: a ticker + an injected bad-data item + a known-correct expected outcome.
2. Calls `runtime.py` (or its planning logic) to run f1 on the ticker.
3. Loads the produced envelope from `docs/runtime/.runs/<run_id>/final_envelope.json`.
4. Asserts the discipline-specific invariant (e.g., citations_used does not include the fabricated URL).
5. Prints a human-readable failure message that names the broken invariant.

Tests are written in plain pytest. Run them via:

```bash
cd docs/runtime/evals
pytest -v
```

## What "pass" means

A passing eval suite is **the only evidence the system works**. The README's "PASS" claim is replaced by:

- Each of the 5 tests passes against the calibrated baseline (a known-clean run).
- Each test fails when the prompt is intentionally regressed (a unit-test-of-tests sanity check).
- The 5 tests run on every prompt change.

## Adding a 6th test

When a new discipline emerges (e.g. "the system never uses the sell-side of an issuer as a primary citation"), add a 6th test. The pattern:

1. Inject a known-bad input.
2. Construct a known-correct expected outcome.
3. Run f1 against the fixture.
4. Assert.

The injection pattern? **Most are `mock`s on the connector layer** (`tools/sec_edgar.py`/`tools/news.py`)/etc.) that ensure retrival returns the bad input; the runtime never realizes.

## Baseline calibration

Before the suite can "go green," you need a calibrated baseline: a memo on a real ticker that all 5 tests pass against. Conventions:

- Pick a ticker with a clean, recent 10-K (no auditor changes, no restatements) — `MSFT` or `AAPL` is fine.
- Run f1 to completion against the calibrated baseline.
- Save the baseline envelope under `docs/runtime/evals/baselines/calibrated_<ticker>_<date>.json`.
- The test suite ships with these as known-good fixtures.

## What this isn't

- **Not lint.** A prompt that passes the v2 linter could still fail every eval here.
- **Not a model benchmark.** The evals test *the system* (prompt + tool layer + discipline), not the underlying model's general capability.
- **Not exhaustive.** These 5 are *the disciplinarians* the audit found. Others might surface with more usage. Add as you find them.

## See also

- [`../../USER-JOBS.md`](../../USER-JOBS.md) — the 5 user jobs the system serves (the evals ensure the discipline that serves those jobs actually holds).
- [`../../CANNOT-DO.md`](../../CANNOT-DO.md) — out-of-scope claims the evals should reject as ABSTAIN.
- [`../thesis_register/README.md`](../thesis_register/README.md) — the durable memory that gives f1/f4/f8 the discipline for tracking.
