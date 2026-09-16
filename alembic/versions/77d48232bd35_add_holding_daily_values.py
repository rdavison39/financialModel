"""add holding daily values

Revision ID: 77d48232bd35
Revises: increase_holding_gain_precision
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "77d48232bd35"
down_revision: Union[str, Sequence[str], None] = "increase_holding_gain_precision"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add brokerage-supplied daily holding values."""

    op.add_column(
        "holding_snapshots",
        sa.Column(
            "unrealized_gain_percent",
            sa.Numeric(20, 6),
            nullable=True,
        ),
    )

    op.add_column(
        "holding_snapshots",
        sa.Column(
            "daily_change",
            sa.Numeric(20, 6),
            nullable=True,
        ),
    )

    op.add_column(
        "holding_snapshots",
        sa.Column(
            "daily_change_percent",
            sa.Numeric(20, 6),
            nullable=True,
        ),
    )

    op.add_column(
        "holding_snapshots",
        sa.Column(
            "previous_close",
            sa.Numeric(20, 6),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove brokerage-supplied daily holding values."""

    op.drop_column("holding_snapshots", "previous_close")
    op.drop_column("holding_snapshots", "daily_change_percent")
    op.drop_column("holding_snapshots", "daily_change")
    op.drop_column("holding_snapshots", "unrealized_gain_percent")