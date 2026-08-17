-- schema.sql — thesis register SQLite schema.
--
-- Usage:
--   sqlite3 theses.db < schema.sql
-- Or from Python:
--   import sqlite3; sqlite3.connect("theses.db").executescript(open("schema.sql").read())
--
-- All dates are ISO-8601 strings. All JSON fields are TEXT containing valid JSON.

CREATE TABLE IF NOT EXISTS theses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker TEXT NOT NULL,
  date TEXT NOT NULL,                   -- 'YYYY-MM-DD'
  thesis_text TEXT NOT NULL,
  conviction INTEGER NOT NULL,          -- 1..5
  bottom_line TEXT NOT NULL,            -- JSON
  evidence_urls TEXT NOT NULL,          -- JSON array of URLs
  flow_id TEXT NOT NULL,
  version INTEGER NOT NULL,             -- monotonically increasing per (ticker, flow_id)
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_theses_ticker_date ON theses(ticker, date DESC);
CREATE INDEX IF NOT EXISTS idx_theses_flow ON theses(flow_id);

CREATE TABLE IF NOT EXISTS updates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  thesis_id INTEGER NOT NULL REFERENCES theses(id) ON DELETE CASCADE,
  date TEXT NOT NULL,
  what_changed TEXT NOT NULL,
  new_thesis_text TEXT,
  deltas TEXT,                          -- JSON; fields that flipped + prior/new values
  reason TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_updates_thesis ON updates(thesis_id);

CREATE TABLE IF NOT EXISTS catalysts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker TEXT NOT NULL,
  event TEXT NOT NULL,
  expected_date TEXT,                   -- 'YYYY-MM-DD' or null for un-dated catalysts
  what_to_watch TEXT,
  resolved_date TEXT,
  resolved_outcome TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_catalysts_ticker ON catalysts(ticker);
CREATE INDEX IF NOT EXISTS idx_catalysts_resolved ON catalysts(resolved_date);

-- View: latest thesis per (ticker, flow_id).
CREATE VIEW IF NOT EXISTS v_latest_thesis AS
  SELECT t.* FROM theses t
  JOIN (
    SELECT ticker, flow_id, MAX(version) AS max_v, MAX(id) AS max_id
    FROM theses
    GROUP BY ticker, flow_id
  ) latest
    ON latest.max_id = t.id
  ORDER BY t.ticker, t.flow_id;
