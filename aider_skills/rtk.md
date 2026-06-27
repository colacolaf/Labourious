# RTK — TOKEN KILLER & OUTPUT FILTER

## Purpose
Reduce token waste in CLI/dev operations. Proxy layer that strips noise from
command output before it reaches the context window.

## Core Behavior
- All shell commands route through RTK proxy automatically (via hook)
- RTK filters: ANSI codes, progress bars, verbose build logs, duplicate lines
- RTK passes: error messages, final status, warnings, actionable output
- Token savings: 60-90% on common dev ops (git, pytest, npm, docker)

## Key Commands
```bash
rtk gain              # Show token savings analytics
rtk gain --history    # Command history with savings
rtk discover          # Find missed RTK opportunities in history
rtk proxy <cmd>       # Run command raw without filtering (debug)
```

## Filter Rules
STRIP from output:
- Progress indicators (`[=====>   ]`, `Downloading...`, `Installing...`)
- ANSI escape codes
- Redundant repetition (same line >3x)
- Verbose debug lines when summary exists
- Timestamps unless error/warning

ALWAYS KEEP:
- Error messages (exact, verbatim)
- Warning lines
- Final status (`PASSED`, `FAILED`, `SUCCESS`, `ERROR`)
- File paths in errors
- Exit codes

## Integration
- Hook-based: transparent to user, zero overhead
- If `rtk gain` fails → possible name collision with `reachingforthejack/rtk`
- Verify: `which rtk` and `rtk --version`

## Token Budget Application
When generating shell commands: prefer single-pass commands over pipelines that
produce verbose intermediate output. Example:
- Avoid: `pip install -r requirements.txt` (verbose) when `pip install -q -r requirements.txt` suffices
- Prefer: `pytest -q` over `pytest -v` unless debugging
