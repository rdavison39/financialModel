"""Enforce one brokerage import snapshot per account per day."""

from alembic import op
import sqlalchemy as sa


revision = "a3f7c2d1e8b4"
down_revision = "9b3e1d2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add snapshot_day and enforce one snapshot per account/day."""

    connection = op.get_bind()

    # Add the calendar-day key temporarily as nullable so existing rows
    # can be backfilled before the NOT NULL constraint is applied.
    op.add_column(
        "import_records",
        sa.Column(
            "snapshot_day",
            sa.Date(),
            nullable=True,
        ),
    )

    connection.execute(
        sa.text(
            """
            UPDATE import_records
            SET snapshot_day = date(snapshot_date)
            """
        )
    )

    # Older versions allowed multiple timestamps for the same account/day.
    # Keep the newest source timestamp and remove the dependent holding/cash
    # rows belonging to older same-day imports before creating the new
    # uniqueness constraint.
    rows = connection.execute(
        sa.text(
            """
            SELECT
                id,
                brokerage_id,
                account_id,
                snapshot_date
            FROM import_records
            ORDER BY brokerage_id, account_id, snapshot_date DESC, id DESC
            """
        )
    ).mappings().all()

    seen: set[tuple[int, int, str]] = set()

    for row in rows:
        key = (
            int(row["brokerage_id"]),
            int(row["account_id"]),
            str(row["snapshot_date"])[:10],
        )

        if key not in seen:
            seen.add(key)
            continue

        connection.execute(
            sa.text(
                """
                DELETE FROM holding_snapshots
                WHERE account_id = :account_id
                  AND snapshot_date = :snapshot_date
                """
            ),
            {
                "account_id": row["account_id"],
                "snapshot_date": row["snapshot_date"],
            },
        )

        connection.execute(
            sa.text(
                """
                DELETE FROM cash_snapshots
                WHERE account_id = :account_id
                  AND snapshot_date = :snapshot_date
                """
            ),
            {
                "account_id": row["account_id"],
                "snapshot_date": row["snapshot_date"],
            },
        )

        connection.execute(
            sa.text(
                """
                DELETE FROM import_records
                WHERE id = :id
                """
            ),
            {"id": row["id"]},
        )

    with op.batch_alter_table(
        "import_records",
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_import_brokerage_account_snapshot",
            type_="unique",
        )
        batch_op.alter_column(
            "snapshot_day",
            existing_type=sa.Date(),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            "uq_import_brokerage_account_snapshot_day",
            [
                "brokerage_id",
                "account_id",
                "snapshot_day",
            ],
        )


def downgrade() -> None:
    """Restore the previous timestamp-based uniqueness rule."""

    with op.batch_alter_table(
        "import_records",
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_import_brokerage_account_snapshot_day",
            type_="unique",
        )
        batch_op.drop_column("snapshot_day")
        batch_op.create_unique_constraint(
            "uq_import_brokerage_account_snapshot",
            [
                "brokerage_id",
                "account_id",
                "snapshot_date",
            ],
        )
