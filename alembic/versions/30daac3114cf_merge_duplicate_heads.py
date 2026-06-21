"""merge_duplicate_heads

Revision ID: 30daac3114cf
Revises: 036ed84704f8, 27340a9ab608
Create Date: 2026-06-20 17:05:02.391943

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30daac3114cf'
down_revision: Union[str, Sequence[str], None] = ('036ed84704f8', '27340a9ab608')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
