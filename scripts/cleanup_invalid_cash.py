"""
Remove invalid cash snapshot records.

This is a one-time cleanup for historical imports where
rows such as "Total(in CAD)" were incorrectly imported as
cash currencies.
"""

import sys
from pathlib import Path

from sqlalchemy import delete, select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_session
from src.database_init import initialize_database
from src.models.cash_snapshot import CashSnapshot


VALID_CURRENCIES = {"CAD", "USD"}


def main() -> None:
    """Remove invalid cash snapshot records."""

    initialize_database()

    session = get_session()

    try:
        invalid_records = list(
            session.scalars(
                select(CashSnapshot).where(
                    CashSnapshot.currency.not_in(
                        VALID_CURRENCIES
                    )
                )
            ).all()
        )

        print(
            f"Invalid cash records found: "
            f"{len(invalid_records)}"
        )

        for record in invalid_records:
            print(
                f"  ID={record.id} "
                f"Account={record.account_id} "
                f"Date={record.snapshot_date} "
                f"Currency={record.currency} "
                f"Amount={record.amount}"
            )

        if not invalid_records:
            print("Nothing to clean up.")
            return

        deleted = session.execute(
            delete(CashSnapshot).where(
                CashSnapshot.currency.not_in(
                    VALID_CURRENCIES
                )
            )
        )

        session.commit()

        print(
            f"\nDeleted {deleted.rowcount} invalid "
            "cash records."
        )

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()