"""Add external cash flow fields to brokerage import snapshots.

Revision ID: 91a4c7d8e2f1
Revises: f2d8585a422e
"""

from alembic import op
import sqlalchemy as sa


revision = "91a4c7d8e2f1"
down_revision = "f2d8585a422e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "import_records",
        sa.Column(
            "external_added",
            sa.Numeric(20, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "import_records",
        sa.Column(
            "external_withdrawn",
            sa.Numeric(20, 2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("import_records", "external_withdrawn")
    op.drop_column("import_records", "external_added")
