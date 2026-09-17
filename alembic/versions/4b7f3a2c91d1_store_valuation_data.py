"""
Store calculated portfolio valuation data.

Revision ID: 4b7f3a2c91d1
Revises: a3f7c2d1e8b4
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4b7f3a2c91d1"
down_revision: Union[str, Sequence[str], None] = "a3f7c2d1e8b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add cached valuation fields to portfolio snapshots."""
    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tsx_daily_change_percent",
                sa.Numeric(20, 6),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "usd_to_cad",
                sa.Numeric(20, 8),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "valuation_updated_at",
                sa.DateTime(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "valuation_data",
                sa.Text(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Remove cached valuation fields."""
    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.drop_column("valuation_data")
        batch_op.drop_column("valuation_updated_at")
        batch_op.drop_column("usd_to_cad")
        batch_op.drop_column("tsx_daily_change_percent")