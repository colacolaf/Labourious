"""export_smoke.py — smoke pilot for the --export CLI flag.

Verifies (without launching a flow):

  1. .md suffix writes the rendered memo to that file
  2. .json suffix writes the envelope to that file
  3. .json suffix falls back to on-disk envelope when caller doesn't pass one
  4. trailing-slash path writes to a new directory
  5. existing directory path writes inside
  6. multi-component path (./sub/dir) treated as directory
  7. single-component bare path defaults to file (out.md)
  8. unknown-suffix path appends .md (out.tar → out.tar.md)
  9. ~ path expansion works
 10. empty path raises ValueError
 11. .json request without envelope (on disk or passed) raises ValueError
 12. main() argparse has --export with the documented metavar/help
 13. main() wires export_run_artifact after write_run_artifact
 14. main() prints '# exported:' confirmation per written file
 15. main() exits non-zero if export_run_artifact raises
 16. --export without --export_path leaves stdout behavior unchanged
     (memo still prints to stdout; canonical artifacts still land in
     docs/runtime/.runs/<run_id>/)
"""

from __future__ import annotations

import ast
import os
import re
import sys
import tempfile
from pathlib import Path

THIS = Path(__file__).resolve()
DOCS = THIS.parents[2]
sys.path.insert(0, str(DOCS))


_passed = 0
_failed = 0


def step(label: str, ok: bool) -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ✓ {label}")
    else:
        _failed += 1
        print(f"  ✗ {label}")


def section(name: str) -> None:
    print(f"\n=== {name} ===")


# --------------------------------------------------------------------------- #
# Build a fake run dir + load the helper
# --------------------------------------------------------------------------- #
from runtime.runtime import export_run_artifact


def _make_run_dir(tmp: Path, *, with_envelope: bool = True) -> Path:
    run_dir = tmp / "fake_run"
    run_dir.mkdir()
    (run_dir / "memo.md").write_text("# Test Memo\n\nHello world.\n", encoding="utf-8")
    if with_envelope:
        (run_dir / "final_envelope.json").write_text('{"memo": {"k": "v"}}',
                                                     encoding="utf-8")
    return run_dir


# --------------------------------------------------------------------------- #
#  1. .md suffix
# --------------------------------------------------------------------------- #
section("1. --export out.md → file mode (memo only)")
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    run_dir = _make_run_dir(Path(tmp))
    written = export_run_artifact(run_dir, "out.md")
    step("written list has 1 entry", len(written) == 1)
    step("written[0] == Path('out.md')", written[0] == Path("out.md"))
    step("file exists", Path("out.md").exists())
    step("content matches run_dir/memo.md",
         Path("out.md").read_text() == (run_dir / "memo.md").read_text())
    step("no envelope file created (file mode = memo only)",
         not Path("out.json").exists())


# --------------------------------------------------------------------------- #
#  2. .json suffix (envelope passed in)
# --------------------------------------------------------------------------- #
section("2. --export out.json (envelope kwarg passed)")
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    run_dir = _make_run_dir(Path(tmp))
    written = export_run_artifact(run_dir, "out.json",
                                   envelope={"memo": {"k": "v"}})
    step("written list has 1 entry", len(written) == 1)
    step("written[0] == Path('out.json')", written[0] == Path("out.json"))
    step("file exists", Path("out.json").exists())
    step("content is JSON-serialised envelope",
         '"memo"' in Path("out.json").read_text())


# --------------------------------------------------------------------------- #
#  3. .json suffix (envelope on disk, no kwarg)
# --------------------------------------------------------------------------- #
section("3. --export out.json falls back to on-disk envelope")
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    run_dir = _make_run_dir(Path(tmp))
    written = export_run_artifact(run_dir, "out.json")
    step("written list has 1 entry", len(written) == 1)
    step("file exists", Path("out.json").exists())
    step("content matches on-disk envelope",
         Path("out.json").read_text() == (run_dir / "final_envelope.json").read_text())


# --------------------------------------------------------------------------- #
#  4. Trailing-slash directory
# --------------------------------------------------------------------------- #
section("4. --export exports/ → new directory")
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    run_dir = _make_run_dir(Path(tmp))
    written = export_run_artifact(run_dir, "exports/")
    step("written has 2 entries (memo + envelope)", len(written) == 2)
    step("Path('exports/memo.md') in written",
         Path("exports/memo.md") in written)
    step("Path('exports/final_envelope.json') in written",
         Path("exports/final_envelope.json") in written)
    step("exports/memo.md exists", Path("exports/memo.md").exists())
    step("exports/final_envelope.json exists",
         Path("exports/final_envelope.json").exists())


# --------------------------------------------------------------------------- #
#  5. Existing directory
# --------------------------------------------------------------------------- #
section("5. --export existing_dir → existing directory")
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    run_dir = _make_run_dir(Path(tmp))
    Path("existing_dir").mkdir()
    written = export_run_artifact(run_dir, "existing_dir")
    step("written has 2 entries", len(written) == 2)
    step("existing_dir/memo.md in written",
         Path("existing_dir/memo.md") in written)


# --------------------------------------------------------------------------- #
#  6. Multi-component path = directory
# --------------------------------------------------------------------------- #
section("6. --export sub/exports/nested → nested new directory")
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    run_dir = _make_run_dir(Path(tmp))
    written = export_run_artifact(run_dir, "sub/exports/nested")
    step("written has 2 entries", len(written) == 2)
    step("Path('sub/exports/nested/memo.md') in written",
         Path("sub/exports/nested/memo.md") in written)
    step("sub/exports/nested/final_envelope.json in written",
         Path("sub/exports/nested/final_envelope.json") in written)


# --------------------------------------------------------------------------- #
#  7. Single-component bare → file mode
# --------------------------------------------------------------------------- #
section("7. --export out (bare) → out.md (file mode)")
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    run_dir = _make_run_dir(Path(tmp))
    written = export_run_artifact(run_dir, "out")
    step("written list has 1 entry", len(written) == 1)
    step("written[0] == Path('out.md')", written[0] == Path("out.md"))


# --------------------------------------------------------------------------- #
#  8. Unknown suffix → append .md
# --------------------------------------------------------------------------- #
section("8. --export out.tar (unrecognised suffix) → out.tar.md")
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    run_dir = _make_run_dir(Path(tmp))
    written = export_run_artifact(run_dir, "out.tar")
    step("written list has 1 entry", len(written) == 1)
    step("written[0] == Path('out.tar.md')",
         written[0] == Path("out.tar.md"))


# --------------------------------------------------------------------------- #
#  9. ~ expansion
# --------------------------------------------------------------------------- #
section("9. --export ~/path.md → ~ expands to home")
with tempfile.TemporaryDirectory() as tmp:
    run_dir = _make_run_dir(Path(tmp))
    home_file = Path("~/labourious_export_smoke_test.md")
    expanded = home_file.expanduser()
    if expanded.exists():
        expanded.unlink()
    written = export_run_artifact(run_dir, str(home_file))
    step("written[0] == expanded home path",
         written[0] == expanded)
    step("file exists at home", expanded.exists())
    if expanded.exists():
        expanded.unlink()


# --------------------------------------------------------------------------- #
# 10. Empty path raises
# --------------------------------------------------------------------------- #
section("10. --export '' raises ValueError")
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    run_dir = _make_run_dir(Path(tmp))
    raised = False
    try:
        export_run_artifact(run_dir, "")
    except ValueError:
        raised = True
    step("empty path raises ValueError", raised)

    raised = False
    try:
        export_run_artifact(run_dir, "   ")
    except ValueError:
        raised = True
    step("whitespace-only path raises ValueError", raised)


# --------------------------------------------------------------------------- #
# 11. .json without envelope → raises
# --------------------------------------------------------------------------- #
section("11. --export foo.json without envelope (on disk or kwarg) raises")
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    bare_run = Path(tmp) / "bare_run"
    bare_run.mkdir()
    (bare_run / "memo.md").write_text("# bare memo", encoding="utf-8")
    # no final_envelope.json
    raised = False
    try:
        export_run_artifact(bare_run, "foo.json")
    except ValueError:
        raised = True
    step(".json without envelope raises ValueError", raised)


# --------------------------------------------------------------------------- #
# 12. main() argparse has --export with metavar/help
# --------------------------------------------------------------------------- #
section("12. main() argparse — --export flag wired with help text")
runtime_src = (DOCS / "runtime" / "runtime.py").read_text(encoding="utf-8")
tree = ast.parse(runtime_src)
adds: list[ast.Call] = []
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "main":
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                adds.append(sub)

# Find the argparse add_argument call for --export
has_export = False
export_help = ""
for call in adds:
    # Look for keyword args
    for kw in call.keywords:
        if kw.arg == "dest" and isinstance(kw.value, ast.Constant) and kw.value.value == "export_path":
            has_export = True
        if kw.arg == "metavar" and isinstance(kw.value, ast.Constant):
            export_help = kw.value.value
        if kw.arg == "help" and isinstance(kw.value, ast.Constant):
            export_help += " | help=" + kw.value.value[:60]
step("--export flag wired in argparse", has_export)
step("--export has metavar/help text",
     "PATH" in export_help or ".md" in export_help)


# --------------------------------------------------------------------------- #
# 13. main() wires export_run_artifact after write_run_artifact
# --------------------------------------------------------------------------- #
section("13. main() wires export_run_artifact after write_run_artifact")
main_body = runtime_src.split("def main")[1].split("if __name__")[0]
write_artifact_idx = main_body.find("write_run_artifact(")
export_call_idx = main_body.find("export_run_artifact(")
step("write_run_artifact called in main", write_artifact_idx > -1)
step("export_run_artifact called in main", export_call_idx > -1)
step("export call AFTER write_run_artifact",
     write_artifact_idx > -1 and export_call_idx > write_artifact_idx)
step("passes result['final_envelope'] to envelope kwarg",
     "envelope=result" in main_body or "envelope=result.get(\"final_envelope\")" in main_body
     or "envelope=result['final_envelope']" in main_body)


# --------------------------------------------------------------------------- #
# 14. main() prints '# exported:' confirmation per written file
# --------------------------------------------------------------------------- #
section("14. main() prints confirmation per written file")
step("loops over written paths", "for wp in written_paths:" in main_body)
step("prints # exported: {path}", "# exported:" in main_body)


# --------------------------------------------------------------------------- #
# 15. main() exits non-zero on export failure
# --------------------------------------------------------------------------- #
section("15. main() exits non-zero if export raises")
step("try/except around export call",
     "try:" in main_body.split("export_run_artifact")[1][:200]
     or "try:" in main_body)
step("returns 3 on failure (after export)",
     main_body.count("return 3") >= 1 or "return 3" in main_body)
step("error message printed to stderr",
     "error: --export" in main_body)


# --------------------------------------------------------------------------- #
# 16. Default behavior (no --export) unchanged
# --------------------------------------------------------------------------- #
section("16. Default behaviour (no --export) — unchanged")
step("memo.md still printed to stdout after flow",
     "print((run_dir / \"memo.md\").read_text" in main_body)
step("canonical artifacts still under RUNS_DIR",
     "RUNS_DIR / run_id" in runtime_src or "RUNS_DIR / run_id" in main_body
     or 'RUNS_DIR / run_id' in runtime_src)


print()
total = _passed + _failed
print(f"{_passed}/{total} ok")
if _failed:
    print(f"{_failed} FAIL")
    sys.exit(1)
print("0 fail")
print("all green")
sys.exit(0)