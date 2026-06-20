"""make_backtest_results_agent_id_nullable

Revision ID: a1b2c3d4e5f6
Revises: 692528d26114
Create Date: 2026-06-19 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '692528d26114'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite doesn't support ALTER TABLE DROP CONSTRAINT, so we recreate the table
    # with agent_id as nullable and without FK constraint
    op.execute("""
        CREATE TABLE backtest_results_new (
            id VARCHAR(36) NOT NULL,
            agent_id INTEGER,
            run_at DATETIME NOT NULL,
            start_date VARCHAR(10) NOT NULL,
            end_date VARCHAR(10) NOT NULL,
            mode VARCHAR(20) NOT NULL DEFAULT 'basic',
            status VARCHAR(20) NOT NULL DEFAULT 'running',
            result_json JSON,
            PRIMARY KEY (id)
        )
    """)
    op.execute("""
        INSERT INTO backtest_results_new
        SELECT id, agent_id, run_at, start_date, end_date, mode, status, result_json
        FROM backtest_results
    """)
    op.execute("DROP TABLE backtest_results")
    op.execute("ALTER TABLE backtest_results_new RENAME TO backtest_results")


def downgrade() -> None:
    """Downgrade schema."""
    # Revert to the old schema with FK constraint
    op.execute("""
        CREATE TABLE backtest_results_new (
            id VARCHAR(36) NOT NULL,
            agent_id INTEGER NOT NULL,
            run_at DATETIME NOT NULL,
            start_date VARCHAR(10) NOT NULL,
            end_date VARCHAR(10) NOT NULL,
            mode VARCHAR(20) NOT NULL DEFAULT 'basic',
            status VARCHAR(20) NOT NULL DEFAULT 'running',
            result_json JSON,
            PRIMARY KEY (id),
            FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
        )
    """)
    op.execute("""
        INSERT INTO backtest_results_new
        SELECT id, agent_id, run_at, start_date, end_date, mode, status, result_json
        FROM backtest_results
        WHERE agent_id IS NOT NULL
    """)
    op.execute("DROP TABLE backtest_results")
    op.execute("ALTER TABLE backtest_results_new RENAME TO backtest_results")
