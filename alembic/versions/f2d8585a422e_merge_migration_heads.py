"""merge migration heads

Revision ID: f2d8585a422e
Revises: 7c1d4e8a2b6f, b6c8d4e5f901
Create Date: 2026-09-30 00:05:13.542179

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2d8585a422e'
down_revision: Union[str, Sequence[str], None] = ('7c1d4e8a2b6f', 'b6c8d4e5f901')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
