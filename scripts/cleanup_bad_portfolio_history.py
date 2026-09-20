"""Remove incorrect portfolio valuation history for 2026-09-15 and 2026-09-16.

This script removes PortfolioSnapshot records only. It does not remove
ImportRecord, HoldingSnapshot, or CashSnapshot data.

Default behavior is a dry run. Pass --yes to perform the deletion.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

# Allow the script to be run directly from the project's scripts directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import delete, select

from src.database import get_session
from src.models.portfolio_snapshot import PortfolioSnapshot


BAD_DATES = (
    date(2026, 9, 15),
    date(2026, 9, 16),
)


def main() -> None:
    """Show or remove the incorrect portfolio snapshots."""
    parser = argparse.ArgumentParser(
        description=(
            "Remove incorrect PortfolioSnapshot history for "
            "2026-09-15 and 2026-09-16."
        )
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "Actually delete the records. Without this flag the script "
            "performs a dry run."
        ),
    )
    args = parser.parse_args()

    session = get_session()

    try:
        rows = list(
            session.scalars(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.snapshot_date.in_(BAD_DATES))
                .order_by(
                    PortfolioSnapshot.snapshot_date,
                    PortfolioSnapshot.account_id,
                    PortfolioSnapshot.id,
                )
            ).all()
        )

        if not rows:
            print(
                "No PortfolioSnapshot records found for "
                "2026-09-15 or 2026-09-16."
            )
            return

        print(
            f"Found {len(rows)} PortfolioSnapshot record(s) "
            "for the dates being cleaned:"
        )

        for row in rows:
            account_label = (
                "CONSOLIDATED"
                if row.account_id is None
                else f"account_id={row.account_id}"
            )
            print(
                f"  id={row.id}, date={row.snapshot_date}, "
                f"{account_label}, value={row.total_value}"
            )

        if not args.yes:
            print()
            print("DRY RUN — nothing was changed.")
            print(
                "Run with --yes to delete these PortfolioSnapshot "
                "records."
            )
            return

        # Use a Core DELETE rather than session.delete(row).  The latter
        # causes SQLAlchemy to flush the entire ORM unit of work and can
        # require every model's foreign-key table to be registered in
        # metadata.  This script only needs to delete these rows.
        result = session.execute(
            delete(PortfolioSnapshot).where(
                PortfolioSnapshot.snapshot_date.in_(BAD_DATES)
            )
        )
        session.commit()

        print()
        print(
            f"Deleted {result.rowcount} incorrect "
            "PortfolioSnapshot record(s)."
        )
        print(
            "ImportRecord, HoldingSnapshot, and CashSnapshot data "
            "were not changed."
        )

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
