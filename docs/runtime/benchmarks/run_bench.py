"""
Run benchmark suite: times smoke tests and writes durations to a JSON baseline.

Usage:
    PYTHONPATH=docs python3 docs/runtime/benchmarks/run_bench.py           # run + print
    PYTHONPATH=docs python3 docs/runtime/benchmarks/run_bench.py --write   # run + write baseline.json
    PYTHONPATH=docs python3 docs/runtime/benchmarks/run_bench.py --check   # run + compare vs baseline

Exit code 0 if within 2× of baseline (or no baseline); exit code 1 if any
benchmark exceeds 2× the baseline wallclock.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DOCS = os.path.join(PROJECT_ROOT, "docs")
BASELINE_PATH = Path(os.path.dirname(__file__)) / "baseline.json"

# ---------------------------------------------------------------------------
# Suite: which smokes to benchmark (representative selection across layers)
# ---------------------------------------------------------------------------
SUITE: list[tuple[str, list[str]]] = [
    # ── Adapter / runtime layer ──
    ("per_agent_routing",  ["docs/runtime/smokes/per_agent_routing_smoke.py"]),
    ("slash_commands",     ["docs/runtime/smokes/slash_commands_smoke.py"]),
    ("tui_hotkeys",        ["docs/runtime/smokes/tui_hotkeys_smoke.py"]),
    ("timeout_guard",      ["docs/runtime/smokes/timeout_smoke.py"]),
    ("settings_roundtrip", ["docs/runtime/smokes/settings_roundtrip_smoke.py"]),
    ("stream_command",     ["docs/runtime/smokes/stream_command_smoke.py"]),
    ("activity_eta",       ["docs/runtime/smokes/activity_eta_smoke.py"]),
    ("connector_strip",    ["docs/runtime/smokes/connector_strip_e2e_smoke.py"]),
    ("wizard_e2e",         ["docs/runtime/smokes/wizard_e2e_smoke.py"]),
    ("wizard_providers",   ["docs/runtime/smokes/wizard_providers_smoke.py"]),
    ("settings_key",       ["docs/runtime/smokes/settings_providers_key_smoke.py"]),
    # ── Frontend / UI layer ──
    ("history_pagination", ["docs/runtime/smokes/history_pagination_smoke.py"]),
    ("history_drill_rerun",["docs/runtime/smokes/history_drill_rerun_smoke.py"]),
    ("history_search_export", ["docs/runtime/smokes/history_search_export_smoke.py"]),
    ("structured_diff",    ["docs/runtime/smokes/structured_diff_smoke.py"]),
    ("cost_footer",        ["docs/runtime/smokes/cost_footer_smoke.py"]),
    ("ticker_shortcuts",   ["docs/runtime/smokes/ticker_shortcuts_smoke.py"]),
    # ── Integration / connector ──
    ("connectors_e2e",     ["docs/runtime/smokes/connectors_e2e_smoke.py"]),
    ("f1_parallel",        ["docs/runtime/smokes/f1_parallel_smoke.py"]),
    ("retry",              ["docs/runtime/smokes/retry_smoke.py"]),
    ("resume",             ["docs/runtime/smokes/resume_smoke.py"]),
    # ── Eval suite ──
    ("evals",              ["-m", "pytest", "docs/runtime/evals/", "-q"]),
]


def run_bench(name: str, cmd: list[str]) -> dict[str, Any]:
    """Run a single benchmark and return {name, wallclock_s, exit_code, n_assertions}."""
    t0 = time.monotonic()
    env = os.environ.copy()
    env["PYTHONPATH"] = DOCS
    result = subprocess.run(
        [sys.executable, *cmd],
        capture_output=True, text=True, timeout=120,
        cwd=PROJECT_ROOT, env=env,
    )
    elapsed = time.monotonic() - t0

    # Parse assertion count from output
    n_assertions = 0
    for line in result.stdout.splitlines():
        line = line.strip()
        # Common "all green", "=== 35/35 ok ===", "N passed" patterns
        if line == "all green":
            # Already counted above
            pass
        elif "/" in line and "ok" in line:
            try:
                parts = line.replace("===", "").strip().split("/")
                n_assertions += int(parts[0])
            except (ValueError, IndexError):
                pass
        elif "passed" in line and "failed" in line:
            import re
            m = re.search(r"(\d+) passed", line)
            if m:
                n_assertions += int(m.group(1))

    return {
        "name": name,
        "wallclock_s": round(elapsed, 3),
        "exit_code": result.returncode,
        "n_assertions": n_assertions,
    }


def load_baseline() -> dict[str, dict]:
    """Load baseline.json if it exists."""
    if BASELINE_PATH.exists():
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return {}


def write_baseline(results: list[dict]) -> None:
    """Write results as the new baseline."""
    bl = {r["name"]: {"wallclock_s": r["wallclock_s"], "n_assertions": r["n_assertions"]}
          for r in results}
    BASELINE_PATH.write_text(json.dumps(bl, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\n# baseline written: {BASELINE_PATH}")


def check_against_baseline(results: list[dict], baseline: dict) -> tuple[bool, list[str]]:
    """Compare current results against baseline. Return (all_ok, failures)."""
    failures: list[str] = []
    for r in results:
        name = r["name"]
        bl = baseline.get(name)
        if bl is None:
            continue  # no baseline for this benchmark yet
        ratio = r["wallclock_s"] / max(bl["wallclock_s"], 0.001)
        if ratio > 2.0:
            msg = (
                f"REGRESSION: {name} — {r['wallclock_s']:.3f}s "
                f"({ratio:.1f}× baseline {bl['wallclock_s']:.3f}s)"
            )
            failures.append(msg)
    return len(failures) == 0, failures


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "print"

    print(f"# benchmark suite — {len(SUITE)} tests")
    t0 = time.monotonic()
    results: list[dict] = []

    for name, cmd in SUITE:
        sys.stdout.write(f"  {name:<28s} ... ")
        sys.stdout.flush()
        result = run_bench(name, cmd)
        results.append(result)
        status = "✅" if result["exit_code"] == 0 else "❌"
        print(f"{status}  {result['wallclock_s']:.3f}s  ({result['n_assertions']} assertions)")

    total = time.monotonic() - t0
    print(f"\n# total: {total:.1f}s  ({len(results)} benchmarks)")

    if mode == "--write":
        write_baseline(results)

    if mode == "--check":
        baseline = load_baseline()
        if not baseline:
            print("# no baseline found — run with --write first")
            return 0
        ok, failures = check_against_baseline(results, baseline)
        if failures:
            print("\n--- REGRESSIONS ---")
            for f in failures:
                print(f"  ❌ {f}")
            return 1
        print("\n# all benchmarks within 2× baseline ✅")

    # Return non-zero if any benchmark failed
    return 1 if any(r["exit_code"] != 0 for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())