"""add_notification_preferences

Revision ID: 46ea0c10600c
Revises: 30daac3114cf
Create Date: 2026-06-20 17:06:03.187220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46ea0c10600c'
down_revision: Union[str, Sequence[str], None] = '30daac3114cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user_notification_preferences table for 4B.1
    op.create_table('user_notification_preferences',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column('sms_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column('phone_number', sa.String(length=20), nullable=True),
    sa.Column('notify_on_trade', sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column('notify_on_agent_pause', sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column('notify_on_drawdown', sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column('daily_digest', sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_notification_preferences')
