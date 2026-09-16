"""
Allow consolidated portfolio snapshots.

Revision ID: 1c9181242cd2
Revises:
Create Date: 2026-09-15 17:05:53.191037
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c9181242cd2"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow account_id to be NULL for consolidated snapshots."""

    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.alter_column(
            "account_id",
            existing_type=sa.INTEGER(),
            nullable=True,
        )


def downgrade() -> None:
    """Require account_id for all portfolio snapshots."""

    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.alter_column(
            "account_id",
            existing_type=sa.INTEGER(),
            nullable=False,
        )