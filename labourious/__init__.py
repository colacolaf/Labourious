"""labourious — top-level package shim.

The implementation lives under ``docs.runtime`` and ``docs.frontend``
(those are the installable Python packages; the installed package name
in pip is the same ``docs``). The ``labourious`` package is a thin
shim so end users can ``import labourious`` or run
``python -m labourious`` without remembering which sub-package their
public API lives in.

Why two packages?
  The project grew inside ``docs/`` because the early shape was a
  documentation-style research repo with prompts + architecture under
  one root. When we started shipping it as a tool, we needed a
  proper Python package — but moving ~30k LOC out of ``docs/`` would
  have churned every import and pilot. So the smallest-blast-radius
  shipping fix: declare ``docs`` as a real Python package alongside a
  thin ``labourious`` shim. Both install together via ``pyproject.toml``.

What's here:
- ``__version__`` — version string
- ``run`` — entry-point that runs the CLI (`python -m labourious …`)
- ``main`` — alias of ``run.main`` for shell-script style imports
- ``__all__`` — short public surface

Anything *not* listed in ``__all__`` is implementation-detail and
should be imported from ``docs.runtime`` / ``docs.frontend`` directly.
"""
from __future__ import annotations

try:
    from docs.runtime import runtime as _runtime  # noqa: F401
except Exception:  # pragma: no cover - allows docs import to fail without crashing __init__
    _runtime = None  # type: ignore[assignment]


__version__ = "0.1.0-dev"


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. ``python -m labourious`` calls this.

    Equivalent to ``python docs/runtime/runtime.py``; the shim just
    lets the installed package expose a friendlier entry point.

    ``argv`` is accepted for shell-script style imports. The runtime
    itself reads ``sys.argv`` directly, so when ``argv`` is None
    (the normal ``python -m labourious …`` case), we re-point
    ``sys.argv`` to the supplied list before calling through. When
    ``argv`` is None, we leave ``sys.argv`` alone so the runtime sees
    whatever the OS handed us.
    """
    if _runtime is None:
        raise RuntimeError(
            "labourious runtime could not import docs.runtime — was the "
            "package installed correctly? Try `pip install -e .` from "
            "the project root."
        )
    if argv is not None:
        # Re-point sys.argv so the runtime's argparse reads what we
        # were given. Restore on exit so callers (and tests) aren't
        # surprised if they reuse globals.
        import sys as _sys
        prev = _sys.argv
        try:
            _sys.argv = [prev[0]] + list(argv)
            return _runtime.main()
        finally:
            _sys.argv = prev
    # Default: just call through. Runtime reads sys.argv.
    return _runtime.main()


if _runtime is not None:
    run = main  # alias used by some docs / test scripts

__all__ = ["__version__", "main", "run"]
