"""
history_io.py — read the thesis register for the History modal.

Wraps `docs/runtime/thesis_register/register.py` with a flat list view
(`read_theses_all`) and a per-thesis diff baseline (`diff_with_prior`)
that the History modal needs.

Public surface:
    ThesisRow              -> dataclass with all display fields
    read_theses_all(db,    -> list[ThesisRow], newest first (across tickers)
                    *, limit=None)
    diff_with_prior(row,   -> dict of {field, prior, current, delta_marker}
                    all_rows)
    DEFAULT_DB             -> Path to the canonical DB

No mutations. This module is read-only — the modal does not write to the
register from inside the TUI. (The runtime writes when an f1 run finishes.)
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


DEFAULT_DB = Path(
    os.environ.get(
        "THESIS_REGISTER_DB",
        Path(__file__).resolve().parents[1] / "runtime" / "thesis_register" / "theses.db",
    )
)


# --------------------------------------------------------------- types
Placement = Literal["BUY", "HOLD", "SELL", "ABSTAIN"]


@dataclass(frozen=True)
class ThesisRow:
    """One thesis row, view-model for the History modal.

    All JSON-encoded fields are pre-parsed so the modal never has to
    touch json.loads.
    """
    id: int
    ticker: str
    date: str                # YYYY-MM-DD
    datetime: str            # ISO 8601 timestamp (with time)
    flow_id: str
    version: int
    conviction: int          # 1..5 (→ confidence percentage = conviction*20)
    placement: Placement
    price: float | None
    base_case: float | None
    bottom_line_text: str
    thesis_text: str
    evidence_urls: list[dict]   # {source: str, url: str, snippet: str or None}
    model: str | None
    paid_for: bool           # did it use a paid-for agent?

    @property
    def confidence_pct(self) -> int:
        return min(100, max(0, self.conviction * 20))


# --------------------------------------------------------------- helpers
def _parse_bottom_line(raw: str) -> tuple[Placement, float | None, float | None, str]:
    """Parse the JSON-encoded bottom_line column into typed fields.

    Returns (placement, price, base_case, free-text).
    Falls back to sensible defaults on parse failure.
    """
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        return ("ABSTAIN", None, None, raw or "")

    direction = (d.get("direction") or "ABSTAIN").upper()
    placement = direction if direction in ("BUY", "HOLD", "SELL") else "ABSTAIN"
    price = _as_float(d.get("price"))
    base_case = _as_float(d.get("base_case") or d.get("intrinsic_value"))
    text = d.get("text") or d.get("summary") or d.get("thesis") or ""
    return (placement, price, base_case, text)


def _as_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_evidence_urls(raw: str) -> list[dict]:
    """Return a list of {source, url, snippet} dicts."""
    if not raw:
        return []
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        # Some older rows store plain \n-separated URLs
        return [{"source": "url", "url": u.strip(), "snippet": None}
                for u in raw.splitlines() if u.strip()]
    if isinstance(d, list):
        out = []
        for item in d:
            if isinstance(item, str):
                out.append({"source": "url", "url": item, "snippet": None})
            elif isinstance(item, dict):
                out.append({
                    "source": str(item.get("source", "url")),
                    "url": str(item.get("url", "")),
                    "snippet": item.get("snippet"),
                })
        return out
    return []


def _row_to_thesis_row(row: sqlite3.Row) -> ThesisRow:
    placement, price, base, bl_text = _parse_bottom_line(row["bottom_line"])
    return ThesisRow(
        id=int(row["id"]),
        ticker=str(row["ticker"]),
        date=str(row["date"]),
        datetime=str(row["created_at"] or row["date"]),
        flow_id=str(row["flow_id"]),
        version=int(row["version"]),
        conviction=int(row["conviction"]),
        placement=placement,
        price=price,
        base_case=base,
        bottom_line_text=bl_text,
        thesis_text=str(row["thesis_text"] or ""),
        evidence_urls=_parse_evidence_urls(row["evidence_urls"]),
        model=str(row["model"]) if "model" in row.keys() and row["model"] else None,
        paid_for=bool(row["paid_for"]) if "paid_for" in row.keys() and row["paid_for"] is not None else False,
    )


# --------------------------------------------------------------- reads
def read_theses_all(db_path: Path | str = DEFAULT_DB, *, limit: int | None = None,
                    ticker_filter: str | None = None) -> list[ThesisRow]:
    """Return all theses, newest first.

    Sorted by `created_at desc` so cartesian-catalog lookup doesn't lose
    meaning when two theses for the same ticker share the same date.
    """
    p = Path(db_path)
    if not p.exists() or p.stat().st_size == 0:
        return []
    try:
        con = sqlite3.connect(str(p))
        con.row_factory = sqlite3.Row
        # Prefer columns that may not exist in old DBs.
        cols = [r[1] for r in con.execute("PRAGMA table_info(theses)").fetchall()]
        # Add "model" + "paid_for" columns ad-hoc if missing so the SELECT doesn't error
        for col, decl in [
            ("model", "TEXT"), ("paid_for", "INTEGER"),
        ]:
            if col not in cols:
                try:
                    con.execute(f"ALTER TABLE theses ADD COLUMN {col} {decl}")
                except sqlite3.OperationalError:
                    pass
        ticker_clause = ""
        ticker_params: tuple = ()
        if ticker_filter:
            ticker_clause = " WHERE ticker = ?"
            ticker_params = (ticker_filter.upper(),)
        limit_clause = f" LIMIT {int(limit)}" if limit else ""
        rows = con.execute(
            "SELECT id, ticker, date, thesis_text, conviction, bottom_line, "
            "evidence_urls, flow_id, version, created_at, model, paid_for "
            "FROM theses"
            + ticker_clause
            + " ORDER BY created_at DESC, id DESC"
            + limit_clause,
            ticker_params,
        ).fetchall()
        return [_row_to_thesis_row(r) for r in rows]
    except sqlite3.DatabaseError:
        return []
    finally:
        try:
            con.close()
        except Exception:
            pass


def read_theses_page(db_path: Path | str = DEFAULT_DB, *,
                     limit: int = 20,
                     cursor: tuple | None = None,
                     ticker_filter: str | None = None) -> list[ThesisRow]:
    """Keyset-paginated read — newest first.

    `cursor` is a `(created_at, id)` tuple marking the row *after* which to
    continue. Pass the last returned row's `(datetime, id)` to fetch the next
    page. Returns an empty list when the end is reached.

    Ticker filter narrows to a single ticker (case-insensitive), so the
    History modal can page across one symbol without loading the whole table.
    """
    p = Path(db_path)
    if not p.exists() or p.stat().st_size == 0:
        return []
    con = None
    try:
        con = sqlite3.connect(str(p))
        con.row_factory = sqlite3.Row
        # Ensure optional columns exist (mirror read_theses_all)
        cols = [r[1] for r in con.execute("PRAGMA table_info(theses)").fetchall()]
        for col, decl in [("model", "TEXT"), ("paid_for", "INTEGER")]:
            if col not in cols:
                try:
                    con.execute(f"ALTER TABLE theses ADD COLUMN {col} {decl}")
                except sqlite3.OperationalError:
                    pass

        where = []
        params: list = []
        if ticker_filter:
            where.append("ticker = ?")
            params.append(ticker_filter.upper())
        if cursor is not None:
            where.append("(created_at < ? OR (created_at = ? AND id < ?))")
            params.extend([cursor[0], cursor[0], cursor[1]])
        where_clause = f" WHERE {' AND '.join(where)}" if where else ""

        rows = con.execute(
            "SELECT id, ticker, date, thesis_text, conviction, bottom_line, "
            "evidence_urls, flow_id, version, created_at, model, paid_for "
            "FROM theses"
            + where_clause
            + " ORDER BY created_at DESC, id DESC LIMIT ?",
            params + [int(limit)],
        ).fetchall()
        return [_row_to_thesis_row(r) for r in rows]
    except sqlite3.DatabaseError:
        return []
    finally:
        if con is not None:
            try:
                con.close()
            except Exception:
                pass


def list_tickers(db_path: Path | str = DEFAULT_DB) -> list[str]:
    """Distinct tickers in the register, newest-activity first."""
    p = Path(db_path)
    if not p.exists() or p.stat().st_size == 0:
        return []
    con = None
    try:
        con = sqlite3.connect(str(p))
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT ticker, MAX(created_at) AS latest FROM theses "
            "GROUP BY ticker ORDER BY latest DESC"
        ).fetchall()
        return [str(r["ticker"]) for r in rows]
    except sqlite3.DatabaseError:
        return []
    finally:
        if con is not None:
            try:
                con.close()
            except Exception:
                pass


def count_theses(db_path: Path | str = DEFAULT_DB,
                 *, ticker_filter: str | None = None) -> int:
    """Total thesis count, optionally narrowed by ticker."""
    p = Path(db_path)
    if not p.exists() or p.stat().st_size == 0:
        return 0
    con = None
    try:
        con = sqlite3.connect(str(p))
        con.row_factory = sqlite3.Row
        if ticker_filter:
            row = con.execute(
                "SELECT COUNT(*) AS n FROM theses WHERE ticker = ?",
                (ticker_filter.upper(),),
            ).fetchone()
        else:
            row = con.execute("SELECT COUNT(*) AS n FROM theses").fetchone()
        return int(row["n"]) if row else 0
    except sqlite3.DatabaseError:
        return 0
    finally:
        if con is not None:
            try:
                con.close()
            except Exception:
                pass


# --------------------------------------------------------------- diff
def diff_with_prior(row: ThesisRow, all_rows: list[ThesisRow]) -> dict | None:
    """Returns the diff baseline view-model for `row` against the most
    recent prior thesis for the same ticker. None if there's no prior.

    The History modal renders this as a small list of rows:
        field  prior → current   (delta marker)
    """
    # find the most recent prior for the same ticker (excluding self)
    # all_rows is newest-first; the first match that is older than `row`
    # is the immediate prior.
    candidates = [
        r for r in all_rows
        if r.ticker == row.ticker and r.id != row.id
        and (r.datetime, r.id) < (row.datetime, row.id)
    ]
    # Newest-first in all_rows; sort by datetime then id so the relevant
    # "later in time" prior has the earliest index in candidates.
    candidates.sort(key=lambda r: (r.datetime, r.id), reverse=True)
    if not candidates:
        return None
    prior = candidates[0]
    return _compute_diff(prior, row)


def _compute_diff(prior: ThesisRow, current: ThesisRow) -> dict:
    """Pure diff calculation — no DB access."""
    fields = []

    # placement (BUY/HOLD/SELL)
    if prior.placement != current.placement:
        marker = _placement_marker(prior.placement, current.placement)
        fields.append({
            "field": "placement", "prior": prior.placement,
            "current": current.placement, "marker": marker,
        })
    else:
        fields.append({
            "field": "placement", "prior": prior.placement,
            "current": current.placement, "marker": "= same",
        })

    # price (only if both have one)
    if prior.price is not None and current.price is not None:
        if prior.price != current.price:
            pct = (current.price - prior.price) / prior.price * 100
            fields.append({
                "field": "price",
                "prior": f"${prior.price:,.2f}",
                "current": f"${current.price:,.2f}",
                "marker": _pct_marker(pct),
            })
        else:
            fields.append({
                "field": "price",
                "prior": f"${prior.price:,.2f}",
                "current": f"${current.price:,.2f}",
                "marker": "= same",
            })

    # base case
    if prior.base_case is not None or current.base_case is not None:
        prior_str = f"${prior.base_case:,.2f}" if prior.base_case is not None else "—"
        curr_str = f"${current.base_case:,.2f}" if current.base_case is not None else "—"
        fields.append({
            "field": "base case", "prior": prior_str, "current": curr_str,
            "marker": "= same" if prior_str == curr_str else "↻ revised",
        })

    # confidence (conviction 1..5 → percentage)
    if prior.confidence_pct != current.confidence_pct:
        delta = current.confidence_pct - prior.confidence_pct
        sign = "▲" if delta > 0 else "▽"
        fields.append({
            "field": "confidence",
            "prior": f"{prior.confidence_pct}%",
            "current": f"{current.confidence_pct}%",
            "marker": f"{sign} {delta:+d} pp" if delta else "= same",
        })
    else:
        fields.append({
            "field": "confidence",
            "prior": f"{prior.confidence_pct}%",
            "current": f"{current.confidence_pct}%",
            "marker": "= same",
        })

    # citations count
    if len(prior.evidence_urls) != len(current.evidence_urls):
        delta = len(current.evidence_urls) - len(prior.evidence_urls)
        sign = "+" if delta > 0 else "-"
        fields.append({
            "field": "citations",
            "prior": f"{len(prior.evidence_urls)}",
            "current": f"{len(current.evidence_urls)}",
            "marker": f"{sign}{abs(delta)}",
        })
    else:
        fields.append({
            "field": "citations",
            "prior": f"{len(prior.evidence_urls)}",
            "current": f"{len(current.evidence_urls)}",
            "marker": "= same",
        })

    # model (free vs hybrid vs paid)
    prior_model = prior.model or "—"
    curr_model = current.model or "—"
    if prior_model != curr_model:
        fields.append({
            "field": "model", "prior": prior_model, "current": curr_model,
            "marker": "↻ changed",
        })
    else:
        fields.append({
            "field": "model", "prior": prior_model, "current": curr_model,
            "marker": "= same",
        })

    return {
        "prior_id": prior.id,
        "prior_date": prior.date,
        "fields": fields,
    }


def _pct_marker(pct: float) -> str:
    if abs(pct) < 0.05:
        return "= same"
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


_PLACEMENT_DELTAS = {
    ("BUY",  "HOLD"): "▼ trim",
    ("BUY",  "SELL"): "▶ flip",
    ("HOLD", "BUY"):  "▲ start",
    ("HOLD", "SELL"): "▶ flip",
    ("SELL", "HOLD"): "▲ cover",
    ("SELL", "BUY"):  "▶ flip",
}


def _placement_marker(prior: str, current: str) -> str:
    delta = _PLACEMENT_DELTAS.get((prior, current))
    if delta:
        return delta
    return "↻ change"


# --------------------------------------------------------------- display
def db_meta(db_path: Path | str = DEFAULT_DB) -> dict:
    """Header info for the modal: count, ticker count, latest mtime."""
    p = Path(db_path)
    out = {
        "count": 0, "tickers": 0, "mtime": "—", "path": str(p),
    }
    if not p.exists():
        return out
    try:
        st = p.stat()
        out["mtime"] = datetime.fromtimestamp(st.st_mtime).strftime("%H:%M:%S")
    except OSError:
        pass
    rows = read_theses_all(p)
    out["count"] = len(rows)
    out["tickers"] = len({r.ticker for r in rows})
    return out
