"""Add external cash flow fields to portfolio snapshots."""

from alembic import op
import sqlalchemy as sa


revision = "b6c8d4e5f901"
down_revision = "a3f7c2d1e8b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add optional external contribution/withdrawal amounts."""
    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "external_added",
            sa.Numeric(20, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "external_withdrawn",
            sa.Numeric(20, 2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Remove external cash flow fields."""
    op.drop_column("portfolio_snapshots", "external_withdrawn")
    op.drop_column("portfolio_snapshots", "external_added")
