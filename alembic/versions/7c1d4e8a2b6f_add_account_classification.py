"""
Add account classification and portfolio inclusion settings.

Revision ID: 7c1d4e8a2b6f
Revises: 4b7f3a2c91d1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c1d4e8a2b6f"
down_revision: Union[str, Sequence[str], None] = "4b7f3a2c91d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add account classification and portfolio inclusion fields."""
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "account_type",
                sa.String(length=20),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "include_in_portfolio",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )


def downgrade() -> None:
    """Remove account classification and portfolio inclusion fields."""
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_column("include_in_portfolio")
        batch_op.drop_column("account_type")
