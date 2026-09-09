"""models_discovery_smoke.py — live model discovery (frontend.models_catalog).

Verifies the dynamic-model contract that replaced the hardcoded lists:

  A. Ollama /api/tags — when a local server is running, fetch_models
     returns its REAL installed models (never a hardcoded list); the
     result is cached and `cached_models` serves the same data without
     network. When no server is running, discovery degrades to the
     curated fallback with status "unreachable" — never raises.
  B. Dead endpoint — an unreachable base_url yields status
     "unreachable" + fallback models, and must complete quickly
     (hard timeouts, no hang).
  C. Cache — clear_models_cache() forces a re-fetch; a second call
     within TTL is served from cache.

Run:  PYTHONPATH=docs python3 docs/runtime/smokes/models_discovery_smoke.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

# Isolate HOME so imports never touch a real config/keychain.
_TMP = Path(tempfile.mkdtemp(prefix="models-discovery-"))
os.environ["HOME"] = str(_TMP)
os.environ["LABOURIOUS_TEST"] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from frontend.models_catalog import (  # noqa: E402
    clear_models_cache,
    cached_models,
    fetch_models,
    fetch_models_result,
)

ok = 0
fails: list[str] = []


def step(desc: str, cond: bool) -> None:
    global ok
    if cond:
        ok += 1
        print(f"  ✓ {desc}")
    else:
        fails.append(desc)
        print(f"  ✗ FAIL {desc}")


def main() -> int:
    print("=== A. Ollama discovery ===")
    clear_models_cache()
    started = time.monotonic()
    result = fetch_models_result("ollama")
    elapsed = time.monotonic() - started
    step("completes fast (<6s ceiling)", elapsed < 6.0)
    step("status is ok or unreachable", result.status in ("ok", "unreachable"))
    step("display models never empty",
         len(result.display_models) > 0)

    if result.status == "ok":
        step("live models present", len(result.models) > 0)
        step("source is 'live'", result.source == "live")
        print(f"      (live: {', '.join(list(result.models)[:4])} · {result.detail})")
        # Cache must now serve the same result without network.
        cached = cached_models("ollama")
        step("cached_models serves the live result",
             cached is not None and cached.models == result.models)
        again = fetch_models("ollama")
        step("second fetch returns same models (cache)", again == result.models)
    else:
        step("fallback equals curated list",
             result.display_models == result.fallback)
        print(f"      (no local ollama · detail: {result.detail[:70]})")

    print("=== B. Dead endpoint degrades gracefully ===")
    clear_models_cache()
    started = time.monotonic()
    dead = fetch_models_result("ollama", base_url="http://127.0.0.1:9", force=True)
    elapsed = time.monotonic() - started
    step("status unreachable", dead.status == "unreachable")
    step("fallback models still offered", len(dead.display_models) > 0)
    step("degrades fast (<6s, no hang)", elapsed < 6.0)
    step("detail mentions reachability", "reach" in dead.detail.lower())

    print("=== C. Unknown provider is safe ===")
    clear_models_cache()
    weird = fetch_models_result("not-a-real-provider")
    step("unknown provider does not raise", weird.status in ("error", "unreachable"))

    print(f"\n{'=' * 60}")
    print(f"models-discovery — {ok} passed, {len(fails)} failed")
    print("=" * 60)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
