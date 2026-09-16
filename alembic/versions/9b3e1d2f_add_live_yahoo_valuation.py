"""Add live Yahoo valuation fields.

Revision ID: 9b3e1d2f
Revises: 77d48232bd35
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b3e1d2f"
down_revision: Union[str, Sequence[str], None] = "77d48232bd35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add live Yahoo valuation columns."""
    with op.batch_alter_table("holding_snapshots") as batch_op:
        batch_op.add_column(sa.Column("current_price", sa.Numeric(20, 6), nullable=True))
        batch_op.add_column(sa.Column("current_market_value", sa.Numeric(20, 2), nullable=True))
        batch_op.add_column(sa.Column("current_previous_close", sa.Numeric(20, 6), nullable=True))
        batch_op.add_column(sa.Column("current_daily_change", sa.Numeric(20, 6), nullable=True))
        batch_op.add_column(sa.Column("current_daily_change_percent", sa.Numeric(20, 6), nullable=True))

    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.add_column(sa.Column("daily_change", sa.Numeric(20, 6), nullable=True))
        batch_op.add_column(sa.Column("daily_change_percent", sa.Numeric(20, 6), nullable=True))


def downgrade() -> None:
    """Remove live Yahoo valuation columns."""
    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.drop_column("daily_change_percent")
        batch_op.drop_column("daily_change")

    with op.batch_alter_table("holding_snapshots") as batch_op:
        batch_op.drop_column("current_daily_change_percent")
        batch_op.drop_column("current_daily_change")
        batch_op.drop_column("current_previous_close")
        batch_op.drop_column("current_market_value")
        batch_op.drop_column("current_price")
