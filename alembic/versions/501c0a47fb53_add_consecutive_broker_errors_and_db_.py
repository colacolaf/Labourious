"""add_consecutive_broker_errors_and_db_indexes

Revision ID: 501c0a47fb53
Revises: 08a6fbe80b17
Create Date: 2026-06-24 18:01:56.442560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '501c0a47fb53'
down_revision: Union[str, Sequence[str], None] = '08a6fbe80b17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('agents', sa.Column('consecutive_broker_errors', sa.Integer(), nullable=False, server_default='0'))
    op.create_index('ix_trades_agent_status', 'trades', ['agent_id', 'status'])
    op.create_index('ix_trades_agent_opened', 'trades', ['agent_id', 'opened_at'])
    op.create_index('ix_daily_snapshots_agent_date', 'daily_snapshots', ['agent_id', 'date'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_trades_agent_status', table_name='trades')
    op.drop_index('ix_trades_agent_opened', table_name='trades')
    op.drop_index('ix_daily_snapshots_agent_date', table_name='daily_snapshots')
    op.drop_column('agents', 'consecutive_broker_errors')
