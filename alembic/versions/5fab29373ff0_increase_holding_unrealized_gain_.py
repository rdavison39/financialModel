"""
Add average cost and unrealized gain to holding snapshots.

Revision ID: increase_holding_gain_precision
Revises: 1c9181242cd2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "increase_holding_gain_precision"
down_revision: Union[str, Sequence[str], None] = "1c9181242cd2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add brokerage-provided holding values."""

    with op.batch_alter_table("holding_snapshots") as batch_op:
        batch_op.add_column(
            sa.Column(
                "average_cost",
                sa.Numeric(20, 6),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "unrealized_gain",
                sa.Numeric(20, 6),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Remove brokerage-provided holding values."""

    with op.batch_alter_table("holding_snapshots") as batch_op:
        batch_op.drop_column("unrealized_gain")
        batch_op.drop_column("average_cost")