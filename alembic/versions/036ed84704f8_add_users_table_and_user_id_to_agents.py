"""Add users table and user_id to agents

Revision ID: 036ed84704f8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-20 16:05:14.055763

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '036ed84704f8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='trader'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])

    # Add user_id column to agents table using batch mode for SQLite compatibility
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(36), nullable=True))
        batch_op.create_foreign_key('fk_agents_user_id', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop user_id column from agents table using batch mode for SQLite compatibility
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.drop_constraint('fk_agents_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')

    # Drop users table
    op.drop_index('ix_users_email', 'users')
    op.drop_index('ix_users_username', 'users')
    op.drop_table('users')
