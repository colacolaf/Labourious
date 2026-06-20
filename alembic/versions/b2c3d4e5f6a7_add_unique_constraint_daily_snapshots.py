"""add_unique_constraint_daily_snapshots

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-19 21:00:00.000000

"""
from alembic import op

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade schema."""
    # SQLite doesn't support ADD CONSTRAINT, so recreate table
    op.execute("""
        CREATE TABLE daily_snapshots_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            date VARCHAR(10) NOT NULL,
            total_pnl REAL NOT NULL DEFAULT 0.0,
            daily_return_pct REAL NOT NULL DEFAULT 0.0,
            sharpe_ratio REAL,
            max_drawdown REAL,
            win_rate REAL,
            trade_count INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            UNIQUE(agent_id, date)
        )
    """)
    op.execute("""
        INSERT INTO daily_snapshots_new
        SELECT id, agent_id, date, total_pnl, daily_return_pct, sharpe_ratio, max_drawdown, win_rate, trade_count, created_at
        FROM daily_snapshots
    """)
    op.execute("DROP TABLE daily_snapshots")
    op.execute("ALTER TABLE daily_snapshots_new RENAME TO daily_snapshots")


def downgrade():
    """Downgrade schema."""
    op.execute("""
        CREATE TABLE daily_snapshots_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            date VARCHAR(10) NOT NULL,
            total_pnl REAL NOT NULL DEFAULT 0.0,
            daily_return_pct REAL NOT NULL DEFAULT 0.0,
            sharpe_ratio REAL,
            max_drawdown REAL,
            win_rate REAL,
            trade_count INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL
        )
    """)
    op.execute("""
        INSERT INTO daily_snapshots_new
        SELECT id, agent_id, date, total_pnl, daily_return_pct, sharpe_ratio, max_drawdown, win_rate, trade_count, created_at
        FROM daily_snapshots
    """)
    op.execute("DROP TABLE daily_snapshots")
    op.execute("ALTER TABLE daily_snapshots_new RENAME TO daily_snapshots")
