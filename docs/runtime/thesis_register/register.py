#!/usr/bin/env python3
"""
register.py — thesis register SQLite wrapper.

Public API:
    ThesisRegister(db_path).read_thesis(ticker, since_days=...)
    ThesisRegister(db_path).diff_thesis(ticker, new_thesis_text)
    ThesisRegister(db_path).write_thesis(ticker, thesis_text, conviction, bottom_line, evidence_urls, flow_id)
    ThesisRegister(db_path).add_update(ticker, what_changed, new_thesis_text=None, deltas=None, reason=None)
    ThesisRegister(db_path).add_catalyst(ticker, event, expected_date, what_to_watch)
    ThesisRegister(db_path).resolve_catalyst(id, resolved_date, outcome)

CLI:
    python register.py show NVDA
    python register.py catalysts AAPL
    python register.py write NVDA --thesis "..." --conviction 4 --bottom-line '{...}' --flow f1
    python register.py update NVDA --changed "..." --reason "..."
    python register.py add-catalyst NVDA --event "Q4 earnings" --expected 2026-11-20 --watch "channel inventory margin"
    python register.py resolve-catalyst <id> --date 2026-11-20 --outcome "..."
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent / "theses.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class ThesisRegister:
    def __init__(self, db_path: str | os.PathLike[str] | None = None):
        self.db_path = Path(db_path) if db_path else Path(os.environ.get("THESIS_REGISTER_DB", DEFAULT_DB))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row

    def _ensure_schema(self) -> None:
        if not self.db_path.exists() or self.db_path.stat().st_size == 0:
            with sqlite3.connect(str(self.db_path)) as c:
                c.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    # ---------------------------------------------------------------- #
    # read
    # ---------------------------------------------------------------- #
    def read_thesis(self, ticker: str, since_days: int | None = None) -> dict | list | None:
        cur = self._conn.cursor()
        if since_days:
            cutoff = (dt.date.today() - dt.timedelta(days=since_days)).isoformat()
            rows = cur.execute(
                "SELECT * FROM theses WHERE ticker=? AND date>=? ORDER BY version DESC",
                (ticker.upper(), cutoff),
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT * FROM v_latest_thesis WHERE ticker=?",
                (ticker.upper(),),
            ).fetchall()
            if not rows:
                # Try plain lookup
                rows = cur.execute(
                    "SELECT * FROM theses WHERE ticker=? ORDER BY id DESC LIMIT 1",
                    (ticker.upper(),),
                ).fetchall()
        return [dict(r) for r in rows] if rows else None

    # ---------------------------------------------------------------- #
    # diff
    # ---------------------------------------------------------------- #
    def diff_thesis(self, ticker: str, new_thesis_text: str) -> dict | None:
        prior = self.read_thesis(ticker)
        if not prior:
            return {"changed": True, "reason": "no prior thesis", "prior": None, "deltas": {}}
        latest = prior[0] if isinstance(prior, list) else prior
        deltas: dict = {}
        if latest.get("thesis_text") != new_thesis_text:
            deltas["thesis_text"] = {
                "prior": latest.get("thesis_text"),
                "new": new_thesis_text,
            }
        return {"changed": bool(deltas), "prior": latest, "deltas": deltas}

    # ---------------------------------------------------------------- #
    # write (returns the new id)
    # ---------------------------------------------------------------- #
    def write_thesis(self, ticker: str, thesis_text: str, conviction: int,
                     bottom_line: dict, evidence_urls: list[str],
                     flow_id: str) -> dict:
        """Insert a new thesis row and return {thesis_id, version} so callers
        can both identify the row (id) and surface the human-readable version
        (1, 2, 3, …) to the TUI's thesis-snapshot chip.
        """
        if isinstance(bottom_line, dict):
            bottom_line = json.dumps(bottom_line)
        if isinstance(evidence_urls, list):
            evidence_urls = json.dumps(evidence_urls)
        # Determine next version
        cur = self._conn.cursor()
        cur.execute(
            "SELECT MAX(version) FROM theses WHERE ticker=? AND flow_id=?",
            (ticker.upper(), flow_id),
        )
        max_v = cur.fetchone()[0] or 0
        cur.execute(
            """INSERT INTO theses
               (ticker, date, thesis_text, conviction, bottom_line, evidence_urls, flow_id, version)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                ticker.upper(),
                dt.date.today().isoformat(),
                thesis_text,
                conviction,
                bottom_line,
                evidence_urls,
                flow_id,
                max_v + 1,
            ),
        )
        self._conn.commit()
        return {"thesis_id": cur.lastrowid, "version": max_v + 1}

    # ---------------------------------------------------------------- #
    # update
    # ---------------------------------------------------------------- #
    def add_update(self, ticker: str, what_changed: str,
                   new_thesis_text: str | None = None,
                   deltas: dict | None = None,
                   reason: str | None = None) -> int:
        prior = self.read_thesis(ticker)
        if not prior:
            raise ValueError(f"No prior thesis for {ticker}; cannot add update.")
        latest = prior[0] if isinstance(prior, list) else prior
        thesis_id = latest["id"]
        if isinstance(deltas, dict):
            deltas = json.dumps(deltas)
        cur = self._conn.cursor()
        cur.execute(
            """INSERT INTO updates
               (thesis_id, date, what_changed, new_thesis_text, deltas, reason)
               VALUES (?,?,?,?,?,?)""",
            (thesis_id, dt.date.today().isoformat(),
             what_changed, new_thesis_text, deltas, reason),
        )
        self._conn.commit()
        return cur.lastrowid

    # ---------------------------------------------------------------- #
    # catalyst add / resolve
    # ---------------------------------------------------------------- #
    def add_catalyst(self, ticker: str, event: str,
                     expected_date: str | None = None,
                     what_to_watch: str | None = None) -> int:
        cur = self._conn.cursor()
        cur.execute(
            """INSERT INTO catalysts
               (ticker, event, expected_date, what_to_watch)
               VALUES (?,?,?,?)""",
            (ticker.upper(), event, expected_date, what_to_watch),
        )
        self._conn.commit()
        return cur.lastrowid

    def resolve_catalyst(self, catalyst_id: int, resolved_date: str,
                         outcome: str) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """UPDATE catalysts SET resolved_date=?, resolved_outcome=?
               WHERE id=?""",
            (resolved_date, outcome, catalyst_id),
        )
        self._conn.commit()

    def list_open_catalysts(self, ticker: str | None = None) -> list[dict]:
        """Return all unresolved catalysts (resolved_date IS NULL).

        If ``ticker`` is supplied, filter to that ticker only. Otherwise
        return every open catalyst across the universe — used by f10's
        daily briefing to populate the watchpoints block.

        Returned shape: list of dicts with keys ``id``, ``ticker``,
        ``event``, ``expected_date``, ``what_to_watch``, ``created_at``.
        Ordered by ``expected_date`` (NULL last) so the user sees the
        nearest catalyst first.
        """
        cur = self._conn.cursor()
        if ticker is not None:
            rows = cur.execute(
                """SELECT id, ticker, event, expected_date, what_to_watch, created_at
                   FROM catalysts
                   WHERE ticker=? AND resolved_date IS NULL
                   ORDER BY (expected_date IS NULL), expected_date, id""",
                (ticker.upper(),),
            ).fetchall()
        else:
            rows = cur.execute(
                """SELECT id, ticker, event, expected_date, what_to_watch, created_at
                   FROM catalysts
                   WHERE resolved_date IS NULL
                   ORDER BY (expected_date IS NULL), expected_date, id""",
            ).fetchall()
        return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> int:
    p = argparse.ArgumentParser(description="Labourious thesis_register CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    show = sub.add_parser("show", help="Show a ticker's theses")
    show.add_argument("ticker")
    show.add_argument("--since", type=int, help="Days back")

    cat = sub.add_parser("catalysts", help="List unresolved catalysts for a ticker")
    cat.add_argument("ticker")

    write = sub.add_parser("write", help="Write a new versioned thesis")
    write.add_argument("ticker")
    write.add_argument("--thesis", required=True)
    write.add_argument("--conviction", type=int, required=True)
    write.add_argument("--bottom-line", required=True,
                       help="JSON string or path to JSON file")
    write.add_argument("--flow", required=True)
    write.add_argument("--evidence-urls", default="[]")

    upd = sub.add_parser("update", help="Record what changed since prior thesis")
    upd.add_argument("ticker")
    upd.add_argument("--changed", required=True)
    upd.add_argument("--reason")

    addc = sub.add_parser("add-catalyst", help="Add a watchlist catalyst")
    addc.add_argument("ticker")
    addc.add_argument("--event", required=True)
    addc.add_argument("--expected", help="YYYY-MM-DD")
    addc.add_argument("--watch")

    resc = sub.add_parser("resolve-catalyst", help="Mark a catalyst resolved")
    resc.add_argument("catalyst_id", type=int)
    resc.add_argument("--date", required=True, help="YYYY-MM-DD")
    resc.add_argument("--outcome", required=True)

    args = p.parse_args()
    reg = ThesisRegister()

    if args.cmd == "show":
        rows = reg.read_thesis(args.ticker, since_days=args.since)
        if not rows:
            print(f"# no theses for {args.ticker}")
            return 0
        for row in rows:
            print(json.dumps({
                k: row[k] for k in (
                    "id", "ticker", "date", "thesis_text", "conviction",
                    "bottom_line", "evidence_urls", "flow_id", "version"
                )
            }, indent=2))
        return 0

    if args.cmd == "catalysts":
        rows = reg._conn.execute(
            "SELECT * FROM catalysts WHERE ticker=? AND resolved_date IS NULL ORDER BY expected_date",
            (args.ticker.upper(),),
        ).fetchall()
        for row in rows:
            print(json.dumps(dict(row), indent=2))
        return 0

    if args.cmd == "write":
        # bottom_line may be a JSON string or a file path
        bl = args.bottom_line
        if os.path.exists(bl):
            bl = open(bl).read()
        new_id = reg.write_thesis(
            ticker=args.ticker,
            thesis_text=args.thesis,
            conviction=args.conviction,
            bottom_line=bl,
            evidence_urls=json.loads(args.evidence_urls),
            flow_id=args.flow,
        )
        print(f"# wrote theses row {new_id} for {args.ticker} (flow {args.flow})")
        return 0

    if args.cmd == "update":
        new_id = reg.add_update(
            ticker=args.ticker,
            what_changed=args.changed,
            reason=args.reason,
        )
        print(f"# wrote updates row {new_id} for {args.ticker}")
        return 0

    if args.cmd == "add-catalyst":
        new_id = reg.add_catalyst(
            ticker=args.ticker,
            event=args.event,
            expected_date=args.expected,
            what_to_watch=args.watch,
        )
        print(f"# wrote catalysts row {new_id} for {args.ticker}")
        return 0

    if args.cmd == "resolve-catalyst":
        reg.resolve_catalyst(
            catalyst_id=args.catalyst_id,
            resolved_date=args.date,
            outcome=args.outcome,
        )
        print(f"# resolved catalyst {args.catalyst_id}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
