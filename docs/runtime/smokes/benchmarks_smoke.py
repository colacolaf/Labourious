"""
smoke — [runtime-5] benchmark infrastructure.

Verifies the benchmark runner, baseline persistence, and regression detection.

Exercises:
  1. run_bench.py exists and is importable
  2. SUITE covers 19 benchmarks
  3. baseline.json exists and is valid JSON
  4. All 19 baseline entries have wallclock_s > 0
  5. check_against_baseline — passes when within 2x
  6. check_against_baseline — fails when > 2x
  7. write_baseline round-trip
  8. All 19 benchmarks in SUITE exist as smoke files
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DOCS = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROJECT_ROOT = os.path.join(DOCS, "..")
sys.path.insert(0, DOCS)

BENCH_DIR = Path(DOCS) / "runtime" / "benchmarks"

passes = 0
fails = 0

def section(title: str) -> None:
    print(f"\n── {title} ──")

def step(label: str, cond: bool) -> None:
    global passes, fails
    if cond:
        print(f"  ✓ {label}")
        passes += 1
    else:
        print(f"  ✗ FAIL: {label}")
        fails += 1

def step_eq(label: str, a, b) -> None:
    step(label, a == b)


# ===========================================================================
# 1. run_bench.py exists and is importable
# ===========================================================================
section("1. run_bench.py exists and importable")

run_bench_path = BENCH_DIR / "run_bench.py"
step("run_bench.py exists", run_bench_path.exists())

sys.path.insert(0, str(BENCH_DIR))
from run_bench import SUITE, BASELINE_PATH, load_baseline, write_baseline, check_against_baseline, run_bench


# ===========================================================================
# 2. SUITE covers expected count
# ===========================================================================
section("2. SUITE coverage")
step_eq("19 benchmarks", len(SUITE), 19)

names = {name for name, _ in SUITE}
step("per_agent_routing in suite", "per_agent_routing" in names)
step("slash_commands in suite", "slash_commands" in names)
step("evals in suite", "evals" in names)
step("connectors_e2e in suite", "connectors_e2e" in names)
step("f1_parallel in suite", "f1_parallel" in names)
step("timeout_guard in suite", "timeout_guard" in names)
step("history_search_export in suite", "history_search_export" in names)
step("structured_diff in suite", "structured_diff" in names)

# ===========================================================================
# 3. baseline.json exists and is valid JSON
# ===========================================================================
section("3. baseline.json exists and valid")
step("baseline.json exists", BASELINE_PATH.exists())

bl = load_baseline()
step("baseline is dict", isinstance(bl, dict))
step_eq("19 entries", len(bl), 19)

# ===========================================================================
# 4. All baseline entries have positive wallclock
# ===========================================================================
section("4. baseline wallclock_s > 0")
for name, entry in bl.items():
    step(f"{name} > 0s ({entry['wallclock_s']:.3f}s)", entry["wallclock_s"] > 0)

# ===========================================================================
# 5. check_against_baseline — within 2× passes
# ===========================================================================
section("5. check_against_baseline — within 2×")

results_within = [
    {"name": "fast_test", "wallclock_s": 0.10, "n_assertions": 42},
    {"name": "slow_test", "wallclock_s": 0.90, "n_assertions": 10},
]
bl_mock = {
    "fast_test": {"wallclock_s": 0.10, "n_assertions": 42},
    "slow_test": {"wallclock_s": 0.50, "n_assertions": 10},
}
ok, failures = check_against_baseline(results_within, bl_mock)
step("within 2× → ok", ok)
step_eq("0 failures", len(failures), 0)

# ===========================================================================
# 6. check_against_baseline — > 2× fails
# ===========================================================================
section("6. check_against_baseline — > 2× fails")

results_slow = [
    {"name": "fast_test", "wallclock_s": 0.10, "n_assertions": 42},
    {"name": "slow_test", "wallclock_s": 2.0, "n_assertions": 10},  # 4× baseline 0.50
]
ok2, failures2 = check_against_baseline(results_slow, bl_mock)
step(">2× → not ok", not ok2)
step_eq("1 failure", len(failures2), 1)
step("failure mentions slow_test", "slow_test" in failures2[0])
step("failure mentions ratio", "×" in failures2[0])

# ===========================================================================
# 7. write_baseline round-trip
# ===========================================================================
section("7. write_baseline round-trip")

import tempfile
tmp_dir = tempfile.mkdtemp()
tmp_path = Path(tmp_dir) / "test_baseline.json"

# Monkey-patch BASELINE_PATH
import run_bench as rb_mod
orig_path = rb_mod.BASELINE_PATH
rb_mod.BASELINE_PATH = tmp_path

test_results = [
    {"name": "a", "wallclock_s": 0.123, "n_assertions": 10},
    {"name": "b", "wallclock_s": 0.456, "n_assertions": 20},
]
write_baseline(test_results)
step("baseline file written", tmp_path.exists())

written = json.loads(tmp_path.read_text())
step_eq("2 entries", len(written), 2)
step_eq("a wallclock", written["a"]["wallclock_s"], 0.123)
step_eq("b assertions", written["b"]["n_assertions"], 20)

rb_mod.BASELINE_PATH = orig_path


# ===========================================================================
# 8. All SUITE entries are real files
# ===========================================================================
section("8. SUITE smoke files exist")
for name, cmd in SUITE:
    # Skip non-file entries (e.g. evals uses "-m", "pytest", ...)
    if cmd[0].startswith("-"):
        step(f"{name}: pytest module entry", True)
        continue
    path = Path(PROJECT_ROOT) / cmd[0]
    step(f"{name}: {path.name} exists", path.exists())


# ===========================================================================
# Summary
# ===========================================================================
print(f"\n=== {passes}/{passes + fails} ok ===")
if fails == 0:
    print("all green")
else:
    print(f"{fails} fail")
    sys.exit(1)