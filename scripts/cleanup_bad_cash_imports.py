"""
Remove the erroneous test imports for the two Nesbitt cash-only accounts.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy import delete, select

from src.database import get_session
from src.models.account import Account
from src.models.cash_snapshot import CashSnapshot
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord


ACCOUNT_NUMBERS = {
    "70556033",
    "70556060",
}


def main() -> None:
    """Remove the bad test records."""

    session = get_session()

    try:
        accounts = session.scalars(
            select(Account).where(
                Account.account_number.in_(ACCOUNT_NUMBERS)
            )
        ).all()

        account_ids = [account.id for account in accounts]

        if not account_ids:
            print("No matching accounts found.")
            return

        holdings_deleted = session.execute(
            delete(HoldingSnapshot).where(
                HoldingSnapshot.account_id.in_(account_ids)
            )
        ).rowcount

        cash_deleted = session.execute(
            delete(CashSnapshot).where(
                CashSnapshot.account_id.in_(account_ids)
            )
        ).rowcount

        imports_deleted = session.execute(
            delete(ImportRecord).where(
                ImportRecord.account_id.in_(account_ids)
            )
        ).rowcount

        session.commit()

        print(f"Holding snapshots deleted: {holdings_deleted}")
        print(f"Cash snapshots deleted:    {cash_deleted}")
        print(f"Import records deleted:     {imports_deleted}")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()